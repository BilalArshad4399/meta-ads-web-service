#!/usr/bin/env python
"""Test deployment signup"""

import requests
import json
import uuid

def test_deployment_signup():
    """Test signup on deployed app"""
    
    base_url = "https://deep-audy-wotbix-9060bbad.koyeb.app"
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    print(f"Testing signup at: {base_url}")
    print(f"Test email: {test_email}")
    
    # Test signup
    signup_data = {
        'email': test_email,
        'password': 'testpass123',
        'name': 'Test User'
    }
    
    try:
        response = requests.post(
            f"{base_url}/auth/signup",
            json=signup_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Signup successful!")
        else:
            print("❌ Signup failed")
            
            # Try to get more info
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Raw response: {response.text}")
                
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

if __name__ == "__main__":
    test_deployment_signup()