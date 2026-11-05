# Prior work — what already exists (checked 5 Nov 2026)

Prayer-time AC scheduling is **not novel**. What we did not find in searches: diagnosis from clip-on current signatures + a worship-calendar baseline, advisory only. "Not found" ≠ novel — re-check on Google Scholar.

| Work | What it does | How Nabd differs |
|---|---|---|
| Masdar Institute smart-mosque pilot (2016), 2 Abu Dhabi mosques — [The National](https://thenationalnews.com/business/technology/mosque-temperatures-to-be-decided-by-worshipper-numbers-using-masdar-professors-system-1.195153) | Video people-counting → AC control | No cameras; diagnoses faults, not just occupancy |
| Etihad ESCO (DEWA) + Siemens, 115 IACAD mosques — [Zawya](https://www.zawya.com/en/press-release/etihad-esco-and-siemens-to-retrofit-115-mosques-amp-2-buildings-r8o4dyfe) | HVAC/lighting upgrades + controls; 20.43% guaranteed saving, 6-yr M&V | Sensor-only, far cheaper; could feed their M&V |
| ADDC + Awqaf AED 20m, ~850 Abu Dhabi/Al Dhafra mosques (~65%) — [Zawya](https://zawya.com/en/press-release/government-news/abu-dhabi-distribution-company-unveils-aed20mln-investment-to-reduce-electricity-consumption-in-abu-dhabi-mosques-axncys6w) | Remote smart thermostats, predictive maintenance, control room; 20% target | They control setpoints; we tell which unit is failing and whether a load is legitimate; covers mosques outside the programme |
| IoT IR-remote AC control with prayer scheduling (Indonesia, 2026) — [JESSI](https://journal.unm.ac.id/index.php/JESSI/article/view/11456) | Mimics AC remote; 23.7% saving in automatic mode | Control vs diagnosis; no fault detection reported |
| Energy audits of 146 UAE mosques — [AlAli et al., *Buildings* 2023](https://www2.mdpi.com/2075-5309/13/4/1007) | 123.4 → 84 kWh/m² mean after audit; HVAC top load | Our baseline numbers |
| NILM anomaly detection (general) — [Strathclyde](https://strathprints.strath.ac.uk/66609/) | Can load monitoring spot anomalous appliances? | Method background; not mosque-specific |

UAE context: 9,083+ mosques ([Gulf News](https://gulfnews.com/uae/government/uae-has-more-than-9083-mosques-overall-1.72334102) — check date).

## The one-line answer to "ADDC already did this"
They control thermostats; we diagnose units and separate real demand from waste — for ~AED 200 of sensors per mosque (estimate), including the mosques their programme doesn't cover.
