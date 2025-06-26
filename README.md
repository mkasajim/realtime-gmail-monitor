# Multi-Account Gmail Monitor

A Python application that monitors multiple Gmail accounts in real-time using Google Pub/Sub and displays new emails in beautiful terminal panels using the Rich library. Now with a user-friendly GUI for account management!

## Features

- **Multi-Account Support**: Monitor multiple Gmail accounts simultaneously
- **GUI Account Manager**: Easy-to-use interface for adding and managing Gmail accounts
- **Single Credentials File**: All accounts use the same `credentials.json` (perfect for test users in the same GCP project)
- **Automated Authentication**: GUI handles OAuth authentication for each account
- **Real-time Notifications**: Uses Google Pub/Sub for instant email notifications
- **Rich Terminal UI**: Beautiful panels showing email details with account identification
- **Duplicate Prevention**: Smart tracking prevents the same email from being displayed multiple times
- **Debug Mode**: Use `--debug` flag for verbose output or run in quiet mode
- **Robust Error Handling**: Graceful handling of API errors and network issues

## Quick Start

### 1. Setup Environment
```bash
setup_env.bat
```
This will create a virtual environment and install all required dependencies including `python-dotenv`.

### 2. Google Cloud Project Setup (Automated)

Run the automated GCP setup:
```bash
setup_gcp.bat
```

This script will:
1. Prompt you for your Google Cloud Project ID
2. Create a Pub/Sub topic (`gmail-realtime-feed`)
3. Grant Gmail API permissions to publish to the topic
4. Create a Pub/Sub subscription (`gmail-realtime-subscriber`)
5. Save your GCP Project ID to a `.env` file

**Prerequisites:**
- Google Cloud Project created
- Gmail API and Pub/Sub API enabled
- `gcloud` CLI installed and authenticated
- OAuth 2.0 credentials downloaded as `credentials.json`

### 3. Account Management

Use the GUI account manager to add Gmail accounts:
```bash
python account_manager.py
```

### 4. Easy Launch

Use the launcher for an interactive experience:
```bash
python launcher.py
```

Or launch components directly:
```bash
# Configure accounts with GUI
python account_manager.py

# Start monitoring (after accounts are configured)
python gmail_monitor.py

# Start monitoring with debug output
python gmail_monitor.py --debug
```

## Account Management GUI

The Account Manager provides a user-friendly interface to:

- **Add Gmail Accounts**: Enter name and email, then authenticate with Google
- **View Current Accounts**: See all configured accounts in a table
- **Remove Accounts**: Delete accounts and optionally their associated files
- **Live Logging**: Real-time feedback during authentication and operations
- **Automatic File Management**: Token and history files are automatically numbered and managed

### Adding an Account

1. Run `python account_manager.py`
2. Enter account name and Gmail address
3. Click "Add Account & Authenticate"
4. Complete Google OAuth in your browser
5. Account is automatically saved and ready for monitoring

### Account Configuration File

Accounts are stored in `accounts_config.json`:
```json
[
  {
    "name": "Primary Account",
    "email": "user@gmail.com",
    "token_file": "token1.json",
    "history_file": "history1.txt"
  }
]
```

## How It Works

### Authentication Flow
1. Each account uses the same `credentials.json` OAuth client
2. Individual `token_*.json` files store per-account access tokens  
3. Tokens are automatically refreshed when needed
4. The GUI handles all authentication steps automatically

### Real-time Monitoring
1. Gmail Watch API sends notifications to the Pub/Sub topic when emails arrive
2. The script subscribes to the Pub/Sub topic and receives notifications
3. When a notification arrives, it identifies which account it belongs to
4. The Gmail History API is used to fetch new messages since the last check
5. New emails are displayed in rich terminal panels with account identification

### Duplicate Prevention
- **History ID Tracking**: Tracks the last processed Gmail history ID per account
- **Message ID Tracking**: Tracks the last seen message ID per account
- **Display Deduplication**: Maintains a global set of displayed message IDs

## Configuration

### Environment Variables

The application uses a `.env` file to store configuration:

```env
# GCP Project ID (automatically set by setup_gcp.bat)
GCP_PROJECT_ID=your-project-id-here
```

**Note:** The `.env` file is automatically created when you run `setup_gcp.bat`. Other configuration values (Pub/Sub topic and subscription IDs) remain in the code as they are typically static for a project.

### Manual Configuration

If you need to manually set the GCP Project ID, create a `.env` file in the project root:

```bash
echo GCP_PROJECT_ID=your-project-id-here > .env
```

## File Structure

```
gmail-monitor2/
├── .env                     # Environment variables (auto-generated)
├── .env.example            # Example environment file
├── credentials.json         # Global OAuth credentials (shared)
├── accounts_config.json     # Account configuration (auto-generated)
├── gmail_monitor.py        # Main monitoring script
├── account_manager.py      # GUI account management
├── launcher.py             # Interactive launcher
├── setup_env.bat           # Environment setup script
├── setup_gcp.bat           # GCP setup launcher (batch)
├── setup_gcp.ps1           # GCP setup script (PowerShell)
├── requirements.txt        # Python dependencies
├── token1.json             # OAuth tokens for account 1
├── token2.json             # OAuth tokens for account 2
├── history1.txt            # Last history ID for account 1
└── history2.txt            # Last history ID for account 2
```

## Adding More Test Accounts

Since all accounts are test users in the same Google Cloud project:

1. **No additional credentials needed** - just use the same `credentials.json`
2. **Add to configuration**:
   ```python
   {
       'name': 'Test User 3',
       'email': 'testuser3@gmail.com',
       'token_file': 'token_testuser3.json',
       'history_file': 'history_testuser3.txt'
   }
   ```
3. **Run the script** - it will automatically prompt for OAuth for the new account
4. **Done!** The new account will be monitored alongside the others

## Troubleshooting

### Gmail API Quotas
- The script is designed to be quota-efficient
- Uses history API instead of polling for messages
- Implements smart deduplication

### Pub/Sub Issues
- Ensure your GCP project has Pub/Sub API enabled
- Verify topic and subscription names match your configuration
- Check IAM permissions for the service account

### Authentication Issues
- Delete token files and re-authenticate if you see auth errors
- Ensure `credentials.json` is from the correct GCP project
- Make sure Gmail API is enabled for your project

## Example Output

```
┌─ Multi-Account Gmail Monitor Active ────────────────────────────────────┐
│ 🔄 Listening for messages on subscription:                              │
│ projects/gmail-monitor-463406/subscriptions/gmail-realtime-subscriber   │
│                                                                          │
│ 📧 Monitoring 3 accounts:                                               │
│   • Primary Account (your-primary-email@gmail.com)                      │
│   • Test User 1 (testuser1@gmail.com)                                   │
│   • Test User 2 (testuser2@gmail.com)                                   │
│                                                                          │
│ 💤 Quiet mode: ON (use --debug for verbose output)                      │
└──────────────────────────────────────────────────────────────────────────┘

┌─ 📧 New Email Detected! ─────────────────────────────────────────────────┐
│ Account: Test User 1                                                     │
│ To: testuser1@gmail.com                                                  │
│ From: sender@example.com                                                 │
│ Subject: Test Email                                                      │
│ Date: Mon, 01 Jan 2024 12:00:00 +0000                                   │
│ Received: 2024-01-01 12:00:00                                           │
│ Snippet: This is a test email message...                                │
└──────────────────────────────────────────────────────────────────────────┘
```

This setup makes it incredibly easy to monitor multiple test Gmail accounts with a single script and minimal configuration!
