from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Blog
from .serializers import BlogListSerializer, BlogDetailSerializer


class BlogListView(generics.ListAPIView):
    serializer_class = BlogListSerializer

    def get_queryset(self):
        return Blog.objects.filter(is_published=True).select_related('category')


class BlogDetailView(APIView):
    def get(self, request, slug):
        blog = get_object_or_404(Blog.objects.select_related('category'), slug=slug, is_published=True)
        serializer = BlogDetailSerializer(blog, context={'request': request})
        return Response(serializer.data)
