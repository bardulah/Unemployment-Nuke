"""Scraper agent for fetching jobs from profesia.sk."""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from datetime import datetime
import json
import time
from pathlib import Path
from .base_agent import BaseAgent

class ScraperAgent(BaseAgent):
    """Agent responsible for scraping job listings from profesia.sk."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the scraper agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.base_url = "https://www.profesia.sk"
        self.search_url = f"{self.base_url}/praca/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def execute(self, job_titles: List[str], locations: List[str]) -> List[Dict[str, Any]]:
        """Fetch job listings from profesia.sk.

        Args:
            job_titles: List of job titles to search for
            locations: List of locations to search in

        Returns:
            List of job dictionaries
        """
        self.log_info("Starting job scraping from profesia.sk")
        all_jobs = []

        for job_title in job_titles:
            for location in locations:
                jobs = self._search_jobs(job_title, location)
                all_jobs.extend(jobs)
                time.sleep(2)  # Be respectful to the server

        # Remove duplicates based on URL
        unique_jobs = self._deduplicate_jobs(all_jobs)
        self.log_info(f"Scraped {len(unique_jobs)} unique job listings")

        # Save jobs to file
        self._save_jobs(unique_jobs)

        return unique_jobs

    def _search_jobs(self, job_title: str, location: str) -> List[Dict[str, Any]]:
        """Search for jobs with specific criteria.

        Args:
            job_title: Job title to search for
            location: Location to search in

        Returns:
            List of job dictionaries
        """
        self.log_debug(f"Searching for '{job_title}' in '{location}'")

        params = {
            'search_anywhere': job_title,
            'region': location
        }

        try:
            response = requests.get(self.search_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            jobs = self._parse_job_listings(soup)

            self.log_debug(f"Found {len(jobs)} jobs for '{job_title}' in '{location}'")
            return jobs

        except requests.RequestException as e:
            self.log_error(f"Error fetching jobs: {e}")
            return []

    def _parse_job_listings(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse job listings from HTML.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of parsed job dictionaries
        """
        jobs = []

        # Note: The actual selectors need to be updated based on profesia.sk's current HTML structure
        # This is a template that needs to be adjusted
        job_cards = soup.find_all('div', class_='list-row')

        for card in job_cards:
            try:
                job = self._extract_job_info(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.log_error(f"Error parsing job card: {e}")
                continue

        return jobs

    def _extract_job_info(self, card) -> Dict[str, Any]:
        """Extract job information from a job card.

        Args:
            card: BeautifulSoup element of the job card

        Returns:
            Dictionary with job information
        """
        try:
            # Note: These selectors are examples and need to be updated based on actual HTML structure
            title_elem = card.find('a', class_='title')
            company_elem = card.find('span', class_='company')
            location_elem = card.find('span', class_='location')
            salary_elem = card.find('span', class_='salary')
            description_elem = card.find('div', class_='description')

            if not title_elem:
                return None

            job_url = title_elem.get('href', '')
            if job_url and not job_url.startswith('http'):
                job_url = f"{self.base_url}{job_url}"

            job = {
                'title': title_elem.text.strip() if title_elem else '',
                'company': company_elem.text.strip() if company_elem else '',
                'location': location_elem.text.strip() if location_elem else '',
                'salary': salary_elem.text.strip() if salary_elem else '',
                'description': description_elem.text.strip() if description_elem else '',
                'url': job_url,
                'scraped_at': datetime.now().isoformat(),
                'source': 'profesia.sk'
            }

            # Fetch detailed job information
            detailed_info = self._fetch_job_details(job_url)
            if detailed_info:
                job.update(detailed_info)

            return job

        except Exception as e:
            self.log_error(f"Error extracting job info: {e}")
            return None

    def _fetch_job_details(self, job_url: str) -> Dict[str, Any]:
        """Fetch detailed information from job detail page.

        Args:
            job_url: URL of the job detail page

        Returns:
            Dictionary with detailed job information
        """
        if not job_url:
            return {}

        try:
            response = requests.get(job_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract additional details (update selectors as needed)
            details = {}

            # Requirements
            requirements = soup.find('div', class_='requirements')
            if requirements:
                details['requirements'] = requirements.text.strip()

            # Benefits
            benefits = soup.find('div', class_='benefits')
            if benefits:
                details['benefits'] = benefits.text.strip()

            # Full description
            full_desc = soup.find('div', class_='full-description')
            if full_desc:
                details['full_description'] = full_desc.text.strip()

            time.sleep(1)  # Be respectful
            return details

        except Exception as e:
            self.log_error(f"Error fetching job details from {job_url}: {e}")
            return {}

    def _deduplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate jobs based on URL.

        Args:
            jobs: List of job dictionaries

        Returns:
            List of unique job dictionaries
        """
        seen_urls = set()
        unique_jobs = []

        for job in jobs:
            url = job.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_jobs.append(job)

        return unique_jobs

    def _save_jobs(self, jobs: List[Dict[str, Any]]):
        """Save scraped jobs to a JSON file.

        Args:
            jobs: List of job dictionaries
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"data/jobs/jobs_{timestamp}.json"

        Path("data/jobs").mkdir(parents=True, exist_ok=True)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)

        self.log_info(f"Saved {len(jobs)} jobs to {filename}")
