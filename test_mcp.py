#!/usr/bin/env python3
"""
Test script to verify MCP server endpoints
"""

import requests
import json
import sys

BASE_URL = "https://deep-audy-wotbix-9060bbad.koyeb.app"

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
        print(f"Headers: {dict(response.headers)}")
        
        if response.text and method != "HEAD":
            try:
                print(f"Body: {json.dumps(json.loads(response.text), indent=2)}")
            except:
                print(f"Body (text): {response.text[:500]}")
        
        return response.status_code < 400
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing MCP Server Endpoints")
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
    
    # Test 5: Unauthenticated Initialize
    results.append(test_endpoint(
        "Unauthenticated Initialize",
        "POST",
        f"{BASE_URL}/",
        headers={"Content-Type": "application/json"},
        data={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18"
            },
            "id": 1
        }
    ))
    
    # Test 6: Protected Resource (should return 401)
    results.append(test_endpoint(
        "Protected Resource (expect 401)",
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