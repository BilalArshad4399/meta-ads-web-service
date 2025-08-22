"""
Meta Ads API Client
"""

import requests
from typing import Dict, List, Any

class MetaAdsClient:
    def __init__(self, access_token: str, api_version: str = 'v21.0'):
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f'https://graph.facebook.com/{api_version}'
    
    def _calculate_roas(self, spend: float, revenue: float) -> float:
        if spend == 0:
            return 0
        return round(revenue / spend, 2)
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        if params is None:
            params = {}
        params['access_token'] = self.access_token
        
        response = requests.get(f'{self.base_url}{endpoint}', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_account_roas(self, account_id: str, date_range: Dict) -> Dict:
        """Get account ROAS metrics"""
        fields = 'account_name,currency,spend,impressions,clicks,conversions,conversion_values'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'account'
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        if not data.get('data'):
            return {
                'account_id': account_id,
                'account_name': 'Unknown',
                'currency': 'USD',
                'spend': 0,
                'revenue': 0,
                'roas': 0,
                'impressions': 0,
                'clicks': 0,
                'conversions': 0
            }
        
        account_data = data['data'][0]
        spend = float(account_data.get('spend', 0))
        
        # Parse conversion values
        conversion_values = account_data.get('conversion_values', [])
        revenue = 0
        if conversion_values:
            revenue = float(conversion_values[0].get('value', 0))
        
        return {
            'account_id': account_id,
            'account_name': account_data.get('account_name', 'Unknown'),
            'currency': account_data.get('currency', 'USD'),
            'spend': spend,
            'revenue': revenue,
            'roas': self._calculate_roas(spend, revenue),
            'impressions': int(account_data.get('impressions', 0)),
            'clicks': int(account_data.get('clicks', 0)),
            'conversions': int(account_data.get('conversions', 0))
        }
    
    def get_campaign_roas(self, account_id: str, date_range: Dict) -> List[Dict]:
        """Get campaign ROAS metrics"""
        fields = 'campaign_id,campaign_name,spend,impressions,clicks,conversions,conversion_values,status'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'campaign',
            'filtering': '[{"field":"impressions","operator":"GREATER_THAN","value":0}]'
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        campaigns = []
        for campaign in data.get('data', []):
            spend = float(campaign.get('spend', 0))
            conversion_values = campaign.get('conversion_values', [])
            revenue = 0
            if conversion_values:
                revenue = float(conversion_values[0].get('value', 0))
            
            campaigns.append({
                'campaign_id': campaign.get('campaign_id'),
                'campaign_name': campaign.get('campaign_name', 'Unknown'),
                'status': campaign.get('status', 'UNKNOWN'),
                'spend': spend,
                'revenue': revenue,
                'roas': self._calculate_roas(spend, revenue),
                'impressions': int(campaign.get('impressions', 0)),
                'clicks': int(campaign.get('clicks', 0)),
                'conversions': int(campaign.get('conversions', 0))
            })
        
        return campaigns
    
    def get_top_performing_ads(self, account_id: str, date_range: Dict, limit: int = 10) -> List[Dict]:
        """Get top performing ads by ROAS"""
        fields = 'ad_id,ad_name,adset_id,campaign_id,spend,impressions,clicks,conversions,conversion_values,status'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'ad',
            'limit': 500,
            'filtering': '[{"field":"impressions","operator":"GREATER_THAN","value":0}]'
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        ads = []
        for ad in data.get('data', []):
            spend = float(ad.get('spend', 0))
            conversion_values = ad.get('conversion_values', [])
            revenue = 0
            if conversion_values:
                revenue = float(conversion_values[0].get('value', 0))
            
            ads.append({
                'ad_id': ad.get('ad_id'),
                'ad_name': ad.get('ad_name', 'Unknown'),
                'adset_id': ad.get('adset_id'),
                'campaign_id': ad.get('campaign_id'),
                'status': ad.get('status', 'UNKNOWN'),
                'spend': spend,
                'revenue': revenue,
                'roas': self._calculate_roas(spend, revenue),
                'impressions': int(ad.get('impressions', 0)),
                'clicks': int(ad.get('clicks', 0)),
                'conversions': int(ad.get('conversions', 0))
            })
        
        # Sort by ROAS and return top performers
        ads.sort(key=lambda x: x['roas'], reverse=True)
        return ads[:limit]