#!/usr/bin/env python3
"""
Test script for unified MCP server
Tests both unauthenticated and authenticated flows
"""

import requests
import json
import sys

# Use local server for testing
BASE_URL = "http://localhost:8080"

def test_endpoint(name, method, url, headers=None, data=None):
    """Test a single endpoint"""
    print(f"\n=== Testing {name} ===")
    print(f"{method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "HEAD":
            response = requests.head(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            print(f"Unknown method: {method}")
            return False
        
        print(f"Status: {response.status_code}")
        
        if response.text and method != "HEAD":
            try:
                body = json.loads(response.text)
                print(f"Body: {json.dumps(body, indent=2)}")
            except:
                print(f"Body (text): {response.text[:500]}")
        
        return response.status_code < 400
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def get_auth_token():
    """Get an authentication token via OAuth flow"""
    print("\n=== Getting Auth Token ===")
    
    # Step 1: Get authorization code
    auth_response = requests.get(f"{BASE_URL}/oauth/authorize", params={
        "client_id": "test-client",
        "response_type": "code",
        "state": "test-state"
    }, allow_redirects=False)
    
    if auth_response.status_code == 302:
        # Parse redirect URL for code
        location = auth_response.headers.get('Location', '')
        if 'code=' in location:
            code = location.split('code=')[1].split('&')[0]
        else:
            # If no redirect, get code from JSON response
            auth_response = requests.get(f"{BASE_URL}/oauth/authorize", params={
                "client_id": "test-client",
                "response_type": "code",
                "state": "test-state"
            })
            code = auth_response.json().get('code')
    else:
        code = auth_response.json().get('code')
    
    print(f"Got authorization code: {code[:20]}...")
    
    # Step 2: Exchange code for token
    token_response = requests.post(f"{BASE_URL}/oauth/token", json={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": "test-client"
    })
    
    if token_response.status_code == 200:
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        print(f"Got access token: {access_token[:20]}...")
        return access_token
    else:
        print(f"Failed to get token: {token_response.text}")
        return None

def main():
    """Run all tests"""
    print("Testing Unified MCP Server")
    print("=" * 50)
    
    results = []
    
    # Test 1: Root GET (discovery)
    results.append(test_endpoint(
        "Root GET (Discovery)",
        "GET",
        f"{BASE_URL}/",
        headers={"Accept": "application/json"}
    ))
    
    # Test 2: Root HEAD
    results.append(test_endpoint(
        "Root HEAD",
        "HEAD",
        f"{BASE_URL}/"
    ))
    
    # Test 3: MCP Manifest
    results.append(test_endpoint(
        "MCP Manifest",
        "GET",
        f"{BASE_URL}/mcp.json"
    ))
    
    # Test 4: OAuth Discovery
    results.append(test_endpoint(
        "OAuth Discovery",
        "GET",
        f"{BASE_URL}/.well-known/oauth-authorization-server"
    ))
    
    # Test 5: Initialize (unauthenticated)
    results.append(test_endpoint(
        "Initialize (Unauthenticated)",
        "POST",
        f"{BASE_URL}/",
        headers={"Content-Type": "application/json"},
        data={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
    ))
    
    # Test 6: Tools List (should require auth)
    results.append(test_endpoint(
        "Tools List (Unauthenticated - expect 401)",
        "POST",
        f"{BASE_URL}/",
        headers={"Content-Type": "application/json"},
        data={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
    ))
    
    # Get auth token for authenticated tests
    token = get_auth_token()
    
    if token:
        # Test 7: Initialize (authenticated)
        results.append(test_endpoint(
            "Initialize (Authenticated)",
            "POST",
            f"{BASE_URL}/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            data={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                },
                "id": 3
            }
        ))
        
        # Test 8: Tools List (authenticated)
        results.append(test_endpoint(
            "Tools List (Authenticated)",
            "POST",
            f"{BASE_URL}/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            data={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 4
            }
        ))
        
        # Test 9: Tool Call (authenticated)
        results.append(test_endpoint(
            "Tool Call - get_meta_ads_overview",
            "POST",
            f"{BASE_URL}/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            },
            data={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_meta_ads_overview",
                    "arguments": {
                        "date_range": "last_30_days"
                    }
                },
                "id": 5
            }
        ))
    
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    
    for i, result in enumerate(results, 1):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"Test {i}: {status}")
    
    total = len(results)
    passed = sum(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())