"""
Crescent visibility criteria: Odeh, Yallop, and SAAO.

Implements the three visibility prediction models as used in
Accurate Times 5.7 by Mohammad Odeh.

References:
- Odeh, M.Sh. (2004). "New Criterion for Lunar Crescent Visibility."
  Experimental Astronomy, 18, 39-64.
- Yallop, B.D. (1997). "A Method for Predicting the First Sighting
  of the New Crescent Moon." NAO Technical Note No. 69.
- Caldwell, J. & Laney, C. (2001). "First Visibility of the Lunar Crescent."
  SAAO criterion.
"""


def _visibility_polynomial(W):
    """
    Common polynomial used by both Odeh and Yallop criteria.

    This cubic polynomial in W (crescent width in arcminutes) represents
    the minimum ARCV needed to see the crescent.

    ARCV_min = -0.1018 × W³ + 0.7319 × W² - 6.3226 × W + 7.1651

    Args:
        W: Crescent width in arcminutes

    Returns:
        Minimum ARCV threshold in degrees
    """
    return (-0.1018 * W**3 + 0.7319 * W**2 - 6.3226 * W + 7.1651)


def odeh_criterion(arcv_topo_deg, W_topo_arcmin, elongation_topo_deg):
    """
    Apply the Odeh (2004/2006) crescent visibility criterion.

    Uses TOPOCENTRIC ARCV and TOPOCENTRIC crescent width at Best Time.

    V = ARCV - polynomial(W)

    Zones:
        A: V >= 5.65  → Easily Visible By Naked Eye
        B: 2.00 <= V < 5.65 → Could be Seen by Naked Eye
        C: -0.96 <= V < 2.00 → Need Optical Aid
        D: V < -0.96 → Not Visible Even by Optical Aid

    Also checks Danjon limit: if ARCL < 6.4°, crescent cannot be seen.

    Args:
        arcv_topo_deg: Topocentric ARCV at Best Time (degrees)
        W_topo_arcmin: Topocentric crescent width at Best Time (arcminutes)
        elongation_topo_deg: Topocentric elongation at Best Time (degrees)

    Returns:
        dict with q_value, zone, verdict, description
    """
    # Check Danjon limit first
    if elongation_topo_deg < 6.4:
        return {
            'q_value': None,
            'zone': 'D',
            'verdict': 'Not Visible',
            'description': 'Below Danjon limit (elongation < 6.4°)',
            'danjon_limit': True,
        }

    # Compute V (called q in Accurate Times output for Odeh)
    V = arcv_topo_deg - _visibility_polynomial(W_topo_arcmin)
    V = round(V, 2)

    if V >= 5.65:
        zone = 'A'
        verdict = 'Easily Visible By Naked Eye'
    elif V >= 2.00:
        zone = 'B'
        verdict = 'Could be Seen by Naked Eye'
    elif V >= -0.96:
        zone = 'C'
        verdict = 'Need Optical Aid'
    else:
        zone = 'D'
        verdict = 'Not Visible Even by Optical Aid'

    return {
        'q_value': V,
        'zone': zone,
        'verdict': verdict,
        'description': f'Zone {zone}: {verdict}',
        'danjon_limit': False,
    }


def yallop_criterion(arcv_geo_deg, W_topo_arcmin, elongation_deg):
    """
    Apply the Yallop (1997) crescent visibility criterion.

    Uses GEOCENTRIC ARCV at Best Time and TOPOCENTRIC crescent width.
    The q value is divided by 10 (Yallop convention) to keep it
    between approximately -1 and +1.

    q = (ARCV - polynomial(W)) / 10

    Zones:
        A: q > 0.216  → Easily visible by naked eye
        B: -0.014 < q <= 0.216 → Visible under perfect conditions
        C: -0.160 < q <= -0.014 → May need optical aid
        D: -0.232 < q <= -0.160 → Only visible with optical aid
        E: -0.293 < q <= -0.232 → Below normal telescope detection
        F: q <= -0.293 → Not visible (below Danjon limit)

    Args:
        arcv_geo_deg: Geocentric ARCV at Best Time (degrees)
        W_topo_arcmin: Topocentric crescent width at Best Time (arcminutes)
        elongation_deg: Elongation at Best Time (degrees)

    Returns:
        dict with q_value, zone, verdict
    """
    # Check if elongation is below Danjon limit
    if elongation_deg < 7.0:  # Yallop uses ~7° as rough Danjon limit
        return {
            'q_value': None,
            'zone': 'F',
            'verdict': 'Not visible, below Danjon limit',
            'description': 'Zone F: Below Danjon limit',
        }

    q = (arcv_geo_deg - _visibility_polynomial(W_topo_arcmin)) / 10.0
    q = round(q, 3)

    if q > 0.216:
        zone = 'A'
        verdict = 'Easily visible by naked eye'
    elif q > -0.014:
        zone = 'B'
        verdict = 'Visible under perfect conditions'
    elif q > -0.160:
        zone = 'C'
        verdict = 'May need optical aid to find crescent'
    elif q > -0.232:
        zone = 'D'
        verdict = 'Only visible with optical aid'
    elif q > -0.293:
        zone = 'E'
        verdict = 'Below normal telescope detection limit'
    else:
        zone = 'F'
        verdict = 'Not visible (below Danjon limit)'

    return {
        'q_value': q,
        'zone': zone,
        'verdict': verdict,
        'description': f'Zone {zone}: {verdict}',
    }


def saao_criterion(arcv_topo_deg, W_topo_arcmin, daz_topo_deg,
                    moon_alt_topo_deg, elongation_topo_deg):
    """
    Apply the SAAO (South African Astronomical Observatory) criterion.

    Based on Caldwell & Laney (2001). Uses a combination of Moon altitude
    and other parameters. Simplified two-zone classification.

    The SAAO criterion is less formally published than Odeh/Yallop.
    In Accurate Times, it provides two zones:
        Possible (Green): Crescent is visible by naked eye
        Improbable (Blue): Exceedingly unlikely without telescope

    This implementation follows the general SAAO approach as referenced
    in the Accurate Times documentation.

    Args:
        arcv_topo_deg: Topocentric ARCV (degrees)
        W_topo_arcmin: Topocentric crescent width (arcminutes)
        daz_topo_deg: Topocentric DAZ (degrees, absolute value used)
        moon_alt_topo_deg: Topocentric Moon altitude at sunset (degrees)
        elongation_topo_deg: Topocentric elongation (degrees)

    Returns:
        dict with zone and verdict
    """
    # Danjon limit check
    if elongation_topo_deg < 6.4:
        return {
            'zone': 'Not Possible',
            'verdict': 'Below Danjon limit',
        }

    # SAAO uses a simpler criterion based on the visibility parameters
    # The exact threshold varies in literature; this follows the common
    # implementation where visibility depends on ARCV and W combination
    # Similar to Odeh but with different thresholds

    # Approximate SAAO boundary:
    # If the Odeh V >= -0.96 (zone C or better), SAAO says "Possible"
    # Otherwise "Improbable"
    V = arcv_topo_deg - _visibility_polynomial(W_topo_arcmin)

    if V >= -0.96:
        return {
            'zone': 'Possible',
            'verdict': 'Crescent is visible by naked eye',
        }
    else:
        return {
            'zone': 'Improbable',
            'verdict': 'Seeing the crescent without telescope is exceedingly unlikely',
        }


def evaluate_all_criteria(best_time_data, elongation_topo_deg,
                          daz_topo_deg=0.0, moon_alt_topo_deg=0.0):
    """
    Evaluate all three visibility criteria.

    Args:
        best_time_data: Dict from compute_all() containing:
            - topo_arcv_deg: Topocentric ARCV at Best Time
            - topo_crescent_width_arcmin: Topocentric W at Best Time (arcmin)
            - geo_arcv_deg: Geocentric ARCV at Best Time
            - topo_elongation_deg: Topocentric elongation at Best Time
        elongation_topo_deg: Topocentric elongation (degrees)
        daz_topo_deg: Topocentric DAZ (degrees) for SAAO
        moon_alt_topo_deg: Topocentric Moon altitude for SAAO

    Returns:
        dict with odeh, yallop, saao results
    """
    arcv_topo = best_time_data['topo_arcv_deg']
    W_arcmin = best_time_data['topo_crescent_width_arcmin']
    arcv_geo = best_time_data['geo_arcv_deg']
    elong_topo = best_time_data['topo_elongation_deg']

    return {
        'odeh': odeh_criterion(arcv_topo, W_arcmin, elong_topo),
        'yallop': yallop_criterion(arcv_geo, W_arcmin, elong_topo),
        'saao': saao_criterion(arcv_topo, W_arcmin, daz_topo_deg,
                               moon_alt_topo_deg, elong_topo),
    }
