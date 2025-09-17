"""
Fixed OAuth MCP implementation for Claude
This version ensures tools are properly exposed after OAuth
"""

from flask import Blueprint, jsonify, request, redirect, Response, make_response, render_template, session
from flask_login import current_user
import json
import jwt
import os
import uuid
from datetime import datetime, timedelta
from app.models import User, AdAccount
from app.meta_client import MetaAdsClient
import logging
from functools import wraps

logger = logging.getLogger(__name__)

oauth_mcp_fixed_bp = Blueprint('oauth_mcp_fixed', __name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')
BASE_URL = os.getenv('BASE_URL', 'https://deep-audy-wotbix-9060bbad.koyeb.app')

# Simple in-memory storage for active sessions
active_sessions = {}

def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

def get_tools_list():
    """Return the list of available tools"""
    return [
        {
            "name": "get_meta_ads_overview",
            "description": "Get Meta Ads account overview and metrics for specified time period",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "number",
                        "description": "Number of days to look back (default: 30, max: 365)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_campaigns",
            "description": "Get list of Meta Ads campaigns with performance metrics for specified time period",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "number",
                        "description": "Number of days to look back (default: 30, max: 365)"
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
            "name": "get_account_metrics",
            "description": "Get detailed account metrics including ROAS, CTR, and spend for specified time period",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "number",
                        "description": "Number of days to look back (default: 30, max: 365)"
                    }
                },
                "required": []
            }
        }
    ]

def execute_tool(tool_name, arguments, user_email=None):
    """Execute a tool and return results from real Facebook data"""
    # IMPORTANT: No demo data - only real data or error messages
    if not user_email:
        return {
            "status": "error",
            "message": "Authentication required. Please reconnect Claude to your Zane account."
        }

    if tool_name == "get_meta_ads_overview":
        try:
            # Get days parameter (default 30, max 365)
            days = min(int(arguments.get("days", 30)), 365)

            # Get user's ad accounts from database
            user = User.get_by_email(user_email)
            if not user:
                return {
                    "status": "error",
                    "message": "User account not found. Please reconnect Claude to your Zane account."
                }

            ad_accounts = user.get_ad_accounts()
            if not ad_accounts or len(ad_accounts) == 0:
                return {
                    "status": "error",
                    "message": "No Facebook Ads account connected. Please connect your Facebook Ads account in Zane dashboard first."
                }

            # Use the first active account
            account = ad_accounts[0]

            # Initialize Meta API client
            client = MetaAdsClient(account.access_token)

            # Get dynamic date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_range = {
                'since': start_date.strftime('%Y-%m-%d'),
                'until': end_date.strftime('%Y-%m-%d')
            }

            # Fetch real data from Facebook
            overview = client.get_account_overview(account.account_id, date_range)

            # Format the response with real data
            return {
                "status": "connected",
                "account_name": account.account_name,
                "account_id": account.account_id,
                "currency": overview.get('currency', 'USD'),
                "total_spend": f"${overview.get('spend', 0):,.2f}",
                "total_revenue": f"${overview.get('revenue', 0):,.2f}",
                "roas": f"{overview.get('roas', 0):.1f}x",
                "impressions": f"{overview.get('impressions', 0):,}",
                "clicks": f"{overview.get('clicks', 0):,}",
                "conversions": overview.get('conversions', 0),
                "ctr": f"{overview.get('ctr', 0):.2f}%",
                "cpc": f"${overview.get('cpc', 0):.2f}",
                "period": f"Last {days} days",
                "date_range": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }

        except Exception as e:
            logger.error(f"Error fetching Meta Ads overview: {str(e)}")
            # Check if it's a requests exception with response
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                    error_code = error_data.get('error', {}).get('code', '')
                    logger.error(f"Facebook API Error - Code: {error_code}, Message: {error_msg}")

                    # Common error handling
                    if error_code == 190 or "expired" in error_msg.lower():
                        return {
                            "status": "error",
                            "message": "Facebook access token has expired. Please reconnect your Facebook account in the Zane dashboard."
                        }
                    elif error_code == 100:
                        return {
                            "status": "error",
                            "message": "Invalid Facebook API request. This may be due to missing permissions or invalid parameters."
                        }
                except:
                    pass

            return {
                "status": "error",
                "message": f"Failed to fetch data from Facebook: {str(e)}"
            }
    
    elif tool_name == "get_campaigns":
        # Get parameters
        days = min(int(arguments.get("days", 30)), 365)
        limit = arguments.get("limit", 10)

        if not user_email:
            return {
                "status": "error",
                "message": "Authentication required. Please reconnect Claude to your Zane account."
            }

        try:
            user = User.get_by_email(user_email)
            if not user:
                return {
                    "status": "error",
                    "message": "User account not found. Please reconnect Claude to your Zane account."
                }

            ad_accounts = user.get_ad_accounts()
            if not ad_accounts or len(ad_accounts) == 0:
                return {
                    "status": "error",
                    "message": "No Facebook Ads account connected. Please connect your Facebook Ads account in Zane dashboard first."
                }

            account = ad_accounts[0]
            client = MetaAdsClient(account.access_token)

            # Get dynamic date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_range = {
                'since': start_date.strftime('%Y-%m-%d'),
                'until': end_date.strftime('%Y-%m-%d')
            }

            # Fetch real campaign data
            campaigns_data = client.get_campaign_roas(account.account_id, date_range)

            # Format campaigns with real data
            campaigns = []
            for camp in campaigns_data[:limit]:
                campaigns.append({
                    "name": camp.get('campaign_name', 'Unknown'),
                    "spend": f"${camp.get('spend', 0):.2f}",
                    "revenue": f"${camp.get('revenue', 0):.2f}",
                    "roas": f"{camp.get('roas', 0):.1f}",
                    "status": camp.get('status', 'Unknown'),
                    "impressions": camp.get('impressions', 0),
                    "clicks": camp.get('clicks', 0)
                })

            return {
                "campaigns": campaigns,
                "total": len(campaigns),
                "currency": "USD",
                "period": f"Last {days} days",
                "date_range": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }

        except Exception as e:
            logger.error(f"Error fetching campaigns: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to fetch campaigns from Facebook: {str(e)}"
            }
    
    elif tool_name == "get_account_metrics":
        days = arguments.get("days", 30)

        if not user_email:
            return {
                "status": "error",
                "message": "Authentication required. Please reconnect Claude to your Zane account."
            }

        try:
            user = User.get_by_email(user_email)
            if not user:
                return {
                    "status": "error",
                    "message": "User account not found. Please reconnect Claude to your Zane account."
                }

            ad_accounts = user.get_ad_accounts()
            if not ad_accounts or len(ad_accounts) == 0:
                return {
                    "status": "error",
                    "message": "No Facebook Ads account connected. Please connect your Facebook Ads account in Zane dashboard first."
                }

            account = ad_accounts[0]
            client = MetaAdsClient(account.access_token)

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_range = {
                'since': start_date.strftime('%Y-%m-%d'),
                'until': end_date.strftime('%Y-%m-%d')
            }

            # Fetch real metrics
            metrics = client.get_account_overview(account.account_id, date_range)

            # Calculate conversion rate
            conv_rate = 0
            if metrics.get('clicks', 0) > 0:
                conv_rate = (metrics.get('conversions', 0) / metrics.get('clicks', 0)) * 100

            return {
                "period": f"Last {days} days",
                "currency": metrics.get('currency', 'USD'),
                "account_name": account.account_name,
                "metrics": {
                    "total_spend": f"${metrics.get('spend', 0):.2f}",
                    "total_revenue": f"${metrics.get('revenue', 0):.2f}",
                    "overall_roas": f"{metrics.get('roas', 0):.1f}",
                    "avg_ctr": f"{metrics.get('ctr', 0):.2f}%",
                    "avg_cpc": f"${metrics.get('cpc', 0):.2f}",
                    "conversions": metrics.get('conversions', 0),
                    "conversion_rate": f"{conv_rate:.2f}%",
                    "impressions": metrics.get('impressions', 0),
                    "clicks": metrics.get('clicks', 0)
                }
            }

        except Exception as e:
            logger.error(f"Error fetching account metrics: {str(e)}")
            # Check if it's a requests exception with response
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                    error_code = error_data.get('error', {}).get('code', '')
                    logger.error(f"Facebook API Error - Code: {error_code}, Message: {error_msg}")

                    # Common error handling
                    if error_code == 190 or "expired" in error_msg.lower():
                        return {
                            "status": "error",
                            "message": "Facebook access token has expired. Please reconnect your Facebook account in the Zane dashboard."
                        }
                    elif error_code == 100:
                        return {
                            "status": "error",
                            "message": "Invalid Facebook API request. This may be due to missing permissions or invalid parameters."
                        }
                except:
                    pass

            return {
                "status": "error",
                "message": f"Failed to fetch metrics from Facebook: {str(e)}"
            }
    
    else:
        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}. Available tools: get_meta_ads_overview, get_campaigns, get_account_metrics"
        }

# Root MCP discovery endpoint for faster validation
@oauth_mcp_fixed_bp.route('/')
def root():
    """Root endpoint for quick availability check"""
    response = jsonify({
        "name": "Zane - Meta Ads Connector",
        "version": "1.0.0",
        "oauth_required": True,
        "discovery": "/.well-known/oauth-authorization-server"
    })
    return add_cors_headers(response)

# OAuth Discovery Endpoints
@oauth_mcp_fixed_bp.route('/.well-known/oauth-authorization-server')
def oauth_discovery():
    """OAuth 2.0 Authorization Server Metadata"""
    response = jsonify({
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
    response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
    return response

@oauth_mcp_fixed_bp.route('/.well-known/oauth-protected-resource')
def oauth_protected_resource():
    """Tell Claude this server requires OAuth"""
    # Return a proper JSON response with the OAuth info
    data = {
        "mcp_server": f"{BASE_URL}/mcp/sse",
        "authorization_server": f"{BASE_URL}/.well-known/oauth-authorization-server",
        "error": "unauthorized",
        "error_description": "OAuth 2.0 authorization required"
    }
    response = make_response(jsonify(data), 401)
    response.headers['WWW-Authenticate'] = f'Bearer realm="{BASE_URL}", authorization_uri="{BASE_URL}/oauth/authorize", token_uri="{BASE_URL}/oauth/token"'
    response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
    response.headers['Content-Type'] = 'application/json'
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
        # Check if user is logged in
        user_logged_in = False
        user_email = None
        has_facebook_account = False
        facebook_account_name = None

        if current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            user_logged_in = True
            user_email = current_user.email

            # Check if user has Facebook account connected
            ad_accounts = current_user.get_ad_accounts()
            if ad_accounts and len(ad_accounts) > 0:
                has_facebook_account = True
                facebook_account_name = ad_accounts[0].account_name

        # Show consent page with user status
        response = make_response(render_template('oauth_authorize.html',
                                                user_logged_in=user_logged_in,
                                                user_email=user_email,
                                                has_facebook_account=has_facebook_account,
                                                facebook_account_name=facebook_account_name,
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

    # Require user to be logged in with Facebook connected
    if not current_user or not current_user.is_authenticated:
        # User not logged in - redirect to error
        if redirect_uri:
            separator = '&' if '?' in redirect_uri else '?'
            return redirect(f"{redirect_uri}{separator}error=unauthorized&error_description=User not logged in")
        return jsonify({"error": "unauthorized", "error_description": "User not logged in"}), 401

    # Check if user has Facebook account
    ad_accounts = current_user.get_ad_accounts()
    if not ad_accounts or len(ad_accounts) == 0:
        # No Facebook account connected
        if redirect_uri:
            separator = '&' if '?' in redirect_uri else '?'
            return redirect(f"{redirect_uri}{separator}error=no_facebook_account&error_description=No Facebook Ads account connected")
        return jsonify({"error": "no_facebook_account", "error_description": "No Facebook Ads account connected"}), 400

    # Get the logged-in user's information
    user_id = str(current_user.id)
    user_email = current_user.email

    if response_type == 'token':
        # Implicit flow
        access_token = jwt.encode({
            'user_id': user_id,
            'email': user_email,
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
            'user_id': user_id,
            'email': user_email,
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
        # Get the logged-in user's information if available
        user_id = 'claude_user'
        user_email = None
        if current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            user_id = str(current_user.id)
            user_email = current_user.email

        access_token = jwt.encode({
            'user_id': user_id,
            'email': user_email,
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
                'email': payload.get('email'),
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
        user_email = payload.get('email')  # Get email from token
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
        print(f"MCP: Executing tool {tool_name} for user {user_email}")

        # Pass user_email to execute_tool to fetch real data
        tool_result = execute_tool(tool_name, arguments, user_email)
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