#!/usr/bin/env python3
"""
Test script to simulate UTC environment and show the timezone issue
"""

import os
import pytz
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

def main():
    """Test timezone handling in a simulated UTC environment"""
    print("Simulating UTC environment (like production servers)...")
    print("=" * 50)
    
    # Simulate UTC environment by setting TZ environment variable
    os.environ['TZ'] = 'UTC'
    
    # Create scheduler (this will now default to UTC)
    scheduler = BackgroundScheduler()
    
    print(f"Scheduler timezone in UTC environment: {scheduler.timezone}")
    
    # Test case: User wants sync at 9:00 AM local time (Chicago)
    sync_time = "09:00"
    hour, minute = map(int, sync_time.split(':'))
    
    print(f"\nUser wants sync at {sync_time} Chicago time")
    
    # Schedule WITHOUT timezone (broken version - uses scheduler default which is now UTC)
    scheduler.add_job(
        lambda: print("Job executed"),
        'cron',
        hour=hour,
        minute=minute,
        id='broken_job'
    )
    
    # Schedule WITH timezone (fixed version)
    chicago_tz = pytz.timezone('America/Chicago')
    scheduler.add_job(
        lambda: print("Job executed"),
        'cron',
        hour=hour,
        minute=minute,
        timezone=chicago_tz,
        id='fixed_job'
    )
    
    scheduler.start()
    
    broken_job = scheduler.get_job('broken_job')
    fixed_job = scheduler.get_job('fixed_job')
    
    print(f"\nBROKEN job (no timezone): {broken_job.next_run_time}")
    print(f"FIXED job (with timezone): {fixed_job.next_run_time}")
    
    # Calculate the difference
    if broken_job.next_run_time and fixed_job.next_run_time:
        # Convert both to UTC for comparison
        broken_utc = broken_job.next_run_time.astimezone(pytz.UTC) if broken_job.next_run_time.tzinfo else pytz.UTC.localize(broken_job.next_run_time)
        fixed_utc = fixed_job.next_run_time.astimezone(pytz.UTC) if fixed_job.next_run_time.tzinfo else pytz.UTC.localize(fixed_job.next_run_time)
        
        diff_hours = (broken_utc - fixed_utc).total_seconds() / 3600
        
        print(f"\nTime difference: {diff_hours} hours")
        
        if abs(diff_hours) > 0:
            print(f"🚨 TIMEZONE BUG DETECTED!")
            print(f"   User expects: 9:00 AM Chicago time")
            print(f"   Fixed version: {fixed_job.next_run_time.strftime('%I:%M %p %Z')}")
            print(f"   Broken version: {broken_job.next_run_time.strftime('%I:%M %p %Z')} (treated as UTC)")
            print(f"   The broken version runs {abs(diff_hours)} hours {'earlier' if diff_hours > 0 else 'later'}!")
        else:
            print("✅ No timezone issue detected")
    
    scheduler.shutdown()
    
    # Reset TZ
    if 'TZ' in os.environ:
        del os.environ['TZ']

if __name__ == "__main__":
    main()