from django.db import models

class EventRegistration(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'), 
        ('Verified', 'Verified'), 
        ('Rejected', 'Rejected')
    ]
    
    # NEW: Identifiers from Strapi (No ForeignKey needed)
    strapi_event_id = models.CharField(max_length=100, help_text="The unique ID from Strapi")
    event_title = models.CharField(max_length=255, help_text="The Title of the event from Strapi")
    location = models.CharField(max_length=255, blank=True, null=True)
    
    # User Details (from your React form)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    event_date = models.CharField(max_length=100, blank=True, null=True)
    
    # Proof of Payment (For paid events)
    # Using ImageField or FileField is fine; ImageField is stricter for receipts.
    proof_of_payment = models.ImageField(upload_to='event_proofs/%Y/%m/', null=True, blank=True)
    
    # Admin Management
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_notes = models.TextField(blank=True, help_text="Reason for rejection or verification notes")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.event_title}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Event Registration"
        verbose_name = "Event Registrations"