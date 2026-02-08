"""
Interactive script to help set up MTN MoMo API credentials.
This script guides you through the process and tests your configuration.
"""
import os
import sys
import uuid
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

def generate_uuid():
    """Generate a new UUID."""
    return str(uuid.uuid4())

def create_api_user(subscription_key, api_user_id, callback_host="webhook.site"):
    """
    Create MTN API User in sandbox.
    
    Args:
        subscription_key: MTN subscription key
        api_user_id: UUID for the API user
        callback_host: Callback host for webhooks
    
    Returns:
        True if successful, False otherwise
    """
    url = "https://sandbox.momodeveloper.mtn.com/v1_0/apiuser"
    
    headers = {
        "X-Reference-Id": api_user_id,
        "Ocp-Apim-Subscription-Key": subscription_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "providerCallbackHost": callback_host
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 201:
            return True
        elif response.status_code == 409:
            print_info("API User already exists (this is okay)")
            return True
        else:
            print_error(f"Failed to create API User: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Error creating API User: {e}")
        return False

def generate_api_key(subscription_key, api_user_id):
    """
    Generate API Key for the API User.
    
    Args:
        subscription_key: MTN subscription key
        api_user_id: UUID of the API user
    
    Returns:
        API key if successful, None otherwise
    """
    url = f"https://sandbox.momodeveloper.mtn.com/v1_0/apiuser/{api_user_id}/apikey"
    
    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=10)
        
        if response.status_code == 201:
            data = response.json()
            return data.get("apiKey")
        else:
            print_error(f"Failed to generate API Key: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print_error(f"Error generating API Key: {e}")
        return None

def test_authentication(subscription_key, api_user_id, api_key):
    """
    Test authentication with MTN API.
    
    Args:
        subscription_key: MTN subscription key
        api_user_id: API user ID
        api_key: API key
    
    Returns:
        True if successful, False otherwise
    """
    import base64
    
    url = "https://sandbox.momodeveloper.mtn.com/collection/token/"
    
    # Create Basic Auth header
    credentials = f"{api_user_id}:{api_key}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Ocp-Apim-Subscription-Key": subscription_key
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print_success(f"Authentication successful!")
            print_info(f"Access Token: {token[:30]}...")
            return True
        else:
            print_error(f"Authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Error testing authentication: {e}")
        return False

def update_env_file(subscription_key, api_user_id, api_key):
    """
    Update the .env file with MTN credentials.
    
    Args:
        subscription_key: MTN subscription key
        api_user_id: API user ID
        api_key: API key
    """
    env_path = Path(__file__).parent / ".env"
    
    # Read existing .env file
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update or add MTN credentials
    mtn_vars = {
        "MTN_SUBSCRIPTION_KEY": subscription_key,
        "MTN_API_USER": api_user_id,
        "MTN_API_KEY": api_key,
        "PAYMENT_ENVIRONMENT": "sandbox"
    }
    
    updated_lines = []
    updated_keys = set()
    
    for line in lines:
        updated = False
        for key, value in mtn_vars.items():
            if line.startswith(f"{key}="):
                updated_lines.append(f"{key}={value}\n")
                updated_keys.add(key)
                updated = True
                break
        if not updated:
            updated_lines.append(line)
    
    # Add any missing keys
    for key, value in mtn_vars.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Write back to .env
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    print_success(f"Updated {env_path}")

def main():
    """Main setup flow."""
    print_header("MTN MoMo API Credentials Setup")
    
    print("This script will help you set up MTN MoMo API credentials for sandbox testing.")
    print("\nYou'll need:")
    print("  1. MTN Developer account (https://momodeveloper.mtn.com/)")
    print("  2. Subscription to Collections product (Sandbox)")
    print("  3. Your Subscription Key (Primary Key)")
    
    input("\nPress Enter to continue...")
    
    # Step 1: Get Subscription Key
    print_step(1, "Enter Your Subscription Key")
    print("Log in to MTN Developer Portal and get your Primary Subscription Key")
    print("from the Collections product subscription.")
    
    subscription_key = input("\nEnter your MTN Subscription Key: ").strip()
    
    if not subscription_key:
        print_error("Subscription key is required!")
        return
    
    print_success("Subscription key received")
    
    # Step 2: Generate or Enter API User ID
    print_step(2, "API User ID")
    print("You can either:")
    print("  1. Generate a new UUID (recommended for first-time setup)")
    print("  2. Enter an existing API User ID")
    
    choice = input("\nGenerate new UUID? (y/n): ").strip().lower()
    
    if choice == 'y':
        api_user_id = generate_uuid()
        print_success(f"Generated API User ID: {api_user_id}")
    else:
        api_user_id = input("Enter your existing API User ID: ").strip()
        if not api_user_id:
            print_error("API User ID is required!")
            return
    
    # Step 3: Create API User
    print_step(3, "Create API User in MTN Sandbox")
    print("Creating API User with MTN...")
    
    if create_api_user(subscription_key, api_user_id):
        print_success("API User created successfully!")
    else:
        print_error("Failed to create API User. Please check your subscription key.")
        return
    
    # Step 4: Generate API Key
    print_step(4, "Generate API Key")
    print("Generating API Key...")
    
    api_key = generate_api_key(subscription_key, api_user_id)
    
    if api_key:
        print_success(f"API Key generated: {api_key}")
    else:
        print_error("Failed to generate API Key.")
        return
    
    # Step 5: Test Authentication
    print_step(5, "Test Authentication")
    print("Testing authentication with MTN API...")
    
    if test_authentication(subscription_key, api_user_id, api_key):
        print_success("All credentials are working correctly!")
    else:
        print_error("Authentication test failed. Please verify your credentials.")
        return
    
    # Step 6: Update .env file
    print_step(6, "Update Environment File")
    
    update_choice = input("\nUpdate Backend/.env file with these credentials? (y/n): ").strip().lower()
    
    if update_choice == 'y':
        update_env_file(subscription_key, api_user_id, api_key)
        print_success("Environment file updated!")
    else:
        print_info("Skipped updating .env file")
        print("\nAdd these to your Backend/.env file manually:")
        print(f"MTN_SUBSCRIPTION_KEY={subscription_key}")
        print(f"MTN_API_USER={api_user_id}")
        print(f"MTN_API_KEY={api_key}")
        print(f"PAYMENT_ENVIRONMENT=sandbox")
    
    # Summary
    print_header("Setup Complete!")
    
    print("Your MTN MoMo API credentials are configured:")
    print(f"  Subscription Key: {subscription_key[:20]}...")
    print(f"  API User ID: {api_user_id}")
    print(f"  API Key: {api_key[:20]}...")
    print(f"  Environment: sandbox")
    
    print("\nNext steps:")
    print("  1. Run: python verify_payments_setup.py")
    print("  2. Start your Django server: python manage.py runserver")
    print("  3. Test payments using sandbox phone numbers:")
    print("     - 256774000001 (will approve)")
    print("     - 256774000002 (will reject)")
    print("     - 256774000003 (will timeout)")
    
    print("\nFor detailed documentation, see:")
    print("  Backend/MTN_MOMO_API_SETUP_GUIDE.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
