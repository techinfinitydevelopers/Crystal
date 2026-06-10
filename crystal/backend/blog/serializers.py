from rest_framework import serializers
from .models import BlogCategory, Blog


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ['id', 'name', 'slug']


class BlogListSerializer(serializers.ModelSerializer):
    category = BlogCategorySerializer(read_only=True)

    class Meta:
        model = Blog
        fields = [
            'id', 'title', 'slug', 'excerpt', 'featured_image',
            'author', 'category', 'is_published', 'published_at',
        ]


class BlogDetailSerializer(serializers.ModelSerializer):
    category = BlogCategorySerializer(read_only=True)

    class Meta:
        model = Blog
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'featured_image',
            'author', 'category', 'is_published', 'published_at',
            'meta_title', 'meta_description',
        ]
