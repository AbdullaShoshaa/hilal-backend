"""
Validation test comparing our calculations against Accurate Times 5.7.

Reference data: Ramadan 1447 AH, Doha Qatar, Waxing Crescent, Geocentric
From Accurate Times 5.7 by Mohammad Odeh (user-provided screenshots).

Run with: python -m app.test_validation
"""

import sys
import math


# ══════════════════════════════════════════════
# REFERENCE DATA (from Accurate Times 5.7)
# ══════════════════════════════════════════════

REFERENCE = {
    'location': {
        'name': 'Doha, Qatar',
        'latitude': 25 + 17/60 + 3.0/3600,   # 25°17'03.0" N = 25.284167°
        'longitude': 51 + 24/60 + 26.0/3600,  # 51°24'26.0" E = 51.407222°
        'elevation': 40.0,
        'timezone_offset': 3.0,
    },
    'settings': {
        'date': '2026-02-18',
        'crescent_type': 'waxing',
        'coordinate_mode': 'geocentric',
        'temperature_c': 10.0,
        'pressure_mb': 1010.0,
        'humidity_pct': 60.0,
        'temp_lapse_rate': 0.0065,
    },
    'expected': {
        # Timing (converted to total seconds from midnight LT for comparison)
        'conjunction_time_lt': '15:01:02',  # 17/02/2026

        'sunset_lt': '17:30:59',
        'moonset_lt': '18:29:51',

        'moon_age_hours': 27,
        'moon_age_minutes': 28,
        'moon_age_seconds': 48,

        'lag_hours': 0,
        'lag_minutes': 58,
        'lag_seconds': 52,

        # Equatorial
        'moon_ra_hours': 23 + 0/60 + 34/3600,      # 23H 00M 34S
        'moon_dec_degrees': -(5 + 49/60 + 49/3600), # -05°49'49"
        'sun_ra_hours': 22 + 8/60 + 18/3600,        # 22H 08M 18S
        'sun_dec_degrees': -(11 + 28/60 + 37/3600), # -11°28'37"

        # Ecliptic
        'moon_lon_degrees': 344 + 4/60 + 17/3600,   # 344°04'17"
        'moon_lat_degrees': 0 + 28/60 + 23/3600,    # +00°28'23"
        'sun_lon_degrees': 329 + 59/60 + 5/3600,    # 329°59'05"
        'sun_lat_degrees': 0.0,                       # +00°00'00"

        # Horizontal (at moonset)
        'moon_altitude_deg': -(0 + 5/60 + 23/3600),  # -00°05'23"
        'moon_azimuth_deg': 263 + 35/60 + 31/3600,   # 263°35'31"
        'sun_altitude_deg': -(14 + 10/60 + 56/3600), # -14°10'56"
        'sun_azimuth_deg': 263 + 49/60 + 22/3600,    # 263°49'22"

        # Angular
        'arcv_deg': 14 + 5/60 + 33/3600,             # +14°05'33"
        'elongation_deg': 14 + 5/60 + 40/3600,       # +14°05'40"
        'daz_deg': -(0 + 13/60 + 51/3600),           # -00°13'51"
        'phase_angle_deg': 165 + 52/60 + 10/3600,    # +165°52'10"

        # Physical
        'crescent_width_deg': 0 + 0/60 + 29/3600,    # +00°00'29" = 0.483'
        'semi_diameter_deg': 0 + 15/60 + 43/3600,    # +00°15'43"
        'illumination_pct': 1.51,
        'horizontal_parallax_deg': 0 + 57/60 + 39/3600,  # +00°57'39"
        'magnitude': -5.39,
        'distance_km': 380305.76,

        # Visibility (Odeh at Best Time, Topocentric)
        'odeh_arcv_topo_deg': 12 + 51/60 + 0/3600,  # 12°51'00" = 12.85°
        'odeh_W_topo_arcmin': 0.40,
        'odeh_q_value': 8.08,
        'odeh_verdict': 'Easily Visible By Naked Eye',

        # Metadata
        'delta_t': 75.16,
        'julian_date': 2461890.14573,
    }
}


def time_to_seconds(time_str):
    """Convert HH:MM:SS to total seconds from midnight."""
    parts = time_str.split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])


def compare(name, computed, expected, tolerance, unit=''):
    """Compare a computed value against expected, with tolerance."""
    diff = abs(computed - expected)
    status = '✅' if diff <= tolerance else '❌'
    print(f"  {status} {name:<35s}  computed: {computed:>12.4f}  expected: {expected:>12.4f}  diff: {diff:.4f}{unit}  (tol: {tolerance})")
    return diff <= tolerance


def run_validation():
    """Run the full validation test against Accurate Times reference data."""
    print("=" * 80)
    print("VALIDATION TEST: Comparing against Accurate Times 5.7")
    print("Reference: Ramadan 1447 AH, Doha Qatar, Geocentric, Waxing Crescent")
    print("=" * 80)
    print()

    from astronomy import compute_all
    from crescent import evaluate_all_criteria

    loc = REFERENCE['location']
    settings = REFERENCE['settings']
    expected = REFERENCE['expected']

    # Run our calculations
    print("Running calculations...")
    result = compute_all(
        latitude=loc['latitude'],
        longitude=loc['longitude'],
        elevation=loc['elevation'],
        tz_offset=loc['timezone_offset'],
        date_year=2026, date_month=2, date_day=18,
        crescent_type=settings['crescent_type'],
        coordinate_mode=settings['coordinate_mode'],
        temperature_c=settings['temperature_c'],
        pressure_mb=settings['pressure_mb'],
        humidity_pct=settings['humidity_pct'],
        temp_lapse_rate=settings['temp_lapse_rate'],
    )

    visibility = evaluate_all_criteria(
        result['best_time_data'],
        result['best_time_data']['topo_elongation_deg'],
    )

    print("Done. Comparing results:\n")

    all_pass = True
    # Tolerances calibrated for cross-implementation comparison (DE440 vs Accurate Times)
    # Equatorial/ecliptic coordinates: tight (10 arcsec) — these are purely ephemeris-based
    tolerance_coord_deg = 10.0 / 3600.0   # 10 arcseconds
    # Horizontal coordinates: looser (90 arcsec) — sensitive to small timing differences
    tolerance_horiz_deg = 90.0 / 3600.0   # 90 arcseconds (1.5 arcminutes)
    # Timing: 10 seconds — accounts for different refraction/horizon models
    tolerance_time_sec = 10
    tolerance_km = 50

    # ── Timing ──
    print("TIMING:")

    # Sunset comparison
    from formatting import format_time_local
    sunset_str = format_time_local(result['timing']['sunset'], loc['timezone_offset'])
    computed_sunset_sec = time_to_seconds(sunset_str.replace(' LT', ''))
    expected_sunset_sec = time_to_seconds(expected['sunset_lt'])
    all_pass &= compare("Sunset", computed_sunset_sec, expected_sunset_sec, tolerance_time_sec, 's')

    # Moonset comparison
    moonset_str = format_time_local(result['timing']['moonset'], loc['timezone_offset'])
    computed_moonset_sec = time_to_seconds(moonset_str.replace(' LT', ''))
    expected_moonset_sec = time_to_seconds(expected['moonset_lt'])
    all_pass &= compare("Moonset", computed_moonset_sec, expected_moonset_sec, tolerance_time_sec, 's')

    # Moon age (compounds conjunction + moonset timing errors, so allow 2× tolerance)
    h, m, s = result['timing']['moon_age_hms']
    computed_age_sec = h * 3600 + m * 60 + s
    expected_age_sec = expected['moon_age_hours'] * 3600 + expected['moon_age_minutes'] * 60 + expected['moon_age_seconds']
    all_pass &= compare("Moon Age", computed_age_sec, expected_age_sec, tolerance_time_sec * 2, 's')

    # Lag time
    sign, h, m, s = result['timing']['lag_time_hms']
    computed_lag_sec = h * 3600 + m * 60 + s
    expected_lag_sec = expected['lag_hours'] * 3600 + expected['lag_minutes'] * 60 + expected['lag_seconds']
    all_pass &= compare("Lag Time", computed_lag_sec, expected_lag_sec, tolerance_time_sec, 's')

    # ── Equatorial ──
    print("\nEQUATORIAL COORDINATES:")
    all_pass &= compare("Moon RA (hours)", result['equatorial']['moon_ra_hours'], expected['moon_ra_hours'], 2.0/3600, 'h')
    all_pass &= compare("Moon Dec (deg)", result['equatorial']['moon_dec_degrees'], expected['moon_dec_degrees'], tolerance_coord_deg, '°')
    all_pass &= compare("Sun RA (hours)", result['equatorial']['sun_ra_hours'], expected['sun_ra_hours'], 2.0/3600, 'h')
    all_pass &= compare("Sun Dec (deg)", result['equatorial']['sun_dec_degrees'], expected['sun_dec_degrees'], tolerance_coord_deg, '°')

    # ── Ecliptic ──
    print("\nECLIPTIC COORDINATES:")
    all_pass &= compare("Moon Lon (deg)", result['ecliptic']['moon_lon_degrees'], expected['moon_lon_degrees'], tolerance_coord_deg, '°')
    all_pass &= compare("Moon Lat (deg)", result['ecliptic']['moon_lat_degrees'], expected['moon_lat_degrees'], tolerance_coord_deg, '°')
    all_pass &= compare("Sun Lon (deg)", result['ecliptic']['sun_lon_degrees'], expected['sun_lon_degrees'], tolerance_coord_deg, '°')

    # ── Horizontal ──
    print("\nHORIZONTAL COORDINATES (at moonset):")
    all_pass &= compare("Moon Altitude", result['horizontal']['moon_altitude_deg'], expected['moon_altitude_deg'], tolerance_horiz_deg, '°')
    all_pass &= compare("Moon Azimuth", result['horizontal']['moon_azimuth_deg'], expected['moon_azimuth_deg'], tolerance_horiz_deg, '°')
    all_pass &= compare("Sun Altitude", result['horizontal']['sun_altitude_deg'], expected['sun_altitude_deg'], tolerance_horiz_deg, '°')
    all_pass &= compare("Sun Azimuth", result['horizontal']['sun_azimuth_deg'], expected['sun_azimuth_deg'], tolerance_horiz_deg, '°')

    # ── Angular ──
    print("\nANGULAR PARAMETERS:")
    all_pass &= compare("ARCV", result['angular']['arcv_deg'], expected['arcv_deg'], tolerance_horiz_deg, '°')
    all_pass &= compare("Elongation (ARCL)", result['angular']['elongation_deg'], expected['elongation_deg'], tolerance_coord_deg, '°')
    all_pass &= compare("DAZ", result['angular']['daz_deg'], expected['daz_deg'], tolerance_horiz_deg, '°')
    all_pass &= compare("Phase Angle", result['angular']['phase_angle_deg'], expected['phase_angle_deg'], tolerance_coord_deg, '°')

    # ── Physical ──
    print("\nPHYSICAL PARAMETERS:")
    all_pass &= compare("Crescent Width", result['physical']['crescent_width_deg'], expected['crescent_width_deg'], tolerance_coord_deg, '°')
    all_pass &= compare("Semi-Diameter", result['physical']['semi_diameter_deg'], expected['semi_diameter_deg'], tolerance_coord_deg, '°')
    all_pass &= compare("Illumination %", result['physical']['illumination_pct'], expected['illumination_pct'], 0.1, '%')
    all_pass &= compare("H. Parallax", result['physical']['horizontal_parallax_deg'], expected['horizontal_parallax_deg'], tolerance_coord_deg, '°')
    all_pass &= compare("Distance (km)", result['physical']['distance_km'], expected['distance_km'], tolerance_km, 'km')

    # ── Visibility ──
    print("\nVISIBILITY CRITERIA (Odeh, at Best Time):")
    all_pass &= compare("T. ARCV at Best", result['best_time_data']['topo_arcv_deg'], expected['odeh_arcv_topo_deg'], 0.1, '°')
    all_pass &= compare("T. W at Best (arcmin)", result['best_time_data']['topo_crescent_width_arcmin'], expected['odeh_W_topo_arcmin'], 0.05, "'")
    all_pass &= compare("Odeh q value", visibility['odeh']['q_value'], expected['odeh_q_value'], 0.5, '')

    odeh_verdict_match = visibility['odeh']['verdict'] == expected['odeh_verdict']
    print(f"  {'✅' if odeh_verdict_match else '❌'} {'Odeh Verdict':<35s}  computed: {visibility['odeh']['verdict']}")
    print(f"     {'':35s}  expected: {expected['odeh_verdict']}")
    all_pass &= odeh_verdict_match

    # ── Summary ──
    print("\n" + "=" * 80)
    if all_pass:
        print("🎉 ALL TESTS PASSED! Output matches Accurate Times 5.7 within tolerance.")
    else:
        print("⚠️  SOME TESTS FAILED. Review the values above and adjust calculations.")
        print("   Note: Small differences may be due to:")
        print("   - Different Delta T values")
        print("   - Slightly different refraction models")
        print("   - Ephemeris version differences (DE440 vs whatever Accurate Times uses)")
        print("   - Geocentric alt/az calculation method differences")
    print("=" * 80)

    return all_pass


if __name__ == '__main__':
    success = run_validation()
    sys.exit(0 if success else 1)
