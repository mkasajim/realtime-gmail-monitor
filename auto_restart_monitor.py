#!/usr/bin/env python3
"""
Gmail Monitor Auto-Restart Wrapper
This script runs the Gmail monitor with automatic restart functionality.
"""

import os
import sys
import subprocess
import time
import signal
import argparse
from datetime import datetime

# Ensure we're in the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

def log_message(message):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def run_monitor_with_restart(debug=False, max_restarts=None, restart_delay=5, log_file=None):
    """
    Run Gmail monitor with automatic restart on unexpected exit.
    
    Args:
        debug: Enable debug mode for monitor
        max_restarts: Maximum number of restarts (None for unlimited)
        restart_delay: Delay in seconds between restarts
        log_file: Optional log file path for restart events
    """
    restart_count = 0
    start_time = datetime.now()
    
    def write_log(message):
        log_message(message)
        if log_file:
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            except Exception as e:
                log_message(f"Failed to write to log file: {e}")
    
    write_log("🔄 Starting Gmail Monitor with Auto-Restart...")
    write_log(f"   Max restarts: {'Unlimited' if max_restarts is None else max_restarts}")
    write_log(f"   Restart delay: {restart_delay} seconds")
    write_log(f"   Debug mode: {'ON' if debug else 'OFF'}")
    if log_file:
        write_log(f"   Log file: {log_file}")
    write_log("")
    write_log("Press Ctrl+C to stop the monitor completely.")
    write_log("=" * 60)
    
    def signal_handler(sig, frame):
        write_log("🛑 Shutdown requested by user. Stopping monitor...")
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
                write_log(f"🚀 Starting Gmail Monitor (Initial run)")
            else:
                runtime = current_time - start_time
                write_log(f"🔄 Restarting Gmail Monitor (Attempt #{restart_count + 1})")
                write_log(f"   Total runtime: {runtime}")
            
            # Run the monitor
            result = subprocess.run(cmd, capture_output=False)
            
            # Check exit code
            if result.returncode == 0:
                write_log("✅ Gmail Monitor exited normally")
                break
            else:
                write_log(f"❌ Gmail Monitor crashed with exit code: {result.returncode}")
                
                # Check if we should restart
                if max_restarts is not None and restart_count >= max_restarts:
                    write_log(f"🛑 Maximum restart limit ({max_restarts}) reached. Stopping.")
                    break
                
                restart_count += 1
                write_log(f"⏳ Waiting {restart_delay} seconds before restart...")
                time.sleep(restart_delay)
                
        except KeyboardInterrupt:
            write_log("🛑 Shutdown requested by user. Stopping monitor...")
            break
        except Exception as e:
            write_log(f"❌ Error running monitor: {e}")
            
            # Check if we should restart
            if max_restarts is not None and restart_count >= max_restarts:
                write_log(f"🛑 Maximum restart limit ({max_restarts}) reached. Stopping.")
                break
            
            restart_count += 1
            write_log(f"⏳ Waiting {restart_delay} seconds before restart...")
            time.sleep(restart_delay)
    
    total_runtime = datetime.now() - start_time
    write_log(f"📊 Monitor Statistics:")
    write_log(f"   Total runtime: {total_runtime}")
    write_log(f"   Restart count: {restart_count}")
    write_log("👋 Gmail Monitor session ended.")

def main():
    parser = argparse.ArgumentParser(description='Gmail Monitor Auto-Restart Wrapper')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug mode for monitor')
    parser.add_argument('--max-restarts', type=int, default=None,
                       help='Maximum number of restarts (default: unlimited)')
    parser.add_argument('--restart-delay', type=int, default=5,
                       help='Delay in seconds between restarts (default: 5)')
    parser.add_argument('--log-file', type=str, default=None,
                       help='Optional log file for restart events')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.restart_delay < 0:
        print("Error: Restart delay must be non-negative")
        sys.exit(1)
    
    if args.max_restarts is not None and args.max_restarts < 0:
        print("Error: Max restarts must be non-negative")
        sys.exit(1)
    
    # Run the monitor with restart
    run_monitor_with_restart(
        debug=args.debug,
        max_restarts=args.max_restarts,
        restart_delay=args.restart_delay,
        log_file=args.log_file
    )

if __name__ == "__main__":
    main()
