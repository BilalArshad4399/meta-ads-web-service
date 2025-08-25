"""
Fixed OAuth MCP implementation for Claude
This version ensures tools are properly exposed after OAuth
"""

from flask import Blueprint, jsonify, request, redirect, Response, make_response, render_template
import json
import jwt
import os
import uuid
from datetime import datetime, timedelta

oauth_mcp_fixed_bp = Blueprint('oauth_mcp_fixed', __name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')
BASE_URL = os.getenv('BASE_URL', 'https://deep-audy-wotbix-9060bbad.koyeb.app')

# Simple in-memory storage for active sessions
active_sessions = {}

def get_tools_list():
    """Return the list of available tools"""
    return [
        {
            "name": "get_meta_ads_overview",
            "description": "Get Meta Ads account overview and metrics",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_campaigns",
            "description": "Get list of Meta Ads campaigns with performance metrics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Number of campaigns to return (default: 10)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_account_metrics",
            "description": "Get detailed account metrics including ROAS, CTR, and spend",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "number",
                        "description": "Number of days to look back (default: 30)"
                    }
                },
                "required": []
            }
        }
    ]

def execute_tool(tool_name, arguments):
    """Execute a tool and return results"""
    if tool_name == "get_meta_ads_overview":
        return {
            "status": "connected",
            "account_name": "Demo Meta Ads Account",
            "total_spend": "$24,532",
            "total_revenue": "$122,660",
            "roas": "5.0x",
            "active_campaigns": 12,
            "total_impressions": "2.4M",
            "total_clicks": "48.2K"
        }
    
    elif tool_name == "get_campaigns":
        limit = arguments.get("limit", 10)
        # Convert PKR to USD for realistic values
        pkr_to_usd = 278
        campaigns = [
            {"name": "Post: \"We provide every type of AI and web service, from...\"", "spend": f"{563.67 / pkr_to_usd:.2f}", "roas": "1.5", "status": "Active"},
            {"name": "Summer Sale Campaign", "spend": f"{782.34 / pkr_to_usd:.2f}", "roas": "1.8", "status": "Active"},
            {"name": "Brand Awareness Q4", "spend": f"{412.89 / pkr_to_usd:.2f}", "roas": "1.3", "status": "Paused"},
            {"name": "Product Launch", "spend": f"{325.00 / pkr_to_usd:.2f}", "roas": "1.6", "status": "Active"},
            {"name": "Back to School", "spend": f"{298.50 / pkr_to_usd:.2f}", "roas": "1.4", "status": "Completed"}
        ]
        return {"campaigns": campaigns[:limit], "total": len(campaigns), "currency": "USD"}
    
    elif tool_name == "get_account_metrics":
        days = arguments.get("days", 30)
        # Convert PKR to USD (1 USD = ~278 PKR)
        pkr_to_usd = 278
        spend_pkr = 563.67
        revenue_pkr = 845.50
        cpc_pkr = 11.74
        
        return {
            "period": f"Last {days} days",
            "currency": "USD",
            "metrics": {
                "total_spend": f"{spend_pkr / pkr_to_usd:.2f}",
                "total_revenue": f"{revenue_pkr / pkr_to_usd:.2f}",
                "overall_roas": "1.5",
                "avg_ctr": "1.56%",
                "avg_cpc": f"{cpc_pkr / pkr_to_usd:.2f}",
                "conversions": 3,
                "conversion_rate": "6.25%"
            },
            "note": f"Values converted from PKR at rate 1 USD = {pkr_to_usd} PKR"
        }
    
    else:
        return {"error": f"Unknown tool: {tool_name}"}

# OAuth Discovery Endpoints
@oauth_mcp_fixed_bp.route('/.well-known/oauth-authorization-server')
def oauth_discovery():
    """OAuth 2.0 Authorization Server Metadata"""
    return jsonify({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "registration_endpoint": f"{BASE_URL}/oauth/register",
        "revocation_endpoint": f"{BASE_URL}/oauth/revoke",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["mcp:read", "mcp:write"],
        "response_modes_supported": ["query", "fragment"],
        "revocation_endpoint_auth_methods_supported": ["none"]
    })

@oauth_mcp_fixed_bp.route('/.well-known/oauth-protected-resource')
def oauth_protected_resource():
    """Tell Claude this server requires OAuth"""
    response = make_response('', 401)
    response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}", authorization_uri="{BASE_URL}/oauth/authorize", token_uri="{BASE_URL}/oauth/token"'
    return response

# OAuth Endpoints
@oauth_mcp_fixed_bp.route('/oauth/register', methods=['POST', 'OPTIONS'])
def oauth_register():
    """Dynamic client registration"""
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    data = request.get_json() or {}
    client_id = str(uuid.uuid4())[:8]
    
    return jsonify({
        "client_id": client_id,
        "client_secret": "not_required",
        "client_id_issued_at": int(datetime.utcnow().timestamp()),
        "redirect_uris": data.get('redirect_uris', []),
        "grant_types": ["authorization_code", "client_credentials"],
        "response_types": ["code", "token"],
        "client_name": data.get('client_name', 'Claude MCP Client'),
        "token_endpoint_auth_method": "none",
        "scope": "mcp:read mcp:write"
    })

@oauth_mcp_fixed_bp.route('/oauth/authorize', methods=['GET', 'POST'])
def oauth_authorize():
    """OAuth authorization with manual consent"""
    if request.method == 'GET':
        # Show consent page
        response = make_response(render_template('oauth_authorize.html',
                                                client_id=request.args.get('client_id'),
                                                redirect_uri=request.args.get('redirect_uri'),
                                                state=request.args.get('state'),
                                                response_type=request.args.get('response_type'),
                                                code_challenge=request.args.get('code_challenge'),
                                                code_challenge_method=request.args.get('code_challenge_method')))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    
    # POST - user approved
    redirect_uri = request.args.get('redirect_uri', '')
    state = request.args.get('state', '')
    response_type = request.args.get('response_type', 'code')
    
    if response_type == 'token':
        # Implicit flow
        access_token = jwt.encode({
            'user_id': 'claude_user',
            'type': 'access_token',
            'exp': datetime.utcnow() + timedelta(days=365)
        }, JWT_SECRET, algorithm='HS256')
        
        if redirect_uri:
            return redirect(f"{redirect_uri}#access_token={access_token}&token_type=Bearer&state={state}")
        return jsonify({"access_token": access_token, "token_type": "Bearer"})
    
    else:
        # Authorization code flow
        code = jwt.encode({
            'type': 'auth_code',
            'user_id': 'claude_user',
            'exp': datetime.utcnow() + timedelta(minutes=10)
        }, JWT_SECRET, algorithm='HS256')
        
        if redirect_uri:
            return redirect(f"{redirect_uri}?code={code}&state={state}")
        return jsonify({"code": code})

@oauth_mcp_fixed_bp.route('/oauth/token', methods=['POST', 'OPTIONS'])
def oauth_token():
    """Token endpoint"""
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    
    # Parse data
    data = request.form.to_dict() if request.form else request.get_json() or {}
    grant_type = data.get('grant_type')
    
    print(f"OAuth Token: grant_type={grant_type}")
    
    if grant_type == 'client_credentials':
        # Direct token issuance
        access_token = jwt.encode({
            'user_id': 'claude_user',
            'type': 'access_token',
            'exp': datetime.utcnow() + timedelta(days=365)
        }, JWT_SECRET, algorithm='HS256')
        
        # Store session
        active_sessions[access_token] = {
            'user_id': 'claude_user',
            'created_at': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 31536000,
            "scope": "mcp:read mcp:write"
        })
    
    elif grant_type == 'authorization_code' or not grant_type:
        # Exchange code for token
        code = data.get('code')
        if not code:
            return jsonify({"error": "invalid_request"}), 400
        
        try:
            # Verify code
            payload = jwt.decode(code, JWT_SECRET, algorithms=['HS256'])
            
            # Generate token
            access_token = jwt.encode({
                'user_id': payload.get('user_id', 'claude_user'),
                'type': 'access_token',
                'exp': datetime.utcnow() + timedelta(days=365)
            }, JWT_SECRET, algorithm='HS256')
            
            # Store session
            active_sessions[access_token] = {
                'user_id': payload.get('user_id', 'claude_user'),
                'created_at': datetime.utcnow().isoformat()
            }
            
            return jsonify({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 31536000,
                "scope": "mcp:read mcp:write"
            })
            
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid_grant"}), 400
    
    return jsonify({"error": "unsupported_grant_type"}), 400

@oauth_mcp_fixed_bp.route('/oauth/revoke', methods=['POST', 'OPTIONS'])
def oauth_revoke():
    """Token revocation"""
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    
    # Get token
    data = request.form.to_dict() if request.form else request.get_json() or {}
    token = data.get('token')
    
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
    
    # Remove from active sessions
    if token and token in active_sessions:
        del active_sessions[token]
        print(f"OAuth Revoke: Token revoked")
    
    # Always return 200 per RFC 7009
    return '', 200

# MCP Endpoints
@oauth_mcp_fixed_bp.route('/', methods=['GET', 'POST', 'OPTIONS', 'HEAD'])
def root_handler():
    """Main MCP endpoint"""
    
    # Handle preflight
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, HEAD',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    
    # Handle HEAD
    if request.method == 'HEAD':
        return '', 200
    
    # Handle GET - server info
    if request.method == 'GET':
        return jsonify({
            "name": "Zane - Meta Ads Connector",
            "version": "1.0.0",
            "protocol": "mcp",
            "description": "Connect Claude to your Meta Ads accounts"
        })
    
    # Handle POST - MCP requests
    auth_header = request.headers.get('Authorization', '')
    
    # Check auth
    if not auth_header or not auth_header.startswith('Bearer '):
        # Trigger OAuth flow
        response = make_response('Authentication required', 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}", authorization_uri="{BASE_URL}/oauth/authorize", token_uri="{BASE_URL}/oauth/token"'
        return response
    
    token = auth_header[7:]
    
    # Verify token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
    except jwt.InvalidTokenError:
        response = make_response('Invalid token', 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}"'
        return response
    
    # Process MCP message
    message = request.get_json()
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    method = message.get('method')
    params = message.get('params', {})
    msg_id = message.get('id')
    
    print(f"MCP Request: method={method}, id={msg_id}")
    
    # Handle different methods
    if method == 'initialize':
        result = {
            "protocolVersion": params.get('protocolVersion', '2024-11-05'),
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "Zane - Meta Ads Connector",
                "version": "1.0.0"
            }
        }
        print(f"MCP: Initialized with protocol {result['protocolVersion']}")
    
    elif method == 'initialized':
        # Client notification - no response needed
        return '', 204
    
    elif method == 'tools/list':
        tools = get_tools_list()
        result = {"tools": tools}
        print(f"MCP: Returning {len(tools)} tools")
    
    elif method == 'tools/call':
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        print(f"MCP: Executing tool {tool_name}")
        
        tool_result = execute_tool(tool_name, arguments)
        result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(tool_result, indent=2)
                }
            ]
        }
    
    elif method == 'ping':
        result = {}
    
    else:
        # Unknown method
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": msg_id
        }), 404
    
    # Return success response
    response = {
        "jsonrpc": "2.0",
        "result": result
    }
    if msg_id is not None:
        response["id"] = msg_id
    
    return jsonify(response), 200, {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }

@oauth_mcp_fixed_bp.route('/rpc', methods=['POST', 'OPTIONS'])
def rpc_handler():
    """Alternative RPC endpoint"""
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
    
    # Forward to root handler
    return root_handler()

@oauth_mcp_fixed_bp.route('/health')
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "sessions": len(active_sessions),
        "timestamp": datetime.utcnow().isoformat()
    })