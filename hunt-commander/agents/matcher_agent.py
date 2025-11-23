"""Matcher agent for comparing jobs with CV and preferences."""
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from anthropic import Anthropic
from .base_agent import BaseAgent

class MatcherAgent(BaseAgent):
    """Agent responsible for matching job listings with user CV and preferences."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the matcher agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.openai_client = None
        self.anthropic_client = None
        self.min_match_score = config.get('min_match_score', 0.7)
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize AI clients if API keys are available."""
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')

        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)
            self.log_info("OpenAI client initialized")

        if anthropic_key:
            self.anthropic_client = Anthropic(api_key=anthropic_key)
            self.log_info("Anthropic client initialized")

    def execute(
        self,
        jobs: List[Dict[str, Any]],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Match jobs against CV and preferences.

        Args:
            jobs: List of job dictionaries
            cv_content: User's CV content
            preferences: User preferences dictionary

        Returns:
            List of matched jobs with match scores and reasons
        """
        self.log_info(f"Matching {len(jobs)} jobs against CV and preferences")
        matched_jobs = []

        for job in jobs:
            match_result = self._match_job(job, cv_content, preferences)

            if match_result['score'] >= self.min_match_score:
                job['match_score'] = match_result['score']
                job['match_reasons'] = match_result['reasons']
                job['missing_skills'] = match_result['missing_skills']
                matched_jobs.append(job)

        self.log_info(f"Found {len(matched_jobs)} matching jobs (score >= {self.min_match_score})")
        return matched_jobs

    def _match_job(
        self,
        job: Dict[str, Any],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Match a single job against CV and preferences.

        Args:
            job: Job dictionary
            cv_content: User's CV content
            preferences: User preferences

        Returns:
            Dictionary with match score, reasons, and missing skills
        """
        self.log_debug(f"Matching job: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")

        # Use AI for intelligent matching
        if self.anthropic_client:
            return self._ai_match_anthropic(job, cv_content, preferences)
        elif self.openai_client:
            return self._ai_match_openai(job, cv_content, preferences)
        else:
            # Fallback to rule-based matching
            return self._rule_based_match(job, preferences)

    def _ai_match_anthropic(
        self,
        job: Dict[str, Any],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use Anthropic Claude for intelligent job matching.

        Args:
            job: Job dictionary
            cv_content: User's CV content
            preferences: User preferences

        Returns:
            Match result dictionary
        """
        prompt = self._build_matching_prompt(job, cv_content, preferences)

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text
            return self._parse_ai_response(result_text)

        except Exception as e:
            self.log_error(f"Error in AI matching: {e}")
            return self._rule_based_match(job, preferences)

    def _ai_match_openai(
        self,
        job: Dict[str, Any],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use OpenAI GPT for intelligent job matching.

        Args:
            job: Job dictionary
            cv_content: User's CV content
            preferences: User preferences

        Returns:
            Match result dictionary
        """
        prompt = self._build_matching_prompt(job, cv_content, preferences)

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert job matcher and career advisor."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            result_text = response.choices[0].message.content
            return self._parse_ai_response(result_text)

        except Exception as e:
            self.log_error(f"Error in AI matching: {e}")
            return self._rule_based_match(job, preferences)

    def _build_matching_prompt(
        self,
        job: Dict[str, Any],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> str:
        """Build the prompt for AI matching.

        Args:
            job: Job dictionary
            cv_content: User's CV content
            preferences: User preferences

        Returns:
            Prompt string
        """
        prompt = f"""Analyze this job posting and determine if it's a good match for the candidate.

JOB INFORMATION:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Description: {job.get('description', 'N/A')}
Requirements: {job.get('requirements', 'N/A')}
Full Description: {job.get('full_description', 'N/A')}

CANDIDATE CV:
{cv_content}

CANDIDATE PREFERENCES:
- Desired job titles: {', '.join(preferences.get('job_titles', []))}
- Preferred locations: {', '.join(preferences.get('locations', []))}
- Required skills: {', '.join(preferences.get('required_skills', []))}
- Preferred skills: {', '.join(preferences.get('preferred_skills', []))}
- Experience level: {preferences.get('experience_level', 'N/A')}

Please provide a match analysis in the following format:

SCORE: [0.0-1.0]
REASONS:
- [Reason 1]
- [Reason 2]
- [Reason 3]
MISSING_SKILLS:
- [Missing skill 1]
- [Missing skill 2]

Base the score on:
1. Job title alignment (25%)
2. Skills match (40%)
3. Experience level fit (20%)
4. Location preference (10%)
5. Overall culture/company fit (5%)

Be honest and critical in your assessment."""

        return prompt

    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response into structured match result.

        Args:
            response_text: AI response text

        Returns:
            Match result dictionary
        """
        result = {
            'score': 0.0,
            'reasons': [],
            'missing_skills': []
        }

        try:
            lines = response_text.strip().split('\n')
            current_section = None

            for line in lines:
                line = line.strip()

                if line.startswith('SCORE:'):
                    score_text = line.replace('SCORE:', '').strip()
                    # Extract first number found
                    import re
                    match = re.search(r'0?\.\d+|1\.0', score_text)
                    if match:
                        result['score'] = float(match.group())
                elif line.startswith('REASONS:'):
                    current_section = 'reasons'
                elif line.startswith('MISSING_SKILLS:'):
                    current_section = 'missing_skills'
                elif line.startswith('- ') and current_section:
                    item = line[2:].strip()
                    if item:
                        result[current_section].append(item)

        except Exception as e:
            self.log_error(f"Error parsing AI response: {e}")

        return result

    def _rule_based_match(
        self,
        job: Dict[str, Any],
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback rule-based matching when AI is not available.

        Args:
            job: Job dictionary
            preferences: User preferences

        Returns:
            Match result dictionary
        """
        score = 0.0
        reasons = []
        missing_skills = []

        job_text = (
            f"{job.get('title', '')} {job.get('description', '')} "
            f"{job.get('requirements', '')} {job.get('full_description', '')}"
        ).lower()

        # Check job title
        job_titles = preferences.get('job_titles', [])
        title_match = any(title.lower() in job.get('title', '').lower() for title in job_titles)
        if title_match:
            score += 0.25
            reasons.append("Job title matches preferences")

        # Check location
        locations = preferences.get('locations', [])
        location_match = any(loc.lower() in job.get('location', '').lower() for loc in locations)
        if location_match:
            score += 0.10
            reasons.append("Location matches preferences")

        # Check required skills
        required_skills = preferences.get('required_skills', [])
        matched_required = sum(1 for skill in required_skills if skill.lower() in job_text)
        if required_skills:
            skill_score = matched_required / len(required_skills)
            score += 0.40 * skill_score
            if skill_score > 0:
                reasons.append(f"Matches {matched_required}/{len(required_skills)} required skills")

            missing_skills = [skill for skill in required_skills if skill.lower() not in job_text]

        # Check preferred skills
        preferred_skills = preferences.get('preferred_skills', [])
        matched_preferred = sum(1 for skill in preferred_skills if skill.lower() in job_text)
        if preferred_skills:
            pref_score = matched_preferred / len(preferred_skills)
            score += 0.20 * pref_score
            if pref_score > 0:
                reasons.append(f"Matches {matched_preferred}/{len(preferred_skills)} preferred skills")

        # Check salary if specified
        min_salary = preferences.get('min_salary')
        if min_salary and job.get('salary'):
            reasons.append("Salary information available")

        if not reasons:
            reasons.append("No strong matches found")

        return {
            'score': round(score, 2),
            'reasons': reasons,
            'missing_skills': missing_skills
        }
