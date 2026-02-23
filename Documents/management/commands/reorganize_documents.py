"""
Management command to reorganize existing documents into the new folder structure.
Moves files from flat structure to organized folders by application/user ID.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from Documents.models import Document, MemberDocument
import os
import shutil


class Command(BaseCommand):
    help = 'Reorganize existing documents into application/user-specific folders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be moved without making changes',
        )
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually move the files and update database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        execute = options['execute']
        
        if not dry_run and not execute:
            self.stdout.write(self.style.WARNING(
                'Please specify either --dry-run to preview or --execute to reorganize files'
            ))
            return

        media_root = settings.MEDIA_ROOT
        
        # Process Application Documents
        self.stdout.write(self.style.SUCCESS('\n=== Processing Application Documents ==='))
        self.reorganize_application_documents(media_root, execute)
        
        # Process Member Documents
        self.stdout.write(self.style.SUCCESS('\n=== Processing Member Documents ==='))
        self.reorganize_member_documents(media_root, execute)

    def reorganize_application_documents(self, media_root, execute):
        """Reorganize application documents into app-specific folders"""
        documents = Document.objects.all()
        moved_count = 0
        error_count = 0
        
        for doc in documents:
            try:
                # Get current file path
                current_path = os.path.join(media_root, doc.file.name)
                
                # Check if file exists
                if not os.path.exists(current_path):
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ Doc {doc.id}: File not found - {doc.file.name}'
                    ))
                    continue
                
                # Check if already in organized structure
                if doc.file.name.startswith(f'application_documents/app_{doc.application_id}/'):
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Doc {doc.id}: Already organized'
                    ))
                    continue
                
                # Generate new path
                app_id = doc.application_id if doc.application_id else 'unassigned'
                timestamp = doc.uploaded_at.strftime('%Y%m%d_%H%M%S')
                clean_filename = doc.file_name.replace(' ', '_').replace('(', '').replace(')', '')
                new_relative_path = f'application_documents/app_{app_id}/{timestamp}_{clean_filename}'
                new_path = os.path.join(media_root, new_relative_path)
                
                # Create directory if it doesn't exist
                new_dir = os.path.dirname(new_path)
                
                if execute:
                    os.makedirs(new_dir, exist_ok=True)
                    
                    # Move the file
                    shutil.move(current_path, new_path)
                    
                    # Update database
                    doc.file.name = new_relative_path
                    doc.save(update_fields=['file'])
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Doc {doc.id}: Moved to {new_relative_path}'
                    ))
                    moved_count += 1
                else:
                    self.stdout.write(
                        f'  → Doc {doc.id}: Would move to {new_relative_path}'
                    )
                    moved_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Doc {doc.id}: Error - {str(e)}'
                ))
                error_count += 1
        
        self.stdout.write('\n' + '='*60)
        if execute:
            self.stdout.write(self.style.SUCCESS(
                f'Moved {moved_count} application documents'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'Would move {moved_count} application documents'
            ))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(
                f'{error_count} errors occurred'
            ))

    def reorganize_member_documents(self, media_root, execute):
        """Reorganize member documents into user-specific folders"""
        documents = MemberDocument.objects.all()
        moved_count = 0
        error_count = 0
        
        for doc in documents:
            try:
                # Get current file path
                current_path = os.path.join(media_root, doc.file.name)
                
                # Check if file exists
                if not os.path.exists(current_path):
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠ Member Doc {doc.id}: File not found - {doc.file.name}'
                    ))
                    continue
                
                # Check if already in organized structure
                if doc.file.name.startswith(f'member_documents/user_{doc.user_id}/'):
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Member Doc {doc.id}: Already organized'
                    ))
                    continue
                
                # Generate new path
                user_id = doc.user_id if doc.user_id else 'unassigned'
                timestamp = doc.uploaded_at.strftime('%Y%m%d_%H%M%S')
                clean_filename = doc.file_name.replace(' ', '_').replace('(', '').replace(')', '')
                new_relative_path = f'member_documents/user_{user_id}/{timestamp}_{clean_filename}'
                new_path = os.path.join(media_root, new_relative_path)
                
                # Create directory if it doesn't exist
                new_dir = os.path.dirname(new_path)
                
                if execute:
                    os.makedirs(new_dir, exist_ok=True)
                    
                    # Move the file
                    shutil.move(current_path, new_path)
                    
                    # Update database
                    doc.file.name = new_relative_path
                    doc.save(update_fields=['file'])
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Member Doc {doc.id}: Moved to {new_relative_path}'
                    ))
                    moved_count += 1
                else:
                    self.stdout.write(
                        f'  → Member Doc {doc.id}: Would move to {new_relative_path}'
                    )
                    moved_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Member Doc {doc.id}: Error - {str(e)}'
                ))
                error_count += 1
        
        self.stdout.write('\n' + '='*60)
        if execute:
            self.stdout.write(self.style.SUCCESS(
                f'Moved {moved_count} member documents'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'Would move {moved_count} member documents'
            ))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(
                f'{error_count} errors occurred'
            ))
