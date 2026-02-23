"""
Management command to sync document file paths in database with actual files on disk.
This fixes the issue where database has old/incorrect file paths.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from Documents.models import Document
import os


class Command(BaseCommand):
    help = 'Sync document file paths in database with actual files on disk'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually fix the file paths in the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        fix = options['fix']
        
        if not dry_run and not fix:
            self.stdout.write(self.style.WARNING(
                'Please specify either --dry-run to preview changes or --fix to apply them'
            ))
            return

        media_root = settings.MEDIA_ROOT
        doc_dir = os.path.join(media_root, 'application_documents')
        
        if not os.path.exists(doc_dir):
            self.stdout.write(self.style.ERROR(f'Directory not found: {doc_dir}'))
            return
        
        # Get all files on disk
        disk_files = set(os.listdir(doc_dir))
        self.stdout.write(f'Found {len(disk_files)} files on disk')
        
        # Get all documents from database
        documents = Document.objects.all()
        self.stdout.write(f'Found {documents.count()} documents in database\n')
        
        fixed_count = 0
        missing_count = 0
        
        for doc in documents:
            # Get the filename from the file field
            current_path = doc.file.name  # e.g., 'application_documents/file.pdf'
            current_filename = os.path.basename(current_path)
            
            # Check if file exists
            if current_filename in disk_files:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Doc {doc.id}: {current_filename} - OK'
                ))
                continue
            
            # File doesn't exist - try to find a match
            self.stdout.write(self.style.WARNING(
                f'✗ Doc {doc.id}: {current_filename} - NOT FOUND'
            ))
            
            # Try to find similar files using multiple strategies
            base_name = doc.file_name.rsplit('.', 1)[0] if '.' in doc.file_name else doc.file_name
            extension = doc.file_name.rsplit('.', 1)[1] if '.' in doc.file_name else ''
            
            # Strategy 1: Exact match on file_name (ignoring Django's random suffix)
            # Remove spaces and special chars for comparison
            normalized_base = base_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
            
            matches = []
            for f in disk_files:
                f_base = f.rsplit('.', 1)[0] if '.' in f else f
                f_ext = f.rsplit('.', 1)[1] if '.' in f else ''
                f_normalized = f_base.lower().replace(' ', '_').replace('(', '').replace(')', '')
                
                # Check if extensions match
                if extension and f_ext.lower() != extension.lower():
                    continue
                
                # Check if the normalized base name matches (with or without Django suffix)
                # Django adds suffixes like _abc123 or _ABC1234
                if f_normalized == normalized_base:
                    matches.append(f)
                elif f_normalized.startswith(normalized_base + '_'):
                    # Check if what follows is a Django-style suffix (alphanumeric)
                    suffix = f_normalized[len(normalized_base)+1:]
                    if len(suffix) <= 10 and suffix.replace('_', '').isalnum():
                        matches.append(f)
                elif normalized_base.startswith(f_normalized):
                    # The file on disk might be the original without suffix
                    matches.append(f)
            
            if matches:
                # Use the first match (or most recent if multiple)
                matched_file = sorted(matches)[-1]  # Get the last one alphabetically (likely most recent)
                new_path = f'application_documents/{matched_file}'
                
                self.stdout.write(self.style.WARNING(
                    f'  → Found potential match: {matched_file}'
                ))
                
                if fix:
                    doc.file.name = new_path
                    doc.save(update_fields=['file'])
                    self.stdout.write(self.style.SUCCESS(
                        f'  → FIXED: Updated to {new_path}'
                    ))
                    fixed_count += 1
                else:
                    self.stdout.write(f'  → Would update to: {new_path}')
            else:
                self.stdout.write(self.style.ERROR(
                    f'  → No match found for {doc.file_name}'
                ))
                missing_count += 1
        
        self.stdout.write('\n' + '='*60)
        if fix:
            self.stdout.write(self.style.SUCCESS(
                f'Fixed {fixed_count} documents'
            ))
            if missing_count > 0:
                self.stdout.write(self.style.ERROR(
                    f'{missing_count} documents still have missing files'
                ))
        else:
            self.stdout.write(self.style.WARNING(
                f'Would fix {fixed_count} documents (use --fix to apply)'
            ))
            if missing_count > 0:
                self.stdout.write(self.style.WARNING(
                    f'{missing_count} documents have no matching files on disk'
                ))
