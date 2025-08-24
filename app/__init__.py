from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
import os
import logging

login_manager = LoginManager()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['APP_NAME'] = 'Zane'
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize extensions
    login_manager.init_app(app)
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": True
        }
    })
    
    # Register blueprints
    from app.routes import main_bp, auth_bp
    from app.oauth_mcp_fixed import oauth_mcp_fixed_bp
    
    # Register non-conflicting routes first
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Register the FIXED OAuth MCP server that properly exposes tools
    app.register_blueprint(oauth_mcp_fixed_bp)
    
    # Register main routes (dashboard, etc) - avoid conflicts with MCP root
    app.register_blueprint(main_bp)
    
    return app