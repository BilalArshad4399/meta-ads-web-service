#!/usr/bin/env python3
"""Test MCP server locally"""

from app import create_app
import json

app = create_app()

# Test client
with app.test_client() as client:
    print("Testing MCP Server Locally\n" + "="*50)
    
    # Test 1: GET root
    print("\n1. GET /")
    response = client.get('/')
    print(f"Status: {response.status_code}")
    print(f"Body: {json.dumps(response.json, indent=2)}")
    
    # Test 2: Initialize
    print("\n2. POST / (initialize)")
    response = client.post('/', json={
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
        "id": 1
    })
    print(f"Status: {response.status_code}")
    print(f"Body: {json.dumps(response.json, indent=2)}")
    
    # Test 3: List tools
    print("\n3. POST / (tools/list)")
    response = client.post('/', json={
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    })
    print(f"Status: {response.status_code}")
    print(f"Body: {json.dumps(response.json, indent=2)[:500]}...")
    
    # Test 4: Call tool
    print("\n4. POST / (tools/call)")
    response = client.post('/', json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_meta_ads_overview",
            "arguments": {"date_range": "last_7_days"}
        },
        "id": 3
    })
    print(f"Status: {response.status_code}")
    print(f"Body: {json.dumps(response.json, indent=2)[:500]}...")
    
    print("\n" + "="*50)
    print("All tests completed successfully!")