from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from pymongo import DESCENDING
from .models import SystemLog

class ListLogAPIView(APIView):
    def get(self, request):
        page_number = max(1, int(request.query_params.get('page', '1')))
        page_size = max(1, int(request.query_params.get('size', '2')))
        
        offset = (page_number - 1) * page_size
        
        cursor = SystemLog.find().sort([('occured_at', DESCENDING)]).skip(offset).limit(page_size)
        
        logs_list = []
        for doc in cursor:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            logs_list.append(doc)
        
        return Response({'results': logs_list}, status=status.HTTP_200_OK)
        
        
        