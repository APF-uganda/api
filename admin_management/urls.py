from django.urls import path
from . import views


urlpatterns = [
    # Member management endpoints
    path('members/', views.AdminMemberListView.as_view(), name='admin-members-list'),
    path('members/bulk-register/', views.BulkMemberRegistrationView.as_view(), name='admin-members-bulk-register'),
    path('members/export/', views.AdminMemberExportCSVView.as_view(), name='admin-members-export-csv'),
    path('members/<int:member_id>/suspend/', views.AdminMemberSuspendView.as_view(), name='admin-member-suspend'),
    path('members/<int:member_id>/reactivate/', views.AdminMemberReactivateView.as_view(), name='admin-member-reactivate'),
    path('members/<int:member_id>/reset-password/', views.AdminResetMemberPasswordView.as_view(), name='admin-member-reset-password'),
    path('members/<int:member_id>/apf-number/', views.AdminAssignApfNumberView.as_view(), name='admin-member-apf-number'),
    path('members/<int:member_id>/delete/', views.AdminDeleteMemberView.as_view(), name='admin-member-delete'),

    # Application delete endpoint
    path('applications/<int:application_id>/delete/', views.AdminDeleteApplicationView.as_view(), name='admin-application-delete'),

    # Payment delete endpoint
    path('payments/<int:payment_id>/delete/', views.AdminDeletePaymentView.as_view(), name='admin-payment-delete'),
    
    # Admin notes endpoints
    path('members/<int:member_id>/notes/', views.AdminNoteListCreateView.as_view(), name='admin-member-notes'),
    path('notes/<int:note_id>/', views.AdminNoteDetailView.as_view(), name='admin-note-detail'),
    
    # Document management endpoints
    path('documents/pending/', views.AdminPendingDocumentsView.as_view(), name='admin-pending-documents'),
    path('documents/<int:document_id>/approve/', views.AdminApproveDocumentView.as_view(), name='admin-document-approve'),
    path('documents/<int:document_id>/reject/', views.AdminRejectDocumentView.as_view(), name='admin-document-reject'),
]