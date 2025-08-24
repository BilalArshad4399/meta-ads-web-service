#!/usr/bin/env python
"""Test Flask app startup"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing Flask app initialization...")

try:
    from app import create_app
    print("✅ App module imported successfully")
    
    app = create_app()
    print("✅ App created successfully")
    
    with app.test_client() as client:
        # Test signup endpoint
        import json
        
        test_data = {
            'email': 'test_flask@example.com',
            'password': 'testpass123',
            'name': 'Flask Test'
        }
        
        print("\nTesting /auth/signup endpoint...")
        response = client.post('/auth/signup', 
                              data=json.dumps(test_data),
                              content_type='application/json')
        
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.get_json()}")
        
        # Clean up if successful
        if response.status_code == 200:
            from app.supabase_client import SupabaseClient
            client_sb = SupabaseClient.get_client(use_service_role=True)
            client_sb.table('users').delete().eq('email', 'test_flask@example.com').execute()
            print("✅ Test user cleaned up")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()