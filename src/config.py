"""
Configuration and constants for UrjaGram Energy (village energy balance + transport).
Follows the UrjaGram platform conventions:
- metric units stated in every field name
- hard safety thresholds set in code
- emission factors with sources
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

# Village identification (same identifiers as the water module so data joins cleanly)
VILLAGE_ID = "IN-MH-NAG-KATLABODI"
VILLAGE_NAME = "Katlabodi"
LATITUDE = 21.2833
LONGITUDE = 78.5833

HP_TO_KW = 0.7457

# Emission factors (kg CO2e per unit)
# Grid: CEA CO2 Baseline Database for the Indian Power Sector (national average, ~0.82 kg/kWh,
# same value the water module uses, so both modules reconcile in the NetZero account).
CEA_GRID_EMISSION_FACTOR_KG_PER_KWH = 0.82
# Fuels: IPCC 2006 Guidelines, Vol 2 Energy (combustion CO2 per litre; CH4/N2O ignored).
DIESEL_EMISSION_FACTOR_KG_PER_L = 2.68
PETROL_EMISSION_FACTOR_KG_PER_L = 2.31
LPG_EMISSION_FACTOR_KG_PER_KG = 2.98

# Indicative solar yield for Nagpur by month, kWh per kWp per day (system-level, incl. losses).
# ASSUMPTION: replace with PVGIS / NASA POWER values for the village coordinates.
SOLAR_YIELD_KWH_PER_KWP_PER_DAY = {
    1: 4.8, 2: 5.4, 3: 5.8, 4: 6.0, 5: 5.9, 6: 4.4,
    7: 3.6, 8: 3.7, 9: 4.4, 10: 5.0, 11: 4.8, 12: 4.6,
}
SUNRISE_HOUR = 6
SUNSET_HOUR = 18  # solar hours are [6, 18)

# Battery
BATTERY_ROUND_TRIP_EFFICIENCY = 0.90
BATTERY_MIN_SOC_FRACTION = 0.20

# Pump motor: electrical input kW = rated HP * 0.7457 / efficiency.
# Default 1.0 keeps the same kWh as the water module (HP * 0.7457) so the two reconcile.
# Set to ~0.85 once pump nameplate / meter readings are collected.
PUMP_MOTOR_EFFICIENCY = 1.0

# Hourly shape of non-pump demand (relative; normalised in code). Index = hour of day.
HOUSEHOLD_HOURLY_SHAPE = [
    0.020, 0.015, 0.015, 0.015, 0.020, 0.040, 0.060, 0.050, 0.035, 0.030, 0.030, 0.030,
    0.035, 0.035, 0.030, 0.030, 0.035, 0.050, 0.090, 0.110, 0.095, 0.070, 0.040, 0.030,
]
STREETLIGHT_HOURS = [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5]

# Operating days per year used to annualise a representative day
AG_PUMPING_DAYS_PER_YEAR = 150   # same as water module
DOMESTIC_DAYS_PER_YEAR = 365

# --- Hard safety rules (Jev may raise an alert level, never lower it) ---
# Drinking-water pump must always be able to run: if no grid hour is available the level is EMERGENCY.
MIN_GRID_HOURS_FRACTION_FOR_WARNING = 0.5   # < 50% of required pumping hours => at least WARNING
# Water-module alert -> maximum agricultural pumping hours per day (water module owns this rule).
WATER_ALERT_PUMP_HOURS_CAP = {
    "LEVEL_0_NORMAL": 24.0,
    "LEVEL_1_ADVISORY": 24.0,
    "LEVEL_2_WARNING": 4.0,
    "LEVEL_3_EMERGENCY": 0.0,
}
