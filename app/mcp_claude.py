"""
MCP Server Implementation for Claude
Follows the exact Claude MCP specification
"""

from flask import Blueprint, request, jsonify, Response, make_response
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
mcp_claude_bp = Blueprint('mcp_claude', __name__)

# Store server state
server_info = {
    "name": "meta-ads-mcp",
    "version": "1.0.0",
    "protocolVersion": "2024-11-05"  # Claude still uses this version
}


@mcp_claude_bp.route('/', methods=['POST'])
def handle_mcp_message():
    """
    Main MCP endpoint - handles JSON-RPC messages from Claude
    """
    try:
        # Parse the JSON-RPC message
        message = request.get_json()
        if not message:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            }), 400
        
        method = message.get('method')
        params = message.get('params', {})
        msg_id = message.get('id')
        
        logger.info(f"MCP: Received {method} with id={msg_id}, params={params}")
        
        # Route to appropriate handler
        if method == 'initialize':
            result = handle_initialize(params)
        elif method == 'initialized':
            # This is a notification from Claude that it's ready
            logger.info("MCP: Client initialized successfully")
            return '', 204  # No response for notifications
        elif method == 'tools/list':
            result = handle_list_tools()
        elif method == 'tools/call':
            result = handle_call_tool(params)
        else:
            logger.warning(f"MCP: Unknown method {method}")
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": msg_id
            })
        
        # Return successful response
        response = {
            "jsonrpc": "2.0",
            "result": result
        }
        
        # Only include id if it was provided (not for notifications)
        if msg_id is not None:
            response["id"] = msg_id
        
        logger.info(f"MCP: Sending response for {method}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"MCP Error: {e}", exc_info=True)
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": message.get('id') if 'message' in locals() else None
        }), 500


def handle_initialize(params: Dict) -> Dict:
    """
    Handle initialization request from Claude
    Must return server capabilities
    """
    client_info = params.get('clientInfo', {})
    protocol_version = params.get('protocolVersion', '2024-11-05')
    
    logger.info(f"MCP: Initializing with client {client_info.get('name', 'unknown')}")
    
    # Return server capabilities
    return {
        "protocolVersion": protocol_version,  # Echo back the client's version
        "capabilities": {
            "tools": {},  # We support tools
            # Don't include resources or prompts unless you implement them
        },
        "serverInfo": {
            "name": server_info["name"],
            "version": server_info["version"]
        }
    }


def handle_list_tools() -> Dict:
    """
    Return the list of available tools
    This is what Claude will show in the UI
    """
    tools = [
        {
            "name": "get_meta_ads_overview",
            "description": "Get an overview of Meta Ads account performance including spend, revenue, ROAS, and other key metrics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "description": "Date range for the data (e.g., 'last_7_days', 'last_30_days', 'last_90_days')",
                        "enum": ["last_7_days", "last_30_days", "last_90_days"],
                        "default": "last_30_days"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_campaign_performance",
            "description": "Get detailed performance metrics for Meta Ads campaigns",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of campaigns to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Metric to sort campaigns by",
                        "enum": ["spend", "roas", "clicks", "impressions"],
                        "default": "spend"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_ad_insights",
            "description": "Get detailed insights for ads including demographic breakdowns",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to get insights for (optional)"
                    },
                    "breakdown": {
                        "type": "string",
                        "description": "How to break down the data",
                        "enum": ["age", "gender", "placement", "device", "none"],
                        "default": "none"
                    }
                },
                "required": []
            }
        }
    ]
    
    logger.info(f"MCP: Returning {len(tools)} tools")
    return {"tools": tools}


def handle_call_tool(params: Dict) -> Dict:
    """
    Execute a tool and return results
    """
    tool_name = params.get('name')
    arguments = params.get('arguments', {})
    
    logger.info(f"MCP: Calling tool {tool_name} with arguments {arguments}")
    
    # Route to specific tool handler
    if tool_name == 'get_meta_ads_overview':
        result = get_meta_ads_overview(arguments)
    elif tool_name == 'get_campaign_performance':
        result = get_campaign_performance(arguments)
    elif tool_name == 'get_ad_insights':
        result = get_ad_insights(arguments)
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


def get_meta_ads_overview(args: Dict) -> Dict:
    """Get Meta Ads account overview"""
    date_range = args.get('date_range', 'last_30_days')
    
    # Demo data - replace with actual Meta API calls
    return {
        "status": "success",
        "date_range": date_range,
        "account_id": "act_123456789",
        "currency": "USD",
        "metrics": {
            "total_spend": 15678.43,
            "total_revenue": 78392.15,
            "roas": 5.0,
            "total_purchases": 1234,
            "cost_per_purchase": 12.71,
            "impressions": 2456789,
            "clicks": 45678,
            "ctr": 1.86,
            "cpc": 0.34,
            "cpm": 6.38
        },
        "top_campaign": {
            "name": "Summer Sale 2024",
            "spend": 5432.10,
            "roas": 6.2
        },
        "trend": "Performance is up 15% compared to previous period"
    }


def get_campaign_performance(args: Dict) -> Dict:
    """Get campaign performance data"""
    limit = args.get('limit', 10)
    sort_by = args.get('sort_by', 'spend')
    
    # Demo data
    campaigns = []
    for i in range(min(limit, 5)):
        campaigns.append({
            "campaign_id": f"camp_{1000+i}",
            "campaign_name": f"Campaign {chr(65+i)}",
            "status": "ACTIVE" if i < 3 else "PAUSED",
            "objective": "CONVERSIONS",
            "spend": round(5000 - i * 800, 2),
            "revenue": round(25000 - i * 3000, 2),
            "roas": round(5.0 - i * 0.5, 2),
            "purchases": 250 - i * 30,
            "impressions": 500000 - i * 50000,
            "clicks": 10000 - i * 1000,
            "ctr": round(2.0 - i * 0.1, 2),
            "cpc": round(0.50 + i * 0.05, 2)
        })
    
    # Sort by requested metric
    if sort_by in ['spend', 'roas', 'clicks', 'impressions']:
        campaigns.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
    
    return {
        "status": "success",
        "campaign_count": len(campaigns),
        "sorted_by": sort_by,
        "campaigns": campaigns
    }


def get_ad_insights(args: Dict) -> Dict:
    """Get ad insights with breakdowns"""
    campaign_id = args.get('campaign_id')
    breakdown = args.get('breakdown', 'none')
    
    result = {
        "status": "success",
        "campaign_id": campaign_id or "all_campaigns",
        "breakdown_type": breakdown,
        "overall_metrics": {
            "impressions": 1234567,
            "clicks": 23456,
            "ctr": 1.90,
            "spend": 8765.43,
            "conversions": 456,
            "conversion_rate": 1.94,
            "cpc": 0.37,
            "cost_per_conversion": 19.22
        }
    }
    
    # Add breakdown data if requested
    if breakdown == 'age':
        result['breakdown_data'] = [
            {"age_range": "18-24", "impressions": 234567, "clicks": 4567, "ctr": 1.95, "conversions": 89},
            {"age_range": "25-34", "impressions": 456789, "clicks": 9123, "ctr": 2.00, "conversions": 178},
            {"age_range": "35-44", "impressions": 345678, "clicks": 6234, "ctr": 1.80, "conversions": 123},
            {"age_range": "45-54", "impressions": 123456, "clicks": 2345, "ctr": 1.90, "conversions": 45},
            {"age_range": "55+", "impressions": 74567, "clicks": 1187, "ctr": 1.59, "conversions": 21}
        ]
    elif breakdown == 'gender':
        result['breakdown_data'] = [
            {"gender": "female", "impressions": 734567, "clicks": 14234, "ctr": 1.94, "conversions": 278},
            {"gender": "male", "impressions": 500000, "clicks": 9222, "ctr": 1.84, "conversions": 178}
        ]
    elif breakdown == 'device':
        result['breakdown_data'] = [
            {"device": "mobile", "impressions": 934567, "clicks": 18234, "ctr": 1.95, "conversions": 367},
            {"device": "desktop", "impressions": 200000, "clicks": 4222, "ctr": 2.11, "conversions": 78},
            {"device": "tablet", "impressions": 100000, "clicks": 1000, "ctr": 1.00, "conversions": 11}
        ]
    elif breakdown == 'placement':
        result['breakdown_data'] = [
            {"placement": "facebook_feed", "impressions": 534567, "clicks": 11234, "ctr": 2.10, "conversions": 234},
            {"placement": "instagram_feed", "impressions": 400000, "clicks": 7600, "ctr": 1.90, "conversions": 156},
            {"placement": "instagram_stories", "impressions": 200000, "clicks": 3622, "ctr": 1.81, "conversions": 56},
            {"placement": "audience_network", "impressions": 100000, "clicks": 1000, "ctr": 1.00, "conversions": 10}
        ]
    
    return result


# Additional endpoints that Claude might check
@mcp_claude_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "server": server_info["name"],
        "version": server_info["version"],
        "timestamp": datetime.utcnow().isoformat()
    })


@mcp_claude_bp.route('/', methods=['GET'])
def server_info_endpoint():
    """Return server information for GET requests"""
    return jsonify({
        "type": "mcp_server",
        "name": server_info["name"],
        "version": server_info["version"],
        "protocol": "mcp",
        "protocolVersion": server_info["protocolVersion"],
        "description": "Meta Ads MCP Server for Claude"
    })