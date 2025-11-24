"""Notification agent for sending job alerts to users."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List
from pathlib import Path
from .base_agent import BaseAgent

class NotificationAgent(BaseAgent):
    """Agent responsible for sending notifications about matched jobs."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the notification agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.notification_email = os.getenv('NOTIFICATION_EMAIL')
        self.notification_method = config.get('notification_method', 'email')

    def execute(
        self,
        job: Dict[str, Any],
        tailored_cv_info: Dict[str, Any] = None
    ) -> bool:
        """Send notification about a matched job.

        Args:
            job: Job dictionary with match information
            tailored_cv_info: Information about the tailored CV

        Returns:
            True if notification sent successfully, False otherwise
        """
        self.log_info(
            f"Sending notification for: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}"
        )

        if self.notification_method == 'email':
            return self._send_email_notification(job, tailored_cv_info)
        else:
            self.log_error(f"Unsupported notification method: {self.notification_method}")
            return False

    def send_batch_notification(
        self,
        jobs: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ) -> bool:
        """Send a batch notification with multiple jobs.

        Args:
            jobs: List of job dictionaries
            summary: Summary statistics

        Returns:
            True if notification sent successfully, False otherwise
        """
        self.log_info(f"Sending batch notification for {len(jobs)} jobs")

        if self.notification_method == 'email':
            return self._send_batch_email(jobs, summary)
        else:
            self.log_error(f"Unsupported notification method: {self.notification_method}")
            return False

    def _send_email_notification(
        self,
        job: Dict[str, Any],
        tailored_cv_info: Dict[str, Any] = None
    ) -> bool:
        """Send email notification for a single job.

        Args:
            job: Job dictionary
            tailored_cv_info: Tailored CV information

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self._validate_email_config():
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🎯 Job Match: {job.get('title', 'New Position')} at {job.get('company', 'Company')}"
            msg['From'] = self.smtp_username
            msg['To'] = self.notification_email

            # Create email body
            html_body = self._create_job_email_html(job, tailored_cv_info)
            text_body = self._create_job_email_text(job, tailored_cv_info)

            # Attach both text and HTML versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Attach CV if available
            if tailored_cv_info and tailored_cv_info.get('cv_file_path'):
                self._attach_file(msg, tailored_cv_info['cv_file_path'])

            # Send email
            self._send_email(msg)
            self.log_info(f"Email notification sent successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to send email notification: {e}")
            return False

    def _send_batch_email(
        self,
        jobs: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ) -> bool:
        """Send batch email notification with multiple jobs.

        Args:
            jobs: List of job dictionaries
            summary: Summary statistics

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self._validate_email_config():
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📬 Daily Job Report: {len(jobs)} Matches Found"
            msg['From'] = self.smtp_username
            msg['To'] = self.notification_email

            # Create email body
            html_body = self._create_batch_email_html(jobs, summary)
            text_body = self._create_batch_email_text(jobs, summary)

            # Attach both versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            self._send_email(msg)
            self.log_info(f"Batch email notification sent successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to send batch email: {e}")
            return False

    def _create_job_email_html(
        self,
        job: Dict[str, Any],
        tailored_cv_info: Dict[str, Any] = None
    ) -> str:
        """Create HTML email body for a job notification.

        Args:
            job: Job dictionary
            tailored_cv_info: Tailored CV information

        Returns:
            HTML email body
        """
        match_score = job.get('match_score', 0)
        critique_score = job.get('critique_score', 0)

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; border-radius: 5px; }}
                .job-title {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
                .company {{ font-size: 18px; }}
                .section {{ margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }}
                .section-title {{ font-size: 18px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }}
                .score {{ display: inline-block; padding: 5px 10px; border-radius: 3px; color: white; font-weight: bold; }}
                .score-high {{ background-color: #4CAF50; }}
                .score-medium {{ background-color: #FF9800; }}
                .score-low {{ background-color: #F44336; }}
                .list-item {{ margin: 5px 0; padding-left: 20px; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="job-title">{job.get('title', 'New Position')}</div>
                    <div class="company">{job.get('company', 'Company Name')}</div>
                    <div>📍 {job.get('location', 'Location')}</div>
                </div>

                <div class="section">
                    <div class="section-title">Match Scores</div>
                    <p>
                        Initial Match: <span class="score score-{'high' if match_score >= 0.7 else 'medium' if match_score >= 0.5 else 'low'}">{match_score:.0%}</span>
                        &nbsp;&nbsp;
                        Critique Score: <span class="score score-{'high' if critique_score >= 0.7 else 'medium' if critique_score >= 0.5 else 'low'}">{critique_score:.0%}</span>
                    </p>
                </div>

                <div class="section">
                    <div class="section-title">Why This Job Matches</div>
                    <ul>
                        {''.join(f'<li class="list-item">{reason}</li>' for reason in job.get('match_reasons', []))}
                    </ul>
                </div>

                <div class="section">
                    <div class="section-title">Job Strengths</div>
                    <ul>
                        {''.join(f'<li class="list-item">✓ {strength}</li>' for strength in job.get('strengths', []))}
                    </ul>
                </div>

                {f'''<div class="section">
                    <div class="section-title">⚠️ Red Flags</div>
                    <ul>
                        {''.join(f'<li class="list-item">{flag}</li>' for flag in job.get('red_flags', []))}
                    </ul>
                </div>''' if job.get('red_flags') else ''}

                {f'''<div class="section">
                    <div class="section-title">Skills to Highlight</div>
                    <ul>
                        {''.join(f'<li class="list-item">{skill}</li>' for skill in job.get('missing_skills', [])[:5])}
                    </ul>
                </div>''' if job.get('missing_skills') else ''}

                <div class="section">
                    <div class="section-title">Job Description</div>
                    <p>{job.get('description', 'No description available')}</p>
                </div>

                {f'''<div class="section">
                    <div class="section-title">📄 Tailored CV</div>
                    <p>A customized CV has been generated for this position and is attached to this email.</p>
                    <p><strong>File:</strong> {Path(tailored_cv_info['cv_file_path']).name}</p>
                </div>''' if tailored_cv_info else ''}

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{job.get('url', '#')}" class="button">View Full Job Posting →</a>
                </div>

                <div class="footer">
                    <p>This job was automatically matched by your Job Agent System.</p>
                    <p>Scraped from: {job.get('source', 'profesia.sk')} | {job.get('scraped_at', '')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _create_job_email_text(
        self,
        job: Dict[str, Any],
        tailored_cv_info: Dict[str, Any] = None
    ) -> str:
        """Create plain text email body for a job notification.

        Args:
            job: Job dictionary
            tailored_cv_info: Tailored CV information

        Returns:
            Plain text email body
        """
        text = f"""
🎯 NEW JOB MATCH

{job.get('title', 'New Position')}
{job.get('company', 'Company Name')}
📍 {job.get('location', 'Location')}

MATCH SCORES:
- Initial Match: {job.get('match_score', 0):.0%}
- Critique Score: {job.get('critique_score', 0):.0%}

WHY THIS JOB MATCHES:
{chr(10).join(f'• {reason}' for reason in job.get('match_reasons', []))}

JOB STRENGTHS:
{chr(10).join(f'✓ {strength}' for strength in job.get('strengths', []))}

{"RED FLAGS:" + chr(10) + chr(10).join(f'⚠️ {flag}' for flag in job.get('red_flags', [])) if job.get('red_flags') else ''}

DESCRIPTION:
{job.get('description', 'No description available')}

{"TAILORED CV:" + chr(10) + f"A customized CV has been generated and attached: {Path(tailored_cv_info['cv_file_path']).name}" if tailored_cv_info else ''}

VIEW JOB: {job.get('url', 'N/A')}

---
Automatically matched by your Job Agent System
Source: {job.get('source', 'profesia.sk')} | {job.get('scraped_at', '')}
        """

        return text.strip()

    def _create_batch_email_html(
        self,
        jobs: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ) -> str:
        """Create HTML for batch email notification.

        Args:
            jobs: List of jobs
            summary: Summary statistics

        Returns:
            HTML email body
        """
        jobs_html = ''
        for i, job in enumerate(jobs, 1):
            jobs_html += f"""
            <div class="job-card">
                <h3>{i}. {job.get('title', 'Unknown')} - {job.get('company', 'Unknown')}</h3>
                <p>📍 {job.get('location', 'N/A')} | Match: {job.get('match_score', 0):.0%}</p>
                <p>{job.get('description', '')[:200]}...</p>
                <a href="{job.get('url', '#')}" class="button">View Job</a>
            </div>
            """

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 30px; border-radius: 5px; text-align: center; }}
                .summary {{ background-color: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 5px; }}
                .job-card {{ border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .button {{ display: inline-block; padding: 8px 15px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📬 Daily Job Report</h1>
                    <p>You have {len(jobs)} new job matches!</p>
                </div>

                <div class="summary">
                    <h2>Summary</h2>
                    <ul>
                        <li>Jobs Scraped: {summary.get('scraped', 0)}</li>
                        <li>Initial Matches: {summary.get('matched', 0)}</li>
                        <li>Approved After Critique: {summary.get('approved', 0)}</li>
                        <li>CVs Generated: {summary.get('cvs_generated', 0)}</li>
                    </ul>
                </div>

                {jobs_html}

                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center;">
                    <p>Job Agent System - Automated Job Matching</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _create_batch_email_text(
        self,
        jobs: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ) -> str:
        """Create plain text for batch email notification.

        Args:
            jobs: List of jobs
            summary: Summary statistics

        Returns:
            Plain text email body
        """
        jobs_text = '\n\n'.join([
            f"{i}. {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}\n"
            f"   Location: {job.get('location', 'N/A')}\n"
            f"   Match Score: {job.get('match_score', 0):.0%}\n"
            f"   URL: {job.get('url', 'N/A')}"
            for i, job in enumerate(jobs, 1)
        ])

        text = f"""
📬 DAILY JOB REPORT

You have {len(jobs)} new job matches!

SUMMARY:
- Jobs Scraped: {summary.get('scraped', 0)}
- Initial Matches: {summary.get('matched', 0)}
- Approved After Critique: {summary.get('approved', 0)}
- CVs Generated: {summary.get('cvs_generated', 0)}

MATCHED JOBS:

{jobs_text}

---
Job Agent System - Automated Job Matching
        """

        return text.strip()

    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Attach a file to the email message.

        Args:
            msg: Email message object
            file_path: Path to file to attach
        """
        try:
            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            filename = Path(file_path).name
            part.add_header('Content-Disposition', f'attachment; filename= {filename}')
            msg.attach(part)

        except Exception as e:
            self.log_error(f"Failed to attach file {file_path}: {e}")

    def _send_email(self, msg: MIMEMultipart):
        """Send email message via SMTP.

        Args:
            msg: Email message to send
        """
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)

    def _validate_email_config(self) -> bool:
        """Validate email configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        if not self.smtp_username:
            self.log_error("SMTP_USERNAME not configured")
            return False

        if not self.smtp_password:
            self.log_error("SMTP_PASSWORD not configured")
            return False

        if not self.notification_email:
            self.log_error("NOTIFICATION_EMAIL not configured")
            return False

        return True
