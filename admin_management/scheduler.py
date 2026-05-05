"""
Membership renewal scheduler.
Uses Python's built-in threading — no extra packages required.

Fires jobs automatically:
  - Monday & Thursday → Fetch ICPAU news from RSS feed
  - March 1st         → 30-day reminder emails to all members
  - March 31st        → Generate invoices + send to all members

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


def _is_target_weekday(weekday: int) -> bool:
    """Check if today is a specific weekday (0=Monday, 6=Sunday)"""
    now = datetime.now()
    return now.weekday() == weekday


def _run_news_fetch():
    """Fetch ICPAU news from RSS feed"""
    try:
        logger.info("[Scheduler] Running ICPAU news fetch")
        from django.core.management import call_command
        call_command("newsfetch")
        logger.info("[Scheduler] ICPAU news fetch completed")
    except Exception as e:
        logger.error(f"[Scheduler] ICPAU news fetch failed: {e}")


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
    Polls every 24 hours. Fires scheduled jobs on their specific dates/days.
    """
    reminders_fired_year = None
    invoices_fired_year = None
    news_fetch_fired_date = None

    while True:
        now = datetime.now()
        current_year = now.year
        today = now.date()

        # Monday (0) and Thursday (3) — Fetch ICPAU news
        if ((_is_target_weekday(0) or _is_target_weekday(3)) and 
            news_fetch_fired_date != today):
            news_fetch_fired_date = today
            t = threading.Thread(target=_run_news_fetch, daemon=True)
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
