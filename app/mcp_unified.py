"""
Unified MCP Server Implementation
Combines OAuth flow with proper MCP protocol handling
Implements the 2025-06-18 specification
"""

from flask import Blueprint, request, jsonify, Response, make_response, redirect
import json
import jwt
import os
import uuid
from datetime import datetime, timedelta
from app.models import User
from app import db
import logging
import hashlib
import base64
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

mcp_unified_bp = Blueprint('mcp_unified', __name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')
BASE_URL = os.getenv('BASE_URL', 'https://deep-audy-wotbix-9060bbad.koyeb.app')

# Store active sessions
active_sessions = {}


@mcp_unified_bp.route('/', methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
def mcp_root():
    """
    Main MCP endpoint - handles all protocol messages
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = make_response('', 204)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, HEAD, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
    # Handle HEAD for discovery
    if request.method == 'HEAD':
        response = make_response('', 200)
        response.headers['X-MCP-Version'] = '2025-06-18'
        response.headers['X-MCP-Transport'] = 'http'
        return response
    
    # Handle GET - return server info with OAuth endpoints
    if request.method == 'GET':
        return jsonify({
            "name": "Zane - Meta Ads Connector",
            "version": "1.0.0",
            "protocol": "mcp",
            "protocolVersion": "2025-06-18",
            "transport": "http",
            "description": "Connect Claude to your Meta Ads accounts",
            "oauth": {
                "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
                "token_endpoint": f"{BASE_URL}/oauth/token"
            }
        })
    
    # Handle POST - MCP protocol messages
    try:
        # Get the JSON-RPC message
        message = request.get_json()
        if not message:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }), 400
        
        method = message.get('method')
        params = message.get('params', {})
        msg_id = message.get('id')
        
        logger.info(f"MCP: Received {method} with id={msg_id}")
        
        # Check authentication for protected methods
        auth_header = request.headers.get('Authorization', '')
        user = None
        
        # Methods that don't require auth
        public_methods = ['initialize', 'initialized']
        
        if method not in public_methods:
            # Require authentication
            if not auth_header or not auth_header.startswith('Bearer '):
                # For tools/list and tools/call, require auth
                logger.info(f"MCP: {method} requires authentication")
                response = make_response('', 401)
                response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}", authorization_uri="{BASE_URL}/oauth/authorize", token_uri="{BASE_URL}/oauth/token"'
                return response
            
            # Verify token
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                user_id = payload.get('user_id')
                user = User.query.get(user_id)
                if not user:
                    logger.error(f"User not found: {user_id}")
                    return jsonify({
                        "jsonrpc": "2.0",
                        "error": {"code": -32000, "message": "Invalid user"},
                        "id": msg_id
                    }), 401
            except jwt.InvalidTokenError as e:
                logger.error(f"Invalid token: {e}")
                response = make_response('', 401)
                response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}"'
                return response
        
        # Handle methods
        if method == 'initialize':
            result = handle_initialize(params, user)
        elif method == 'initialized':
            # This is a notification, no response needed
            logger.info("Client initialized notification received")
            return '', 204
        elif method == 'tools/list':
            result = handle_tools_list(params, user)
        elif method == 'tools/call':
            result = handle_tool_call(params, user)
        elif method == 'ping':
            result = {}  # Ping returns empty object
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
        
        logger.info(f"MCP: Returning response for {method}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"MCP Error: {e}", exc_info=True)
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": message.get('id') if 'message' in locals() else None
        }), 500


def handle_initialize(params, user):
    """Handle initialize request"""
    protocol_version = params.get('protocolVersion', '2025-06-18')
    client_info = params.get('clientInfo', {})
    
    logger.info(f"Initializing MCP: protocol={protocol_version}, authenticated={user is not None}")
    
    # Build response based on auth status
    response = {
        "protocolVersion": protocol_version,
        "capabilities": {
            "tools": {},
            "resources": {},
            "prompts": {}
        },
        "serverInfo": {
            "name": "Zane - Meta Ads Connector",
            "version": "1.0.0"
        }
    }
    
    # If not authenticated, indicate auth is required
    if not user:
        response["authRequired"] = True
        response["authUrl"] = f"{BASE_URL}/oauth/authorize"
    
    return response


def handle_tools_list(params, user):
    """Return list of available tools"""
    if not user:
        raise ValueError("Authentication required")
    
    logger.info(f"Listing tools for user: {user.email}")
    
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


def handle_tool_call(params, user):
    """Execute a tool and return results"""
    if not user:
        raise ValueError("Authentication required")
    
    tool_name = params.get('name')
    arguments = params.get('arguments', {})
    
    logger.info(f"User {user.email} calling tool: {tool_name} with args: {arguments}")
    
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


@mcp_unified_bp.route('/mcp.json')
def mcp_manifest():
    """MCP manifest endpoint"""
    return jsonify({
        "name": "Zane - Meta Ads Connector",
        "version": "1.0.0",
        "description": "Connect Claude to your Meta Ads accounts",
        "protocol": "mcp",
        "protocolVersion": "2025-06-18",
        "transport": "http",
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False
        },
        "authentication": {
            "type": "oauth2",
            "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
            "token_endpoint": f"{BASE_URL}/oauth/token"
        }
    })


@mcp_unified_bp.route('/.well-known/oauth-authorization-server')
def oauth_discovery():
    """OAuth 2.0 authorization server metadata"""
    return jsonify({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "token_endpoint_auth_methods_supported": ["none"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "scopes_supported": ["mcp:read", "mcp:write"],
        "service_documentation": "https://modelcontextprotocol.io"
    })


@mcp_unified_bp.route('/oauth/authorize')
def oauth_authorize():
    """OAuth authorization endpoint"""
    client_id = request.args.get('client_id', 'claude')
    redirect_uri = request.args.get('redirect_uri', '')
    state = request.args.get('state', '')
    response_type = request.args.get('response_type', 'code')
    code_challenge = request.args.get('code_challenge')
    code_challenge_method = request.args.get('code_challenge_method', 'S256')
    
    logger.info(f"OAuth: Authorize request from {client_id} with redirect_uri: {redirect_uri}")
    
    # Get or create Claude user - auto-approve for Claude
    user = User.query.filter_by(email='claude@anthropic.com').first()
    if not user:
        user = User(email='claude@anthropic.com', name='Claude AI')
        user.set_password('claude-mcp-integration')
        user.api_key = str(uuid.uuid4())
        db.session.add(user)
        db.session.commit()
        logger.info(f"OAuth: Created Claude user with ID {user.id}")
    
    if response_type == 'code':
        # Generate authorization code
        code_payload = {
            'type': 'auth_code',
            'client_id': client_id,
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(minutes=10)
        }
        
        if code_challenge:
            code_payload['code_challenge'] = code_challenge
            code_payload['code_challenge_method'] = code_challenge_method
        
        code = jwt.encode(code_payload, JWT_SECRET, algorithm='HS256')
        
        logger.info(f"OAuth: Issuing code for user {user.id}, redirecting to: {redirect_uri}")
        
        # ALWAYS redirect if redirect_uri is provided (Claude expects this)
        if redirect_uri:
            params = {'code': code}
            if state:
                params['state'] = state
            separator = '&' if '?' in redirect_uri else '?'
            redirect_url = f"{redirect_uri}{separator}{urlencode(params)}"
            logger.info(f"OAuth: Redirecting to {redirect_url}")
            return redirect(redirect_url)
        else:
            # Fallback for testing
            return jsonify({"code": code, "state": state})
    
    return jsonify({"error": "unsupported_response_type"}), 400


@mcp_unified_bp.route('/oauth/token', methods=['POST', 'OPTIONS'])
def oauth_token():
    """OAuth token endpoint"""
    if request.method == 'OPTIONS':
        response = make_response('', 204)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    # Parse request data (handle both JSON and form-encoded)
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()
    
    grant_type = data.get('grant_type')
    logger.info(f"OAuth: Token request with grant_type={grant_type}")
    
    if grant_type == 'authorization_code':
        code = data.get('code')
        if not code:
            return jsonify({"error": "invalid_request", "error_description": "Missing code"}), 400
        
        try:
            # Verify code
            payload = jwt.decode(code, JWT_SECRET, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            # Verify PKCE if present
            if 'code_challenge' in payload:
                code_verifier = data.get('code_verifier')
                if not code_verifier:
                    return jsonify({"error": "invalid_request", "error_description": "Missing code_verifier"}), 400
                
                if payload.get('code_challenge_method') == 'S256':
                    challenge = base64.urlsafe_b64encode(
                        hashlib.sha256(code_verifier.encode()).digest()
                    ).decode().rstrip('=')
                else:
                    challenge = code_verifier
                
                if challenge != payload.get('code_challenge'):
                    logger.error("OAuth: PKCE verification failed")
                    return jsonify({"error": "invalid_grant", "error_description": "Invalid code_verifier"}), 400
            
            # Generate access token
            access_token = jwt.encode({
                'user_id': user_id,
                'type': 'access_token',
                'exp': datetime.utcnow() + timedelta(days=365)
            }, JWT_SECRET, algorithm='HS256')
            
            logger.info(f"OAuth: Issued token for user {user_id}")
            
            return jsonify({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 31536000,
                "scope": "mcp:read mcp:write"
            })
            
        except jwt.InvalidTokenError as e:
            logger.error(f"OAuth: Invalid code - {e}")
            return jsonify({"error": "invalid_grant", "error_description": "Invalid code"}), 400
    
    return jsonify({"error": "unsupported_grant_type"}), 400


@mcp_unified_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Zane MCP Server",
        "timestamp": datetime.utcnow().isoformat()
    })