from django.urls import path

from .views import PageSectionFeedView

urlpatterns = [path('', PageSectionFeedView.as_view(), name='section-feed')]
