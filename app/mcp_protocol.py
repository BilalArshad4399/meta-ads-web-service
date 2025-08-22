"""
MCP (Model Context Protocol) implementation for Meta Ads
Provides SSE endpoint for Claude integration
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.models import User, AdAccount, MCPSession
from app.meta_client import MetaAdsClient

class MCPHandler:
    """Handles MCP protocol messages and tool execution"""
    
    def __init__(self, user: User):
        self.user = user
        self.meta_clients = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Meta API clients for all user's ad accounts"""
        for account in self.user.ad_accounts:
            if account.is_active:
                self.meta_clients[account.account_id] = MetaAdsClient(
                    access_token=account.access_token
                )
    
    def handle_message(self, message: Dict) -> Dict:
        """
        Handle incoming MCP message and return response
        """
        method = message.get('method')
        params = message.get('params', {})
        message_id = message.get('id')
        
        handlers = {
            'initialize': self._handle_initialize,
            'tools/list': self._handle_list_tools,
            'tools/call': self._handle_call_tool,
            'ping': self._handle_ping
        }
        
        handler = handlers.get(method)
        if not handler:
            return self._error_response(message_id, f"Unknown method: {method}")
        
        try:
            result = handler(params)
            return self._success_response(message_id, result)
        except Exception as e:
            return self._error_response(message_id, str(e))
    
    def _handle_initialize(self, params: Dict) -> Dict:
        """Initialize MCP session"""
        return {
            'protocolVersion': '1.0',
            'capabilities': {
                'tools': {},
                'prompts': {}
            },
            'serverInfo': {
                'name': 'zane-mcp',
                'version': '1.0.0'
            }
        }
    
    def _handle_list_tools(self, params: Dict) -> List[Dict]:
        """Return list of available tools"""
        tools = [
            {
                'name': 'get_account_roas',
                'description': 'Get ROAS metrics for Meta Ads accounts',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {
                            'type': 'string',
                            'description': 'Meta Ad Account ID (optional, uses default if not provided)'
                        },
                        'since': {
                            'type': 'string',
                            'description': 'Start date YYYY-MM-DD (optional, defaults to 30 days ago)'
                        },
                        'until': {
                            'type': 'string',
                            'description': 'End date YYYY-MM-DD (optional, defaults to today)'
                        }
                    }
                }
            },
            {
                'name': 'get_campaigns_roas',
                'description': 'Get ROAS for all campaigns',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {
                            'type': 'string',
                            'description': 'Meta Ad Account ID (optional)'
                        },
                        'since': {
                            'type': 'string',
                            'description': 'Start date YYYY-MM-DD'
                        },
                        'until': {
                            'type': 'string',
                            'description': 'End date YYYY-MM-DD'
                        }
                    }
                }
            },
            {
                'name': 'get_top_performing_ads',
                'description': 'Get top performing ads by ROAS',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {
                            'type': 'string',
                            'description': 'Meta Ad Account ID (optional)'
                        },
                        'since': {
                            'type': 'string',
                            'description': 'Start date YYYY-MM-DD'
                        },
                        'until': {
                            'type': 'string',
                            'description': 'End date YYYY-MM-DD'
                        },
                        'limit': {
                            'type': 'number',
                            'description': 'Number of top ads (default: 10)'
                        }
                    }
                }
            },
            {
                'name': 'get_all_accounts_summary',
                'description': 'Get ROAS summary for all connected accounts',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'since': {
                            'type': 'string',
                            'description': 'Start date YYYY-MM-DD'
                        },
                        'until': {
                            'type': 'string',
                            'description': 'End date YYYY-MM-DD'
                        }
                    }
                }
            }
        ]
        
        return {'tools': tools}
    
    def _handle_call_tool(self, params: Dict) -> Dict:
        """Execute a tool and return results"""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        # Set default dates if not provided
        if 'since' not in arguments:
            arguments['since'] = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if 'until' not in arguments:
            arguments['until'] = datetime.now().strftime('%Y-%m-%d')
        
        # Get default account if not specified
        if 'account_id' not in arguments and self.user.ad_accounts:
            default_account = self.user.ad_accounts[0]
            arguments['account_id'] = default_account.account_id
        
        tool_handlers = {
            'get_account_roas': self._get_account_roas,
            'get_campaigns_roas': self._get_campaigns_roas,
            'get_top_performing_ads': self._get_top_performing_ads,
            'get_all_accounts_summary': self._get_all_accounts_summary
        }
        
        handler = tool_handlers.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        result = handler(**arguments)
        
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps(result, indent=2)
                }
            ]
        }
    
    def _get_account_roas(self, account_id: str, since: str, until: str) -> Dict:
        """Get account ROAS metrics"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return client.get_account_roas(account_id, {'since': since, 'until': until})
    
    def _get_campaigns_roas(self, account_id: str, since: str, until: str) -> List[Dict]:
        """Get campaigns ROAS metrics"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return client.get_campaign_roas(account_id, {'since': since, 'until': until})
    
    def _get_top_performing_ads(self, account_id: str, since: str, until: str, limit: int = 10) -> List[Dict]:
        """Get top performing ads"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return client.get_top_performing_ads(account_id, {'since': since, 'until': until}, limit)
    
    def _get_all_accounts_summary(self, since: str, until: str) -> Dict:
        """Get summary for all accounts"""
        summary = {
            'accounts': [],
            'total_spend': 0,
            'total_revenue': 0,
            'overall_roas': 0,
            'date_range': {'since': since, 'until': until}
        }
        
        for account in self.user.ad_accounts:
            if account.is_active and account.account_id in self.meta_clients:
                try:
                    client = self.meta_clients[account.account_id]
                    account_data = client.get_account_roas(
                        account.account_id, 
                        {'since': since, 'until': until}
                    )
                    summary['accounts'].append(account_data)
                    summary['total_spend'] += account_data.get('spend', 0)
                    summary['total_revenue'] += account_data.get('revenue', 0)
                except Exception as e:
                    # Log error but continue with other accounts
                    print(f"Error fetching data for account {account.account_id}: {e}")
        
        if summary['total_spend'] > 0:
            summary['overall_roas'] = round(summary['total_revenue'] / summary['total_spend'], 2)
        
        return summary
    
    def _handle_ping(self, params: Dict) -> Dict:
        """Handle ping request"""
        return {'status': 'ok', 'timestamp': datetime.now().isoformat()}
    
    def _success_response(self, message_id: Optional[str], result: Any) -> Dict:
        """Create success response"""
        response = {
            'jsonrpc': '2.0',
            'result': result
        }
        if message_id:
            response['id'] = message_id
        return response
    
    def _error_response(self, message_id: Optional[str], error: str) -> Dict:
        """Create error response"""
        response = {
            'jsonrpc': '2.0',
            'error': {
                'code': -32603,
                'message': error
            }
        }
        if message_id:
            response['id'] = message_id
        return response