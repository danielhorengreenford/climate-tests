# Climate Testing Fossil Fuel Extraction: Code Repository

**Supporting code for:** Horen Greenford, D., Lesk, C., Barnes, A., Wakefield, J.R., Lloyd, S. & Matthews, H.D. "Robust climate tests for fossil fuel supply under the Paris Agreement" *Nature Communications* (*under review*). Preprint available at https://dx.doi.org/10.21203/rs.3.rs-9546305/v1

---

## Overview

This repository contains the Python code used to derive cost-optimal benchmarks, compute test subject emissions, calculate climate compatibility ratios (γ), and produce all figures for the paper. The analysis compares cumulative UK oil and gas extraction emissions ("test subjects") against Paris-compliant allowances ("benchmarks") under multiple equity, feasibility, and climate adequacy frameworks.

---

## Repository Structure

```
├── decline_rate_benchmarks.py            # Cost-optimal benchmark derivation
├── test-subject-emissions.py             # Test subject emissions & Fig. 2a
├── climate_tests_and_heat_maps.py        # γ calculations & Fig. 3 heatmaps
├── benchmark-plot.py                     # Benchmark bar chart (Fig. 2b)
├── data/                                 # Input data (see Data Requirements below)
└── outputs/                              # Generated figures and data tables
```

---

## Scripts

### 1. `decline_rate_benchmarks.py`
**Purpose:** Derives cost-optimal benchmarks for UK oil and gas by fitting an exponential decline rate to TIAM-UCL model output (Welsby et al. 2021) and extrapolating forward from recent observed production.

**Method:**
- Fits v(t) = v₀(1 − r)^t to Welsby et al. UK production trajectories using nonlinear least squares (NLS), recovering compound annual decline rates separately for oil and gas. An OLS log-linear alternative is also implemented.
- Calibrates the level parameter v₀ to the last five years of real UK production data from DUKES, anchoring the projection to observed output rather than model-implied levels.
- Extrapolates from 2025 to 2100, converts cumulative production to downstream CO₂ emissions using standard conversion factors (0.0733 MtCO₂/PJ oil; 0.0505 MtCO₂/PJ gas).
- Applies a scaling factor to adjust for the difference between Welsby et al.'s original carbon budget and current estimates (Forster et al. 2025).
- Runs IEA Net Zero Emissions European-level decline rates (8%/year oil and gas) as a sensitivity check, following Welsby et al. (2022) UCL report.

**Key inputs:**
- `Decline-rates.xlsx` — Welsby et al. TIAM-UCL UK production output (sheet: `Welsby`), in PJ, interpolated to annual timesteps
- `Oil and gas production DUKES 2025.xlsx` — Real UK oil and gas production data (sheet: `Production_PJ`), in PJ

**Key outputs:**
- `oil_gas_projections-2050.xlsx` — Projected production and emissions under Welsby et al. fitted decline rates (sheets: `Production`, `Emissions`)
- `oil_gas_projections-IEA.xlsx` — Projected production and emissions under IEA 8% sensitivity (sheets: `Production`, `Emissions`)
- Diagnostic plots of fitted vs. observed production for each fuel

---

### 2. `test-subject-emissions.py`
**Purpose:** Processes NSTA reserves and resources data to compute cumulative stacked test subject emissions for all ordering scenarios and production scenarios. Produces Figure 2a (stacked bar charts of UK oil and gas potential production).

**Method:**
- Loads oil and gas emissions by category (Reserves, Producing fields, Proposed new developments, Licensed marginal discoveries, Unlicensed marginal discoveries) and separately for fields under regulatory scrutiny (Rosebank Phases 1 & 2, Jackdaw, Cambo).
- Generates all possible category assignments for fields under regulatory scrutiny (e.g., whether Rosebank Phase 1 is classified as Reserves or Proposed new developments) and all within-category orderings, enabling sensitivity analysis across ordering scenarios.
- For each combination of ordering scenario × production scenario (Central, EIA, Upper), subtracts field-specific volumes from base category totals to avoid double counting, then stacks components cumulatively in order of likelihood of extraction.
- Production scenarios: Central uses P50 reserves and P50 resources (2P+2C); Upper uses P10 throughout (3P+3C); EIA uses P50 reserves with P10 resources (2P+3C), representing a best-estimate baseline paired with a conservative upper bound for fields under regulatory scrutiny.
- Converts all volumes to downstream combustion CO₂ (MtCO₂) using 3.22 tCO₂/toe (oil) and 2.0414 tCO₂/bcm (gas).

**Key inputs:**
- `Data-Climate_tests-clean.xlsx` with sheets:
  - `oil_emissions` — Base category emissions by scenario (Reserves, Producing fields, etc.)
  - `gas_emissions` — Same for gas
  - `foi_oil_emissions` — P50 and P10 emissions for each field under regulatory scrutiny (oil)
  - `foi_gas_emissions` — Same for gas
  - `test_subjects` — Stacking order definitions for each ordering scenario

**Key outputs:**
- `outputs/oil_[central|eia|upper]_test_subjects.csv` — Cumulative oil emissions by ordering scenario and production scenario
- `outputs/gas_[central|eia|upper]_test_subjects.csv` — Same for gas
- `outputs/[scenario_name]_oil_gas-share_y.svg` — Stacked bar panel plots (Fig. 2a) for each ordering scenario

---

### 3. `climate_tests_and_heat_maps.py`
**Purpose:** Calculates climate compatibility ratios (γ = test subject / benchmark) for all combinations of ordering scenario, production scenario, benchmark, and temperature target. Produces Figure 3 heatmap tables and exports all results to Excel.

**Method:**
- Loads pre-computed test subject CSV files (output of Script 2) and benchmark values.
- For each ordering scenario, stacks cumulative emissions in the defined order and divides by each benchmark to calculate γ at each cumulative position.
- Colour-codes results by pass/fail category: Pass (γ ≤ 0.9), Precautionary Failure (0.9–1.1), Failure (1.1–2.0), Major Failure (≥ 2.0).
- Applies grey background to 1.7°C benchmark row labels for visual distinction.
- Generates one heatmap per fuel × production scenario combination (6 heatmaps per ordering scenario: oil Central/EIA/Upper and gas Central/EIA/Upper).
- Exports all γ values for all combinations to a single Excel file for further analysis.

**Key inputs:**
- `outputs/oil_[central|eia|upper]_test_subjects.csv`
- `outputs/gas_[central|eia|upper]_test_subjects.csv`
- `benchmarks-MtCO2-2025_2100.csv` — Benchmark allowances in MtCO₂ for each allocation approach and temperature target

**Key outputs:**
- `outputs/[scenario]_oil_[central|eia|upper]_heatmap.pdf` — Oil heatmaps (Fig. 3 and Supplementary Results)
- `outputs/[scenario]_gas_[central|eia|upper]_heatmap.pdf` — Gas heatmaps
- `outputs/heatmap_legend.pdf` — Standalone legend
- `outputs/all_heatmap_data.xlsx` — All γ values for all combinations (Supplementary Data)

---

### 4. `benchmark-plot.py`
**Purpose:** Produces Figure 2b — the grouped bar chart showing downstream benchmark emissions for UK oil and gas under each allocation approach and temperature target.

**Method:**
- Loads benchmark values from CSV and plots paired oil/gas bars for each benchmark, colour-coded by allocation approach (cost-optimal, current trends, equity via partial reallocation, equity via full reallocation).
- Temperature targets (1.7°C and 1.5°C) are shown as bar pairs within each benchmark group, labelled with rotated text.
- Output in both PDF and SVG for publication.

**Key inputs:**
- `benchmarks-GtCO2-2025_2100.csv` — Benchmark allowances in GtCO₂ (same data as MtCO₂ file, rescaled)

**Key outputs:**
- `benchmark_nature.pdf` / `benchmark_nature.svg` — Figure 2b

---

## Data Requirements

The following input files are required. Raw NSTA data and publicly available sources are described in the paper's Data and Code Availability statement.

| File | Contents | Source |
|------|----------|--------|
| `Data-Climate_tests-clean.xlsx` | NSTA oil and gas emissions by category and field, stacking order definitions | Derived from NSTA Reserves and Resources Report 2024 |
| `Decline-rates.xlsx` | Welsby et al. TIAM-UCL UK production trajectories (annual, PJ) | Obtained from study authors (J. Price & S. Pye, personal communication, November 2024) |
| `Oil and gas production DUKES 2025.xlsx` | Real UK oil and gas production (annual, PJ) | UK DESNZ Digest of United Kingdom Energy Statistics (DUKES) 2025 |
| `benchmarks-MtCO2-2025_2100.csv` | Benchmark allowances (MtCO₂) for all allocation approaches and temperature targets | Derived in this study; see Methods |
| `benchmarks-GtCO2-2025_2100.csv` | Same as above in GtCO₂ | Derived in this study; see Methods |

**Note:** TIAM-UCL model output (Decline-rates.xlsx) was obtained via correspondence with James Price and Steve Pye (UCL) and is not publicly archived. Requests for this data should be directed to the original authors.

---

## Dependencies

Python 3.9 or later is recommended.

```
pandas
numpy
scipy
matplotlib
openpyxl
```

Install all dependencies with:
```bash
pip install pandas numpy scipy matplotlib openpyxl
```

---

## Reproducing the Analysis

Scripts were run using Spyder 6.1.3 in an Anaconda Python environment

Run scripts in the following order, if using python in command line:

```bash
# Step 1: Compute test subject emissions and generate Fig. 2a
python test-subject-emissions.py

# Step 2: Derive cost-optimal benchmarks
python decline_rate_benchmarks.py

# Step 3: Generate Fig. 2b benchmark bar chart
python benchmark-plot.py

# Step 4: Calculate γ ratios and generate Fig. 3 heatmaps
python climate_tests_and_heat_maps.py
```

**Before running**, update the file paths at the top of each script to point to your local data directory. All scripts use a `loc` variable for the base directory.

The main text Figure 3 corresponds to ordering Scenario 7 under the EIA production scenario. Supplementary Results include all ordering scenarios and all production scenarios.

---

## Notes on Ordering Scenarios

Script 2 generates multiple ordering scenarios reflecting alternative classifications and sequencing of fields under regulatory scrutiny. The main text presents the most likely ordering (Rosebank Phase 1 and Jackdaw classified as Reserves, ordered by likelihood of extraction). Supplementary Results include sensitivity analyses for alternative orderings, including scenarios where Rosebank Phase 1 is reclassified as a proposed new development.

---

## Citation

If you use this code, please cite:

Horen Greenford, D., Lesk, C., Barnes, A., Wakefield, J.R., Lloyd, S. & Matthews, H.D. (2026). Climate testing fossil fuel extraction: A framework applied to UK oil and gas. *in rev.*. https://dx.doi.org/10.21203/rs.3.rs-9546305/v1

---

## Contact

Daniel Horen Greenford  
SSHRC Postdoctoral Fellow, Department of Earth and Planetary Sciences, McGill University  
[daniel.horengreenford@mcgill.ca]
