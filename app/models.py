from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import login_manager
from app.supabase_client import SupabaseClient
import uuid
import logging

logger = logging.getLogger(__name__)

class User(UserMixin):
    """User model that works directly with Supabase"""
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('id')
            self.email = data.get('email')
            self.name = data.get('name')
            self.google_id = data.get('google_id')
            self.password_hash = data.get('password_hash')
            self.api_key = data.get('api_key')
            self.created_at = data.get('created_at')
        else:
            self.id = None
            self.email = None
            self.name = None
            self.google_id = None
            self.password_hash = None
            self.api_key = None
            self.created_at = None
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def save(self):
        """Save user to Supabase"""
        user_data = {
            'email': self.email,
            'name': self.name,
            'google_id': self.google_id,
            'password_hash': self.password_hash,
            'api_key': self.api_key
        }
        result = SupabaseClient.sync_user_to_supabase(user_data)
        if result:
            self.id = result.get('id')
        return result
    
    @classmethod
    def get_by_email(cls, email):
        """Get user by email from Supabase"""
        data = SupabaseClient.get_user_from_supabase(email)
        if data:
            return cls(data)
        return None
    
    @classmethod
    def get_by_id(cls, user_id):
        """Get user by ID from Supabase"""
        try:
            client = SupabaseClient.get_client()
            result = client.table('users').select('*').eq('id', user_id).execute()
            if result.data:
                return cls(result.data[0])
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
        return None
    
    @classmethod
    def create(cls, email, name, password):
        """Create a new user"""
        user = cls()
        user.email = email
        user.name = name
        user.set_password(password)
        user.api_key = str(uuid.uuid4())
        result = user.save()
        if result:
            user.id = result.get('id')
            return user
        return None
    
    def get_ad_accounts(self):
        """Get all ad accounts for this user"""
        return AdAccount.get_by_user_email(self.email)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at,
            'has_ad_accounts': len(self.get_ad_accounts()) > 0
        }

class AdAccount:
    """Ad Account model that works directly with Supabase"""
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('id')
            self.user_id = data.get('user_id')
            self.account_id = data.get('account_id')
            self.account_name = data.get('account_name')
            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')
            self.token_expires_at = data.get('token_expires_at')
            self.is_active = data.get('is_active', True)
            self.last_synced = data.get('last_synced')
            self.created_at = data.get('created_at')
    
    def save(self, user_email):
        """Save ad account to Supabase"""
        account_data = {
            'user_email': user_email,
            'account_id': self.account_id,
            'account_name': self.account_name,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'is_active': self.is_active,
            'last_synced': self.last_synced
        }
        result = SupabaseClient.sync_ad_account_to_supabase(account_data)
        if result:
            self.id = result.get('id')
        return result
    
    @classmethod
    def get_by_user_email(cls, user_email):
        """Get all ad accounts for a user"""
        accounts_data = SupabaseClient.get_ad_accounts_from_supabase(user_email)
        return [cls(data) for data in accounts_data]
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'account_name': self.account_name,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'last_synced': self.last_synced
        }

class MCPSession:
    """MCP Session model that works directly with Supabase"""
    
    def __init__(self, data=None):
        if data:
            self.id = data.get('id')
            self.user_id = data.get('user_id')
            self.session_token = data.get('session_token')
            self.client_info = data.get('client_info')
            self.last_activity = data.get('last_activity')
            self.is_active = data.get('is_active', True)
            self.created_at = data.get('created_at')
    
    def save(self):
        """Save MCP session to Supabase"""
        try:
            client = SupabaseClient.get_client()
            session_data = {
                'user_id': self.user_id,
                'session_token': self.session_token,
                'client_info': self.client_info,
                'is_active': self.is_active
            }
            
            # Check if session exists
            result = client.table('mcp_sessions').select('*').eq('session_token', self.session_token).execute()
            
            if result.data:
                # Update existing session
                updated = client.table('mcp_sessions').update({
                    'last_activity': 'now()',
                    'is_active': self.is_active
                }).eq('session_token', self.session_token).execute()
                return updated.data[0] if updated.data else None
            else:
                # Create new session
                created = client.table('mcp_sessions').insert(session_data).execute()
                if created.data:
                    self.id = created.data[0].get('id')
                return created.data[0] if created.data else None
        except Exception as e:
            logger.error(f"Error saving MCP session: {e}")
            return None
    
    @classmethod
    def get_by_token(cls, token):
        """Get session by token"""
        try:
            client = SupabaseClient.get_client()
            result = client.table('mcp_sessions').select('*').eq('session_token', token).eq('is_active', True).execute()
            if result.data:
                return cls(result.data[0])
        except Exception as e:
            logger.error(f"Error getting session: {e}")
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))