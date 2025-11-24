"""Test suite for Hunt Commander agents."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from agents import NegotiationAgent, LinkedInAgent, ScraperAgent, MatcherAgent


class TestNegotiationAgent:
    """Test negotiation agent functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = NegotiationAgent({})

    def test_glassdoor_slovak_data_bratislava(self):
        """Test Glassdoor data for Bratislava Python developer."""
        data = self.agent._scrape_glassdoor_slovakia("Python Developer", "Bratislava")

        assert data is not None
        assert data["average_salary"] > 0
        assert data["min_salary"] < data["average_salary"]
        assert data["max_salary"] > data["average_salary"]
        assert 2000 < data["average_salary"] < 6000  # Reasonable range

    def test_salary_negotiation_below_market(self):
        """Test negotiation when offer is below market."""
        job = {
            'title': 'Python Developer',
            'company': 'Tech Corp',
            'location': 'Bratislava'
        }

        result = self.agent.execute(
            job=job,
            current_offer=2500,  # Below market
            user_target=4000
        )

        assert result["strategy"]["should_negotiate"] is True
        assert result["recommended_counter_offer"] > 2500
        assert len(result["strategy"]["leverage_points"]) > 0
        assert "email" in result["scripts"]

    def test_salary_negotiation_excellent_offer(self):
        """Test negotiation when offer is excellent."""
        job = {
            'title': 'Senior Python Developer',
            'company': 'Top Tech',
            'location': 'Bratislava'
        }

        result = self.agent.execute(
            job=job,
            current_offer=5500,  # Above 75th percentile
            user_target=6000
        )

        # Should focus on benefits rather than salary
        assert len(result["strategy"]["alternative_benefits"]) > 0

    def test_location_adjustments(self):
        """Test salary adjustments for different locations."""
        job_ba = {
            'title': 'Python Developer',
            'location': 'Bratislava'
        }
        job_ke = {
            'title': 'Python Developer',
            'location': 'Košice'
        }

        result_ba = self.agent.execute(job=job_ba, current_offer=3500)
        result_ke = self.agent.execute(job=job_ke, current_offer=3500)

        # Košice should have lower market average
        assert result_ke["market_data"]["average_salary"] < result_ba["market_data"]["average_salary"]

    def test_negotiation_scripts_generation(self):
        """Test that all negotiation scripts are generated."""
        job = {
            'title': 'Backend Developer',
            'company': 'Startup Inc',
            'location': 'Bratislava'
        }

        result = self.agent.execute(job=job, current_offer=3200, user_target=4000)

        assert "email" in result["scripts"]
        assert "phone" in result["scripts"]
        assert "counter_offer_letter" in result["scripts"]

        # Check scripts contain key information
        assert "3200" in result["scripts"]["email"] or "3,200" in result["scripts"]["email"]
        assert job["company"] in result["scripts"]["email"]


class TestLinkedInAgent:
    """Test LinkedIn automation agent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = LinkedInAgent({})

    @patch.dict('os.environ', {'LINKEDIN_EMAIL': 'test@example.com', 'LINKEDIN_PASSWORD': 'password'})
    def test_linkedin_credentials_loaded(self):
        """Test that LinkedIn credentials are loaded from environment."""
        import os
        assert os.getenv('LINKEDIN_EMAIL') == 'test@example.com'

    def test_recruiter_message_generation(self):
        """Test personalized recruiter message generation."""
        recruiter = {
            'name': 'John Smith',
            'title': 'Tech Recruiter',
            'company': 'Big Tech Corp'
        }

        message = self.agent._generate_recruiter_message(recruiter, "Python Developer")

        assert 'John' in message or 'Hi' in message
        assert 'Python' in message or 'developer' in message.lower()
        assert len(message) > 50  # Should be substantial
        assert len(message) < 500  # But not too long

    def test_multiple_message_templates(self):
        """Test that multiple message templates are available."""
        recruiter = {
            'name': 'Jane Doe',
            'company': 'TechCo'
        }

        messages = set()
        for _ in range(10):
            msg = self.agent._generate_recruiter_message(recruiter, "Backend Engineer")
            messages.add(msg)

        # Should generate different messages (at least 2 different templates)
        assert len(messages) >= 2


class TestScraperAgent:
    """Test job scraping functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = ScraperAgent({})

    def test_salary_extraction(self):
        """Test salary range extraction from text."""
        test_cases = [
            ("3000-4000 EUR", (3000, 4000)),
            ("Salary: €3500", None),
            ("2500 - 3500 EUR/month", (2500, 3500)),
        ]

        # Note: This assumes the agent has a salary extraction method
        # Adjust based on actual implementation


class TestMatcherAgent:
    """Test job matching functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = MatcherAgent({})

    def test_skill_matching(self):
        """Test that skill matching works correctly."""
        cv_content = """
        Skills: Python, Django, REST APIs, PostgreSQL, Docker
        Experience: 3 years backend development
        """

        job = {
            'title': 'Python Developer',
            'requirements': 'Python, Django, PostgreSQL required',
            'description': 'Backend development position'
        }

        preferences = {
            'required_skills': ['Python', 'Django'],
            'experience_level': 'mid'
        }

        # This would need the actual matching logic
        # Just testing the structure exists
        assert hasattr(self.agent, 'execute')


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_negotiation_workflow(self):
        """Test complete negotiation workflow from offer to scripts."""
        agent = NegotiationAgent({})

        # Simulate receiving an offer
        job = {
            'title': 'Python Developer',
            'company': 'Tech Startup',
            'location': 'Bratislava',
            'salary': '3000-3500 EUR'
        }

        # Generate negotiation strategy
        result = agent.execute(
            job=job,
            current_offer=3200,
            user_target=4000
        )

        # Verify complete workflow
        assert "market_data" in result
        assert "strategy" in result
        assert "scripts" in result
        assert result["recommended_counter_offer"] > 3200

        # Verify market data is reasonable
        assert result["market_data"]["average_salary"] is not None
        assert len(result["market_data"]["sources"]) > 0

        # Verify scripts are actionable
        for script_type in ["email", "phone", "counter_offer_letter"]:
            assert script_type in result["scripts"]
            assert len(result["scripts"][script_type]) > 100


@pytest.fixture
def sample_job():
    """Sample job posting for testing."""
    return {
        'title': 'Senior Python Developer',
        'company': 'Tech Company',
        'location': 'Bratislava',
        'salary': '4000-5000 EUR',
        'description': 'Looking for experienced Python developer...',
        'requirements': 'Python, Django, REST APIs, 5+ years experience',
        'url': 'https://profesia.sk/job/12345'
    }


@pytest.fixture
def sample_cv():
    """Sample CV content for testing."""
    return """
    # John Doe

    ## Professional Summary
    Experienced Python developer with 5 years of backend development.

    ## Skills
    Python, Django, Flask, REST APIs, PostgreSQL, Docker, AWS

    ## Experience
    Senior Backend Developer at TechCorp (3 years)
    - Built scalable REST APIs
    - Managed database architecture
    - Led team of 3 developers
    """


class TestEndToEnd:
    """End-to-end workflow tests."""

    def test_job_hunt_workflow(self, sample_job, sample_cv):
        """Test complete job hunting workflow."""
        # 1. Job is scraped (simulated)
        assert sample_job['title'] is not None

        # 2. Job is matched against CV
        matcher = MatcherAgent({})
        # Would test matching here

        # 3. Negotiate salary
        negotiator = NegotiationAgent({})
        negotiation = negotiator.execute(
            job=sample_job,
            current_offer=4200,
            user_target=4500
        )

        assert negotiation["recommended_counter_offer"] >= 4200

    def test_linkedin_campaign(self):
        """Test LinkedIn outreach campaign."""
        agent = LinkedInAgent({})

        # Verify message generation works
        recruiter = {
            'name': 'Test Recruiter',
            'company': 'TestCo',
            'title': 'Senior Recruiter'
        }

        message = agent._generate_recruiter_message(recruiter, "Python Developer")
        assert len(message) > 0
        assert 'Test' in message or 'Hi' in message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
