"""
Village transport: fuel use, emissions and an electric-vehicle shift scenario.
"""

from typing import Any, Dict, List, Optional

from . import config as C

_FUEL_FACTOR = {"diesel": C.DIESEL_EMISSION_FACTOR_KG_PER_L, "petrol": C.PETROL_EMISSION_FACTOR_KG_PER_L}


def _litres_per_year(v: Dict[str, Any]) -> float:
    days = v["operating_days_per_year"]
    if "litres_per_day" in v:
        per_vehicle = v["litres_per_day"] * days
    else:
        per_vehicle = v["km_per_day"] / v["km_per_litre"] * days
    return per_vehicle * v["count"]


def fleet_fuel_use(fleet: Dict[str, Any]) -> Dict[str, Any]:
    by_class = []
    for v in fleet["vehicles"]:
        litres = _litres_per_year(v)
        by_class.append({
            "vehicle_class": v["class"],
            "count": v["count"],
            "fuel": v["fuel"],
            "fuel_litres_per_year": round(litres, 1),
            "emissions_tco2e_per_year": round(litres * _FUEL_FACTOR[v["fuel"]] / 1000.0, 3),
        })
    return {
        "by_class": by_class,
        "total_fuel_litres_per_year": round(sum(c["fuel_litres_per_year"] for c in by_class), 1),
        "total_emissions_tco2e_per_year": round(sum(c["emissions_tco2e_per_year"] for c in by_class), 3),
    }


def ev_shift_scenario(
    fleet: Dict[str, Any],
    shift_share: Dict[str, float],
    grid_emission_factor_kg_per_kwh: float = C.CEA_GRID_EMISSION_FACTOR_KG_PER_KWH,
    solar_charging_fraction: float = 0.0,
) -> Dict[str, Any]:
    """shift_share maps vehicle class -> fraction (0..1) switched to electric. Tractors cannot be shifted here."""
    fuel_saved_l = {"diesel": 0.0, "petrol": 0.0}
    charging_kwh_year = 0.0
    avoided_t = 0.0
    shifted: List[Dict[str, Any]] = []
    for v in fleet["vehicles"]:
        share = shift_share.get(v["class"], 0.0)
        if share <= 0 or not v.get("electrifiable"):
            continue
        share = min(share, 1.0)
        n = v["count"] * share
        litres = _litres_per_year({**v, "count": n})
        km = v["km_per_day"] * v["operating_days_per_year"] * n
        kwh = km * v["ev_kwh_per_km"]
        fuel_saved_l[v["fuel"]] += litres
        charging_kwh_year += kwh
        avoided_t += litres * _FUEL_FACTOR[v["fuel"]] / 1000.0
        shifted.append({"vehicle_class": v["class"], "vehicles_shifted": round(n, 1),
                        "fuel_saved_litres_per_year": round(litres, 1), "charging_kwh_per_year": round(kwh, 1)})
    added_t = charging_kwh_year * (1.0 - solar_charging_fraction) * grid_emission_factor_kg_per_kwh / 1000.0
    return {
        "shifted": shifted,
        "fuel_saved_litres_per_year": {k: round(v, 1) for k, v in fuel_saved_l.items()},
        "charging_kwh_per_year": round(charging_kwh_year, 1),
        "charging_kwh_per_day": round(charging_kwh_year / 365.0, 2),
        "avoided_fuel_tco2e_per_year": round(avoided_t, 3),
        "added_grid_tco2e_per_year": round(added_t, 3),
        "net_reduction_tco2e_per_year": round(avoided_t - added_t, 3),
    }


def ev_charging_profile_kw(charging_kwh_per_day: float, charge_hours: Optional[List[int]] = None) -> Dict[int, float]:
    """Spread daily charging evenly over chosen hours (default: solar midday window)."""
    hours = charge_hours or [10, 11, 12, 13, 14, 15]
    return {h: charging_kwh_per_day / len(hours) for h in hours}
