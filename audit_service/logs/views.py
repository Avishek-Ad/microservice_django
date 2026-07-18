from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import SystemLog

class ListLogAPIView(APIView):
    def get(self, request):
        page_number = int(request.query_params.get('page', '1'))
        page_size = int(request.query_params.get('size', '2'))
        
        offset = (page_number - 1) * page_size
        
        results = SystemLog.find().skip(offset).limit(page_size)
        
        return Response({'results': results}, status=status.HTTP_200_OK)
        
        
        