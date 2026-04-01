"""
Membership renewal scheduler.
Uses Python's built-in threading — no extra packages required.

Fires two jobs automatically each year:
  - March 1st  → 30-day reminder emails to all members
  - March 31st → Generate invoices + send to all members
"""
import threading
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_scheduler_started = False


def _seconds_until(month: int, day: int, hour: int = 6) -> float:
    """Return seconds from now until the next occurrence of month/day at hour:00."""
    now = datetime.now()
    target = now.replace(month=month, day=day, hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        # Already passed this year — schedule for next year
        target = target.replace(year=target.year + 1)
    return (target - now).total_seconds()


def _run_send_reminders():
    """Send 30-day renewal reminder emails to all active members."""
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
    finally:
        # Re-schedule for next year
        _schedule_reminders()


def _run_generate_invoices():
    """Generate annual invoices and send them to all active members."""
    try:
        logger.info("[Scheduler] Running March 31st invoice generation job")
        from django.core.management import call_command
        call_command("generate_annual_invoices", force=True)
        logger.info("[Scheduler] Invoice generation job done")
    except Exception as e:
        logger.error(f"[Scheduler] Invoice generation job failed: {e}")
    finally:
        # Re-schedule for next year
        _schedule_invoices()


def _schedule_reminders():
    delay = _seconds_until(month=3, day=1, hour=6)
    days = int(delay // 86400)
    logger.info(f"[Scheduler] Next renewal reminder scheduled in {days} days (March 1st)")
    t = threading.Timer(delay, _run_send_reminders)
    t.daemon = True
    t.start()


def _schedule_invoices():
    delay = _seconds_until(month=3, day=31, hour=6)
    days = int(delay // 86400)
    logger.info(f"[Scheduler] Next invoice generation scheduled in {days} days (March 31st)")
    t = threading.Timer(delay, _run_generate_invoices)
    t.daemon = True
    t.start()


def start():
    """Start both scheduled jobs. Safe to call multiple times — only starts once."""
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True
    logger.info("[Scheduler] Starting membership renewal scheduler")
    _schedule_reminders()
    _schedule_invoices()
