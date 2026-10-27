"""
End-to-end energy pipeline:
baseline data -> hourly balance (as scheduled vs shifted to solar) -> Jev level + hard rules
-> pump schedule action -> decision log -> NetZero stream.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from . import config as C
from .energy_balance import DayScenario, simulate_day
from .jev_engine import (
    AlertLevel, allowed_pump_hours, classify_status, enforce_hard_rules, log_decision,
)
from .netzero_emitter import build_stream
from .transport import ev_charging_profile_kw, ev_shift_scenario, fleet_fuel_use

SOLAR_WINDOW = [9, 10, 11, 12, 13, 14, 15, 16]  # 09:00-17:00, 8 pump hours


def _load(data_dir: Path, name: str) -> Dict[str, Any]:
    with open(data_dir / name, "r", encoding="utf-8") as f:
        return json.load(f)


def biogas_potential(baseline: Dict[str, Any]) -> Dict[str, float]:
    lv = baseline["livestock"]
    dung_t = lv["dung_tractor_loads_per_year"] * lv["tonnes_fresh_dung_per_load"] * lv["collectable_fraction"]
    m3 = dung_t * lv["biogas_m3_per_tonne_fresh_dung"]
    return {
        "collectable_dung_tonnes_per_year": round(dung_t, 1),
        "biogas_m3_per_year": round(m3, 1),
        "electric_kwh_per_year": round(m3 * lv["kwh_electric_per_m3_biogas"], 1),
        "lpg_displaced_kg_per_year": round(m3 * lv["kg_lpg_displaced_per_m3_biogas"], 1),
    }


def run_assessment(
    month: int = 11,
    solar_kwp: Optional[float] = None,
    battery_kwh: Optional[float] = None,
    grid_hours_available_today: Optional[float] = None,
    water_alert: str = "LEVEL_0_NORMAL",
    ev_shift: Optional[Dict[str, float]] = None,
    data_dir: Optional[Path] = None,
    log_path: Optional[Path] = None,
    write_log: bool = True,
) -> Dict[str, Any]:
    data_dir = data_dir or C.DATA_DIR
    baseline = _load(data_dir, "katlabodi_energy_baseline.json")
    fleet = _load(data_dir, "transport_fleet.json")
    farmer = _load(data_dir, "partner_farmer.json")

    solar_kwp = baseline["installed"]["solar_kwp"] if solar_kwp is None else solar_kwp
    battery_kwh = baseline["installed"]["battery_kwh"] if battery_kwh is None else battery_kwh
    ag = baseline["agriculture"]
    required_hours = ag["required_pump_hours_per_day"]
    grid_hours = ag["grid_supply_hours"]
    available_today = float(len(grid_hours)) if grid_hours_available_today is None else grid_hours_available_today

    # Transport / EV
    transport_use = fleet_fuel_use(fleet)
    ev = ev_shift_scenario(fleet, ev_shift) if ev_shift else None
    extra = ev_charging_profile_kw(ev["charging_kwh_per_day"]) if ev else {}

    # If the grid has fewer hours today, the feeder only supplies the first hours of its normal window.
    todays_grid_hours = list(grid_hours)[: int(available_today)]
    bio = biogas_potential(baseline)

    common = dict(month=month, solar_kwp=solar_kwp, battery_kwh=battery_kwh,
                  ag_pumps_active=ag["borewells_count"], extra_load_kw_by_hour=extra)
    as_scheduled = simulate_day(baseline, DayScenario(
        ag_pumping_hours=grid_hours, ag_grid_hours=todays_grid_hours, **common))
    shifted = simulate_day(baseline, DayScenario(
        ag_pumping_hours=SOLAR_WINDOW, ag_grid_hours=todays_grid_hours, **common))

    solar_window_available = solar_kwp > 0
    # Jev decides on the as-scheduled case; hard rules can only raise the level.
    deficit = max(0.0, required_hours - available_today)
    # Judge on the best feasible schedule: shifting to the solar window is only an option if solar exists.
    unmet = as_scheduled["summary"]["ag_unmet_fraction"]
    if solar_kwp > 0:
        unmet = min(unmet, shifted["summary"]["ag_unmet_fraction"])
    jev_level = classify_status(unmet, deficit, water_alert)
    final_level, directive, rule_note = enforce_hard_rules(
        jev_level, available_today, required_hours, solar_window_available)
    pump_hours = allowed_pump_hours(required_hours, water_alert, directive)

    chosen = shifted if directive.value.startswith("SHIFT") else as_scheduled
    now = datetime.now(timezone.utc).isoformat()
    action = {
        "type": "pump_schedule",
        "recipient": "Gram Panchayat and farmer " + farmer["farmer_code"],
        "ag_pumping_hours_allowed_per_day": pump_hours,
        "pumping_window": "09:00-17:00" if directive.value.startswith("SHIFT") else (
            "{:02d}:00-{:02d}:00".format(grid_hours[0], (grid_hours[-1] + 1) % 24) if grid_hours else "none"),
        "directive": directive.value,
    }

    result = {
        "village_id": C.VILLAGE_ID,
        "village_name": C.VILLAGE_NAME,
        "timestamp": now,
        "inputs": {
            "month": month, "solar_kwp": solar_kwp, "battery_kwh": battery_kwh,
            "grid_hours_available_today": available_today, "required_pump_hours": required_hours,
            "water_alert": water_alert,
        },
        "status_code": final_level.value,
        "jev_level_before_hard_rules": jev_level.value,
        "guardrail_status": rule_note,
        "action": action,
        "balance_as_scheduled": as_scheduled["summary"],
        "balance_shifted_to_solar_window": shifted["summary"],
        "sector_kwh_per_day": as_scheduled["sector_kwh_per_day"],
        "transport": transport_use,
        "ev_scenario": ev,
        "biogas_potential": bio,
        "netzero_stream": build_stream(
            chosen, baseline, transport_use, ev,
            biogas_kwh_per_year=0.0,  # potential only; credited once a biogas genset is installed
            lpg_displaced_kg_per_year=0.0, timestamp=now),
    }
    if write_log:
        log_decision({
            "village_id": C.VILLAGE_ID, "inputs": result["inputs"],
            "jev_level": jev_level.value, "final_level": final_level.value,
            "directive": directive.value, "rule_note": rule_note, "action": action,
        }, log_path)
    return result
