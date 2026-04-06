# Product Requirements Document — Hilal Moon App

**Version:** 1.0
**Date:** 2026-03-28
**Status:** Active Development

---

## 1. Project Overview

**Hilal** is a professional-grade crescent moon visibility calculator. It accepts an observer's geographic location and a calendar date, then returns a detailed astronomical analysis predicting whether the lunar crescent (hilal) will be visible from that location on that evening (or morning, for the waning crescent).

The backend replicates the output of **Accurate Times 5.7** by Mohammad Odeh — the de-facto reference software used by Islamic calendar authorities worldwide. Calculations are powered by the **JPL DE440 ephemeris** via Skyfield, giving sub-arcsecond positional accuracy across the years 1849–2150.

A companion **React + Vite** web frontend provides a browser-based UI for interactive queries.

---

## 2. Purpose and Motivation

Islamic jurisprudence ties the start of lunar months (Ramadan, Eid, Hajj, etc.) to the confirmed sighting of the crescent moon. Authorities and observatories need:

- Reliable predictions computed from accepted astronomical models
- Output that matches the tools they already trust (Accurate Times)
- A programmable API so the calculations can be embedded in mobile apps, websites, and decision-support tools

Hilal provides all three through a REST API and an interactive web UI.

---

## 3. Target Users / Personas

| Persona | Description | Primary Need |
|---|---|---|
| **Islamic Calendar Authority** | National moon-sighting committees, Islamic courts | Accurate nightly crescent predictions across multiple locations |
| **Astronomer / Researcher** | Academic studying lunar visibility models | Raw values, multi-criteria comparison, model validation |
| **Mosque / Community App Developer** | Building prayer-time or calendar apps | Programmable API returning structured JSON |
| **Hobbyist / Enthusiast** | Interested in moon sighting | Simple web UI to check a date and location |
| **Backend Developer / QA** | Validating integration | Postman / curl access to the API |

---

## 4. Core Features and Functional Requirements

### 4.1 Crescent Visibility Prediction API

**Endpoint:** `POST /api/v1/crescent-visibility`

The API accepts observer location + date and returns a full visibility analysis.

#### Input Parameters

| Field | Type | Description |
|---|---|---|
| `latitude` | float | Observer latitude (−90 to +90) |
| `longitude` | float | Observer longitude (−180 to +180) |
| `elevation` | float | Elevation above sea level in metres (default 0) |
| `timezone_offset` | float | UTC offset in hours (e.g. 3.0 for UTC+3) |
| `date` | string | Observation date in `YYYY-MM-DD` format |
| `coordinate_mode` | string | `"geocentric"` or `"topocentric"` |
| `location_name` | string | Optional display label for the location |
| `refraction.temperature_c` | float | Temperature in °C for atmospheric refraction (default 10) |
| `refraction.pressure_mb` | float | Pressure in mbar (default 1010) |
| `refraction.humidity_pct` | float | Humidity % (default 60) |
| `refraction.temp_lapse_rate` | float | Temperature lapse rate K/m (default 0.0065) |

#### Auto-Detection

- **Crescent type** (`waxing` / `waning`) is automatically determined by comparing the Moon's ecliptic longitude to the Sun's at noon on the observation date. It is never taken as user input.

#### Output Groups

| Group | Contents |
|---|---|
| **Metadata** | Crescent type, moon label (New/Old Moon), visibility date, coordinate mode, conjunction dates (new moon and next new moon), Delta T, Julian Date, location details |
| **Timing** | Conjunction time, sunset, moonset, sunrise, moonrise, moon age, lag time, best observation time |
| **Equatorial** | Moon and Sun Right Ascension and Declination |
| **Ecliptic** | Moon and Sun ecliptic longitude and latitude |
| **Horizontal** | Moon and Sun altitude and azimuth at the calculation time |
| **Angular** | ARCV (arc of vision), ARCL (elongation), DAZ (relative azimuth), phase angle |
| **Physical** | Crescent width, illumination %, semi-diameter, horizontal parallax, magnitude, distance (km) |
| **Visibility Criteria** | Verdicts from three independent models (see §4.2) |
| **Raw Values** | Full-precision decimal values for all angular/physical parameters |
| **Text Report** | Multi-line plain-text report formatted to match Accurate Times 5.7 output |

---

### 4.2 Visibility Criteria

All three criteria are evaluated at **sunset** (waxing crescent) or **sunrise** (waning crescent), not at "best time".

#### Odeh (2004 / 2006)
Uses topocentric ARCV and crescent width W (arcmin).
`V = ARCV − (−0.1018·W³ + 0.7319·W² − 6.3226·W + 7.1651)`

| Zone | Condition | Verdict |
|---|---|---|
| A | V ≥ 5.65 | Easily Visible By Naked Eye |
| B | 2.00 ≤ V < 5.65 | Could be Seen by Naked Eye |
| C | −0.96 ≤ V < 2.00 | Need Optical Aid |
| D | V < −0.96 | Not Visible Even by Optical Aid |

Danjon limit: elongation < 6.4° → automatically Zone D.

#### Yallop (1997)
Uses **geocentric** ARCV and topocentric crescent width.
`q = (ARCV − polynomial(W)) / 10`

| Zone | Condition | Verdict |
|---|---|---|
| A | q > 0.216 | Easily visible by naked eye |
| B | −0.014 < q ≤ 0.216 | Visible under perfect conditions |
| C | −0.160 < q ≤ −0.014 | May need optical aid |
| D | −0.232 < q ≤ −0.160 | Only visible with optical aid |
| E | −0.293 < q ≤ −0.232 | Below normal telescope detection |
| F | q ≤ −0.293 | Not visible (below Danjon limit) |

#### SAAO — Caldwell & Laney (2001)
Uses Moon altitude at sunset (DALT) compared to threshold altitudes (DALT1, DALT2) that vary with |DAZ| via linear interpolation from a reference table.

| |DAZ| | DALT1 | DALT2 |
|---|---|---|
| 0° | 6.3° | 8.2° |
| 5° | 5.9° | 7.8° |
| 10° | 4.9° | 6.8° |
| 15° | 3.8° | 5.7° |
| 20° | 2.6° | 4.5° |

| Zone | Condition | Verdict |
|---|---|---|
| Possible | DALT ≥ DALT2 | Naked eye visible |
| Improbable | DALT1 ≤ DALT < DALT2 | Optical aid only |
| Not Possible | DALT < DALT1 | Not visible |

---

### 4.3 Coordinate Modes

| Mode | Description |
|---|---|
| **Geocentric** | Positions calculated as if viewed from Earth's centre. No lunar parallax. Used to match Accurate Times geocentric output. |
| **Topocentric** | Positions corrected for the observer's actual location on Earth's surface. Accounts for lunar parallax (~1° shift). More physically accurate for a ground observer. |

The topocentric conjunction time may differ from the geocentric conjunction by up to ~1.5 hours.

---

### 4.4 Rise / Set Times

Sunset, sunrise, moonset, and moonrise are computed using Skyfield's almanac with:
- Atmospheric refraction correction (standard 34 arcminute refraction)
- Geometric horizon dip for elevated observers
- Upper-limb criterion (when the upper edge of the disc touches the horizon)

---

### 4.5 New Moon Context

Each response includes:
- **New Moon** — the most recent geocentric conjunction on or before the observation date
- **Next New Moon** — the first geocentric conjunction after the observation date

These allow the caller to know which lunar month the observation falls within.

---

### 4.6 Impossible Visibility Detection

The API flags geometrically impossible sighting scenarios:

- **Waxing:** Moonset before Sunset, or topocentric conjunction after Sunset
- **Waning:** Moonrise after Sunrise, or topocentric conjunction after Sunrise

When flagged, `visibility.impossible = true` and `visibility.impossible_reason` describes the cause.

---

### 4.7 Web Frontend

A React + Vite single-page application at `hilal-frontend/` provides:

- Form with fields for location name, date, timezone offset, latitude, longitude, elevation, and coordinate mode
- One-click calculation via the backend API (proxied through Vite dev server)
- Results display including:
  - Observation date and location
  - New Moon and Next New Moon dates
  - Visibility criterion cards (Odeh, Yallop, SAAO) with colour-coded zone badges
  - Timing table (sunset, moonset, sunrise, moonrise, moon age, lag time, best time, conjunction)
  - Angular and physical parameter tables
  - Horizontal coordinate table
  - Full Accurate Times–format text report

---

### 4.8 Health and Discovery Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Service metadata (name, version, description, reference) |
| `/health` | GET | Liveness check (`{"status": "ok"}`) |

---

## 5. Non-Functional Requirements

### 5.1 Accuracy

- Positional accuracy: sub-arcsecond (JPL DE440 ephemeris)
- Timing accuracy: within ±10 seconds of Accurate Times 5.7 reference output
- Coordinate accuracy: within ±10 arcseconds (equatorial/ecliptic), ±90 arcseconds (horizontal — more sensitive to timing precision)
- Validated against published Accurate Times 5.7 output for Ramadan 1447 AH (Doha, Qatar, February 2026)

### 5.2 Performance

- The JPL ephemeris (`de440s.bsp`, ~120 MB) is loaded **once** at module start to avoid repeated disk I/O
- A single API request completes in under 3 seconds on typical hardware (ephemeris lookups dominate)
- No database required; all computation is stateless and in-memory

### 5.3 Coverage

- Valid date range: 1849–2150 (DE440s ephemeris bounds)
- Valid locations: any point on Earth's surface (−90° to +90° latitude, −180° to +180° longitude)

### 5.4 Reliability

- A single well-defined entry point (`compute_all()`) processes all inputs
- All calculation errors are caught at the API layer and returned as HTTP 500 with a descriptive message
- Auto-detection of crescent type prevents an entire class of user input errors

### 5.5 Security

- CORS currently allows all origins (`allow_origins=["*"]`) — must be tightened before public deployment
- No authentication or rate limiting is implemented in the current version
- No user data is stored or logged
- The `.env` file and `.claude/` directory are excluded from version control via `.gitignore`

### 5.6 Maintainability

- Calculations are separated into focused modules: `astronomy.py` (physics), `crescent.py` (criteria), `formatting.py` (display)
- A validation suite (`test_validation.py`) guards against regressions in numerical output
- All functions are documented with docstrings explaining inputs, outputs, and design decisions
- The ephemeris file is excluded from the repository; the README documents how to obtain it

### 5.7 Portability

- Pure Python 3 with standard scientific libraries (Skyfield, NumPy, FastAPI, Pydantic)
- Runs on any platform with Python 3.10+ and the ephemeris file
- Frontend is a standard Vite/React SPA deployable to any static host

---

## 6. User Flows and Use Cases

### UC-1: Islamic Authority Checks Tonight's Crescent

1. Authority enters their city's coordinates, today's date, and local UTC offset
2. Submits the form (or sends a POST request)
3. System auto-detects crescent type (waxing, since it's near new moon)
4. System returns: sunset time, moonset time, moon age, lag time, and verdicts from all three criteria
5. Authority reads the Odeh zone (A = easily visible) and confirms the sighting is expected
6. Text report can be copy-pasted into official documentation

### UC-2: Developer Integrates API into a Calendar App

1. Developer sends a POST to `/api/v1/crescent-visibility` with location and date
2. API returns structured JSON with `visibility.odeh.zone`, `timing.sunset`, and `metadata.new_moon`
3. App displays the new moon date and a colour-coded visibility badge
4. App iterates over multiple cities in a loop for a global crescent map

### UC-3: Researcher Compares Criteria Across Models

1. Researcher queries the same date/location in both `geocentric` and `topocentric` modes
2. Compares Odeh zone (A–D), Yallop zone (A–F), and SAAO zone (Possible/Improbable/Not Possible)
3. Uses `raw_values` fields for precise decimal inputs to their own statistical analysis

### UC-4: Observer Checks a Waning (Old) Moon

1. Observer enters a date before the upcoming new moon
2. System auto-detects crescent type as `waning`
3. System returns: moonrise time, sunrise time, lag time (moonrise to sunrise)
4. Visibility criteria evaluated at sunrise, showing if the thin old crescent is observable

### UC-5: Authority Checks the New Moon Date for a Given Month

1. Authority enters any date in the target lunar month
2. Response `metadata.new_moon` shows the exact date/time of the conjunction
3. Response `metadata.next_new_moon` shows when the following month begins

---

## 7. Out-of-Scope Items

The following are **not** implemented and are outside the current scope:

| Item | Notes |
|---|---|
| **Authentication / user accounts** | No login, no session management, no API keys |
| **Rate limiting** | No throttling of requests |
| **Historical sighting records** | No database; no storage of past calculation results |
| **Global crescent maps** | No map rendering; callers must loop over locations themselves |
| **Prayer time calculation** | Only crescent visibility; Fajr/Dhuhr/Asr/Maghrib/Isha are not computed |
| **Qibla direction** | Not computed |
| **Islamic calendar date conversion** | No Hijri ↔ Gregorian conversion |
| **Push notifications / alerts** | No scheduling or notification system |
| **Multi-location batch API** | One location per request |
| **Cloudy-sky or weather data** | Purely astronomical; actual cloud cover is not factored in |
| **Naked-eye observer skill adjustment** | Criteria use published formulas; no personalised visibility modelling |
| **Ephemeris outside 1849–2150** | DE440s bounds; queries outside this range will fail |
| **Mobile native app** | Frontend is web-only; no iOS/Android native app |
| **Offline mode** | Both backend and frontend require a network connection |
| **Localisation / i18n** | UI and API responses are English-only |

---

## 8. Architecture Summary

```
Browser (React + Vite)
        │
        │  HTTP POST /api/v1/crescent-visibility
        ▼
FastAPI (main.py)
        │
        ├── models.py        — Request validation (Pydantic)
        ├── astronomy.py     — Positions, rise/set, conjunction, derived params (Skyfield + DE440)
        ├── crescent.py      — Odeh / Yallop / SAAO visibility criteria
        └── formatting.py    — DMS / time / report formatting (Accurate Times style)
```

---

## 9. References

- Odeh, M.Sh. (2004). *New Criterion for Lunar Crescent Visibility.* Experimental Astronomy, 18, 39–64.
- Yallop, B.D. (1997). *A Method for Predicting the First Sighting of the New Crescent Moon.* NAO Technical Note No. 69.
- Caldwell, J. & Laney, C. (2001). *First Visibility of the Lunar Crescent.* SAAO criterion.
- Odeh, M.Sh. (2006). *Accurate Times 5.7.* Islamic Crescents' Observation Project (ICOP).
- Folkner, W.M. et al. (2014). *The Planetary and Lunar Ephemerides DE430 and DE431.* JPL IPN Progress Report 42-196.
