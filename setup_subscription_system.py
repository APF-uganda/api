"""
Setup script for subscription management system
Run this after pulling the changes to set up everything automatically
"""
import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"{'='*60}")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     Subscription Management System Setup                  ║
    ║     This will set up the subscription system              ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("✗ Error: manage.py not found!")
        print("Please run this script from the Backend/api directory")
        sys.exit(1)
    
    steps = [
        {
            'command': 'python manage.py migrate authentication',
            'description': 'Apply authentication migrations (adds subscription_due_date field)'
        },
        {
            'command': 'python manage.py migrate admin_management',
            'description': 'Apply admin_management migrations'
        },
        {
            'command': 'python test_subscription_system.py',
            'description': 'Run system verification tests'
        }
    ]
    
    success_count = 0
    for step in steps:
        if run_command(step['command'], step['description']):
            success_count += 1
        else:
            print(f"\n✗ Setup failed at: {step['description']}")
            print("Please fix the error and run this script again")
            sys.exit(1)
    
    print(f"""
    
    ╔════════════════════════════════════════════════════════════╗
    ║     ✓ Setup Complete!                                     ║
    ╚════════════════════════════════════════════════════════════╝
    
    All {success_count} steps completed successfully!
    
    Next Steps:
    ───────────────────────────────────────────────────────────
    
    1. Test the suspend/reactivate functionality:
       - Go to admin panel → Manage Users
       - Try suspending and reactivating a test member
    
    2. Set up automated expiration checking:
       
       Linux/Mac (crontab):
       ─────────────────────
       crontab -e
       # Add this line:
       0 2 * * * cd {os.getcwd()} && python manage.py check_expired_subscriptions
       
       Windows (Task Scheduler):
       ─────────────────────────
       - Open Task Scheduler
       - Create Basic Task
       - Trigger: Daily at 2:00 AM
       - Action: Start a program
       - Program: python
       - Arguments: manage.py check_expired_subscriptions
       - Start in: {os.getcwd()}
    
    3. Test the expiration check command:
       python manage.py check_expired_subscriptions --dry-run
    
    4. Read the documentation:
       - admin_management/SUBSCRIPTION_MANAGEMENT.md
       - SUBSCRIPTION_SYSTEM_CHANGES.md
    
    ───────────────────────────────────────────────────────────
    
    The system is now ready to use! 🎉
    """)

if __name__ == '__main__':
    main()
