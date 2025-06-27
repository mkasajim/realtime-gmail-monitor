#!/usr/bin/env python3
"""
Gmail Monitor Launcher
This script helps you choose between configuring accounts or running the monitor.
"""

import os
import sys
import subprocess
import argparse
import time
import signal
from datetime import datetime

# Ensure we're in the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

def check_config_exists():
    """Check if accounts configuration file exists"""
    return os.path.exists('accounts_config.json')

def check_accounts_configured():
    """Check if any accounts are configured"""
    if not check_config_exists():
        return False
    
    try:
        import json
        with open('accounts_config.json', 'r') as f:
            accounts = json.load(f)
            return len(accounts) > 0
    except:
        return False

def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("  📧 Gmail Monitor - Multi-Account Real-time Email Monitor")
    print("=" * 60)
    print()

def run_monitor_with_restart(debug=False, max_restarts=None, restart_delay=5):
    """
    Run Gmail monitor with automatic restart on unexpected exit.
    
    Args:
        debug: Enable debug mode for monitor
        max_restarts: Maximum number of restarts (None for unlimited)
        restart_delay: Delay in seconds between restarts
    """
    restart_count = 0
    start_time = datetime.now()
    
    print("🔄 Starting Gmail Monitor with Auto-Restart...")
    print(f"   Max restarts: {'Unlimited' if max_restarts is None else max_restarts}")
    print(f"   Restart delay: {restart_delay} seconds")
    print(f"   Debug mode: {'ON' if debug else 'OFF'}")
    print()
    print("Press Ctrl+C to stop the monitor completely.")
    print("=" * 60)
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutdown requested by user. Stopping monitor...")
        sys.exit(0)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    while True:
        try:
            # Prepare command
            cmd = [sys.executable, 'gmail_monitor.py']
            if debug:
                cmd.append('--debug')
            
            # Log restart attempt
            current_time = datetime.now()
            if restart_count == 0:
                print(f"🚀 [{current_time.strftime('%H:%M:%S')}] Starting Gmail Monitor (Initial run)")
            else:
                runtime = current_time - start_time
                print(f"🔄 [{current_time.strftime('%H:%M:%S')}] Restarting Gmail Monitor (Attempt #{restart_count + 1})")
                print(f"   Total runtime: {runtime}")
            
            # Run the monitor
            result = subprocess.run(cmd, capture_output=False)
            
            # Check exit code
            if result.returncode == 0:
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Gmail Monitor exited normally")
                break
            else:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Gmail Monitor crashed with exit code: {result.returncode}")
                
                # Check if we should restart
                if max_restarts is not None and restart_count >= max_restarts:
                    print(f"🛑 Maximum restart limit ({max_restarts}) reached. Stopping.")
                    break
                
                restart_count += 1
                print(f"⏳ Waiting {restart_delay} seconds before restart...")
                time.sleep(restart_delay)
                
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user. Stopping monitor...")
            break
        except Exception as e:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Error running monitor: {e}")
            
            # Check if we should restart
            if max_restarts is not None and restart_count >= max_restarts:
                print(f"🛑 Maximum restart limit ({max_restarts}) reached. Stopping.")
                break
            
            restart_count += 1
            print(f"⏳ Waiting {restart_delay} seconds before restart...")
            time.sleep(restart_delay)
    
    total_runtime = datetime.now() - start_time
    print(f"\n📊 Monitor Statistics:")
    print(f"   Total runtime: {total_runtime}")
    print(f"   Restart count: {restart_count}")
    print("👋 Gmail Monitor session ended.")

def show_restart_options():
    """Show options for configuring auto-restart"""
    print("🔄 Auto-Restart Configuration")
    print("=" * 40)
    print()
    print("Choose restart behavior:")
    print("1. Unlimited restarts (recommended)")
    print("2. Limited restarts (specify max)")
    print("3. Single run (no restart)")
    print("4. Back to main menu")
    print()
    
    while True:
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            # Unlimited restarts
            debug_choice = input("Enable debug mode? (y/n): ").strip().lower()
            debug = debug_choice in ['y', 'yes']
            
            delay_input = input("Restart delay in seconds (default: 5): ").strip()
            try:
                delay = int(delay_input) if delay_input else 5
                if delay < 0:
                    delay = 5
            except ValueError:
                delay = 5
            
            print()
            run_monitor_with_restart(debug=debug, max_restarts=None, restart_delay=delay)
            return
            
        elif choice == '2':
            # Limited restarts
            max_restarts_input = input("Maximum number of restarts (default: 3): ").strip()
            try:
                max_restarts = int(max_restarts_input) if max_restarts_input else 3
                if max_restarts < 0:
                    max_restarts = 3
            except ValueError:
                max_restarts = 3
            
            debug_choice = input("Enable debug mode? (y/n): ").strip().lower()
            debug = debug_choice in ['y', 'yes']
            
            delay_input = input("Restart delay in seconds (default: 5): ").strip()
            try:
                delay = int(delay_input) if delay_input else 5
                if delay < 0:
                    delay = 5
            except ValueError:
                delay = 5
            
            print()
            run_monitor_with_restart(debug=debug, max_restarts=max_restarts, restart_delay=delay)
            return
            
        elif choice == '3':
            # Single run
            debug_choice = input("Enable debug mode? (y/n): ").strip().lower()
            debug = debug_choice in ['y', 'yes']
            
            print()
            print("📧 Starting Gmail Monitor (Single Run)...")
            cmd = [sys.executable, 'gmail_monitor.py']
            if debug:
                cmd.append('--debug')
            subprocess.run(cmd)
            return
            
        elif choice == '4':
            return
        else:
            print("Invalid choice. Please enter 1-4.")

def main():
    parser = argparse.ArgumentParser(description='Gmail Monitor Launcher')
    parser.add_argument('--manage', action='store_true', 
                       help='Launch the account manager directly')
    parser.add_argument('--monitor', action='store_true', 
                       help='Launch the monitor directly')
    parser.add_argument('--auto-restart', action='store_true', 
                       help='Launch the monitor with auto-restart (unlimited restarts)')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug mode for monitor')
    
    args = parser.parse_args()
    
    print_banner()
    
    # If specific mode requested, launch it
    if args.manage:
        print("🔧 Launching Account Manager...")
        subprocess.run([sys.executable, 'account_manager.py'])
        return
    
    if args.monitor:
        print("📧 Launching Gmail Monitor...")
        cmd = [sys.executable, 'gmail_monitor.py']
        if args.debug:
            cmd.append('--debug')
        subprocess.run(cmd)
        return
    
    if args.auto_restart:
        print("🔄 Launching Gmail Monitor with Auto-Restart...")
        run_monitor_with_restart(debug=args.debug, max_restarts=None, restart_delay=5)
        return
    
    # Interactive mode
    if not check_accounts_configured():
        print("⚠️  No accounts configured yet!")
        print()
        print("You need to configure at least one Gmail account before")
        print("you can start monitoring emails.")
        print()
        print("Would you like to:")
        print("1. Configure accounts (Account Manager)")
        print("2. Exit")
        print()
        
        while True:
            choice = input("Enter your choice (1-2): ").strip()
            if choice == '1':
                print()
                print("🔧 Launching Account Manager...")
                subprocess.run([sys.executable, 'account_manager.py'])
                break
            elif choice == '2':
                print("Goodbye!")
                return
            else:
                print("Invalid choice. Please enter 1 or 2.")
    else:
        # Accounts are configured, show main menu
        try:
            import json
            with open('accounts_config.json', 'r') as f:
                accounts = json.load(f)
            
            print(f"✅ Found {len(accounts)} configured account(s):")
            for i, account in enumerate(accounts, 1):
                print(f"   {i}. {account['name']} ({account['email']})")
            print()
        except:
            pass
        
        print("What would you like to do?")
        print("1. Start Gmail Monitor")
        print("2. Manage Accounts (add/remove/configure)")
        print("3. Start Gmail Monitor with Debug Mode")
        print("4. Configure Auto-Restart for Monitor")
        print("5. Exit")
        print()
        
        while True:
            choice = input("Enter your choice (1-5): ").strip()
            if choice == '1':
                print()
                print("📧 Starting Gmail Monitor...")
                subprocess.run([sys.executable, 'gmail_monitor.py'])
                break
            elif choice == '2':
                print()
                print("🔧 Launching Account Manager...")
                subprocess.run([sys.executable, 'account_manager.py'])
                break
            elif choice == '3':
                print()
                print("📧 Starting Gmail Monitor (Debug Mode)...")
                subprocess.run([sys.executable, 'gmail_monitor.py', '--debug'])
                break
            elif choice == '4':
                print()
                show_restart_options()
                break
            elif choice == '5':
                print("Goodbye!")
                return
            else:
                print("Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()
