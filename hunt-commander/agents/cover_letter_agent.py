"""Cover Letter Generator Agent - AI-powered personalized cover letters."""
import os
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from utils import log


class CoverLetterAgent(BaseAgent):
    """Agent for generating personalized cover letters."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize cover letter agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__("CoverLetterAgent", config)

    def execute(
        self,
        job: Dict[str, Any],
        cv_content: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate personalized cover letter.

        Args:
            job: Job details
            cv_content: User's CV content
            user_info: Additional user information

        Returns:
            Cover letter content and metadata
        """
        log.info(f"Generating cover letter for {job.get('title', 'Unknown')}")

        # Extract key information
        job_title = job.get('title', '')
        company = job.get('company', 'your company')
        description = job.get('description', '')
        requirements = job.get('requirements', '')

        # Generate cover letter
        cover_letter = self._generate_cover_letter(
            job_title, company, description, requirements, cv_content, user_info
        )

        # Generate subject line
        subject_line = self._generate_subject_line(job_title, company)

        return {
            "cover_letter": cover_letter,
            "subject_line": subject_line,
            "word_count": len(cover_letter.split()),
            "tone": "professional_enthusiastic"
        }

    def _generate_cover_letter(
        self,
        job_title: str,
        company: str,
        description: str,
        requirements: str,
        cv_content: str,
        user_info: Optional[Dict[str, Any]]
    ) -> str:
        """Generate personalized cover letter content.

        Args:
            job_title: Job title
            company: Company name
            description: Job description
            requirements: Job requirements
            cv_content: CV content
            user_info: User information

        Returns:
            Cover letter text
        """
        # Extract key skills from requirements
        key_skills = self._extract_key_skills(requirements)

        # Extract relevant experience from CV
        relevant_experience = self._extract_relevant_experience(cv_content, key_skills)

        # Get user details
        name = user_info.get('name', 'Your Name') if user_info else 'Your Name'
        email = user_info.get('email', 'your.email@example.com') if user_info else 'your.email@example.com'
        phone = user_info.get('phone', '+421 XXX XXX XXX') if user_info else '+421 XXX XXX XXX'

        # Generate compelling opening
        opening = self._generate_opening(job_title, company)

        # Generate body paragraphs
        body_experience = self._generate_experience_paragraph(relevant_experience, key_skills)
        body_motivation = self._generate_motivation_paragraph(company, job_title)
        body_value = self._generate_value_proposition(job_title, key_skills)

        # Generate closing
        closing = self._generate_closing()

        # Assemble cover letter
        cover_letter = f"""{name}
{email} | {phone}
Bratislava, Slovakia

{company}
Hiring Manager

Dear Hiring Manager,

{opening}

{body_experience}

{body_motivation}

{body_value}

{closing}

Best regards,
{name}"""

        return cover_letter

    def _generate_opening(self, job_title: str, company: str) -> str:
        """Generate compelling opening paragraph.

        Args:
            job_title: Job title
            company: Company name

        Returns:
            Opening paragraph
        """
        openings = [
            f"I am writing to express my strong interest in the {job_title} position at {company}. With my proven track record in Python development and passion for building scalable backend systems, I am confident I would be a valuable addition to your team.",

            f"I was excited to discover the {job_title} opening at {company}. As a dedicated Python developer with extensive experience in modern backend technologies, I believe my skills align perfectly with your requirements.",

            f"The {job_title} position at {company} immediately caught my attention as it combines my technical expertise with my passion for solving complex problems. I am eager to bring my Python development experience to your innovative team.",

            f"I am reaching out regarding the {job_title} role at {company}. Your company's reputation for technical excellence and innovation makes this opportunity particularly appealing, and I am confident my background in Python development would contribute significantly to your team's success."
        ]

        # Select based on company name hash for consistency
        index = hash(company) % len(openings)
        return openings[index]

    def _generate_experience_paragraph(
        self,
        experience: str,
        key_skills: list
    ) -> str:
        """Generate experience paragraph.

        Args:
            experience: Relevant experience
            key_skills: Key skills from job

        Returns:
            Experience paragraph
        """
        skills_list = ", ".join(key_skills[:4])  # Top 4 skills

        return f"""In my current role, I have gained extensive experience with {skills_list}, which directly aligns with your requirements. I have successfully delivered multiple production systems, handling everything from database design and API development to deployment and monitoring. My work has consistently focused on writing clean, maintainable code that scales effectively."""

    def _generate_motivation_paragraph(self, company: str, job_title: str) -> str:
        """Generate motivation paragraph.

        Args:
            company: Company name
            job_title: Job title

        Returns:
            Motivation paragraph
        """
        return f"""What excites me most about {company} is the opportunity to work on challenging problems at scale. I am particularly drawn to your technical stack and the innovative approach your team takes to development. The {job_title} role represents exactly the kind of challenge I am seeking in my career, where I can leverage my technical skills while continuing to grow as a developer."""

    def _generate_value_proposition(self, job_title: str, key_skills: list) -> str:
        """Generate value proposition paragraph.

        Args:
            job_title: Job title
            key_skills: Key skills

        Returns:
            Value proposition paragraph
        """
        return f"""I am confident that I can contribute immediately to your team. My hands-on experience with the technologies you use, combined with my problem-solving abilities and collaborative approach, would allow me to hit the ground running. I am excited about the possibility of bringing my technical expertise and enthusiasm to the {job_title} role."""

    def _generate_closing(self) -> str:
        """Generate closing paragraph.

        Returns:
            Closing paragraph
        """
        closings = [
            "Thank you for considering my application. I would welcome the opportunity to discuss how my background, skills, and enthusiasm can contribute to your team's success. I am available for an interview at your convenience and look forward to hearing from you.",

            "I appreciate your time and consideration. I am eager to discuss how my experience and skills align with your needs. Please feel free to contact me at your convenience to arrange an interview. I look forward to the possibility of contributing to your team.",

            "Thank you for reviewing my application. I am enthusiastic about the opportunity to join your team and would be delighted to discuss my qualifications in more detail. I am available for an interview at your earliest convenience."
        ]

        return closings[0]

    def _generate_subject_line(self, job_title: str, company: str) -> str:
        """Generate email subject line.

        Args:
            job_title: Job title
            company: Company name

        Returns:
            Subject line
        """
        return f"Application for {job_title} Position - Experienced Python Developer"

    def _extract_key_skills(self, requirements: str) -> list:
        """Extract key skills from job requirements.

        Args:
            requirements: Job requirements text

        Returns:
            List of key skills
        """
        # Common skills to look for
        common_skills = [
            'Python', 'Django', 'Flask', 'FastAPI',
            'REST API', 'PostgreSQL', 'MySQL', 'MongoDB',
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
            'Git', 'CI/CD', 'Redis', 'RabbitMQ',
            'Microservices', 'GraphQL', 'Celery'
        ]

        found_skills = []
        requirements_lower = requirements.lower()

        for skill in common_skills:
            if skill.lower() in requirements_lower:
                found_skills.append(skill)

        return found_skills[:6]  # Return top 6

    def _extract_relevant_experience(self, cv_content: str, key_skills: list) -> str:
        """Extract relevant experience from CV.

        Args:
            cv_content: CV content
            key_skills: Key skills to focus on

        Returns:
            Relevant experience summary
        """
        # Simple extraction - in production would use NLP
        lines = cv_content.split('\n')
        relevant_lines = []

        for line in lines:
            for skill in key_skills:
                if skill.lower() in line.lower():
                    relevant_lines.append(line.strip())
                    break

        return ' '.join(relevant_lines[:3])  # Top 3 relevant lines

    def generate_batch(
        self,
        jobs: list,
        cv_content: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate cover letters for multiple jobs.

        Args:
            jobs: List of job dictionaries
            cv_content: User's CV content
            user_info: User information

        Returns:
            Dictionary mapping job IDs to cover letters
        """
        results = {}

        for job in jobs:
            job_id = job.get('id') or job.get('url')
            try:
                cover_letter = self.execute(job, cv_content, user_info)
                results[job_id] = cover_letter
                log.debug(f"Generated cover letter for {job.get('title')}")
            except Exception as e:
                log.error(f"Failed to generate cover letter for {job.get('title')}: {e}")
                results[job_id] = None

        return results
