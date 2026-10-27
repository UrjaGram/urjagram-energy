"""
Hourly village energy demand-supply balance.

Demand: households, streetlights, dairy chilling, drinking-water pump, agricultural pumps.
Supply, in dispatch order: solar -> battery -> biogas genset -> grid.
The grid serves the village feeder all day and the agricultural feeder only in its supply hours.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from . import config as C


@dataclass
class DayScenario:
    month: int
    solar_kwp: float = 0.0
    battery_kwh: float = 0.0
    biogas_genset_kw: float = 0.0
    biogas_energy_available_kwh: float = 0.0
    ag_pumping_hours: Sequence[int] = field(default_factory=lambda: [22, 23, 0, 1, 2, 3, 4, 5])
    ag_grid_hours: Sequence[int] = field(default_factory=lambda: [22, 23, 0, 1, 2, 3, 4, 5])
    village_outage_hours: Sequence[int] = field(default_factory=list)
    ag_pumps_active: int = 42
    extra_load_kw_by_hour: Dict[int, float] = field(default_factory=dict)  # e.g. EV charging


def solar_generation_kwh_by_hour(month: int, solar_kwp: float) -> List[float]:
    """Spread the daily yield over the daylight hours with a half-sine shape."""
    import math

    daily = C.SOLAR_YIELD_KWH_PER_KWP_PER_DAY[month] * solar_kwp
    hours = range(C.SUNRISE_HOUR, C.SUNSET_HOUR)
    span = C.SUNSET_HOUR - C.SUNRISE_HOUR
    shape = {h: math.sin(math.pi * (h + 0.5 - C.SUNRISE_HOUR) / span) for h in hours}
    total = sum(shape.values())
    return [daily * shape[h] / total if h in shape else 0.0 for h in range(24)]


def household_kwh_by_hour(households: int, kwh_per_household_per_day: float) -> List[float]:
    total = sum(C.HOUSEHOLD_HOURLY_SHAPE)
    daily = households * kwh_per_household_per_day
    return [daily * s / total for s in C.HOUSEHOLD_HOURLY_SHAPE]


def fixed_load_kwh_by_hour(baseline: Dict[str, Any]) -> Dict[str, List[float]]:
    """Non-agricultural loads per hour (kWh in that hour = kW over one hour)."""
    streetlight_kw = baseline["streetlights"]["count"] * baseline["streetlights"]["watts_each"] / 1000.0
    dairy = baseline["dairy"]
    dairy_daily = dairy["milk_litres_per_day"] * dairy["chilling_kwh_per_litre"]
    dw = baseline["drinking_water"]
    return {
        "households": household_kwh_by_hour(baseline["households"], baseline["household_kwh_per_day"]),
        "streetlights": [streetlight_kw if h in C.STREETLIGHT_HOURS else 0.0 for h in range(24)],
        "dairy_chilling": [dairy_daily / 24.0] * 24,
        "drinking_water_pump": [dw["village_borewell_kw"] if h in dw["run_hours"] else 0.0 for h in range(24)],
    }


def pump_input_kw(pump_hp: float) -> float:
    return pump_hp * C.HP_TO_KW / C.PUMP_MOTOR_EFFICIENCY


def simulate_day(baseline: Dict[str, Any], scenario: DayScenario) -> Dict[str, Any]:
    fixed = fixed_load_kwh_by_hour(baseline)
    solar = solar_generation_kwh_by_hour(scenario.month, scenario.solar_kwp)
    ag_kw_each = pump_input_kw(baseline["agriculture"]["pump_hp"])
    ag_hours = set(scenario.ag_pumping_hours)
    ag_grid = set(scenario.ag_grid_hours)
    outage = set(scenario.village_outage_hours)

    capacity = scenario.battery_kwh
    soc = capacity * C.BATTERY_MIN_SOC_FRACTION  # start the day at the reserve floor
    eta = C.BATTERY_ROUND_TRIP_EFFICIENCY ** 0.5
    biogas_left = scenario.biogas_energy_available_kwh

    rows = []
    totals = {k: 0.0 for k in (
        "demand_kwh", "ag_demand_kwh", "ag_served_kwh", "solar_used_kwh", "battery_discharge_kwh",
        "biogas_used_kwh", "grid_import_kwh", "unmet_kwh", "curtailed_kwh", "evening_peak_grid_kwh",
    )}
    sector_totals = {k: 0.0 for k in fixed}
    sector_totals["agricultural_pumps"] = 0.0
    sector_totals["extra_loads"] = 0.0
    peak_grid_kw = 0.0

    for h in range(24):
        dom = sum(fixed[k][h] for k in fixed)
        ag = ag_kw_each * scenario.ag_pumps_active if h in ag_hours else 0.0
        extra = scenario.extra_load_kw_by_hour.get(h, 0.0)
        demand = dom + ag + extra
        for k in fixed:
            sector_totals[k] += fixed[k][h]
        sector_totals["agricultural_pumps"] += ag
        sector_totals["extra_loads"] += extra

        village_grid_on = h not in outage
        ag_grid_on = village_grid_on and h in ag_grid

        floor = capacity * C.BATTERY_MIN_SOC_FRACTION
        pool = {
            "solar": solar[h],
            "battery": max(0.0, (soc - floor) * eta) if capacity > 0 else 0.0,
            "biogas": min(scenario.biogas_genset_kw, biogas_left) if scenario.biogas_genset_kw > 0 else 0.0,
        }

        def serve(load, grid_on):
            """Take `load` kWh from solar, battery, biogas in that order, then grid if its feeder is on."""
            got = {}
            need = load
            for src in ("solar", "battery", "biogas"):
                take = min(need, pool[src])
                pool[src] -= take
                need -= take
                got[src] = take
            got["grid"] = need if grid_on else 0.0
            got["unmet"] = 0.0 if grid_on else need
            return got

        dom_got = serve(dom + extra, village_grid_on)   # households first
        ag_got = serve(ag, ag_grid_on)                  # then agricultural pumps
        solar_used = dom_got["solar"] + ag_got["solar"]
        discharge = dom_got["battery"] + ag_got["battery"]
        biogas = dom_got["biogas"] + ag_got["biogas"]
        grid = dom_got["grid"] + ag_got["grid"]
        unmet = dom_got["unmet"] + ag_got["unmet"]
        ag_served = ag - ag_got["unmet"]

        soc -= discharge / eta if capacity > 0 else 0.0
        biogas_left -= biogas
        surplus = pool["solar"]
        curtailed = surplus
        if surplus > 0 and capacity > 0:
            charged = min(surplus * eta, capacity - soc)
            soc += charged
            curtailed = surplus - charged / eta

        rows.append({
            "hour": h, "demand_kwh": round(demand, 3), "ag_demand_kwh": round(ag, 3),
            "solar_kwh": round(solar[h], 3), "solar_used_kwh": round(solar_used, 3),
            "battery_discharge_kwh": round(discharge, 3), "biogas_kwh": round(biogas, 3),
            "grid_import_kwh": round(grid, 3), "unmet_kwh": round(unmet, 3),
            "curtailed_kwh": round(curtailed, 3), "battery_soc_kwh": round(soc, 3),
        })
        totals["demand_kwh"] += demand
        totals["ag_demand_kwh"] += ag
        totals["ag_served_kwh"] += ag_served
        totals["solar_used_kwh"] += solar_used
        totals["battery_discharge_kwh"] += discharge
        totals["biogas_used_kwh"] += biogas
        totals["grid_import_kwh"] += grid
        totals["unmet_kwh"] += unmet
        totals["curtailed_kwh"] += curtailed
        if 18 <= h < 22:
            totals["evening_peak_grid_kwh"] += grid
        peak_grid_kw = max(peak_grid_kw, grid)

    demand = totals["demand_kwh"]
    summary = {k: round(v, 2) for k, v in totals.items()}
    summary["peak_grid_kw"] = round(peak_grid_kw, 2)
    summary["solar_share_of_demand"] = round(totals["solar_used_kwh"] / demand, 4) if demand else 0.0
    summary["unmet_fraction_of_demand"] = round(totals["unmet_kwh"] / demand, 4) if demand else 0.0
    summary["ag_unmet_fraction"] = (
        round(1.0 - totals["ag_served_kwh"] / totals["ag_demand_kwh"], 4) if totals["ag_demand_kwh"] else 0.0
    )
    return {
        "hourly": rows,
        "summary": summary,
        "sector_kwh_per_day": {k: round(v, 2) for k, v in sector_totals.items()},
    }
