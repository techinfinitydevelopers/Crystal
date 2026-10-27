"""Emails sent when an enquiry arrives.

Two go out: a thank-you to the customer so they know a real person has it, and
a notification to Crystal so somebody acts on it. Neither is allowed to break
the submission — an enquiry that reached the database is a won lead even if
the mail server is down, so failures are logged and swallowed rather than
raised back to the customer as an error.

Delivery needs SMTP credentials in the environment (EMAIL_HOST_USER /
EMAIL_HOST_PASSWORD, or a full EMAIL_BACKEND). Without them Django's default
console backend just prints the message, which is a safe no-op.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.html import escape

logger = logging.getLogger(__name__)


def team_recipients():
    """sales@crystalcook.com always; ADMIN_NOTIFICATION_EMAIL too, when set."""
    to = list(getattr(settings, "ENQUIRY_NOTIFY_EMAILS", []) or [])
    extra = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", "")
    if extra and extra not in to:
        to.append(extra)
    return to


def _site_url(path):
    """A site-relative path ("product-photos/x.jpg") as a link an inbox can open."""
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    return settings.PUBLIC_SITE_URL.rstrip("/") + "/" + path.lstrip("/")


def _when(dt):
    local = timezone.localtime(dt)
    return local.strftime("%d %b %Y, %I:%M %p")


def _row(label, value):
    return ('<tr><td style="padding:6px 0;color:#8a8a8a;width:130px;vertical-align:top;">%s</td>'
            '<td style="padding:6px 0;">%s</td></tr>' % (escape(label), value or "&mdash;"))


def _items_text(enquiry):
    lines = []
    for item in enquiry.items.all():
        code = f" ({item.product_sku})" if item.product_sku else ""
        lines.append(f"  - {item.product_name}{code} x {item.quantity}")
    return "\n".join(lines)


def _items_html(enquiry):
    rows = []
    for item in enquiry.items.all():
        code = (f'<span style="color:#8a8a8a;font-size:12px;"> · {escape(item.product_sku)}</span>'
                if item.product_sku else "")
        rows.append(
            '<tr>'
            f'<td style="padding:10px 0;border-bottom:1px solid #eee;">{escape(item.product_name)}{code}</td>'
            f'<td style="padding:10px 0;border-bottom:1px solid #eee;text-align:right;'
            f'white-space:nowrap;color:#616161;">Qty {item.quantity}</td>'
            '</tr>'
        )
    return "".join(rows)


def _send(subject, to, text, html, reply_to=None):
    if not to:
        return False
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to] if isinstance(to, str) else list(to),
            reply_to=[reply_to] if reply_to else None,
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception:
        # An enquiry that reached the database is still a won lead; losing the
        # email must not lose the enquiry, and must not show the customer an
        # error for something that already succeeded.
        logger.exception("Could not send enquiry email to %s", to)
        return False


def send_customer_thank_you(enquiry):
    """Confirm to the customer that a person has their enquiry."""
    first = (enquiry.full_name or "").split()[0] if enquiry.full_name else "there"
    subject = f"Thank you — we have your enquiry ({enquiry.ref_number})"

    text = (
        f"Hi {first},\n\n"
        "Thank you for your enquiry with Crystal Cook N Serve Products.\n"
        f"Your reference number is {enquiry.ref_number}. Please quote it if you "
        "get in touch.\n\n"
        "What you asked about:\n"
        f"{_items_text(enquiry)}\n\n"
        "Our team will review it and come back to you with pricing and "
        "availability, usually within one working day.\n\n"
        "This was an enquiry, not an order — nothing has been charged.\n\n"
        "Crystal Cook N Serve Products Pvt. Ltd.\n"
        "Customer support: 022-49702803/06\n"
    )

    html = f"""\
<div style="font-family:Inter,-apple-system,'Segoe UI',Roboto,sans-serif;
            max-width:560px;margin:0 auto;color:#303030;line-height:1.6;">
  <div style="background:#ED3338;color:#fff;padding:22px 26px;border-radius:12px 12px 0 0;">
    <div style="font-weight:700;font-size:19px;letter-spacing:-0.01em;">Thank you, {escape(first)}</div>
    <div style="opacity:.9;font-size:13.5px;margin-top:4px;">We have your enquiry.</div>
  </div>
  <div style="border:1px solid #e1e1e1;border-top:0;border-radius:0 0 12px 12px;padding:26px;">
    <p style="margin:0 0 18px;">
      Your reference is
      <strong style="font-variant-numeric:tabular-nums;">{escape(enquiry.ref_number)}</strong>.
      Please quote it if you get in touch.
    </p>
    <p style="margin:0 0 8px;font-size:12px;font-weight:600;letter-spacing:.06em;
              text-transform:uppercase;color:#8a8a8a;">What you asked about</p>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">{_items_html(enquiry)}</table>
    <p style="margin:22px 0 0;">
      Our team will review it and come back to you with pricing and availability,
      usually within one working day.
    </p>
    <p style="margin:16px 0 0;color:#616161;font-size:13px;">
      This was an enquiry, not an order — nothing has been charged.
    </p>
    <p style="margin:22px 0 0;padding-top:16px;border-top:1px solid #e1e1e1;
              color:#8a8a8a;font-size:12.5px;">
      Crystal Cook N Serve Products Pvt. Ltd.<br>Customer support: 022-49702803/06
    </p>
  </div>
</div>"""

    return _send(subject, enquiry.email, text, html)


def _team_items_text(enquiry):
    lines = []
    for n, item in enumerate(enquiry.items.all(), 1):
        bits = [f"{n}. {item.product_name}", f"   Quantity: {item.quantity}"]
        if item.product_sku:
            bits.append(f"   SKU: {item.product_sku}")
        if item.brand:
            bits.append(f"   Brand: {item.brand.title()}")
        if item.category:
            bits.append(f"   Category: {item.category.replace('-', ' ').title()}")
        if item.site_id:
            bits.append(f"   Link: {_site_url('Product.html?p=' + item.site_id)}")
        lines.append("\n".join(bits))
    return "\n\n".join(lines)


def _team_items_html(enquiry):
    rows = []
    for item in enquiry.items.all():
        img = _site_url(item.image)
        pic = (f'<img src="{escape(img)}" width="64" height="64" alt="" '
               f'style="display:block;width:64px;height:64px;object-fit:contain;'
               f'border:1px solid #eee;border-radius:8px;background:#fff;">' if img else "")
        link = _site_url("Product.html?p=" + item.site_id) if item.site_id else ""
        name = (f'<a href="{escape(link)}" style="color:#ED3338;font-weight:600;text-decoration:none;">'
                f'{escape(item.product_name)}</a>' if link
                else f'<strong>{escape(item.product_name)}</strong>')
        meta = " · ".join(escape(x) for x in (
            ("SKU " + item.product_sku) if item.product_sku else "",
            item.brand.title() if item.brand else "",
            item.category.replace("-", " ").title() if item.category else "") if x)
        rows.append(
            '<tr>'
            f'<td style="padding:10px 12px 10px 0;border-bottom:1px solid #eee;width:64px;">{pic}</td>'
            f'<td style="padding:10px 0;border-bottom:1px solid #eee;">{name}'
            f'<div style="color:#8a8a8a;font-size:12.5px;margin-top:2px;">{meta}</div></td>'
            f'<td style="padding:10px 0;border-bottom:1px solid #eee;text-align:right;'
            f'white-space:nowrap;font-weight:600;">Qty {item.quantity}</td>'
            '</tr>'
        )
    return "".join(rows)


def send_team_notification(enquiry):
    """Tell the sales team an enquiry is waiting -- every field the customer
    filled in and every product with its code, brand, category, quantity,
    photo and link -- with reply-to set to the customer."""
    to = team_recipients()
    if not to:
        return False

    count = enquiry.items.count()
    subject = f"New product enquiry {enquiry.ref_number} — {enquiry.full_name} ({count} product{'s' if count != 1 else ''})"
    where = ", ".join(x for x in (enquiry.city, enquiry.state, enquiry.country) if x)
    page = _site_url(enquiry.source_page) if enquiry.source_page else ""

    text = (
        f"New product enquiry from the website.\n\n"
        f"Reference: {enquiry.ref_number}\n"
        f"Received: {_when(enquiry.created_at)}\n"
        f"Name: {enquiry.full_name}\n"
        f"Email: {enquiry.email}\n"
        f"Phone: {enquiry.phone}\n"
        f"Company: {enquiry.company_name or '-'}\n"
        f"Business type: {enquiry.get_business_type_display()}\n"
        f"City / State / Country: {where}\n"
        f"Sent from: {page or '-'}\n\n"
        f"Message:\n{enquiry.message or '-'}\n\n"
        f"Products ({count}):\n\n{_team_items_text(enquiry)}\n\n"
        f"Reply to this email to answer {enquiry.full_name} directly.\n"
    )

    details = "".join([
        _row("Reference", f"<strong>{escape(enquiry.ref_number)}</strong>"),
        _row("Received", escape(_when(enquiry.created_at))),
        _row("Name", escape(enquiry.full_name)),
        _row("Email", f'<a href="mailto:{escape(enquiry.email)}">{escape(enquiry.email)}</a>'),
        _row("Phone", f'<a href="tel:{escape(enquiry.phone)}">{escape(enquiry.phone)}</a>'),
        _row("Company", escape(enquiry.company_name)),
        _row("Business type", escape(enquiry.get_business_type_display())),
        _row("City / State / Country", escape(where)),
        _row("Sent from", f'<a href="{escape(page)}">{escape(page)}</a>' if page else ""),
    ])
    message = (f'<p style="margin:20px 0 6px;font-size:12px;font-weight:600;letter-spacing:.06em;'
               f'text-transform:uppercase;color:#8a8a8a;">Message</p>'
               f'<p style="margin:0;padding:14px;background:#f6f6f7;border-radius:8px;white-space:pre-wrap;">'
               f'{escape(enquiry.message)}</p>') if enquiry.message else ""

    html = f"""\
<div style="font-family:Inter,-apple-system,'Segoe UI',Roboto,sans-serif;
            max-width:640px;color:#303030;line-height:1.6;">
  <div style="background:#ED3338;color:#fff;padding:18px 22px;border-radius:12px 12px 0 0;">
    <div style="font-weight:700;font-size:18px;">New product enquiry — {escape(enquiry.ref_number)}</div>
    <div style="opacity:.9;font-size:13px;margin-top:2px;">
      {count} product{'s' if count != 1 else ''} · reply to this email to answer {escape(enquiry.full_name)} directly
    </div>
  </div>
  <div style="border:1px solid #e1e1e1;border-top:0;border-radius:0 0 12px 12px;padding:22px;">
    <table style="width:100%;border-collapse:collapse;font-size:14px;">{details}</table>
    {message}
    <p style="margin:22px 0 6px;font-size:12px;font-weight:600;letter-spacing:.06em;
              text-transform:uppercase;color:#8a8a8a;">Products ({count})</p>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">{_team_items_html(enquiry)}</table>
  </div>
</div>"""

    return _send(subject, to, text, html, reply_to=enquiry.email)


def send_message_notification(msg):
    """A Contact or Request-a-quote form, every field, to the sales team."""
    to = team_recipients()
    if not to:
        return False
    kind = msg.get_kind_display()
    subject = f"{kind} — {msg.full_name}" + (f" ({msg.subject})" if msg.subject else "")
    page = _site_url(msg.source_page) if msg.source_page else ""
    topic_label = "Enquiry type" if msg.kind == "quote" else "Subject"

    fields = [
        ("Form", kind),
        ("Received", _when(msg.created_at)),
        ("Name", msg.full_name),
        ("Email", msg.email),
        ("Phone", msg.phone),
        ("Company", msg.company_name),
        (topic_label, msg.subject),
        ("Product interest", msg.product_interest),
        ("Quantity", msg.quantity),
        ("Sent from", page),
    ]
    if msg.kind == "contact":
        fields = [f for f in fields if f[0] not in ("Company", "Product interest", "Quantity")]

    text = "\n".join(f"{k}: {v or '-'}" for k, v in fields) + f"\n\nMessage:\n{msg.message}\n"
    rows = []
    for k, v in fields:
        if k == "Email" and v:
            v = f'<a href="mailto:{escape(v)}">{escape(v)}</a>'
        elif k == "Phone" and v:
            v = f'<a href="tel:{escape(v)}">{escape(v)}</a>'
        elif k == "Sent from" and v:
            v = f'<a href="{escape(v)}">{escape(v)}</a>'
        else:
            v = escape(v)
        rows.append(_row(k, v))

    html = f"""\
<div style="font-family:Inter,-apple-system,'Segoe UI',Roboto,sans-serif;
            max-width:640px;color:#303030;line-height:1.6;">
  <div style="background:#ED3338;color:#fff;padding:18px 22px;border-radius:12px 12px 0 0;">
    <div style="font-weight:700;font-size:18px;">{escape(kind)} — {escape(msg.full_name)}</div>
    <div style="opacity:.9;font-size:13px;margin-top:2px;">Reply to this email to answer them directly.</div>
  </div>
  <div style="border:1px solid #e1e1e1;border-top:0;border-radius:0 0 12px 12px;padding:22px;">
    <table style="width:100%;border-collapse:collapse;font-size:14px;">{''.join(rows)}</table>
    <p style="margin:20px 0 6px;font-size:12px;font-weight:600;letter-spacing:.06em;
              text-transform:uppercase;color:#8a8a8a;">Message</p>
    <p style="margin:0;padding:14px;background:#f6f6f7;border-radius:8px;white-space:pre-wrap;">{escape(msg.message)}</p>
  </div>
</div>"""
    return _send(subject, to, text, html, reply_to=msg.email)


def send_enquiry_emails(enquiry):
    """Both messages. Returns what actually went out, for the API response."""
    return {
        "customer": send_customer_thank_you(enquiry),
        "team": send_team_notification(enquiry),
    }
