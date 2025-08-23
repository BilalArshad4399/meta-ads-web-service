from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from flask_migrate import Migrate
import os
import logging

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config['APP_NAME'] = 'Zane'
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///meta_ads.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
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
    from app.oauth_mcp import oauth_mcp_bp
    
    # Register non-conflicting routes first
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Register the OAuth MCP server (includes OAuth flow and disconnect support)
    app.register_blueprint(oauth_mcp_bp)
    
    # Register main routes (dashboard, etc) - avoid conflicts with MCP root
    app.register_blueprint(main_bp)
    
    return app