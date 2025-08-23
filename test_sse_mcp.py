#!/usr/bin/env python3
"""
Test SSE MCP Server Implementation
"""

import requests
import json
import sys
import threading
import time

# For local testing
BASE_URL = "http://localhost:8082"

# For production testing
# BASE_URL = "https://deep-audy-wotbix-9060bbad.koyeb.app"


def test_sse_connection():
    """Test SSE connection"""
    print("\n=== Testing SSE Connection ===")
    try:
        response = requests.get(f"{BASE_URL}/sse", stream=True, timeout=5)
        print(f"Status: {response.status_code}")
        
        connection_id = response.headers.get('X-Connection-Id')
        print(f"Connection ID: {connection_id}")
        
        # Read first event
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(f"First event: {data}")
                    break
        
        return connection_id
    except Exception as e:
        print(f"SSE Error: {e}")
        return None


def test_mcp_request(name, message, connection_id=None):
    """Send MCP request"""
    print(f"\n=== {name} ===")
    
    headers = {"Content-Type": "application/json"}
    if connection_id:
        headers["X-Connection-Id"] = connection_id
    
    print(f"Request: {json.dumps(message, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/",
            json=message,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        
        if response.text and response.status_code != 204:
            body = json.loads(response.text)
            print(f"Response: {json.dumps(body, indent=2)}")
            return response.status_code == 200 and 'result' in body
        else:
            return response.status_code == 204
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run SSE MCP tests"""
    print("Testing SSE MCP Server")
    print("=" * 50)
    
    results = []
    
    # Test 1: Server info
    print("\n=== Server Info ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        results.append(response.status_code == 200)
    except Exception as e:
        print(f"Error: {e}")
        results.append(False)
    
    # Test 2: Initialize
    results.append(test_mcp_request(
        "Initialize",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
    ))
    
    # Test 3: Initialized notification
    results.append(test_mcp_request(
        "Initialized Notification",
        {
            "jsonrpc": "2.0",
            "method": "initialized"
        }
    ))
    
    # Test 4: List tools
    results.append(test_mcp_request(
        "List Tools",
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
    ))
    
    # Test 5: Call tool
    results.append(test_mcp_request(
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
    
    # Test 6: Ping
    results.append(test_mcp_request(
        "Ping",
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "ping",
            "params": {}
        }
    ))
    
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)
    
    test_names = [
        "Server Info",
        "Initialize",
        "Initialized",
        "List Tools",
        "Call Tool",
        "Ping"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results), 1):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"Test {i} ({name}): {status}")
    
    total = len(results)
    passed = sum(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ Server is ready for Claude!")
    else:
        print("\n⚠️ Some tests failed.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())