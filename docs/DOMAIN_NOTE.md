# Domain note: energy and transport in Katlabodi

Source for village facts: Katlabodi Survey by the VNIT Nagpur team (visits Sept-Oct 2026). Numbers marked
ASSUMPTION are placeholders until measured. No names or phone numbers are stored in this repository.

## The village in energy terms
- About 717 people, 160 households, 52% Scheduled Tribe, 75% in agriculture. Average household income about Rs 50,000 a year.
- Village supply is 24 hours. Agricultural supply is 8 hours a day in rotating shifts (night 10 PM-6 AM this week).
- 100% groundwater irrigation: 42 agricultural borewells with about 5 HP pumps (shared with the water module).
- No internet or mobile tower in the village; every household has a smartphone. Anything that needs a connection must work offline and sync on a visit.
- About 1,000 cattle, buffaloes and goats; at least 150 tractor loads of dung a year. Animals graze freely in forest in monsoon and winter, so only part of the dung can be collected.
- Mostly tar (Damar) roads; goods go to local markets because Nagpur mandis cost too much to reach.

## Who decides what
| User | Decision | Data |
|---|---|---|
| Farmer | When to run the pump, and whether to shift to daytime | grid hours today, pump size, crop need |
| Gram Panchayat | Where to put community solar and how big, which loads get priority in a shortfall | hourly demand, solar yield, outages |
| SHG women | Whether a small enterprise (for example agarbatti) can run on solar hours | machine kW, hours |
| Village drivers and owners | Whether an electric two-wheeler or auto pays back | km per day, fuel price |

## Schemes that apply (to verify with the DISCOM and Agriculture Department)
- PM-KUSUM: component A (solar plants on barren land), B (standalone solar pumps), C (solarising grid pumps). Survey finding: farmers do not use it because the 25% upfront share is unaffordable, paperwork is complex, and they doubt a solar pump can run 8 straight hours. Awareness is near zero.
- Maharashtra's daytime solar feeder programme for agriculture (Mukhyamantri Saur Krishi Vahini): check whether the Katol feeder is covered; this would move pumping to daytime without any farmer investment.
- PM Surya Ghar for household rooftops: covered by the Surya Ghar module (Jay).

## Current problems
1. Pumping happens at night, when solar cannot help and farmers work in the dark.
2. 8 supply hours at a rotating time makes pump scheduling guesswork.
3. Grid electricity (mostly pumping) and transport fuel are the two large sources: about 259 and 228 tCO2e a year on the assumed inputs.
4. Fuel for tractors, two-wheelers and autos is bought with no record, so emissions and savings cannot be measured.
5. Dung is not collected for biogas.

## Method
Hourly balance of demand and supply for one representative day per month, then annualised for the NetZero account.
Emission factors: CEA grid average 0.82 kg/kWh (same as the water module); IPCC 2006 fuel factors for diesel and petrol.

## Data sources
- Katlabodi Survey (VNIT Nagpur team), Sept-Oct 2026.
- UrjaGram/urjagram-aquagram-water data (borewell count, pump HP).
- CEA CO2 Baseline Database for the Indian Power Sector; IPCC 2006 Guidelines, Volume 2.
- Solar yield per month is an indicative table; replace with PVGIS or NASA POWER for 21.28 N, 78.58 E.

## Partner farmer family
Code: Farmer-KB-01 (to confirm). Land about 3.5 acres, one 5 HP submersible pump, night supply. Consent and visit log: see family-log.md.
