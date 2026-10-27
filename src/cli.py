"""Command line: python -m src.cli --month 11 --solar-kwp 250 --battery-kwh 300"""

import argparse
import json

from .pipeline import run_assessment


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="UrjaGram Energy: village energy balance and pumping decision")
    p.add_argument("--month", type=int, default=11)
    p.add_argument("--solar-kwp", type=float, default=None)
    p.add_argument("--battery-kwh", type=float, default=None)
    p.add_argument("--grid-hours", type=float, default=None, help="grid hours available today for the agricultural feeder")
    p.add_argument("--water-alert", default="LEVEL_0_NORMAL", help="alert level from the water module")
    p.add_argument("--ev-two-wheeler-share", type=float, default=0.0)
    p.add_argument("--ev-auto-share", type=float, default=0.0)
    p.add_argument("--json", action="store_true", help="print the full result as JSON")
    p.add_argument("--no-log", action="store_true")
    a = p.parse_args(argv)

    ev = None
    if a.ev_two_wheeler_share or a.ev_auto_share:
        ev = {"two_wheeler": a.ev_two_wheeler_share, "auto_rickshaw": a.ev_auto_share}
    r = run_assessment(month=a.month, solar_kwp=a.solar_kwp, battery_kwh=a.battery_kwh,
                       grid_hours_available_today=a.grid_hours, water_alert=a.water_alert,
                       ev_shift=ev, write_log=not a.no_log)
    if a.json:
        print(json.dumps(r, indent=2))
        return 0

    s, h = r["balance_as_scheduled"], r["balance_shifted_to_solar_window"]
    print("UrjaGram Energy | {} | month {}".format(r["village_id"], a.month))
    print("Status: {} (Jev said {}; {})".format(r["status_code"], r["jev_level_before_hard_rules"], r["guardrail_status"]))
    print("Action: {} | pump hours {} | window {}".format(
        r["action"]["directive"], r["action"]["ag_pumping_hours_allowed_per_day"], r["action"]["pumping_window"]))
    print("Per day, as scheduled : demand {demand_kwh} kWh, grid {grid_import_kwh}, solar {solar_used_kwh}, unmet {unmet_kwh}".format(**s))
    print("Per day, solar window : demand {demand_kwh} kWh, grid {grid_import_kwh}, solar {solar_used_kwh}, unmet {unmet_kwh}".format(**h))
    m = r["netzero_stream"]["metrics"]
    print("NetZero: scope2 {} tCO2e/yr, transport {} tCO2e/yr, net {} tCO2e/yr".format(
        m["scope2_electricity_tco2e_per_year"], m["scope1_transport_fuel_tco2e_per_year"], m["net_energy_position_tco2e_per_year"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
