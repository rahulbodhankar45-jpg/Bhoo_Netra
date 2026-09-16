"""
Planning, Zoning, Master Plan, and Building Permission models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from app.core.database import Base, TimestampMixin


class LandUse(Base, TimestampMixin):
    __tablename__ = "land_use"

    id = Column(Integer, primary_key=True, index=True)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), unique=True, index=True, nullable=False)
    zone = Column(String(50), nullable=False)  # Residential, Commercial, Mixed, Agricultural, Industrial, Forest
    permitted_use = Column(String(255), nullable=False)  # "Residential villas & low-rise apartments"
    fsi_allowed = Column(Float, default=1.5)  # Floor Space Index
    development_restrictions = Column(String(255), default="NONE")  # Coastal Regulation Zone, Height Limit 15m, None


class MasterPlan(Base):
    __tablename__ = "master_plans"

    plan_id = Column(String(50), primary_key=True, index=True)
    jurisdiction = Column(String(100), nullable=False)  # e.g., 'CMDA Chennai', 'PMRDA Pune'
    master_plan_year = Column(Integer, default=2026)
    zoning_code = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)


class BuildingPermission(Base, TimestampMixin):
    __tablename__ = "building_permissions"

    permission_id = Column(String(50), primary_key=True, index=True)
    application_no = Column(String(50), unique=True, nullable=False)
    ulpin = Column(String(32), ForeignKey("parcels.ulpin"), index=True, nullable=False)
    status = Column(String(20), default="APPROVED")  # APPROVED, PENDING, REJECTED
    approved_floors = Column(Integer, default=2)
    sanctioned_area = Column(Float, nullable=False)
    approval_date = Column(DateTime, default=datetime.utcnow)
