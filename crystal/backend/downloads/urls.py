from django.urls import path
from .views import DownloadListView

urlpatterns = [
    path('', DownloadListView.as_view(), name='download-list'),
]
