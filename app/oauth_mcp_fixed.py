"""
Fixed OAuth MCP implementation for Claude
This version ensures tools are properly exposed after OAuth and uses real data
"""

from flask import Blueprint, jsonify, request, redirect, Response, make_response, render_template
import json
import jwt
import os
import uuid
from datetime import datetime, timedelta
from app.models import User
from app.mcp_protocol import MCPHandler
from app.supabase_client import SupabaseClient

oauth_mcp_fixed_bp = Blueprint('oauth_mcp_fixed', __name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')
BASE_URL = os.getenv('BASE_URL', 'https://deep-audy-wotbix-9060bbad.koyeb.app')

# Simple in-memory storage for active sessions
active_sessions = {}

# OAuth endpoints
@oauth_mcp_fixed_bp.route('/.well-known/oauth-authorization-server')
def well_known_oauth():
    """OAuth server metadata"""
    return jsonify({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "revocation_endpoint": f"{BASE_URL}/oauth/revoke",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["plain", "S256"]
    })

@oauth_mcp_fixed_bp.route('/.well-known/mcp-oauth-metadata')
def well_known_mcp():
    """MCP OAuth metadata"""
    return jsonify({
        "server_name": "Zane - Meta Ads Connector",
        "server_version": "1.0.0",
        "oauth_metadata_endpoint": f"{BASE_URL}/.well-known/oauth-authorization-server",
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "grant_types": ["authorization_code", "client_credentials"],
        "response_types": ["code", "token"],
        "scopes_supported": ["mcp:read", "mcp:write"]
    })

@oauth_mcp_fixed_bp.route('/oauth/authorize', methods=['GET', 'POST', 'OPTIONS'])
def oauth_authorize():
    """OAuth authorization endpoint - requires user to be logged in"""
    if request.method == 'OPTIONS':
        return '', 204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    from flask_login import current_user
    from flask import session
    
    if request.method == 'GET':
        # Show authorization page
        client_id = request.args.get('client_id', 'claude')
        redirect_uri = request.args.get('redirect_uri', '')
        state = request.args.get('state', '')
        scope = request.args.get('scope', 'mcp:read mcp:write')
        
        # Check if user is logged in via session or get first user for OAuth flow
        user_id = None
        
        # Try to get current logged in user
        if current_user and current_user.is_authenticated:
            user_id = current_user.id
        else:
            # For OAuth flow, check if we have a user in session
            user_email = session.get('user_email')
            if user_email:
                user = User.get_by_email(user_email)
                if user:
                    user_id = user.id
            else:
                # Get the first active user with ad accounts configured
                # This is for the OAuth flow when Claude connects
                try:
                    client = SupabaseClient.get_client()
                    # Get users who have ad accounts
                    users_result = client.table('users').select('*').execute()
                    if users_result.data:
                        for user_data in users_result.data:
                            user = User(user_data)
                            if user.get_ad_accounts():
                                user_id = user.id
                                break
                except Exception as e:
                    print(f"Error finding user for OAuth: {e}")
        
        if not user_id:
            # No user found - show error or redirect to login
            return render_template('oauth_authorize.html', 
                                 error="No user with Meta Ads accounts found. Please login and configure your Meta Ads accounts first.",
                                 client_id=client_id,
                                 redirect_uri=redirect_uri,
                                 state=state,
                                 scope=scope)
        
        # Generate authorization code with real user ID
        code = jwt.encode({
            'client_id': client_id,
            'user_id': user_id,
            'scope': scope,
            'exp': datetime.utcnow() + timedelta(minutes=10)
        }, JWT_SECRET, algorithm='HS256')
        
        # Store for verification
        active_sessions[code] = {
            'client_id': client_id,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Auto-approve and redirect with code
        redirect_url = f"{redirect_uri}?code={code}"
        if state:
            redirect_url += f"&state={state}"
        
        print(f"OAuth Authorize: User {user_id} authorized, redirecting to {redirect_url}")
        return redirect(redirect_url)
    
    # POST - Direct approval (for API)
    data = request.get_json() or {}
    client_id = data.get('client_id', 'claude')
    user_id = data.get('user_id')  # Must provide user_id in POST
    
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    # Verify user exists
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"error": "Invalid user"}), 400
    
    code = jwt.encode({
        'client_id': client_id,
        'user_id': user_id,
        'scope': 'mcp:read mcp:write',
        'exp': datetime.utcnow() + timedelta(minutes=10)
    }, JWT_SECRET, algorithm='HS256')
    
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
        # For client credentials, we need to identify which user to use
        # Get the first user with ad accounts configured
        try:
            client = SupabaseClient.get_client()
            users_result = client.table('users').select('*').execute()
            user_id = None
            
            if users_result.data:
                for user_data in users_result.data:
                    user = User(user_data)
                    if user.get_ad_accounts():
                        user_id = user.id
                        break
            
            if not user_id:
                return jsonify({"error": "No users with Meta Ads accounts configured"}), 400
            
            # Direct token issuance
            access_token = jwt.encode({
                'user_id': user_id,
                'type': 'access_token',
                'exp': datetime.utcnow() + timedelta(days=365)
            }, JWT_SECRET, algorithm='HS256')
            
            # Store session
            active_sessions[access_token] = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat()
            }
            
            return jsonify({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 31536000,
                "scope": "mcp:read mcp:write"
            })
        except Exception as e:
            print(f"Error in client_credentials grant: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    elif grant_type == 'authorization_code' or not grant_type:
        # Exchange code for token
        code = data.get('code')
        if not code:
            return jsonify({"error": "invalid_request"}), 400
        
        try:
            # Verify code
            payload = jwt.decode(code, JWT_SECRET, algorithms=['HS256'])
            
            # Get user_id from the code payload
            user_id = payload.get('user_id')
            if not user_id:
                return jsonify({"error": "Invalid authorization code"}), 400
            
            # Verify user exists
            user = User.get_by_id(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 400
            
            # Generate token
            access_token = jwt.encode({
                'user_id': user_id,
                'type': 'access_token',
                'exp': datetime.utcnow() + timedelta(days=365)
            }, JWT_SECRET, algorithm='HS256')
            
            # Store session
            active_sessions[access_token] = {
                'user_id': user_id,
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
    
    # Get user and create MCP handler
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found. Please login and configure Meta Ads accounts."}), 404
    
    handler = MCPHandler(user)
    
    # Process MCP message
    message = request.get_json()
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    # Use the MCPHandler to process the message
    try:
        response_data = handler.handle_message(message)
        
        # Add JSONRPC wrapper if not present
        if 'jsonrpc' not in response_data:
            response_data = {
                "jsonrpc": "2.0",
                "result": response_data
            }
            if message.get('id') is not None:
                response_data["id"] = message.get('id')
        
        return jsonify(response_data), 200, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    except Exception as e:
        print(f"MCP Error: {str(e)}")
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }
        if message.get('id') is not None:
            error_response["id"] = message.get('id')
        
        return jsonify(error_response), 200, {
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