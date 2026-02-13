# Scheduled Announcements Setup

This document explains how to set up automatic processing of scheduled announcements in the APF Portal.

## Overview

The AdminNotifications app includes functionality to schedule announcements for future delivery. The system uses Django management commands that can be run periodically to process scheduled announcements.

## Management Commands

### Process Scheduled Announcements
```bash
python manage.py process_scheduled_announcements
```

This command:
- Finds all announcements with status 'scheduled' that are due to be sent
- Updates their status to 'sent'
- Sends both email and in-app notifications to the targeted audience
- Sets the sent_at timestamp

### Send Test Announcement
```bash
python manage.py send_test_announcement --title "Test Title" --content "Test content" --audience members
```

This command sends a test announcement to verify the notification system is working properly.

## Setting Up Periodic Execution

### Option 1: Cron Job (Linux/macOS)

Add a cron job to run every minute to check for scheduled announcements:
```bash
# Edit crontab
crontab -e

# Add this line to run every minute
* * * * * cd /path/to/your/project && python manage.py process_scheduled_announcements >> /var/log/apf_scheduler.log 2>&1
```

### Option 2: Windows Task Scheduler

1. Open Task Scheduler
2. Create a Basic Task
3. Set trigger to run every 1-5 minutes
4. Action: Start a program
5. Program: `python`
6. Arguments: `manage.py process_scheduled_announcements`
7. Start in: Your project directory

### Option 3: Using Celery Beat (Recommended for Production)

If you're using Celery for task queue management, you can set up a periodic task:

1. Install Celery and Redis/RabbitMQ
2. Configure Celery in your settings
3. Create a periodic task that runs the management command

## How It Works

1. Admins create announcements through the API with a scheduled date/time
2. The announcement status is set to 'scheduled' 
3. The scheduled_for field contains the date/time to send
4. The periodic task checks for announcements that are due to be sent
5. When due, the system sends notifications to the appropriate audience

## Audience Types

- `all_users`: All users in the system
- `members`: Users with role '2' (active members)
- `applicants`: Users with pending applications
- `admins`: Users with role '1' (administrators)
- `expired_members`: Members whose subscription has expired

## Channels

- `email`: Send via email
- `in_app`: Create in-app notifications
- `both`: Send both email and in-app notifications