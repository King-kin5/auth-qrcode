# model.py
from datetime import datetime
import uuid
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from backend.database.config import Base

class Student(Base):
    __tablename__ = "Student"
    
    id = Column(Integer, primary_key=True, index=True)
    Matric = Column(String, index=True)
    Firstname = Column(String)
    Lastname = Column(String)
    gender = Column(String)
    course = Column(String, index=True)
    level = Column(String)
    section = Column(String)
    image = Column(Text)  # Store base64 encoded image string
    qr_code = Column(String)  # Store the SVG string