"""
MCP Server implementation with proper HTTP+SSE transport
"""

from flask import Blueprint, request, Response, jsonify, stream_with_context
from app import db
from app.models import User, MCPSession
from app.mcp_protocol import MCPHandler
import json
import jwt
import uuid
from datetime import datetime
import os

mcp_server_bp = Blueprint('mcp_server', __name__)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret-key')

def verify_token(token):
    """Verify JWT token and return user"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload.get('user_id')
        user = User.query.get(user_id)
        return user
    except:
        return None

@mcp_server_bp.route('/', methods=['POST'])
def handle_mcp_request():
    """
    Handle MCP JSON-RPC requests
    This endpoint processes commands from Claude
    """
    # Get token from header or query params
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header else request.args.get('token')
    
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    user = verify_token(token)
    if not user:
        return jsonify({'error': 'Invalid token'}), 401
    
    # Get the JSON-RPC request
    try:
        message = request.get_json()
        print(f"MCP: Received message: {message}")
        
        # Handle the message using MCP handler
        handler = MCPHandler(user)
        response = handler.handle_message(message)
        
        print(f"MCP: Sending response: {response}")
        return jsonify(response)
        
    except Exception as e:
        print(f"MCP Error: {e}")
        return jsonify({
            'jsonrpc': '2.0',
            'error': {
                'code': -32603,
                'message': str(e)
            },
            'id': message.get('id') if 'message' in locals() else None
        }), 500

@mcp_server_bp.route('/sse', methods=['GET'])
def handle_mcp_sse():
    """
    SSE endpoint for server-initiated messages
    """
    token = request.args.get('token')
    
    if not token:
        return Response('No token provided', status=401)
    
    user = verify_token(token)
    if not user:
        return Response('Invalid token', status=401)
    
    def generate():
        # Send connection established event
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        
        # Keep connection alive
        while True:
            # In a real implementation, you'd check for server events here
            # For now, just send periodic heartbeats
            import time
            time.sleep(30)
            yield f": heartbeat\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@mcp_server_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Zane MCP Server',
        'transport': 'http+sse',
        'timestamp': datetime.utcnow().isoformat()
    })