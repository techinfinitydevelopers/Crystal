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
from django.utils.html import escape

logger = logging.getLogger(__name__)


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


def send_team_notification(enquiry):
    """Tell Crystal an enquiry is waiting, with reply-to set to the customer."""
    to = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", "")
    if not to:
        return False

    subject = f"New enquiry {enquiry.ref_number} — {enquiry.full_name}"
    company = f"\nCompany: {enquiry.company_name}" if enquiry.company_name else ""
    note = f"\n\nMessage:\n{enquiry.message}" if enquiry.message else ""

    text = (
        f"{enquiry.full_name} sent an enquiry.\n\n"
        f"Reference: {enquiry.ref_number}\n"
        f"Email: {enquiry.email}\n"
        f"Phone: {enquiry.phone}{company}\n"
        f"Where: {enquiry.city}, {enquiry.state}, {enquiry.country}\n"
        f"Type: {enquiry.get_business_type_display()}\n\n"
        f"Products:\n{_items_text(enquiry)}{note}\n"
    )

    html = f"""\
<div style="font-family:Inter,-apple-system,'Segoe UI',Roboto,sans-serif;
            max-width:600px;color:#303030;line-height:1.6;">
  <h2 style="margin:0 0 4px;font-size:18px;">New enquiry — {escape(enquiry.ref_number)}</h2>
  <p style="margin:0 0 18px;color:#616161;font-size:13.5px;">
    Reply to this email to answer {escape(enquiry.full_name)} directly.
  </p>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    <tr><td style="padding:6px 0;color:#8a8a8a;width:110px;">Name</td><td>{escape(enquiry.full_name)}</td></tr>
    <tr><td style="padding:6px 0;color:#8a8a8a;">Email</td><td>{escape(enquiry.email)}</td></tr>
    <tr><td style="padding:6px 0;color:#8a8a8a;">Phone</td><td>{escape(enquiry.phone)}</td></tr>
    <tr><td style="padding:6px 0;color:#8a8a8a;">Company</td><td>{escape(enquiry.company_name) or '&mdash;'}</td></tr>
    <tr><td style="padding:6px 0;color:#8a8a8a;">Where</td><td>{escape(enquiry.city)}, {escape(enquiry.state)}, {escape(enquiry.country)}</td></tr>
    <tr><td style="padding:6px 0;color:#8a8a8a;">Type</td><td>{escape(enquiry.get_business_type_display())}</td></tr>
  </table>
  <p style="margin:20px 0 6px;font-size:12px;font-weight:600;letter-spacing:.06em;
            text-transform:uppercase;color:#8a8a8a;">Products</p>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">{_items_html(enquiry)}</table>
  {'<p style="margin:20px 0 0;padding:14px;background:#f6f6f7;border-radius:8px;">'
   + escape(enquiry.message) + '</p>' if enquiry.message else ''}
</div>"""

    return _send(subject, to, text, html, reply_to=enquiry.email)


def send_enquiry_emails(enquiry):
    """Both messages. Returns what actually went out, for the API response."""
    return {
        "customer": send_customer_thank_you(enquiry),
        "team": send_team_notification(enquiry),
    }
