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

# Global credentials file (same for all accounts in the project)
GLOBAL_CREDENTIALS_FILE = 'credentials.json'

# Multi-account configuration - only need to specify account-specific files
ACCOUNTS_CONFIG = [
    {
        'name': 'Primary Account',
        'email': 'appassistant9@gmail.com',  # Add email for identification
        'token_file': 'token1.json',
        'history_file': 'history1.txt'
    },
    # Add more test accounts here by uncommenting and modifying:
    {
        'name': 'Test User 1', 
        'email': 'percysimpson330@gmail.com',  # Replace with actual test account email
        'token_file': 'token2.json',
        'history_file': 'history2.txt'
    },
    {
        'name': 'Test User 2', 
        'email': 'rachelbasin4@gmail.com',  # Replace with actual test account email
        'token_file': 'token3.json',
        'history_file': 'history3.txt'
    },
    # {
    #     'name': 'Test User 3', 
    #     'email': 'testuser3@gmail.com',  # Replace with actual test account email
    #     'token_file': 'token_testuser3.json',
    #     'history_file': 'history_testuser3.txt'
    # }
]

# Global variables to track state
account_data = {}  # Dictionary to store data for each account
displayed_message_ids = set()  # Track messages we've already displayed across all accounts
last_notification_time = 0  # Track when we last processed a notification
debug_mode = False  # Debug mode flag


class GmailAccount:
    """Class to manage individual Gmail account data and operations."""
    
    def __init__(self, config):
        self.name = config['name']
        self.email = config['email']
        self.token_file = config['token_file']
        self.history_file = config['history_file']
        self.last_processed_history_id = None
        self.last_seen_message_id = None
        self.service = None
        
    def load_last_history_id(self):
        """Load the last processed history ID from file."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    content = f.read().strip()
                    if ',' in content:
                        # New format: history_id,message_id
                        self.last_processed_history_id, self.last_seen_message_id = content.split(',', 1)
                    else:
                        # Old format: just history_id
                        self.last_processed_history_id = content
                    return self.last_processed_history_id
        except Exception:
            pass
        return None

    def save_last_history_id(self, history_id, message_id=None):
        """Save the last processed history ID and optionally message ID to file."""
        try:
            with open(self.history_file, 'w') as f:
                if message_id:
                    f.write(f"{history_id},{message_id}")
                    self.last_seen_message_id = message_id
                else:
                    f.write(str(history_id))
            self.last_processed_history_id = str(history_id)
        except Exception:
            pass
            
    def get_gmail_service(self):
        """Authenticates with Google and returns a Gmail service object."""
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GLOBAL_CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        self.service = build('gmail', 'v1', credentials=creds)
        return self.service


def debug_print(console, message):
    """Print debug messages only when debug mode is enabled."""
    if debug_mode:
        console.print(message)


def get_email_details(service, message_id):
    """Fetches the details of a specific email."""
    try:
        message = service.users().messages().get(
            userId='me', id=message_id, format='full'
        ).execute()
        return message
    except Exception as e:
        return None


def find_account_by_email(email_address):
    """Find the account object that matches the given email address."""
    for account in account_data.values():
        if account.email == email_address:
            return account
    return None


def process_pubsub_message(message, console):
    """Processes a single Pub/Sub message for multiple accounts."""
    global last_notification_time
    try:
        # Decode and parse the message data
        data = json.loads(message.data.decode('utf-8'))
        email_address = data['emailAddress']
        notification_history_id = data['historyId']
        
        # Find the account that this notification belongs to
        account = find_account_by_email(email_address)
        if not account:
            debug_print(console, f"[yellow]⚠ No account configured for {email_address}[/yellow]")
            return
            
        # Simple rate limiting - if we just processed a notification very recently, be more conservative
        current_time = time.time()
        time_since_last = current_time - last_notification_time
        
        if time_since_last < 2:  # Less than 2 seconds since last notification
            debug_print(console, f"[dim]Received notification for {email_address} ({account.name}), history ID: {notification_history_id} (rate limited check)[/dim]")
        else:
            debug_print(console, f"[dim]Received notification for {email_address} ({account.name}), history ID: {notification_history_id}[/dim]")
        
        last_notification_time = current_time

        # Use the stored last history ID as starting point, or get current if none stored
        start_history_id = account.last_processed_history_id
        if not start_history_id:
            # If no stored history, get current profile and use it as baseline
            profile = account.service.users().getProfile(userId='me').execute()
            start_history_id = str(int(profile['historyId']) - 100)  # Go back further to catch recent changes
            debug_print(console, f"[dim]No stored history ID for {account.name}, using baseline: {start_history_id}[/dim]")
        
        debug_print(console, f"[dim]Checking history for {account.name} from {start_history_id} to {notification_history_id}[/dim]")
        
        messages_found = 0
        
        # Approach 1: Try history API
        try:
            history = account.service.users().history().list(
                userId='me', 
                startHistoryId=start_history_id,
                historyTypes=['messageAdded'],
                maxResults=100
            ).execute()

            if 'history' in history:
                debug_print(console, f"[dim]Processing {len(history['history'])} history records for {account.name}[/dim]")
                for h in history['history']:
                    if 'messagesAdded' in h:
                        for msg in h['messagesAdded']:
                            message_id = msg['message']['id']
                            email = get_email_details(account.service, message_id)
                            if email:
                                if display_email(email, console, account.name):
                                    messages_found += 1
            
        except Exception as history_error:
            debug_print(console, f"[red]History API error for {account.name}: {history_error}[/red]")
        
        # Approach 2: If history didn't find anything, check recent messages since last check
        if messages_found == 0:
            debug_print(console, f"[dim]No messages in history for {account.name}, checking recent messages[/dim]")
            
            try:
                # Get recent messages from inbox
                recent_messages = account.service.users().messages().list(
                    userId='me', 
                    maxResults=10,
                    q='in:inbox'
                ).execute()
                
                if 'messages' in recent_messages:
                    # Check if the most recent message is different from what we've seen
                    most_recent_id = recent_messages['messages'][0]['id']
                    
                    if account.last_seen_message_id and most_recent_id != account.last_seen_message_id:
                        debug_print(console, f"[dim]New message detected for {account.name}! Previous: {account.last_seen_message_id}, Current: {most_recent_id}[/dim]")
                        
                        # Show the new message
                        email = get_email_details(account.service, most_recent_id)
                        if email:
                            if display_email(email, console, account.name):
                                messages_found += 1
                            # Update the last seen message ID
                            account.save_last_history_id(notification_history_id, most_recent_id)
                    elif not account.last_seen_message_id:
                        # First run - just store the current message ID without showing it
                        debug_print(console, f"[dim]First run for {account.name} - storing current latest message ID: {most_recent_id}[/dim]")
                        account.save_last_history_id(notification_history_id, most_recent_id)
                    else:
                        debug_print(console, f"[dim]No new messages for {account.name} - latest is still: {most_recent_id}[/dim]")
                            
            except Exception as recent_error:
                debug_print(console, f"[red]Recent messages check error for {account.name}: {recent_error}[/red]")
        
        if messages_found == 0:
            debug_print(console, f"[dim]No new messages found for {account.name}[/dim]")
            # Show the most recent email for debugging
            if debug_mode:
                try:
                    recent_messages = account.service.users().messages().list(
                        userId='me', 
                        maxResults=1,
                        q='in:inbox'
                    ).execute()
                    
                    if 'messages' in recent_messages:
                        email = get_email_details(account.service, recent_messages['messages'][0]['id'])
                        if email:
                            headers = email['payload'].get('headers', [])
                            subject = next(
                                (h['value'] for h in headers if h['name'] == 'Subject'),
                                'No Subject'
                            )
                            internal_date = int(email.get('internalDate', 0)) / 1000
                            debug_print(console, f"[dim]Most recent email for {account.name}: {subject} (ID: {recent_messages['messages'][0]['id']}, Date: {internal_date})[/dim]")
                except Exception:
                    pass
        
        # Update the last processed history ID (only if we didn't already update it with a message)
        if messages_found == 0:
            account.save_last_history_id(notification_history_id)
        
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


def display_email(email, console, account_name="Unknown"):
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
        to_ = next(
            (h['value'] for h in headers if h['name'] == 'To'),
            'Unknown Recipient'
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
        
        panel_content = f"[bold]Account:[/bold] {account_name}\n[bold]To:[/bold] {to_}\n[bold]From:[/bold] {from_}\n[bold]Subject:[/bold] {subject}\n[bold]Date:[/bold] {date_header}\n[bold]Received:[/bold] {formatted_time}\n[bold]Snippet:[/bold] {snippet}"
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


def check_watch_status(account, console):
    """Check the current watch status and provide diagnostic information."""
    try:
        # Check if we have an active watch
        profile = account.service.users().getProfile(userId='me').execute()
        debug_print(console, f"[dim]Current Gmail profile history ID for {account.name}: {profile['historyId']}[/dim]")
        
        # List recent messages to verify connection
        results = account.service.users().messages().list(
            userId='me', 
            maxResults=1,
            q='in:inbox'
        ).execute()
        messages = results.get('messages', [])
        
        if messages:
            debug_print(console, f"[dim]✓ Successfully connected to {account.name}. Latest message ID: {messages[0]['id']}[/dim]")
        else:
            console.print(f"[yellow]⚠ No messages found in inbox for {account.name}[/yellow]")
            
        return True
    except Exception as e:
        console.print(f"[red]✗ Failed to check Gmail status for {account.name}: {e}[/red]")
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
    """Starts the Gmail monitor for multiple accounts."""
    global debug_mode, account_data
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Gmail Real-time Monitor (Multi-Account)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose output')
    args = parser.parse_args()
    
    debug_mode = args.debug
    
    console = Console()
    console.print(Panel("Starting Multi-Account Gmail Monitor...",
                  title="Status", border_style="blue"))
    
    if debug_mode:
        console.print("[dim]Debug mode enabled - showing verbose output[/dim]")

    # Initialize all accounts
    for config in ACCOUNTS_CONFIG:
        try:
            account = GmailAccount(config)
            console.print(f"[cyan]Setting up account: {account.name} ({account.email})[/cyan]")
            
            # Authenticate and get service
            service = account.get_gmail_service()
            
            # Load history
            account.load_last_history_id()
            debug_print(console, f"[dim]Last processed history ID for {account.name}: {account.last_processed_history_id or 'None (first run)'}[/dim]")
            debug_print(console, f"[dim]Last seen message ID for {account.name}: {account.last_seen_message_id or 'None (first run)'}[/dim]")
            
            # Store in global dictionary
            account_data[account.email] = account
            
            console.print(f"[green]✓ {account.name} configured successfully[/green]")
            
        except Exception as e:
            console.print(f"[red]✗ Failed to setup {config['name']}: {e}[/red]")
            continue
    
    if not account_data:
        console.print(Panel("No accounts configured successfully. Exiting.", title="Error", border_style="red"))
        return
    
    # Run diagnostics for all accounts
    if debug_mode:
        console.print(Panel("Running diagnostics...", title="🔧 Setup Check", border_style="yellow"))
    
    # Check each account
    for email, account in account_data.items():
        if not check_watch_status(account, console):
            console.print(Panel(f"Failed Gmail connection check for {account.name}. Please verify credentials.", title="Error", border_style="red"))
            continue
    
    # Test Pub/Sub connection (shared across all accounts)
    if not test_pubsub_connection(console):
        console.print(Panel("Failed Pub/Sub connection check. Please verify your GCP setup.", title="Error", border_style="red"))
        return

    # Start watching for all accounts
    watch_count = 0
    for email, account in account_data.items():
        request = {
            'labelIds': ['INBOX'],
            'topicName': f'projects/{GCP_PROJECT_ID}/topics/{PUB_SUB_TOPIC_ID}'
        }
        try:
            watch_response = account.service.users().watch(userId='me', body=request).execute()
            console.print(Panel(
                f"✓ Successfully started watching {account.name}\n"
                f"Email: {account.email}\n"
                f"Topic: {PUB_SUB_TOPIC_ID}\n"
                f"Watch expires: {watch_response.get('expiration', 'Unknown')}", 
                title=f"✅ Watch Active - {account.name}", 
                border_style="green"
            ))
            watch_count += 1
        except Exception as e:
            console.print(Panel(f"Failed to start watching {account.name}: {e}", title="Error", border_style="red"))
            continue

    if watch_count == 0:
        console.print(Panel("No accounts are being watched. Exiting.", title="Error", border_style="red"))
        return

    # Set up Pub/Sub subscription
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        GCP_PROJECT_ID, PUB_SUB_SUBSCRIPTION_ID
    )

    def callback(message):
        debug_print(console, f"[dim]Received Pub/Sub message: {len(message.data)} bytes[/dim]")
        process_pubsub_message(message, console)

    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=callback
    )
    
    # Create account list for display
    account_list = "\n".join([f"  • {acc.name} ({acc.email})" for acc in account_data.values()])
    
    console.print(
        Panel(
            f"🔄 Listening for messages on subscription:\n{subscription_path}\n\n"
            f"📧 Monitoring {len(account_data)} accounts:\n{account_list}\n\n"
            f"{'🐛 Debug mode: ON (use --debug to toggle)' if debug_mode else '💤 Quiet mode: ON (use --debug for verbose output)'}",
            title="Multi-Account Gmail Monitor Active",
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
        console.print(Panel("Multi-Account Gmail Monitor Stopped.",
                      title="Status", border_style="red"))


if __name__ == '__main__':
    main()
