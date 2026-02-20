"""
Management command to clean up orphaned document records (documents in DB with no file on disk).
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from Documents.models import Document
import os


class Command(BaseCommand):
    help = 'Clean up orphaned document records (documents in DB with no file on disk)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without making changes',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Actually delete the orphaned document records',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete = options['delete']
        
        if not dry_run and not delete:
            self.stdout.write(self.style.WARNING(
                'Please specify either --dry-run to preview or --delete to remove orphaned records'
            ))
            return

        media_root = settings.MEDIA_ROOT
        
        # Get all documents from database
        documents = Document.objects.all()
        self.stdout.write(f'Checking {documents.count()} documents...\n')
        
        orphaned = []
        
        for doc in documents:
            # Get the full file path
            file_path = os.path.join(media_root, doc.file.name)
            
            # Check if file exists
            if not os.path.exists(file_path):
                orphaned.append(doc)
                app_id = doc.application_id if doc.application_id else 'N/A'
                self.stdout.write(self.style.WARNING(
                    f'✗ Doc {doc.id} (App {app_id}): {doc.file_name} - FILE MISSING'
                ))
        
        if not orphaned:
            self.stdout.write(self.style.SUCCESS('\n✓ No orphaned documents found!'))
            return
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING(
            f'Found {len(orphaned)} orphaned document(s)'
        ))
        
        if delete:
            self.stdout.write('\nDeleting orphaned documents...')
            for doc in orphaned:
                app_id = doc.application_id if doc.application_id else 'N/A'
                self.stdout.write(f'  Deleting Doc {doc.id} (App {app_id}): {doc.file_name}')
                doc.delete()
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Deleted {len(orphaned)} orphaned document record(s)'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'\nWould delete {len(orphaned)} orphaned document record(s) (use --delete to apply)'
            ))
