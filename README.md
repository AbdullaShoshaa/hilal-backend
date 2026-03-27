# Hilal Moon App — Backend

Professional-grade crescent moon visibility calculator matching Accurate Times 5.7 by Mohammad Odeh.

## Quick Start

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download JPL ephemeris (first run only — ~120MB)
python -c "from skyfield.api import load; load('de440s.bsp')"

# 4. Run the validation test
python test_validation.py

# 5. Start the API server
uvicorn main:app --reload --port 8000
```

## API Usage

```bash
curl -X POST http://localhost:8000/api/v1/crescent-visibility \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 25.284167,
    "longitude": 51.407222,
    "elevation": 40.0,
    "timezone_offset": 3.0,
    "date": "2026-02-18",
    "crescent_type": "waxing",
    "coordinate_mode": "geocentric"
  }'
```

## Project Structure

```
hilal-backend/
├── requirements.txt
├── README.md
├── main.py              # FastAPI app & endpoints
├── astronomy.py         # Core astronomical calculations (Skyfield)
├── crescent.py          # Crescent visibility criteria (Odeh/Yallop/SAAO)
├── models.py            # Pydantic request/response models
├── formatting.py        # DMS formatting to match Accurate Times output
├── test_validation.py   # Validation against Accurate Times reference data
└── de440s.bsp           # JPL ephemeris data file (not in repo — download via step 3)
```

## Validation

The test suite compares all output values against known Accurate Times 5.7 output
for Ramadan 1447 AH (18 Feb 2026), Doha Qatar. Acceptable tolerance:
- Positions: typically around ±10 arcseconds (equatorial/ecliptic) and up to ±90 arcseconds for horizontal values
- Times: ±10 seconds (Moon age can allow up to ±20 seconds)
- q-value: ±0.5
