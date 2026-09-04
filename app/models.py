from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String, unique=True, index=True)
    full_name = Column(String)
    password_hash = Column(String, nullable=True)
    swachhata_user_id = Column(Integer, nullable=True)
    complaints = relationship("Complaint", back_populates="owner")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String, nullable=False)
    landmark = Column(String, nullable=True)
    image_url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    swachhata_complaint_id = Column(String, nullable=True)
    status = Column(String, default="Pending Sync")
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="complaints")
