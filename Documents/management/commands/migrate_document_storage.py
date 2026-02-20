"""
Migrate documents to organized folder structure.
This command moves existing files and updates database records.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from Documents.models import Document, MemberDocument
import os
import shutil


class Command(BaseCommand):
    help = 'Migrate documents to organized folder structure (app_id/user_id based)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Actually perform the migration (default is dry-run)',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip files that don\'t exist on disk',
        )

    def handle(self, *args, **options):
        execute = options['execute']
        skip_existing = options['skip_existing']
        
        if not execute:
            self.stdout.write(self.style.WARNING(
                '\n*** DRY RUN MODE - No changes will be made ***'
            ))
            self.stdout.write(self.style.WARNING(
                'Use --execute to actually migrate files\n'
            ))
        
        media_root = settings.MEDIA_ROOT
        
        # Migrate Application Documents
        self.stdout.write(self.style.SUCCESS('\n=== Migrating Application Documents ===\n'))
        app_stats = self.migrate_application_documents(media_root, execute, skip_existing)
        
        # Migrate Member Documents
        self.stdout.write(self.style.SUCCESS('\n=== Migrating Member Documents ===\n'))
        member_stats = self.migrate_member_documents(media_root, execute, skip_existing)
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write('='*60)
        self.stdout.write(f'Application Documents:')
        self.stdout.write(f'  - Migrated: {app_stats["migrated"]}')
        self.stdout.write(f'  - Already organized: {app_stats["already_organized"]}')
        self.stdout.write(f'  - Missing files: {app_stats["missing"]}')
        self.stdout.write(f'  - Errors: {app_stats["errors"]}')
        self.stdout.write(f'\nMember Documents:')
        self.stdout.write(f'  - Migrated: {member_stats["migrated"]}')
        self.stdout.write(f'  - Already organized: {member_stats["already_organized"]}')
        self.stdout.write(f'  - Missing files: {member_stats["missing"]}')
        self.stdout.write(f'  - Errors: {member_stats["errors"]}')

    def migrate_application_documents(self, media_root, execute, skip_existing):
        """Migrate application documents to app-specific folders"""
        documents = Document.objects.all()
        stats = {'migrated': 0, 'already_organized': 0, 'missing': 0, 'errors': 0}
        
        total = documents.count()
        self.stdout.write(f'Processing {total} application documents...\n')
        
        for idx, doc in enumerate(documents, 1):
            if idx % 10 == 0:
                self.stdout.write(f'Progress: {idx}/{total}')
            
            try:
                current_path = os.path.join(media_root, doc.file.name)
                
                # Check if already organized
                if '/app_' in doc.file.name:
                    stats['already_organized'] += 1
                    continue
                
                # Check if file exists
                if not os.path.exists(current_path):
                    if not skip_existing:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠ Doc {doc.id}: File missing - {doc.file.name}'
                        ))
                    stats['missing'] += 1
                    continue
                
                # Generate new path
                app_id = doc.application_id or 'unassigned'
                timestamp = doc.uploaded_at.strftime('%Y%m%d_%H%M%S')
                clean_filename = doc.file_name.replace(' ', '_').replace('(', '').replace(')', '')
                new_relative_path = os.path.join('application_documents', f'app_{app_id}', f'{timestamp}_{clean_filename}')
                new_path = os.path.join(media_root, new_relative_path)
                
                if execute:
                    # Create directory
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    
                    # Move file
                    shutil.move(current_path, new_path)
                    
                    # Update database
                    doc.file.name = new_relative_path
                    doc.save(update_fields=['file'])
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Doc {doc.id}: {os.path.basename(current_path)} → app_{app_id}/'
                    ))
                else:
                    self.stdout.write(
                        f'  → Doc {doc.id}: Would move to app_{app_id}/'
                    )
                
                stats['migrated'] += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Doc {doc.id}: {str(e)}'
                ))
                stats['errors'] += 1
        
        return stats

    def migrate_member_documents(self, media_root, execute, skip_existing):
        """Migrate member documents to user-specific folders"""
        documents = MemberDocument.objects.all()
        stats = {'migrated': 0, 'already_organized': 0, 'missing': 0, 'errors': 0}
        
        total = documents.count()
        if total == 0:
            self.stdout.write('No member documents to migrate.\n')
            return stats
        
        self.stdout.write(f'Processing {total} member documents...\n')
        
        for idx, doc in enumerate(documents, 1):
            try:
                current_path = os.path.join(media_root, doc.file.name)
                
                # Check if already organized
                if '/user_' in doc.file.name:
                    stats['already_organized'] += 1
                    continue
                
                # Check if file exists
                if not os.path.exists(current_path):
                    if not skip_existing:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠ Member Doc {doc.id}: File missing - {doc.file.name}'
                        ))
                    stats['missing'] += 1
                    continue
                
                # Generate new path
                user_id = doc.user_id or 'unassigned'
                timestamp = doc.uploaded_at.strftime('%Y%m%d_%H%M%S')
                clean_filename = doc.file_name.replace(' ', '_').replace('(', '').replace(')', '')
                new_relative_path = os.path.join('member_documents', f'user_{user_id}', f'{timestamp}_{clean_filename}')
                new_path = os.path.join(media_root, new_relative_path)
                
                if execute:
                    # Create directory
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    
                    # Move file
                    shutil.move(current_path, new_path)
                    
                    # Update database
                    doc.file.name = new_relative_path
                    doc.save(update_fields=['file'])
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Member Doc {doc.id}: {os.path.basename(current_path)} → user_{user_id}/'
                    ))
                else:
                    self.stdout.write(
                        f'  → Member Doc {doc.id}: Would move to user_{user_id}/'
                    )
                
                stats['migrated'] += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'  ✗ Member Doc {doc.id}: {str(e)}'
                ))
                stats['errors'] += 1
        
        return stats
