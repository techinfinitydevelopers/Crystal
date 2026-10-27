import random
import string
from django.db import models
from django.utils import timezone


class Enquiry(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('in_discussion', 'In Discussion'),
        ('quotation_sent', 'Quotation Sent'),
        ('converted', 'Converted'),
        ('closed', 'Closed'),
    ]

    BUSINESS_TYPE_CHOICES = [
        ('dealer', 'Dealer'),
        ('distributor', 'Distributor'),
        ('retailer', 'Retailer'),
        ('customer', 'Customer'),
        ('other', 'Other'),
    ]

    ref_number = models.CharField(max_length=20, unique=True, blank=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    company_name = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPE_CHOICES, default='customer')
    message = models.TextField(blank=True)
    source_page = models.CharField(max_length=300, blank=True, help_text='The page the enquiry was sent from.')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Enquiries'

    def __str__(self):
        return f"{self.ref_number} - {self.full_name}"

    def save(self, *args, **kwargs):
        if not self.ref_number:
            date_str = timezone.now().strftime('%Y%m%d')
            rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            self.ref_number = f"CRY-{date_str}-{rand_str}"
        super().save(*args, **kwargs)


class EnquiryItem(models.Model):
    enquiry = models.ForeignKey(Enquiry, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='enquiry_items')
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=100, blank=True)
    image = models.CharField(max_length=500, blank=True, help_text='The product photo the customer saw.')
    site_id = models.CharField(max_length=120, blank=True, help_text="The product's id on the website (Product.html?p=...).")
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.enquiry.ref_number}: {self.product_name} x{self.quantity}"


class WebsiteMessage(models.Model):
    """A message from the Contact or Request-a-quote form.

    These forms used to show "your message is on its way" without sending
    anything; every one is now stored here and emailed to the sales team.
    """
    KIND_CHOICES = [
        ('contact', 'Contact form'),
        ('quote', 'Request a quote'),
    ]
    STATUS_CHOICES = [
        ('new', 'New'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=200, blank=True, help_text='Contact: topic. Quote: enquiry type.')
    product_interest = models.CharField(max_length=200, blank=True)
    quantity = models.CharField(max_length=100, blank=True)
    message = models.TextField()
    source_page = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact / quote message'
        verbose_name_plural = 'Contact / quote messages'

    def __str__(self):
        return f"{self.get_kind_display()} - {self.full_name}"
