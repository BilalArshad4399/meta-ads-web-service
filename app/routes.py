"""
Flask routes for web interface and API endpoints
"""

from flask import Blueprint, render_template, request, Response, jsonify, redirect, url_for, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, AdAccount, MCPSession
from app.mcp_protocol import MCPHandler
import json
import uuid
import jwt
from datetime import datetime, timedelta
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

# Blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
mcp_bp = Blueprint('mcp', __name__)

# Secret key for JWT tokens
JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')

@main_bp.route('/home')
def index():
    """Landing page"""
    return render_template('index.html')

@main_bp.route('/debug/env')
def debug_env():
    """Debug endpoint to check environment variables"""
    import os
    env_status = {
        'SUPABASE_URL': 'SET' if os.getenv('SUPABASE_URL') else 'NOT SET',
        'SUPABASE_ANON_KEY': 'SET' if os.getenv('SUPABASE_ANON_KEY') else 'NOT SET',
        'SUPABASE_SERVICE_KEY': 'SET' if os.getenv('SUPABASE_SERVICE_KEY') else 'NOT SET',
        'SECRET_KEY': 'SET' if os.getenv('SECRET_KEY') else 'NOT SET',
        'URL_PREFIX': os.getenv('SUPABASE_URL', '')[:30] if os.getenv('SUPABASE_URL') else 'None'
    }
    return jsonify(env_status)

@main_bp.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated - used for OAuth auto-refresh"""
    return jsonify({
        'authenticated': current_user.is_authenticated if current_user else False,
        'email': current_user.email if current_user and current_user.is_authenticated else None
    })

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    return render_template('dashboard.html', user=current_user)

# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler using Supabase"""
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Get user from Supabase
    user = User.get_by_email(email)
    
    if user and user.check_password(password):
        login_user(user)
        return jsonify({'success': True, 'redirect': '/dashboard'})
    
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and handler using Supabase"""
    if request.method == 'GET':
        return render_template('signup.html')
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    try:
        # Check if user exists in Supabase
        existing_user = User.get_by_email(email)
        if existing_user:
            return jsonify({'success': False, 'error': 'Email already registered'}), 400
        
        # Create new user in Supabase
        user = User.create(email, name, password)
        
        if user and user.id:
            login_user(user)
            return jsonify({'success': True, 'redirect': '/dashboard'})
        else:
            logger.error(f"Failed to create user: {email}")
            return jsonify({'success': False, 'error': 'Failed to create user'}), 500
    except Exception as e:
        logger.error(f"Signup error for {email}: {str(e)}")
        return jsonify({'success': False, 'error': f'Signup failed: {str(e)}'}), 500

@auth_bp.route('/google')
def google_login():
    """Google OAuth login handler"""
    # This would integrate with Google OAuth
    # For now, returning a placeholder
    return jsonify({'error': 'Google OAuth not configured'}), 501

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout handler"""
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/facebook/callback')
def facebook_callback():
    """Handle Facebook OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        return render_template('oauth_callback.html', 
                             success=False, 
                             error=error)
    
    if not code:
        return render_template('oauth_callback.html', 
                             success=False, 
                             error='No authorization code received')
    
    # Pass the code back to the parent window
    return render_template('oauth_callback.html', 
                         success=True, 
                         code=code, 
                         state=state)

# Facebook OAuth API endpoints
@main_bp.route('/api/facebook/config')
@login_required
def facebook_config():
    """Get Facebook app configuration"""
    app_id = os.getenv('FACEBOOK_APP_ID', '')
    if not app_id:
        logger.warning("FACEBOOK_APP_ID not configured in environment")
    return jsonify({'app_id': app_id})

@main_bp.route('/api/facebook/exchange-token', methods=['POST'])
@login_required
def facebook_exchange_token():
    """Exchange Facebook authorization code for access token"""
    data = request.get_json()
    code = data.get('code')
    state = data.get('state')
    
    if not code:
        return jsonify({'error': 'No authorization code provided'}), 400
    
    try:
        # Exchange code for access token
        app_id = os.getenv('FACEBOOK_APP_ID')
        app_secret = os.getenv('FACEBOOK_APP_SECRET')
        redirect_uri = f"{request.host_url}auth/facebook/callback"
        
        # Exchange code for token using Marketing API version
        token_url = f"https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            'client_id': app_id,
            'client_secret': app_secret,
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        import requests
        response = requests.get(token_url, params=params)
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to exchange token'}), 400
            
        token_data = response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            return jsonify({'error': 'No access token received'}), 400
        
        # Get user's ad accounts
        accounts_url = f"https://graph.facebook.com/v18.0/me/adaccounts"
        accounts_params = {
            'access_token': access_token,
            'fields': 'id,name,account_status,currency,business_name'
        }
        
        accounts_response = requests.get(accounts_url, params=accounts_params)
        
        if accounts_response.status_code != 200:
            return jsonify({'error': 'Failed to fetch ad accounts'}), 400
            
        accounts_data = accounts_response.json()
        
        # Save accounts to database
        for account in accounts_data.get('data', []):
            # Remove 'act_' prefix from account ID
            account_id = account['id'].replace('act_', '')
            
            # Save or update account
            AdAccount.create_or_update(
                user_id=current_user.id,
                account_id=account_id,
                account_name=account.get('name', 'Unnamed Account'),
                access_token=access_token,
                is_active=account.get('account_status', 1) == 1
            )

        # Test if we can actually get data from the accounts
        warnings = []
        test_results = []

        for account in accounts_data.get('data', []):
            account_id = account['id'].replace('act_', '')

            # Test insights API access - check last 90 days for any data
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)

            test_url = f"https://graph.facebook.com/v18.0/act_{account_id}/insights"
            test_params = {
                'access_token': access_token,
                'fields': 'spend,impressions',
                'time_range': f'{{"since":"{start_date.strftime("%Y-%m-%d")}","until":"{end_date.strftime("%Y-%m-%d")}"}}',
                'level': 'account'
            }

            try:
                test_response = requests.get(test_url, params=test_params)
                test_data = test_response.json()

                if 'error' in test_data:
                    error_msg = test_data['error'].get('message', 'Unknown error')
                    error_code = test_data['error'].get('code', '')

                    if 'no data available' in error_msg.lower() or 'no results' in error_msg.lower():
                        warnings.append({
                            'account': account.get('name', account_id),
                            'type': 'NO_DATA',
                            'message': f"No ads data available for {account.get('name', 'this account')}. This account may not have any campaigns or ad spend yet."
                        })
                    elif error_code == 100:
                        warnings.append({
                            'account': account.get('name', account_id),
                            'type': 'PERMISSION_ERROR',
                            'message': f"Permission denied for {account.get('name', 'this account')}. Please ensure you have admin or advertiser access."
                        })
                    elif error_code == 190:
                        warnings.append({
                            'account': account.get('name', account_id),
                            'type': 'TOKEN_ERROR',
                            'message': f"Token issue for {account.get('name', 'this account')}. Please try reconnecting."
                        })
                    else:
                        warnings.append({
                            'account': account.get('name', account_id),
                            'type': 'API_ERROR',
                            'message': f"API Error ({error_code}): {error_msg}"
                        })

                    test_results.append({
                        'account_id': account_id,
                        'status': 'error',
                        'error': error_msg
                    })
                elif not test_data.get('data') or len(test_data.get('data', [])) == 0:
                    warnings.append({
                        'account': account.get('name', account_id),
                        'type': 'NO_DATA',
                        'message': f"No campaign data found for {account.get('name', 'this account')}. The account may be new or have no active campaigns."
                    })
                    test_results.append({
                        'account_id': account_id,
                        'status': 'no_data'
                    })
                else:
                    # Data is available
                    test_results.append({
                        'account_id': account_id,
                        'status': 'success',
                        'has_data': True
                    })

            except Exception as e:
                warnings.append({
                    'account': account.get('name', account_id),
                    'type': 'CONNECTION_ERROR',
                    'message': f"Could not connect to {account.get('name', 'this account')}: {str(e)}"
                })
                test_results.append({
                    'account_id': account_id,
                    'status': 'error',
                    'error': str(e)
                })

        return jsonify({
            'success': True,
            'accounts_added': len(accounts_data.get('data', [])),
            'warnings': warnings,
            'test_results': test_results,
            'debug_info': {
                'total_accounts': len(accounts_data.get('data', [])),
                'accounts_with_errors': len([r for r in test_results if r['status'] == 'error']),
                'accounts_with_no_data': len([r for r in test_results if r['status'] == 'no_data']),
                'accounts_with_data': len([r for r in test_results if r['status'] == 'success'])
            }
        })
        
    except Exception as e:
        logger.error(f"Facebook token exchange error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Meta Ads account management
@main_bp.route('/api/accounts', methods=['GET', 'POST'])
@login_required
def manage_accounts():
    """Manage Meta Ads accounts"""
    if request.method == 'GET':
        accounts = [acc.to_dict() for acc in current_user.get_ad_accounts()]
        return jsonify({'accounts': accounts})
    
    # POST method is deprecated - use Facebook OAuth instead
    # Manual token addition is no longer supported for security
    return jsonify({
        'error': 'Manual account addition is disabled. Please use "Connect with Facebook" button to authorize your accounts.'
    }), 400

@main_bp.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@login_required
def delete_account(account_id):
    """Delete an ad account"""
    # Get user's accounts
    accounts = current_user.get_ad_accounts()
    
    # Find the account to delete
    account_to_delete = None
    for acc in accounts:
        if acc.id == account_id:
            account_to_delete = acc
            break
    
    if not account_to_delete:
        return jsonify({'error': 'Account not found'}), 404
    
    # Delete from Supabase
    try:
        from app.supabase_client import SupabaseClient
        client = SupabaseClient.get_client(use_service_role=True)
        client.table('ad_accounts').delete().eq('id', account_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        return jsonify({'error': 'Failed to delete account'}), 500

# MCP SSE endpoint
@mcp_bp.route('/sse', methods=['GET', 'POST'])
def mcp_sse():
    """
    Server-Sent Events endpoint for MCP protocol
    This is what Claude connects to
    """
    
    # Extract all request data BEFORE entering generator
    token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    user_agent = request.headers.get('User-Agent', '')
    remote_addr = request.remote_addr
    app = current_app._get_current_object()  # Get the actual app instance
    
    def generate():
        with app.app_context():
            if not token:
                print("SSE: No token provided")
                yield f"data: {json.dumps({'error': 'No token provided'})}\n\n"
                return
            
            try:
                # Decode JWT token to get user ID
                print(f"SSE: Attempting to decode token with secret: {JWT_SECRET[:10]}...")
                payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
                user_id = payload.get('user_id')
                print(f"SSE: Token decoded successfully, user_id: {user_id}")
                
                user = User.get_by_id(user_id)
                if not user:
                    print(f"SSE: User not found: {user_id}")
                    yield f"data: {json.dumps({'error': 'Invalid user'})}\n\n"
                    return
                
                print(f"SSE: User found: {user.email}")
                
                # Create MCP session
                session_token = str(uuid.uuid4())
                mcp_session = MCPSession()
                mcp_session.user_id = user.id
                mcp_session.session_token = session_token
                mcp_session.client_info = json.dumps({
                    'user_agent': user_agent,
                    'ip': remote_addr
                })
                mcp_session.save()
                
                # Initialize MCP handler
                handler = MCPHandler(user)
                
                # Send initialization message
                init_response = handler.handle_message({
                    'method': 'initialize',
                    'params': {},
                    'id': 1
                })
                print(f"SSE: Sending init response: {init_response}")
                yield f"data: {json.dumps(init_response)}\n\n"
                
                # Send initialized notification (no id for notifications)
                initialized_event = {
                    'jsonrpc': '2.0',
                    'method': 'initialized',
                    'params': {}
                }
                print(f"SSE: Sending initialized event")
                yield f"data: {json.dumps(initialized_event)}\n\n"
                
                # Send tools/list response
                tools_response = handler.handle_message({
                    'method': 'tools/list',
                    'params': {},
                    'id': 2
                })
                print(f"SSE: Sending tools list: {len(tools_response.get('result', {}).get('tools', []))} tools")
                yield f"data: {json.dumps(tools_response)}\n\n"
                
                # Keep connection open for Claude to send commands
                # Claude will close the connection when done
                print("SSE: Connection established, waiting for Claude commands...")
                
            except jwt.ExpiredSignatureError as e:
                print(f"SSE: Token expired: {e}")
                yield f"data: {json.dumps({'error': 'Token expired'})}\n\n"
            except jwt.InvalidTokenError as e:
                print(f"SSE: Invalid token: {e}")
                yield f"data: {json.dumps({'error': 'Invalid token'})}\n\n"
            except Exception as e:
                print(f"SSE: Unexpected error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response

@mcp_bp.route('/health', methods=['GET'])
def mcp_health():
    """Health check endpoint for MCP"""
    return jsonify({
        'status': 'ok',
        'service': 'Zane MCP Server',
        'timestamp': datetime.utcnow().isoformat()
    })

@mcp_bp.route('/rpc', methods=['POST'])
def mcp_rpc():
    """
    JSON-RPC endpoint for MCP protocol
    Alternative to SSE for request-response pattern
    """
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'Invalid user'}), 401
        
        # Handle MCP message
        handler = MCPHandler(user)
        message = request.get_json()
        response = handler.handle_message(message)
        
        return jsonify(response)
        
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/health')
def health_check():
    """Lightweight health check endpoint for monitoring"""
    return jsonify({'status': 'healthy', 'service': 'zane-mcp'}), 200

@main_bp.route('/api/integration-url')
@login_required
def get_integration_url():
    """Get the integration URL for Claude"""
    # For OAuth flow, we just provide the base URL
    # Claude will discover the endpoints via .well-known
    base_url = request.host_url.rstrip('/')
    
    print(f"Integration URL for {current_user.email}: {base_url}")
    
    return jsonify({
        'integration_name': 'Zane - Meta Ads',
        'integration_url': base_url,
        'description': 'Connect Claude to your Meta Ads accounts'
    })