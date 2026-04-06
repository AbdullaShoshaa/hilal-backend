"""
Hilal Moon App — FastAPI Backend

Professional-grade crescent moon visibility calculator.
Matches Accurate Times 5.7 by Mohammad Odeh.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from models import CrescentRequest
from astronomy import compute_all, detect_crescent_type
from crescent import evaluate_all_criteria
from formatting import (
    format_dms, format_dms_short, format_ra, format_time_local,
    format_datetime_local, format_moon_age, format_lag_time,
    format_illumination, format_magnitude, format_distance,
    generate_accurate_times_report,
)

app = FastAPI(
    title="Hilal Moon App API",
    description="Professional crescent moon visibility calculator matching Accurate Times 5.7",
    version="1.0.0",
)

# Allow CORS for the React Native app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Hilal Moon App API",
        "version": "1.0.0",
        "description": "Professional crescent visibility calculator",
        "reference": "Accurate Times 5.7 by Mohammad Odeh",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/crescent-visibility")
async def crescent_visibility(request: CrescentRequest):
    """
    Calculate crescent visibility for a given location, date, and settings.

    Returns all astronomical parameters and visibility verdicts matching
    Accurate Times 5.7 output format.
    """
    try:
        # Parse date
        date_parts = request.date.split('-')
        year = int(date_parts[0])
        month = int(date_parts[1])
        day = int(date_parts[2])

        # Auto-detect crescent type from moon phase
        crescent_type = detect_crescent_type(year, month, day, request.timezone_offset)

        # Run the full calculation pipeline
        result = compute_all(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation,
            tz_offset=request.timezone_offset,
            date_year=year,
            date_month=month,
            date_day=day,
            crescent_type=crescent_type,
            coordinate_mode=request.coordinate_mode,
            temperature_c=request.refraction.temperature_c,
            pressure_mb=request.refraction.pressure_mb,
            humidity_pct=request.refraction.humidity_pct,
            temp_lapse_rate=request.refraction.temp_lapse_rate,
        )

        # Evaluate visibility criteria
        visibility = evaluate_all_criteria(
            result['best_time_data'],
            result['best_time_data']['topo_elongation_deg'],
        )

        # Build formatted response
        timing = result['timing']
        tz = request.timezone_offset

        response = {
            "metadata": {
                "crescent_type": crescent_type,
                "moon_label": result['metadata']['moon_label'],
                "visibility_date": request.date,
                "coordinate_mode": request.coordinate_mode,
                "calculation_time_event": result['metadata']['calculation_time_event'],
                "calculation_time": format_time_local(timing['calculation_time'], tz),
                "previous_new_moon": format_datetime_local(result['metadata']['previous_new_moon'], tz),
                "next_new_moon": format_datetime_local(result['metadata']['next_new_moon'], tz),
                "location": {
                    "name": request.location_name,
                    "latitude": request.latitude,
                    "longitude": request.longitude,
                    "elevation": request.elevation,
                    "timezone_offset": request.timezone_offset,
                },
                "refraction": {
                    "temperature_c": request.refraction.temperature_c,
                    "pressure_mb": request.refraction.pressure_mb,
                    "humidity_pct": request.refraction.humidity_pct,
                    "temp_lapse_rate": request.refraction.temp_lapse_rate,
                },
                "delta_t": result['metadata']['delta_t'],
                "julian_date": result['metadata']['julian_date'],
            },
            "timing": {
                "conjunction": format_datetime_local(
                    timing['conjunction_geo'] if request.coordinate_mode == 'geocentric'
                    else timing['conjunction_topo'], tz
                ),
                "sunset": format_time_local(timing['sunset'], tz),
                "moonset": format_time_local(timing['moonset'], tz),
                "sunrise": format_time_local(timing['sunrise'], tz),
                "moonrise": format_time_local(timing['moonrise'], tz),
                "moon_age": format_moon_age(timing['moon_age_hms']),
                "lag_time": format_lag_time(timing['lag_time_hms']),
                "best_time": format_time_local(timing['best_time'], tz),
            },
            "equatorial": {
                "moon_ra": format_ra(result['equatorial']['moon_ra_hours']),
                "moon_dec": format_dms_short(result['equatorial']['moon_dec_degrees']),
                "sun_ra": format_ra(result['equatorial']['sun_ra_hours']),
                "sun_dec": format_dms_short(result['equatorial']['sun_dec_degrees']),
            },
            "ecliptic": {
                "moon_longitude": format_dms(result['ecliptic']['moon_lon_degrees']),
                "moon_latitude": format_dms_short(result['ecliptic']['moon_lat_degrees']),
                "sun_longitude": format_dms(result['ecliptic']['sun_lon_degrees']),
                "sun_latitude": format_dms_short(result['ecliptic']['sun_lat_degrees']),
            },
            "horizontal": {
                "moon_altitude": format_dms_short(result['horizontal']['moon_altitude_deg']),
                "moon_azimuth": format_dms(result['horizontal']['moon_azimuth_deg']),
                "sun_altitude": format_dms_short(result['horizontal']['sun_altitude_deg']),
                "sun_azimuth": format_dms(result['horizontal']['sun_azimuth_deg']),
            },
            "angular": {
                "ARCV": format_dms_short(result['angular']['arcv_deg']),
                "ARCL": format_dms_short(result['angular']['elongation_deg']),
                "DAZ": format_dms_short(result['angular']['daz_deg']),
                "phase_angle": format_dms(result['angular']['phase_angle_deg']),
            },
            "physical": {
                "crescent_width": format_dms_short(result['physical']['crescent_width_deg']),
                "moon_semi_diameter": format_dms_short(result['physical']['semi_diameter_deg']),
                "illumination": f"{result['physical']['illumination_pct']:.2f} %",
                "horizontal_parallax": format_dms_short(result['physical']['horizontal_parallax_deg']),
                "magnitude": format_magnitude(result['physical']['magnitude']),
                "distance_km": result['physical']['distance_km'],
            },
            "raw_values": {
                "moon_altitude_deg": round(result['horizontal']['moon_altitude_deg'], 6),
                "moon_azimuth_deg": round(result['horizontal']['moon_azimuth_deg'], 6),
                "sun_altitude_deg": round(result['horizontal']['sun_altitude_deg'], 6),
                "sun_azimuth_deg": round(result['horizontal']['sun_azimuth_deg'], 6),
                "arcv_deg": round(result['angular']['arcv_deg'], 6),
                "elongation_deg": round(result['angular']['elongation_deg'], 6),
                "daz_deg": round(result['angular']['daz_deg'], 6),
                "phase_angle_deg": round(result['angular']['phase_angle_deg'], 6),
                "crescent_width_deg": round(result['physical']['crescent_width_deg'], 6),
                "crescent_width_arcmin": round(result['physical']['crescent_width_deg'] * 60.0, 4),
                "semi_diameter_deg": round(result['physical']['semi_diameter_deg'], 6),
                "illumination_pct": result['physical']['illumination_pct'],
                "distance_km": result['physical']['distance_km'],
                "moon_age_seconds": round(timing['moon_age_seconds'], 1),
                "lag_time_seconds": round(timing['lag_time_seconds'], 1),
            },
            "visibility": {
                "impossible": result['impossible'],
                "impossible_reason": result['impossible_reason'],
                "at_sunset": {
                    "topo_ARCV": format_dms_short(result['best_time_data']['topo_arcv_deg']),
                    "topo_ARCV_decimal": round(result['best_time_data']['topo_arcv_deg'], 1),
                    "topo_W": format_dms_short(result['best_time_data']['topo_crescent_width_deg']),
                    "topo_W_arcmin": round(result['best_time_data']['topo_crescent_width_arcmin'], 2),
                },
                "odeh": visibility['odeh'],
                "yallop": visibility['yallop'],
                "saao": visibility['saao'],
            },
            "text_report": generate_accurate_times_report(
                result, tz, request.latitude, request.longitude,
                request.elevation, request.location_name,
                request.refraction.temperature_c, request.refraction.pressure_mb,
                request.refraction.humidity_pct, request.refraction.temp_lapse_rate,
            ),
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
