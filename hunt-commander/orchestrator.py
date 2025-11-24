"""Main orchestrator for the multi-agent job matching system."""
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from agents import (
    ScraperAgent,
    MatcherAgent,
    CritiqueAgent,
    CVTailorAgent,
    NotificationAgent
)
from utils import ConfigLoader, log

class JobAgentOrchestrator:
    """Orchestrates all agents in the job matching system."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
        """
        self.config = ConfigLoader(config_path)
        self.config.create_directories()

        log.info("=" * 60)
        log.info("Initializing Job Agent Orchestrator")
        log.info("=" * 60)

        # Initialize agents
        self.scraper = ScraperAgent(self.config.agent_config)
        self.matcher = MatcherAgent(self.config.agent_config)
        self.critique = CritiqueAgent(self.config.agent_config)
        self.cv_tailor = CVTailorAgent({
            **self.config.agent_config,
            **self.config.cv_config
        })
        self.notification = NotificationAgent(self.config.agent_config)

        log.info("All agents initialized successfully")

    def run(self):
        """Execute the complete job matching workflow."""
        log.info("=" * 60)
        log.info("Starting Job Matching Workflow")
        log.info("=" * 60)

        try:
            # Step 1: Scrape jobs
            log.info("\n[STEP 1/5] Scraping jobs from profesia.sk...")
            jobs = self._scrape_jobs()
            if not jobs:
                log.warning("No jobs found. Exiting.")
                return

            # Step 2: Match jobs
            log.info(f"\n[STEP 2/5] Matching {len(jobs)} jobs against CV and preferences...")
            cv_content = self._load_cv()
            matched_jobs = self._match_jobs(jobs, cv_content)
            if not matched_jobs:
                log.warning("No jobs matched. Exiting.")
                return

            # Step 3: Critique matches
            log.info(f"\n[STEP 3/5] Critiquing {len(matched_jobs)} matched jobs...")
            validated_jobs = self._critique_jobs(matched_jobs, cv_content)
            if not validated_jobs:
                log.warning("No jobs passed critique. Exiting.")
                return

            # Step 4: Tailor CVs
            log.info(f"\n[STEP 4/5] Tailoring CVs for {len(validated_jobs)} validated jobs...")
            jobs_with_cvs = self._tailor_cvs(validated_jobs, cv_content)

            # Step 5: Send notifications
            log.info(f"\n[STEP 5/5] Sending notifications...")
            self._send_notifications(jobs_with_cvs)

            # Generate summary
            self._print_summary(jobs, matched_jobs, validated_jobs, jobs_with_cvs)

            log.info("=" * 60)
            log.info("Workflow completed successfully!")
            log.info("=" * 60)

        except Exception as e:
            log.error(f"Error in workflow: {e}")
            raise

    def _scrape_jobs(self) -> List[Dict[str, Any]]:
        """Scrape jobs from profesia.sk.

        Returns:
            List of scraped jobs
        """
        preferences = self.config.user_preferences
        job_titles = preferences.get('job_titles', [])
        locations = preferences.get('locations', [])

        if not job_titles:
            log.error("No job titles configured in preferences")
            return []

        jobs = self.scraper.execute(job_titles, locations)
        log.info(f"✓ Scraped {len(jobs)} jobs")

        return jobs

    def _load_cv(self) -> str:
        """Load user's CV content.

        Returns:
            CV content as string
        """
        cv_template_path = self.config.get('cv_config.cv_template_path')

        if not cv_template_path or not Path(cv_template_path).exists():
            log.warning(f"CV template not found at {cv_template_path}")
            log.info("Using placeholder CV content")
            return self._generate_placeholder_cv()

        try:
            with open(cv_template_path, 'r', encoding='utf-8') as f:
                cv_content = f.read()
            log.info(f"✓ Loaded CV from {cv_template_path}")
            return cv_content
        except Exception as e:
            log.error(f"Error loading CV: {e}")
            return self._generate_placeholder_cv()

    def _generate_placeholder_cv(self) -> str:
        """Generate placeholder CV from config.

        Returns:
            Placeholder CV content
        """
        personal_info = self.config.get('cv_config.personal_info', {})
        preferences = self.config.user_preferences

        cv = f"""
# {personal_info.get('name', 'Your Name')}

## Contact Information
- Email: {personal_info.get('email', 'email@example.com')}
- Phone: {personal_info.get('phone', '+421 XXX XXX XXX')}
- Location: {personal_info.get('location', 'Bratislava, Slovakia')}
- LinkedIn: {personal_info.get('linkedin', 'linkedin.com/in/yourprofile')}
- GitHub: {personal_info.get('github', 'github.com/yourusername')}

## Professional Summary
Experienced professional seeking {preferences.get('experience_level', 'mid-level')} position in {', '.join(preferences.get('job_titles', ['Software Development']))}.

## Technical Skills
{', '.join(preferences.get('required_skills', []) + preferences.get('preferred_skills', []))}

## Work Experience
[Add your work experience here]

## Education
[Add your education here]

## Languages
{', '.join(preferences.get('languages', ['English', 'Slovak']))}
        """

        return cv.strip()

    def _match_jobs(
        self,
        jobs: List[Dict[str, Any]],
        cv_content: str
    ) -> List[Dict[str, Any]]:
        """Match jobs against CV and preferences.

        Args:
            jobs: List of scraped jobs
            cv_content: CV content

        Returns:
            List of matched jobs
        """
        preferences = self.config.user_preferences
        max_jobs = self.config.get('agent_config.max_jobs_per_day', 10)

        matched_jobs = self.matcher.execute(jobs, cv_content, preferences)

        # Limit to max jobs per day
        if len(matched_jobs) > max_jobs:
            log.info(f"Limiting to top {max_jobs} matches (from {len(matched_jobs)})")
            matched_jobs = sorted(
                matched_jobs,
                key=lambda x: x.get('match_score', 0),
                reverse=True
            )[:max_jobs]

        log.info(f"✓ Found {len(matched_jobs)} matching jobs")
        return matched_jobs

    def _critique_jobs(
        self,
        matched_jobs: List[Dict[str, Any]],
        cv_content: str
    ) -> List[Dict[str, Any]]:
        """Critique matched jobs.

        Args:
            matched_jobs: List of matched jobs
            cv_content: CV content

        Returns:
            List of validated jobs
        """
        if not self.config.get('agent_config.critique_enabled', True):
            log.info("Critique agent disabled, skipping...")
            return matched_jobs

        preferences = self.config.user_preferences
        validated_jobs = self.critique.execute(matched_jobs, cv_content, preferences)

        log.info(f"✓ {len(validated_jobs)} jobs approved after critique")
        return validated_jobs

    def _tailor_cvs(
        self,
        validated_jobs: List[Dict[str, Any]],
        cv_content: str
    ) -> List[Dict[str, Any]]:
        """Tailor CVs for validated jobs.

        Args:
            validated_jobs: List of validated jobs
            cv_content: Original CV content

        Returns:
            List of jobs with tailored CV information
        """
        cv_template_path = self.config.get('cv_config.cv_template_path')
        jobs_with_cvs = []

        for job in validated_jobs:
            try:
                tailored_cv_info = self.cv_tailor.execute(
                    job,
                    cv_content,
                    cv_template_path
                )

                if tailored_cv_info:
                    job['tailored_cv'] = tailored_cv_info
                    jobs_with_cvs.append(job)
                    log.debug(f"✓ CV tailored for {job['title']}")
                else:
                    log.warning(f"✗ Failed to tailor CV for {job['title']}")

            except Exception as e:
                log.error(f"Error tailoring CV for {job['title']}: {e}")

        log.info(f"✓ Generated {len(jobs_with_cvs)} tailored CVs")
        return jobs_with_cvs

    def _send_notifications(self, jobs: List[Dict[str, Any]]):
        """Send notifications for jobs.

        Args:
            jobs: List of jobs with tailored CVs
        """
        if not self.config.get('agent_config.send_notifications', True):
            log.info("Notifications disabled, skipping...")
            return

        notification_method = self.config.get('agent_config.notification_method', 'email')

        if notification_method == 'email':
            # Send individual notifications
            for job in jobs:
                try:
                    tailored_cv = job.get('tailored_cv')
                    success = self.notification.execute(job, tailored_cv)
                    if success:
                        log.debug(f"✓ Notification sent for {job['title']}")
                    else:
                        log.warning(f"✗ Failed to send notification for {job['title']}")
                except Exception as e:
                    log.error(f"Error sending notification for {job['title']}: {e}")

            log.info(f"✓ Sent {len(jobs)} email notifications")

        else:
            log.warning(f"Unsupported notification method: {notification_method}")

    def _print_summary(
        self,
        scraped_jobs: List[Dict[str, Any]],
        matched_jobs: List[Dict[str, Any]],
        validated_jobs: List[Dict[str, Any]],
        jobs_with_cvs: List[Dict[str, Any]]
    ):
        """Print workflow summary.

        Args:
            scraped_jobs: Jobs scraped
            matched_jobs: Jobs matched
            validated_jobs: Jobs validated
            jobs_with_cvs: Jobs with tailored CVs
        """
        log.info("\n" + "=" * 60)
        log.info("WORKFLOW SUMMARY")
        log.info("=" * 60)
        log.info(f"Jobs Scraped:              {len(scraped_jobs)}")
        log.info(f"Initial Matches:           {len(matched_jobs)}")
        log.info(f"Approved After Critique:   {len(validated_jobs)}")
        log.info(f"CVs Generated:             {len(jobs_with_cvs)}")
        log.info(f"Notifications Sent:        {len(jobs_with_cvs)}")
        log.info("=" * 60)

        if jobs_with_cvs:
            log.info("\nMATCHED JOBS:")
            for i, job in enumerate(jobs_with_cvs, 1):
                log.info(f"\n{i}. {job['title']} at {job.get('company', 'Unknown')}")
                log.info(f"   Match Score: {job.get('match_score', 0):.0%}")
                log.info(f"   Critique Score: {job.get('critique_score', 0):.0%}")
                log.info(f"   URL: {job.get('url', 'N/A')}")
                if job.get('tailored_cv'):
                    log.info(f"   CV: {job['tailored_cv']['cv_file_path']}")

    def run_test_mode(self):
        """Run in test mode with limited scraping."""
        log.info("Running in TEST MODE (limited functionality)")

        # Create sample job data for testing
        sample_jobs = [
            {
                'title': 'Python Developer',
                'company': 'Tech Company',
                'location': 'Bratislava',
                'salary': '3000-4000 EUR',
                'description': 'We are looking for a Python developer with experience in Django and REST APIs.',
                'requirements': 'Python, Django, REST APIs, PostgreSQL',
                'url': 'https://www.profesia.sk/example-job-1',
                'scraped_at': datetime.now().isoformat(),
                'source': 'profesia.sk'
            }
        ]

        log.info(f"Using {len(sample_jobs)} sample jobs for testing")

        # Run workflow with sample data
        cv_content = self._load_cv()
        matched_jobs = self._match_jobs(sample_jobs, cv_content)

        if matched_jobs:
            validated_jobs = self._critique_jobs(matched_jobs, cv_content)

            if validated_jobs:
                log.info("Test mode: Skipping CV tailoring and notifications")
                log.info(f"\n✓ Test successful! Found {len(validated_jobs)} matching job(s)")
            else:
                log.info("Test mode: No jobs passed critique")
        else:
            log.info("Test mode: No matching jobs found")
