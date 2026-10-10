"""
Shared SQLAlchemy declarative base.
Import this in every service's model file to keep metadata unified.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
