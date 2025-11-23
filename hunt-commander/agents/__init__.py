"""Agents package for Hunt Commander multi-agent system."""
from .base_agent import BaseAgent
from .scraper_agent import ScraperAgent
from .matcher_agent import MatcherAgent
from .critique_agent import CritiqueAgent
from .cv_tailor_agent import CVTailorAgent
from .notification_agent import NotificationAgent
from .negotiation_agent import NegotiationAgent
from .linkedin_agent import LinkedInAgent

__all__ = [
    'BaseAgent',
    'ScraperAgent',
    'MatcherAgent',
    'CritiqueAgent',
    'CVTailorAgent',
    'NotificationAgent',
    'NegotiationAgent',
    'LinkedInAgent'
]
