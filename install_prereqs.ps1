# This script automates the installation of prerequisites for the Gmail Watcher project on Windows.
# It uses the winget package manager and PowerShell.
# 
# IMPORTANT: This script should be run as Administrator for winget installations to work properly.

param(
    [switch]$SkipAuth = $false
)

# Set error action preference to stop on errors
$ErrorActionPreference = "Stop"

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to restart script as administrator
function Start-AsAdministrator {
    if (-not (Test-Administrator)) {
        Write-Status "This script requires administrator privileges for package installations." "WARNING"
        Write-Status "Attempting to restart as administrator..." "INFO"
        
        $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`""
        if ($SkipAuth) {
            $arguments += " -SkipAuth"
        }
        
        try {
            Start-Process PowerShell -Verb RunAs -ArgumentList $arguments
            exit 0
        }
        catch {
            Write-Status "Failed to restart as administrator. Please run this script as administrator manually." "ERROR"
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
}

# Function to write colored output
function Write-Status {
    param(
        [string]$Message,
        [ValidateSet("INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG", "IMPORTANT")]
        [string]$Level = "INFO"
    )
    
    $color = switch ($Level) {
        "INFO" { "Cyan" }
        "SUCCESS" { "Green" }
        "WARNING" { "Yellow" }
        "ERROR" { "Red" }
        "DEBUG" { "Gray" }
        "IMPORTANT" { "Magenta" }
    }
    
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

# Function to check if a command exists
function Test-Command {
    param([string]$CommandName)
    
    try {
        Get-Command $CommandName -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to run a command and check its exit code
function Invoke-SafeCommand {
    param(
        [string]$Command,
        [string[]]$Arguments = @(),
        [string]$SuccessMessage,
        [string]$ErrorMessage,
        [switch]$SuppressOutput = $false
    )
    
    try {
        if ($SuppressOutput) {
            $result = & $Command @Arguments 2>$null
        } else {
            $result = & $Command @Arguments
        }
        
        if ($LASTEXITCODE -eq 0) {
            if ($SuccessMessage) {
                Write-Status $SuccessMessage "SUCCESS"
            }
            return $true
        } else {
            if ($ErrorMessage) {
                Write-Status $ErrorMessage "ERROR"
            }
            return $false
        }
    }
    catch {
        if ($ErrorMessage) {
            Write-Status "$ErrorMessage Error: $($_.Exception.Message)" "ERROR"
        }
        return $false
    }
}

# Function to install a package using winget
function Install-WingetPackage {
    param(
        [string]$PackageId,
        [string]$PackageName,
        [string]$PostInstallMessage = ""
    )
    
    Write-Status "Installing $PackageName..." "INFO"
    Write-Status "This may take a few minutes. Please wait..." "DEBUG"
    
    try {
        # Use direct winget command with better error handling
        $process = Start-Process -FilePath "winget" -ArgumentList @("install", "-e", "--id", $PackageId, "--silent", "--accept-package-agreements", "--accept-source-agreements") -PassThru -Wait -NoNewWindow -RedirectStandardOutput "winget_output.tmp" -RedirectStandardError "winget_error.tmp"
        
        $exitCode = $process.ExitCode
        $output = ""
        $errorOutput = ""
        
        if (Test-Path "winget_output.tmp") {
            $output = Get-Content "winget_output.tmp" -Raw
            Remove-Item "winget_output.tmp" -Force -ErrorAction SilentlyContinue
        }
        
        if (Test-Path "winget_error.tmp") {
            $errorOutput = Get-Content "winget_error.tmp" -Raw
            Remove-Item "winget_error.tmp" -Force -ErrorAction SilentlyContinue
        }
        
        if ($exitCode -eq 0) {
            Write-Status "$PackageName installation completed." "SUCCESS"
            if ($PostInstallMessage) {
                Write-Status $PostInstallMessage "IMPORTANT"
            }
            return $true
        } else {
            Write-Status "$PackageName installation failed (exit code: $exitCode)." "ERROR"
            if ($errorOutput -and $errorOutput.Trim() -ne "") {
                Write-Status "Error details: $($errorOutput.Trim())" "DEBUG"
            }
            if ($output -and $output.Trim() -ne "") {
                Write-Status "Output: $($output.Trim())" "DEBUG"
            }
            return $false
        }
    }
    catch {
        Write-Status "$PackageName installation failed with exception: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Main script execution
Write-Status "Starting prerequisite setup for Windows..." "INFO"
Write-Status "This script will attempt to install Python and Google Cloud SDK." "INFO"
Write-Host

# Check for administrator privileges
Start-AsAdministrator

# 1. Check for winget
Write-Status "Checking for winget (Windows Package Manager)..." "INFO"

if (-not (Test-Command "winget")) {
    Write-Status "winget is not found or not working properly." "ERROR"
    Write-Status "Please install it from the Microsoft Store (search for 'App Installer')" "ERROR"
    Write-Status "or visit https://aka.ms/getwinget" "ERROR"
    Write-Status "You may also need to restart your terminal after installation." "ERROR"
    Read-Host "Press Enter to exit"
    exit 1
}

$wingetVersion = winget --version 2>$null
Write-Status "winget is available (version: $wingetVersion)" "SUCCESS"
Write-Host

# 2. Install Tools
Write-Status "Starting tool checks..." "DEBUG"

# Check and install Python
Write-Status "Checking for python..." "DEBUG"
if (Test-Command "python") {
    $pythonVersion = python --version 2>$null
    Write-Status "python is already installed ($pythonVersion)" "SUCCESS"
} else {
    Write-Status "python not found. Installing..." "INFO"
    $pythonInstalled = Install-WingetPackage -PackageId "Python.Python.3" -PackageName "Python" `
        -PostInstallMessage "If this is a new installation, you may need to restart your PowerShell session for 'python' to be available in the PATH."
}

# Check and install pip
Write-Status "Checking for pip..." "DEBUG"
if (Test-Command "pip") {
    $pipVersion = pip --version 2>$null
    Write-Status "pip is already installed ($pipVersion)" "SUCCESS"
} else {
    Write-Status "Python's package manager 'pip' should have been installed with Python. If not, please reinstall Python." "INFO"
    Write-Status "pip check completed." "SUCCESS"
}

# Check and install Google Cloud SDK
Write-Status "Checking for gcloud..." "DEBUG"
if (Test-Command "gcloud") {
    Write-Status "gcloud is already installed" "SUCCESS"
} else {
    Write-Status "gcloud not found. Installing..." "INFO"
    $gcloudInstalled = Install-WingetPackage -PackageId "Google.CloudSDK" -PackageName "Google Cloud SDK" `
        -PostInstallMessage @"
The Google Cloud SDK installer may launch. Please follow the on-screen instructions.
Ensure you leave the options to add the SDK to your PATH checked!
After the installer finishes, you may need to RESTART this PowerShell session.
"@
}

Write-Status "All tool checks completed" "DEBUG"

# 3. Final Authentication Step (unless skipped)
if (-not $SkipAuth) {
    Write-Host
    Write-Status "All prerequisite checks completed. The final step is to authenticate with Google." "INFO"
    Write-Status "A browser window will now open for you to log in to your Google Account." "INFO"
    Write-Host

    Write-Status "Starting Google Cloud authentication..." "INFO"
    $authSuccess = Invoke-SafeCommand -Command "gcloud" -Arguments @("auth", "login") `
        -ErrorMessage "Google Cloud authentication failed."

    if ($authSuccess) {
        Write-Status "Setting up application default credentials..." "INFO"
        $adcSuccess = Invoke-SafeCommand -Command "gcloud" -Arguments @("auth", "application-default", "login") `
            -ErrorMessage "Application default credentials setup failed."

        if ($adcSuccess) {
            Write-Host
            Write-Status "Authentication successful!" "SUCCESS"
            Write-Status "Prerequisite setup is complete. You can now proceed with your Gmail monitor setup." "SUCCESS"
        } else {
            Write-Host
            Write-Status "Authentication failed. Please run 'gcloud auth login' and 'gcloud auth application-default login' manually." "ERROR"
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Write-Host
        Write-Status "Authentication failed. Please run 'gcloud auth login' manually." "ERROR"
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host
    Write-Status "Authentication skipped (--SkipAuth flag used)." "WARNING"
    Write-Status "Remember to run 'gcloud auth login' and 'gcloud auth application-default login' before using the Gmail watcher." "INFO"
}

Write-Host
Read-Host "Press Enter to exit"
