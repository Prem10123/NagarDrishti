# File: app/models.py

from sqlalchemy import Boolean, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    # Internal ID for our app
    id = Column(Integer, primary_key=True, index=True)
    
    # [cite_start]Required by Swachhata API for Registration [cite: 91]
    mobile_number = Column(String, unique=True, index=True) 
    full_name = Column(String)
    
    # [cite_start]We save this after registering the user with the Govt API [cite: 102]
    swachhata_user_id = Column(Integer, nullable=True)
    
    # Relationship to complaints
    complaints = relationship("Complaint", back_populates="owner")

class Complaint(Base):
    __tablename__ = "complaints"

    # Internal ID
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to the User who reported this
    user_id = Column(Integer, ForeignKey("users.id"))

    # [cite_start]--- Fields Required by Swachhata API [cite: 7, 8] ---
    # [cite_start]1. Category ID (e.g., 1=Dead Animal, 2=Dustbin) [cite: 10-28]
    category_id = Column(Integer, nullable=False)
    
    # [cite_start]2. Location Data [cite: 8]
    latitude = Column(Float, nullable=False)   # complaintLatitude
    longitude = Column(Float, nullable=False)  # complaintLongitude
    address = Column(String, nullable=False)   # complaintLocation
    landmark = Column(String, nullable=True)   # complaintLandmark
    
    # 3. Evidence
    # [cite_start]The API expects a String URL, not a binary file [cite: 9]
    image_url = Column(String, nullable=False) 
    
    # 4. Description (Optional in API, but good for us)
    description = Column(String, nullable=True)

    # --- Sync Tracking ---
    # [cite_start]The 'generic_id' returned by the API upon success [cite: 41]
    swachhata_complaint_id = Column(String, nullable=True)
    
    # Status: 'Pending Sync', 'Synced', 'Failed', 'Resolved'
    status = Column(String, default="Pending Sync") 
    
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="complaints")