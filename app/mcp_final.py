"""
Final MCP Server Implementation - Simplified and Working
Based on successful implementations research
"""

from flask import Blueprint, request, jsonify, Response
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

mcp_final_bp = Blueprint('mcp_final', __name__)

# Server configuration
SERVER_INFO = {
    "name": "meta-ads-server",
    "version": "1.0.0"
}


@mcp_final_bp.route('/', methods=['GET', 'POST', 'OPTIONS'])
def handle_request():
    """Main endpoint handling all MCP requests"""
    
    # Handle CORS
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
    
    # Handle GET - Server discovery
    if request.method == 'GET':
        logger.info("GET request - returning server info")
        return jsonify({
            "mcp": "1.0",
            "name": SERVER_INFO["name"],
            "version": SERVER_INFO["version"],
            "description": "Meta Ads connector for Claude",
            "capabilities": {
                "tools": True
            }
        })
    
    # Handle POST - JSON-RPC requests
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }), 400
        
        method = data.get('method')
        params = data.get('params', {})
        msg_id = data.get('id')
        
        logger.info(f"Processing: {method} (id={msg_id})")
        logger.debug(f"Full request: {json.dumps(data)}")
        
        # Route methods
        if method == 'initialize':
            result = handle_initialize(params)
        elif method == 'initialized':
            logger.info("Client initialized successfully")
            return '', 204
        elif method == 'tools/list':
            result = handle_list_tools()
        elif method == 'tools/call':
            result = handle_call_tool(params)
        else:
            logger.warning(f"Unknown method: {method}")
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
                "id": msg_id
            })
        
        response = {
            "jsonrpc": "2.0",
            "result": result
        }
        
        if msg_id is not None:
            response["id"] = msg_id
        
        logger.debug(f"Response: {json.dumps(response)}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": data.get('id') if 'data' in locals() else None
        }), 500


def handle_initialize(params: Dict) -> Dict:
    """Initialize the connection"""
    protocol_version = params.get('protocolVersion', '2024-11-05')
    
    logger.info(f"Initializing with protocol {protocol_version}")
    
    return {
        "protocolVersion": protocol_version,
        "capabilities": {
            "tools": {}
        },
        "serverInfo": SERVER_INFO
    }


def handle_list_tools() -> Dict:
    """List available tools"""
    tools = [
        {
            "name": "get_ads_overview",
            "description": "Get Meta Ads account overview with key metrics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 30)",
                        "default": 30
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_campaigns",
            "description": "List Meta Ads campaigns with performance data",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: all, active, paused",
                        "default": "all"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_ad_performance",
            "description": "Get detailed ad performance metrics",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]
    
    logger.info(f"Returning {len(tools)} tools")
    return {"tools": tools}


def handle_call_tool(params: Dict) -> Dict:
    """Execute a tool"""
    tool_name = params.get('name')
    arguments = params.get('arguments', {})
    
    logger.info(f"Executing tool: {tool_name}")
    
    # Simple tool implementations with demo data
    if tool_name == 'get_ads_overview':
        days = arguments.get('days', 30)
        result = {
            "period": f"Last {days} days",
            "account": "Meta Ads Account",
            "spend": "$15,234.56",
            "revenue": "$76,172.80",
            "roas": "5.0x",
            "impressions": "2.4M",
            "clicks": "48.2K",
            "ctr": "2.0%",
            "conversions": "1,524",
            "cpc": "$0.32"
        }
        
    elif tool_name == 'get_campaigns':
        status = arguments.get('status', 'all')
        result = {
            "filter": status,
            "total": 3,
            "campaigns": [
                {
                    "name": "Summer Sale 2024",
                    "status": "active",
                    "spend": "$5,234.56",
                    "roas": "6.2x",
                    "clicks": "18.5K"
                },
                {
                    "name": "Brand Awareness",
                    "status": "active",
                    "spend": "$4,567.89",
                    "roas": "4.8x",
                    "clicks": "15.2K"
                },
                {
                    "name": "Holiday Campaign",
                    "status": "paused",
                    "spend": "$5,432.11",
                    "roas": "4.5x",
                    "clicks": "14.5K"
                }
            ]
        }
        
    elif tool_name == 'get_ad_performance':
        result = {
            "top_performing_ads": [
                {
                    "ad_name": "Video Ad - Product Demo",
                    "impressions": "850K",
                    "clicks": "17K",
                    "ctr": "2.0%",
                    "conversions": "340",
                    "roas": "7.2x"
                },
                {
                    "ad_name": "Carousel - Features",
                    "impressions": "650K",
                    "clicks": "11.7K",
                    "ctr": "1.8%",
                    "conversions": "234",
                    "roas": "5.8x"
                }
            ],
            "insights": "Video ads performing 24% better than static images"
        }
        
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    # Return in the format Claude expects
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, indent=2)
            }
        ]
    }


# Additional endpoints for discovery
@mcp_final_bp.route('/health')
def health():
    """Health check"""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@mcp_final_bp.route('/.well-known/mcp')
def well_known():
    """Well-known MCP discovery endpoint"""
    return jsonify({
        "mcp_version": "1.0",
        "server": SERVER_INFO,
        "capabilities": ["tools"],
        "endpoints": {
            "main": "/",
            "health": "/health"
        }
    })