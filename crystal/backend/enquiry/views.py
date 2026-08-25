from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .emails import send_enquiry_emails
from .serializers import EnquiryCreateSerializer


class EnquiryCreateView(APIView):
    """Receives an enquiry from the website.

    The emails are sent after the row is committed and their failure is never
    surfaced as an error: an enquiry that reached the database is a won lead,
    and telling the customer it failed because a mail server was down would
    lose it for no reason. What actually went out is reported in `emailed` so
    the caller can log it.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = EnquiryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        enquiry = serializer.save()
        sent = send_enquiry_emails(enquiry)

        return Response(
            {
                'ref': enquiry.ref_number,
                'message': 'Enquiry submitted successfully.',
                'emailed': sent,
            },
            status=status.HTTP_201_CREATED,
        )
