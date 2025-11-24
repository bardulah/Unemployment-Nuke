"""Agents package for Hunt Commander multi-agent system."""
from .base_agent import BaseAgent
from .scraper_agent import ScraperAgent
from .matcher_agent import MatcherAgent
from .critique_agent import CritiqueAgent
from .cv_tailor_agent import CVTailorAgent
from .notification_agent import NotificationAgent
from .negotiation_agent import NegotiationAgent
from .linkedin_agent import LinkedInAgent
from .cover_letter_agent import CoverLetterAgent
from .auto_submit_agent import AutoSubmitAgent
from .email_parser_agent import EmailParserAgent

__all__ = [
    'BaseAgent',
    'ScraperAgent',
    'MatcherAgent',
    'CritiqueAgent',
    'CVTailorAgent',
    'NotificationAgent',
    'NegotiationAgent',
    'LinkedInAgent',
    'CoverLetterAgent',
    'AutoSubmitAgent',
    'EmailParserAgent'
]
