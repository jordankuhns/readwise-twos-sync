#!/usr/bin/env python3
"""
Test script to verify the scheduler timezone fix
"""

import pytz
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import time

def simulate_sync_job(user_id):
    """Simulate a sync job"""
    now = datetime.now()
    now_utc = datetime.now(pytz.UTC)
    now_chicago = now_utc.astimezone(pytz.timezone('America/Chicago'))
    
    print(f"Sync job for user {user_id} executed at:")
    print(f"  System local: {now}")
    print(f"  UTC: {now_utc}")
    print(f"  Chicago: {now_chicago}")

def schedule_sync_job_with_timezone(user_id, sync_time, scheduler):
    """Schedule a sync job with proper timezone handling (like the fixed version)"""
    # Parse sync time (format: "HH:MM")
    hour, minute = map(int, sync_time.split(':'))
    
    # Get the system's local timezone - detect automatically
    try:
        # Try to get system timezone
        import time
        local_tz_name = time.tzname[time.daylight]
        if local_tz_name in ['CDT', 'CST']:
            local_tz = pytz.timezone('America/Chicago')
        else:
            # Fallback to system timezone
            local_tz = pytz.timezone('America/Chicago')  # Default for this deployment
    except:
        # Fallback to Chicago timezone
        local_tz = pytz.timezone('America/Chicago')
    
    # Remove existing job if it exists
    try:
        scheduler.remove_job(f"sync_user_{user_id}")
    except:
        pass
    
    # Schedule new job with timezone (FIXED VERSION)
    scheduler.add_job(
        simulate_sync_job,
        'cron',
        hour=hour,
        minute=minute,
        timezone=local_tz,  # This is the key fix!
        id=f"sync_user_{user_id}",
        args=[user_id]
    )
    print(f"✅ FIXED: Scheduled daily sync for user {user_id} at {hour}:{minute} {local_tz}")
    return scheduler.get_job(f"sync_user_{user_id}")

def schedule_sync_job_without_timezone(user_id, sync_time, scheduler):
    """Schedule a sync job without timezone handling (like the broken version)"""
    # Parse sync time (format: "HH:MM")
    hour, minute = map(int, sync_time.split(':'))
    
    # Remove existing job if it exists
    try:
        scheduler.remove_job(f"sync_user_broken_{user_id}")
    except:
        pass
    
    # Schedule new job WITHOUT timezone (BROKEN VERSION)
    scheduler.add_job(
        simulate_sync_job,
        'cron',
        hour=hour,
        minute=minute,
        # No timezone specified - this was the bug!
        id=f"sync_user_broken_{user_id}",
        args=[user_id]
    )
    print(f"❌ BROKEN: Scheduled daily sync for user {user_id} at {hour}:{minute} (no timezone)")
    return scheduler.get_job(f"sync_user_broken_{user_id}")

def main():
    """Test the scheduler timezone fix"""
    print("Testing scheduler timezone fix...")
    print("=" * 50)
    
    # Get current time in different timezones
    now_utc = datetime.now(pytz.UTC)
    now_chicago = now_utc.astimezone(pytz.timezone('America/Chicago'))
    now_local = datetime.now()
    
    print(f"Current times:")
    print(f"  System local: {now_local}")
    print(f"  UTC: {now_utc}")
    print(f"  Chicago: {now_chicago}")
    print()
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # Test case: User wants sync at 9:00 AM local time
    sync_time = "09:00"
    user_id = 1
    
    print(f"User wants sync at {sync_time} local time")
    print()
    
    # Schedule with the FIXED version (includes timezone)
    fixed_job = schedule_sync_job_with_timezone(user_id, sync_time, scheduler)
    
    # Schedule with the BROKEN version (no timezone)
    broken_job = schedule_sync_job_without_timezone(user_id, sync_time, scheduler)
    
    print()
    print("Comparison of scheduled jobs:")
    print("-" * 30)
    
    print(f"FIXED job next run time:  {fixed_job.next_run_time}")
    print(f"BROKEN job next run time: {broken_job.next_run_time}")
    
    # Calculate the difference
    if fixed_job.next_run_time and broken_job.next_run_time:
        # Convert both to UTC for comparison
        fixed_utc = fixed_job.next_run_time.astimezone(pytz.UTC) if fixed_job.next_run_time.tzinfo else pytz.UTC.localize(fixed_job.next_run_time)
        broken_utc = broken_job.next_run_time.astimezone(pytz.UTC) if broken_job.next_run_time.tzinfo else pytz.UTC.localize(broken_job.next_run_time)
        
        diff = (fixed_utc - broken_utc).total_seconds() / 3600  # Convert to hours
        
        print(f"\nTime difference: {diff} hours")
        
        if abs(diff) > 0:
            print(f"🚨 The broken version would run {abs(diff)} hours {'earlier' if diff > 0 else 'later'} than expected!")
            print(f"   User expects: 9:00 AM local time")
            print(f"   Fixed runs at: {fixed_job.next_run_time.strftime('%I:%M %p %Z')}")
            print(f"   Broken runs at: {broken_job.next_run_time.strftime('%I:%M %p %Z')} (interpreted as UTC)")
        else:
            print("✅ Both versions would run at the same time (timezone not an issue)")
    
    scheduler.shutdown()
    print("\nTest completed!")

if __name__ == "__main__":
    main()