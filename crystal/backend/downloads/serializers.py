from rest_framework import serializers
from .models import Download


class DownloadSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True, default=None)
    brand_slug = serializers.CharField(source='brand.slug', read_only=True, default=None)
    file_url = serializers.SerializerMethodField()

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None

    class Meta:
        model = Download
        fields = [
            'id', 'title', 'slug', 'brand_name', 'brand_slug',
            'file', 'file_url', 'thumbnail', 'category', 'description',
            'is_active', 'created_at',
        ]
