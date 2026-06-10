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
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.enquiry.ref_number}: {self.product_name} x{self.quantity}"
