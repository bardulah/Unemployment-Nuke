"""Database models and configuration."""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# Database URL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./hunt_commander.db')

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Models
class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    applications = relationship("Application", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")


class Application(Base):
    """Job application model."""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    job_title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=False)
    salary_range = Column(String)
    job_url = Column(String, nullable=False)

    status = Column(String, default="applied")  # applied, interviewing, offer, rejected, withdrawn
    applied_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    notes = Column(Text)
    tailored_cv_path = Column(String)
    match_score = Column(Float)

    # Relationships
    user = relationship("User", back_populates="applications")
    interview_preps = relationship("InterviewPrep", back_populates="application")


class InterviewPrep(Base):
    """Interview preparation model."""
    __tablename__ = "interview_preps"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    interview_date = Column(DateTime)
    interview_type = Column(String)  # phone, technical, cultural, final
    interviewer_name = Column(String)
    notes = Column(Text)
    outcome = Column(String)  # passed, failed, pending

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="interview_preps")


class Subscription(Base):
    """Subscription model for Stripe integration."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    stripe_subscription_id = Column(String, unique=True, nullable=False)
    stripe_customer_id = Column(String, nullable=False)

    status = Column(String, nullable=False)  # active, canceled, past_due
    current_period_end = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    canceled_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="subscriptions")


# Create tables
def init_db():
    """Initialize database."""
    Base.metadata.create_all(bind=engine)


# Dependency
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
