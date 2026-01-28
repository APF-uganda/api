from django.shortcuts import render
from  .services import get_total_applications
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import TotalApplicationSerializer

class TotalApplicationView(APIView):
    def get(self, request):
        data = {
            "total_applications": get_total_applications()
        }
        serializer = TotalApplicationSerializer(data)

        return Response(serializer.data)

# Create your views here.
