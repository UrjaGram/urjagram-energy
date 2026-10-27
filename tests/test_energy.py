import json
import pytest

from src import config as C
from src.energy_balance import DayScenario, simulate_day, solar_generation_kwh_by_hour
from src.jev_engine import (ActionDirective, AlertLevel, allowed_pump_hours, classify_status,
                            enforce_hard_rules, log_decision)
from src.pipeline import biogas_potential, run_assessment, _load
from src.transport import ev_shift_scenario, fleet_fuel_use


@pytest.fixture(scope="module")
def baseline():
    return _load(C.DATA_DIR, "katlabodi_energy_baseline.json")


@pytest.fixture(scope="module")
def fleet():
    return _load(C.DATA_DIR, "transport_fleet.json")


def test_energy_is_conserved(baseline):
    d = simulate_day(baseline, DayScenario(month=11, solar_kwp=200, battery_kwh=300,
                                           ag_pumping_hours=range(9, 17), ag_grid_hours=range(22, 24)))
    s = d["summary"]
    supplied = s["solar_used_kwh"] + s["battery_discharge_kwh"] + s["biogas_used_kwh"] + s["grid_import_kwh"] + s["unmet_kwh"]
    assert supplied == pytest.approx(s["demand_kwh"], abs=0.5)


def test_night_pumping_without_storage_gets_no_solar(baseline):
    d = simulate_day(baseline, DayScenario(month=11, solar_kwp=200))
    assert d["summary"]["ag_unmet_fraction"] == 0.0
    ag_night = sum(r["ag_demand_kwh"] for r in d["hourly"] if r["hour"] in (22, 23, 0, 1, 2, 3, 4, 5))
    assert ag_night == pytest.approx(d["summary"]["ag_demand_kwh"], abs=0.01)


def test_shifting_pumps_to_daytime_raises_solar_share(baseline):
    night = simulate_day(baseline, DayScenario(month=11, solar_kwp=250))
    day = simulate_day(baseline, DayScenario(month=11, solar_kwp=250, ag_pumping_hours=range(9, 17), ag_grid_hours=[]))
    assert day["summary"]["solar_share_of_demand"] > night["summary"]["solar_share_of_demand"] + 0.3


def test_no_ag_feeder_hours_and_no_solar_means_unmet(baseline):
    d = simulate_day(baseline, DayScenario(month=11, ag_grid_hours=[]))
    assert d["summary"]["ag_unmet_fraction"] == pytest.approx(1.0)


def test_outage_leaves_households_unserved(baseline):
    d = simulate_day(baseline, DayScenario(month=11, village_outage_hours=[19, 20]))
    assert d["summary"]["unmet_kwh"] > 0


def test_solar_total_matches_yield():
    gen = solar_generation_kwh_by_hour(10, 100)
    assert sum(gen) == pytest.approx(C.SOLAR_YIELD_KWH_PER_KWP_PER_DAY[10] * 100)
    assert gen[2] == 0.0


def test_hard_rule_never_lowers_level():
    for lvl in AlertLevel:
        out, _, _ = enforce_hard_rules(lvl, grid_hours_available_today=8, required_pump_hours=8, solar_window_available=True)
        assert list(AlertLevel).index(out) >= list(AlertLevel).index(lvl)


def test_hard_rule_raises_when_grid_gone():
    out, directive, note = enforce_hard_rules(AlertLevel.NORMAL, 0, 8, True)
    assert out == AlertLevel.EMERGENCY
    assert directive == ActionDirective.PRIORITISE_DRINKING_WATER
    assert "forced" in note


def test_hard_rule_warning_when_grid_below_half():
    out, directive, _ = enforce_hard_rules(AlertLevel.NORMAL, 3, 8, True)
    assert out == AlertLevel.WARNING
    assert directive == ActionDirective.SHIFT_TO_SOLAR_WINDOW


def test_water_cap_always_applies():
    assert allowed_pump_hours(8, "LEVEL_2_WARNING", ActionDirective.SHIFT_TO_SOLAR_WINDOW) == 4.0
    assert allowed_pump_hours(8, "LEVEL_3_EMERGENCY", ActionDirective.RUN_AS_SCHEDULED) == 0.0
    assert allowed_pump_hours(8, "LEVEL_0_NORMAL", ActionDirective.RUN_AS_SCHEDULED) == 8.0


def test_classifier_orders_risk():
    assert classify_status(0.0, 0, "LEVEL_0_NORMAL") == AlertLevel.NORMAL
    assert classify_status(0.6, 6, "LEVEL_3_EMERGENCY") == AlertLevel.EMERGENCY


def test_fleet_fuel_numbers(fleet):
    use = fleet_fuel_use(fleet)
    two = next(c for c in use["by_class"] if c["vehicle_class"] == "two_wheeler")
    assert two["fuel_litres_per_year"] == pytest.approx(150 * 10 / 40 * 330)
    assert use["total_emissions_tco2e_per_year"] > 0


def test_ev_shift_saves_fuel_and_cannot_move_tractors(fleet):
    ev = ev_shift_scenario(fleet, {"two_wheeler": 0.5, "tractor": 1.0})
    assert all(s["vehicle_class"] != "tractor" for s in ev["shifted"])
    assert ev["fuel_saved_litres_per_year"]["petrol"] > 0
    assert ev["net_reduction_tco2e_per_year"] > 0


def test_biogas_potential(baseline):
    b = biogas_potential(baseline)
    assert b["collectable_dung_tonnes_per_year"] == pytest.approx(150 * 3.0 * 0.4)


def test_pipeline_end_to_end_logs_decision(tmp_path):
    log = tmp_path / "log.jsonl"
    r = run_assessment(month=11, solar_kwp=250, battery_kwh=200, grid_hours_available_today=2,
                       log_path=log, ev_shift={"two_wheeler": 0.3})
    assert r["status_code"] in {l.value for l in AlertLevel}
    assert r["action"]["directive"].startswith("SHIFT")
    assert r["netzero_stream"]["metrics"]["scope2_electricity_tco2e_per_year"] >= 0
    rec = json.loads(log.read_text().splitlines()[-1])
    assert rec["inputs"]["grid_hours_available_today"] == 2
    assert rec["final_level"] == r["status_code"]


def test_netzero_units_and_ids():
    r = run_assessment(write_log=False)
    m = r["netzero_stream"]["metrics"]
    assert r["netzero_stream"]["village_id"] == "IN-MH-NAG-KATLABODI"
    assert all(k.endswith(("_per_year", "_per_kwh")) for k in m)
