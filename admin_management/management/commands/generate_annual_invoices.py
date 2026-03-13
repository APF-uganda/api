"""
Management command to generate annual membership renewal invoices
This should be run automatically on March 31st each year

Usage: python manage.py generate_annual_invoices [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from authentication.models import User
from admin_management.membership_renewal_service import MembershipRenewalService


class Command(BaseCommand):
    help = 'Generate annual membership renewal invoices for all active members (Run on March 31st)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate invoice generation without creating records or sending emails',
        )
        parser.add_argument(
            '--no-email',
            action='store_true',
            help='Create invoices but do not send emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        send_email = not options['no_email']
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('ANNUAL MEMBERSHIP RENEWAL INVOICE GENERATION'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No invoices will be created\n'))
        
        # Get current date
        today = timezone.now().date()
        self.stdout.write(f"Date: {today.strftime('%B %d, %Y')}")
        
        # Check if it's March 31st (or allow manual run)
        if today.month != 3 or today.day != 31:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  Warning: This command is designed to run on March 31st"
            ))
            self.stdout.write(self.style.WARNING(
                f"   Current date is {today.strftime('%B %d, %Y')}"
            ))
            response = input("\nContinue anyway? (yes/no): ")
            if response.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return
        
        # Get next membership year
        next_start_year, next_end_year = MembershipRenewalService.get_next_membership_year()
        renewal_period = f"April {next_start_year} - March {next_end_year}"
        
        self.stdout.write(f"Renewal Period: {renewal_period}")
        self.stdout.write(f"Invoice Amount: UGX {MembershipRenewalService.ANNUAL_SUBSCRIPTION_FEE:,}\n")
        
        # Get all active members
        members = MembershipRenewalService.get_all_active_members()
        total_members = members.count()
        
        self.stdout.write(f"Active Members: {total_members}\n")
        
        if total_members == 0:
            self.stdout.write(self.style.WARNING('No active members found.'))
            return
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS('Would generate invoices for:'))
            for member in members[:10]:  # Show first 10
                self.stdout.write(f"  • {member.email} - {member.full_name}")
            if total_members > 10:
                self.stdout.write(f"  ... and {total_members - 10} more")
            self.stdout.write(f"\nTotal: {total_members} invoices would be generated")
            return
        
        # Confirm before proceeding
        self.stdout.write(self.style.WARNING(
            f"\n⚠️  About to generate {total_members} invoices"
        ))
        if send_email:
            self.stdout.write(self.style.WARNING(
                f"   Emails will be sent to all members"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"   Invoices will be created but NO emails will be sent"
            ))
        
        response = input("\nProceed? (yes/no): ")
        if response.lower() != 'yes':
            self.stdout.write(self.style.ERROR('Aborted.'))
            return
        
        # Generate invoices
        self.stdout.write(self.style.SUCCESS('\n📝 Generating invoices...\n'))
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        failed_members = []
        
        for i, member in enumerate(members, 1):
            try:
                # Create invoice (with or without email)
                invoice, created, message = MembershipRenewalService.create_membership_invoice(
                    member,
                    send_email=send_email
                )
                
                if created:
                    if 'already exists' in message.lower():
                        skipped_count += 1
                        self.stdout.write(f"  [{i}/{total_members}] ⏭️  {member.email} - {message}")
                    else:
                        success_count += 1
                        status = "✅ Created" if not send_email else "✅ Created & Sent"
                        self.stdout.write(f"  [{i}/{total_members}] {status} - {member.email} - {invoice.invoice_number}")
                else:
                    failed_count += 1
                    failed_members.append({
                        'email': member.email,
                        'name': member.full_name,
                        'error': message
                    })
                    self.stdout.write(self.style.ERROR(
                        f"  [{i}/{total_members}] ❌ Failed - {member.email} - {message}"
                    ))
                    
            except Exception as e:
                failed_count += 1
                failed_members.append({
                    'email': member.email,
                    'name': member.full_name,
                    'error': str(e)
                })
                self.stdout.write(self.style.ERROR(
                    f"  [{i}/{total_members}] ❌ Error - {member.email} - {str(e)}"
                ))
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f"Total Members: {total_members}")
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully Generated: {success_count}"))
        
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f"⏭️  Skipped (Already Exists): {skipped_count}"))
        
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f"❌ Failed: {failed_count}"))
            
            if failed_members:
                self.stdout.write(self.style.ERROR('\nFailed Members:'))
                for failed in failed_members:
                    self.stdout.write(f"  • {failed['email']} - {failed['error']}")
        
        self.stdout.write(self.style.SUCCESS('\n✅ Invoice generation complete!'))
        
        # Next steps
        self.stdout.write(self.style.SUCCESS('\nNext Steps:'))
        self.stdout.write('1. Review generated invoices in admin panel')
        self.stdout.write('2. Monitor payment receipts')
        self.stdout.write('3. Follow up with members who haven\'t paid by due date')
