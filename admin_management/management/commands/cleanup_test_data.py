"""
Management command to clean up test/dummy data while preserving production logic
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from admin_management.models import MembershipInvoice, InvoicePaymentLink
from payments.models import Payment
from authentication.models import User


class Command(BaseCommand):
    help = 'Remove test/dummy data while preserving all business logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of data',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']

        if not dry_run and not confirm:
            self.stdout.write(
                self.style.WARNING(
                    'This will delete test data. Use --dry-run to preview or --confirm to proceed.'
                )
            )
            return

        # Count items to be deleted
        invoice_links_count = InvoicePaymentLink.objects.count()
        invoices_count = MembershipInvoice.objects.count()
        # Get payments linked to invoices
        linked_payment_ids = InvoicePaymentLink.objects.values_list('payment_id', flat=True)
        payments_count = Payment.objects.filter(id__in=linked_payment_ids).count()

        self.stdout.write(self.style.WARNING('\n=== CLEANUP SUMMARY ==='))
        self.stdout.write(f'Invoice Payment Links: {invoice_links_count}')
        self.stdout.write(f'Membership Invoices: {invoices_count}')
        self.stdout.write(f'Linked Payments: {payments_count}')

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('\n[DRY RUN] No data was deleted.')
            )
            return

        # Confirm before proceeding
        self.stdout.write(
            self.style.WARNING(
                '\nThis will permanently delete the above records. '
                'All business logic and models will remain intact.'
            )
        )

        try:
            with transaction.atomic():
                # Get payment IDs before deleting links
                linked_payment_ids = list(
                    InvoicePaymentLink.objects.values_list('payment_id', flat=True)
                )
                
                # Delete in correct order to respect foreign keys
                deleted_links = InvoicePaymentLink.objects.all().delete()
                deleted_invoices = MembershipInvoice.objects.all().delete()
                deleted_payments = Payment.objects.filter(id__in=linked_payment_ids).delete()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Successfully deleted:'
                        f'\n  - {deleted_links[0]} invoice payment links'
                        f'\n  - {deleted_invoices[0]} membership invoices'
                        f'\n  - {deleted_payments[0]} linked payments'
                    )
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        '\n✓ All business logic, models, and functionality preserved!'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n✗ Error during cleanup: {str(e)}')
            )
            raise
