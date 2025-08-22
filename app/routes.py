"""
Flask routes for web interface and API endpoints
"""

from flask import Blueprint, render_template, request, Response, jsonify, redirect, url_for, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, AdAccount, MCPSession
from app.mcp_protocol import MCPHandler
import json
import uuid
import jwt
from datetime import datetime, timedelta
import os
import time

# Blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
mcp_bp = Blueprint('mcp', __name__)

# Secret key for JWT tokens
JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')

@main_bp.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    return render_template('dashboard.html', user=current_user)

# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        login_user(user)
        return jsonify({'success': True, 'redirect': '/dashboard'})
    
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and handler"""
    if request.method == 'GET':
        return render_template('signup.html')
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Email already registered'}), 400
    
    # Create new user
    user = User(email=email, name=name)
    user.set_password(password)
    user.api_key = str(uuid.uuid4())
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return jsonify({'success': True, 'redirect': '/dashboard'})

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

# Meta Ads account management
@main_bp.route('/api/accounts', methods=['GET', 'POST'])
@login_required
def manage_accounts():
    """Manage Meta Ads accounts"""
    if request.method == 'GET':
        accounts = [acc.to_dict() for acc in current_user.ad_accounts]
        return jsonify({'accounts': accounts})
    
    # Add new account
    data = request.get_json()
    account_id = data.get('account_id')
    access_token = data.get('access_token')
    account_name = data.get('account_name', 'Unknown')
    
    # Check if account already exists
    existing = AdAccount.query.filter_by(
        user_id=current_user.id,
        account_id=account_id
    ).first()
    
    if existing:
        existing.access_token = access_token
        existing.is_active = True
    else:
        account = AdAccount(
            user_id=current_user.id,
            account_id=account_id,
            account_name=account_name,
            access_token=access_token
        )
        db.session.add(account)
    
    db.session.commit()
    return jsonify({'success': True})

@main_bp.route('/api/accounts/<int:account_id>', methods=['DELETE'])
@login_required
def delete_account(account_id):
    """Delete an ad account"""
    account = AdAccount.query.filter_by(
        id=account_id,
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(account)
    db.session.commit()
    
    return jsonify({'success': True})

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
                
                user = User.query.get(user_id)
                if not user:
                    # Check if any users exist
                    all_users = User.query.all()
                    print(f"SSE: User not found: {user_id}. Total users in DB: {len(all_users)}")
                    if all_users:
                        print(f"SSE: Available users: {[u.email for u in all_users]}")
                    yield f"data: {json.dumps({'error': 'Invalid user'})}\n\n"
                    return
                
                print(f"SSE: User found: {user.email}")
                
                # Create MCP session
                session_token = str(uuid.uuid4())
                mcp_session = MCPSession(
                    user_id=user.id,
                    session_token=session_token,
                    client_info=json.dumps({
                        'user_agent': user_agent,
                        'ip': remote_addr
                    })
                )
                db.session.add(mcp_session)
                db.session.commit()
                
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
        
        user = User.query.get(user_id)
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