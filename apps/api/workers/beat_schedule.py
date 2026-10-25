"""
Celery Beat Schedule — defines all periodic cron tasks.
Run with: celery -A workers.beat_schedule beat --loglevel=info
"""
from celery.schedules import crontab
from workers.celery_app import celery_app

celery_app.conf.beat_schedule = {

    # ── Agent 1: Daily trend research for all active tenants ──────────────────
    "daily-trend-research": {
        "task": "workers.tasks.newsjack_poller.run_daily_trend_research",
        "schedule": crontab(hour=6, minute=0),   # 6:00 AM UTC daily
        "options": {"queue": "research_queue"},
    },

    # ── Agent 1: Newsjack poll every 15 minutes (active tenants only) ─────────
    "newsjack-poll-15min": {
        "task": "workers.tasks.newsjack_poller.poll_all_tenants_newsjack",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "research_queue"},
    },

    # ── Agent 5: High-frequency analytics poll every 60 seconds ──────────────
    "hf-analytics-poll-60s": {
        "task": "workers.tasks.analytics_poller.poll_all_active_posts",
        "schedule": 60.0,   # Every 60 seconds
        "options": {"queue": "analytics_queue"},
    },

    # ── Agent 5: Daily analytics rollup (for dashboard charts) ───────────────
    "daily-analytics-rollup": {
        "task": "workers.tasks.analytics_poller.compute_daily_rollup",
        "schedule": crontab(hour=1, minute=0),   # 1:00 AM UTC daily
        "options": {"queue": "analytics_queue"},
    },

    # ── DM backlog retry (process rate-limited DMs from backlog queue) ────────
    "dm-backlog-retry": {
        "task": "workers.tasks.dm_dispatcher.retry_backlog_dms",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "dm_queue"},
    },

    # ── Tenant quota reset (1st of each month at midnight UTC) ────────────────
    "monthly-quota-reset": {
        "task": "workers.tasks.scheduler.reset_monthly_quotas",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
        "options": {"queue": "default"},
    },
}
