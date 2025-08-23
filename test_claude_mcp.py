#!/usr/bin/env python3
"""
Test script for Claude MCP protocol
Tests the exact message flow Claude expects
"""

import requests
import json
import sys

# For local testing
BASE_URL = "http://localhost:8081"

# For production testing
# BASE_URL = "https://deep-audy-wotbix-9060bbad.koyeb.app"

def test_mcp_message(name, message):
    """Send a JSON-RPC message and print the response"""
    print(f"\n=== {name} ===")
    print(f"Request: {json.dumps(message, indent=2)}")
    
    try:
        response = requests.post(
            BASE_URL + "/",
            json=message,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.text:
            try:
                body = json.loads(response.text)
                print(f"Response: {json.dumps(body, indent=2)}")
                return response.status_code == 200 and 'result' in body
            except:
                print(f"Response (text): {response.text}")
                return response.status_code == 204  # For notifications
        else:
            return response.status_code == 204
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run Claude MCP protocol tests"""
    print("Testing Claude MCP Protocol")
    print("=" * 50)
    
    results = []
    
    # Test 1: Initialize (what Claude sends first)
    results.append(test_mcp_message(
        "Initialize",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "claude",
                    "version": "1.0.0"
                }
            }
        }
    ))
    
    # Test 2: Initialized notification (Claude sends after successful init)
    results.append(test_mcp_message(
        "Initialized Notification",
        {
            "jsonrpc": "2.0",
            "method": "initialized"
            # No id for notifications
        }
    ))
    
    # Test 3: List tools (Claude needs this to show tools in UI)
    results.append(test_mcp_message(
        "List Tools",
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
    ))
    
    # Test 4: Call a tool
    results.append(test_mcp_message(
        "Call Tool - get_meta_ads_overview",
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_meta_ads_overview",
                "arguments": {
                    "date_range": "last_30_days"
                }
            }
        }
    ))
    
    # Test 5: Call another tool with different params
    results.append(test_mcp_message(
        "Call Tool - get_campaign_performance",
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_campaign_performance",
                "arguments": {
                    "limit": 5,
                    "sort_by": "roas"
                }
            }
        }
    ))
    
    # Test 6: GET request for server info
    print("\n=== Server Info (GET) ===")
    try:
        response = requests.get(BASE_URL + "/")
        print(f"Status: {response.status_code}")
        if response.text:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        results.append(response.status_code == 200)
    except Exception as e:
        print(f"Error: {e}")
        results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    
    test_names = [
        "Initialize",
        "Initialized Notification",
        "List Tools",
        "Call Tool - Overview",
        "Call Tool - Campaigns",
        "Server Info GET"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results), 1):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"Test {i} ({name}): {status}")
    
    total = len(results)
    passed = sum(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! The server is ready for Claude.")
    else:
        print("\n⚠️ Some tests failed. Check the implementation.")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())