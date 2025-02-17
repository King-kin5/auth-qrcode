from sqlalchemy import Column, Integer, String
from backend.database.config import Base
class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    course= Column(String, unique=True, index=True)
    level = Column(String)
    section = Column(String)
    qr_code = Column(String)  # Store the SVG string
