"""
Management command to check payment metrics and alerts.
"""
from django.core.management.base import BaseCommand
from payments.services.metrics_service import PaymentMetricsService
from payments.services.alert_service import AlertService
import json


class Command(BaseCommand):
    help = 'Check payment metrics and alerts'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Time window in hours (default: 24)'
        )
        parser.add_argument(
            '--provider',
            type=str,
            choices=['mtn', 'airtel', 'all'],
            default='all',
            help='Provider to check (default: all)'
        )
        parser.add_argument(
            '--check-alerts',
            action='store_true',
            help='Check for active alerts'
        )
    
    def handle(self, *args, **options):
        hours = options['hours']
        provider = options['provider'] if options['provider'] != 'all' else None
        check_alerts = options['check_alerts']
        
        metrics_service = PaymentMetricsService()
        alert_service = AlertService()
        
        self.stdout.write(self.style.SUCCESS(f'\n=== Payment Metrics (Last {hours} hours) ===\n'))
        
        if provider:
            self.stdout.write(self.style.WARNING(f'Provider: {provider.upper()}\n'))
        else:
            self.stdout.write(self.style.WARNING('Provider: ALL\n'))
        
        # Get all metrics
        metrics = metrics_service.get_all_metrics(provider=provider, hours=hours)
        
        # Display success rate
        success_rate = metrics['success_rate']
        self.stdout.write(f"Success Rate:")
        self.stdout.write(f"  Total Payments: {success_rate['total_payments']}")
        self.stdout.write(f"  Successful: {success_rate['successful_payments']}")
        self.stdout.write(f"  Rate: {success_rate['success_rate']}%")
        
        if success_rate['success_rate'] < 90:
            self.stdout.write(self.style.ERROR(f"  ⚠️  WARNING: Success rate below 90% threshold!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Success rate healthy"))
        
        self.stdout.write('')
        
        # Display average completion time
        completion_time = metrics['average_completion_time']
        self.stdout.write(f"Average Completion Time:")
        self.stdout.write(f"  Completed Payments: {completion_time['completed_payments']}")
        self.stdout.write(f"  Average: {completion_time['average_seconds']} seconds")
        
        if completion_time['average_seconds'] > 30:
            self.stdout.write(self.style.WARNING(f"  ⚠️  Completion time above 30 seconds"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Completion time healthy"))
        
        self.stdout.write('')
        
        # Display timeout rate
        timeout_rate = metrics['timeout_rate']
        self.stdout.write(f"Timeout Rate:")
        self.stdout.write(f"  Total Payments: {timeout_rate['total_payments']}")
        self.stdout.write(f"  Timeouts: {timeout_rate['timeout_payments']}")
        self.stdout.write(f"  Rate: {timeout_rate['timeout_rate']}%")
        
        if timeout_rate['timeout_rate'] > 10:
            self.stdout.write(self.style.ERROR(f"  ⚠️  WARNING: Timeout rate above 10%!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Timeout rate healthy"))
        
        self.stdout.write('')
        
        # Display retry rate
        retry_rate = metrics['retry_rate']
        self.stdout.write(f"Retry Rate:")
        self.stdout.write(f"  Failed/Timeout Payments: {retry_rate['failed_or_timeout_payments']}")
        self.stdout.write(f"  Retried: {retry_rate['retried_payments']}")
        self.stdout.write(f"  Rate: {retry_rate['retry_rate']}%")
        self.stdout.write(self.style.SUCCESS(f"  ✓ Retry metrics"))
        
        self.stdout.write('')
        
        # Check alerts if requested
        if check_alerts:
            self.stdout.write(self.style.SUCCESS(f'\n=== Active Alerts ===\n'))
            
            alert_status = alert_service.get_alert_status()
            active_alerts = alert_status['active_alerts']
            
            if active_alerts:
                self.stdout.write(self.style.ERROR(f"Found {len(active_alerts)} active alert(s):\n"))
                
                for alert in active_alerts:
                    severity_style = self.style.ERROR if alert['severity'] == 'critical' else self.style.WARNING
                    self.stdout.write(severity_style(f"[{alert['severity'].upper()}] {alert['type']}"))
                    self.stdout.write(f"  {alert['message']}")
                    self.stdout.write('')
            else:
                self.stdout.write(self.style.SUCCESS("✓ No active alerts"))
        
        # Display by provider if checking all
        if not provider:
            self.stdout.write(self.style.SUCCESS(f'\n=== Success Rate by Provider ===\n'))
            
            by_provider = metrics_service.get_success_rate_by_provider(hours=hours)
            
            self.stdout.write(f"MTN:")
            self.stdout.write(f"  Total: {by_provider['mtn']['total']}")
            self.stdout.write(f"  Successful: {by_provider['mtn']['successful']}")
            self.stdout.write(f"  Rate: {by_provider['mtn']['rate']}%")
            self.stdout.write('')
            
            self.stdout.write(f"Airtel:")
            self.stdout.write(f"  Total: {by_provider['airtel']['total']}")
            self.stdout.write(f"  Successful: {by_provider['airtel']['successful']}")
            self.stdout.write(f"  Rate: {by_provider['airtel']['rate']}%")
            self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('\n=== Metrics Check Complete ===\n'))
