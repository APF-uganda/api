from django.db import models

class Event(models.Model):
    title = models.CharField(max_length=255)
    date = models.DateTimeField()
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price_physical = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price_virtual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
   
    is_paid_event = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class EventRegistration(models.Model):
    ATTENDANCE_CHOICES = [('Physical', 'Physical'), ('Virtual', 'Virtual')]
    STATUS_CHOICES = [('Pending', 'Pending'), ('Verified', 'Verified'), ('Rejected', 'Rejected')]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    company_name = models.CharField(max_length=255, blank=True)
    attendance_mode = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES)
    
    # Proof of Payment
    proof_of_payment = models.ImageField(upload_to='event_proofs/%Y/%m/', null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # Internal Admin Notes
    admin_notes = models.TextField(blank=True, help_text="Reason for rejection or verification notes")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.event.title}"