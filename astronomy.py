"""
Core astronomical calculations using Skyfield (JPL DE440 ephemeris).

This module computes all Sun and Moon parameters needed for crescent
visibility prediction, matching the output of Accurate Times 5.7.

Key design decisions:
- Uses JPL DE440 ephemeris via Skyfield for sub-arcsecond accuracy
- Supports both geocentric and topocentric coordinate modes
- Rise/set times use iterative refinement with atmospheric refraction
- All angular values computed in degrees, converted to DMS for display
"""

import math
import numpy as np
from datetime import datetime, timedelta, timezone
from skyfield.api import load, Topos, Star, wgs84
from skyfield.almanac import find_discrete, risings_and_settings
from skyfield import almanac
from skyfield.units import Angle


# ──────────────────────────────────────────────
# Module-level ephemeris loading
# ──────────────────────────────────────────────

# Load once at module level. de440s.bsp covers 1849-2150, ~120MB
# de440.bsp covers 1549-2650, ~1.6GB (use if needed)
_ts = load.timescale()
_eph = load('de440s.bsp')
_sun = _eph['sun']
_moon = _eph['moon']
_earth = _eph['earth']


def get_timescale():
    """Return the shared timescale object."""
    return _ts


def get_delta_t(t):
    """
    Return Delta T (TT - UT1) in seconds for a given Skyfield time.
    Skyfield computes this internally from built-in tables.
    """
    # Skyfield time object has tt and ut1 attributes (Julian dates)
    # Delta T = TT - UT1 in days, convert to seconds
    return (t.tt - t.ut1) * 86400.0


def make_time(year, month, day, hour=0, minute=0, second=0.0, tz_offset=0.0):
    """
    Create a Skyfield time from local date/time and timezone offset.

    Args:
        year, month, day: Date components
        hour, minute: Time components (local time)
        second: Seconds (can be fractional)
        tz_offset: Hours offset from UTC (e.g., 3.0 for UTC+3)

    Returns:
        Skyfield Time object in UTC
    """
    # Convert local time to UTC
    utc_hour = hour - tz_offset
    return _ts.utc(year, month, day, utc_hour, minute, second)


def make_topos(latitude, longitude, elevation=0.0):
    """
    Create a geographic position on Earth (for almanac functions).

    Args:
        latitude: Degrees (positive North)
        longitude: Degrees (positive East)
        elevation: Meters above sea level

    Returns:
        Skyfield GeographicPosition (wgs84.latlon)
    """
    return wgs84.latlon(latitude, longitude, elevation_m=elevation)


def make_observer(latitude, longitude, elevation=0.0):
    """
    Create an observer position on Earth (for .at().observe() calls).

    Args:
        latitude: Degrees (positive North)
        longitude: Degrees (positive East)
        elevation: Meters above sea level

    Returns:
        Skyfield VectorSum (earth + topos)
    """
    return _earth + wgs84.latlon(latitude, longitude, elevation_m=elevation)


# ──────────────────────────────────────────────
# Sun/Moon Position Calculations
# ──────────────────────────────────────────────

def sun_position_geocentric(t):
    """
    Compute geocentric apparent position of the Sun.

    Returns dict with:
        ra: Right Ascension (hours, decimal)
        dec: Declination (degrees, decimal)
        lon: Ecliptic longitude (degrees)
        lat: Ecliptic latitude (degrees)
        distance_au: Distance in AU
    """
    astrometric = _earth.at(t).observe(_sun)
    apparent = astrometric.apparent()

    ra, dec, dist = apparent.radec(epoch='date')
    lat, lon, _ = apparent.ecliptic_latlon(epoch='date')

    return {
        'ra_hours': ra.hours,
        'dec_degrees': dec.degrees,
        'lon_degrees': lon.degrees,
        'lat_degrees': lat.degrees,
        'distance_au': dist.au,
        'distance_km': dist.km,
    }


def moon_position_geocentric(t):
    """
    Compute geocentric apparent position of the Moon.

    Returns dict with:
        ra: Right Ascension (hours, decimal)
        dec: Declination (degrees, decimal)
        lon: Ecliptic longitude (degrees)
        lat: Ecliptic latitude (degrees)
        distance_km: Distance in km
        semi_diameter_deg: Angular semi-diameter in degrees
        horizontal_parallax_deg: Horizontal parallax in degrees
    """
    astrometric = _earth.at(t).observe(_moon)
    apparent = astrometric.apparent()

    ra, dec, dist = apparent.radec(epoch='date')
    lat, lon, _ = apparent.ecliptic_latlon(epoch='date')

    distance_km = dist.km
    # Moon mean radius = 1737.4 km
    semi_diameter_deg = math.degrees(math.asin(1737.4 / distance_km))
    # Horizontal parallax = arcsin(Earth_equatorial_radius / distance)
    # Earth equatorial radius = 6378.137 km
    horizontal_parallax_deg = math.degrees(math.asin(6378.137 / distance_km))

    return {
        'ra_hours': ra.hours,
        'dec_degrees': dec.degrees,
        'lon_degrees': lon.degrees,
        'lat_degrees': lat.degrees,
        'distance_km': distance_km,
        'distance_au': dist.au,
        'semi_diameter_deg': semi_diameter_deg,
        'horizontal_parallax_deg': horizontal_parallax_deg,
    }


def sun_position_topocentric(t, observer):
    """
    Compute topocentric apparent position of the Sun from observer location.

    Returns dict with same keys as geocentric plus altitude/azimuth.
    """
    apparent = observer.at(t).observe(_sun).apparent()

    ra, dec, dist = apparent.radec(epoch='date')
    alt, az, _ = apparent.altaz()
    lat, lon, _ = apparent.ecliptic_latlon(epoch='date')

    return {
        'ra_hours': ra.hours,
        'dec_degrees': dec.degrees,
        'lon_degrees': lon.degrees,
        'lat_degrees': lat.degrees,
        'altitude_deg': alt.degrees,
        'azimuth_deg': az.degrees,
        'distance_au': dist.au,
        'distance_km': dist.km,
    }


def moon_position_topocentric(t, observer):
    """
    Compute topocentric apparent position of the Moon from observer location.

    Returns dict with same keys as geocentric plus altitude/azimuth.
    """
    apparent = observer.at(t).observe(_moon).apparent()

    ra, dec, dist = apparent.radec(epoch='date')
    alt, az, _ = apparent.altaz()
    lat, lon, _ = apparent.ecliptic_latlon(epoch='date')

    distance_km = dist.km
    semi_diameter_deg = math.degrees(math.asin(1737.4 / distance_km))
    horizontal_parallax_deg = math.degrees(math.asin(6378.137 / distance_km))

    return {
        'ra_hours': ra.hours,
        'dec_degrees': dec.degrees,
        'lon_degrees': lon.degrees,
        'lat_degrees': lat.degrees,
        'altitude_deg': alt.degrees,
        'azimuth_deg': az.degrees,
        'distance_km': distance_km,
        'distance_au': dist.au,
        'semi_diameter_deg': semi_diameter_deg,
        'horizontal_parallax_deg': horizontal_parallax_deg,
    }


def sun_altaz(t, observer, temperature_c=10.0, pressure_mb=1010.0):
    """
    Compute Sun's altitude and azimuth with atmospheric refraction.

    Args:
        t: Skyfield time
        observer: Observer position
        temperature_c: Temperature in Celsius for refraction
        pressure_mb: Pressure in millibars for refraction

    Returns:
        (altitude_degrees, azimuth_degrees) — refraction-corrected
    """
    apparent = observer.at(t).observe(_sun).apparent()
    alt, az, _ = apparent.altaz(temperature_C=temperature_c, pressure_mbar=pressure_mb)
    return alt.degrees, az.degrees


def moon_altaz(t, observer, temperature_c=10.0, pressure_mb=1010.0):
    """
    Compute Moon's altitude and azimuth with atmospheric refraction.

    Returns:
        (altitude_degrees, azimuth_degrees) — refraction-corrected
    """
    apparent = observer.at(t).observe(_moon).apparent()
    alt, az, _ = apparent.altaz(temperature_C=temperature_c, pressure_mbar=pressure_mb)
    return alt.degrees, az.degrees


# ──────────────────────────────────────────────
# Geocentric Altitude/Azimuth
# ──────────────────────────────────────────────

def geocentric_altaz(t, latitude, longitude, body_ra_hours, body_dec_degrees):
    """
    Compute geocentric (no parallax) altitude and azimuth.

    This calculates where the body would appear if viewed from Earth's center,
    projected onto the observer's local horizon coordinate system.
    Used when Accurate Times is set to 'Geocentric' mode.

    Args:
        t: Skyfield time
        latitude: Observer latitude in degrees
        longitude: Observer longitude in degrees
        body_ra_hours: Body's geocentric RA in decimal hours
        body_dec_degrees: Body's geocentric Dec in decimal degrees

    Returns:
        (altitude_degrees, azimuth_degrees)
    """
    # Compute local sidereal time
    gst = t.gast  # Greenwich Apparent Sidereal Time in hours
    lst = gst + longitude / 15.0  # Local Sidereal Time in hours

    # Hour angle
    ha_hours = lst - body_ra_hours
    ha_rad = math.radians(ha_hours * 15.0)

    lat_rad = math.radians(latitude)
    dec_rad = math.radians(body_dec_degrees)

    # Altitude
    sin_alt = (math.sin(lat_rad) * math.sin(dec_rad) +
               math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad))
    alt_rad = math.asin(max(-1.0, min(1.0, sin_alt)))

    # Azimuth
    cos_az = ((math.sin(dec_rad) - math.sin(lat_rad) * math.sin(alt_rad)) /
              (math.cos(lat_rad) * math.cos(alt_rad) + 1e-15))
    cos_az = max(-1.0, min(1.0, cos_az))
    az_rad = math.acos(cos_az)

    if math.sin(ha_rad) > 0:
        az_rad = 2 * math.pi - az_rad

    return math.degrees(alt_rad), math.degrees(az_rad)


# ──────────────────────────────────────────────
# Rise/Set Time Calculations
# ──────────────────────────────────────────────

def _geometric_dip(elevation_m):
    """
    Compute geometric horizon dip for an elevated observer.

    Args:
        elevation_m: Observer elevation in meters

    Returns:
        Dip angle in degrees (always positive)
    """
    if elevation_m <= 0:
        return 0.0
    return math.degrees(math.acos(6371000.0 / (6371000.0 + elevation_m)))


_SUN_SEMI_DIAMETER_DEG = 0.2667   # ~16 arcminutes (average)
_MOON_SEMI_DIAMETER_DEG = 0.2619  # ~15.7 arcminutes (approximate average)
_STD_REFRACTION_DEG = 0.5667      # ~34 arcminutes (standard atmospheric refraction)


def find_sunset(t_date, topos, tz_offset, temperature_c=10.0, pressure_mb=1010.0, elevation_m=0.0):
    """
    Find sunset time on the given date.

    Sunset = upper limb of Sun touches apparent horizon, corrected for
    atmospheric refraction and geometric dip from elevation.

    Args:
        t_date: Skyfield time for the date (start of day UTC)
        topos: Skyfield GeographicPosition (wgs84.latlon)
        tz_offset: Timezone offset in hours
        elevation_m: Observer elevation in meters (for horizon dip)

    Returns:
        Skyfield time of sunset, or None if no sunset found
    """
    year = t_date.utc.year
    month = t_date.utc.month
    day = t_date.utc.day

    t0 = _ts.utc(year, month, day, -tz_offset)
    t1 = _ts.utc(year, month, day, 24 - tz_offset)

    dip = _geometric_dip(elevation_m)
    horizon = -(_STD_REFRACTION_DEG + dip)

    f = almanac.risings_and_settings(
        _eph, _sun, topos,
        horizon_degrees=horizon,
        radius_degrees=_SUN_SEMI_DIAMETER_DEG,
    )
    times, events = find_discrete(t0, t1, f)

    for ti, event in zip(times, events):
        if event == 0:  # 0 = setting
            return ti
    return None


def find_sunrise(t_date, topos, tz_offset, temperature_c=10.0, pressure_mb=1010.0, elevation_m=0.0):
    """
    Find sunrise time on the given date.

    Returns:
        Skyfield time of sunrise, or None
    """
    year = t_date.utc.year
    month = t_date.utc.month
    day = t_date.utc.day

    t0 = _ts.utc(year, month, day, -tz_offset)
    t1 = _ts.utc(year, month, day, 24 - tz_offset)

    dip = _geometric_dip(elevation_m)
    horizon = -(_STD_REFRACTION_DEG + dip)

    f = almanac.risings_and_settings(
        _eph, _sun, topos,
        horizon_degrees=horizon,
        radius_degrees=_SUN_SEMI_DIAMETER_DEG,
    )
    times, events = find_discrete(t0, t1, f)

    for ti, event in zip(times, events):
        if event == 1:  # 1 = rising
            return ti
    return None


def find_moonset(t_date, topos, tz_offset, elevation_m=0.0):
    """
    Find moonset time on the given date.

    Moon rise/set corrected for atmospheric refraction, geometric dip,
    and Moon's semi-diameter (upper limb criterion).

    Returns:
        Skyfield time of moonset, or None
    """
    year = t_date.utc.year
    month = t_date.utc.month
    day = t_date.utc.day

    t0 = _ts.utc(year, month, day, -tz_offset)
    t1 = _ts.utc(year, month, day, 24 - tz_offset + 6)

    dip = _geometric_dip(elevation_m)
    horizon = -(_STD_REFRACTION_DEG + dip)

    f = almanac.risings_and_settings(
        _eph, _moon, topos,
        horizon_degrees=horizon,
        radius_degrees=_MOON_SEMI_DIAMETER_DEG,
    )
    times, events = find_discrete(t0, t1, f)

    for ti, event in zip(times, events):
        if event == 0:  # 0 = setting
            return ti
    return None


def find_moonrise(t_date, topos, tz_offset, elevation_m=0.0):
    """
    Find moonrise time on the given date.

    Returns:
        Skyfield time of moonrise, or None
    """
    year = t_date.utc.year
    month = t_date.utc.month
    day = t_date.utc.day

    t0 = _ts.utc(year, month, day, -tz_offset - 6)
    t1 = _ts.utc(year, month, day, 24 - tz_offset)

    dip = _geometric_dip(elevation_m)
    horizon = -(_STD_REFRACTION_DEG + dip)

    f = almanac.risings_and_settings(
        _eph, _moon, topos,
        horizon_degrees=horizon,
        radius_degrees=_MOON_SEMI_DIAMETER_DEG,
    )
    times, events = find_discrete(t0, t1, f)

    for ti, event in zip(times, events):
        if event == 1:  # 1 = rising
            return ti
    return None


# ──────────────────────────────────────────────
# Crescent Type Detection
# ──────────────────────────────────────────────

def detect_crescent_type(date_year, date_month, date_day, tz_offset=0.0):
    """
    Auto-detect whether the crescent is waxing or waning on the given date.

    Computes the Moon's ecliptic longitude relative to the Sun at noon local time.
    If Moon is 0-180° ahead of Sun (eastward), it's waxing (new/evening crescent).
    If Moon is 180-360° ahead of Sun, it's waning (old/morning crescent).

    Returns:
        'waxing' or 'waning'
    """
    t = _ts.utc(date_year, date_month, date_day, 12.0 - tz_offset)

    sun_apparent = _earth.at(t).observe(_sun).apparent()
    moon_apparent = _earth.at(t).observe(_moon).apparent()

    _, sun_lon, _ = sun_apparent.ecliptic_latlon(epoch='date')
    _, moon_lon, _ = moon_apparent.ecliptic_latlon(epoch='date')

    diff = (moon_lon.degrees - sun_lon.degrees) % 360.0
    return 'waxing' if diff < 180.0 else 'waning'


# ──────────────────────────────────────────────
# Conjunction Finding
# ──────────────────────────────────────────────

def find_geocentric_conjunction(year, month, search_days=35):
    """
    Find the geocentric conjunction (new moon) nearest to the given month.

    Conjunction = moment when Sun and Moon have the same ecliptic longitude
    (geocentric). This is the "birth" of the new moon.

    Uses Skyfield's moon_phase function: conjunction is when phase = 0°.

    Args:
        year, month: Approximate date to search around
        search_days: Days to search before and after

    Returns:
        Skyfield time of conjunction
    """
    # Search window centered on the given month
    t0 = _ts.utc(year, month, 1, 0, 0, 0) - timedelta(days=search_days // 2)
    t1 = _ts.utc(year, month, 1, 0, 0, 0) + timedelta(days=search_days // 2)

    # Convert to Skyfield times
    t0_sf = _ts.utc(t0.year, t0.month, t0.day)
    t1_sf = _ts.utc(t1.year, t1.month, t1.day + search_days)

    # Find moon phases (0=new, 1=first quarter, 2=full, 3=last quarter)
    times, phases = almanac.find_discrete(t0_sf, t1_sf, almanac.moon_phases(_eph))

    # Find the new moon (phase 0) closest to our target date
    target = _ts.utc(year, month, 1)
    best_conjunction = None
    best_diff = float('inf')

    for ti, phase in zip(times, phases):
        if phase == 0:  # New moon
            diff = abs(ti.tt - target.tt)
            if diff < best_diff:
                best_diff = diff
                best_conjunction = ti

    return best_conjunction


def find_conjunction_before_date(date_year, date_month, date_day, tz_offset=0.0):
    """
    Find the most recent geocentric conjunction before the given date.

    This is needed because for a crescent observation on date X,
    we need the conjunction that occurred before X.

    Args:
        date_year, date_month, date_day: The observation date
        tz_offset: Timezone offset in hours

    Returns:
        Skyfield time of the conjunction
    """
    # Search from 35 days before to the end of the observation day (local midnight).
    # Using end-of-day ensures a conjunction occurring any time on the observation
    # date (including afternoon/evening) is captured as the "previous new moon".
    t_obs = _ts.utc(date_year, date_month, date_day, 24 - tz_offset)
    t_start = _ts.utc(date_year, date_month, date_day - 35, 0)

    times, phases = almanac.find_discrete(t_start, t_obs, almanac.moon_phases(_eph))

    # Find the last new moon before observation date
    last_conjunction = None
    for ti, phase in zip(times, phases):
        if phase == 0:
            last_conjunction = ti

    return last_conjunction


def find_next_conjunction_after_date(date_year, date_month, date_day, tz_offset=0.0):
    """
    Find the first geocentric conjunction (new moon) after the given date.

    Used to determine the upcoming new moon when the crescent is waning.

    Returns:
        Skyfield time of the next conjunction
    """
    t_obs = _ts.utc(date_year, date_month, date_day, 12 - tz_offset)
    t_end = _ts.utc(date_year, date_month, date_day + 35, 0)

    times, phases = almanac.find_discrete(t_obs, t_end, almanac.moon_phases(_eph))

    for ti, phase in zip(times, phases):
        if phase == 0:
            return ti

    return None


# ──────────────────────────────────────────────
# Topocentric Conjunction
# ──────────────────────────────────────────────

def find_topocentric_conjunction(t_geocentric, observer, search_hours=6):
    """
    Find the topocentric conjunction time near a known geocentric conjunction.

    Topocentric conjunction = moment when the topocentric ecliptic longitudes
    of the Sun and Moon are equal, as seen from a specific observer.

    This differs from geocentric conjunction by up to ~1.5 hours due to
    the Moon's parallax.

    Uses bisection method for precision.

    Args:
        t_geocentric: Skyfield time of geocentric conjunction (starting point)
        observer: Observer position
        search_hours: Hours to search around geocentric time

    Returns:
        Skyfield time of topocentric conjunction
    """
    def moon_sun_lon_diff(t):
        """Topocentric ecliptic longitude difference (Moon - Sun)."""
        moon_app = observer.at(t).observe(_moon).apparent()
        sun_app = observer.at(t).observe(_sun).apparent()

        _, moon_lon, _ = moon_app.ecliptic_latlon(epoch='date')
        _, sun_lon, _ = sun_app.ecliptic_latlon(epoch='date')

        diff = moon_lon.degrees - sun_lon.degrees
        # Normalize to -180 to +180
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        return diff

    # Bisection search
    t_start = _ts.tt_jd(t_geocentric.tt - search_hours / 24.0)
    t_end = _ts.tt_jd(t_geocentric.tt + search_hours / 24.0)

    d_start = moon_sun_lon_diff(t_start)
    d_end = moon_sun_lon_diff(t_end)

    # Iterate bisection
    for _ in range(60):  # 60 iterations gives sub-second precision
        t_mid = _ts.tt_jd((t_start.tt + t_end.tt) / 2.0)
        d_mid = moon_sun_lon_diff(t_mid)

        if d_start * d_mid < 0:
            t_end = t_mid
            d_end = d_mid
        else:
            t_start = t_mid
            d_start = d_mid

    return _ts.tt_jd((t_start.tt + t_end.tt) / 2.0)


# ──────────────────────────────────────────────
# Derived Parameters
# ──────────────────────────────────────────────

def compute_elongation(sun_ra_h, sun_dec_d, moon_ra_h, moon_dec_d):
    """
    Compute angular separation (elongation / ARCL) between Sun and Moon.

    Uses the spherical law of cosines:
    cos(ARCL) = sin(δ₁)sin(δ₂) + cos(δ₁)cos(δ₂)cos(α₁ - α₂)

    Args:
        sun_ra_h: Sun RA in hours
        sun_dec_d: Sun Dec in degrees
        moon_ra_h: Moon RA in hours
        moon_dec_d: Moon Dec in degrees

    Returns:
        Elongation in degrees
    """
    ra1 = math.radians(sun_ra_h * 15.0)
    dec1 = math.radians(sun_dec_d)
    ra2 = math.radians(moon_ra_h * 15.0)
    dec2 = math.radians(moon_dec_d)

    cos_elong = (math.sin(dec1) * math.sin(dec2) +
                 math.cos(dec1) * math.cos(dec2) * math.cos(ra2 - ra1))
    cos_elong = max(-1.0, min(1.0, cos_elong))

    return math.degrees(math.acos(cos_elong))


def compute_arcv(moon_alt, sun_alt):
    """
    Compute ARCV (relative altitude / arc of vision).

    ARCV = Moon altitude - Sun altitude

    Returns:
        ARCV in degrees (positive means Moon is above Sun)
    """
    return moon_alt - sun_alt


def compute_daz(sun_az, moon_az):
    """
    Compute DAZ (relative azimuth).

    DAZ = Moon azimuth - Sun azimuth
    (Accurate Times sign convention)

    Returns:
        DAZ in degrees (signed)
    """
    return moon_az - sun_az


def compute_phase_angle(elongation_deg, moon_distance_km, sun_distance_km):
    """
    Compute phase angle using the Sun-Moon-Earth triangle.

    The phase angle is the angle at the Moon between the Sun and Earth.
    Uses law of cosines with the three sides of the triangle:
    - d = Earth-Moon distance
    - R = Earth-Sun distance
    - D = Sun-Moon distance (computed from d, R, and elongation)

    Args:
        elongation_deg: Earth-centric elongation (ARCL) in degrees
        moon_distance_km: Earth-Moon distance in km
        sun_distance_km: Earth-Sun distance in km

    Returns:
        Phase angle in degrees
    """
    d = moon_distance_km
    R = sun_distance_km
    elong_rad = math.radians(elongation_deg)

    # Sun-Moon distance via law of cosines (triangle at Earth vertex)
    D2 = R * R + d * d - 2.0 * R * d * math.cos(elong_rad)
    D = math.sqrt(D2)

    # Phase angle via law of cosines (angle at Moon vertex)
    cos_i = (d * d + D2 - R * R) / (2.0 * d * D)
    cos_i = max(-1.0, min(1.0, cos_i))

    return math.degrees(math.acos(cos_i))


def compute_illumination(phase_angle_deg):
    """
    Compute Moon illumination percentage.

    Illumination = (1 + cos(phase_angle)) / 2 × 100

    Returns:
        Illumination as percentage
    """
    return (1.0 + math.cos(math.radians(phase_angle_deg))) / 2.0 * 100.0


def compute_crescent_width(semi_diameter_deg, elongation_deg):
    """
    Compute crescent width W.

    W = SD × (1 - cos(ARCL))

    where SD is semi-diameter and ARCL is elongation.

    Returns:
        Crescent width in degrees (convert to arcminutes for display)
    """
    sd = semi_diameter_deg
    w = sd * (1.0 - math.cos(math.radians(elongation_deg)))
    return w


def compute_moon_magnitude(phase_angle_deg):
    """
    Approximate Moon visual magnitude.

    Based on Allen's Astrophysical Quantities formula, adapted.
    At full moon: ~-12.7
    For thin crescent, magnitude is much dimmer.

    Returns:
        Approximate visual magnitude
    """
    pa = abs(phase_angle_deg)
    # Simple polynomial approximation
    mag = -12.73 + 0.026 * pa + 4.0e-9 * pa**4
    return mag


def compute_best_time(t_sunset, t_moonset, crescent_type='waxing', t_sunrise=None, t_moonrise=None):
    """
    Compute the best time for crescent observation.

    For new (waxing) crescent: Best Time = Sunset + (4/9) × Lag
    For old (waning) crescent: Best Time = Sunrise - (4/9) × Lag

    Args:
        t_sunset: Skyfield time of sunset
        t_moonset: Skyfield time of moonset
        crescent_type: 'waxing' or 'waning'
        t_sunrise: Skyfield time of sunrise (needed for waning)
        t_moonrise: Skyfield time of moonrise (needed for waning)

    Returns:
        Skyfield time of best observation time
    """
    if crescent_type == 'waxing':
        lag_days = t_moonset.tt - t_sunset.tt  # in Julian days
        best_jd = t_sunset.tt + (4.0 / 9.0) * lag_days
    else:  # waning
        lag_days = t_sunrise.tt - t_moonrise.tt
        best_jd = t_sunrise.tt - (4.0 / 9.0) * lag_days

    return _ts.tt_jd(best_jd)


def compute_moon_age(t_conjunction, t_reference):
    """
    Compute Moon age (time since conjunction).

    Args:
        t_conjunction: Skyfield time of conjunction
        t_reference: Skyfield time of reference (usually sunset)

    Returns:
        Age in seconds (total), and as (hours, minutes, seconds) tuple
    """
    diff_days = t_reference.tt - t_conjunction.tt
    total_seconds = diff_days * 86400.0

    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)

    return total_seconds, (hours, minutes, seconds)


def compute_lag_time(t_sunset, t_moonset):
    """
    Compute lag time (Moonset - Sunset for new crescent).

    Returns:
        Lag in seconds (total), and as (hours, minutes, seconds) tuple
    """
    diff_days = t_moonset.tt - t_sunset.tt
    total_seconds = diff_days * 86400.0

    sign = '+' if total_seconds >= 0 else '-'
    total_seconds_abs = abs(total_seconds)
    hours = int(total_seconds_abs // 3600)
    minutes = int((total_seconds_abs % 3600) // 60)
    seconds = int(total_seconds_abs % 60)

    return total_seconds, (sign, hours, minutes, seconds)


def julian_date(t):
    """Return Julian Date for a Skyfield time."""
    return t.tt  # Skyfield .tt is already Julian Date (TT)


# ──────────────────────────────────────────────
# Full Calculation Pipeline
# ──────────────────────────────────────────────

def compute_all(latitude, longitude, elevation, tz_offset,
                date_year, date_month, date_day,
                crescent_type='waxing',
                coordinate_mode='geocentric',
                temperature_c=10.0, pressure_mb=1010.0,
                humidity_pct=60.0, temp_lapse_rate=0.0065):
    """
    Compute all crescent visibility parameters.

    This is the main entry point that calculates everything needed
    for the API response, matching Accurate Times output.

    Args:
        latitude: Observer latitude (degrees, positive North)
        longitude: Observer longitude (degrees, positive East)
        elevation: Observer elevation (meters)
        tz_offset: Timezone offset from UTC (hours)
        date_year, date_month, date_day: Observation date
        crescent_type: 'waxing' (new/evening) or 'waning' (old/morning)
        coordinate_mode: 'geocentric' or 'topocentric'
        temperature_c: Temperature for refraction (°C)
        pressure_mb: Pressure for refraction (mbar)
        humidity_pct: Humidity (%)
        temp_lapse_rate: Temperature lapse rate (K/m)

    Returns:
        Dictionary with all computed parameters
    """
    topos = make_topos(latitude, longitude, elevation)
    observer = make_observer(latitude, longitude, elevation)

    # Reference date (start of the observation day)
    t_ref = _ts.utc(date_year, date_month, date_day)

    # ── 1. Find rise/set times (almanac functions need bare topos) ──
    t_sunset = find_sunset(t_ref, topos, tz_offset, temperature_c, pressure_mb, elevation)
    t_sunrise = find_sunrise(t_ref, topos, tz_offset, temperature_c, pressure_mb, elevation)
    t_moonset = find_moonset(t_ref, topos, tz_offset, elevation)
    t_moonrise = find_moonrise(t_ref, topos, tz_offset, elevation)

    # ── 2. Find conjunction ──
    t_conjunction_geo = find_conjunction_before_date(
        date_year, date_month, date_day, tz_offset
    )
    t_conjunction_topo = find_topocentric_conjunction(t_conjunction_geo, observer)
    t_next_conjunction_geo = find_next_conjunction_after_date(
        date_year, date_month, date_day, tz_offset
    )

    # ── 3. Determine calculation time ──
    # Accurate Times calculates positions at moonset (new) or moonrise (old)
    if crescent_type == 'waxing':
        t_calc = t_moonset
    else:
        t_calc = t_moonrise

    # ── 4. Compute positions at calculation time ──
    sun_geo = sun_position_geocentric(t_calc)
    moon_geo = moon_position_geocentric(t_calc)
    sun_topo = sun_position_topocentric(t_calc, observer)
    moon_topo = moon_position_topocentric(t_calc, observer)

    # Choose which coordinates to report based on mode
    if coordinate_mode == 'geocentric':
        # Geocentric RA/Dec/ecliptic
        sun_pos = sun_geo
        moon_pos = moon_geo

        # For geocentric alt/az, we compute from geocentric RA/Dec
        # projected onto observer's local horizon
        moon_alt, moon_az = geocentric_altaz(
            t_calc, latitude, longitude,
            moon_geo['ra_hours'], moon_geo['dec_degrees']
        )
        sun_alt, sun_az = geocentric_altaz(
            t_calc, latitude, longitude,
            sun_geo['ra_hours'], sun_geo['dec_degrees']
        )

        # Elongation from geocentric coordinates
        elongation = compute_elongation(
            sun_geo['ra_hours'], sun_geo['dec_degrees'],
            moon_geo['ra_hours'], moon_geo['dec_degrees']
        )
        semi_diameter = moon_geo['semi_diameter_deg']
        h_parallax = moon_geo['horizontal_parallax_deg']
        distance_km = moon_geo['distance_km']
    else:
        # Topocentric
        sun_pos = sun_topo
        moon_pos = moon_topo
        moon_alt = moon_topo['altitude_deg']
        moon_az = moon_topo['azimuth_deg']
        sun_alt = sun_topo['altitude_deg']
        sun_az = sun_topo['azimuth_deg']

        elongation = compute_elongation(
            sun_topo['ra_hours'], sun_topo['dec_degrees'],
            moon_topo['ra_hours'], moon_topo['dec_degrees']
        )
        semi_diameter = moon_topo['semi_diameter_deg']
        h_parallax = moon_topo['horizontal_parallax_deg']
        distance_km = moon_topo['distance_km']

    # ── 5. Derived angular parameters ──
    arcv = compute_arcv(moon_alt, sun_alt)
    daz = compute_daz(sun_az, moon_az)
    phase_angle = compute_phase_angle(elongation, moon_pos['distance_km'], sun_pos['distance_km'])
    illumination = compute_illumination(phase_angle)
    crescent_width = compute_crescent_width(semi_diameter, elongation)
    magnitude = compute_moon_magnitude(phase_angle)

    # ── 6. Timing parameters ──
    if crescent_type == 'waxing':
        conjunction_used = t_conjunction_geo if coordinate_mode == 'geocentric' else t_conjunction_topo
        moon_age_total, moon_age_hms = compute_moon_age(conjunction_used, t_calc)
        lag_total, lag_hms = compute_lag_time(t_sunset, t_moonset)
        t_best = compute_best_time(t_sunset, t_moonset, crescent_type)
    else:
        conjunction_used = t_conjunction_geo if coordinate_mode == 'geocentric' else t_conjunction_topo
        moon_age_total, moon_age_hms = compute_moon_age(conjunction_used, t_calc)
        lag_total, lag_hms = compute_lag_time(t_moonrise, t_sunrise)
        t_best = compute_best_time(None, None, crescent_type, t_sunrise, t_moonrise)

    # ── 7. Compute positions at sunset/sunrise for all visibility criteria ──
    # All three criteria (Odeh, Yallop, SAAO) are evaluated at the moment
    # the Sun sets (waxing crescent) or rises (waning crescent).
    t_criteria_ref = t_sunset if crescent_type == 'waxing' else t_sunrise
    if t_criteria_ref is not None:
        sun_crit_topo = sun_position_topocentric(t_criteria_ref, observer)
        moon_crit_topo = moon_position_topocentric(t_criteria_ref, observer)

        crit_moon_alt = moon_crit_topo['altitude_deg']
        crit_moon_az = moon_crit_topo['azimuth_deg']
        crit_sun_alt = sun_crit_topo['altitude_deg']
        crit_sun_az = sun_crit_topo['azimuth_deg']

        crit_arcv_topo = compute_arcv(crit_moon_alt, crit_sun_alt)
        crit_elongation_topo = compute_elongation(
            sun_crit_topo['ra_hours'], sun_crit_topo['dec_degrees'],
            moon_crit_topo['ra_hours'], moon_crit_topo['dec_degrees']
        )
        crit_semi_diameter_topo = moon_crit_topo['semi_diameter_deg']
        crit_crescent_width_topo = compute_crescent_width(
            crit_semi_diameter_topo, crit_elongation_topo
        )
        crit_daz = compute_daz(crit_sun_az, crit_moon_az)

        # Geocentric ARCV at criteria time (for Yallop)
        moon_geo_crit = moon_position_geocentric(t_criteria_ref)
        sun_geo_crit = sun_position_geocentric(t_criteria_ref)
        crit_moon_alt_geo, _ = geocentric_altaz(
            t_criteria_ref, latitude, longitude,
            moon_geo_crit['ra_hours'], moon_geo_crit['dec_degrees']
        )
        crit_sun_alt_geo, _ = geocentric_altaz(
            t_criteria_ref, latitude, longitude,
            sun_geo_crit['ra_hours'], sun_geo_crit['dec_degrees']
        )
        crit_arcv_geo = compute_arcv(crit_moon_alt_geo, crit_sun_alt_geo)
    else:
        crit_arcv_topo = None
        crit_crescent_width_topo = None
        crit_arcv_geo = None
        crit_elongation_topo = None
        crit_daz = None
        crit_moon_alt = None

    # ── 9. Delta T and Julian Date ──
    delta_t = get_delta_t(t_calc)
    jd = t_calc.tt

    # ── 11. Impossible flag ──
    impossible = False
    impossible_reason = None
    if crescent_type == 'waxing':
        if t_moonset is not None and t_sunset is not None and t_moonset.tt < t_sunset.tt:
            impossible = True
            impossible_reason = "Moonset occurs before Sunset"
        if t_conjunction_topo is not None and t_sunset is not None and t_conjunction_topo.tt > t_sunset.tt:
            impossible = True
            impossible_reason = "Topocentric conjunction occurs after Sunset"
    else:
        if t_moonrise is not None and t_sunrise is not None and t_moonrise.tt > t_sunrise.tt:
            impossible = True
            impossible_reason = "Moonrise occurs after Sunrise"
        if t_conjunction_topo is not None and t_sunrise is not None and t_conjunction_topo.tt > t_sunrise.tt:
            impossible = True
            impossible_reason = "Topocentric conjunction occurs after Sunrise"

    # ── 12. Build result dictionary ──
    result = {
        'metadata': {
            'crescent_type': crescent_type,
            'moon_label': 'New Moon' if crescent_type == 'waxing' else 'Old Moon',
            'coordinate_mode': coordinate_mode,
            'calculation_time_event': 'Moonset' if crescent_type == 'waxing' else 'Moonrise',
            'delta_t': round(delta_t, 2),
            'julian_date': round(jd, 5),
            'next_new_moon': t_next_conjunction_geo,
            'previous_new_moon': t_conjunction_geo,
        },
        'timing': {
            'conjunction_geo': t_conjunction_geo,
            'conjunction_topo': t_conjunction_topo,
            'sunset': t_sunset,
            'moonset': t_moonset,
            'sunrise': t_sunrise,
            'moonrise': t_moonrise,
            'moon_age_seconds': moon_age_total,
            'moon_age_hms': moon_age_hms,
            'lag_time_seconds': lag_total,
            'lag_time_hms': lag_hms,
            'best_time': t_best,
            'calculation_time': t_calc,
        },
        'equatorial': {
            'moon_ra_hours': moon_pos['ra_hours'],
            'moon_dec_degrees': moon_pos['dec_degrees'],
            'sun_ra_hours': sun_pos['ra_hours'],
            'sun_dec_degrees': sun_pos['dec_degrees'],
        },
        'ecliptic': {
            'moon_lon_degrees': moon_pos['lon_degrees'],
            'moon_lat_degrees': moon_pos['lat_degrees'],
            'sun_lon_degrees': sun_pos['lon_degrees'],
            'sun_lat_degrees': sun_pos['lat_degrees'],
        },
        'horizontal': {
            'moon_altitude_deg': moon_alt,
            'moon_azimuth_deg': moon_az,
            'sun_altitude_deg': sun_alt,
            'sun_azimuth_deg': sun_az,
        },
        'angular': {
            'arcv_deg': arcv,
            'elongation_deg': elongation,
            'daz_deg': daz,
            'phase_angle_deg': phase_angle,
        },
        'physical': {
            'crescent_width_deg': crescent_width,
            'semi_diameter_deg': semi_diameter,
            'illumination_pct': round(illumination, 2),
            'horizontal_parallax_deg': h_parallax,
            'magnitude': round(magnitude, 2),
            'distance_km': round(distance_km, 2),
        },
        'best_time_data': {
            'topo_arcv_deg': crit_arcv_topo,
            'topo_crescent_width_deg': crit_crescent_width_topo,
            'topo_crescent_width_arcmin': crit_crescent_width_topo * 60.0 if crit_crescent_width_topo is not None else None,
            'geo_arcv_deg': crit_arcv_geo,
            'topo_elongation_deg': crit_elongation_topo,
            'saao_moon_alt_deg': crit_moon_alt,
            'saao_daz_deg': crit_daz,
        },
        'impossible': impossible,
        'impossible_reason': impossible_reason,
    }

    return result
