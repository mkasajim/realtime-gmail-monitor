#!/usr/bin/env python3
"""
Gmail Monitor Launcher
This script helps you choose between configuring accounts or running the monitor.
"""

import os
import sys
import subprocess
import argparse

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

def main():
    parser = argparse.ArgumentParser(description='Gmail Monitor Launcher')
    parser.add_argument('--manage', action='store_true', 
                       help='Launch the account manager directly')
    parser.add_argument('--monitor', action='store_true', 
                       help='Launch the monitor directly')
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
        print("4. Exit")
        print()
        
        while True:
            choice = input("Enter your choice (1-4): ").strip()
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
                print("Goodbye!")
                return
            else:
                print("Invalid choice. Please enter 1-4.")

if __name__ == "__main__":
    main()
