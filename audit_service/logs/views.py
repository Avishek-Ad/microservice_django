from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer
from rest_framework import serializers
from pymongo import DESCENDING
from .models import SystemLog

class ListLogAPIView(APIView):
    @extend_schema(
        summary="List system logs",
        description="Retrieve paginated system logs sorted by occurrence date in descending order.",
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number (default: 1)",
                default=1,
            ),
            OpenApiParameter(
                name="size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of logs per page (default: 2)",
                default=2,
            ),
        ],
        responses={
            200: inline_serializer(
                name="SystemLogListResponse",
                fields={
                    "results": serializers.ListField(
                        child=inline_serializer(
                            name="SystemLogDocument",
                            fields={
                                "_id": serializers.CharField(help_text="MongoDB Object ID string"),
                                "occured_at": serializers.DateTimeField(help_text="Timestamp of the log event"),
                                "event_type": serializers.CharField(required=False),
                                "message": serializers.CharField(required=False),
                                "level": serializers.CharField(required=False),
                            },
                        )
                    )
                },
            )
        },
    )
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
        
