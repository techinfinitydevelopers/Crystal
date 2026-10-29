from django.urls import path

from .views import ThemeFeedView

urlpatterns = [path('', ThemeFeedView.as_view(), name='theme-feed')]
