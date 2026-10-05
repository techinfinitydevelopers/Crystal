from django.urls import path
from .views import AwardFeedView

urlpatterns = [
    path('', AwardFeedView.as_view(), name='award-feed'),
]
