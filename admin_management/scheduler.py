"""
Membership renewal scheduler.
Uses Python's built-in threading — no extra packages required.

Fires jobs automatically:
  - Daily        → Send renewal reminders (14d, 7d, 1d before due, weekly after)
  - March 1st    → 30-day reminder emails to all members
  - March 31st   → Generate invoices + send to all members

Uses a daily polling loop to avoid Windows threading overflow issues.
"""
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_scheduler_started = False

# Check every 24 hours
POLL_INTERVAL_SECONDS = 24 * 60 * 60


def _is_target_date(month: int, day: int) -> bool:
    now = datetime.now()
    return now.month == month and now.day == day


def _run_daily_renewal_reminders():
    """Run every day — sends reminders at 14d, 7d, 1d before due and weekly after."""
    try:
        logger.info("[Scheduler] Running daily renewal reminders")
        from django.core.management import call_command
        call_command("send_renewal_reminders")
        logger.info("[Scheduler] Daily renewal reminders done")
    except Exception as e:
        logger.error(f"[Scheduler] Daily renewal reminders failed: {e}")


def _run_send_reminders():
    try:
        logger.info("[Scheduler] Running March 1st renewal reminder job")
        from admin_management.membership_renewal_service import MembershipRenewalService
        members = MembershipRenewalService.get_all_active_members()
        results = MembershipRenewalService.send_bulk_renewal_invoices(members)
        logger.info(
            f"[Scheduler] Reminder job done — "
            f"sent: {results['success_count']}, failed: {results['failed_count']}"
        )
    except Exception as e:
        logger.error(f"[Scheduler] Reminder job failed: {e}")


def _run_generate_invoices():
    try:
        logger.info("[Scheduler] Running March 31st invoice generation job")
        from django.core.management import call_command
        call_command("generate_annual_invoices", force=True)
        logger.info("[Scheduler] Invoice generation job done")
    except Exception as e:
        logger.error(f"[Scheduler] Invoice generation job failed: {e}")


def _poll_loop():
    """
    Polls every 24 hours. Fires daily reminders every day, and
    annual jobs on their specific dates.
    """
    reminders_fired_year = None
    invoices_fired_year = None
    daily_reminder_fired_date = None

    while True:
        now = datetime.now()
        current_year = now.year
        today = now.date()

        # Daily — renewal reminders (upcoming: 14d/7d/1d; overdue: weekly)
        if daily_reminder_fired_date != today:
            daily_reminder_fired_date = today
            t = threading.Thread(target=_run_daily_renewal_reminders, daemon=True)
            t.start()

        # March 1st — bulk invoice reminder emails
        if _is_target_date(3, 1) and reminders_fired_year != current_year:
            reminders_fired_year = current_year
            t = threading.Thread(target=_run_send_reminders, daemon=True)
            t.start()

        # March 31st — generate invoices
        if _is_target_date(3, 31) and invoices_fired_year != current_year:
            invoices_fired_year = current_year
            t = threading.Thread(target=_run_generate_invoices, daemon=True)
            t.start()

        # Sleep 24 hours before checking again
        threading.Event().wait(POLL_INTERVAL_SECONDS)


def start():
    """Start the scheduler poll loop. Safe to call multiple times — only starts once."""
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True
    logger.info("[Scheduler] Starting membership renewal scheduler (polling every 24 hours)")
    t = threading.Thread(target=_poll_loop, daemon=True, name="renewal-scheduler")
    t.start()
