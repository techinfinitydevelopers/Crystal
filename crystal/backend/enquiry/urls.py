from django.urls import path
from .views import EnquiryCreateView, WebsiteMessageCreateView

urlpatterns = [
    path('', EnquiryCreateView.as_view(), name='enquiry-create'),
    path('message/', WebsiteMessageCreateView.as_view(), name='website-message-create'),
]
