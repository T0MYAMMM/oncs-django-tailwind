"""
Scrapyd API Utility

This module provides a comprehensive interface to Scrapyd's HTTP API.
Based on Scrapyd's official API documentation: https://scrapyd.readthedocs.io/en/stable/api.html
"""

import json
import requests
from typing import Dict, List, Optional, Any
from django.conf import settings
from .models import ScrapydServer


class ScrapydAPIError(Exception):
    """Custom exception for Scrapyd API errors"""
    pass


class ScrapydAPI:
    """
    Comprehensive Scrapyd API client
    
    Provides all Scrapyd API endpoints:
    - addversion.json
    - schedule.json
    - cancel.json
    - listprojects.json
    - listversions.json
    - listspiders.json
    - listjobs.json
    - delversion.json
    - delproject.json
    - log
    - items
    """
    
    def __init__(self, server: ScrapydServer):
        self.server = server
        self.base_url = server.base_url
        self.timeout = 30
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """
        Make a request to Scrapyd API
        
        Args:
            endpoint: API endpoint (e.g., 'listprojects.json')
            method: HTTP method ('GET' or 'POST')
            data: Data to send with POST request
            
        Returns:
            Dict containing the response
            
        Raises:
            ScrapydAPIError: If the request fails
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, timeout=self.timeout)
            else:
                response = requests.post(url, data=data, timeout=self.timeout)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError as e:
            raise ScrapydAPIError(f"Connection error to Scrapyd server {self.base_url}: {str(e)}")
        except requests.exceptions.Timeout as e:
            raise ScrapydAPIError(f"Timeout error to Scrapyd server {self.base_url}: {str(e)}")
        except requests.exceptions.HTTPError as e:
            raise ScrapydAPIError(f"HTTP error from Scrapyd server {self.base_url}: {str(e)}")
        except Exception as e:
            raise ScrapydAPIError(f"Unexpected error communicating with Scrapyd server {self.base_url}: {str(e)}")
    
    def addversion(self, project: str, version: str, egg: bytes) -> Dict:
        """
        Add a new version to a project
        
        Args:
            project: Project name
            version: Version name
            egg: Project egg as bytes
            
        Returns:
            Dict containing the response
        """
        data = {
            'project': project,
            'version': version,
        }
        files = {'egg': ('project.egg', egg, 'application/octet-stream')}
        
        url = f"{self.base_url}/addversion.json"
        try:
            response = requests.post(url, data=data, files=files, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise ScrapydAPIError(f"Error adding version: {str(e)}")
    
    def schedule(self, project: str, spider: str, **kwargs) -> Dict:
        """
        Schedule a spider run
        
        Args:
            project: Project name
            spider: Spider name
            **kwargs: Additional parameters (settings, jobid, etc.)
            
        Returns:
            Dict containing the response with jobid
        """
        data = {
            'project': project,
            'spider': spider,
            **kwargs
        }
        return self._make_request('schedule.json', method='POST', data=data)
    
    def cancel(self, project: str, job: str) -> Dict:
        """
        Cancel a spider run
        
        Args:
            project: Project name
            job: Job ID
            
        Returns:
            Dict containing the response
        """
        data = {
            'project': project,
            'job': job
        }
        return self._make_request('cancel.json', method='POST', data=data)
    
    def listprojects(self) -> Dict:
        """
        List all projects
        
        Returns:
            Dict containing the list of projects
        """
        return self._make_request('listprojects.json')
    
    def listversions(self, project: str) -> Dict:
        """
        List all versions of a project
        
        Args:
            project: Project name
            
        Returns:
            Dict containing the list of versions
        """
        return self._make_request(f'listversions.json?project={project}')
    
    def listspiders(self, project: str, version: Optional[str] = None) -> Dict:
        """
        List all spiders of a project
        
        Args:
            project: Project name
            version: Version name (optional)
            
        Returns:
            Dict containing the list of spiders
        """
        url = f'listspiders.json?project={project}'
        if version:
            url += f'&_version={version}'
        return self._make_request(url)
    
    def listjobs(self, project: str) -> Dict:
        """
        List all jobs of a project
        
        Args:
            project: Project name
            
        Returns:
            Dict containing the list of jobs
        """
        return self._make_request(f'listjobs.json?project={project}')
    
    def delversion(self, project: str, version: str) -> Dict:
        """
        Delete a version of a project
        
        Args:
            project: Project name
            version: Version name
            
        Returns:
            Dict containing the response
        """
        data = {
            'project': project,
            'version': version
        }
        return self._make_request('delversion.json', method='POST', data=data)
    
    def delproject(self, project: str) -> Dict:
        """
        Delete a project
        
        Args:
            project: Project name
            
        Returns:
            Dict containing the response
        """
        data = {
            'project': project
        }
        return self._make_request('delproject.json', method='POST', data=data)
    
    def get_log(self, project: str, spider: str, job: str) -> str:
        """
        Get the log of a spider run
        
        Args:
            project: Project name
            spider: Spider name
            job: Job ID
            
        Returns:
            String containing the log content
        """
        url = f"{self.base_url}/logs/{project}/{spider}/{job}.log"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise ScrapydAPIError(f"Error getting log: {str(e)}")
    
    def get_items(self, project: str, spider: str, job: str) -> str:
        """
        Get the items of a spider run
        
        Args:
            project: Project name
            spider: Spider name
            job: Job ID
            
        Returns:
            String containing the items (JSONL format)
        """
        url = f"{self.base_url}/items/{project}/{spider}/{job}.jl"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise ScrapydAPIError(f"Error getting items: {str(e)}")
    
    def get_job_status(self, project: str, job: str) -> Dict:
        """
        Get the status of a specific job
        
        Args:
            project: Project name
            job: Job ID
            
        Returns:
            Dict containing job status information
        """
        jobs = self.listjobs(project)
        
        # Search for the specific job
        for status in ['pending', 'running', 'finished']:
            if status in jobs:
                for job_info in jobs[status]:
                    if job_info.get('id') == job:
                        return {
                            'status': status,
                            'job_info': job_info
                        }
        
        return {'status': 'not_found', 'job_info': None}


def get_scrapyd_api(server_id: Optional[int] = None) -> ScrapydAPI:
    """
    Get a ScrapydAPI instance for a server
    
    Args:
        server_id: Server ID (optional, uses first active server if not provided)
        
    Returns:
        ScrapydAPI instance
        
    Raises:
        ScrapydAPIError: If no active server is found
    """
    if server_id:
        server = ScrapydServer.objects.get(id=server_id, is_active=True)
    else:
        server = ScrapydServer.objects.filter(is_active=True).first()
    
    if not server:
        raise ScrapydAPIError("No active Scrapyd server found")
    
    return ScrapydAPI(server)


def fetch_and_save_logs(crawler_task_id: int) -> Optional[str]:
    """
    Fetch logs from Scrapyd and save them locally
    
    Args:
        crawler_task_id: CrawlerTask ID
        
    Returns:
        Path to the saved log file or None if failed
    """
    from apps.common.models import CrawlerTask
    from .tasks import write_to_log_file
    
    try:
        crawler_task = CrawlerTask.objects.get(id=crawler_task_id)
        if not crawler_task.scrapyd_job_id:
            return None
        
        # Get the Scrapyd API
        api = get_scrapyd_api()
        
        # Fetch the log
        log_content = api.get_log('scrapy_crawler', 'generic', crawler_task.scrapyd_job_id)
        
        # Save the log locally
        log_file = write_to_log_file(log_content, f"scrapyd_log_{crawler_task.scrapyd_job_id}")
        
        return log_file
        
    except Exception as e:
        print(f"Error fetching logs for task {crawler_task_id}: {str(e)}")
        return None


def fetch_and_save_items(crawler_task_id: int) -> Optional[str]:
    """
    Fetch items from Scrapyd and save them locally
    
    Args:
        crawler_task_id: CrawlerTask ID
        
    Returns:
        Path to the saved items file or None if failed
    """
    from apps.common.models import CrawlerTask
    from .tasks import write_to_log_file
    
    try:
        crawler_task = CrawlerTask.objects.get(id=crawler_task_id)
        if not crawler_task.scrapyd_job_id:
            return None
        
        # Get the Scrapyd API
        api = get_scrapyd_api()
        
        # Fetch the items
        items_content = api.get_items('scrapy_crawler', 'generic', crawler_task.scrapyd_job_id)
        
        # Save the items locally
        items_file = write_to_log_file(items_content, f"scrapyd_items_{crawler_task.scrapyd_job_id}")
        
        return items_file
        
    except Exception as e:
        print(f"Error fetching items for task {crawler_task_id}: {str(e)}")
        return None


def get_job_details(crawler_task_id: int) -> Dict:
    """
    Get comprehensive job details including status, logs, and items
    
    Args:
        crawler_task_id: CrawlerTask ID
        
    Returns:
        Dict containing job details
    """
    from apps.common.models import CrawlerTask
    
    try:
        crawler_task = CrawlerTask.objects.get(id=crawler_task_id)
        if not crawler_task.scrapyd_job_id:
            return {'error': 'No Scrapyd job ID found'}
        
        # Get the Scrapyd API
        api = get_scrapyd_api()
        
        # Get job status
        job_status = api.get_job_status('scrapy_crawler', crawler_task.scrapyd_job_id)
        
        # Get logs and items
        log_content = None
        items_content = None
        
        try:
            log_content = api.get_log('scrapy_crawler', 'generic', crawler_task.scrapyd_job_id)
        except:
            pass
        
        try:
            items_content = api.get_items('scrapy_crawler', 'generic', crawler_task.scrapyd_job_id)
        except:
            pass
        
        return {
            'task_id': crawler_task_id,
            'scrapyd_job_id': crawler_task.scrapyd_job_id,
            'status': job_status.get('status'),
            'job_info': job_status.get('job_info'),
            'log_content': log_content,
            'items_content': items_content,
            'log_url': f"{api.base_url}/logs/scrapy_crawler/generic/{crawler_task.scrapyd_job_id}.log",
            'items_url': f"{api.base_url}/items/scrapy_crawler/generic/{crawler_task.scrapyd_job_id}.jl"
        }
        
    except Exception as e:
        return {'error': f'Error getting job details: {str(e)}'}
