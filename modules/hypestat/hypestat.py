#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HypeStat Domain Statistics Crawler

This script crawls domain statistics from HypeStat.com for a list of domains.
It uses ThreadPool for concurrent processing and can save results to a JSON file
or push them to a PostgreSQL database.

Author: Claude
"""

import os
import re
import json
import time
import logging
import argparse
import requests
from typing import List, Dict, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from urllib.parse import quote
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("hypestat_crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("HypeStatCrawler")

# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
DEFAULT_THREADS = 1


@dataclass
class DomainStats:
    """Data model for domain statistics from HypeStat"""
    domain: str
    status: str = "pending"  # pending, success, error
    error_message: str = ""
    
    # Website Profile
    title: str = ""
    description: str = ""
    
    # Traffic Info
    global_rank: int = 0
    daily_visitors: int = 0
    monthly_visits: int = 0
    pages_per_visit: float = 0.0
    daily_pageviews: int = 0
    avg_visit_duration: str = ""
    bounce_rate: str = ""
    global_reach_percentage: float = 0.0
    
    # Revenue Info
    daily_revenue: float = 0.0
    monthly_revenue: float = 0.0
    yearly_revenue: float = 0.0
    website_value: float = 0.0
    
    # Server Info
    server_ip: str = ""
    server_location: str = ""
    
    # Technologies
    technologies: List[Dict[str, str]] = field(default_factory=list)
    
    # Backlinks
    total_backlinks: int = 0
    referring_domains: int = 0
    
    # SSL Info
    ssl_supported: bool = False
    
    # Additional metadata
    crawled_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, converting float timestamp to ISO format string"""
        result = asdict(self)
        result['crawled_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.crawled_at))
        return result


class HypeStatScraper:
    """Handles scraping of HypeStat domain statistics"""
    
    def __init__(self, use_proxy: bool = False, proxy_url: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        if use_proxy and proxy_url:
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
    
    def get_domain_stats(self, domain: str) -> DomainStats:
        """Fetch and parse statistics for a domain from HypeStat"""
        stats = DomainStats(domain=domain)
        
        try:
            url = f"https://hypestat.com/info/{quote(domain)}"
            logger.info(f"Fetching stats for {domain} from {url}")
            
            # Make request with retries
            response = None
            attempts = 0
            
            while attempts < MAX_RETRIES:
                try:
                    response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                    response.raise_for_status()
                    break
                except (requests.RequestException, ConnectionError) as e:
                    attempts += 1
                    if attempts >= MAX_RETRIES:
                        stats.status = "error"
                        stats.error_message = f"Failed to fetch after {MAX_RETRIES} attempts: {str(e)}"
                        logger.error(f"Failed to fetch {domain}: {e}")
                        return stats
                    
                    logger.warning(f"Retry {attempts} for {domain} after error: {e}")
                    time.sleep(RETRY_DELAY)
            
            # Parse the HTML content
            stats = self._parse_html(response.text, stats)
            stats.status = "success"
            
        except Exception as e:
            stats.status = "error"
            stats.error_message = str(e)
            logger.error(f"Error processing {domain}: {e}", exc_info=True)
        
        return stats
    
    def _parse_html(self, html_content: str, stats: DomainStats) -> DomainStats:
        """Parse the HTML content from HypeStat to extract domain statistics"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract website profile
        try:
            title_element = soup.select_one('.about_span_txt')
            if title_element:
                stats.title = title_element.get_text(strip=True)
            
            desc_element = soup.select('.about_span_txt')[1] if len(soup.select('.about_span_txt')) > 1 else None
            if desc_element:
                stats.description = desc_element.get_text(strip=True)
        except Exception as e:
            logger.warning(f"Error extracting website profile for {stats.domain}: {e}")
        
        # Extract traffic information
        try:
            # Global rank
            rank_element = soup.select_one("dd:-soup-contains('HypeRank:')")
            if rank_element:
                rank_text = rank_element.find_next_sibling('dd').get_text(strip=True).replace(',', '')
                stats.global_rank = int(rank_text) if rank_text.isdigit() else 0
            
            # Daily visitors
            visitors_element = soup.select_one("dt:-soup-contains('Daily Unique Visitors:')")
            if visitors_element:
                visitors_text = visitors_element.find_next_sibling('dd').get_text(strip=True)
                stats.daily_visitors = self._parse_number(visitors_text)
                #with open('daily_visitors5.txt', 'a') as f:
                    #f.write(f"{stats.domain}: {stats.daily_visitors}\n")
                #    f.write(f"{stats.daily_visitors}\n")

            # Monthly visits
            monthly_visits_element = soup.select_one("dt:-soup-contains('Monthly Visits:')")
            if monthly_visits_element:
                monthly_visits_text = monthly_visits_element.find_next_sibling('dd').get_text(strip=True)
                stats.monthly_visits = self._parse_number(monthly_visits_text)
            
            # Pages per visit
            pages_element = soup.select_one("dt:-soup-contains('Pages per Visit:')")
            if pages_element:
                pages_text = pages_element.find_next_sibling('dd').get_text(strip=True)
                if pages_text != 'n/a':
                    stats.pages_per_visit = float(pages_text)
            
            # Daily pageviews
            pageviews_element = soup.select_one("dt:-soup-contains('Daily Pageviews:')")
            if pageviews_element:
                pageviews_text = pageviews_element.find_next_sibling('dd').get_text(strip=True)
                stats.daily_pageviews = self._parse_number(pageviews_text)
            
            # Visit duration
            duration_element = soup.select_one("dt:-soup-contains('Avg. visit duration:')")
            if duration_element:
                stats.avg_visit_duration = duration_element.find_next_sibling('dd').get_text(strip=True)
            
            # Bounce rate
            bounce_element = soup.select_one("dt:-soup-contains('Bounce rate:')")
            if bounce_element:
                stats.bounce_rate = bounce_element.find_next_sibling('dd').get_text(strip=True)
            
            # Global reach percentage
            reach_element = soup.select_one("dt:-soup-contains('Global Reach:')")
            if reach_element:
                reach_text = reach_element.find_next_sibling('dd').get_text(strip=True)
                reach_text = reach_text.strip().replace('%', '')
                try:
                    stats.global_reach_percentage = float(reach_text)
                except ValueError:
                    stats.global_reach_percentage = 0.0
        except Exception as e:
            logger.warning(f"Error extracting traffic info for {stats.domain}: {e}")
        
        # Extract revenue information
        try:
            # Daily revenue
            daily_rev_element = soup.select_one("dt:-soup-contains('Daily Revenue:')")
            if daily_rev_element:
                daily_rev_text = daily_rev_element.find_next_sibling('dd').get_text(strip=True)
                stats.daily_revenue = self._parse_money(daily_rev_text)
            
            # Monthly revenue
            monthly_rev_element = soup.select_one("dt:-soup-contains('Monthly Revenue:')")
            if monthly_rev_element:
                monthly_rev_text = monthly_rev_element.find_next_sibling('dd').get_text(strip=True)
                stats.monthly_revenue = self._parse_money(monthly_rev_text)
            
            # Yearly revenue
            yearly_rev_element = soup.select_one("dt:-soup-contains('Yearly Revenue:')")
            if yearly_rev_element:
                yearly_rev_text = yearly_rev_element.find_next_sibling('dd').get_text(strip=True)
                stats.yearly_revenue = self._parse_money(yearly_rev_text)
            
            # Website value
            value_element = soup.select_one("dt:-soup-contains('Website Value:')")
            if value_element:
                value_text = value_element.find_next_sibling('dd').get_text(strip=True)
                stats.website_value = self._parse_money(value_text)
        except Exception as e:
            logger.warning(f"Error extracting revenue info for {stats.domain}: {e}")
        
        # Extract server information
        try:
            # Server IP
            ip_element = soup.select_one("dt:-soup-contains('Server IP:')")
            if ip_element:
                stats.server_ip = ip_element.find_next_sibling('dd').get_text(strip=True)
            
            # Server location
            location_element = soup.select_one("dt:-soup-contains('Server Location:')")
            if location_element:
                stats.server_location = location_element.find_next_sibling('dd').get_text(strip=True).replace('\n', ', ')
        except Exception as e:
            logger.warning(f"Error extracting server info for {stats.domain}: {e}")
        
        # Extract technologies
        try:
            tech_sections = soup.select('.tech_report > div')
            for section in tech_sections:
                category = section.find('a').get_text(strip=True) if section.find('a') else "Unknown"
                tech_items = section.select('span > a')
                
                for tech in tech_items:
                    tech_name = tech.get_text(strip=True)
                    stats.technologies.append({
                        'category': category,
                        'name': tech_name
                    })
        except Exception as e:
            logger.warning(f"Error extracting technologies for {stats.domain}: {e}")
        
        # Extract backlinks information
        try:
            # Total backlinks
            backlinks_element = soup.select_one("dt:-soup-contains('Total Backlinks:')")
            if backlinks_element:
                backlinks_text = backlinks_element.find_next_sibling('dd').get_text(strip=True)
                stats.total_backlinks = self._parse_number(backlinks_text)
            
            # Referring domains
            referring_domains_element = soup.select_one("dt:-soup-contains('Referring Domains:')")
            if referring_domains_element:
                domains_text = referring_domains_element.find_next_sibling('dd').get_text(strip=True)
                stats.referring_domains = self._parse_number(domains_text)
        except Exception as e:
            logger.warning(f"Error extracting backlinks info for {stats.domain}: {e}")
        
        # Check SSL support
        try:
            ssl_element = soup.select_one('#ssl_yes')
            stats.ssl_supported = bool(ssl_element and not ssl_element.get('style') == 'display:none;')
        except Exception as e:
            logger.warning(f"Error checking SSL support for {stats.domain}: {e}")
        
        return stats
    
    @staticmethod
    def _parse_number(text: str) -> int:
        """Parse numbers from text, handling K, M, B suffixes"""
        text = text.strip()
        if text == 'n/a':
            return 0
        
        text = text.replace(',', '')
        multiplier = 1
        
        if 'K' in text:
            multiplier = 1000
            text = text.replace('K', '')
        elif 'M' in text:
            multiplier = 1000000
            text = text.replace('M', '')
        elif 'B' in text:
            multiplier = 1000000000
            text = text.replace('B', '')
        
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return 0
    
    @staticmethod
    def _parse_money(text: str) -> float:
        """Parse money values from text"""
        if not text:
            return 0.0
        
        # Extract digits and decimal points
        amount_match = re.search(r'[\d,]+\.?\d*[KMB]?', text.replace('$', ''))
        if not amount_match:
            return 0.0
        
        amount_str = amount_match.group(0)
        multiplier = 1
        
        if 'K' in amount_str:
            multiplier = 1000
            amount_str = amount_str.replace('K', '')
        elif 'M' in amount_str:
            multiplier = 1000000
            amount_str = amount_str.replace('M', '')
        elif 'B' in amount_str:
            multiplier = 1000000000
            amount_str = amount_str.replace('B', '')
        
        try:
            return float(amount_str.replace(',', '')) * multiplier
        except ValueError:
            return 0.0


class DataStorage:
    """Handles storage of domain statistics to JSON or database"""
    
    @staticmethod
    def save_to_json(stats_list: List[DomainStats], filename: str) -> None:
        """Save a list of domain statistics to a JSON file"""
        output_dir = os.path.dirname(filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([stat.to_dict() for stat in stats_list], f, indent=2)
        
        logger.info(f"Saved {len(stats_list)} domain statistics to {filename}")
    
    @staticmethod
    def save_to_database(stats_list: List[DomainStats], db_config: Dict[str, Any]) -> None:
        """Save domain statistics to a PostgreSQL database"""
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            # Create the table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS domain_stats (
                    id SERIAL PRIMARY KEY,
                    domain VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    error_message TEXT,
                    title TEXT,
                    description TEXT,
                    global_rank INTEGER,
                    daily_visitors INTEGER,
                    monthly_visits INTEGER,
                    pages_per_visit FLOAT,
                    daily_pageviews INTEGER,
                    avg_visit_duration VARCHAR(50),
                    bounce_rate VARCHAR(50),
                    global_reach_percentage FLOAT,
                    daily_revenue FLOAT,
                    monthly_revenue FLOAT,
                    yearly_revenue FLOAT,
                    website_value FLOAT,
                    server_ip VARCHAR(255),
                    server_location TEXT,
                    technologies JSONB,
                    total_backlinks INTEGER,
                    referring_domains INTEGER,
                    ssl_supported BOOLEAN,
                    crawled_at TIMESTAMP,
                    UNIQUE(domain, crawled_at)
                )
            """)
            
            # Create technologies table for normalized data structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS domain_technologies (
                    id SERIAL PRIMARY KEY,
                    domain_stats_id INTEGER REFERENCES domain_stats(id),
                    category VARCHAR(255),
                    name VARCHAR(255),
                    UNIQUE(domain_stats_id, category, name)
                )
            """)
            
            # Prepare data for insertion
            stats_data = []
            for stat in stats_list:
                stats_dict = stat.to_dict()
                # Convert technologies list to JSON string
                stats_dict['technologies'] = json.dumps(stats_dict['technologies'])
                stats_data.append((
                    stats_dict['domain'],
                    stats_dict['status'],
                    stats_dict['error_message'],
                    stats_dict['title'],
                    stats_dict['description'],
                    stats_dict['global_rank'],
                    stats_dict['daily_visitors'],
                    stats_dict['monthly_visits'],
                    stats_dict['pages_per_visit'],
                    stats_dict['daily_pageviews'],
                    stats_dict['avg_visit_duration'],
                    stats_dict['bounce_rate'],
                    stats_dict['global_reach_percentage'],
                    stats_dict['daily_revenue'],
                    stats_dict['monthly_revenue'],
                    stats_dict['yearly_revenue'],
                    stats_dict['website_value'],
                    stats_dict['server_ip'],
                    stats_dict['server_location'],
                    stats_dict['technologies'],
                    stats_dict['total_backlinks'],
                    stats_dict['referring_domains'],
                    stats_dict['ssl_supported'],
                    stats_dict['crawled_at']
                ))
            
            # Insert data in batches
            execute_batch(cursor, """
                INSERT INTO domain_stats (
                    domain, status, error_message, title, description, global_rank,
                    daily_visitors, monthly_visits, pages_per_visit, daily_pageviews,
                    avg_visit_duration, bounce_rate, global_reach_percentage,
                    daily_revenue, monthly_revenue, yearly_revenue, website_value,
                    server_ip, server_location, technologies, total_backlinks,
                    referring_domains, ssl_supported, crawled_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (domain, crawled_at) DO UPDATE SET
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    global_rank = EXCLUDED.global_rank,
                    daily_visitors = EXCLUDED.daily_visitors,
                    monthly_visits = EXCLUDED.monthly_visits,
                    pages_per_visit = EXCLUDED.pages_per_visit,
                    daily_pageviews = EXCLUDED.daily_pageviews,
                    avg_visit_duration = EXCLUDED.avg_visit_duration,
                    bounce_rate = EXCLUDED.bounce_rate,
                    global_reach_percentage = EXCLUDED.global_reach_percentage,
                    daily_revenue = EXCLUDED.daily_revenue,
                    monthly_revenue = EXCLUDED.monthly_revenue,
                    yearly_revenue = EXCLUDED.yearly_revenue,
                    website_value = EXCLUDED.website_value,
                    server_ip = EXCLUDED.server_ip,
                    server_location = EXCLUDED.server_location,
                    technologies = EXCLUDED.technologies,
                    total_backlinks = EXCLUDED.total_backlinks,
                    referring_domains = EXCLUDED.referring_domains,
                    ssl_supported = EXCLUDED.ssl_supported
            """, stats_data, page_size=100)
            
            # Insert technologies for normalized access
            # First get the IDs of all the inserted records
            tech_data = []
            for stat in stats_list:
                cursor.execute("SELECT id FROM domain_stats WHERE domain = %s ORDER BY crawled_at DESC LIMIT 1",
                              (stat.domain,))
                domain_id = cursor.fetchone()[0]
                
                for tech in stat.technologies:
                    tech_data.append((
                        domain_id,
                        tech['category'],
                        tech['name']
                    ))
            
            if tech_data:
                execute_batch(cursor, """
                    INSERT INTO domain_technologies (domain_stats_id, category, name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (domain_stats_id, category, name) DO NOTHING
                """, tech_data, page_size=100)
            
            conn.commit()
            logger.info(f"Saved {len(stats_list)} domain statistics to database")
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class DomainCrawler:
    """Main controller for crawling domain statistics"""
    
    def __init__(self, 
                 max_threads: int = DEFAULT_THREADS,
                 use_proxy: bool = False,
                 proxy_url: Optional[str] = None):
        self.max_threads = max_threads
        self.scraper = HypeStatScraper(use_proxy, proxy_url)
    
    def process_domains(self, domains: List[str]) -> List[DomainStats]:
        """Process a list of domains using ThreadPool"""
        results = []
        total = len(domains)
        
        logger.info(f"Starting to process {total} domains with {self.max_threads} threads")
        
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            for i, result in enumerate(executor.map(self.scraper.get_domain_stats, domains), 1):
                results.append(result)
                logger.info(f"Processed {i}/{total} domains: {result.domain} - {result.status}")
        
        logger.info(f"Completed processing {total} domains")
        return results


def load_domains_from_file(filename: str) -> List[str]:
    """Load domains from a file, one domain per line"""
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(description='Crawl domain statistics from HypeStat')
    parser.add_argument('--input', '-i', required=True, help='Input file with domains (one per line)')
    parser.add_argument('--output', '-o', help='Output JSON file for results')
    parser.add_argument('--threads', '-t', type=int, default=DEFAULT_THREADS, help='Number of concurrent threads')
    parser.add_argument('--database', '-d', action='store_true', help='Store results in PostgreSQL database')
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', type=int, default=5432, help='Database port')
    parser.add_argument('--db-name', help='Database name')
    parser.add_argument('--db-user', help='Database user')
    parser.add_argument('--db-password', help='Database password')
    parser.add_argument('--proxy', help='Proxy URL (e.g., http://user:pass@host:port)')
    
    args = parser.parse_args()
    
    # Load domains from file
    try:
        domains = load_domains_from_file(args.input)
        logger.info(f"Loaded {len(domains)} domains from {args.input}")
    except Exception as e:
        logger.error(f"Error loading domains from {args.input}: {e}")
        return
    
    # Initialize the crawler
    crawler = DomainCrawler(
        max_threads=args.threads,
        use_proxy=bool(args.proxy),
        proxy_url=args.proxy
    )
    
    # Process domains
    start_time = time.time()
    results = crawler.process_domains(domains)
    elapsed_time = time.time() - start_time
    
    successful = sum(1 for r in results if r.status == 'success')
    logger.info(f"Processed {len(results)} domains in {elapsed_time:.2f} seconds "
                f"({successful} successful, {len(results) - successful} failed)")
    
    # Save results
    if args.output:
        DataStorage.save_to_json(results, args.output)
    
    if args.database:
        if not all([args.db_name, args.db_user, args.db_password]):
            logger.error("Database parameters missing. Please provide --db-name, --db-user, and --db-password")
            return
        
        db_config = {
            'host': args.db_host,
            'port': args.db_port,
            'dbname': args.db_name,
            'user': args.db_user,
            'password': args.db_password
        }
        
        DataStorage.save_to_database(results, db_config)

if __name__ == "__main__":
    main()