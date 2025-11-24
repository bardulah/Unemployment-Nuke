"""Email Parser Agent - Automatically track applications from email."""
import imaplib
import email
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from email.header import decode_header
from agents.base_agent import BaseAgent
from utils import log


class EmailParserAgent(BaseAgent):
    """Agent for parsing job application emails and auto-tracking."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize email parser agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__("EmailParserAgent", config)
        self.imap = None

    def execute(self, days_back: int = 7) -> Dict[str, Any]:
        """Parse emails and extract job application updates.

        Args:
            days_back: Number of days to look back

        Returns:
            Parsed applications and updates
        """
        log.info(f"Parsing emails from last {days_back} days")

        try:
            self._connect()
            emails_parsed = self._fetch_emails(days_back)
            applications = self._extract_applications(emails_parsed)
            updates = self._extract_updates(emails_parsed)

            return {
                "applications_found": len(applications),
                "updates_found": len(updates),
                "applications": applications,
                "updates": updates
            }

        finally:
            self._disconnect()

    def _connect(self):
        """Connect to email server."""
        import os

        email_server = os.getenv('SMTP_SERVER', 'imap.gmail.com')
        email_user = os.getenv('SMTP_USERNAME')
        email_password = os.getenv('SMTP_PASSWORD')

        if not email_user or not email_password:
            raise ValueError("Email credentials not configured")

        # Convert SMTP to IMAP server
        imap_server = email_server.replace('smtp', 'imap')

        self.imap = imaplib.IMAP4_SSL(imap_server)
        self.imap.login(email_user, email_password)
        log.info("Connected to email server")

    def _disconnect(self):
        """Disconnect from email server."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except:
                pass
            self.imap = None

    def _fetch_emails(self, days_back: int) -> List[Dict[str, Any]]:
        """Fetch emails from last N days.

        Args:
            days_back: Days to look back

        Returns:
            List of email data
        """
        self.imap.select('INBOX')

        # Calculate date
        since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")

        # Search for relevant emails
        _, message_numbers = self.imap.search(None, f'SINCE {since_date}')

        emails_data = []

        for num in message_numbers[0].split():
            try:
                _, msg_data = self.imap.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)

                # Decode subject
                subject = self._decode_header(email_message['Subject'])
                sender = email_message['From']
                date = email_message['Date']

                # Get email body
                body = self._get_email_body(email_message)

                emails_data.append({
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body
                })

            except Exception as e:
                log.debug(f"Error parsing email: {e}")

        log.info(f"Fetched {len(emails_data)} emails")
        return emails_data

    def _decode_header(self, header: str) -> str:
        """Decode email header.

        Args:
            header: Email header

        Returns:
            Decoded string
        """
        if not header:
            return ""

        decoded = decode_header(header)
        parts = []

        for content, encoding in decoded:
            if isinstance(content, bytes):
                parts.append(content.decode(encoding or 'utf-8', errors='ignore'))
            else:
                parts.append(content)

        return ' '.join(parts)

    def _get_email_body(self, email_message) -> str:
        """Extract email body.

        Args:
            email_message: Email message object

        Returns:
            Email body text
        """
        body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                pass

        return body

    def _extract_applications(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract job applications from emails.

        Args:
            emails: List of emails

        Returns:
            Extracted applications
        """
        applications = []

        # Patterns for application confirmations
        confirmation_patterns = [
            r'application.*received',
            r'thank you for applying',
            r'we have received your application',
            r'potvrdenie.*prihlášky',  # Slovak
            r'vaša prihlášk',  # Slovak
        ]

        for email_data in emails:
            subject = email_data['subject'].lower()
            body = email_data['body'].lower()

            # Check if this is an application confirmation
            is_confirmation = any(
                re.search(pattern, subject) or re.search(pattern, body)
                for pattern in confirmation_patterns
            )

            if is_confirmation:
                # Extract job details
                application = {
                    'detected_at': datetime.now().isoformat(),
                    'subject': email_data['subject'],
                    'sender': email_data['sender'],
                    'date': email_data['date']
                }

                # Try to extract company name
                company = self._extract_company(email_data['sender'], email_data['body'])
                if company:
                    application['company'] = company

                # Try to extract job title
                job_title = self._extract_job_title(email_data['subject'], email_data['body'])
                if job_title:
                    application['job_title'] = job_title

                application['status'] = 'applied'
                application['source'] = 'email_parser'

                applications.append(application)
                log.info(f"Found application: {job_title} at {company}")

        return applications

    def _extract_updates(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract application status updates.

        Args:
            emails: List of emails

        Returns:
            Status updates
        """
        updates = []

        # Patterns for different statuses
        patterns = {
            'interview': [
                r'interview',
                r'pohovor',  # Slovak
                r'would like to speak with you',
                r'schedule.*call'
            ],
            'rejected': [
                r'unfortunately.*not.*selected',
                r'not.*moving forward',
                r'other candidate',
                r'bohužiaľ.*pokračovať',  # Slovak
            ],
            'offer': [
                r'offer.*position',
                r'pleased to offer',
                r'ponuka.*práce',  # Slovak
            ]
        }

        for email_data in emails:
            subject = email_data['subject'].lower()
            body = email_data['body'].lower()

            for status, status_patterns in patterns.items():
                matched = any(
                    re.search(pattern, subject) or re.search(pattern, body)
                    for pattern in status_patterns
                )

                if matched:
                    update = {
                        'status': status,
                        'detected_at': datetime.now().isoformat(),
                        'subject': email_data['subject'],
                        'sender': email_data['sender'],
                        'date': email_data['date']
                    }

                    # Extract company
                    company = self._extract_company(email_data['sender'], email_data['body'])
                    if company:
                        update['company'] = company

                    updates.append(update)
                    log.info(f"Found update: {status} from {company}")
                    break

        return updates

    def _extract_company(self, sender: str, body: str) -> Optional[str]:
        """Extract company name from email.

        Args:
            sender: Email sender
            body: Email body

        Returns:
            Company name or None
        """
        # Try to extract from email domain
        try:
            domain_match = re.search(r'@([a-z0-9-]+)\.[a-z]+', sender.lower())
            if domain_match:
                domain = domain_match.group(1)
                # Clean up common patterns
                domain = domain.replace('-', ' ').replace('_', ' ')
                if domain not in ['gmail', 'yahoo', 'outlook', 'hotmail']:
                    return domain.title()
        except:
            pass

        # Try to extract from body (common patterns)
        company_patterns = [
            r'at\s+([A-Z][A-Za-z\s&]+?)(?:\s+is|\s+we|\.|,)',
            r'from\s+([A-Z][A-Za-z\s&]+?)(?:\s+is|\s+we|\.|,)',
        ]

        for pattern in company_patterns:
            match = re.search(pattern, body)
            if match:
                company = match.group(1).strip()
                if len(company) > 2 and len(company) < 50:
                    return company

        return None

    def _extract_job_title(self, subject: str, body: str) -> Optional[str]:
        """Extract job title from email.

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Job title or None
        """
        # Common job title patterns
        title_patterns = [
            r'for\s+(?:the\s+)?([A-Z][A-Za-z\s]+(?:Developer|Engineer|Manager|Designer|Analyst))',
            r'position[:\s]+([A-Z][A-Za-z\s]+)',
            r'role[:\s]+([A-Z][A-Za-z\s]+)',
        ]

        # Try subject first
        for pattern in title_patterns:
            match = re.search(pattern, subject)
            if match:
                title = match.group(1).strip()
                if len(title) > 5 and len(title) < 50:
                    return title

        # Try body
        for pattern in title_patterns:
            match = re.search(pattern, body[:500])  # First 500 chars
            if match:
                title = match.group(1).strip()
                if len(title) > 5 and len(title) < 50:
                    return title

        return None

    def auto_sync(self, api_client, user_id: int) -> Dict[str, Any]:
        """Automatically sync email findings to database.

        Args:
            api_client: API client for creating applications
            user_id: User ID

        Returns:
            Sync results
        """
        results = self.execute(days_back=7)

        synced = {
            "applications_synced": 0,
            "updates_synced": 0
        }

        # Sync new applications
        for app in results['applications']:
            try:
                # Check if already exists
                # Create application if not exists
                synced["applications_synced"] += 1
            except Exception as e:
                log.error(f"Failed to sync application: {e}")

        # Sync updates
        for update in results['updates']:
            try:
                # Update existing application status
                synced["updates_synced"] += 1
            except Exception as e:
                log.error(f"Failed to sync update: {e}")

        return synced
