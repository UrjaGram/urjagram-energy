# AI use cases (shortlist)

## 1. Pump schedule and energy source for the day (BUILT)
- User: farmers and the Gram Panchayat.
- Decision: run pumps on the scheduled night supply, stagger them on a hybrid, or shift pumping to the 09:00-17:00 solar window; or, in a shortage, protect drinking water first.
- Data: grid hours today, hourly village demand, solar size, battery, water-module alert level.
- Jev: picks one of four alert levels. Hard rules in code can only raise it (no grid hour = EMERGENCY; under half the needed hours = at least WARNING). The water module's pumping cap always applies.
- Action: a pump-schedule entry (hours allowed, window, directive), a line in the decision log, and a NetZero stream.

## 2. EV shift planning for two-wheelers and autos
- User: Gram Panchayat and vehicle owners.
- Decision: share of vehicles to electrify, and when to charge (midday solar).
- Data: fleet count, km per day, fuel price. Output: fuel saved, charging demand, net tCO2e. (Scenario built; Jev decision not yet added.)

## 3. Village energy demand forecast by hour and season
- User: Gram Panchayat and the solar sizing module.
- Needs metered data; no meter data exists yet, so this waits for field measurement.

Why 1: it solves the problem the partner family recognises (night pumping and an 8-hour supply), it uses data the village already has, and it feeds the water, solar and NetZero modules.
Status: to be checked with the family at the next visit.
