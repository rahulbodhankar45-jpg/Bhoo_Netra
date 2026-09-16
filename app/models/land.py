"""
Land, Parcel, ULPIN Registry, and Cadastral Boundary models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from app.core.database import Base, TimestampMixin


class ULPINRegistry(Base):
    __tablename__ = "ulpin_registry"

    id = Column(Integer, primary_key=True, index=True)
    ulpin = Column(String(32), unique=True, index=True, nullable=False)
    state_code = Column(String(10), nullable=False, index=True)
    district_code = Column(String(10), nullable=False)
    subdistrict_code = Column(String(10), nullable=True)
    village_code = Column(String(20), nullable=True)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, SPLIT, MERGED, ARCHIVED
    generated_at = Column(DateTime, default=datetime.utcnow)


class Parcel(Base, TimestampMixin):
    __tablename__ = "parcels"

    ulpin = Column(String(32), primary_key=True, index=True)
    survey_number = Column(String(50), nullable=False, index=True)
    subdivision_number = Column(String(50), nullable=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    taluk = Column(String(100), nullable=False, index=True)
    village = Column(String(100), nullable=False, index=True)
    area = Column(Float, nullable=False)
    area_unit = Column(String(20), default="sq.m", nullable=False)
    land_type = Column(String(50), default="Residential", nullable=False)  # Residential, Commercial, Agricultural, etc.
    
    # Spatial attributes (GeoJSON geometry: Polygon coordinates)
    geometry_type = Column(String(20), default="Polygon")
    coordinates = Column(JSON, nullable=False)  # [[[lng, lat], ...]]
    centroid_lat = Column(Float, nullable=True)
    centroid_lng = Column(Float, nullable=True)


class ParcelBoundary(Base):
    __tablename__ = "parcel_boundaries"

    id = Column(Integer, primary_key=True, index=True)
    ulpin = Column(String(32), index=True, nullable=False)
    boundary_points = Column(JSON, nullable=False)
    crs = Column(String(20), default="EPSG:4326")
    last_survey_date = Column(DateTime, nullable=True)


class ParcelHistory(Base):
    __tablename__ = "parcel_history"

    id = Column(Integer, primary_key=True, index=True)
    ulpin = Column(String(32), index=True, nullable=False)
    change_type = Column(String(50), nullable=False)  # MUTATION, SUBDIVISION, MERGER, SURVEY_UPDATE
    snapshot_json = Column(JSON, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)
