"""
Preview how documents would be reorganized
"""
from django.core.management.base import BaseCommand
from Documents.models import Document
import os


class Command(BaseCommand):
    help = 'Preview document reorganization'

    def handle(self, *args, **options):
        documents = Document.objects.all()[:10]  # Just first 10 for preview
        
        self.stdout.write(f'Previewing reorganization for {documents.count()} documents:\n')
        
        for doc in documents:
            app_id = doc.application_id if doc.application_id else 'unassigned'
            timestamp = doc.uploaded_at.strftime('%Y%m%d_%H%M%S')
            clean_filename = doc.file_name.replace(' ', '_').replace('(', '').replace(')', '')
            
            old_path = doc.file.name
            new_path = f'application_documents/app_{app_id}/{timestamp}_{clean_filename}'
            
            self.stdout.write(f'Doc {doc.id}:')
            self.stdout.write(f'  FROM: {old_path}')
            self.stdout.write(f'  TO:   {new_path}\n')
