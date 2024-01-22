from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from bot.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String(255))
    tags = relationship("Tag", back_populates="user")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    tag = Column(String(30))
    text = Column(String(2000))
    user = relationship("User", back_populates="tags")
