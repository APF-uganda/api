"""
Interactive script to help set up Airtel Money API credentials.
This script guides you through the process and tests your configuration.
"""
import os
import sys
import requests
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def print_step(number, text):
    """Print a step number."""
    print(f"\n[Step {number}] {text}")
    print("-" * 70)

def print_success(text):
    """Print success message."""
    print(f"✓ {text}")

def print_error(text):
    """Print error message."""
    print(f"✗ {text}")

def print_info(text):
    """Print info message."""
    print(f"ℹ {text}")

def print_warning(text):
    """Print warning message."""
    print(f"⚠ {text}")

def test_authentication(client_id, client_secret, environment="sandbox"):
    """
    Test authentication with Airtel API.
    
    Args:
        client_id: Airtel client ID
        client_secret: Airtel client secret
        environment: 'sandbox' or 'production'
    
    Returns:
        True if successful, False otherwise
    """
    if environment == "production":
        base_url = "https://openapi.airtel.africa"
    else:
        base_url = "https://openapiuat.airtel.africa"
    
    url = f"{base_url}/auth/oauth2/token"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            expires_in = data.get("expires_in", 0)
            
            print_success(f"Authentication successful!")
            print_info(f"Access Token: {token[:30]}...")
            print_info(f"Token expires in: {expires_in} seconds ({expires_in // 3600} hours)")
            return True
        else:
            print_error(f"Authentication failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data}")
            except:
                print(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Error testing authentication: {e}")
        return False

def update_env_file(client_id, client_secret, environment="sandbox"):
    """
    Update the .env file with Airtel credentials.
    
    Args:
        client_id: Airtel client ID
        client_secret: Airtel client secret
        environment: 'sandbox' or 'production'
    """
    env_path = Path(__file__).parent / ".env"
    
    # Read existing .env file
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update or add Airtel credentials
    airtel_vars = {
        "AIRTEL_CLIENT_ID": client_id,
        "AIRTEL_CLIENT_SECRET": client_secret,
        "PAYMENT_ENVIRONMENT": environment
    }
    
    updated_lines = []
    updated_keys = set()
    
    for line in lines:
        updated = False
        for key, value in airtel_vars.items():
            if line.startswith(f"{key}="):
                updated_lines.append(f"{key}={value}\n")
                updated_keys.add(key)
                updated = True
                break
        if not updated:
            updated_lines.append(line)
    
    # Add any missing keys
    for key, value in airtel_vars.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Write back to .env
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    print_success(f"Updated {env_path}")

def display_instructions():
    """Display instructions for getting Airtel credentials."""
    print("\n📋 How to Get Airtel Money API Credentials:")
    print("\n1. Go to: https://developers.airtel.africa/")
    print("2. Sign up or log in to your account")
    print("3. Navigate to 'My Apps' or 'Applications'")
    print("4. Click 'Create New App' or 'Add Application'")
    print("5. Fill in the application details:")
    print("   - Name: APF Portal")
    print("   - Description: Payment integration for membership portal")
    print("   - Category: Financial Services")
    print("   - Country: Uganda")
    print("   - Product: Collections (for receiving payments)")
    print("   - Environment: UAT/Sandbox")
    print("6. Submit and wait for approval (usually instant for sandbox)")
    print("7. Go to your app and find the 'Credentials' section")
    print("8. Copy your Client ID and Client Secret")

def main():
    """Main setup flow."""
    print_header("Airtel Money API Credentials Setup")
    
    print("This script will help you set up Airtel Money API credentials for sandbox testing.")
    print("\nYou'll need:")
    print("  1. Airtel Developer account (https://developers.airtel.africa/)")
    print("  2. An application created in the developer portal")
    print("  3. Your Client ID and Client Secret")
    
    # Ask if user needs instructions
    need_help = input("\nDo you need instructions on how to get credentials? (y/n): ").strip().lower()
    
    if need_help == 'y':
        display_instructions()
        input("\nPress Enter when you have your credentials ready...")
    
    # Step 1: Get Client ID
    print_step(1, "Enter Your Client ID")
    print("From the Airtel Developer Portal, copy your application's Client ID")
    print("(Also called App ID or API Key)")
    
    client_id = input("\nEnter your Airtel Client ID: ").strip()
    
    if not client_id:
        print_error("Client ID is required!")
        return
    
    print_success("Client ID received")
    
    # Step 2: Get Client Secret
    print_step(2, "Enter Your Client Secret")
    print("From the Airtel Developer Portal, copy your application's Client Secret")
    print("(Also called App Secret or API Secret)")
    
    client_secret = input("\nEnter your Airtel Client Secret: ").strip()
    
    if not client_secret:
        print_error("Client Secret is required!")
        return
    
    print_success("Client Secret received")
    
    # Step 3: Choose Environment
    print_step(3, "Choose Environment")
    print("Which environment are these credentials for?")
    print("  1. Sandbox/UAT (for testing)")
    print("  2. Production (for live transactions)")
    
    env_choice = input("\nEnter choice (1 or 2) [default: 1]: ").strip() or "1"
    
    if env_choice == "2":
        environment = "production"
        print_warning("Using PRODUCTION environment!")
    else:
        environment = "sandbox"
        print_info("Using SANDBOX environment")
    
    # Step 4: Test Authentication
    print_step(4, "Test Authentication")
    print("Testing authentication with Airtel API...")
    
    if test_authentication(client_id, client_secret, environment):
        print_success("All credentials are working correctly!")
    else:
        print_error("Authentication test failed. Please verify your credentials.")
        
        retry = input("\nDo you want to try again with different credentials? (y/n): ").strip().lower()
        if retry == 'y':
            main()
        return
    
    # Step 5: Update .env file
    print_step(5, "Update Environment File")
    
    update_choice = input("\nUpdate Backend/.env file with these credentials? (y/n): ").strip().lower()
    
    if update_choice == 'y':
        update_env_file(client_id, client_secret, environment)
        print_success("Environment file updated!")
    else:
        print_info("Skipped updating .env file")
        print("\nAdd these to your Backend/.env file manually:")
        print(f"AIRTEL_CLIENT_ID={client_id}")
        print(f"AIRTEL_CLIENT_SECRET={client_secret}")
        print(f"PAYMENT_ENVIRONMENT={environment}")
    
    # Summary
    print_header("Setup Complete!")
    
    print("Your Airtel Money API credentials are configured:")
    print(f"  Client ID: {client_id[:20]}...")
    print(f"  Client Secret: {client_secret[:20]}...")
    print(f"  Environment: {environment}")
    
    print("\nNext steps:")
    print("  1. Run: python verify_payments_setup.py")
    print("  2. Start your Django server: python manage.py runserver")
    
    if environment == "sandbox":
        print("  3. Test payments using sandbox phone numbers:")
        print("     - 256700000001 (will approve)")
        print("     - 256700000002 (will reject - insufficient funds)")
        print("     - 256700000003 (will timeout)")
        print("\n  Note: Test numbers may vary. Check Airtel documentation for current numbers.")
    else:
        print("  3. Test with real phone numbers (charges will apply)")
    
    print("\nFor detailed documentation, see:")
    print("  Backend/AIRTEL_MONEY_API_SETUP_GUIDE.md")
    
    # Additional tips
    print("\n💡 Pro Tips:")
    print("  - Airtel tokens are valid for 2 hours (vs MTN's 1 hour)")
    print("  - Phone numbers are auto-formatted (country code stripped)")
    print("  - Your app supports automatic provider detection (MTN/Airtel)")
    print("  - Set up both MTN and Airtel for complete payment coverage")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
