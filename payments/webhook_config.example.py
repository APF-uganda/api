"""
Example configuration for webhook-first with polling fallback.
Copy relevant settings to your Django settings.py file.
"""

# ============================================================================
# PAYMENT WEBHOOK & POLLING CONFIGURATION
# ============================================================================

# Webhook timeout before falling back to polling (seconds)
# If webhook not received within this time, polling starts
PAYMENT_WEBHOOK_TIMEOUT = 60

# Polling interval when webhook not received (seconds)
# Time to wait between each polling attempt
PAYMENT_POLLING_INTERVAL = 10

# Maximum number of polling attempts before giving up
# Total polling time = POLLING_INTERVAL * MAX_POLLING_ATTEMPTS
PAYMENT_MAX_POLLING_ATTEMPTS = 9

# Total timeout for payment verification (seconds)
# After this time, payment marked as timeout regardless of status
PAYMENT_TOTAL_TIMEOUT = 90

# ============================================================================
# WEBHOOK SECURITY
# ============================================================================

# MTN Mobile Money webhook secret for HMAC-SHA256 signature verification
# Get this from MTN Developer Portal when configuring webhooks
MTN_WEBHOOK_SECRET = 'your-mtn-webhook-secret-here'

# Airtel Money webhook secret for HMAC-SHA256 signature verification
# Get this from Airtel Developer Portal when configuring webhooks
AIRTEL_WEBHOOK_SECRET = 'your-airtel-webhook-secret-here'

# ============================================================================
# CELERY CONFIGURATION (if using Celery for background polling)
# ============================================================================

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'poll-pending-payments': {
        'task': 'payments.tasks.poll_pending_payments',
        'schedule': 15.0,  # Run every 15 seconds
        'options': {
            'expires': 10.0,  # Task expires after 10 seconds if not picked up
        }
    },
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/payments.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'payments': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'payments.services.webhook_service': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',  # More verbose for webhook debugging
            'propagate': False,
        },
    },
}

# ============================================================================
# EXAMPLE ENVIRONMENT VARIABLES (.env file)
# ============================================================================

"""
# Payment Configuration
PAYMENT_WEBHOOK_TIMEOUT=60
PAYMENT_POLLING_INTERVAL=10
PAYMENT_MAX_POLLING_ATTEMPTS=9
PAYMENT_TOTAL_TIMEOUT=90

# Webhook Security
MTN_WEBHOOK_SECRET=your_secret_here
AIRTEL_WEBHOOK_SECRET=your_secret_here

# MTN API Configuration (existing)
MTN_BASE_URL=https://sandbox.momodeveloper.mtn.com
MTN_SUBSCRIPTION_KEY=your_subscription_key
MTN_API_USER=your_api_user_uuid
MTN_API_KEY=your_api_key
MTN_TARGET_ENVIRONMENT=sandbox

# Airtel API Configuration (existing)
AIRTEL_BASE_URL=https://openapiuat.airtel.africa
AIRTEL_CLIENT_ID=your_client_id
AIRTEL_CLIENT_SECRET=your_client_secret
AIRTEL_GRANT_TYPE=client_credentials
"""

# ============================================================================
# RECOMMENDED SETTINGS BY ENVIRONMENT
# ============================================================================

# Development / Sandbox
DEVELOPMENT_CONFIG = {
    'PAYMENT_WEBHOOK_TIMEOUT': 60,
    'PAYMENT_POLLING_INTERVAL': 15,
    'PAYMENT_MAX_POLLING_ATTEMPTS': 6,
    'PAYMENT_TOTAL_TIMEOUT': 90,
}

# Production - High Volume
PRODUCTION_HIGH_VOLUME_CONFIG = {
    'PAYMENT_WEBHOOK_TIMEOUT': 45,      # Shorter wait for webhook
    'PAYMENT_POLLING_INTERVAL': 8,      # Faster polling
    'PAYMENT_MAX_POLLING_ATTEMPTS': 10, # More attempts
    'PAYMENT_TOTAL_TIMEOUT': 120,       # Longer total timeout
}

# Production - Low Volume
PRODUCTION_LOW_VOLUME_CONFIG = {
    'PAYMENT_WEBHOOK_TIMEOUT': 60,
    'PAYMENT_POLLING_INTERVAL': 12,
    'PAYMENT_MAX_POLLING_ATTEMPTS': 7,
    'PAYMENT_TOTAL_TIMEOUT': 90,
}

# ============================================================================
# WEBHOOK URL CONFIGURATION
# ============================================================================

"""
Configure these URLs in your payment provider portals:

MTN Mobile Money:
- Webhook URL: https://yourdomain.com/api/v1/payments/webhooks/mtn/
- Method: POST
- Headers: X-Signature (HMAC-SHA256)

Airtel Money:
- Webhook URL: https://yourdomain.com/api/v1/payments/webhooks/airtel/
- Method: POST
- Headers: X-Signature (HMAC-SHA256)

Requirements:
- Must be HTTPS (not HTTP)
- Must be publicly accessible
- Must return 200 OK for successful processing
- Must handle idempotent requests (same webhook sent multiple times)
"""
