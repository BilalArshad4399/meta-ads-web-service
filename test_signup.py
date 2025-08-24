#!/usr/bin/env python
"""Test signup functionality directly"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import User
import uuid

def test_signup():
    """Test user signup"""
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    test_name = "Test User"
    test_password = "testpass123"
    
    print(f"Testing signup with email: {test_email}")
    
    try:
        # Check if user exists
        existing = User.get_by_email(test_email)
        if existing:
            print("❌ User already exists")
            return False
        
        # Create user
        print("Creating user...")
        user = User.create(test_email, test_name, test_password)
        
        if user and user.id:
            print(f"✅ User created successfully!")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Name: {user.name}")
            print(f"   API Key: {user.api_key}")
            
            # Test login
            print("\nTesting login...")
            login_user = User.get_by_email(test_email)
            if login_user and login_user.check_password(test_password):
                print("✅ Login successful!")
            else:
                print("❌ Login failed")
            
            # Clean up
            from app.supabase_client import SupabaseClient
            client = SupabaseClient.get_client(use_service_role=True)
            client.table('users').delete().eq('email', test_email).execute()
            print("✅ Test user cleaned up")
            
            return True
        else:
            print(f"❌ Failed to create user - no ID returned")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_signup()
    sys.exit(0 if success else 1)