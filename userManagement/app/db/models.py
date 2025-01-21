"""
models.py

Purpose: Define SQLAlchemy models for User, Device, and Subscription management.
These models represent the database schema and relationships.
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # One-to-one relationship with Device
    device = relationship("Device", back_populates="user", uselist=False)
    subscription = relationship("Subscription", back_populates="user", uselist=False)

class Device(Base):
    __tablename__ = "devices"
    
    uuid = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)  
    last_check_in = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="device")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    status = Column(String)  # e.g., 'active', 'cancelled'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="subscription")
