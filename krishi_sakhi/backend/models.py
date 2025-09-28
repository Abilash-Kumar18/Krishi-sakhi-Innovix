from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Farmer(Base):
 __tablename__ = 'farmers'
 id = Column(Integer, primary_key=True)
 username = Column(String(50), unique=True, nullable=False)
 name = Column(String(100), nullable=False)
 age = Column(Integer)
 gender = Column(String(10))
 phone = Column(String(15))
 fcm_token = Column(String(500))  # For FCM push notifications
 location_ml = Column(String(100))
 location_en = Column(String(100))
 lat = Column(Float)
 lon = Column(Float)
 crop = Column(String(100))
 soil = Column(String(100))
 field_type = Column(String(100))
 farm_size = Column(Float)
 irrigation_type = Column(String(50))
 experience = Column(Integer)
 pests_history = Column(Text)
 yield_goals = Column(Text)
 created_at = Column(DateTime, default=datetime.utcnow)
 queries = relationship("Query", backref="farmer")

class Query(Base):
 __tablename__ = 'queries'
 id = Column(Integer, primary_key=True)
 farmer_id = Column(Integer, ForeignKey('farmers.id'))
 user_input = Column(Text)
 ai_response = Column(Text)
 timestamp = Column(DateTime, default=datetime.utcnow)

