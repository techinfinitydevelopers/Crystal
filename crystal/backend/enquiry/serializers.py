import re
from rest_framework import serializers
from .models import Enquiry, EnquiryItem


class EnquiryItemInputSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField()
    brand = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    sku = serializers.CharField(required=False, allow_blank=True)
    img = serializers.CharField(required=False, allow_blank=True)
    qty = serializers.IntegerField(min_value=1, default=1)


class EnquiryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=2)
    email = serializers.EmailField()
    phone = serializers.CharField(min_length=7, max_length=20)
    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField(default='India')
    businessType = serializers.ChoiceField(choices=['Dealer', 'Distributor', 'Retailer', 'Customer', 'Other'])
    company = serializers.CharField(required=False, allow_blank=True, default='')
    message = serializers.CharField(required=False, allow_blank=True, default='')
    items = EnquiryItemInputSerializer(many=True)

    def validate_phone(self, value):
        if not re.match(r'^[\d\s\+\(\)\-]{7,20}$', value):
            raise serializers.ValidationError('Invalid phone number format.')
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('At least one product must be in the enquiry.')
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        business_type_map = {
            'Dealer': 'dealer',
            'Distributor': 'distributor',
            'Retailer': 'retailer',
            'Customer': 'customer',
            'Other': 'other',
        }
        enquiry = Enquiry.objects.create(
            full_name=validated_data['name'],
            email=validated_data['email'],
            phone=validated_data['phone'],
            city=validated_data['city'],
            state=validated_data['state'],
            country=validated_data.get('country', 'India'),
            business_type=business_type_map.get(validated_data['businessType'], 'customer'),
            company_name=validated_data.get('company', ''),
            message=validated_data.get('message', ''),
        )
        for item in items_data:
            from products.models import Product
            product_obj = None
            product_id_slug = item.get('id', '')
            if product_id_slug:
                product_obj = Product.objects.filter(slug=product_id_slug).first()
            EnquiryItem.objects.create(
                enquiry=enquiry,
                product=product_obj,
                product_name=item['name'],
                product_sku=item.get('sku', ''),
                quantity=item.get('qty', 1),
            )
        return enquiry
