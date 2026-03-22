from django.urls import path
from . import views


urlpatterns = [
    # Member management endpoints
    path('members/', views.AdminMemberListView.as_view(), name='admin-members-list'),
    path('members/export/', views.AdminMemberExportCSVView.as_view(), name='admin-members-export-csv'),
    path('members/<int:member_id>/suspend/', views.AdminMemberSuspendView.as_view(), name='admin-member-suspend'),
    path('members/<int:member_id>/reactivate/', views.AdminMemberReactivateView.as_view(), name='admin-member-reactivate'),
    
    # Admin notes endpoints
    path('members/<int:member_id>/notes/', views.AdminNoteListCreateView.as_view(), name='admin-member-notes'),
    path('notes/<int:note_id>/', views.AdminNoteDetailView.as_view(), name='admin-note-detail'),
    
    # Document management endpoints
    path('documents/pending/', views.AdminPendingDocumentsView.as_view(), name='admin-pending-documents'),
    path('documents/<int:document_id>/approve/', views.AdminApproveDocumentView.as_view(), name='admin-document-approve'),
    path('documents/<int:document_id>/reject/', views.AdminRejectDocumentView.as_view(), name='admin-document-reject'),
]