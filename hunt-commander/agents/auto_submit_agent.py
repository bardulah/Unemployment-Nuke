"""Application Auto-Submit Bot - Automatically submit job applications."""
import time
import random
from typing import Dict, Any, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from agents.base_agent import BaseAgent
from utils import log


class AutoSubmitAgent(BaseAgent):
    """Agent for automatically submitting job applications."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize auto-submit agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__("AutoSubmitAgent", config)
        self.driver = None

    def execute(
        self,
        job: Dict[str, Any],
        cv_path: str,
        cover_letter_path: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Auto-submit application for job.

        Args:
            job: Job details with URL
            cv_path: Path to CV file
            cover_letter_path: Optional path to cover letter
            user_data: User information for form filling

        Returns:
            Submission result
        """
        job_url = job.get('url')
        if not job_url:
            return {"success": False, "error": "No job URL provided"}

        log.info(f"Auto-submitting application for {job.get('title')}")

        # Detect job board and use appropriate strategy
        if 'profesia.sk' in job_url:
            return self._submit_profesia(job, cv_path, cover_letter_path, user_data)
        elif 'linkedin.com' in job_url:
            return self._submit_linkedin(job, cv_path, user_data)
        else:
            return self._submit_generic(job, cv_path, cover_letter_path, user_data)

    def _init_driver(self):
        """Initialize Selenium WebDriver."""
        if self.driver:
            return

        options = webdriver.ChromeOptions()
        # Run in visible mode for form filling (more reliable)
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        self.driver = webdriver.Chrome(options=options)
        log.info("WebDriver initialized")

    def _submit_profesia(
        self,
        job: Dict[str, Any],
        cv_path: str,
        cover_letter_path: Optional[str],
        user_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Submit application on Profesia.sk.

        Args:
            job: Job details
            cv_path: CV path
            cover_letter_path: Cover letter path
            user_data: User data

        Returns:
            Submission result
        """
        self._init_driver()
        result = {"success": False, "platform": "profesia.sk"}

        try:
            # Navigate to job
            self.driver.get(job['url'])
            time.sleep(2)

            # Click "Apply" button
            apply_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Odoslať životopis') or contains(text(), 'Apply')]"))
            )
            apply_button.click()
            time.sleep(2)

            # Fill in form
            if user_data:
                # Name
                try:
                    name_field = self.driver.find_element(By.NAME, 'name')
                    name_field.send_keys(user_data.get('name', ''))
                    time.sleep(0.5)
                except:
                    pass

                # Email
                try:
                    email_field = self.driver.find_element(By.NAME, 'email')
                    email_field.send_keys(user_data.get('email', ''))
                    time.sleep(0.5)
                except:
                    pass

                # Phone
                try:
                    phone_field = self.driver.find_element(By.NAME, 'phone')
                    phone_field.send_keys(user_data.get('phone', ''))
                    time.sleep(0.5)
                except:
                    pass

            # Upload CV
            try:
                cv_upload = self.driver.find_element(By.CSS_SELECTOR, "input[type='file'][accept*='pdf']")
                cv_upload.send_keys(cv_path)
                time.sleep(1)
                log.info("CV uploaded successfully")
            except Exception as e:
                log.error(f"Failed to upload CV: {e}")

            # Upload cover letter if provided
            if cover_letter_path:
                try:
                    cover_upload = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']:not([accept*='pdf'])")
                    cover_upload.send_keys(cover_letter_path)
                    time.sleep(1)
                    log.info("Cover letter uploaded")
                except:
                    log.warning("Could not upload cover letter")

            # Add message/motivation
            try:
                message_field = self.driver.find_element(By.NAME, 'message')
                message = f"I am very interested in the {job.get('title')} position. Please find my CV attached. I am available for an interview at your convenience."
                message_field.send_keys(message)
                time.sleep(0.5)
            except:
                pass

            # Submit application (with confirmation prompt)
            log.warning("⚠️  READY TO SUBMIT - Manual confirmation required")
            input("Press Enter to submit application (or Ctrl+C to cancel): ")

            try:
                submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Odoslať') or contains(text(), 'Submit')]")
                submit_button.click()
                time.sleep(3)

                result["success"] = True
                result["message"] = "Application submitted successfully"
                log.info("✅ Application submitted!")
            except Exception as e:
                result["error"] = f"Failed to submit: {e}"
                log.error(f"Submission failed: {e}")

        except Exception as e:
            result["error"] = str(e)
            log.error(f"Profesia submission error: {e}")

        return result

    def _submit_linkedin(
        self,
        job: Dict[str, Any],
        cv_path: str,
        user_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Submit application on LinkedIn (Easy Apply).

        Args:
            job: Job details
            cv_path: CV path
            user_data: User data

        Returns:
            Submission result
        """
        self._init_driver()
        result = {"success": False, "platform": "linkedin"}

        try:
            self.driver.get(job['url'])
            time.sleep(2)

            # Look for "Easy Apply" button
            easy_apply = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'jobs-apply-button')]"))
            )
            easy_apply.click()
            time.sleep(2)

            # Navigate through multi-step form
            while True:
                try:
                    # Check if there's a "Next" button
                    next_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Continue') or contains(text(), 'Next')]")

                    # Fill any visible required fields
                    self._fill_linkedin_form_fields(user_data)

                    time.sleep(1)
                    next_button.click()
                    time.sleep(2)

                except:
                    # No more "Next" buttons - look for "Submit" or "Review"
                    break

            # Final submission
            log.warning("⚠️  READY TO SUBMIT - Manual confirmation required")
            input("Press Enter to submit application (or Ctrl+C to cancel): ")

            submit_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Submit') or contains(text(), 'Submit')]")
            submit_button.click()
            time.sleep(3)

            result["success"] = True
            result["message"] = "LinkedIn Easy Apply submitted"
            log.info("✅ LinkedIn application submitted!")

        except Exception as e:
            result["error"] = str(e)
            log.error(f"LinkedIn submission error: {e}")

        return result

    def _submit_generic(
        self,
        job: Dict[str, Any],
        cv_path: str,
        cover_letter_path: Optional[str],
        user_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Submit application on generic job board.

        Args:
            job: Job details
            cv_path: CV path
            cover_letter_path: Cover letter path
            user_data: User data

        Returns:
            Submission result
        """
        self._init_driver()
        result = {"success": False, "platform": "generic"}

        try:
            self.driver.get(job['url'])
            time.sleep(2)

            # Try to find common apply button patterns
            apply_selectors = [
                "//button[contains(text(), 'Apply')]",
                "//a[contains(text(), 'Apply')]",
                "//button[contains(@class, 'apply')]",
                "//a[contains(@class, 'apply-button')]"
            ]

            apply_button = None
            for selector in apply_selectors:
                try:
                    apply_button = self.driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue

            if not apply_button:
                result["error"] = "Could not find apply button"
                return result

            apply_button.click()
            time.sleep(2)

            # Try to fill common form fields
            self._fill_generic_form(user_data, cv_path)

            log.warning("⚠️  Manual review required - form may need additional input")
            input("Press Enter after reviewing the form (or Ctrl+C to cancel): ")

            result["success"] = True
            result["message"] = "Form prepared - manual submission required"

        except Exception as e:
            result["error"] = str(e)
            log.error(f"Generic submission error: {e}")

        return result

    def _fill_linkedin_form_fields(self, user_data: Optional[Dict[str, Any]]):
        """Fill LinkedIn Easy Apply form fields.

        Args:
            user_data: User information
        """
        if not user_data:
            return

        # Phone number
        try:
            phone_field = self.driver.find_element(By.XPATH, "//input[contains(@id, 'phone')]")
            if not phone_field.get_attribute('value'):
                phone_field.send_keys(user_data.get('phone', ''))
        except:
            pass

        # Years of experience
        try:
            exp_field = self.driver.find_element(By.XPATH, "//input[contains(@id, 'experience') or contains(@placeholder, 'years')]")
            if not exp_field.get_attribute('value'):
                exp_field.send_keys(str(user_data.get('years_experience', '3')))
        except:
            pass

    def _fill_generic_form(self, user_data: Optional[Dict[str, Any]], cv_path: str):
        """Fill generic application form.

        Args:
            user_data: User data
            cv_path: CV path
        """
        if not user_data:
            return

        # Common field patterns
        fields = {
            'name': ['name', 'full_name', 'fullname'],
            'email': ['email', 'e-mail', 'mail'],
            'phone': ['phone', 'telephone', 'tel', 'mobile'],
            'message': ['message', 'cover', 'motivation', 'additional']
        }

        for field_type, patterns in fields.items():
            for pattern in patterns:
                try:
                    field = self.driver.find_element(By.XPATH, f"//input[contains(@name, '{pattern}')] | //textarea[contains(@name, '{pattern}')]")
                    value = user_data.get(field_type, '')
                    if value and not field.get_attribute('value'):
                        field.send_keys(value)
                        break
                except:
                    continue

        # File upload
        try:
            file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            file_input.send_keys(cv_path)
            log.info("CV uploaded")
        except:
            log.warning("Could not upload CV")

    def submit_batch(
        self,
        jobs: List[Dict[str, Any]],
        cv_path: str,
        user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Submit applications to multiple jobs.

        Args:
            jobs: List of jobs
            cv_path: CV path
            user_data: User data

        Returns:
            Batch submission results
        """
        results = {
            "total": len(jobs),
            "successful": 0,
            "failed": 0,
            "details": []
        }

        for job in jobs:
            log.info(f"Submitting to: {job.get('title')} at {job.get('company')}")

            result = self.execute(job, cv_path, user_data=user_data)

            if result.get('success'):
                results["successful"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "job": job.get('title'),
                "company": job.get('company'),
                "result": result
            })

            # Delay between submissions to appear more human
            if len(jobs) > 1:
                delay = random.uniform(30, 60)
                log.info(f"Waiting {delay:.0f}s before next submission...")
                time.sleep(delay)

        return results

    def close(self):
        """Close WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
