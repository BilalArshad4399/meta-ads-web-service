"""
Simplified MCP Server for Claude Integration
Implements minimal MCP protocol for HTTP transport
"""

from flask import Blueprint, request, jsonify, Response, make_response
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
mcp_simple_bp = Blueprint('mcp_simple', __name__)

BASE_URL = os.getenv('BASE_URL', 'https://deep-audy-wotbix-9060bbad.koyeb.app')

# Simple in-memory session storage
sessions = {}

@mcp_simple_bp.route('/', methods=['GET', 'POST', 'OPTIONS', 'HEAD'])
def mcp_endpoint():
    """Main MCP endpoint - handles all protocol messages"""
    
    # Handle CORS
    if request.method == 'OPTIONS':
        response = make_response('', 204)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, HEAD'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
    # Handle HEAD - for discovery
    if request.method == 'HEAD':
        response = make_response('', 200)
        response.headers['X-MCP-Version'] = '2025-06-18'
        return response
    
    # Handle GET - return capabilities
    if request.method == 'GET':
        return jsonify({
            "mcp": {
                "version": "2025-06-18",
                "name": "GoMarble Meta Ads",
                "description": "Connect to Meta Ads accounts"
            }
        })
    
    # Handle POST - JSON-RPC messages
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }), 400
        
        method = data.get('method')
        params = data.get('params', {})
        msg_id = data.get('id')
        
        logger.info(f"MCP request: method={method}, id={msg_id}")
        
        # Handle methods
        if method == 'initialize':
            result = handle_initialize(params)
        elif method == 'initialized':
            # This is a notification, no response needed
            logger.info("Client initialized")
            return '', 204
        elif method == 'tools/list':
            result = handle_tools_list(params)
        elif method == 'tools/call':
            result = handle_tool_call(params)
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": msg_id
            })
        
        # Return response
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": msg_id
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": data.get('id') if 'data' in locals() else None
        }), 500


def handle_initialize(params):
    """Handle initialize request"""
    protocol_version = params.get('protocolVersion', '2025-06-18')
    client_info = params.get('clientInfo', {})
    
    logger.info(f"Initializing MCP session: protocol={protocol_version}, client={client_info}")
    
    # Match the client's protocol version for compatibility
    supported_versions = ['2025-06-18', '2024-11-05']
    response_version = protocol_version if protocol_version in supported_versions else '2025-06-18'
    
    return {
        "protocolVersion": response_version,
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "GoMarble Meta Ads",
            "version": "1.0.0"
        }
    }


def handle_tools_list(params):
    """Return list of available tools"""
    logger.info("Listing available tools")
    
    tools = [
        {
            "name": "get_meta_ads_overview",
            "description": "Get overview of Meta Ads account performance including spend, ROAS, and key metrics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Meta Ads account ID (optional)"
                    },
                    "date_range": {
                        "type": "string",
                        "description": "Date range: last_7_days, last_30_days, last_90_days (default: last_30_days)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_campaign_performance",
            "description": "Get performance data for Meta Ads campaigns",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Meta Ads account ID"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Number of campaigns to return (default: 10)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_ad_insights",
            "description": "Get detailed insights for ads including CTR, CPC, CPM metrics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to get insights for"
                    },
                    "breakdown": {
                        "type": "string",
                        "description": "Breakdown by: age, gender, placement, device (optional)"
                    }
                },
                "required": []
            }
        }
    ]
    
    return {"tools": tools}


def handle_tool_call(params):
    """Execute a tool and return results"""
    tool_name = params.get('name')
    arguments = params.get('arguments', {})
    
    logger.info(f"Executing tool: {tool_name} with args: {arguments}")
    
    # Demo responses with realistic data
    if tool_name == 'get_meta_ads_overview':
        date_range = arguments.get('date_range', 'last_30_days')
        result = {
            "account_id": arguments.get('account_id', 'act_demo_12345'),
            "date_range": date_range,
            "currency": "USD",
            "metrics": {
                "total_spend": 24532.18,
                "total_revenue": 98128.72,
                "roas": 4.00,
                "impressions": 2456789,
                "clicks": 45678,
                "ctr": 1.86,
                "cpc": 0.54,
                "cpm": 9.98,
                "conversions": 3456,
                "conversion_rate": 7.56
            },
            "trend": "improving",
            "top_performing_campaign": "Summer Sale 2024"
        }
        
    elif tool_name == 'get_campaign_performance':
        limit = arguments.get('limit', 10)
        campaigns = []
        for i in range(min(limit, 5)):
            campaigns.append({
                "campaign_id": f"camp_{i+1:03d}",
                "campaign_name": f"Campaign {i+1}",
                "status": "ACTIVE" if i < 3 else "PAUSED",
                "spend": 5000 + i * 1000,
                "revenue": 20000 + i * 4000,
                "roas": 4.0 - i * 0.2,
                "impressions": 500000 - i * 50000,
                "clicks": 10000 - i * 1000
            })
        result = {
            "account_id": arguments.get('account_id', 'act_demo_12345'),
            "campaigns": campaigns,
            "total_campaigns": len(campaigns)
        }
        
    elif tool_name == 'get_ad_insights':
        breakdown = arguments.get('breakdown', 'none')
        result = {
            "campaign_id": arguments.get('campaign_id', 'camp_001'),
            "breakdown": breakdown,
            "insights": {
                "impressions": 345678,
                "clicks": 6789,
                "ctr": 1.96,
                "cpc": 0.48,
                "cpm": 9.42,
                "spend": 3257.72,
                "conversions": 234,
                "conversion_rate": 3.45
            }
        }
        if breakdown == 'age':
            result['breakdown_data'] = [
                {"age": "18-24", "impressions": 89000, "ctr": 2.1},
                {"age": "25-34", "impressions": 156000, "ctr": 1.95},
                {"age": "35-44", "impressions": 67000, "ctr": 1.85},
                {"age": "45+", "impressions": 33678, "ctr": 1.75}
            ]
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, indent=2)
            }
        ]
    }


@mcp_simple_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "GoMarble MCP Server",
        "timestamp": datetime.utcnow().isoformat()
    })


@mcp_simple_bp.route('/mcp.json')
def mcp_manifest():
    """MCP manifest endpoint - provides server configuration"""
    return jsonify({
        "name": "GoMarble Meta Ads Connector",
        "version": "1.0.0",
        "description": "Connect Claude to your Meta Ads accounts for real-time insights and management",
        "protocol": "mcp",
        "protocolVersion": "2025-06-18",
        "transport": "http",
        "serverUrl": BASE_URL,
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False
        },
        "tools": [
            {
                "name": "get_meta_ads_overview",
                "description": "Get overview of Meta Ads account performance"
            },
            {
                "name": "get_campaign_performance",
                "description": "Get performance data for Meta Ads campaigns"
            },
            {
                "name": "get_ad_insights",
                "description": "Get detailed insights for ads"
            }
        ]
    })