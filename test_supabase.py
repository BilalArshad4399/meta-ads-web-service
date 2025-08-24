#!/usr/bin/env python
"""
Test script for Supabase connection
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test basic Supabase connection"""
    try:
        from app.supabase_client import SupabaseClient
        
        print("Testing Supabase connection...")
        client = SupabaseClient.get_client()
        print("✅ Successfully connected to Supabase!")
        
        # Test database access
        result = client.table('users').select('*').limit(1).execute()
        print(f"✅ Database access working!")
        
        return True
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        print("\nPlease check:")
        print("1. SUPABASE_URL is set correctly")
        print("2. SUPABASE_ANON_KEY is set correctly")
        print("3. Tables are created in Supabase (run supabase_schema.sql)")
        return False

def test_user_operations():
    """Test user CRUD operations"""
    try:
        from app.models import User
        import uuid
        
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        print(f"\nTesting user operations with email: {test_email}")
        
        # Test creating a user
        user = User.create(test_email, 'Test User', 'test_password')
        
        if user and user.id:
            print(f"✅ User created successfully!")
            print(f"   User ID: {user.id}")
            
            # Test retrieving the user
            retrieved = User.get_by_email(test_email)
            if retrieved:
                print(f"✅ User retrieved successfully!")
                
                # Test password verification
                if retrieved.check_password('test_password'):
                    print(f"✅ Password verification working!")
                
                # Clean up test user
                from app.supabase_client import SupabaseClient
                client = SupabaseClient.get_client()
                client.table('users').delete().eq('email', test_email).execute()
                print(f"✅ Test user cleaned up")
                
                return True
            else:
                print(f"❌ Failed to retrieve user")
                return False
        else:
            print(f"❌ Failed to create user")
            return False
            
    except Exception as e:
        print(f"❌ Error during user operations test: {e}")
        return False

def main():
    print("=" * 50)
    print("Supabase Connection Test")
    print("=" * 50)
    
    # Check environment variables
    print("\nChecking environment variables...")
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # Test connection
    if test_supabase_connection():
        print("\n" + "=" * 50)
        # Test user operations
        test_user_operations()
    
    print("\n" + "=" * 50)
    print("Test complete!")
    print("=" * 50)

if __name__ == "__main__":
    main()