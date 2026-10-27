# UrjaGram Energy

Village energy balance, pumping decision and transport emissions for Katlabodi (IN-MH-NAG-KATLABODI), part of the UrjaGram OS platform.
Built in the same shape as the water module (urjagram-aquagram-water) so the two connect.

## What it does
1. Builds an hourly demand-supply balance for one day: households, streetlights, dairy chilling, drinking-water pump and the 42 agricultural pumps, against solar, battery, biogas and the grid (agricultural feeder only in its supply hours).
2. Compares pumping as scheduled (night) with pumping shifted to the 09:00-17:00 solar window.
3. A Jev stand-in picks an alert level; hard rules in code can only raise it; the water module's pump-hour cap always applies.
4. Writes the pump-schedule action, logs the decision with its inputs, and builds the NetZero stream (tCO2e per year).
5. Transport: fuel and emissions by vehicle class, and an EV-shift scenario.

## Inputs
`data/katlabodi_energy_baseline.json`, `data/transport_fleet.json`, `data/partner_farmer.json`. Items marked ASSUMPTION are placeholders until measured. No personal data; the family is referred to by code.

## Outputs
Result dict / JSON (status, action, balances, transport, EV, biogas potential, `netzero_stream`) and `outputs/decision_log.jsonl`.

## Run
```
python -m pip install -r requirements.txt
python -m pytest
python -m src.cli --solar-kwp 250 --battery-kwh 300 --grid-hours 3 --ev-two-wheeler-share 0.3
python -m src.cli --json
```

## Layout
`src/energy_balance.py` hourly balance, `src/transport.py`, `src/jev_engine.py` decision and hard rules, `src/netzero_emitter.py`, `src/pipeline.py`, `src/cli.py`, `docs/` (domain note, use cases, contracts), `tests/`.

## Honest limits
- The Kurukshetra team's energy model was not available, so this is a fresh build. It should be merged with theirs.
- Jev is a deterministic stand-in with the same interface; the live model is not connected.
- Household use, fleet, solar yield and dung figures are assumptions pending meter readings and a vehicle count.
- The NetZero stream annualises a representative day; the solar credit is an upper bound.

## Links to other modules
Weather (solar forecast), Water (alert level, pump hours), Community Solar (kWp, battery), Dairy (biogas), NetZero (stream). See `docs/API_CONTRACTS.md`.
