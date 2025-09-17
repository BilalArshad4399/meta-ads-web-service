"""
Meta Ads API Client
"""

import requests
from typing import Dict, List, Any

class MetaAdsClient:
    def __init__(self, access_token: str, api_version: str = 'v18.0'):
        """Initialize Meta Marketing API client with latest version"""
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

        # Better error handling with detailed messages
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                error_code = error_data.get('error', {}).get('code', '')
                error_type = error_data.get('error', {}).get('type', '')

                logger.error(f"Facebook API Error - Endpoint: {endpoint}, Code: {error_code}, Type: {error_type}, Message: {error_msg}")

                # Raise with detailed error message
                raise requests.exceptions.HTTPError(f"Facebook API Error ({error_code}): {error_msg}")
            except ValueError:
                # If response is not JSON
                response.raise_for_status()

        return response.json()
    
    def get_account_overview(self, account_id: str, date_range: Dict) -> Dict:
        """Get comprehensive account overview with ROAS metrics using Marketing API"""
        # Updated fields for Marketing API including purchase_roas
        fields = 'account_name,currency,spend,impressions,clicks,ctr,cpm,cpc,reach,frequency,purchase_roas,actions,action_values'
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
        
        # Parse action values for revenue (purchases, conversions)
        action_values = account_data.get('action_values', [])
        revenue = 0
        for action in action_values:
            if action.get('action_type') in ['purchase', 'omni_purchase', 'offsite_conversion.fb_pixel_purchase']:
                revenue += float(action.get('value', 0))
        
        # Get purchase ROAS from API or calculate
        purchase_roas_data = account_data.get('purchase_roas', [])
        if purchase_roas_data and len(purchase_roas_data) > 0:
            roas = float(purchase_roas_data[0].get('value', 0))
        else:
            roas = self._calculate_roas(spend, revenue)
        
        # Parse actions for conversions count
        actions = account_data.get('actions', [])
        conversions = 0
        for action in actions:
            if action.get('action_type') in ['purchase', 'omni_purchase', 'lead', 'complete_registration']:
                conversions += int(action.get('value', 0))
        
        return {
            'account_id': account_id,
            'account_name': account_data.get('account_name', 'Unknown'),
            'currency': account_data.get('currency', 'USD'),
            'spend': spend,
            'revenue': revenue,
            'roas': roas,
            'purchase_roas': roas,
            'impressions': int(account_data.get('impressions', 0)),
            'clicks': int(account_data.get('clicks', 0)),
            'conversions': conversions,
            'ctr': float(account_data.get('ctr', 0)),
            'cpm': float(account_data.get('cpm', 0)),
            'cpc': float(account_data.get('cpc', 0))
        }
    
    def get_all_campaigns(self, account_id: str) -> List[Dict]:
        """Get ALL campaigns from account, including paused/inactive ones"""
        try:
            # This endpoint gets campaign structure, not insights
            campaigns_url = f'/act_{account_id}/campaigns'
            params = {
                'fields': 'id,name,status,objective,created_time,updated_time,effective_status',
                'limit': 500
            }

            response = self._make_request(campaigns_url, params)
            campaigns = []

            for camp in response.get('data', []):
                campaigns.append({
                    'campaign_id': camp.get('id'),
                    'campaign_name': camp.get('name'),
                    'status': camp.get('status'),
                    'effective_status': camp.get('effective_status'),  # ACTIVE, PAUSED, DELETED, etc.
                    'objective': camp.get('objective'),
                    'created_time': camp.get('created_time'),
                    'updated_time': camp.get('updated_time')
                })

            return campaigns
        except Exception as e:
            logger.error(f"Error getting all campaigns: {e}")
            return []

    def get_campaign_roas(self, account_id: str, date_range: Dict) -> List[Dict]:
        """Get campaign ROAS metrics using Marketing API"""
        fields = 'campaign_id,campaign_name,spend,impressions,clicks,status,purchase_roas,actions,action_values,ctr,cpm,cpc'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'campaign'
            # Removed filtering to include ALL campaigns, even with 0 impressions
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        campaigns = []
        for campaign in data.get('data', []):
            spend = float(campaign.get('spend', 0))
            # Parse action values for revenue
            action_values = campaign.get('action_values', [])
            revenue = 0
            for action in action_values:
                if action.get('action_type') in ['purchase', 'omni_purchase', 'offsite_conversion.fb_pixel_purchase']:
                    revenue += float(action.get('value', 0))
            
            # Get purchase ROAS
            purchase_roas_data = campaign.get('purchase_roas', [])
            if purchase_roas_data and len(purchase_roas_data) > 0:
                roas = float(purchase_roas_data[0].get('value', 0))
            else:
                roas = self._calculate_roas(spend, revenue)
            
            # Count conversions
            actions = campaign.get('actions', [])
            conversions = 0
            for action in actions:
                if action.get('action_type') in ['purchase', 'omni_purchase', 'lead']:
                    conversions += int(action.get('value', 0))
            
            campaigns.append({
                'campaign_id': campaign.get('campaign_id'),
                'campaign_name': campaign.get('campaign_name', 'Unknown'),
                'status': campaign.get('status', 'UNKNOWN'),
                'spend': spend,
                'revenue': revenue,
                'roas': roas,
                'impressions': int(campaign.get('impressions', 0)),
                'clicks': int(campaign.get('clicks', 0)),
                'conversions': conversions,
                'ctr': float(campaign.get('ctr', 0)),
                'cpm': float(campaign.get('cpm', 0)),
                'cpc': float(campaign.get('cpc', 0))
            })
        
        return campaigns
    
    def get_top_performing_ads(self, account_id: str, date_range: Dict, limit: int = 10) -> List[Dict]:
        """Get top performing ads by ROAS using Marketing API"""
        fields = 'ad_id,ad_name,adset_id,campaign_id,spend,impressions,clicks,status,purchase_roas,actions,action_values,ctr,cpm,cpc'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'ad',
            'limit': 500
            # Removed filtering to include ALL ads, even with 0 impressions
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        ads = []
        for ad in data.get('data', []):
            spend = float(ad.get('spend', 0))
            # Parse action values for revenue
            action_values = ad.get('action_values', [])
            revenue = 0
            for action in action_values:
                if action.get('action_type') in ['purchase', 'omni_purchase', 'offsite_conversion.fb_pixel_purchase']:
                    revenue += float(action.get('value', 0))
            
            # Get purchase ROAS
            purchase_roas_data = ad.get('purchase_roas', [])
            if purchase_roas_data and len(purchase_roas_data) > 0:
                roas = float(purchase_roas_data[0].get('value', 0))
            else:
                roas = self._calculate_roas(spend, revenue)
            
            # Count conversions
            actions = ad.get('actions', [])
            conversions = 0
            for action in actions:
                if action.get('action_type') in ['purchase', 'omni_purchase', 'lead']:
                    conversions += int(action.get('value', 0))
            
            ads.append({
                'ad_id': ad.get('ad_id'),
                'ad_name': ad.get('ad_name', 'Unknown'),
                'adset_id': ad.get('adset_id'),
                'campaign_id': ad.get('campaign_id'),
                'status': ad.get('status', 'UNKNOWN'),
                'spend': spend,
                'revenue': revenue,
                'roas': roas,
                'impressions': int(ad.get('impressions', 0)),
                'clicks': int(ad.get('clicks', 0)),
                'conversions': conversions,
                'ctr': float(ad.get('ctr', 0)),
                'cpm': float(ad.get('cpm', 0)),
                'cpc': float(ad.get('cpc', 0))
            })
        
        # Sort by ROAS and return top performers
        ads.sort(key=lambda x: x['roas'], reverse=True)
        return ads[:limit]
    
    def get_account_roas(self, account_id: str, date_range: Dict) -> Dict:
        """Alias for get_account_overview for backward compatibility"""
        return self.get_account_overview(account_id, date_range)
    
    def get_adsets_performance(self, account_id: str, date_range: Dict, campaign_id: str = None) -> List[Dict]:
        """Get ad sets performance with real data"""
        fields = 'adset_id,adset_name,campaign_id,campaign_name,spend,impressions,clicks,conversions,conversion_values,ctr,cpm,daily_budget,lifetime_budget,status'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'adset'
        }
        
        if campaign_id:
            params['filtering'] = f'[{{"field":"campaign_id","operator":"EQUAL","value":"{campaign_id}"}}]'
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        adsets = []
        for adset in data.get('data', []):
            spend = float(adset.get('spend', 0))
            conversion_values = adset.get('conversion_values', [])
            revenue = 0
            if conversion_values:
                revenue = float(conversion_values[0].get('value', 0))
            
            adsets.append({
                'adset_id': adset.get('adset_id'),
                'adset_name': adset.get('adset_name', 'Unknown'),
                'campaign_id': adset.get('campaign_id'),
                'campaign_name': adset.get('campaign_name'),
                'status': adset.get('status', 'UNKNOWN'),
                'spend': spend,
                'revenue': revenue,
                'roas': self._calculate_roas(spend, revenue),
                'impressions': int(adset.get('impressions', 0)),
                'clicks': int(adset.get('clicks', 0)),
                'conversions': int(adset.get('conversions', 0)),
                'ctr': float(adset.get('ctr', 0)),
                'cpm': float(adset.get('cpm', 0)),
                'budget': float(adset.get('daily_budget', adset.get('lifetime_budget', 0)))
            })
        
        return adsets
    
    def get_audience_insights(self, account_id: str, date_range: Dict, breakdown: str = 'age,gender') -> Dict:
        """Get audience demographic insights with breakdowns"""
        fields = 'spend,impressions,clicks,conversions,conversion_values,ctr'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'account',
            'breakdowns': breakdown
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        insights = {
            'age_breakdown': {},
            'gender_breakdown': {},
            'total_metrics': {'spend': 0, 'conversions': 0, 'revenue': 0}
        }
        
        for segment in data.get('data', []):
            spend = float(segment.get('spend', 0))
            conversions = int(segment.get('conversions', 0))
            conversion_values = segment.get('conversion_values', [])
            revenue = float(conversion_values[0].get('value', 0)) if conversion_values else 0
            
            age = segment.get('age', 'unknown')
            gender = segment.get('gender', 'unknown')
            
            # Age breakdown
            if age != 'unknown':
                if age not in insights['age_breakdown']:
                    insights['age_breakdown'][age] = {'spend': 0, 'conversions': 0, 'revenue': 0}
                insights['age_breakdown'][age]['spend'] += spend
                insights['age_breakdown'][age]['conversions'] += conversions
                insights['age_breakdown'][age]['revenue'] += revenue
                insights['age_breakdown'][age]['roas'] = self._calculate_roas(
                    insights['age_breakdown'][age]['spend'],
                    insights['age_breakdown'][age]['revenue']
                )
            
            # Gender breakdown
            if gender != 'unknown':
                if gender not in insights['gender_breakdown']:
                    insights['gender_breakdown'][gender] = {'spend': 0, 'conversions': 0, 'revenue': 0}
                insights['gender_breakdown'][gender]['spend'] += spend
                insights['gender_breakdown'][gender]['conversions'] += conversions
                insights['gender_breakdown'][gender]['revenue'] += revenue
                insights['gender_breakdown'][gender]['roas'] = self._calculate_roas(
                    insights['gender_breakdown'][gender]['spend'],
                    insights['gender_breakdown'][gender]['revenue']
                )
            
            insights['total_metrics']['spend'] += spend
            insights['total_metrics']['conversions'] += conversions
            insights['total_metrics']['revenue'] += revenue
        
        return insights
    
    def get_daily_trends(self, account_id: str, date_range: Dict) -> List[Dict]:
        """Get daily performance trends"""
        fields = 'spend,impressions,clicks,conversions,conversion_values,ctr,cpm'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'time_increment': '1',  # Daily breakdown
            'level': 'account'
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        trends = []
        for day in data.get('data', []):
            spend = float(day.get('spend', 0))
            conversion_values = day.get('conversion_values', [])
            revenue = float(conversion_values[0].get('value', 0)) if conversion_values else 0
            
            trends.append({
                'date': day.get('date_start'),
                'spend': spend,
                'revenue': revenue,
                'roas': self._calculate_roas(spend, revenue),
                'impressions': int(day.get('impressions', 0)),
                'clicks': int(day.get('clicks', 0)),
                'conversions': int(day.get('conversions', 0)),
                'ctr': float(day.get('ctr', 0)),
                'cpm': float(day.get('cpm', 0))
            })
        
        return sorted(trends, key=lambda x: x['date'])
    
    def get_placement_performance(self, account_id: str, date_range: Dict) -> List[Dict]:
        """Get performance by placement (Facebook, Instagram, etc)"""
        fields = 'spend,impressions,clicks,conversions,conversion_values,ctr,cpm'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'account',
            'breakdowns': 'publisher_platform,placement'
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        placements = {}
        for item in data.get('data', []):
            platform = item.get('publisher_platform', 'unknown')
            placement = item.get('placement', platform)
            
            spend = float(item.get('spend', 0))
            conversion_values = item.get('conversion_values', [])
            revenue = float(conversion_values[0].get('value', 0)) if conversion_values else 0
            
            if placement not in placements:
                placements[placement] = {
                    'placement': placement,
                    'platform': platform,
                    'spend': 0,
                    'revenue': 0,
                    'impressions': 0,
                    'clicks': 0,
                    'conversions': 0
                }
            
            placements[placement]['spend'] += spend
            placements[placement]['revenue'] += revenue
            placements[placement]['impressions'] += int(item.get('impressions', 0))
            placements[placement]['clicks'] += int(item.get('clicks', 0))
            placements[placement]['conversions'] += int(item.get('conversions', 0))
        
        # Calculate ROAS for each placement
        result = []
        for placement_data in placements.values():
            placement_data['roas'] = self._calculate_roas(placement_data['spend'], placement_data['revenue'])
            result.append(placement_data)
        
        return sorted(result, key=lambda x: x['spend'], reverse=True)
    
    def get_creative_performance(self, account_id: str, date_range: Dict) -> List[Dict]:
        """Get performance by creative type"""
        # First get all ads with their creative info
        ads_endpoint = f'/act_{account_id}/ads'
        ads_params = {
            'fields': 'id,name,creative{object_type}',
            'limit': 500
        }
        
        ads_data = self._make_request(ads_endpoint, ads_params)
        
        # Map ad IDs to creative types
        ad_creative_types = {}
        for ad in ads_data.get('data', []):
            ad_id = ad.get('id')
            creative = ad.get('creative', {})
            object_type = creative.get('object_type', 'UNKNOWN')
            
            # Map Facebook creative types to simple categories
            if object_type in ['VIDEO', 'VIDEO_AUTOPLAY']:
                creative_type = 'video'
            elif object_type in ['LINK', 'IMAGE', 'PHOTO']:
                creative_type = 'image'
            elif object_type == 'CAROUSEL':
                creative_type = 'carousel'
            else:
                creative_type = 'other'
            
            ad_creative_types[ad_id] = creative_type
        
        # Now get performance data
        fields = 'ad_id,spend,impressions,clicks,conversions,conversion_values,ctr'
        params = {
            'fields': fields,
            'time_range': f'{{"since":"{date_range["since"]}","until":"{date_range["until"]}"}}',
            'level': 'ad'
        }
        
        data = self._make_request(f'/act_{account_id}/insights', params)
        
        # Aggregate by creative type
        creative_performance = {}
        for ad in data.get('data', []):
            ad_id = ad.get('ad_id')
            creative_type = ad_creative_types.get(ad_id, 'unknown')
            
            if creative_type not in creative_performance:
                creative_performance[creative_type] = {
                    'type': creative_type,
                    'count': 0,
                    'spend': 0,
                    'revenue': 0,
                    'impressions': 0,
                    'clicks': 0,
                    'conversions': 0
                }
            
            creative_performance[creative_type]['count'] += 1
            creative_performance[creative_type]['spend'] += float(ad.get('spend', 0))
            
            conversion_values = ad.get('conversion_values', [])
            revenue = float(conversion_values[0].get('value', 0)) if conversion_values else 0
            creative_performance[creative_type]['revenue'] += revenue
            
            creative_performance[creative_type]['impressions'] += int(ad.get('impressions', 0))
            creative_performance[creative_type]['clicks'] += int(ad.get('clicks', 0))
            creative_performance[creative_type]['conversions'] += int(ad.get('conversions', 0))
        
        # Calculate metrics
        result = []
        for perf in creative_performance.values():
            perf['roas'] = self._calculate_roas(perf['spend'], perf['revenue'])
            if perf['impressions'] > 0:
                perf['ctr'] = round((perf['clicks'] / perf['impressions']) * 100, 2)
            else:
                perf['ctr'] = 0
            result.append(perf)
        
        return sorted(result, key=lambda x: x['spend'], reverse=True)