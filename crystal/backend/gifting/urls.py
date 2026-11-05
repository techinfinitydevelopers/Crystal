from django.urls import path

from .views import GiftingFeedView

urlpatterns = [path('', GiftingFeedView.as_view(), name='gifting-feed')]
