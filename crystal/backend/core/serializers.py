from rest_framework import serializers
from .models import ContactSubmission


class ContactSerializer(serializers.ModelSerializer):
    subject = serializers.ChoiceField(choices=[
        'General Inquiry', 'Product Inquiry',
        'Bulk Order / Distributorship', 'Partnership & Export', 'Customer Support',
    ])

    class Meta:
        model = ContactSubmission
        fields = ['full_name', 'email', 'phone', 'subject', 'message']

    def validate_message(self, value):
        if len(value) < 10:
            raise serializers.ValidationError('Message must be at least 10 characters.')
        return value

    def create(self, validated_data):
        subject_map = {
            'General Inquiry': 'general_inquiry',
            'Product Inquiry': 'product_inquiry',
            'Bulk Order / Distributorship': 'bulk_order',
            'Partnership & Export': 'partnership',
            'Customer Support': 'customer_support',
        }
        validated_data['subject'] = subject_map.get(validated_data['subject'], validated_data['subject'])
        return super().create(validated_data)
