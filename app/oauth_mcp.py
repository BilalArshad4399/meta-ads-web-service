"""
OAuth-compatible MCP server for Claude integration
Implements the OAuth discovery endpoints Claude expects
"""

from flask import Blueprint, jsonify, request, redirect, Response, make_response
import json
import jwt
import os
import uuid
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
        print("Root POST: No auth header, triggering OAuth flow")
        response = make_response('Authentication required', 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}", authorization_uri="{BASE_URL}/oauth/authorize", token_uri="{BASE_URL}/oauth/token"'
        return response
    
    # If we have auth, handle as MCP request
    if not auth_header.startswith('Bearer '):
        print(f"Root POST: Invalid auth header format: {auth_header[:20]}...")
        return jsonify({"error": "Invalid authorization"}), 401
    
    token = auth_header[7:]
    print(f"Root POST: Processing request with token")
    
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

@oauth_mcp_bp.route('/oauth/register', methods=['POST', 'OPTIONS'])
def oauth_register():
    """
    OAuth Dynamic Client Registration endpoint
    """
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    # Get registration data
    data = request.get_json() or {}
    
    print(f"OAuth Register: Received registration request: {data}")
    
    # Generate client credentials
    client_id = data.get('client_name', 'claude') + '_' + str(uuid.uuid4())[:8]
    
    # Return registration response
    response = {
        "client_id": client_id,
        "client_secret": "not_required",  # We don't require client secret
        "client_id_issued_at": int(datetime.utcnow().timestamp()),
        "redirect_uris": data.get('redirect_uris', []),
        "grant_types": ["authorization_code", "implicit", "client_credentials"],
        "response_types": ["code", "token"],
        "client_name": data.get('client_name', 'Claude MCP Client'),
        "token_endpoint_auth_method": "none",
        "scope": "mcp:read mcp:write"
    }
    
    print(f"OAuth Register: Returning client_id: {client_id}")
    
    return jsonify(response)

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
        "registration_endpoint": f"{BASE_URL}/oauth/register",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "implicit", "client_credentials"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
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
    
    print(f"OAuth Authorize: client_id={client_id}, response_type={response_type}, redirect_uri={redirect_uri}")
    
    # Get or create a default user for Claude
    from app import db
    user = User.query.filter_by(email='claude@anthropic.com').first()
    if not user:
        # Create default Claude user
        user = User(email='claude@anthropic.com', name='Claude AI')
        user.set_password('claude-mcp-integration')
        user.api_key = str(uuid.uuid4())
        db.session.add(user)
        db.session.commit()
        print(f"Created default Claude user with ID: {user.id}")
    
    if response_type == 'token':
        # Implicit flow - return token directly
        access_token = jwt.encode({
            'user_id': user.id,
            'type': 'access_token',
            'exp': datetime.utcnow() + timedelta(days=365)
        }, JWT_SECRET, algorithm='HS256')
        
        print(f"Issuing access token for user {user.id}")
        
        if redirect_uri:
            return redirect(f"{redirect_uri}#access_token={access_token}&token_type=Bearer&state={state}")
        else:
            return jsonify({"access_token": access_token, "token_type": "Bearer", "state": state})
    else:
        # Authorization code flow
        # Get PKCE parameters
        code_challenge = request.args.get('code_challenge')
        code_challenge_method = request.args.get('code_challenge_method', 'S256')
        
        code_payload = {
            'type': 'auth_code',
            'client_id': client_id,
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(minutes=10)
        }
        
        # Store code challenge if provided (for PKCE)
        if code_challenge:
            code_payload['code_challenge'] = code_challenge
            code_payload['code_challenge_method'] = code_challenge_method
        
        code = jwt.encode(code_payload, JWT_SECRET, algorithm='HS256')
        
        print(f"Issuing auth code for user {user.id} with PKCE: {bool(code_challenge)}")
        
        if redirect_uri:
            return redirect(f"{redirect_uri}?code={code}&state={state}")
        else:
            return jsonify({"code": code, "state": state})

@oauth_mcp_bp.route('/oauth/token', methods=['POST', 'OPTIONS'])
def oauth_token():
    """
    OAuth token endpoint
    Supports authorization_code and client_credentials grant types
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    # Parse request data - handle both form-encoded and JSON
    data = {}
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json() or {}
    else:
        # Try form data first, then fall back to JSON
        data = dict(request.form)
        # Convert single-item lists to strings
        for key, value in data.items():
            if isinstance(value, list) and len(value) == 1:
                data[key] = value[0]
        
        # If no form data, try JSON
        if not data:
            try:
                data = request.get_json(force=True) or {}
            except:
                data = {}
    
    # Get grant type
    grant_type = data.get('grant_type')
    
    print(f"OAuth Token: content_type={request.content_type}, grant_type={grant_type}, data={data}")
    
    if grant_type == 'client_credentials':
        # Client credentials flow - direct token issuance
        # Get or create Claude user
        from app import db
        user = User.query.filter_by(email='claude@anthropic.com').first()
        if not user:
            user = User(email='claude@anthropic.com', name='Claude AI')
            user.set_password('claude-mcp-integration')
            user.api_key = str(uuid.uuid4())
            db.session.add(user)
            db.session.commit()
            print(f"Created default Claude user with ID: {user.id}")
        
        # Generate access token
        access_token = jwt.encode({
            'user_id': user.id,
            'type': 'access_token',
            'exp': datetime.utcnow() + timedelta(days=365)
        }, JWT_SECRET, algorithm='HS256')
        
        print(f"Issued client_credentials token for user {user.id}")
        
        return jsonify({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 31536000,  # 1 year
            "scope": "mcp:read mcp:write"
        })
    
    elif grant_type == 'authorization_code' or not grant_type:
        # Authorization code flow
        code = data.get('code')
        
        if not code:
            return jsonify({"error": "invalid_request", "error_description": "Missing code"}), 400
        
        try:
            # Verify the authorization code
            payload = jwt.decode(code, JWT_SECRET, algorithms=['HS256'])
            user_id = payload.get('user_id', 1)
            
            # Verify PKCE if it was used
            if 'code_challenge' in payload:
                code_verifier = data.get('code_verifier')
                if not code_verifier:
                    return jsonify({"error": "invalid_request", "error_description": "Missing code_verifier for PKCE"}), 400
                
                # Verify the code challenge
                import hashlib
                import base64
                
                if payload.get('code_challenge_method') == 'S256':
                    # SHA256 hash the verifier
                    challenge = base64.urlsafe_b64encode(
                        hashlib.sha256(code_verifier.encode()).digest()
                    ).decode().rstrip('=')
                else:
                    # Plain method
                    challenge = code_verifier
                
                if challenge != payload.get('code_challenge'):
                    print(f"PKCE verification failed: expected {payload.get('code_challenge')}, got {challenge}")
                    return jsonify({"error": "invalid_grant", "error_description": "Invalid code_verifier"}), 400
            
            print(f"Token exchange for user_id: {user_id}, PKCE verified: {'code_challenge' in payload}")
            
            # Generate access token
            access_token = jwt.encode({
                'user_id': user_id,
                'type': 'access_token',
                'exp': datetime.utcnow() + timedelta(days=365)
            }, JWT_SECRET, algorithm='HS256')
            
            return jsonify({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 31536000,  # 1 year
                "scope": "mcp:read mcp:write"
            })
            
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid_grant", "error_description": "Invalid code"}), 400
    
    else:
        return jsonify({"error": "unsupported_grant_type", "error_description": f"Grant type '{grant_type}' is not supported"}), 400

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