import os
from supabase import create_client, Client
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    _anon_client: Optional[Client] = None
    _service_client: Optional[Client] = None
    
    @classmethod
    def get_client(cls, use_service_role: bool = False) -> Client:
        """
        Get Supabase client.
        
        Args:
            use_service_role: If True, uses service role key (bypasses RLS).
                            If False, uses anon key (respects RLS).
        """
        url = os.getenv('SUPABASE_URL')
        
        if not url:
            raise ValueError("SUPABASE_URL must be set in environment variables")
        
        if use_service_role:
            # Use service role for admin operations (bypasses RLS)
            if cls._service_client is None:
                service_key = os.getenv('SUPABASE_SERVICE_KEY')
                if not service_key:
                    # Fallback to anon key if service key not available
                    logger.warning("Service role key not found, using anon key")
                    return cls.get_client(use_service_role=False)
                
                cls._service_client = create_client(url, service_key)
                logger.info("Supabase service client initialized")
            return cls._service_client
        else:
            # Use anon key for regular operations (respects RLS)
            if cls._anon_client is None:
                anon_key = os.getenv('SUPABASE_ANON_KEY')
                if not anon_key:
                    raise ValueError("SUPABASE_ANON_KEY must be set in environment variables")
                
                cls._anon_client = create_client(url, anon_key)
                logger.info("Supabase anon client initialized")
            return cls._anon_client
    
    @classmethod
    def sync_user_to_supabase(cls, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sync user data to Supabase.
        Uses service role to bypass RLS for user creation/update.
        """
        try:
            # Use service role for user management (bypasses RLS)
            client = cls.get_client(use_service_role=True)
            
            # Check if user exists
            result = client.table('users').select('*').eq('email', user_data['email']).execute()
            
            if result.data:
                # Update existing user
                updated = client.table('users').update({
                    'name': user_data.get('name'),
                    'google_id': user_data.get('google_id'),
                    'api_key': user_data.get('api_key'),
                    'password_hash': user_data.get('password_hash'),
                    'updated_at': 'now()'
                }).eq('email', user_data['email']).execute()
                logger.info(f"Updated user in Supabase: {user_data['email']}")
                return updated.data[0] if updated.data else None
            else:
                # Create new user
                created = client.table('users').insert({
                    'email': user_data['email'],
                    'name': user_data.get('name'),
                    'google_id': user_data.get('google_id'),
                    'password_hash': user_data.get('password_hash'),
                    'api_key': user_data.get('api_key')
                }).execute()
                logger.info(f"Created new user in Supabase: {user_data['email']}")
                return created.data[0] if created.data else None
                
        except Exception as e:
            logger.error(f"Error syncing user to Supabase: {str(e)}")
            logger.error(f"User data attempted: {user_data.get('email')}")
            logger.error(f"Full error details: {repr(e)}")
            raise e  # Re-raise to see the actual error
    
    @classmethod
    def sync_ad_account_to_supabase(cls, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sync ad account data to Supabase.
        Uses service role to ensure write access.
        """
        try:
            client = cls.get_client(use_service_role=True)
            
            # Get user's Supabase ID
            user_result = client.table('users').select('id').eq('email', account_data['user_email']).execute()
            if not user_result.data:
                logger.error(f"User not found in Supabase: {account_data['user_email']}")
                return None
            
            supabase_user_id = user_result.data[0]['id']
            
            # Check if ad account exists
            result = client.table('ad_accounts').select('*').eq('account_id', account_data['account_id']).eq('user_id', supabase_user_id).execute()
            
            if result.data:
                # Update existing ad account
                updated = client.table('ad_accounts').update({
                    'account_name': account_data.get('account_name'),
                    'access_token': account_data.get('access_token'),
                    'refresh_token': account_data.get('refresh_token'),
                    'is_active': account_data.get('is_active', True),
                    'last_synced': account_data.get('last_synced'),
                    'updated_at': 'now()'
                }).eq('account_id', account_data['account_id']).eq('user_id', supabase_user_id).execute()
                logger.info(f"Updated ad account in Supabase: {account_data['account_id']}")
                return updated.data[0] if updated.data else None
            else:
                # Create new ad account
                created = client.table('ad_accounts').insert({
                    'user_id': supabase_user_id,
                    'account_id': account_data['account_id'],
                    'account_name': account_data.get('account_name'),
                    'access_token': account_data.get('access_token'),
                    'refresh_token': account_data.get('refresh_token'),
                    'is_active': account_data.get('is_active', True),
                    'last_synced': account_data.get('last_synced')
                }).execute()
                logger.info(f"Created new ad account in Supabase: {account_data['account_id']}")
                return created.data[0] if created.data else None
                
        except Exception as e:
            logger.error(f"Error syncing ad account to Supabase: {str(e)}")
            return None
    
    @classmethod
    def get_user_from_supabase(cls, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from Supabase.
        Uses service role to bypass RLS for authentication.
        """
        try:
            # Use service role for authentication (needs to read any user)
            client = cls.get_client(use_service_role=True)
            result = client.table('users').select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user from Supabase: {str(e)}")
            return None
    
    @classmethod
    def get_ad_accounts_from_supabase(cls, user_email: str) -> list:
        """
        Get all ad accounts for a user from Supabase.
        Uses service role to ensure read access.
        """
        try:
            client = cls.get_client(use_service_role=True)
            
            # Get user's Supabase ID
            user_result = client.table('users').select('id').eq('email', user_email).execute()
            if not user_result.data:
                return []
            
            supabase_user_id = user_result.data[0]['id']
            
            # Get ad accounts
            result = client.table('ad_accounts').select('*').eq('user_id', supabase_user_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting ad accounts from Supabase: {str(e)}")
            return []