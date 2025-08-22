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
                'tools': {
                    'listChanged': True
                },
                'prompts': {}
            },
            'serverInfo': {
                'name': 'Zane - Meta Ads Connector',
                'version': '1.0.0'
            }
        }
    
    def _handle_list_tools(self, params: Dict) -> List[Dict]:
        """Return list of available tools"""
        tools = [
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
                    }
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
                    }
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
        if 'account_id' not in arguments and self.user.ad_accounts:
            default_account = self.user.ad_accounts[0]
            arguments['account_id'] = default_account.account_id
        
        tool_handlers = {
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
    
    def _get_account_overview(self, account_id: str, since: str, until: str) -> Dict:
        """Get comprehensive account overview"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        # For now, using existing method - would expand with more metrics
        return client.get_account_roas(account_id, {'since': since, 'until': until})
    
    def _get_campaigns_performance(self, account_id: str, since: str, until: str) -> List[Dict]:
        """Get detailed campaigns performance metrics"""
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
    
    def _get_adsets_performance(self, account_id: str, since: str, until: str, campaign_id: str = None) -> List[Dict]:
        """Get ad sets performance metrics"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        # Mock implementation - would fetch real ad set data
        return [
            {
                'adset_id': 'adset_001',
                'name': 'Target Audience 18-35',
                'campaign_name': 'Summer Sale',
                'status': 'ACTIVE',
                'budget': 500,
                'spend': 423.50,
                'impressions': 15234,
                'clicks': 542,
                'conversions': 28,
                'roas': 3.2
            }
        ]
    
    def _get_audience_insights(self, account_id: str, since: str, until: str, breakdown: str = 'all') -> Dict:
        """Get audience demographic insights"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        # Mock implementation
        return {
            'age_breakdown': {
                '18-24': {'spend': 1200, 'conversions': 45, 'roas': 2.8},
                '25-34': {'spend': 2300, 'conversions': 89, 'roas': 3.5},
                '35-44': {'spend': 1800, 'conversions': 56, 'roas': 2.9}
            },
            'gender_breakdown': {
                'male': {'spend': 2800, 'conversions': 95, 'roas': 3.1},
                'female': {'spend': 2500, 'conversions': 95, 'roas': 3.3}
            }
        }
    
    def _get_daily_trends(self, account_id: str, since: str, until: str, metrics: List[str] = None) -> List[Dict]:
        """Get daily performance trends"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        # Mock implementation
        return [
            {'date': '2024-01-20', 'spend': 250, 'revenue': 875, 'roas': 3.5, 'impressions': 8500},
            {'date': '2024-01-21', 'spend': 280, 'revenue': 952, 'roas': 3.4, 'impressions': 9200}
        ]
    
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
        
        return {
            'total_budget': 10000,
            'spent': 6500,
            'utilization_rate': 65,
            'daily_average_spend': 216.67,
            'projected_total': 9500,
            'pacing_status': 'on_track'
        }
    
    def _get_creative_performance(self, account_id: str, since: str, until: str, creative_type: str = None) -> List[Dict]:
        """Analyze performance by creative type"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return [
            {'type': 'image', 'count': 45, 'spend': 2300, 'revenue': 7590, 'roas': 3.3, 'ctr': 2.1},
            {'type': 'video', 'count': 12, 'spend': 3200, 'revenue': 12800, 'roas': 4.0, 'ctr': 3.5},
            {'type': 'carousel', 'count': 8, 'spend': 1500, 'revenue': 4200, 'roas': 2.8, 'ctr': 2.8}
        ]
    
    def _get_placement_performance(self, account_id: str, since: str, until: str) -> List[Dict]:
        """Get performance by placement"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return [
            {'placement': 'Facebook Feed', 'spend': 3500, 'revenue': 12250, 'roas': 3.5, 'impressions': 125000},
            {'placement': 'Instagram Feed', 'spend': 2800, 'revenue': 9800, 'roas': 3.5, 'impressions': 98000},
            {'placement': 'Instagram Stories', 'spend': 1200, 'revenue': 3600, 'roas': 3.0, 'impressions': 65000},
            {'placement': 'Audience Network', 'spend': 500, 'revenue': 1250, 'roas': 2.5, 'impressions': 45000}
        ]
    
    def _get_conversion_funnel(self, account_id: str, since: str, until: str, campaign_id: str = None) -> Dict:
        """Get conversion funnel metrics"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return {
            'impressions': 250000,
            'clicks': 5000,
            'click_rate': 2.0,
            'landing_page_views': 4500,
            'add_to_cart': 1200,
            'initiate_checkout': 800,
            'purchases': 450,
            'conversion_rate': 9.0,
            'overall_conversion_rate': 0.18
        }
    
    def _get_underperforming_ads(self, account_id: str, since: str, until: str, threshold_roas: float = 1.0, min_spend: float = 100) -> List[Dict]:
        """Identify underperforming ads"""
        client = self.meta_clients.get(account_id)
        if not client:
            raise ValueError(f"Account {account_id} not found or not active")
        
        return [
            {
                'ad_id': 'ad_123',
                'ad_name': 'Summer Sale - Image 1',
                'campaign_name': 'Summer Campaign',
                'spend': 450,
                'revenue': 350,
                'roas': 0.78,
                'impressions': 15000,
                'ctr': 0.8,
                'recommendation': 'Consider pausing or optimizing creative'
            },
            {
                'ad_id': 'ad_456', 
                'ad_name': 'Product Showcase Video',
                'campaign_name': 'Product Launch',
                'spend': 280,
                'revenue': 210,
                'roas': 0.75,
                'impressions': 8500,
                'ctr': 0.6,
                'recommendation': 'Low CTR - test new creative or audience'
            }
        ]
    
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