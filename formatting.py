"""
Formatting utilities to match Accurate Times output format.

Accurate Times uses specific DMS (Degrees:Minutes:Seconds) formatting:
- Angles: ±DD°:MM':SS"
- Right Ascension: ±HHH MM SS
- Time: HH:MM:SS LT

All formatting functions return strings matching Accurate Times exactly.
"""

import math


def deg_to_dms(degrees):
    """
    Convert decimal degrees to (sign, degrees, minutes, seconds).

    Returns:
        Tuple (sign_str, deg, min, sec) where sign_str is '+' or '-'
    """
    sign = '+' if degrees >= 0 else '-'
    d = abs(degrees)
    deg = int(d)
    m = (d - deg) * 60.0
    minutes = int(m)
    sec = (m - minutes) * 60.0
    # Round seconds
    sec = round(sec)
    # Handle carry-over
    if sec >= 60:
        sec -= 60
        minutes += 1
    if minutes >= 60:
        minutes -= 60
        deg += 1

    return sign, deg, minutes, sec


def format_dms(degrees, width=3):
    """
    Format degrees as ±DDD°:MM':SS" (matching Accurate Times).

    Args:
        degrees: Decimal degrees
        width: Minimum width for degree part (2 or 3)

    Returns:
        Formatted string like "+263°:35':31\""
    """
    sign, deg, minutes, sec = deg_to_dms(degrees)
    if width == 3:
        return f"{sign}{deg:03d}°:{minutes:02d}':{sec:02d}\""
    else:
        return f"{sign}{deg:02d}°:{minutes:02d}':{sec:02d}\""


def format_dms_short(degrees):
    """
    Format degrees as ±DD°:MM':SS" with 2-digit degree width.
    Used for declination, altitude, etc.
    """
    return format_dms(degrees, width=2)


def format_ra(hours_decimal):
    """
    Format Right Ascension as ±HHH MM SS.

    Args:
        hours_decimal: RA in decimal hours

    Returns:
        Formatted string like "+23H 00M 34S"
    """
    sign = '+' if hours_decimal >= 0 else '-'
    h = abs(hours_decimal)
    hours = int(h)
    m = (h - hours) * 60.0
    minutes = int(m)
    sec = round((m - minutes) * 60.0)
    if sec >= 60:
        sec -= 60
        minutes += 1
    if minutes >= 60:
        minutes -= 60
        hours += 1

    return f"{sign}{hours:02d}H {minutes:02d}M {sec:02d}S"


def format_time_local(skyfield_time, tz_offset):
    """
    Format a Skyfield time as HH:MM:SS in local time.

    Args:
        skyfield_time: Skyfield Time object (UTC)
        tz_offset: Timezone offset in hours from UTC

    Returns:
        Formatted string like "17:30:59 LT"
    """
    if skyfield_time is None:
        return "N/A"

    # Get UTC datetime
    utc_dt = skyfield_time.utc_datetime()
    # Add timezone offset
    from datetime import timedelta
    local_dt = utc_dt + timedelta(hours=tz_offset)

    return f"{local_dt.hour:02d}:{local_dt.minute:02d}:{local_dt.second:02d} LT"


def format_datetime_local(skyfield_time, tz_offset):
    """
    Format as dd/mm/yyyy, HH:MM:SS LT.

    Args:
        skyfield_time: Skyfield Time object
        tz_offset: Hours from UTC

    Returns:
        Formatted string like "17/02/2026, 15:01:02 LT"
    """
    if skyfield_time is None:
        return "N/A"

    utc_dt = skyfield_time.utc_datetime()
    from datetime import timedelta
    local_dt = utc_dt + timedelta(hours=tz_offset)

    return (f"{local_dt.day:02d}/{local_dt.month:02d}/{local_dt.year}, "
            f"{local_dt.hour:02d}:{local_dt.minute:02d}:{local_dt.second:02d} LT")


def format_moon_age(hms_tuple):
    """
    Format moon age as +HHH MM SS.

    Args:
        hms_tuple: (hours, minutes, seconds)

    Returns:
        Formatted string like "+27H 28M 48S"
    """
    h, m, s = hms_tuple
    sign = '+' if h >= 0 else '-'
    return f"{sign}{abs(h):02d}H {m:02d}M {s:02d}S"


def format_lag_time(lag_tuple):
    """
    Format lag time as ±HHH MM SS.

    Args:
        lag_tuple: (sign, hours, minutes, seconds)

    Returns:
        Formatted string like "+00H 58M 52S"
    """
    sign, h, m, s = lag_tuple
    return f"{sign}{h:02d}H {m:02d}M {s:02d}S"


def format_illumination(pct):
    """Format illumination as XX.XX %."""
    return f"{pct:05.2f} %"


def format_magnitude(mag):
    """Format magnitude as ±XX.XX."""
    sign = '-' if mag < 0 else '+'
    return f"{sign}{abs(mag):05.2f}"


def format_distance(km):
    """Format distance as XXXXXXX.XX Km."""
    return f"{km:.2f} Km"


def format_location_dms(degrees, is_longitude=False):
    """
    Format a geographic coordinate in DMS notation.

    Args:
        degrees: Decimal degrees
        is_longitude: True for longitude, False for latitude

    Returns:
        Formatted string like "51:24:26.0"
    """
    sign, deg, minutes, sec = deg_to_dms(degrees)
    return f"{deg}:{minutes:02d}:{sec:04.1f}"


def generate_accurate_times_report(result, tz_offset, latitude, longitude,
                                    elevation, location_name="",
                                    temperature_c=10.0, pressure_mb=1010.0,
                                    humidity_pct=60.0, temp_lapse_rate=0.0065):
    """
    Generate a text report matching Accurate Times output format.

    Args:
        result: Dictionary from astronomy.compute_all()
        tz_offset: Timezone offset in hours
        And other settings

    Returns:
        Multi-line string matching Accurate Times format
    """
    timing = result['timing']
    eq = result['equatorial']
    ecl = result['ecliptic']
    horiz = result['horizontal']
    ang = result['angular']
    phys = result['physical']
    meta = result['metadata']
    best = result['best_time_data']

    prefix = 'G.' if meta['coordinate_mode'] == 'geocentric' else 'T.'

    lines = []
    lines.append("=" * 70)

    # Conjunction
    lines.append(f"- {prefix} Conjunction Time: {format_datetime_local(timing['conjunction_geo'] if meta['coordinate_mode'] == 'geocentric' else timing['conjunction_topo'], tz_offset)}")
    lines.append(f"- Julian Date at Time of Calculations: {meta['julian_date']}")

    # Sunset/Moonset & Age/Lag
    lines.append(f"- Sunset: {format_time_local(timing['sunset'], tz_offset):<40s}{prefix} Moon Age:   {format_moon_age(timing['moon_age_hms'])}")
    lines.append(f"- Moonset: {format_time_local(timing['moonset'], tz_offset):<39s}Moon Lag Time: {format_lag_time(timing['lag_time_hms'])}")

    # Equatorial
    lines.append(f"- {prefix} Moon Right Ascension: {format_ra(eq['moon_ra_hours']):<28s}{prefix} Moon Declination: {format_dms_short(eq['moon_dec_degrees'])}")
    lines.append(f"- {prefix} Sun Right Ascension:  {format_ra(eq['sun_ra_hours']):<28s}{prefix} Sun Declination:  {format_dms_short(eq['sun_dec_degrees'])}")

    # Ecliptic
    lines.append(f"- {prefix} Moon Longitude: {format_dms(ecl['moon_lon_degrees']):<35s}{prefix} Moon Latitude: {format_dms_short(ecl['moon_lat_degrees'])}")
    lines.append(f"- {prefix} Sun Longitude:  {format_dms(ecl['sun_lon_degrees']):<35s}{prefix} Sun Latitude:  {format_dms_short(ecl['sun_lat_degrees'])}")

    # Horizontal
    lines.append(f"- {prefix} Moon Altitude: {format_dms_short(horiz['moon_altitude_deg']):<36s}{prefix} Moon Azimuth: {format_dms(horiz['moon_azimuth_deg'])}")
    lines.append(f"- {prefix} Sun Altitude:  {format_dms_short(horiz['sun_altitude_deg']):<36s}{prefix} Sun Azimuth:  {format_dms(horiz['sun_azimuth_deg'])}")

    # Angular
    lines.append(f"- {prefix} Relative Altitude: {format_dms_short(ang['arcv_deg']):<32s}{prefix} Elongation:  {format_dms_short(ang['elongation_deg'])}")
    lines.append(f"- {prefix} Relative Azimuth:  {format_dms_short(ang['daz_deg']):<32s}{prefix} Phase Angle: {format_dms(ang['phase_angle_deg'])}")

    # Physical
    lines.append(f"- {prefix} Crescent Width: {format_dms_short(phys['crescent_width_deg']):<35s}{prefix} Moon Semi-Diameter: {format_dms_short(phys['semi_diameter_deg'])}")
    lines.append(f"- {prefix} Illumination: {format_illumination(phys['illumination_pct']):<37s}{prefix} Horizontal Parallax: {format_dms_short(phys['horizontal_parallax_deg'])}")
    lines.append(f"- {prefix} Magnitude: {format_magnitude(phys['magnitude']):<40s}{prefix} Distance: {format_distance(phys['distance_km'])}")

    lines.append("")
    lines.append("According to Odeh Criteria, using the following values at Best Time:")
    lines.append(f"* Moon-Sun Topocentric Relative Altitude = {format_dms_short(best['topo_arcv_deg'])} ({best['topo_arcv_deg']:.1f}°)")
    lines.append(f"* Topocentric Crescent width = {format_dms_short(best['topo_crescent_width_deg'])} ({best['topo_crescent_width_arcmin']:.2f}')")

    lines.append("=" * 70)

    return '\n'.join(lines)
