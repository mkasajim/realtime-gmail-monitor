import base64
import json
import os
import time
import argparse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.cloud import pubsub_v1
from rich.console import Console
from rich.panel import Panel
from rich.live import Live

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
# Replace with your project ID
GCP_PROJECT_ID = "gmail-monitor-463406"
# Replace with your Pub/Sub topic ID
PUB_SUB_TOPIC_ID = "gmail-realtime-feed"
# Replace with your Pub/Sub subscription ID
PUB_SUB_SUBSCRIPTION_ID = "gmail-realtime-subscriber"
# Path to your credentials file
CLIENT_SECRET_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
HISTORY_FILE = 'last_history_id.txt'

# Global variables to track state
last_processed_history_id = None
last_seen_message_id = None
displayed_message_ids = set()  # Track messages we've already displayed
last_notification_time = 0  # Track when we last processed a notification
debug_mode = False  # Debug mode flag


def debug_print(console, message):
    """Print debug messages only when debug mode is enabled."""
    if debug_mode:
        console.print(message)

def load_last_history_id():
    """Load the last processed history ID from file."""
    global last_processed_history_id, last_seen_message_id
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                content = f.read().strip()
                if ',' in content:
                    # New format: history_id,message_id
                    last_processed_history_id, last_seen_message_id = content.split(',', 1)
                else:
                    # Old format: just history_id
                    last_processed_history_id = content
                return last_processed_history_id
    except Exception:
        pass
    return None


def save_last_history_id(history_id, message_id=None):
    """Save the last processed history ID and optionally message ID to file."""
    global last_processed_history_id, last_seen_message_id
    try:
        with open(HISTORY_FILE, 'w') as f:
            if message_id:
                f.write(f"{history_id},{message_id}")
                last_seen_message_id = message_id
            else:
                f.write(str(history_id))
        last_processed_history_id = str(history_id)
    except Exception:
        pass


def get_gmail_service():
    """Authenticates with Google and returns a Gmail service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def get_email_details(service, message_id):
    """Fetches the details of a specific email."""
    try:
        message = service.users().messages().get(
            userId='me', id=message_id, format='full'
        ).execute()
        return message
    except Exception as e:
        return None


def process_pubsub_message(message, service, console):
    """Processes a single Pub/Sub message."""
    global last_processed_history_id, last_seen_message_id, last_notification_time
    try:
        # Decode and parse the message data
        data = json.loads(message.data.decode('utf-8'))
        email_address = data['emailAddress']
        notification_history_id = data['historyId']
        
        # Simple rate limiting - if we just processed a notification very recently, be more conservative
        current_time = time.time()
        time_since_last = current_time - last_notification_time
        
        if time_since_last < 2:  # Less than 2 seconds since last notification
            debug_print(console, f"[dim]Received notification for {email_address}, history ID: {notification_history_id} (rate limited check)[/dim]")
        else:
            debug_print(console, f"[dim]Received notification for {email_address}, history ID: {notification_history_id}[/dim]")
        
        last_notification_time = current_time

        # Use the stored last history ID as starting point, or get current if none stored
        start_history_id = last_processed_history_id
        if not start_history_id:
            # If no stored history, get current profile and use it as baseline
            profile = service.users().getProfile(userId='me').execute()
            start_history_id = str(int(profile['historyId']) - 100)  # Go back further to catch recent changes
            debug_print(console, f"[dim]No stored history ID, using baseline: {start_history_id}[/dim]")
        
        debug_print(console, f"[dim]Checking history from {start_history_id} to {notification_history_id}[/dim]")
        
        messages_found = 0
        
        # Approach 1: Try history API
        try:
            history = service.users().history().list(
                userId='me', 
                startHistoryId=start_history_id,
                historyTypes=['messageAdded'],
                maxResults=100
            ).execute()

            if 'history' in history:
                debug_print(console, f"[dim]Processing {len(history['history'])} history records[/dim]")
                for h in history['history']:
                    if 'messagesAdded' in h:
                        for msg in h['messagesAdded']:
                            message_id = msg['message']['id']
                            email = get_email_details(service, message_id)
                            if email:
                                if display_email(email, console):
                                    messages_found += 1
            
        except Exception as history_error:
            debug_print(console, f"[red]History API error: {history_error}[/red]")
        
        # Approach 2: If history didn't find anything, check recent messages since last check
        if messages_found == 0:
            debug_print(console, "[dim]No messages in history, checking recent messages with timestamp filter[/dim]")
            
            try:
                # Get recent messages from inbox
                recent_messages = service.users().messages().list(
                    userId='me', 
                    maxResults=10,
                    q='in:inbox'
                ).execute()
                
                if 'messages' in recent_messages:
                    # Check if the most recent message is different from what we've seen
                    most_recent_id = recent_messages['messages'][0]['id']
                    
                    if last_seen_message_id and most_recent_id != last_seen_message_id:
                        debug_print(console, f"[dim]New message detected! Previous: {last_seen_message_id}, Current: {most_recent_id}[/dim]")
                        
                        # Show the new message
                        email = get_email_details(service, most_recent_id)
                        if email:
                            if display_email(email, console):
                                messages_found += 1
                            # Update the last seen message ID
                            save_last_history_id(notification_history_id, most_recent_id)
                    elif not last_seen_message_id:
                        # First run - just store the current message ID without showing it
                        debug_print(console, f"[dim]First run - storing current latest message ID: {most_recent_id}[/dim]")
                        save_last_history_id(notification_history_id, most_recent_id)
                    else:
                        debug_print(console, f"[dim]No new messages - latest is still: {most_recent_id}[/dim]")
                            
            except Exception as recent_error:
                debug_print(console, f"[red]Recent messages check error: {recent_error}[/red]")
        
        if messages_found == 0:
            debug_print(console, "[dim]No new messages found in either history or recent check[/dim]")
            # Show the most recent email for debugging
            if debug_mode:
                try:
                    recent_messages = service.users().messages().list(
                        userId='me', 
                        maxResults=1,
                        q='in:inbox'
                    ).execute()
                    
                    if 'messages' in recent_messages:
                        email = get_email_details(service, recent_messages['messages'][0]['id'])
                        if email:
                            headers = email['payload'].get('headers', [])
                            subject = next(
                                (h['value'] for h in headers if h['name'] == 'Subject'),
                                'No Subject'
                            )
                            internal_date = int(email.get('internalDate', 0)) / 1000
                            debug_print(console, f"[dim]Most recent email: {subject} (ID: {recent_messages['messages'][0]['id']}, Date: {internal_date})[/dim]")
                except Exception:
                    pass
        
        # Update the last processed history ID (only if we didn't already update it with a message)
        if messages_found == 0:
            save_last_history_id(notification_history_id)
        
    except Exception as e:
        console.print(
            Panel(
                f"Error processing message: {e}",
                title="Error",
                border_style="red"
            )
        )
    finally:
        message.ack()


def display_email(email, console):
    """Display email details in a formatted panel."""
    global displayed_message_ids
    try:
        message_id = email.get('id')
        
        # Check if we've already displayed this email
        if message_id in displayed_message_ids:
            debug_print(console, f"[dim]Skipping duplicate email display for message ID: {message_id}[/dim]")
            return False
        
        # Add to displayed set
        displayed_message_ids.add(message_id)
        
        # Keep only the last 100 message IDs to prevent memory growth
        if len(displayed_message_ids) > 100:
            # Remove the oldest ones (this is a simple approach)
            displayed_message_ids = set(list(displayed_message_ids)[-50:])
        
        # Safely extract headers
        headers = email['payload'].get('headers', [])
        subject = next(
            (h['value'] for h in headers if h['name'] == 'Subject'),
            'No Subject'
        )
        from_ = next(
            (h['value'] for h in headers if h['name'] == 'From'),
            'Unknown Sender'
        )
        snippet = email.get('snippet', 'No preview available')
        
        # Get timestamp
        date_header = next(
            (h['value'] for h in headers if h['name'] == 'Date'),
            'Unknown Date'
        )
        
        # Get internal date for more precise timing
        internal_date = int(email.get('internalDate', 0)) / 1000
        formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(internal_date))
        
        panel_content = f"[bold]From:[/bold] {from_}\n[bold]Subject:[/bold] {subject}\n[bold]Date:[/bold] {date_header}\n[bold]Received:[/bold] {formatted_time}\n[bold]Snippet:[/bold] {snippet}"
        console.print(
            Panel(
                panel_content,
                title="📧 New Email Detected!",
                border_style="green"
            )
        )
        return True
    except Exception as e:
        console.print(f"[red]Error displaying email: {e}[/red]")
        return False


def check_watch_status(service, console):
    """Check the current watch status and provide diagnostic information."""
    try:
        # Check if we have an active watch
        profile = service.users().getProfile(userId='me').execute()
        debug_print(console, f"[dim]Current Gmail profile history ID: {profile['historyId']}[/dim]")
        
        # List recent messages to verify connection
        results = service.users().messages().list(
            userId='me', 
            maxResults=1,
            q='in:inbox'
        ).execute()
        messages = results.get('messages', [])
        
        if messages:
            debug_print(console, f"[dim]✓ Successfully connected to Gmail. Latest message ID: {messages[0]['id']}[/dim]")
        else:
            console.print("[yellow]⚠ No messages found in inbox[/yellow]")
            
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to check Gmail status: {e}[/red]")
        return False

def test_pubsub_connection(console):
    """Test the Pub/Sub connection."""
    try:
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(
            GCP_PROJECT_ID, PUB_SUB_SUBSCRIPTION_ID
        )
        
        # Check if subscription exists
        try:
            subscription = subscriber.get_subscription(request={"subscription": subscription_path})
            debug_print(console, f"[dim]✓ Pub/Sub subscription exists: {subscription.name}[/dim]")
            debug_print(console, f"[dim]  Topic: {subscription.topic}[/dim]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Pub/Sub subscription error: {e}[/red]")
            console.print(f"[yellow]Make sure the subscription '{PUB_SUB_SUBSCRIPTION_ID}' exists in project '{GCP_PROJECT_ID}'[/yellow]")
            return False
            
    except Exception as e:
        console.print(f"[red]✗ Pub/Sub client error: {e}[/red]")
        return False


def main():
    """Starts the Gmail monitor."""
    global debug_mode
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Gmail Real-time Monitor')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose output')
    args = parser.parse_args()
    
    debug_mode = args.debug
    
    console = Console()
    console.print(Panel("Starting Gmail Monitor...",
                  title="Status", border_style="blue"))
    
    if debug_mode:
        console.print("[dim]Debug mode enabled - showing verbose output[/dim]")

    service = get_gmail_service()
    
    # Load the last processed history ID
    load_last_history_id()
    debug_print(console, f"[dim]Last processed history ID: {last_processed_history_id or 'None (first run)'}[/dim]")
    debug_print(console, f"[dim]Last seen message ID: {last_seen_message_id or 'None (first run)'}[/dim]")
    
    # Run diagnostics
    if debug_mode:
        console.print(Panel("Running diagnostics...", title="🔧 Setup Check", border_style="yellow"))
    
    if not check_watch_status(service, console):
        console.print(Panel("Failed Gmail connection check. Please verify your credentials.", title="Error", border_style="red"))
        return
        
    if not test_pubsub_connection(console):
        console.print(Panel("Failed Pub/Sub connection check. Please verify your GCP setup.", title="Error", border_style="red"))
        return

    # Start watching the inbox for changes
    request = {
        'labelIds': ['INBOX'],
        'topicName': f'projects/{GCP_PROJECT_ID}/topics/{PUB_SUB_TOPIC_ID}'
    }
    try:
        watch_response = service.users().watch(userId='me', body=request).execute()
        console.print(Panel(
            f"✓ Successfully started watching Gmail inbox\n"
            f"Topic: {PUB_SUB_TOPIC_ID}\n"
            f"Watch expires: {watch_response.get('expiration', 'Unknown')}", 
            title="✅ Watch Active", 
            border_style="green"
        ))
    except Exception as e:
        console.print(Panel(f"Failed to start watching topic: {e}", title="Error", border_style="red"))
        console.print(Panel(
            "Common issues:\n"
            "• Make sure the Pub/Sub topic exists\n"
            "• Verify the Gmail API has permission to publish to the topic\n"
            "• Check that the service account has proper IAM roles",
            title="Troubleshooting Tips",
            border_style="yellow"
        ))
        return

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        GCP_PROJECT_ID, PUB_SUB_SUBSCRIPTION_ID
    )

    def callback(message):
        debug_print(console, f"[dim]Received Pub/Sub message: {len(message.data)} bytes[/dim]")
        process_pubsub_message(message, service, console)

    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=callback
    )
    console.print(
        Panel(
            f"🔄 Listening for messages on subscription:\n{subscription_path}\n\n"
            f"📧 Send an email to your Gmail to test the real-time monitoring!\n\n"
            f"{'🐛 Debug mode: ON (use --debug to toggle)' if debug_mode else '💤 Quiet mode: ON (use --debug for verbose output)'}",
            title="Gmail Monitor Active",
            border_style="cyan"
        )
    )

    try:
        # Add a timeout to periodically show that we're still listening
        while True:
            try:
                streaming_pull_future.result(timeout=30)
            except Exception:
                if debug_mode:
                    console.print("[dim]Still listening for new emails...[/dim]")
                continue
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
        console.print(Panel("Gmail Monitor Stopped.",
                      title="Status", border_style="red"))


if __name__ == '__main__':
    main()
