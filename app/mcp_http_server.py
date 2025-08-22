"""
MCP HTTP Server with proper persistent connection handling
Implements the 2025-06-18 specification
"""

from flask import Blueprint, request, jsonify, Response, make_response, redirect
import json
import jwt
import os
import uuid
from datetime import datetime, timedelta
from app.models import User
from app.mcp_protocol import MCPHandler
from app import db
import logging

logger = logging.getLogger(__name__)

mcp_http_bp = Blueprint('mcp_http', __name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')
BASE_URL = os.getenv('BASE_URL', 'https://deep-audy-wotbix-9060bbad.koyeb.app')

# Store active sessions
active_sessions = {}

@mcp_http_bp.route('/', methods=['POST', 'GET', 'HEAD', 'OPTIONS'])
def mcp_root():
    """
    Main MCP endpoint - handles all MCP protocol messages
    """
    # Handle preflight
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS, HEAD'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    # Handle HEAD requests for discovery
    if request.method == 'HEAD':
        return '', 200
    
    # Handle GET requests - return server info
    if request.method == 'GET':
        return jsonify({
            "name": "Zane - Meta Ads Connector",
            "version": "1.0.0",
            "protocol": "mcp",
            "protocolVersion": "2025-06-18",
            "description": "Connect Claude to your Meta Ads accounts"
        })
    
    # Handle POST requests - MCP protocol messages
    auth_header = request.headers.get('Authorization', '')
    
    # Check authentication
    if not auth_header:
        logger.info("No auth header, triggering OAuth flow")
        response = make_response('Authentication required', 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}", authorization_uri="{BASE_URL}/oauth/authorize", token_uri="{BASE_URL}/oauth/token"'
        return response
    
    if not auth_header.startswith('Bearer '):
        logger.error(f"Invalid auth header format: {auth_header[:20]}...")
        return jsonify({"error": "Invalid authorization"}), 401
    
    token = auth_header[7:]
    
    try:
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User not found: {user_id}")
            return jsonify({"error": "Invalid user"}), 401
        
        # Get the JSON-RPC message
        message = request.get_json()
        if not message:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request - No JSON body"
                },
                "id": None
            }), 400
        
        method = message.get('method')
        message_id = message.get('id')
        params = message.get('params', {})
        
        logger.info(f"MCP: User {user.email} called {method} with id={message_id}")
        logger.info(f"MCP: Full request: {json.dumps(message)}")
        
        # Handle the message
        handler = MCPHandler(user)
        
        # Special handling for initialize to track sessions
        if method == 'initialize':
            session_id = str(uuid.uuid4())
            active_sessions[session_id] = {
                'user_id': user.id,
                'created_at': datetime.utcnow(),
                'last_activity': datetime.utcnow()
            }
            logger.info(f"MCP: Created session {session_id} for user {user.email}")
        
        # Process the message
        response = handler.handle_message(message)
        
        logger.info(f"MCP: Full response for {method}: {json.dumps(response)}")
        
        # Send response with proper headers
        resp = jsonify(response)
        resp.headers['Content-Type'] = 'application/json'
        resp.headers['Connection'] = 'keep-alive'
        resp.headers['Keep-Alive'] = 'timeout=300'
        resp.headers['Cache-Control'] = 'no-cache'
        
        # If this was an initialize request, send notifications
        if method == 'initialize' and 'result' in response:
            # The protocol expects the server to be ready for subsequent requests
            logger.info("MCP: Initialization complete, server ready for requests")
        
        return resp
        
    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        response = make_response('Token expired', 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}"'
        return response
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {e}")
        response = make_response('Invalid token', 401)
        response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}"'
        return response
    except Exception as e:
        logger.error(f"MCP error: {e}", exc_info=True)
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": message.get('id') if 'message' in locals() else None
        }), 500

@mcp_http_bp.route('/.well-known/oauth-protected-resource')
def oauth_protected_resource():
    """OAuth discovery endpoint"""
    response = make_response('', 401)
    response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}", authorization_uri="{BASE_URL}/oauth/authorize", token_uri="{BASE_URL}/oauth/token"'
    return response

@mcp_http_bp.route('/.well-known/oauth-authorization-server')
def oauth_authorization_server():
    """OAuth authorization server metadata"""
    return jsonify({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "registration_endpoint": f"{BASE_URL}/oauth/register",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "scopes_supported": ["mcp:read", "mcp:write"],
        "response_modes_supported": ["query", "fragment"],
        "authorization_response_iss_parameter_supported": True
    })

@mcp_http_bp.route('/oauth/authorize')
def oauth_authorize():
    """OAuth authorization endpoint"""
    client_id = request.args.get('client_id', 'claude')
    redirect_uri = request.args.get('redirect_uri', '')
    state = request.args.get('state', '')
    response_type = request.args.get('response_type', 'code')
    code_challenge = request.args.get('code_challenge')
    code_challenge_method = request.args.get('code_challenge_method', 'S256')
    
    logger.info(f"OAuth: Authorize request from {client_id}")
    
    # Get or create Claude user
    user = User.query.filter_by(email='claude@anthropic.com').first()
    if not user:
        user = User(email='claude@anthropic.com', name='Claude AI')
        user.set_password('claude-mcp-integration')
        user.api_key = str(uuid.uuid4())
        db.session.add(user)
        db.session.commit()
        logger.info(f"OAuth: Created Claude user with ID {user.id}")
    
    if response_type == 'code':
        # Authorization code flow with PKCE
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
        
        logger.info(f"OAuth: Issuing code for user {user.id}")
        
        if redirect_uri:
            from urllib.parse import urlencode
            params = {'code': code, 'state': state}
            separator = '&' if '?' in redirect_uri else '?'
            return redirect(f"{redirect_uri}{separator}{urlencode(params)}")
        else:
            return jsonify({"code": code, "state": state})
    
    return jsonify({"error": "unsupported_response_type"}), 400

@mcp_http_bp.route('/oauth/token', methods=['POST', 'OPTIONS'])
def oauth_token():
    """OAuth token endpoint"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    # Parse request data
    data = {}
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json() or {}
    else:
        data = dict(request.form)
        for key, value in data.items():
            if isinstance(value, list) and len(value) == 1:
                data[key] = value[0]
        if not data:
            try:
                data = request.get_json(force=True) or {}
            except:
                data = {}
    
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
                
                import hashlib
                import base64
                
                if payload.get('code_challenge_method') == 'S256':
                    challenge = base64.urlsafe_b64encode(
                        hashlib.sha256(code_verifier.encode()).digest()
                    ).decode().rstrip('=')
                else:
                    challenge = code_verifier
                
                if challenge != payload.get('code_challenge'):
                    logger.error(f"OAuth: PKCE verification failed")
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

@mcp_http_bp.route('/oauth/register', methods=['POST', 'OPTIONS'])
def oauth_register():
    """OAuth Dynamic Client Registration"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    data = request.get_json() or {}
    logger.info(f"OAuth: Client registration request: {data}")
    
    client_id = data.get('client_name', 'claude') + '_' + str(uuid.uuid4())[:8]
    
    response = {
        "client_id": client_id,
        "client_secret": "not_required",
        "client_id_issued_at": int(datetime.utcnow().timestamp()),
        "redirect_uris": data.get('redirect_uris', []),
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "client_name": data.get('client_name', 'Claude MCP Client'),
        "token_endpoint_auth_method": "none",
        "scope": "mcp:read mcp:write"
    }
    
    logger.info(f"OAuth: Registered client {client_id}")
    
    return jsonify(response)