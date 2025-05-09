from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=True, autoincrement=True)
    username = Column(String, nullable=True)
    useremail = Column(String(100), nullable=True)
    password = Column(String(50), nullable=True)
    bio = Column(Text)
