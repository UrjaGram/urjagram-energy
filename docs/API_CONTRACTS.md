# Inter-module contracts (Energy)

Common format: village_id, latitude/longitude, ISO 8601 timestamp, units in field names. Open items are marked.

## Inbound from Weather (Vibhor)
```json
{"village_id": "IN-MH-NAG-KATLABODI", "timestamp": "2026-10-28T06:00:00Z",
 "daily_forecast": [{"date": "2026-10-29", "solar_irradiance_kwh_per_m2_day": 5.1, "max_temperature_celsius": 33.5}]}
```
Used to replace the monthly solar yield table. Not wired yet.

## Inbound from Water (Kushagra)
```json
{"village_id": "IN-MH-NAG-KATLABODI", "timestamp": "2026-10-28T06:00:00Z", "status_code": "LEVEL_2_WARNING"}
```
Used as `--water-alert`. The water module's pump-hour cap always applies.

## Inbound from Community Solar (Devanshu)
```json
{"village_id": "IN-MH-NAG-KATLABODI", "solar_pv_kwp": 250.0, "battery_kwh": 300.0}
```
Used as `--solar-kwp` and `--battery-kwh`.

## Outbound to Water and Community Solar: pump schedule
```json
{"village_id": "IN-MH-NAG-KATLABODI", "action": {"type": "pump_schedule", "ag_pumping_hours_allowed_per_day": 8.0,
 "pumping_window": "09:00-17:00", "directive": "SHIFT_PUMPING_TO_SOLAR_WINDOW"}}
```

## Outbound to NetZero (Raj): tonnes CO2e per year
See `netzero_stream` in the output of `python -m src.cli --json`. Keys end in `_tco2e_per_year`.

Open item for the weekly review: this module reports all grid electricity including pumping; the water module should
not report pumping electricity again, to avoid double counting.
