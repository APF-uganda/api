from rest_framework import serializers


class TotalApplicationSerializer(serializers.Serializer):
    total_applications = serializers.IntegerField()

class TotalMemberSerializer(serializers.Serializer):
    total_members = serializers.IntegerField()

class TrendSerializer(serializers.Serializer):
    total_change = serializers.FloatField()
    pending_change = serializers.FloatField()
    approved_change = serializers.FloatField()
    rejected_change = serializers.FloatField()
    paid_change = serializers.FloatField()
    revenue_change = serializers.FloatField()

class ApplicationStatisticsSerializer(serializers.Serializer):
    total_applications = serializers.IntegerField()
    pending_applications = serializers.IntegerField()
    approved_applications = serializers.IntegerField()
    rejected_applications = serializers.IntegerField()
    paid_applications = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    trends = TrendSerializer()


