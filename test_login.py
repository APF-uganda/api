#!/usr/bin/env python3
"""
Test complete login flow with OTP
"""
import requests
import json

def test_complete_login():
    # Step 1: Login to get OTP
    login_url = "http://localhost:8000/api/v1/auth/login/"
    login_data = {
        "email": "admin@apf.com",
        "password": "admin123"
    }
    
    print("Step 1: Login to get OTP")
    print(f"URL: {login_url}")
    print(f"Data: {login_data}")
    
    try:
        login_response = requests.post(login_url, json=login_data)
        print(f"Status Code: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            session_id = login_result.get('session_id')
            otp_code = login_result.get('otp_code')  # For development only
            
            if session_id and otp_code:
                print(f"\nStep 2: Verify OTP")
                
                # Step 2: Verify OTP to get JWT tokens
                verify_url = "http://localhost:8000/api/v1/auth/verify-otp/"
                verify_data = {
                    "session_id": session_id,
                    "otp": otp_code,
                    "remember_me": False
                }
                
                print(f"URL: {verify_url}")
                print(f"Data: {verify_data}")
                
                verify_response = requests.post(verify_url, json=verify_data)
                print(f"Status Code: {verify_response.status_code}")
                print(f"Response: {verify_response.text}")
                
                if verify_response.status_code == 200:
                    verify_result = verify_response.json()
                    access_token = verify_result.get('access')
                    
                    if access_token:
                        print(f"\nStep 3: Test applications endpoint with JWT token")
                        
                        # Step 3: Test applications endpoint with JWT token
                        headers = {"Authorization": f"Bearer {access_token}"}
                        apps_response = requests.get("http://localhost:8000/api/v1/applications/", headers=headers)
                        print(f"Applications Status: {apps_response.status_code}")
                        
                        if apps_response.status_code == 200:
                            apps_data = apps_response.json()
                            print(f"SUCCESS! Number of applications: {len(apps_data)}")
                            if apps_data:
                                print("First application:")
                                print(json.dumps(apps_data[0], indent=2))
                        else:
                            print(f"Applications Error: {apps_response.text}")
                    else:
                        print("No access token in verify response")
                else:
                    print(f"OTP verification failed: {verify_response.text}")
            else:
                print("No session_id or otp_code in login response")
        else:
            print(f"Login failed: {login_response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_complete_login()