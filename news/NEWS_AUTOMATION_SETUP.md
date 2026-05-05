# ICPAU News Fetch Automation Setup

This document provides two options for automating the ICPAU news fetch to run twice a week on your server.

## What Does the News Fetch Do?

The `newsfetch` command:
- Fetches news articles from ICPAU's RSS feed (https://www.icpau.co.ug/rss.xml)
- Parses and cleans the HTML content
- Syncs articles to your Strapi CMS at http://64.225.121.230:1337
- Updates existing articles or creates new ones

---

## Option 1: Celery + Redis (Recommended for Production)

### Advantages
✅ Better for multiple scheduled tasks  
✅ Built-in retry logic and error handling  
✅ Task monitoring and logging  
✅ Already partially configured in your project  
✅ Can run other background tasks (payments, etc.)

### Prerequisites
1. **Redis** must be installed and running on your server
2. **Celery** Python package (should already be installed)

### Installation Steps

#### 1. Install Redis (if not already installed)

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

#### 2. Update Environment Variables

Add to your `.env` file:
```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

If Redis is on a different host or requires authentication:
```bash
CELERY_BROKER_URL=redis://:password@hostname:6379/0
CELERY_RESULT_BACKEND=redis://:password@hostname:6379/0
```

#### 3. Install Celery (if not already installed)

```bash
pip install celery redis django-celery-beat
```

#### 4. Start Celery Worker

Create a systemd service file for the Celery worker:

**Create `/etc/systemd/system/celery-worker.service`:**
```ini
[Unit]
Description=Celery Worker for APF Portal
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/venv/bin"
ExecStart=/path/to/your/venv/bin/celery -A api worker --loglevel=info --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Replace:**
- `/path/to/your/project` with your actual project path
- `/path/to/your/venv/bin` with your virtual environment path
- `www-data` with your server user if different

#### 5. Start Celery Beat (Scheduler)

Create a systemd service file for Celery Beat:

**Create `/etc/systemd/system/celery-beat.service`:**
```ini
[Unit]
Description=Celery Beat Scheduler for APF Portal
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/venv/bin"
ExecStart=/path/to/your/venv/bin/celery -A api beat --loglevel=info
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

#### 6. Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable celery-worker
sudo systemctl enable celery-beat

# Start services
sudo systemctl start celery-worker
sudo systemctl start celery-beat

# Check status
sudo systemctl status celery-worker
sudo systemctl status celery-beat
```

#### 7. Verify It's Working

```bash
# Check Celery logs
sudo journalctl -u celery-worker -f
sudo journalctl -u celery-beat -f

# Test the task manually
python manage.py shell
>>> from news.tasks import fetch_icpau_news
>>> fetch_icpau_news.delay()
```

### Schedule Configuration

The news fetch is configured to run **twice a week**:
- **Monday at 9:00 AM**
- **Thursday at 9:00 AM**

To change the schedule, edit `api/celery.py`:

```python
# Current schedule
'fetch-icpau-news-monday-thursday': {
    'task': 'news.tasks.fetch_icpau_news',
    'schedule': crontab(hour=9, minute=0, day_of_week='1,4'),  # Monday=1, Thursday=4
},

# Examples of other schedules:
# Every Monday and Friday at 2:00 PM
'schedule': crontab(hour=14, minute=0, day_of_week='1,5'),

# Every Tuesday and Saturday at 10:30 AM
'schedule': crontab(hour=10, minute=30, day_of_week='2,6'),

# Every day at midnight
'schedule': crontab(hour=0, minute=0),
```

After changing the schedule, restart Celery Beat:
```bash
sudo systemctl restart celery-beat
```

---

## Option 2: Simple Cron Job (Simpler Setup)

### Advantages
✅ No additional dependencies (Redis)  
✅ Simple to set up  
✅ Works well for single scheduled task  
✅ Native to Linux systems

### Disadvantages
❌ No built-in retry logic  
❌ Less sophisticated error handling  
❌ Harder to monitor  
❌ Not ideal if you need many scheduled tasks

### Setup Steps

#### 1. Create a Shell Script

Create a file `/path/to/your/project/scripts/fetch_news.sh`:

```bash
#!/bin/bash

# APF Portal - ICPAU News Fetch Script
# Runs twice a week to fetch news from ICPAU RSS feed

# Configuration
PROJECT_DIR="/path/to/your/project"
VENV_DIR="/path/to/your/venv"
LOG_DIR="/var/log/apf-portal"
LOG_FILE="$LOG_DIR/news-fetch.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Change to project directory
cd "$PROJECT_DIR"

# Run the management command
echo "========================================" >> "$LOG_FILE"
echo "News fetch started at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

python manage.py newsfetch >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ News fetch completed successfully at $(date)" >> "$LOG_FILE"
else
    echo "❌ News fetch failed with exit code $EXIT_CODE at $(date)" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"

# Deactivate virtual environment
deactivate
```

**Replace:**
- `/path/to/your/project` with your actual project path
- `/path/to/your/venv` with your virtual environment path

#### 2. Make the Script Executable

```bash
chmod +x /path/to/your/project/scripts/fetch_news.sh
```

#### 3. Test the Script

```bash
/path/to/your/project/scripts/fetch_news.sh
```

Check the log file:
```bash
cat /var/log/apf-portal/news-fetch.log
```

#### 4. Set Up Cron Job

Edit the crontab for your server user:

```bash
crontab -e
```

Add the following lines to run **twice a week (Monday and Thursday at 9:00 AM)**:

```cron
# ICPAU News Fetch - Runs Monday and Thursday at 9:00 AM
0 9 * * 1 /path/to/your/project/scripts/fetch_news.sh
0 9 * * 4 /path/to/your/project/scripts/fetch_news.sh
```

**Cron Schedule Explanation:**
```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday=0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

**Other Schedule Examples:**
```cron
# Every Monday and Friday at 2:00 PM
0 14 * * 1,5 /path/to/your/project/scripts/fetch_news.sh

# Every Tuesday and Saturday at 10:30 AM
30 10 * * 2,6 /path/to/your/project/scripts/fetch_news.sh

# Every day at midnight
0 0 * * * /path/to/your/project/scripts/fetch_news.sh

# Every Sunday at 8:00 AM
0 8 * * 0 /path/to/your/project/scripts/fetch_news.sh
```

#### 5. Verify Cron Job

List your cron jobs:
```bash
crontab -l
```

Check cron logs:
```bash
# On Ubuntu/Debian
grep CRON /var/log/syslog

# Or check your application log
tail -f /var/log/apf-portal/news-fetch.log
```

#### 6. Log Rotation (Optional but Recommended)

To prevent log files from growing too large, set up log rotation:

Create `/etc/logrotate.d/apf-portal`:

```
/var/log/apf-portal/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 www-data www-data
}
```

Test log rotation:
```bash
sudo logrotate -f /etc/logrotate.d/apf-portal
```

---

## Monitoring and Troubleshooting

### Check if News is Being Fetched

**For Celery:**
```bash
# Check Celery logs
sudo journalctl -u celery-beat -n 100
sudo journalctl -u celery-worker -n 100

# Check task status in Django shell
python manage.py shell
>>> from django_celery_beat.models import PeriodicTask
>>> PeriodicTask.objects.all()
```

**For Cron:**
```bash
# Check cron execution
grep CRON /var/log/syslog | grep fetch_news

# Check application logs
tail -f /var/log/apf-portal/news-fetch.log
```

### Manual Test

Run the command manually to verify it works:
```bash
python manage.py newsfetch
```

### Common Issues

**Issue: Command not found**
- Verify virtual environment is activated
- Check Python path in script/service file

**Issue: Permission denied**
- Check file permissions: `chmod +x script.sh`
- Verify user has access to project directory

**Issue: Redis connection failed (Celery)**
- Check Redis is running: `redis-cli ping`
- Verify CELERY_BROKER_URL in .env

**Issue: No news being fetched**
- Check ICPAU RSS feed is accessible: `curl https://www.icpau.co.ug/rss.xml`
- Verify Strapi API credentials in the command file
- Check network connectivity from server

---

## Recommendation

**For your use case, I recommend Option 2 (Cron Job)** because:
1. You only need to schedule one task (news fetch)
2. Simpler setup without Redis dependency
3. Easier to troubleshoot
4. Native to Linux systems

**However, if you plan to add more scheduled tasks in the future** (like the payment polling, subscription checks, etc.), then **Option 1 (Celery)** would be better as it provides a centralized task management system.

---

## Next Steps

1. Choose which option you want to use
2. Follow the setup steps for that option
3. Test manually first
4. Monitor the logs for the first few runs
5. Adjust the schedule if needed

Let me know if you need help with any of the setup steps!
