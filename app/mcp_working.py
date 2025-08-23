"""
MCP Server that actually works with Claude
Based on working implementations and Claude's actual requirements
"""

from flask import Blueprint, request, jsonify, Response
import json
import logging

logger = logging.getLogger(__name__)
mcp_working_bp = Blueprint('mcp_working', __name__)


@mcp_working_bp.route('/', methods=['GET', 'POST', 'OPTIONS', 'HEAD'])
def mcp_handler():
    """Single endpoint handling all MCP communication"""
    
    # CORS headers for all responses
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, HEAD',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS (CORS preflight)
    if request.method == 'OPTIONS':
        return '', 204, headers
    
    # Handle HEAD (connection check)
    if request.method == 'HEAD':
        return '', 200, headers
    
    # Handle GET (server info)
    if request.method == 'GET':
        return jsonify({
            "mcp": {
                "version": "1.0.0",
                "name": "zane-meta-ads",
                "description": "Meta Ads connector for Claude"
            }
        }), 200, headers
    
    # Handle POST (JSON-RPC)
    try:
        data = request.get_json(force=True)
        method = data.get('method')
        params = data.get('params', {})
        msg_id = data.get('id')
        
        logger.info(f"MCP Request: {method}")
        
        # Initialize connection
        if method == 'initialize':
            result = {
                "protocolVersion": params.get('protocolVersion', '2024-11-05'),
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "zane-meta-ads",
                    "version": "1.0.0"
                }
            }
        
        # Client ready notification
        elif method == 'initialized':
            return '', 204, headers
        
        # List available tools
        elif method == 'tools/list':
            result = {
                "tools": [
                    {
                        "name": "get_meta_ads_metrics",
                        "description": "Get Meta Ads metrics and performance data",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "get_campaign_data",
                        "description": "Get campaign performance information",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        
        # Execute tool
        elif method == 'tools/call':
            tool = params.get('name')
            
            if tool == 'get_meta_ads_metrics':
                content = {
                    "account": "Meta Ads Account #12345",
                    "period": "Last 30 days",
                    "total_spend": "$24,532",
                    "total_revenue": "$122,660",
                    "roas": "5.0x",
                    "campaigns_active": 12,
                    "top_campaign": "Summer Sale 2024",
                    "impressions": "2.4M",
                    "clicks": "48.2K"
                }
            elif tool == 'get_campaign_data':
                content = {
                    "campaigns": [
                        {"name": "Summer Sale", "spend": "$8,765", "roas": "6.2x", "status": "Active"},
                        {"name": "Brand Awareness", "spend": "$6,543", "roas": "4.8x", "status": "Active"},
                        {"name": "Holiday Preview", "spend": "$5,432", "roas": "4.5x", "status": "Paused"}
                    ]
                }
            else:
                content = {"error": f"Unknown tool: {tool}"}
            
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(content, indent=2)
                    }
                ]
            }
        
        # Unknown method
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": msg_id
            }), 404, headers
        
        # Return successful response
        response = {
            "jsonrpc": "2.0",
            "result": result
        }
        if msg_id is not None:
            response["id"] = msg_id
            
        return jsonify(response), 200, headers
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": data.get('id') if 'data' in locals() else None
        }), 500, headers


@mcp_working_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})