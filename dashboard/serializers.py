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


class MemberDashboardProfileSerializer(serializers.Serializer):
    display_name = serializers.CharField()
    membership_category = serializers.CharField()
    membership_status = serializers.CharField()
    member_since = serializers.DateField(allow_null=True)
    next_renewal_date = serializers.DateField(allow_null=True)


class MemberDashboardDocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    document_type = serializers.CharField(allow_blank=True)
    uploaded_at = serializers.DateTimeField()
    file_url = serializers.CharField(allow_blank=True, allow_null=True)


class MemberDashboardActivitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    action = serializers.CharField()
    field_changed = serializers.CharField(allow_blank=True)
    timestamp = serializers.DateTimeField()


class MemberDashboardNotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    message = serializers.CharField()
    type = serializers.CharField()
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    application_id = serializers.IntegerField(allow_null=True)


class MemberDashboardSerializer(serializers.Serializer):
    profile = MemberDashboardProfileSerializer()
    documents = MemberDashboardDocumentSerializer(many=True)
    recent_activity = MemberDashboardActivitySerializer(many=True)
    notifications = MemberDashboardNotificationSerializer(many=True)


