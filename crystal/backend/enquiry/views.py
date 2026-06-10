from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import EnquiryCreateSerializer


class EnquiryCreateView(APIView):
    def post(self, request):
        serializer = EnquiryCreateSerializer(data=request.data)
        if serializer.is_valid():
            enquiry = serializer.save()
            return Response({'ref': enquiry.ref_number, 'message': 'Enquiry submitted successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
