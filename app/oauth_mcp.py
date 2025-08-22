"""
OAuth-compatible MCP server for Claude integration
Implements the OAuth discovery endpoints Claude expects
"""

from flask import Blueprint, jsonify, request, redirect, Response, make_response
import json
import jwt
import os
from datetime import datetime, timedelta
from app.models import User
from app.mcp_protocol import MCPHandler

oauth_mcp_bp = Blueprint('oauth_mcp', __name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')
BASE_URL = os.getenv('BASE_URL', 'https://deep-audy-wotbix-9060bbad.koyeb.app')

@oauth_mcp_bp.route('/.well-known/oauth-protected-resource')
def oauth_protected_resource():
    """
    OAuth protected resource discovery
    Tells Claude this server requires OAuth
    """
    response = make_response('', 401)
    response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}", authorization_uri="{BASE_URL}/oauth/authorize", token_uri="{BASE_URL}/oauth/token"'
    return response

@oauth_mcp_bp.route('/', methods=['POST', 'GET', 'HEAD', 'OPTIONS'])
def root_handler():
    """
    Root endpoint handler for MCP
    """
    if request.method == 'HEAD':
        return '', 200
    
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS, HEAD'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    if request.method == 'GET':
        # Return server info for GET requests
        return jsonify({
            "name": "Zane - Meta Ads Connector",
            "version": "1.0.0",
            "protocol": "mcp",
            "description": "Connect Claude to your Meta Ads accounts"
        })
    
    # Handle POST requests (MCP commands)
    auth_header = request.headers.get('Authorization', '')
    
    # Check if this is an initial connection attempt
    if not auth_header:
        # Return 401 with OAuth info to trigger auth flow
        response = make_response('Authentication required', 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}"'
        return response
    
    # If we have auth, handle as MCP request
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Invalid authorization"}), 401
    
    token = auth_header[7:]
    
    try:
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        # Get user
        from app.models import User
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Invalid user"}), 401
        
        # Process MCP message
        message = request.get_json()
        if not message:
            return jsonify({"error": "No message provided"}), 400
            
        print(f"Root handler: Received {message.get('method')} from {user.email}")
        
        from app.mcp_protocol import MCPHandler
        handler = MCPHandler(user)
        response = handler.handle_message(message)
        
        return jsonify(response)
        
    except jwt.InvalidTokenError:
        response = make_response('Invalid token', 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}"'
        return response
    except Exception as e:
        print(f"Root handler error: {e}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": message.get('id') if 'message' in locals() else None
        }), 500

@oauth_mcp_bp.route('/register', methods=['POST', 'OPTIONS'])
def register():
    """
    Registration endpoint that Claude might call
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    # For now, auto-approve registration
    return jsonify({
        "status": "registered",
        "client_id": "claude",
        "client_secret": "not_required",
        "auth_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token"
    })

@oauth_mcp_bp.route('/.well-known/oauth-authorization-server')
def oauth_discovery():
    """
    OAuth 2.0 Authorization Server Metadata
    This is what Claude looks for first
    """
    return jsonify({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "implicit", "client_credentials"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "scopes_supported": ["mcp:read", "mcp:write"],
        "response_modes_supported": ["query", "fragment"],
        "service_documentation": f"{BASE_URL}/docs",
        "authorization_response_iss_parameter_supported": True,
        "claims_supported": ["sub", "iss", "aud", "exp", "iat"]
    })

@oauth_mcp_bp.route('/.well-known/mcp-server')
def mcp_server_info():
    """
    MCP Server metadata
    """
    return jsonify({
        "name": "Zane - Meta Ads Connector",
        "version": "1.0.0",
        "description": "Connect Claude to your Meta Ads accounts",
        "mcp_version": "1.0",
        "transport": "http",
        "endpoints": {
            "rpc": "/rpc",
            "sse": "/sse"
        },
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False
        }
    })

@oauth_mcp_bp.route('/oauth/authorize')
def oauth_authorize():
    """
    OAuth authorization endpoint
    Simplified flow - immediately redirect with token
    """
    # Get parameters
    client_id = request.args.get('client_id', 'claude')
    redirect_uri = request.args.get('redirect_uri', '')
    state = request.args.get('state', '')
    response_type = request.args.get('response_type', 'code')
    
    # For simplicity, we'll use a pre-authorized approach
    # In production, you'd show a login/consent screen here
    
    if response_type == 'token':
        # Implicit flow - return token directly
        access_token = jwt.encode({
            'user_id': 1,  # Default user for demo
            'type': 'access_token',
            'exp': datetime.utcnow() + timedelta(days=365)
        }, JWT_SECRET, algorithm='HS256')
        
        if redirect_uri:
            return redirect(f"{redirect_uri}#access_token={access_token}&token_type=Bearer&state={state}")
        else:
            return jsonify({"access_token": access_token, "token_type": "Bearer", "state": state})
    else:
        # Authorization code flow
        code = jwt.encode({
            'type': 'auth_code',
            'client_id': client_id,
            'exp': datetime.utcnow() + timedelta(minutes=10)
        }, JWT_SECRET, algorithm='HS256')
        
        if redirect_uri:
            return redirect(f"{redirect_uri}?code={code}&state={state}")
        else:
            return jsonify({"code": code, "state": state})

@oauth_mcp_bp.route('/oauth/token', methods=['POST'])
def oauth_token():
    """
    OAuth token endpoint
    Exchange authorization code for access token
    """
    # Get the authorization code
    code = request.form.get('code') or request.json.get('code')
    
    if not code:
        return jsonify({"error": "invalid_request", "error_description": "Missing code"}), 400
    
    try:
        # Verify the authorization code
        payload = jwt.decode(code, JWT_SECRET, algorithms=['HS256'])
        
        # Generate access token
        # For demo, we'll use user ID 1 - in production, this would be from the auth flow
        access_token = jwt.encode({
            'user_id': 1,  # Default to first user for demo
            'type': 'access_token',
            'exp': datetime.utcnow() + timedelta(days=365)
        }, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 31536000  # 1 year
        })
        
    except jwt.InvalidTokenError:
        return jsonify({"error": "invalid_grant", "error_description": "Invalid code"}), 400

@oauth_mcp_bp.route('/rpc', methods=['POST', 'OPTIONS'])
def handle_rpc():
    """
    Main RPC endpoint for MCP commands
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "unauthorized"}), 401
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    try:
        # Decode token to get user ID
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "invalid_token"}), 401
        
        # Process MCP message
        message = request.get_json()
        print(f"MCP RPC: Received {message.get('method')} from {user.email}")
        
        handler = MCPHandler(user)
        response = handler.handle_message(message)
        
        # Add CORS headers to response
        return jsonify(response), 200, {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
    except jwt.InvalidTokenError as e:
        print(f"Token error: {e}")
        return jsonify({"error": "invalid_token"}), 401
    except Exception as e:
        print(f"RPC error: {e}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            },
            "id": message.get('id') if 'message' in locals() else None
        }), 500

@oauth_mcp_bp.route('/sse', methods=['GET'])
def handle_sse():
    """
    Server-Sent Events endpoint
    """
    # Get token
    auth_header = request.headers.get('Authorization', '')
    token = auth_header[7:] if auth_header.startswith('Bearer ') else request.args.get('token')
    
    if not token:
        return Response('Unauthorized', status=401)
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return Response('Invalid user', status=401)
        
        def generate():
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'user': user.email})}\n\n"
            
            # Keep connection alive
            import time
            while True:
                time.sleep(30)
                yield f": heartbeat\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*'
            }
        )
        
    except jwt.InvalidTokenError:
        return Response('Invalid token', status=401)