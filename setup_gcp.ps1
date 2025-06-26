# PowerShell Script to Automate GCP Setup for Gmail Monitor

# --- Configuration ---
$TOPIC_ID = "gmail-realtime-feed"
$SUBSCRIPTION_ID = "gmail-realtime-subscriber"
$GMAIL_SERVICE_ACCOUNT = "serviceAccount:gmail-api-push@system.gserviceaccount.com"
$PUBLISHER_ROLE = "roles/pubsub.publisher"

# --- Script ---

# Prompt for the Google Cloud Project ID
$PROJECT_ID = Read-Host -Prompt "Please enter your Google Cloud Project ID"

if (-not $PROJECT_ID) {
    Write-Host "Project ID cannot be empty. Exiting." -ForegroundColor Red
    exit
}

Write-Host "-----------------------------------------------------"
Write-Host "Starting GCP setup for project: $PROJECT_ID"
Write-Host "-----------------------------------------------------"

# 1. Create the Pub/Sub Topic
Write-Host "Step 1: Creating Pub/Sub topic '$TOPIC_ID'..." -ForegroundColor Yellow
try {
    gcloud pubsub topics create $TOPIC_ID --project=$PROJECT_ID --quiet
    Write-Host "Successfully created topic: $TOPIC_ID" -ForegroundColor Green
} catch {
    Write-Host "Error creating Pub/Sub topic. Please check your gcloud configuration and permissions." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit
}

# 2. Grant Gmail API publish permissions to the topic
Write-Host "\nStep 2: Granting Gmail permission to publish to the topic..." -ForegroundColor Yellow
try {
    gcloud pubsub topics add-iam-policy-binding $TOPIC_ID --project=$PROJECT_ID --member=$GMAIL_SERVICE_ACCOUNT --role=$PUBLISHER_ROLE --quiet
    Write-Host "Successfully granted permissions to the Gmail service account." -ForegroundColor Green
} catch {
    Write-Host "Error granting IAM permissions. Please check your gcloud configuration and permissions." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit
}

# 3. Create the Pub/Sub Subscription
Write-Host "\nStep 3: Creating Pub/Sub subscription '$SUBSCRIPTION_ID'..." -ForegroundColor Yellow
try {
    gcloud pubsub subscriptions create $SUBSCRIPTION_ID --project=$PROJECT_ID --topic=$TOPIC_ID --quiet
    Write-Host "Successfully created subscription: $SUBSCRIPTION_ID" -ForegroundColor Green
} catch {
    Write-Host "Error creating Pub/Sub subscription. Please check your gcloud configuration and permissions." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit
}

# 4. Save GCP Project ID to .env file
Write-Host "\nStep 4: Saving GCP Project ID to .env file..." -ForegroundColor Yellow
try {
    $envContent = "GCP_PROJECT_ID=$PROJECT_ID"
    $utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
    [System.IO.File]::WriteAllText(".env", $envContent, $utf8NoBomEncoding)
    Write-Host "Successfully saved GCP Project ID to .env file" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not save to .env file. You may need to set the project ID manually." -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host "\n-----------------------------------------------------"
Write-Host "GCP setup completed successfully!" -ForegroundColor Green
Write-Host "The following configuration has been set up:"
Write-Host "- GCP Project ID: $PROJECT_ID (saved to .env file)"
Write-Host "- Pub/Sub Topic: $TOPIC_ID"
Write-Host "- Pub/Sub Subscription: $SUBSCRIPTION_ID"
Write-Host ""
Write-Host "Your gmail_monitor.py will automatically load the project ID from .env"
Write-Host "-----------------------------------------------------"
