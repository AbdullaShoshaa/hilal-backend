"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class RefractionSettings(BaseModel):
    """Atmospheric refraction parameters."""
    temperature_c: float = Field(default=10.0, description="Temperature in Celsius")
    pressure_mb: float = Field(default=1010.0, description="Pressure in millibars")
    humidity_pct: float = Field(default=60.0, description="Humidity percentage")
    temp_lapse_rate: float = Field(default=0.0065, description="Temperature lapse rate K/m")


class CrescentRequest(BaseModel):
    """Request body for crescent visibility calculation."""
    latitude: float = Field(..., ge=-90, le=90, description="Observer latitude (degrees, positive North)")
    longitude: float = Field(..., ge=-180, le=180, description="Observer longitude (degrees, positive East)")
    elevation: float = Field(default=0.0, ge=0, description="Observer elevation in meters above sea level")
    timezone_offset: float = Field(..., description="Hours offset from UTC (e.g., 3.0 for UTC+3)")
    date: str = Field(..., description="Observation date in YYYY-MM-DD format")
    coordinate_mode: Literal['geocentric', 'topocentric'] = Field(
        default='geocentric',
        description="Coordinate calculation mode"
    )
    refraction: RefractionSettings = Field(default_factory=RefractionSettings)
    location_name: Optional[str] = Field(default="", description="Location name for display")


class CrescentResponse(BaseModel):
    """Full crescent visibility calculation response."""

    class Config:
        # Allow arbitrary types for nested dicts
        arbitrary_types_allowed = True

    # We return a flexible dict since the response structure is complex
    # The actual structure matches the Accurate Times output format
    # See formatting.py for the text report generation
    pass
