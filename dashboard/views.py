from django.shortcuts import render
from  .services import get_total_applications,get_total_members
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import TotalApplicationSerializer, TotalMemberSerializer
from authentication.permissions import IsAuthenticated, IsAdmin

from rest_framework.permissions import AllowAny

class TotalApplicationView(APIView):
    # permission_classes = [IsAuthenticated, IsAdmin]
    permission_classes = [AllowAny]
    def get(self, request):
        data = {
            "total_applications": get_total_applications()
        }
        serializer = TotalApplicationSerializer(data)

        return Response(serializer.data)

class TotalMemberView(APIView):
    #  permission_classes = [IsAuthenticated, IsAdmin]
     permission_classes = [AllowAny]

     def get(self, request):
         data ={
             "total_members": get_total_members()
         }
         serializer = TotalMemberSerializer(data)

         return Response(serializer.data)


