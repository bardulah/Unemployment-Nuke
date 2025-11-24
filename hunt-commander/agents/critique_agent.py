"""Critique agent for validating job matches."""
import os
from typing import List, Dict, Any
from openai import OpenAI
from anthropic import Anthropic
from .base_agent import BaseAgent

class CritiqueAgent(BaseAgent):
    """Agent responsible for critiquing and validating job matches."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the critique agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.openai_client = None
        self.anthropic_client = None
        self.strict_mode = config.get('critique_strict_mode', False)
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
        matched_jobs: List[Dict[str, Any]],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Critique and validate matched jobs.

        Args:
            matched_jobs: List of jobs that were matched by the matcher agent
            cv_content: User's CV content
            preferences: User preferences dictionary

        Returns:
            List of validated jobs (some may be rejected)
        """
        self.log_info(f"Critiquing {len(matched_jobs)} matched jobs")
        validated_jobs = []

        for job in matched_jobs:
            critique_result = self._critique_job(job, cv_content, preferences)

            if critique_result['approved']:
                job['critique_score'] = critique_result['score']
                job['critique_feedback'] = critique_result['feedback']
                job['red_flags'] = critique_result['red_flags']
                job['strengths'] = critique_result['strengths']
                validated_jobs.append(job)
                self.log_debug(f"✓ Approved: {job['title']} at {job.get('company', 'Unknown')}")
            else:
                self.log_debug(
                    f"✗ Rejected: {job['title']} at {job.get('company', 'Unknown')} - "
                    f"Reason: {critique_result['rejection_reason']}"
                )

        self.log_info(
            f"Validation complete: {len(validated_jobs)} approved, "
            f"{len(matched_jobs) - len(validated_jobs)} rejected"
        )
        return validated_jobs

    def _critique_job(
        self,
        job: Dict[str, Any],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Critique a single matched job.

        Args:
            job: Job dictionary with match information
            cv_content: User's CV content
            preferences: User preferences

        Returns:
            Dictionary with critique results
        """
        self.log_debug(f"Critiquing: {job.get('title', 'Unknown')}")

        # Use AI for intelligent critique
        if self.anthropic_client:
            return self._ai_critique_anthropic(job, cv_content, preferences)
        elif self.openai_client:
            return self._ai_critique_openai(job, cv_content, preferences)
        else:
            # Fallback to rule-based critique
            return self._rule_based_critique(job)

    def _ai_critique_anthropic(
        self,
        job: Dict[str, Any],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use Anthropic Claude for intelligent job critique.

        Args:
            job: Job dictionary
            cv_content: User's CV content
            preferences: User preferences

        Returns:
            Critique result dictionary
        """
        prompt = self._build_critique_prompt(job, cv_content, preferences)

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text
            return self._parse_critique_response(result_text)

        except Exception as e:
            self.log_error(f"Error in AI critique: {e}")
            return self._rule_based_critique(job)

    def _ai_critique_openai(
        self,
        job: Dict[str, Any],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use OpenAI GPT for intelligent job critique.

        Args:
            job: Job dictionary
            cv_content: User's CV content
            preferences: User preferences

        Returns:
            Critique result dictionary
        """
        prompt = self._build_critique_prompt(job, cv_content, preferences)

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a critical career advisor who reviews job matches and identifies potential issues."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            result_text = response.choices[0].message.content
            return self._parse_critique_response(result_text)

        except Exception as e:
            self.log_error(f"Error in AI critique: {e}")
            return self._rule_based_critique(job)

    def _build_critique_prompt(
        self,
        job: Dict[str, Any],
        cv_content: str,
        preferences: Dict[str, Any]
    ) -> str:
        """Build the prompt for AI critique.

        Args:
            job: Job dictionary
            cv_content: User's CV content
            preferences: User preferences

        Returns:
            Prompt string
        """
        prompt = f"""You are a critical career advisor reviewing a job match. Your job is to identify potential issues, red flags, and provide an honest second opinion.

JOB INFORMATION:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Description: {job.get('description', 'N/A')}
Requirements: {job.get('requirements', 'N/A')}
Full Description: {job.get('full_description', 'N/A')}

INITIAL MATCH RESULTS:
Match Score: {job.get('match_score', 0)}
Match Reasons: {', '.join(job.get('match_reasons', []))}
Missing Skills: {', '.join(job.get('missing_skills', []))}

CANDIDATE CV:
{cv_content}

CANDIDATE PREFERENCES:
{preferences}

Please provide a critical review in the following format:

APPROVED: [YES/NO]
SCORE: [0.0-1.0]
REJECTION_REASON: [If not approved, explain why]
FEEDBACK:
- [Critical feedback point 1]
- [Critical feedback point 2]
RED_FLAGS:
- [Red flag 1]
- [Red flag 2]
STRENGTHS:
- [Strength 1]
- [Strength 2]

Look for:
1. Unrealistic requirements or expectations
2. Missing critical skills that can't be easily learned
3. Misalignment with career progression
4. Location/remote work concerns
5. Salary expectations vs reality
6. Company culture fit
7. Job description clarity and completeness
8. Potential bait-and-switch indicators

Be especially critical if strict_mode is enabled: {self.strict_mode}"""

        return prompt

    def _parse_critique_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI critique response into structured result.

        Args:
            response_text: AI response text

        Returns:
            Critique result dictionary
        """
        result = {
            'approved': False,
            'score': 0.0,
            'rejection_reason': '',
            'feedback': [],
            'red_flags': [],
            'strengths': []
        }

        try:
            lines = response_text.strip().split('\n')
            current_section = None

            for line in lines:
                line = line.strip()

                if line.startswith('APPROVED:'):
                    approved_text = line.replace('APPROVED:', '').strip().upper()
                    result['approved'] = approved_text in ['YES', 'TRUE', 'APPROVE']
                elif line.startswith('SCORE:'):
                    score_text = line.replace('SCORE:', '').strip()
                    import re
                    match = re.search(r'0?\.\d+|1\.0', score_text)
                    if match:
                        result['score'] = float(match.group())
                elif line.startswith('REJECTION_REASON:'):
                    result['rejection_reason'] = line.replace('REJECTION_REASON:', '').strip()
                elif line.startswith('FEEDBACK:'):
                    current_section = 'feedback'
                elif line.startswith('RED_FLAGS:'):
                    current_section = 'red_flags'
                elif line.startswith('STRENGTHS:'):
                    current_section = 'strengths'
                elif line.startswith('- ') and current_section:
                    item = line[2:].strip()
                    if item:
                        result[current_section].append(item)

        except Exception as e:
            self.log_error(f"Error parsing critique response: {e}")

        return result

    def _rule_based_critique(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based critique when AI is not available.

        Args:
            job: Job dictionary

        Returns:
            Critique result dictionary
        """
        match_score = job.get('match_score', 0)
        missing_skills = job.get('missing_skills', [])

        # Simple rules
        approved = True
        rejection_reason = ''
        feedback = []
        red_flags = []
        strengths = []

        # Check if match score is sufficient
        if match_score < 0.5:
            approved = False
            rejection_reason = "Match score too low"

        # Check for too many missing skills
        if len(missing_skills) > 3:
            if self.strict_mode:
                approved = False
                rejection_reason = "Too many missing required skills"
            else:
                red_flags.append(f"Missing {len(missing_skills)} skills: {', '.join(missing_skills[:3])}")

        # Check for red flag keywords in description
        job_text = f"{job.get('description', '')} {job.get('full_description', '')}".lower()
        red_flag_keywords = ['unpaid', 'no salary', 'commission only', 'must have car']

        for keyword in red_flag_keywords:
            if keyword in job_text:
                red_flags.append(f"Found potential red flag: '{keyword}'")

        # Add positive feedback
        if match_score >= 0.8:
            strengths.append("Strong match score")

        if not missing_skills:
            strengths.append("All required skills matched")

        if not red_flags:
            strengths.append("No obvious red flags detected")

        if approved:
            feedback.append("Job passes basic validation criteria")
        else:
            feedback.append(rejection_reason)

        return {
            'approved': approved,
            'score': match_score,
            'rejection_reason': rejection_reason,
            'feedback': feedback,
            'red_flags': red_flags,
            'strengths': strengths
        }
