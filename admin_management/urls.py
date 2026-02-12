from django.urls import path
from . import views


urlpatterns = [
    # Member management endpoints
    path('members/', views.AdminMemberListView.as_view(), name='admin-members-list'),
    path('members/<int:member_id>/suspend/', views.AdminMemberSuspendView.as_view(), name='admin-member-suspend'),
    path('members/<int:member_id>/reactivate/', views.AdminMemberReactivateView.as_view(), name='admin-member-reactivate'),
    
    # Document management endpoints
    path('documents/pending/', views.AdminPendingDocumentsView.as_view(), name='admin-pending-documents'),
    path('documents/<int:document_id>/approve/', views.AdminApproveDocumentView.as_view(), name='admin-document-approve'),
    path('documents/<int:document_id>/reject/', views.AdminRejectDocumentView.as_view(), name='admin-document-reject'),
]