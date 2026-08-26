from django.urls import path

from .views import BannerFeedView

urlpatterns = [path('', BannerFeedView.as_view(), name='banner-feed')]
