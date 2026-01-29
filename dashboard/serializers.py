from rest_framework import serializers


class TotalApplicationSerializer(serializers.Serializer):
    total_applications = serializers.IntegerField()

class TotalMemberSerializer(serializers.Serializer):
    total_members = serializers.IntegerField()


