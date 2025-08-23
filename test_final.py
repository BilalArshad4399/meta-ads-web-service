#!/usr/bin/env python3
"""Test the final MCP implementation"""

import requests
import json

# Change to your deployed URL
BASE_URL = "https://deep-audy-wotbix-9060bbad.koyeb.app"

def test(name, method, url, data=None):
    print(f"\n=== {name} ===")
    try:
        if method == "GET":
            r = requests.get(url)
        else:
            r = requests.post(url, json=data, headers={"Content-Type": "application/json"})
        
        print(f"Status: {r.status_code}")
        if r.text:
            print(f"Response: {json.dumps(r.json(), indent=2)}")
        return r.status_code in [200, 204]
    except Exception as e:
        print(f"Error: {e}")
        return False

# Tests
print("Testing MCP Server")
print("=" * 50)

results = []

# 1. Discovery
results.append(test("Discovery", "GET", BASE_URL + "/"))

# 2. Initialize
results.append(test("Initialize", "POST", BASE_URL + "/", {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2024-11-05"}
}))

# 3. List tools
results.append(test("List Tools", "POST", BASE_URL + "/", {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
}))

# 4. Call tool
results.append(test("Call Tool", "POST", BASE_URL + "/", {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "get_ads_overview",
        "arguments": {"days": 7}
    }
}))

print("\n" + "=" * 50)
print(f"Results: {sum(results)}/{len(results)} passed")
print("\nTo connect in Claude:")
print(f"1. Go to Claude Settings > Connectors")
print(f"2. Add custom connector")
print(f"3. Enter URL: {BASE_URL}")
print(f"4. After connecting, ask Claude: 'What tools are available in the meta-ads-server connector?'")