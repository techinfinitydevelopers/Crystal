from rest_framework import generics
from .models import Download
from .serializers import DownloadSerializer


class DownloadListView(generics.ListAPIView):
    serializer_class = DownloadSerializer

    def get_queryset(self):
        qs = Download.objects.filter(is_active=True).select_related('brand')
        brand = self.request.query_params.get('brand')
        category = self.request.query_params.get('category')
        if brand:
            qs = qs.filter(brand__slug=brand)
        if category:
            qs = qs.filter(category=category)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
