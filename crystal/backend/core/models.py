from django.db import models


class ContactSubmission(models.Model):
    SUBJECT_CHOICES = [
        ('general_inquiry', 'General Inquiry'),
        ('product_inquiry', 'Product Inquiry'),
        ('bulk_order', 'Bulk Order / Distributorship'),
        ('partnership', 'Partnership & Export'),
        ('customer_support', 'Customer Support'),
    ]

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=30, choices=SUBJECT_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.get_subject_display()}"
