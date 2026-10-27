"""
NetZero stream for the energy module: Scope 2 electricity, Scope 1 transport fuel and avoided emissions,
all in tonnes CO2e per year, for the NetZero account (Raj).

Boundary (to be agreed with the water module at the weekly review): this module reports ALL grid electricity,
including agricultural pumping. The water module should report water metrics only, so pumping is not counted twice.
"""

from typing import Any, Dict, Optional

from . import config as C


def build_stream(
    day: Dict[str, Any],
    baseline: Dict[str, Any],
    transport_use: Dict[str, Any],
    ev: Optional[Dict[str, Any]] = None,
    biogas_kwh_per_year: float = 0.0,
    lpg_displaced_kg_per_year: float = 0.0,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    ef = C.CEA_GRID_EMISSION_FACTOR_KG_PER_KWH
    sector = day["sector_kwh_per_day"]
    s = day["summary"]

    # Annualise: agricultural pumps run AG_PUMPING_DAYS_PER_YEAR, everything else every day.
    ag_share_grid = s["grid_import_kwh"] * (
        sector["agricultural_pumps"] / s["demand_kwh"] if s["demand_kwh"] else 0.0
    )
    non_ag_grid = s["grid_import_kwh"] - ag_share_grid
    grid_kwh_year = non_ag_grid * C.DOMESTIC_DAYS_PER_YEAR + ag_share_grid * C.AG_PUMPING_DAYS_PER_YEAR
    solar_kwh_year = s["solar_used_kwh"] * C.DOMESTIC_DAYS_PER_YEAR  # upper bound: ag days are a subset
    scope2_t = grid_kwh_year * ef / 1000.0
    avoided_solar_t = solar_kwh_year * ef / 1000.0
    avoided_biogas_t = (biogas_kwh_per_year * ef + lpg_displaced_kg_per_year * C.LPG_EMISSION_FACTOR_KG_PER_KG) / 1000.0
    scope1_t = transport_use["total_emissions_tco2e_per_year"]

    ev_net = ev["net_reduction_tco2e_per_year"] if ev else 0.0
    return {
        "village_id": C.VILLAGE_ID,
        "location": {"latitude": C.LATITUDE, "longitude": C.LONGITUDE},
        "timestamp": timestamp,
        "module": "energy",
        "metrics": {
            "grid_electricity_kwh_per_year": round(grid_kwh_year, 1),
            "grid_emission_factor_kg_co2e_per_kwh": ef,
            "scope2_electricity_tco2e_per_year": round(scope2_t, 3),
            "scope1_transport_fuel_tco2e_per_year": round(scope1_t, 3),
            "transport_fuel_litres_per_year": transport_use["total_fuel_litres_per_year"],
            "avoided_solar_tco2e_per_year": round(avoided_solar_t, 3),
            "avoided_biogas_tco2e_per_year": round(avoided_biogas_t, 3),
            "avoided_ev_net_tco2e_per_year": round(ev_net, 3),
            "gross_emissions_tco2e_per_year": round(scope2_t + scope1_t, 3),
            "net_energy_position_tco2e_per_year": round(scope2_t + scope1_t - avoided_solar_t - avoided_biogas_t - ev_net, 3),
        },
        "compliance": {
            "standard": "IPCC 2006 Guidelines (fuels) and CEA CO2 Baseline Database (grid)",
            "status": "SIMULATION_ON_ASSUMED_INPUTS",
        },
        "target_recipient": "netzero",
    }
