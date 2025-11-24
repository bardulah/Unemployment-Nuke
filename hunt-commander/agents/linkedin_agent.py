"""LinkedIn Infiltrator Agent - Auto-DM recruiters with personalized messages."""
import os
import json
import time
import random
from typing import Dict, Any, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from agents.base_agent import BaseAgent
from utils import log


class LinkedInAgent(BaseAgent):
    """Agent for LinkedIn automation - recruiter outreach and networking."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize LinkedIn agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__("LinkedInAgent", config)
        self.driver = None
        self.logged_in = False

    def execute(
        self,
        action: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute LinkedIn action.

        Args:
            action: Action to perform (dm_recruiters, search_jobs, etc.)
            **kwargs: Action-specific parameters

        Returns:
            Action results
        """
        if action == "dm_recruiters":
            return self._dm_recruiters(
                search_query=kwargs.get('search_query', 'Python Developer'),
                location=kwargs.get('location', 'Bratislava'),
                max_messages=kwargs.get('max_messages', 10)
            )
        elif action == "search_jobs":
            return self._search_jobs(
                keywords=kwargs.get('keywords', 'Python'),
                location=kwargs.get('location', 'Slovakia')
            )
        elif action == "connect_with_recruiters":
            return self._connect_with_recruiters(
                industry=kwargs.get('industry', 'Technology'),
                max_connections=kwargs.get('max_connections', 20)
            )
        else:
            log.error(f"Unknown action: {action}")
            return {"error": "Unknown action"}

    def _init_driver(self):
        """Initialize Selenium WebDriver."""
        if self.driver:
            return

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            log.info("WebDriver initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize WebDriver: {e}")
            raise

    def _login_linkedin(self):
        """Log in to LinkedIn."""
        if self.logged_in:
            return True

        self._init_driver()

        username = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')

        if not username or not password:
            log.error("LinkedIn credentials not found in environment")
            return False

        try:
            log.info("Logging in to LinkedIn...")
            self.driver.get('https://www.linkedin.com/login')
            time.sleep(2)

            # Enter credentials
            username_field = self.driver.find_element(By.ID, 'username')
            password_field = self.driver.find_element(By.ID, 'password')

            username_field.send_keys(username)
            time.sleep(random.uniform(0.5, 1.5))
            password_field.send_keys(password)
            time.sleep(random.uniform(0.5, 1.5))
            password_field.send_keys(Keys.RETURN)

            # Wait for login
            time.sleep(5)

            # Check if logged in
            if 'feed' in self.driver.current_url or 'mynetwork' in self.driver.current_url:
                log.info("Successfully logged in to LinkedIn")
                self.logged_in = True
                return True
            else:
                log.error("Login may have failed - unexpected URL")
                return False

        except Exception as e:
            log.error(f"LinkedIn login failed: {e}")
            return False

    def _dm_recruiters(
        self,
        search_query: str,
        location: str,
        max_messages: int
    ) -> Dict[str, Any]:
        """Send DMs to recruiters.

        Args:
            search_query: Job search query
            location: Location filter
            max_messages: Maximum messages to send

        Returns:
            Results with sent message count
        """
        if not self._login_linkedin():
            return {"error": "Login failed"}

        log.info(f"Searching for recruiters: {search_query} in {location}")

        # Search for recruiters
        recruiters = self._find_recruiters(search_query, location, max_messages)

        sent_count = 0
        results = {
            "total_found": len(recruiters),
            "messages_sent": 0,
            "failed": 0,
            "recruiters_contacted": []
        }

        for recruiter in recruiters:
            if sent_count >= max_messages:
                break

            # Generate personalized message
            message = self._generate_recruiter_message(recruiter, search_query)

            # Send message
            success = self._send_linkedin_message(recruiter['profile_url'], message)

            if success:
                sent_count += 1
                results["messages_sent"] += 1
                results["recruiters_contacted"].append({
                    "name": recruiter.get('name'),
                    "title": recruiter.get('title'),
                    "company": recruiter.get('company')
                })
                log.info(f"Message sent to {recruiter.get('name')}")
            else:
                results["failed"] += 1

            # Random delay to avoid detection
            time.sleep(random.uniform(30, 60))

        return results

    def _find_recruiters(
        self,
        search_query: str,
        location: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Find recruiters on LinkedIn.

        Args:
            search_query: Search query
            location: Location
            max_results: Maximum results to return

        Returns:
            List of recruiter profiles
        """
        recruiters = []

        try:
            # Navigate to LinkedIn search
            search_url = f"https://www.linkedin.com/search/results/people/?keywords=recruiter%20{search_query.replace(' ', '%20')}&origin=SWITCH_SEARCH_VERTICAL&geoUrn=%5B%22Slovakia%22%5D"
            self.driver.get(search_url)
            time.sleep(3)

            # Scroll to load more results
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            # Extract recruiter profiles
            profile_cards = self.driver.find_elements(By.CLASS_NAME, 'reusable-search__result-container')

            for card in profile_cards[:max_results]:
                try:
                    name_elem = card.find_element(By.CLASS_NAME, 'entity-result__title-text')
                    name = name_elem.text.strip()

                    title_elem = card.find_element(By.CLASS_NAME, 'entity-result__primary-subtitle')
                    title = title_elem.text.strip()

                    profile_link = card.find_element(By.TAG_NAME, 'a').get_attribute('href')

                    # Try to get company
                    company = "Unknown"
                    try:
                        company_elem = card.find_element(By.CLASS_NAME, 'entity-result__secondary-subtitle')
                        company = company_elem.text.strip()
                    except:
                        pass

                    recruiters.append({
                        'name': name,
                        'title': title,
                        'company': company,
                        'profile_url': profile_link
                    })

                except Exception as e:
                    log.debug(f"Error extracting recruiter info: {e}")
                    continue

            log.info(f"Found {len(recruiters)} recruiters")

        except Exception as e:
            log.error(f"Error finding recruiters: {e}")

        return recruiters

    def _generate_recruiter_message(
        self,
        recruiter: Dict[str, Any],
        search_query: str
    ) -> str:
        """Generate personalized recruiter message.

        Args:
            recruiter: Recruiter information
            search_query: Job search query

        Returns:
            Personalized message
        """
        name = recruiter.get('name', '').split()[0]  # First name
        company = recruiter.get('company', 'your company')

        # Multiple message templates
        templates = [
            f"""Hi {name},

I noticed you're recruiting for {search_query} roles at {company}. I'm actively seeking opportunities in Bratislava and have strong experience with Python, Django, and modern backend development.

I'd love to connect and learn more about any current or upcoming positions that might be a good fit.

Best regards""",

            f"""Hello {name},

I came across your profile while researching {search_query} opportunities in Slovakia. With my background in Python development and proven track record delivering scalable applications, I believe I could add value to {company}'s team.

Would you be open to a quick chat about potential opportunities?

Thanks!""",

            f"""Hi {name},

I'm a {search_query} actively looking for new challenges in the Bratislava area. I noticed you recruit for tech positions at {company} and wanted to reach out directly.

Key strengths:
• Python, Django, REST APIs
• 3+ years backend development
• Available immediately

Would love to discuss any relevant openings.

Cheers""",

            f"""Hello {name},

Hope you're having a great week! I'm exploring {search_query} opportunities and saw that you work with {company}.

I'm particularly interested in roles involving Python development and would appreciate any insights you might have about the current market in Slovakia.

Looking forward to connecting!"""
        ]

        # Select random template
        return random.choice(templates)

    def _send_linkedin_message(
        self,
        profile_url: str,
        message: str
    ) -> bool:
        """Send message to LinkedIn profile.

        Args:
            profile_url: LinkedIn profile URL
            message: Message to send

        Returns:
            True if successful
        """
        try:
            # Navigate to profile
            self.driver.get(profile_url)
            time.sleep(3)

            # Click "Message" button
            try:
                message_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'message-anywhere-button')]"))
                )
                message_btn.click()
                time.sleep(2)
            except TimeoutException:
                log.warning("Message button not found - may need connection first")
                return False

            # Type message
            message_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']"))
            )

            # Type naturally with delays
            for char in message:
                message_box.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))

            time.sleep(1)

            # Send message
            send_btn = self.driver.find_element(By.XPATH, "//button[@type='submit' and contains(@class, 'msg-form__send-button')]")
            send_btn.click()

            time.sleep(2)
            return True

        except Exception as e:
            log.error(f"Failed to send message: {e}")
            return False

    def _search_jobs(
        self,
        keywords: str,
        location: str
    ) -> Dict[str, Any]:
        """Search for jobs on LinkedIn.

        Args:
            keywords: Job search keywords
            location: Location filter

        Returns:
            Job search results
        """
        if not self._login_linkedin():
            return {"error": "Login failed"}

        jobs = []

        try:
            # Navigate to jobs search
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
            self.driver.get(search_url)
            time.sleep(3)

            # Scroll to load jobs
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            # Extract jobs
            job_cards = self.driver.find_elements(By.CLASS_NAME, 'job-card-container')

            for card in job_cards[:20]:
                try:
                    title = card.find_element(By.CLASS_NAME, 'job-card-list__title').text
                    company = card.find_element(By.CLASS_NAME, 'job-card-container__company-name').text
                    location = card.find_element(By.CLASS_NAME, 'job-card-container__metadata-item').text
                    link = card.find_element(By.TAG_NAME, 'a').get_attribute('href')

                    jobs.append({
                        'title': title,
                        'company': company,
                        'location': location,
                        'url': link,
                        'source': 'LinkedIn'
                    })
                except Exception as e:
                    log.debug(f"Error extracting job: {e}")

        except Exception as e:
            log.error(f"Job search failed: {e}")

        return {
            "jobs_found": len(jobs),
            "jobs": jobs
        }

    def _connect_with_recruiters(
        self,
        industry: str,
        max_connections: int
    ) -> Dict[str, Any]:
        """Send connection requests to recruiters.

        Args:
            industry: Industry filter
            max_connections: Max connection requests to send

        Returns:
            Connection results
        """
        if not self._login_linkedin():
            return {"error": "Login failed"}

        sent_count = 0
        results = {
            "requests_sent": 0,
            "failed": 0
        }

        try:
            # Search for recruiters
            search_url = f"https://www.linkedin.com/search/results/people/?keywords=recruiter%20{industry}"
            self.driver.get(search_url)
            time.sleep(3)

            # Find and click "Connect" buttons
            connect_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Connect')]")

            for btn in connect_buttons[:max_connections]:
                try:
                    btn.click()
                    time.sleep(1)

                    # Add note (optional)
                    try:
                        add_note_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Add a note')]")
                        add_note_btn.click()
                        time.sleep(1)

                        note_field = self.driver.find_element(By.ID, 'custom-message')
                        note_field.send_keys(f"Hi! I'm exploring opportunities in {industry} and would love to connect.")

                        send_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send now')]")
                        send_btn.click()
                    except:
                        # Just send without note
                        send_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Send')]")
                        send_btn.click()

                    sent_count += 1
                    results["requests_sent"] += 1
                    time.sleep(random.uniform(5, 10))

                except Exception as e:
                    log.debug(f"Failed to send connection: {e}")
                    results["failed"] += 1

        except Exception as e:
            log.error(f"Connection process failed: {e}")

        return results

    def close(self):
        """Close WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logged_in = False
