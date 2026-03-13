"""
Admin configuration for membership management
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import MembershipInvoice, InvoicePaymentLink


@admin.register(MembershipInvoice)
class MembershipInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number',
        'user_email',
        'membership_period',
        'total_amount_display',
        'amount_paid_display',
        'balance_due_display',
        'status_badge',
        'email_sent_badge',
        'invoice_date',
    ]
    
    list_filter = [
        'status',
        'email_sent',
        'invoice_date',
        'period_start',
    ]
    
    search_fields = [
        'invoice_number',
        'user__email',
        'user__full_name',
        'user__icpau_registration_number',
    ]
    
    readonly_fields = [
        'invoice_number',
        'balance_due',
        'created_at',
        'updated_at',
        'paid_at',
        'email_sent_at',
        'payment_percentage',
        'view_payments',
    ]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'user', 'status')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date', 'period_start', 'period_end')
        }),
        ('Financial Details', {
            'fields': (
                'base_amount',
                'previous_balance',
                'discount',
                'total_amount',
                'amount_paid',
                'balance_due',
                'payment_percentage',
            )
        }),
        ('Email Status', {
            'fields': ('email_sent', 'email_sent_at')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        }),
        ('Related', {
            'fields': ('view_payments',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Member Email'
    user_email.admin_order_field = 'user__email'
    
    def membership_period(self, obj):
        return f"{obj.period_start.strftime('%b %Y')} - {obj.period_end.strftime('%b %Y')}"
    membership_period.short_description = 'Period'
    
    def total_amount_display(self, obj):
        return f"UGX {obj.total_amount:,.0f}"
    total_amount_display.short_description = 'Total'
    total_amount_display.admin_order_field = 'total_amount'
    
    def amount_paid_display(self, obj):
        if obj.amount_paid > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">UGX {}</span>',
                f"{obj.amount_paid:,.0f}"
            )
        return format_html("UGX {}", f"{obj.amount_paid:,.0f}")
    amount_paid_display.short_description = 'Paid'
    amount_paid_display.admin_order_field = 'amount_paid'
    
    def balance_due_display(self, obj):
        if obj.balance_due > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">UGX {}</span>',
                f"{obj.balance_due:,.0f}"
            )
        return format_html("UGX {}", f"{obj.balance_due:,.0f}")
    balance_due_display.short_description = 'Balance'
    balance_due_display.admin_order_field = 'balance_due'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'partial': '#17a2b8',
            'paid': '#28a745',
            'overdue': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def email_sent_badge(self, obj):
        if obj.email_sent:
            return format_html(
                '<span style="color: green;">✓ Sent</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Not Sent</span>'
        )
    email_sent_badge.short_description = 'Email'
    email_sent_badge.admin_order_field = 'email_sent'
    
    def payment_percentage(self, obj):
        percentage = obj.get_payment_percentage()
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: #28a745; color: white; text-align: center; border-radius: 3px; padding: 2px;">{:.0f}%</div>'
            '</div>',
            percentage,
            percentage
        )
    payment_percentage.short_description = 'Payment Progress'
    
    def view_payments(self, obj):
        if obj.pk:
            payment_links = obj.payment_links.all()
            if payment_links:
                html = '<ul style="margin: 0; padding-left: 20px;">'
                for link in payment_links:
                    payment_url = reverse('admin:payments_payment_change', args=[link.payment.pk])
                    html += f'<li><a href="{payment_url}">{link.payment.transaction_reference}</a> - UGX {link.amount:,.0f}</li>'
                html += '</ul>'
                return mark_safe(html)
            return "No payments yet"
        return "Save invoice first"
    view_payments.short_description = 'Linked Payments'
    
    actions = ['mark_as_paid', 'mark_as_cancelled', 'resend_invoice_email']
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='paid')
        self.message_user(request, f'{updated} invoice(s) marked as paid.')
    mark_as_paid.short_description = 'Mark selected invoices as paid'
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} invoice(s) marked as cancelled.')
    mark_as_cancelled.short_description = 'Mark selected invoices as cancelled'
    
    def resend_invoice_email(self, request, queryset):
        from admin_management.membership_renewal_service import MembershipRenewalService
        
        success_count = 0
        for invoice in queryset:
            success, message = MembershipRenewalService.send_renewal_invoice_email(
                invoice.user,
                invoice=invoice
            )
            if success:
                success_count += 1
                invoice.email_sent = True
                invoice.email_sent_at = timezone.now()
                invoice.save()
        
        self.message_user(request, f'{success_count} invoice email(s) sent successfully.')
    resend_invoice_email.short_description = 'Resend invoice emails'


@admin.register(InvoicePaymentLink)
class InvoicePaymentLinkAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number',
        'payment_reference',
        'amount_display',
        'created_at',
    ]
    
    list_filter = [
        'created_at',
    ]
    
    search_fields = [
        'invoice__invoice_number',
        'payment__transaction_reference',
    ]
    
    readonly_fields = [
        'invoice',
        'payment',
        'amount',
        'created_at',
    ]
    
    def invoice_number(self, obj):
        return obj.invoice.invoice_number
    invoice_number.short_description = 'Invoice'
    invoice_number.admin_order_field = 'invoice__invoice_number'
    
    def payment_reference(self, obj):
        return obj.payment.transaction_reference
    payment_reference.short_description = 'Payment Reference'
    payment_reference.admin_order_field = 'payment__transaction_reference'
    
    def amount_display(self, obj):
        return f"UGX {obj.amount:,.0f}"
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
