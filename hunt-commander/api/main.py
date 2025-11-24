"""Hunt Commander API - FastAPI backend for job hunting dashboard."""
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import stripe
from sqlalchemy.orm import Session

from api.database import get_db, Application, User, InterviewPrep, Subscription
from api.auth import create_access_token, decode_token
from agents import (
    ScraperAgent,
    MatcherAgent,
    CVTailorAgent,
    NegotiationAgent,
    LinkedInAgent
)

# Initialize FastAPI
app = FastAPI(
    title="Hunt Commander API",
    description="AI-powered job hunting platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')  # €19/month price ID

# Security
security = HTTPBearer()


# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ApplicationCreate(BaseModel):
    job_title: str
    company: str
    location: str
    salary_range: Optional[str] = None
    job_url: str
    status: str = "applied"
    notes: Optional[str] = None


class NegotiationRequest(BaseModel):
    application_id: int
    current_offer: Optional[float] = None
    target_salary: Optional[float] = None


class LinkedInDMRequest(BaseModel):
    search_query: str
    location: str = "Bratislava"
    max_messages: int = 10


class SubscriptionCreate(BaseModel):
    payment_method_id: str


# Auth dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current authenticated user."""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


# Subscription check
async def check_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has active subscription."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status == "active",
        Subscription.current_period_end > datetime.utcnow()
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required. Subscribe for €19/month for unlimited access."
        )

    return subscription


# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Hunt Commander API",
        "version": "1.0.0",
        "status": "operational",
        "message": "Land that €4k/month Python gig in Bratislava 🎯"
    }


@app.post("/auth/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user."""
    # Check if user exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    new_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=user.password  # Hash in production
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create token
    token = create_access_token({"sub": new_user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name
        }
    }


@app.post("/auth/login")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user."""
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or user.hashed_password != credentials.password:  # Use proper hash check
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    token = create_access_token({"sub": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }


@app.get("/applications")
async def get_applications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = None
):
    """Get user's job applications."""
    query = db.query(Application).filter(Application.user_id == user.id)

    if status_filter:
        query = query.filter(Application.status == status_filter)

    applications = query.order_by(Application.applied_at.desc()).all()

    return {
        "total": len(applications),
        "applications": applications
    }


@app.post("/applications")
async def create_application(
    app_data: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new job application."""
    application = Application(
        user_id=user.id,
        **app_data.dict()
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return application


@app.get("/applications/stats")
async def get_application_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get application statistics."""
    applications = db.query(Application).filter(Application.user_id == user.id).all()

    stats = {
        "total_applications": len(applications),
        "pending": sum(1 for a in applications if a.status == "applied"),
        "interviewing": sum(1 for a in applications if a.status == "interviewing"),
        "offers": sum(1 for a in applications if a.status == "offer"),
        "rejected": sum(1 for a in applications if a.status == "rejected"),
        "acceptance_rate": 0,
        "average_response_time": None,
        "applications_this_week": 0
    }

    # Calculate acceptance rate
    if stats["total_applications"] > 0:
        stats["acceptance_rate"] = (stats["interviewing"] + stats["offers"]) / stats["total_applications"] * 100

    # Applications this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    stats["applications_this_week"] = sum(
        1 for a in applications if a.applied_at >= week_ago
    )

    return stats


@app.post("/negotiate")
async def negotiate_salary(
    request: NegotiationRequest,
    user: User = Depends(get_current_user),
    subscription: Subscription = Depends(check_subscription),
    db: Session = Depends(get_db)
):
    """Generate salary negotiation strategy."""
    # Get application
    application = db.query(Application).filter(
        Application.id == request.application_id,
        Application.user_id == user.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Generate negotiation strategy
    agent = NegotiationAgent({})
    job = {
        'title': application.job_title,
        'company': application.company,
        'location': application.location,
        'salary': application.salary_range
    }

    strategy = agent.execute(
        job=job,
        current_offer=request.current_offer,
        user_target=request.target_salary
    )

    return strategy


@app.post("/linkedin/dm-recruiters")
async def dm_recruiters(
    request: LinkedInDMRequest,
    user: User = Depends(get_current_user),
    subscription: Subscription = Depends(check_subscription),
    background_tasks: BackgroundTasks = None
):
    """Send DMs to recruiters on LinkedIn."""
    # Initialize LinkedIn agent
    agent = LinkedInAgent({})

    try:
        results = agent.execute(
            action="dm_recruiters",
            search_query=request.search_query,
            location=request.location,
            max_messages=request.max_messages
        )

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        agent.close()


@app.get("/interview-prep/{application_id}")
async def get_interview_prep(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview preparation for application."""
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == user.id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Generate interview prep
    prep = {
        "company": application.company,
        "role": application.job_title,
        "common_questions": [
            "Tell me about yourself and your experience with Python",
            "What's your experience with Django/Flask?",
            "Describe a challenging project you worked on",
            "How do you handle tight deadlines?",
            "What's your experience with REST APIs?",
            "How do you approach debugging complex issues?",
            "What's your testing methodology?",
            "Where do you see yourself in 5 years?"
        ],
        "technical_questions": [
            "Explain the difference between list and tuple in Python",
            "What are decorators in Python?",
            "How does garbage collection work in Python?",
            "Explain async/await in Python",
            "What's the difference between SQL and NoSQL?",
            "How would you optimize a slow database query?",
            "Explain RESTful API design principles"
        ],
        "questions_to_ask": [
            "What does a typical day look like for this role?",
            "What are the biggest challenges facing the team?",
            "How do you measure success in this position?",
            "What's the team structure and who would I work with?",
            "What technologies does the team use?",
            "What's the deployment process?",
            "What are the growth opportunities?"
        ],
        "company_research": {
            "industry": "Technology",
            "key_points": [
                "Research company's tech stack",
                "Review recent news and product launches",
                "Check employee reviews on Glassdoor",
                "Understand their business model"
            ]
        }
    }

    return prep


@app.get("/rejection-analysis")
async def analyze_rejections(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze rejection patterns and provide insights."""
    rejections = db.query(Application).filter(
        Application.user_id == user.id,
        Application.status == "rejected"
    ).all()

    if not rejections:
        return {
            "total_rejections": 0,
            "insights": ["No rejections yet - keep applying!"]
        }

    # Analyze patterns
    analysis = {
        "total_rejections": len(rejections),
        "rejection_rate": 0,
        "common_rejection_stages": {},
        "insights": [],
        "recommendations": []
    }

    # Calculate rejection rate
    total_apps = db.query(Application).filter(Application.user_id == user.id).count()
    if total_apps > 0:
        analysis["rejection_rate"] = (len(rejections) / total_apps) * 100

    # Analyze rejection reasons (if available)
    rejection_notes = [r.notes for r in rejections if r.notes]

    # Generate insights
    if analysis["rejection_rate"] > 50:
        analysis["insights"].append("High rejection rate detected. Consider:")
        analysis["recommendations"].extend([
            "Tailor your CV more specifically to each role",
            "Focus on roles that match your experience level",
            "Improve your cover letter personalization",
            "Consider adding more relevant skills to your CV"
        ])

    if len(rejections) > 10:
        analysis["insights"].append("Multiple rejections - persistence is key!")
        analysis["recommendations"].append("Review and update your application strategy")

    # Company/role analysis
    rejected_companies = [r.company for r in rejections]
    rejected_roles = [r.job_title for r in rejections]

    analysis["most_rejected_companies"] = list(set(rejected_companies))[:5]
    analysis["most_rejected_roles"] = list(set(rejected_roles))[:5]

    return analysis


@app.post("/subscribe")
async def create_subscription(
    subscription_data: SubscriptionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe subscription."""
    try:
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            payment_method=subscription_data.payment_method_id,
            invoice_settings={"default_payment_method": subscription_data.payment_method_id}
        )

        # Create subscription
        stripe_subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": STRIPE_PRICE_ID}],
            expand=["latest_invoice.payment_intent"]
        )

        # Save to database
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=stripe_subscription.id,
            stripe_customer_id=customer.id,
            status="active",
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end)
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        return {
            "subscription_id": subscription.id,
            "status": "active",
            "message": "Welcome to Hunt Commander Premium! 🎯"
        }

    except stripe.error.CardError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/subscription/status")
async def get_subscription_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's subscription status."""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id
    ).order_by(Subscription.created_at.desc()).first()

    if not subscription:
        return {
            "status": "inactive",
            "message": "No active subscription. Subscribe for €19/month for unlimited access!"
        }

    return {
        "status": subscription.status,
        "current_period_end": subscription.current_period_end,
        "stripe_subscription_id": subscription.stripe_subscription_id
    }


@app.post("/jobs/scrape")
async def scrape_jobs(
    keywords: List[str],
    locations: List[str],
    user: User = Depends(get_current_user),
    subscription: Subscription = Depends(check_subscription)
):
    """Scrape jobs from profesia.sk."""
    agent = ScraperAgent({})
    jobs = agent.execute(keywords, locations)

    return {
        "jobs_found": len(jobs),
        "jobs": jobs[:20]  # Return first 20
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
