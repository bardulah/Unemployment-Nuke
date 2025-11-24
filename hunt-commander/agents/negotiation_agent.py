"""Negotiation Agent - Salary negotiation and counter-offer generation."""
import os
import json
import re
import requests
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from agents.base_agent import BaseAgent
from utils import log


class NegotiationAgent(BaseAgent):
    """Agent for salary negotiation and counter-offer generation."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize negotiation agent.

        Args:
            config: Configuration dictionary
        """
        super().__init__("NegotiationAgent", config)
        self.glassdoor_cache = {}

    def execute(
        self,
        job: Dict[str, Any],
        current_offer: Optional[float] = None,
        user_target: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate negotiation strategy and counter-offer.

        Args:
            job: Job details
            current_offer: Current salary offer in EUR
            user_target: User's target salary in EUR

        Returns:
            Negotiation strategy with counter-offer details
        """
        log.info(f"Generating negotiation strategy for {job.get('title', 'Unknown')}")

        # Get market data for the role
        market_data = self._get_market_data_slovakia(job)

        # Analyze the offer
        analysis = self._analyze_offer(job, current_offer, market_data, user_target)

        # Generate counter-offer strategy
        strategy = self._generate_counter_offer_strategy(
            job, current_offer, market_data, analysis, user_target
        )

        # Create negotiation scripts
        scripts = self._generate_negotiation_scripts(strategy, job)

        return {
            "market_data": market_data,
            "analysis": analysis,
            "strategy": strategy,
            "scripts": scripts,
            "recommended_counter_offer": strategy.get("counter_offer"),
            "negotiation_leverage_points": strategy.get("leverage_points", [])
        }

    def _get_market_data_slovakia(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Scrape and analyze salary data for Slovakia market.

        Args:
            job: Job details

        Returns:
            Market salary data
        """
        job_title = job.get('title', '')
        location = job.get('location', 'Bratislava')

        # Try multiple sources
        market_data = {
            "average_salary": None,
            "min_salary": None,
            "max_salary": None,
            "percentile_25": None,
            "percentile_50": None,
            "percentile_75": None,
            "data_points": 0,
            "sources": []
        }

        # Source 1: Glassdoor Slovakia data (simulated - in production use real API)
        glassdoor_data = self._scrape_glassdoor_slovakia(job_title, location)
        if glassdoor_data:
            market_data.update(glassdoor_data)
            market_data["sources"].append("Glassdoor SK")

        # Source 2: Profesia.sk salary data
        profesia_data = self._scrape_profesia_salaries(job_title, location)
        if profesia_data:
            # Merge data
            if market_data["average_salary"]:
                market_data["average_salary"] = (
                    market_data["average_salary"] + profesia_data["average_salary"]
                ) / 2
            else:
                market_data["average_salary"] = profesia_data["average_salary"]
            market_data["sources"].append("Profesia SK")

        # Source 3: Platy.sk data
        platy_data = self._scrape_platy_sk(job_title)
        if platy_data:
            if market_data["average_salary"]:
                market_data["average_salary"] = (
                    market_data["average_salary"] + platy_data["average_salary"]
                ) / 2
            else:
                market_data["average_salary"] = platy_data["average_salary"]
            market_data["sources"].append("Platy.sk")

        # Fallback: Use job posting salary range if available
        if not market_data["average_salary"]:
            salary_range = self._extract_salary_from_job(job)
            if salary_range:
                market_data.update(salary_range)
                market_data["sources"].append("Job Posting")

        # Apply Slovakia market adjustments
        market_data = self._apply_slovakia_market_factors(market_data, location)

        return market_data

    def _scrape_glassdoor_slovakia(
        self,
        job_title: str,
        location: str
    ) -> Optional[Dict[str, Any]]:
        """Scrape Glassdoor for Slovakia salary data.

        Note: This is a simplified version. Real implementation would use
        Glassdoor API or proper web scraping with headers/sessions.

        Args:
            job_title: Job title to search
            location: Location in Slovakia

        Returns:
            Salary data or None
        """
        # Glassdoor Slovakia salary estimates (sample data for common roles)
        # In production, this would scrape glassdoor.com/Salaries or use their API

        salary_database = {
            "python developer": {
                "bratislava": {"avg": 3200, "min": 2400, "max": 4800, "p25": 2800, "p50": 3200, "p75": 3800},
                "kosice": {"avg": 2600, "min": 2000, "max": 3800, "p25": 2300, "p50": 2600, "p75": 3100},
                "remote": {"avg": 3500, "min": 2600, "max": 5200, "p25": 3000, "p50": 3500, "p75": 4200}
            },
            "backend developer": {
                "bratislava": {"avg": 3400, "min": 2600, "max": 5000, "p25": 2900, "p50": 3400, "p75": 4000},
                "kosice": {"avg": 2800, "min": 2200, "max": 4000, "p25": 2500, "p50": 2800, "p75": 3300},
                "remote": {"avg": 3700, "min": 2800, "max": 5400, "p25": 3200, "p50": 3700, "p75": 4400}
            },
            "fullstack developer": {
                "bratislava": {"avg": 3300, "min": 2500, "max": 4900, "p25": 2850, "p50": 3300, "p75": 3900},
                "remote": {"avg": 3600, "min": 2700, "max": 5300, "p25": 3100, "p50": 3600, "p75": 4300}
            },
            "senior python developer": {
                "bratislava": {"avg": 4200, "min": 3400, "max": 6000, "p25": 3700, "p50": 4200, "p75": 5000},
                "remote": {"avg": 4800, "min": 3800, "max": 6800, "p25": 4200, "p50": 4800, "p75": 5600}
            },
            "devops engineer": {
                "bratislava": {"avg": 3800, "min": 3000, "max": 5500, "p25": 3300, "p50": 3800, "p75": 4500},
                "remote": {"avg": 4200, "min": 3300, "max": 6000, "p25": 3700, "p50": 4200, "p75": 5000}
            }
        }

        # Normalize job title and location
        title_key = job_title.lower().strip()
        location_key = location.lower().strip()

        # Find best match
        for key in salary_database.keys():
            if key in title_key or title_key in key:
                if location_key in salary_database[key]:
                    data = salary_database[key][location_key]
                    return {
                        "average_salary": data["avg"],
                        "min_salary": data["min"],
                        "max_salary": data["max"],
                        "percentile_25": data["p25"],
                        "percentile_50": data["p50"],
                        "percentile_75": data["p75"],
                        "data_points": 100
                    }

        return None

    def _scrape_profesia_salaries(
        self,
        job_title: str,
        location: str
    ) -> Optional[Dict[str, Any]]:
        """Scrape salary data from Profesia.sk.

        Args:
            job_title: Job title
            location: Location

        Returns:
            Salary data or None
        """
        # Simplified profesia.sk salary data
        # In production, scrape from profesia.sk/mzdy

        base_salaries = {
            "python": 3100,
            "backend": 3300,
            "fullstack": 3200,
            "frontend": 2900,
            "devops": 3700,
            "senior": 4500
        }

        title_lower = job_title.lower()
        estimated_salary = 2800  # Base salary

        for keyword, salary in base_salaries.items():
            if keyword in title_lower:
                estimated_salary = max(estimated_salary, salary)

        return {
            "average_salary": estimated_salary,
            "data_points": 50
        }

    def _scrape_platy_sk(self, job_title: str) -> Optional[Dict[str, Any]]:
        """Scrape salary data from Platy.sk.

        Args:
            job_title: Job title

        Returns:
            Salary data or None
        """
        # Simplified platy.sk data
        # In production, scrape from platy.sk

        if "python" in job_title.lower():
            return {"average_salary": 3000, "data_points": 30}
        elif "senior" in job_title.lower():
            return {"average_salary": 4300, "data_points": 25}

        return None

    def _extract_salary_from_job(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract salary information from job posting.

        Args:
            job: Job details

        Returns:
            Salary data or None
        """
        salary_text = job.get('salary', '')
        if not salary_text:
            return None

        # Extract numbers from salary text
        numbers = re.findall(r'\d+', salary_text)
        if len(numbers) >= 2:
            min_sal = int(numbers[0])
            max_sal = int(numbers[1])
            avg_sal = (min_sal + max_sal) / 2

            return {
                "min_salary": min_sal,
                "max_salary": max_sal,
                "average_salary": avg_sal,
                "percentile_50": avg_sal
            }

        return None

    def _apply_slovakia_market_factors(
        self,
        market_data: Dict[str, Any],
        location: str
    ) -> Dict[str, Any]:
        """Apply Slovakia-specific market adjustments.

        Args:
            market_data: Raw market data
            location: Location in Slovakia

        Returns:
            Adjusted market data
        """
        # Location multipliers for Slovakia
        location_multipliers = {
            "bratislava": 1.0,
            "košice": 0.85,
            "žilina": 0.80,
            "banská bystrica": 0.78,
            "prešov": 0.80,
            "nitra": 0.82,
            "remote": 1.1,  # Remote positions often pay more
            "eu remote": 1.3
        }

        location_lower = location.lower()
        multiplier = 1.0

        for loc, mult in location_multipliers.items():
            if loc in location_lower:
                multiplier = mult
                break

        # Apply multiplier
        if market_data.get("average_salary"):
            market_data["average_salary"] = int(market_data["average_salary"] * multiplier)
        if market_data.get("min_salary"):
            market_data["min_salary"] = int(market_data["min_salary"] * multiplier)
        if market_data.get("max_salary"):
            market_data["max_salary"] = int(market_data["max_salary"] * multiplier)

        return market_data

    def _analyze_offer(
        self,
        job: Dict[str, Any],
        current_offer: Optional[float],
        market_data: Dict[str, Any],
        user_target: Optional[float]
    ) -> Dict[str, Any]:
        """Analyze current offer vs market.

        Args:
            job: Job details
            current_offer: Current offer in EUR
            market_data: Market salary data
            user_target: User's target salary

        Returns:
            Offer analysis
        """
        analysis = {
            "offer_vs_market": "unknown",
            "percentile": None,
            "gap_to_target": None,
            "negotiation_room": "medium",
            "market_position": "fair"
        }

        if not current_offer or not market_data.get("average_salary"):
            return analysis

        avg_salary = market_data["average_salary"]

        # Calculate percentile
        if market_data.get("percentile_25") and market_data.get("percentile_75"):
            p25 = market_data["percentile_25"]
            p75 = market_data["percentile_75"]

            if current_offer < p25:
                analysis["percentile"] = "<25th"
                analysis["offer_vs_market"] = "below_market"
                analysis["negotiation_room"] = "high"
            elif current_offer < market_data["percentile_50"]:
                analysis["percentile"] = "25-50th"
                analysis["offer_vs_market"] = "fair"
                analysis["negotiation_room"] = "medium"
            elif current_offer < p75:
                analysis["percentile"] = "50-75th"
                analysis["offer_vs_market"] = "good"
                analysis["negotiation_room"] = "medium"
            else:
                analysis["percentile"] = ">75th"
                analysis["offer_vs_market"] = "excellent"
                analysis["negotiation_room"] = "low"

        # Calculate gap to target
        if user_target:
            gap = user_target - current_offer
            gap_percent = (gap / current_offer) * 100
            analysis["gap_to_target"] = {
                "amount": gap,
                "percent": gap_percent
            }

        # Market position
        diff_percent = ((current_offer - avg_salary) / avg_salary) * 100
        if diff_percent < -10:
            analysis["market_position"] = "below_market"
        elif diff_percent < 5:
            analysis["market_position"] = "fair"
        elif diff_percent < 15:
            analysis["market_position"] = "good"
        else:
            analysis["market_position"] = "excellent"

        return analysis

    def _generate_counter_offer_strategy(
        self,
        job: Dict[str, Any],
        current_offer: Optional[float],
        market_data: Dict[str, Any],
        analysis: Dict[str, Any],
        user_target: Optional[float]
    ) -> Dict[str, Any]:
        """Generate counter-offer strategy.

        Args:
            job: Job details
            current_offer: Current offer
            market_data: Market data
            analysis: Offer analysis
            user_target: Target salary

        Returns:
            Counter-offer strategy
        """
        strategy = {
            "should_negotiate": True,
            "counter_offer": None,
            "min_acceptable": None,
            "ideal_outcome": None,
            "leverage_points": [],
            "risks": [],
            "alternative_benefits": []
        }

        if not current_offer:
            # No offer yet - provide guidance
            if market_data.get("percentile_75"):
                strategy["counter_offer"] = market_data["percentile_75"]
                strategy["min_acceptable"] = market_data.get("percentile_50")
                strategy["ideal_outcome"] = market_data.get("max_salary")
            else:
                strategy["counter_offer"] = user_target or 4000
                strategy["min_acceptable"] = 3500

            strategy["leverage_points"] = [
                "Market data shows role commands €{:,}".format(int(strategy["counter_offer"])),
                "Your skills in Python, Django, REST APIs are in high demand",
                "Remote work capabilities add value"
            ]
            return strategy

        # Calculate counter-offer
        if analysis["offer_vs_market"] in ["below_market", "fair"]:
            # Aim for 75th percentile
            if market_data.get("percentile_75"):
                strategy["counter_offer"] = market_data["percentile_75"]
            else:
                strategy["counter_offer"] = current_offer * 1.15

            strategy["should_negotiate"] = True
            strategy["leverage_points"].append(
                f"Current offer is below market average by {int(market_data['average_salary'] - current_offer):,} EUR"
            )

        elif analysis["offer_vs_market"] == "good":
            # Try for modest increase
            strategy["counter_offer"] = current_offer * 1.08
            strategy["should_negotiate"] = True
            strategy["leverage_points"].append(
                "Requesting slight adjustment to align with top market performers"
            )

        else:
            # Offer is excellent - focus on benefits
            strategy["should_negotiate"] = False
            strategy["counter_offer"] = current_offer
            strategy["alternative_benefits"] = [
                "Additional vacation days",
                "Remote work flexibility",
                "Professional development budget",
                "Sign-on bonus",
                "Stock options or equity"
            ]

        # Set boundaries
        strategy["min_acceptable"] = current_offer * 1.05
        strategy["ideal_outcome"] = user_target or strategy["counter_offer"]

        # Add leverage points
        strategy["leverage_points"].extend([
            f"Market data from {', '.join(market_data.get('sources', []))}",
            f"Average salary for this role: €{market_data.get('average_salary', 0):,}",
            "Proven track record in similar positions",
            "Immediate availability and no notice period"
        ])

        # Identify risks
        if analysis["negotiation_room"] == "low":
            strategy["risks"].append("Offer already at top of market range")

        if job.get('company_size') == 'startup':
            strategy["risks"].append("Startup may have limited salary flexibility")
            strategy["alternative_benefits"].append("Equity compensation")

        return strategy

    def _generate_negotiation_scripts(
        self,
        strategy: Dict[str, Any],
        job: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate negotiation conversation scripts.

        Args:
            strategy: Negotiation strategy
            job: Job details

        Returns:
            Dictionary of negotiation scripts
        """
        counter_offer = strategy.get("counter_offer", 0)

        scripts = {}

        # Email script
        scripts["email"] = f"""Subject: Re: Job Offer - {job.get('title')}

Dear Hiring Manager,

Thank you for the offer for the {job.get('title')} position. I'm very excited about the opportunity to join your team and contribute to {job.get('company', 'the company')}.

After careful consideration and based on my research of the current market for this role in Slovakia, I would like to discuss the compensation package. Based on my experience and the value I can bring to the team, I was hoping we could meet at €{counter_offer:,.0f} per month.

This figure reflects:
- Market data from multiple Slovak salary sources
- My {len(strategy.get('leverage_points', []))} years of relevant experience
- The specialized skills I bring in {job.get('requirements', 'Python development')}

I'm confident that I can deliver significant value to your team from day one. I'm happy to discuss this further and find a mutually beneficial arrangement.

Looking forward to your response.

Best regards"""

        # Phone script
        scripts["phone"] = f"""
OPENING:
"Thank you so much for the offer. I'm really excited about this opportunity and I can see myself thriving in this role."

TRANSITION TO NEGOTIATION:
"I've done some market research, and I was wondering if there's any flexibility in the compensation package?"

YOUR ASK:
"Based on the market data I've gathered from Glassdoor, Profesia, and Platy.sk, similar roles in Bratislava are ranging from €{strategy.get('min_acceptable', counter_offer):,.0f} to €{counter_offer:,.0f}. Would it be possible to meet at €{counter_offer:,.0f}?"

JUSTIFICATION:
{chr(10).join('- ' + point for point in strategy.get('leverage_points', [])[:3])}

IF THEY PUSH BACK:
"I completely understand. Would you be open to exploring alternative benefits such as {', '.join(strategy.get('alternative_benefits', ['flexible work arrangements', 'professional development budget'])[:2])}?"

CLOSING:
"I'm really excited to join the team. What do you think about this proposal?"
"""

        # Counter-offer letter
        scripts["counter_offer_letter"] = f"""Dear [Hiring Manager],

I want to express my enthusiasm for the {job.get('title')} position at {job.get('company', 'your company')}. After our discussions, I'm confident this role aligns perfectly with my career goals.

Regarding the compensation package, I'd like to propose €{counter_offer:,.0f} monthly gross salary. This figure is based on:

1. Market Research: Data from Glassdoor Slovakia, Profesia.sk, and Platy.sk shows the market rate for this position in Bratislava ranges from €{strategy.get('min_acceptable', 3000):,.0f} to €{strategy.get('ideal_outcome', 5000):,.0f}.

2. My Value Proposition:
{chr(10).join('   - ' + point for point in strategy.get('leverage_points', [])[:4])}

I'm flexible and open to discussing the total compensation package, including:
{chr(10).join('   - ' + benefit for benefit in strategy.get('alternative_benefits', [])[:3])}

I'm excited to contribute to your team's success and look forward to reaching an agreement that works for both of us.

Best regards"""

        return scripts

    def simulate_negotiation(
        self,
        initial_offer: float,
        your_counter: float,
        employer_max: float
    ) -> List[Dict[str, Any]]:
        """Simulate negotiation rounds.

        Args:
            initial_offer: Employer's initial offer
            your_counter: Your counter-offer
            employer_max: Employer's maximum they can offer

        Returns:
            List of negotiation rounds with likely outcomes
        """
        rounds = []

        # Round 1
        rounds.append({
            "round": 1,
            "employer_offer": initial_offer,
            "your_response": "counter",
            "your_counter": your_counter,
            "analysis": "Initial counter-offer submitted"
        })

        # Round 2 - Employer response
        if your_counter <= employer_max:
            # They can afford it
            if your_counter - initial_offer > employer_max * 0.15:
                # Big jump - they'll counter
                employer_counter = (initial_offer + your_counter) / 2
                rounds.append({
                    "round": 2,
                    "employer_offer": employer_counter,
                    "your_response": "evaluate",
                    "analysis": f"Employer countered at middle ground: €{employer_counter:,.0f}"
                })
            else:
                # Reasonable ask - likely to accept
                rounds.append({
                    "round": 2,
                    "employer_offer": your_counter,
                    "your_response": "accept",
                    "analysis": "Employer accepted your counter-offer"
                })
        else:
            # Too high - they'll counter at their max
            rounds.append({
                "round": 2,
                "employer_offer": employer_max,
                "your_response": "evaluate",
                "analysis": f"Employer countered at their maximum: €{employer_max:,.0f}"
            })

        return rounds
