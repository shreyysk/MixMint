import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class VercelManager:
    """
    Manages custom domains on Vercel [Spec P3 Section C Fix 02].
    """
    def __init__(self):
        self.token = settings.VERCEL_TOKEN
        self.project_id = settings.VERCEL_PROJECT_ID
        self.team_id = settings.VERCEL_TEAM_ID
        self.base_url = "https://api.vercel.com"
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def add_domain(self, domain_name):
        """Adds a domain to the Vercel project."""
        url = f"{self.base_url}/v9/projects/{self.project_id}/domains"
        if self.team_id:
            url += f"?teamId={self.team_id}"
            
        payload = {"name": domain_name}
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code in (200, 201):
            return response.json()
        else:
            logger.error(f"Vercel add_domain failed: {response.text}")
            raise Exception(f"Failed to add domain to Vercel: {response.json().get('error', {}).get('message', 'Unknown error')}")

    def get_domain_status(self, domain_name):
        """Checks domain verification and SSL status."""
        url = f"{self.base_url}/v9/projects/{self.project_id}/domains/{domain_name}"
        if self.team_id:
            url += f"?teamId={self.team_id}"
            
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'verified': data.get('verified', False),
                'misconfigured': data.get('misconfigured', False),
                'ssl_status': data.get('verification', {}).get('status', 'pending')
            }
        else:
            logger.error(f"Vercel get_domain_status failed: {response.text}")
            return None

    def remove_domain(self, domain_name):
        """Removes a domain from the Vercel project."""
        url = f"{self.base_url}/v9/projects/{self.project_id}/domains/{domain_name}"
        if self.team_id:
            url += f"?teamId={self.team_id}"
            
        response = requests.delete(url, headers=self.headers)
        return response.status_code in (200, 204)
