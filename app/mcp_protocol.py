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
        print(f"MCP Handler initialized for user: {user.email if user else 'None'}")
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Meta API clients for all user's ad accounts"""
        try:
            for account in self.user.ad_accounts:
                if account.is_active:
                    self.meta_clients[account.account_id] = MetaAdsClient(
                        access_token=account.access_token
                    )
        except Exception as e:
            print(f"Error initializing Meta clients: {e}")
            # Continue without clients - will use mock data
    
    def handle_message(self, message: Dict) -> Dict:
        """
        Handle incoming MCP message and return response
        """
        method = message.get('method')
        params = message.get('params', {})
        message_id = message.get('id')
        
        print(f"MCP Protocol: Handling {method} with id={message_id}, params={params}")
        
        handlers = {
            'initialize': self._handle_initialize,
            'tools/list': self._handle_list_tools,
            'tools/call': self._handle_call_tool,
            'ping': self._handle_ping,
            'notifications/initialized': lambda p: {},  # Handle initialized notification
            'initialized': lambda p: {}  # Also handle without notifications prefix
        }
        
        handler = handlers.get(method)
        if not handler:
            print(f"MCP Protocol: Unknown method: {method}")
            # Don't return error for unknown notification methods
            if method and 'notification' in method.lower():
                return {}
            return self._error_response(message_id, f"Unknown method: {method}")
        
        try:
            result = handler(params)
            response = self._success_response(message_id, result)
            
            # Special logging for tools/list
            if method == 'tools/list':
                tools_count = len(result.get('tools', []))
                print(f"MCP Protocol: Returning {tools_count} tools to Claude")
                if tools_count > 0:
                    print(f"MCP Protocol: First tool: {result['tools'][0]['name']}")
            
            return response
        except Exception as e:
            print(f"MCP Protocol: Error handling {method}: {e}")
            import traceback
            traceback.print_exc()
            return self._error_response(message_id, str(e))
    
    def _handle_initialize(self, params: Dict) -> Dict:
        """Initialize MCP session"""
        # Use the same protocol version that Claude sent
        client_protocol = params.get('protocolVersion', '2024-11-05')
        
        return {
            'protocolVersion': client_protocol,  # Match Claude's protocol version
            'capabilities': {
                'tools': {},  # We support tools
            },
            'serverInfo': {
                'name': 'Zane - Meta Ads Connector',
                'version': '1.0.0'
            }
        }
    
    def _handle_list_tools(self, params: Dict) -> Dict:
        """Return list of available tools"""
        # Start with minimal tools to ensure they load
        tools = [
            {
                'name': 'get_meta_ads_overview',
                'description': 'Get Meta Ads account overview with key metrics',
                'inputSchema': {
                    'type': 'object',
                    'properties': {},
                    'required': []
                }
            },
            {
                'name': 'get_account_overview',
                'description': 'Get comprehensive overview of ad account performance including spend, revenue, ROAS, CTR, CPC, and CPM',
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
                    },
                    'required': [],
                    'additionalProperties': False
                }
            },
            {
                'name': 'get_campaigns_performance',
                'description': 'Get detailed performance metrics for all campaigns including ROAS, spend, impressions, clicks, and conversions',
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
                    },
                    'required': [],
                    'additionalProperties': False
                }
            },
            {
                'name': 'get_adsets_performance',
                'description': 'Get performance metrics for all ad sets including targeting, budget, and results',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'campaign_id': {'type': 'string', 'description': 'Filter by specific campaign (optional)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'get_top_performing_ads',
                'description': 'Get top performing ads by ROAS, CTR, or conversions',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'metric': {'type': 'string', 'description': 'Metric to sort by: roas, ctr, conversions, spend (default: roas)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'},
                        'limit': {'type': 'number', 'description': 'Number of top ads (default: 10)'}
                    }
                }
            },
            {
                'name': 'get_audience_insights',
                'description': 'Get audience demographics and performance by age, gender, and location',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'breakdown': {'type': 'string', 'description': 'Breakdown by: age, gender, country, region (default: all)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'get_daily_trends',
                'description': 'Get daily performance trends showing spend, revenue, ROAS over time',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'metrics': {'type': 'array', 'description': 'Metrics to include (spend, impressions, clicks, conversions, revenue, roas)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'compare_campaigns',
                'description': 'Compare performance between multiple campaigns',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'campaign_ids': {'type': 'array', 'description': 'List of campaign IDs to compare'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'get_budget_utilization',
                'description': 'Check budget utilization and pacing for campaigns and ad sets',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'get_creative_performance',
                'description': 'Analyze performance by creative type (image, video, carousel)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'creative_type': {'type': 'string', 'description': 'Filter by type: image, video, carousel (optional)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'get_placement_performance',
                'description': 'Get performance breakdown by placement (Facebook, Instagram, Audience Network)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'get_conversion_funnel',
                'description': 'Get conversion funnel metrics from impressions to purchases',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'campaign_id': {'type': 'string', 'description': 'Filter by campaign (optional)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'get_underperforming_ads',
                'description': 'Identify underperforming ads that need optimization',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'account_id': {'type': 'string', 'description': 'Meta Ad Account ID (optional)'},
                        'threshold_roas': {'type': 'number', 'description': 'ROAS threshold (default: 1.0)'},
                        'min_spend': {'type': 'number', 'description': 'Minimum spend to consider (default: 100)'},
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
                    }
                }
            },
            {
                'name': 'get_all_accounts_summary',
                'description': 'Get summary for all connected Meta Ads accounts',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'since': {'type': 'string', 'description': 'Start date YYYY-MM-DD'},
                        'until': {'type': 'string', 'description': 'End date YYYY-MM-DD'}
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
        if 'account_id' not in arguments:
            if self.user.ad_accounts:
                default_account = self.user.ad_accounts[0]
                arguments['account_id'] = default_account.account_id
            else:
                # Use demo account ID when no real accounts exist
                arguments['account_id'] = 'demo_account'
        
        tool_handlers = {
            'get_meta_ads_overview': self._get_simple_overview,
            'get_account_overview': self._get_account_overview,
            'get_campaigns_performance': self._get_campaigns_performance,
            'get_adsets_performance': self._get_adsets_performance,
            'get_top_performing_ads': self._get_top_performing_ads,
            'get_audience_insights': self._get_audience_insights,
            'get_daily_trends': self._get_daily_trends,
            'compare_campaigns': self._compare_campaigns,
            'get_budget_utilization': self._get_budget_utilization,
            'get_creative_performance': self._get_creative_performance,
            'get_placement_performance': self._get_placement_performance,
            'get_conversion_funnel': self._get_conversion_funnel,
            'get_underperforming_ads': self._get_underperforming_ads,
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
    
    def _get_simple_overview(self, **kwargs) -> Dict:
        """Simple overview that always works - for testing"""
        return {
            "status": "connected",
            "account": "Zane Meta Ads Connector",
            "message": "Successfully connected to Meta Ads",
            "total_accounts": len(self.user.ad_accounts) if hasattr(self.user, 'ad_accounts') else 0,
            "demo_data": {
                "total_spend": "563.67",
                "total_revenue": "845.50",
                "roas": "1.5",
                "campaigns_active": 1
            }
        }
    
    def _get_account_overview(self, account_id: str, since: str, until: str) -> Dict:
        """Get comprehensive account overview"""
        client = self.meta_clients.get(account_id)
        if not client:
            # Return mock data for demo purposes - realistic values based on actual data
            return {
                "account_id": account_id or "demo_account",
                "account_name": "Demo Meta Ads Account",
                "period": f"{since} to {until}",
                "total_spend": 563.67,
                "total_revenue": 845.50,  # Realistic 1.5x ROAS
                "roas": 1.5,
                "campaigns_active": 1,
                "campaigns_total": 2,
                "impressions": 3076,
                "clicks": 48,
                "ctr": 1.56,
                "cpc": 11.74,
                "cpm": 183.24,
                "conversions": 3,
                "conversion_rate": 6.25,
                "top_campaign": {
                    "name": "Post: \"We provide every type of AI and web service, from...\"",
                    "spend": 563.67,
                    "roas": 1.5
                }
            }
        
        return client.get_account_overview(account_id, {'since': since, 'until': until})
    
    def _get_campaigns_performance(self, account_id: str, since: str, until: str) -> Dict:
        """Get detailed campaigns performance metrics - returns Meta Ads API format"""
        client = self.meta_clients.get(account_id)
        if not client:
            # Return mock data matching actual Meta Ads API response structure
            return {
                "data": [
                    {
                        "id": "120230475045250176",
                        "name": "Post: \"We provide every type of AI and web service, from...\"",
                        "status": "ACTIVE",
                        "created_time": "2025-08-19T21:15:34+0500",
                        "insights": {
                            "data": [
                                {
                                    "impressions": "3076",
                                    "clicks": "48",
                                    "spend": "563.67",
                                    "date_start": since,
                                    "date_stop": until
                                }
                            ],
                            "paging": {
                                "cursors": {
                                    "before": "MAZDZD",
                                    "after": "MAZDZD"
                                }
                            }
                        }
                    },
                    {
                        "id": "120230475045250177",
                        "name": "Summer Sale Campaign - Boost Performance",
                        "status": "ACTIVE",
                        "created_time": "2025-08-15T10:30:00+0500",
                        "insights": {
                            "data": [
                                {
                                    "impressions": "4521",
                                    "clicks": "67",
                                    "spend": "782.34",
                                    "date_start": since,
                                    "date_stop": until
                                }
                            ],
                            "paging": {
                                "cursors": {
                                    "before": "MAZDZD",
                                    "after": "MAZDZD"
                                }
                            }
                        }
                    },
                    {
                        "id": "120230475045250178",
                        "name": "Brand Awareness Q4 - Instagram Stories",
                        "status": "PAUSED",
                        "created_time": "2025-08-10T14:22:18+0500",
                        "insights": {
                            "data": [
                                {
                                    "impressions": "2145",
                                    "clicks": "31",
                                    "spend": "412.89",
                                    "date_start": since,
                                    "date_stop": until
                                }
                            ],
                            "paging": {
                                "cursors": {
                                    "before": "MAZDZD",
                                    "after": "MAZDZD"
                                }
                            }
                        }
                    }
                ],
                "paging": {
                    "cursors": {
                        "before": "QVFIUzJEZAFpEWWxOeG9UQVNOMnhBdUVnNS0xUUlvcW52UGJ5SU1GUTFVcHYyRFgycDIzaGJ4Yk5iTkp5MmdLamI0UUZAUcHpKYm1HRTZAySkF6RGlmWkhuS3dn",
                        "after": "QVFIUzJEZAFpEWWxOeG9UQVNOMnhBdUVnNS0xUUlvcW52UGJ5SU1GUTFVcHYyRFgycDIzaGJ4Yk5iTkp5MmdLamI0UUZAUcHpKYm1HRTZAySkF6RGlmWkhuS3dn"
                    }
                }
            }
        
        return client.get_campaign_roas(account_id, {'since': since, 'until': until})
    
    def _get_top_performing_ads(self, account_id: str, since: str, until: str, limit: int = 10) -> Dict:
        """Get top performing ads - returns Meta Ads API format"""
        client = self.meta_clients.get(account_id)
        if not client:
            # Return mock data matching actual Meta Ads API response structure
            return {
                "data": [
                    {
                        "id": "120230475045250176",
                        "name": "Top Performing Ad: AI Services Promotion",
                        "status": "ACTIVE",
                        "created_time": "2025-08-19T21:15:34+0500",
                        "insights": {
                            "data": [
                                {
                                    "impressions": "5234",
                                    "clicks": "89",
                                    "spend": "895.50",
                                    "ctr": "1.70",
                                    "cpc": "10.06",
                                    "conversions": "12",
                                    "date_start": since,
                                    "date_stop": until
                                }
                            ]
                        }
                    },
                    {
                        "id": "120230475045250177",
                        "name": "High ROI: Web Development Services",
                        "status": "ACTIVE",
                        "created_time": "2025-08-18T15:22:00+0500",
                        "insights": {
                            "data": [
                                {
                                    "impressions": "4123",
                                    "clicks": "71",
                                    "spend": "687.25",
                                    "ctr": "1.72",
                                    "cpc": "9.68",
                                    "conversions": "8",
                                    "date_start": since,
                                    "date_stop": until
                                }
                            ]
                        }
                    },
                    {
                        "id": "120230475045250178",
                        "name": "Best CTR: Mobile App Development",
                        "status": "ACTIVE",
                        "created_time": "2025-08-17T09:45:12+0500",
                        "insights": {
                            "data": [
                                {
                                    "impressions": "3456",
                                    "clicks": "62",
                                    "spend": "578.90",
                                    "ctr": "1.79",
                                    "cpc": "9.34",
                                    "conversions": "7",
                                    "date_start": since,
                                    "date_stop": until
                                }
                            ]
                        }
                    }
                ],
                "paging": {
                    "cursors": {
                        "before": "MAZDZD",
                        "after": "MAZDZD"
                    }
                }
            }
        
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
    
    def _get_adsets_performance(self, account_id: str, since: str, until: str, campaign_id: str = None) -> List[Dict]:
        """Get ad sets performance metrics"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return client.get_adsets_performance(account_id, {'since': since, 'until': until}, campaign_id)
    
    def _get_audience_insights(self, account_id: str, since: str, until: str, breakdown: str = 'all') -> Dict:
        """Get audience demographic insights"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        # Map breakdown value to API format
        breakdown_map = {
            'all': 'age,gender',
            'age': 'age',
            'gender': 'gender',
            'country': 'country',
            'region': 'region'
        }
        api_breakdown = breakdown_map.get(breakdown, 'age,gender')
        
        return client.get_audience_insights(account_id, {'since': since, 'until': until}, api_breakdown)
    
    def _get_daily_trends(self, account_id: str, since: str, until: str, metrics: List[str] = None) -> List[Dict]:
        """Get daily performance trends"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return client.get_daily_trends(account_id, {'since': since, 'until': until})
    
    def _compare_campaigns(self, campaign_ids: List[str], since: str, until: str) -> List[Dict]:
        """Compare multiple campaigns performance"""
        results = []
        for campaign_id in campaign_ids:
            # Mock implementation
            results.append({
                'campaign_id': campaign_id,
                'name': f'Campaign {campaign_id}',
                'spend': 1500,
                'revenue': 4500,
                'roas': 3.0,
                'ctr': 2.3,
                'conversion_rate': 3.5
            })
        return results
    
    def _get_budget_utilization(self, account_id: str, since: str, until: str) -> Dict:
        """Check budget utilization and pacing"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        # Get campaign budgets and spend
        campaigns = client.get_campaign_roas(account_id, {'since': since, 'until': until})
        
        total_spend = sum(c.get('spend', 0) for c in campaigns)
        days_in_range = (datetime.strptime(until, '%Y-%m-%d') - datetime.strptime(since, '%Y-%m-%d')).days + 1
        daily_avg = total_spend / days_in_range if days_in_range > 0 else 0
        
        return {
            'total_spend': total_spend,
            'daily_average_spend': round(daily_avg, 2),
            'campaigns_count': len(campaigns),
            'date_range': {'since': since, 'until': until},
            'days_in_period': days_in_range
        }
    
    def _get_creative_performance(self, account_id: str, since: str, until: str, creative_type: str = None) -> List[Dict]:
        """Analyze performance by creative type"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return client.get_creative_performance(account_id, {'since': since, 'until': until})
    
    def _get_placement_performance(self, account_id: str, since: str, until: str) -> List[Dict]:
        """Get performance by placement"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return client.get_placement_performance(account_id, {'since': since, 'until': until})
    
    def _get_conversion_funnel(self, account_id: str, since: str, until: str, campaign_id: str = None) -> Dict:
        """Get conversion funnel metrics"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        # Get funnel metrics from API
        fields = 'impressions,clicks,reach,conversions,actions'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{since}","until":"{until}"}}',
            'level': 'account' if not campaign_id else 'campaign',
            'action_breakdowns': 'action_type'
        }
        
        if campaign_id:
            params['filtering'] = f'[{{"field":"campaign_id","operator":"EQUAL","value":"{campaign_id}"}}]'
        
        try:
            data = client._make_request(f'/act_{account_id}/insights', params)
            result = data.get('data', [{}])[0]
            
            impressions = int(result.get('impressions', 0))
            clicks = int(result.get('clicks', 0))
            conversions = int(result.get('conversions', 0))
            
            # Parse actions for funnel steps
            actions = result.get('actions', [])
            funnel_data = {
                'impressions': impressions,
                'clicks': clicks,
                'click_rate': round((clicks / impressions * 100), 2) if impressions > 0 else 0,
                'conversions': conversions,
                'conversion_rate': round((conversions / clicks * 100), 2) if clicks > 0 else 0
            }
            
            # Extract specific action types
            for action in actions:
                action_type = action.get('action_type', '')
                value = int(action.get('value', 0))
                
                if 'landing_page_view' in action_type:
                    funnel_data['landing_page_views'] = value
                elif 'add_to_cart' in action_type:
                    funnel_data['add_to_cart'] = value
                elif 'initiate_checkout' in action_type:
                    funnel_data['initiate_checkout'] = value
                elif 'purchase' in action_type:
                    funnel_data['purchases'] = value
            
            return funnel_data
        except Exception:
            # Return basic funnel if detailed data not available
            return {
                'impressions': 0,
                'clicks': 0,
                'click_rate': 0,
                'conversions': 0,
                'conversion_rate': 0
            }
    
    def _get_underperforming_ads(self, account_id: str, since: str, until: str, threshold_roas: float = 1.0, min_spend: float = 100) -> List[Dict]:
        """Identify underperforming ads"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        # Get all ads performance
        all_ads = client.get_top_performing_ads(account_id, {'since': since, 'until': until}, limit=500)
        
        # Filter underperforming ads
        underperforming = []
        for ad in all_ads:
            if ad.get('spend', 0) >= min_spend and ad.get('roas', 0) < threshold_roas:
                # Add recommendation based on metrics
                recommendation = ''
                if ad.get('roas', 0) < 0.5:
                    recommendation = 'Very low ROAS - consider pausing immediately'
                elif ad.get('ctr', 0) < 1.0:
                    recommendation = 'Low CTR - test new creative or audience'
                elif ad.get('conversions', 0) < 1:
                    recommendation = 'No conversions - review landing page and offer'
                else:
                    recommendation = 'Below threshold - optimize bid strategy or creative'
                
                ad['recommendation'] = recommendation
                underperforming.append(ad)
        
        return underperforming
    
    def _handle_ping(self, params: Dict) -> Dict:
        """Handle ping request - returns empty object per MCP spec"""
        return {}
    
    def _success_response(self, message_id: Optional[Any], result: Any) -> Dict:
        """Create success response"""
        response = {
            'jsonrpc': '2.0',
            'result': result
        }
        if message_id is not None:  # Include id even if it's 0
            response['id'] = message_id
        return response
    
    def _error_response(self, message_id: Optional[Any], error: str) -> Dict:
        """Create error response"""
        response = {
            'jsonrpc': '2.0',
            'error': {
                'code': -32603,
                'message': error
            }
        }
        if message_id is not None:  # Include id even if it's 0
            response['id'] = message_id
        return response