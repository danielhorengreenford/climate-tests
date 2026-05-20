#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cost-optimal and other decline rates for benchmarking

Created on Mon Feb 23 19:01:11 2026

@author: danielhorengreenford
"""

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.stats import linregress


def exponential_decay(t, v0, r):
    """v0 * (1 - r)^t"""
    return v0 * (1 - r) ** t


def fit_decline_rate_ols(series):
    """
    Estimate decline rate via log-linear OLS.
    Fits: log(value) = log(v0) + t * log(1 - r)
    
    Returns
    -------
    dict with 'decline_rate', 'v0', and 'r_squared'
    """
    t = series.index - series.index[0]  # years since start
    log_values = np.log(series.values)

    slope, intercept, r, _, _ = linregress(t, log_values)

    v0 = np.exp(intercept)
    r = 1 - np.exp(slope)  # recover decline rate from slope

    return {'decline_rate': r, 'v0': v0, 'r_squared': r**2}


def fit_decline_rate_nls(series):
    """
    Estimate decline rate via nonlinear least squares on the original scale.
    Fits: value = v0 * (1 - r)^t
    
    Returns
    -------
    dict with 'decline_rate', 'v0', and 'rmse'
    """
    t = series.index - series.index[0]
    v = series.values

    # Initial guesses: v0 = first value, r = 5%
    p0 = [v[0], 0.05]
    bounds = ([0, -1], [np.inf, 1])  # v0 > 0, -100% < r < 100%

    popt, _ = curve_fit(exponential_decay, t, v, p0=p0, bounds=bounds)
    v0, r = popt

    fitted = exponential_decay(t, v0, r)
    rmse = np.sqrt(np.mean((v - fitted) ** 2))

    return {'decline_rate': r, 'v0': v0, 'rmse': rmse}


def extrapolate_from_fit(series, projection_years, method='nls', decline_rate=None):
    """
    Fit an exponential decay to the series and extrapolate forward.

    Parameters
    ----------
    series : pd.Series
        Observed data indexed by year.
    projection_years : array-like
        Future years to project.
    method : 'nls' or 'ols'
        Fitting method to use if decline_rate is not provided.
    decline_rate : float, optional
        Override the fitted rate with a known value.

    Returns
    -------
    pd.DataFrame
        Observed + projected values with 'value', 'source', 'decline_rate' columns.
    """
    if decline_rate is not None:
        fit = {'decline_rate': decline_rate, 'v0': series.iloc[-1]}
    elif method == 'nls':
        fit = fit_decline_rate_nls(series)
    elif method == 'ols':
        fit = fit_decline_rate_ols(series)
    else:
        raise ValueError("method must be 'nls' or 'ols'")

    r = fit['decline_rate']
    base_value = series.iloc[-1]
    base_year = series.index[-1]

    n_years = np.array(projection_years) - base_year
    projected = base_value * (1 - r) ** n_years

    observed_df = series.to_frame(name='value')
    observed_df['source'] = 'observed'

    projected_df = pd.Series(projected, index=projection_years).to_frame(name='value')
    projected_df['source'] = 'projected'

    result = pd.concat([observed_df, projected_df])
    result['decline_rate'] = r
    return result, fit

#Example usage
real_data = pd.Series(
    [1000, 950, 890, 840, 800],
    index=[2018, 2019, 2020, 2021, 2022]
)

projection_years = range(2023, 2041)

result_nls, fit_nls = extrapolate_from_fit(real_data, projection_years, method='nls')
result_ols, fit_ols = extrapolate_from_fit(real_data, projection_years, method='ols')

print(f"NLS decline rate: {fit_nls['decline_rate']:.2%},  RMSE: {fit_nls['rmse']:.2f}")
print(f"OLS decline rate: {fit_ols['decline_rate']:.2%},  R²:   {fit_ols['r_squared']:.4f}")

# Using Welsby et al. (We can try Pye et al. later, and don't forget to include NZE for Europe too; Ref: Welsby et al (2021), UCL report)

loc = "/Users/danielhorengreenford/Documents/Research/Paper 2 - climate tests/"

# Load the Excel file
excel_file = pd.ExcelFile(loc + "Decline-rates.xlsx")

# Load specific sheets
df_modelled = pd.read_excel(excel_file, sheet_name='Welsby', index_col=0)

result_nls, fit_nls = extrapolate_from_fit(df_modelled.loc[:,"oil"], df_modelled.index.to_list(), method='nls')
result_ols, fit_ols = extrapolate_from_fit(df_modelled.loc[:,"oil"], df_modelled.index.to_list(), method='ols')

print(f"NLS decline rate: {fit_nls['decline_rate']:.2%},  RMSE: {fit_nls['rmse']:.2f}")
print(f"OLS decline rate: {fit_ols['decline_rate']:.2%},  R²:   {fit_ols['r_squared']:.4f}")

# Here we fit the last n=5 years of the real production data to the decline rate we estimated and extrapolate it forewards in time

def calibrate_v0_to_real(real_data, decline_rate, n_tail_years=5):
    """
    Given a fixed decline rate (from modelled data), fit the level (v0)
    to the last n_tail_years of real observed data.

    Solves: value = v0 * (1 - r)^t  for v0, with r fixed.

    Parameters
    ----------
    real_data : pd.Series
        Full observed series indexed by year.
    decline_rate : float
        Decline rate estimated from modelled data.
    n_tail_years : int
        Number of trailing years of real data to calibrate against.

    Returns
    -------
    float
        Calibrated v0 (level at t=0, i.e. the first year of the tail window).
    """
    tail = real_data.iloc[-n_tail_years:]
    t = tail.index - tail.index[0]  # years since start of tail window
    v = tail.values
    r = decline_rate

    # With r fixed, the model is linear in v0: v ≈ v0 * (1-r)^t
    # OLS solution: v0 = sum(v * basis) / sum(basis^2)
    basis = (1 - r) ** t
    v0 = np.dot(v, basis) / np.dot(basis, basis)

    return v0


def extrapolate_with_modelled_rate(real_data, projection_years, n_tail_years=5,
                                    modelled_data=None, fit_method='nls',
                                    decline_rate=None):
    """
    Estimate decline rate from modelled data (or use a supplied one), calibrate 
    level to real data, and extrapolate forward.

    Parameters
    ----------
    real_data : pd.Series
        Observed data indexed by year.
    modelled_data : pd.Series, optional
        Model output indexed by year, used to estimate the decline rate.
        Required if decline_rate is not provided.
    projection_years : array-like
        Future years to project into.
    n_tail_years : int
        Number of trailing real data years to calibrate the level against.
    fit_method : 'nls' or 'ols'
        Method for estimating decline rate from modelled data.
    decline_rate : float, optional
        If provided, skip fitting and use this rate directly.

    Returns
    -------
    pd.DataFrame, dict
        Combined observed + projected DataFrame, and fit diagnostics.
    """

    # Step 1: get decline rate — from argument or fitted from modelled data
    if decline_rate is not None:
        r = decline_rate
    else:
        if modelled_data is None:
            raise ValueError("Must provide either modelled_data or decline_rate.")
        fit = fit_decline_rate_nls(modelled_data) if fit_method == 'nls' else fit_decline_rate_ols(modelled_data)
        r = fit['decline_rate']

    # Step 2: calibrate level to last n_tail_years of real data
    tail = real_data.iloc[-n_tail_years:]
    v0 = calibrate_v0_to_real(real_data, r, n_tail_years)
    base_year = tail.index[0]

    # Step 3: extrapolate from last real data point forward
    last_real_year = real_data.index[-1]
    last_real_value = v0 * (1 - r) ** (last_real_year - base_year)
    n_years = np.array(projection_years) - last_real_year
    projected = last_real_value * (1 - r) ** n_years

    # Step 4: reconstruct fitted curve over the tail for diagnostics
    t_tail = tail.index - base_year
    fitted_tail = v0 * (1 - r) ** t_tail
    rmse_tail = np.sqrt(np.mean((tail.values - fitted_tail) ** 2))

    observed_df = real_data.to_frame(name='value')
    observed_df['source'] = 'observed'

    projected_df = pd.Series(projected, index=projection_years).to_frame(name='value')
    projected_df['source'] = 'projected'

    result = pd.concat([observed_df, projected_df])
    result['decline_rate'] = r

    diagnostics = {
        'decline_rate': r,
        'v0': v0,
        'base_year': base_year,
        'tail_rmse': rmse_tail,
        'n_tail_years': n_tail_years,
    }

    return result, diagnostics

"""
# Use case

real_data = pd.Series(
    [1050, 1020, 980, 960, 940, 910, 880],
    index=range(2016, 2023)
)

modelled_data = pd.Series(
    [1200, 1100, 1000, 900, 800, 700, 600, 500],
    index=range(2015, 2023)
)

projection_years = range(2023, 2041)

result, diag = extrapolate_with_modelled_rate(
    real_data, modelled_data, projection_years, n_tail_years=5
)

print(f"Decline rate (from model): {diag['decline_rate']:.2%}")
print(f"Calibrated v0:             {diag['v0']:.1f}  (anchored to {diag['base_year']})")
print(f"Tail RMSE:                 {diag['tail_rmse']:.2f}")
print(result)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def plot_fit_and_projection(real_data, modelled_data, result, diagnostics,
                             n_tail_years=5, 
                             real_label='Real data',
                             modelled_label='Modelled data',
                             figsize=(12, 6)):
    """
    Plot real data, modelled data (used for rate estimation), 
    fitted curve calibrated to real data tail, and projection.

    Parameters
    ----------
    real_data : pd.Series
        Observed real-world data indexed by year. Used for level calibration.
    modelled_data : pd.Series
        Separate modelled dataset indexed by year. Used for rate estimation only.
    result : pd.DataFrame
        Output from extrapolate_with_modelled_rate (observed + projected).
    diagnostics : dict
        Diagnostics dict from extrapolate_with_modelled_rate.
    n_tail_years : int
        Number of tail years used for level calibration.
    real_label : str
        Legend label for the real data series.
    modelled_label : str
        Legend label for the modelled data series.
    figsize : tuple
    """
    r = diagnostics['decline_rate']
    v0 = diagnostics['v0']
    base_year = diagnostics['base_year']

    # Fitted curve over the real data range (rate from model, level from real tail)
    t_fit = real_data.index - base_year
    fitted_curve = v0 * (1 - r) ** t_fit

    projected = result[result['source'] == 'projected']

    fig, ax = plt.subplots(figsize=figsize)

    # Shade the calibration window on the real data
    tail_start = real_data.index[-n_tail_years]
    ax.axvspan(tail_start, real_data.index[-1], alpha=0.08, color='steelblue',
               label=f'Calibration window (last {n_tail_years} yrs)')

    # Modelled data — separate dataset, used only for rate estimation
    ax.plot(modelled_data.index, modelled_data.values, color='grey',
            linewidth=1.5, linestyle='--', marker='x', markersize=5,
            label=f'{modelled_label} (rate estimation)')

    # Real data — separate dataset, used only for level calibration
    ax.plot(real_data.index, real_data.values, color='steelblue',
            linewidth=2, marker='o', markersize=5,
            label=f'{real_label} (level calibration)')

    # Fitted curve: shape from modelled data, level anchored to real data tail
    ax.plot(real_data.index, fitted_curve, color='tomato',
            linewidth=1.5, linestyle=':',
            label=f'Fitted curve (r={r:.2%} from {modelled_label})')

    # Projection forward from last real data point
    ax.plot(projected.index, projected['value'], color='tomato',
            linewidth=2, linestyle='-', label='Projection')
    
    # Projection forward — prepend the last real point to close the gap
    join_year = real_data.index[-1]
    join_value = real_data.iloc[-1]

    projection_with_join = pd.concat([
        pd.Series([join_value], index=[join_year]),
        projected['value']
    ])
    
    ax.plot(projection_with_join.index, projection_with_join.values, color='tomato',
            linewidth=2, linestyle='-', label='Projection')

    # Mark the observed/projected join
    join_year = real_data.index[-1]
    join_value = real_data.iloc[-1]
    ax.axvline(join_year, color='grey', linewidth=0.8, linestyle='--', alpha=0.5)
    # ax.scatter([join_year], [join_value], color='tomato', zorder=5, s=50)

    ax.set_xlabel('Year')
    ax.set_ylabel('Value')
    ax.set_title(
        f'Decline rate ({r:.2%}) estimated from {modelled_label}\n'
        f'Level calibrated to last {n_tail_years} years of {real_label} '
        f'(RMSE: {diagnostics["tail_rmse"]:.2f})'
    )
    ax.legend(framealpha=0.9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    return fig, ax
"""
fig, ax = plot_fit_and_projection(
    real_data, modelled_data, result, diag,
    n_tail_years=5,
    real_label='Production data',
    modelled_label='IEA scenario'
)
plt.show()
"""
# import actual production data

# Load the Excel file
excel_file = pd.ExcelFile(loc + "Oil and gas production DUKES 2025.xlsx")

# Load specific sheets
df_real = pd.read_excel(excel_file, sheet_name='Production_PJ', index_col=0)


# Do the fit and extrapolation and plot with actual data
"""
projection_years = range(2025, 2101)

result, diag = extrapolate_with_modelled_rate(
    real_data, modelled_data, projection_years, n_tail_years=5
)

print(f"Decline rate (from model): {diag['decline_rate']:.2%}")
print(f"Calibrated v0:             {diag['v0']:.1f}  (anchored to {diag['base_year']})")
print(f"Tail RMSE:                 {diag['tail_rmse']:.2f}")
print(result)


fig, ax = plot_fit_and_projection(
    real_data, modelled_data, result, diag,
    n_tail_years=5,
    real_label='Production data',
    modelled_label='IEA scenario'
)
plt.show()
"""
# Assumes df_modelled has columns: 'year', 'oil', 'gas'
# Assumes df_real    has columns: 'year', 'oil', 'gas'

# Set year as index
# df_modelled = df_modelled.set_index('year')
# df_real      = df_real.set_index('year')

"""
To do:
    1) Recalculate the decline rates using Welsby et al. (2021) data
    2) Add IEA NZA European rates 8% for oil and for gas, according to Welsby et al. UCL report: https://www.ucl.ac.uk/bartlett/sites/bartlett/files/uk_oil_and_gas_in_a_1.5_degree_world_final_0.pdf
"""

# could leave as 2025–2100 and just use the cum sum until 2050 or change to 2050 (2051 in counter)
projection_years = range(2025, 2051) #changing to 2050, this is what they used in study, and coincides with a 2050 net-zero date. Produciton past then should be minimal and otherwise relies heavily on negative emissions tech
n_tail_years = 5

results = {}
diagnostics = {}

for fuel in ['oil', 'gas']:
    modelled_series = df_modelled[fuel].dropna()
    real_series     = df_real[fuel].dropna()

    result, diag = extrapolate_with_modelled_rate(
        real_data=real_series,
        modelled_data=modelled_series,
        projection_years=projection_years,
        n_tail_years=n_tail_years,
        fit_method='nls' #could use ols
    )

    results[fuel]     = result
    diagnostics[fuel] = diag

    print(f"\n--- {fuel.upper()} ---")
    print(f"  Decline rate (from modelled): {diag['decline_rate']:.2%}")
    print(f"  Calibrated v0:                {diag['v0']:.1f} PJ")
    print(f"  Tail RMSE:                    {diag['tail_rmse']:.2f} PJ")

# Plot both fuels
for fuel in ['oil', 'gas']:
    fig, ax = plot_fit_and_projection(
        real_data=df_real[fuel].dropna(),
        modelled_data=df_modelled[fuel].dropna(),
        result=results[fuel],
        diagnostics=diagnostics[fuel],
        n_tail_years=n_tail_years,
        real_label=f'Real {fuel} consumption',
        modelled_label=f'Modelled {fuel} scenario'
    )
    ax.set_ylabel('PJ')
    ax.set_title(
        f'{fuel.upper()} — decline rate ({diagnostics[fuel]["decline_rate"]:.2%}) '
        f'from modelled scenario\n'
        f'Level calibrated to last {n_tail_years} years of real data '
        f'(RMSE: {diagnostics[fuel]["tail_rmse"]:.2f} PJ)'
    )
    plt.savefig(f'{fuel}_projection.png', dpi=150, bbox_inches='tight')
    plt.show()

# To output the time series and take sum to get cumulative production over 2025-2100
"""
# Build a clean projection DataFrame for 2025–2100
projection_df = pd.DataFrame({
    fuel: results[fuel][results[fuel]['source'] == 'projected']['value']
    for fuel in ['oil', 'gas']
})

projection_df.index.name = 'year'
print(projection_df)

# Cumulative production
projection_df['total'] = projection_df['oil'] + projection_df['gas']
cumulative = projection_df.sum()

print("\nCumulative 2025–2100:")
print(f"  Oil:   {cumulative['oil']:,.1f} PJ")
print(f"  Gas:   {cumulative['gas']:,.1f} PJ")
print(f"  Total: {cumulative['total']:,.1f} PJ")
"""
# Conversion factors (MtCO2 per PJ)
conversion_factors = {
    'oil': 0.0733,
    'gas': 0.0505
}

# --- Production DataFrame with totals ---
production_df = pd.DataFrame({
    fuel: results[fuel][results[fuel]['source'] == 'projected']['value']
    for fuel in ['oil', 'gas']
})
production_df.index.name = 'year'
production_df['total'] = production_df['oil'] + production_df['gas']

# Append a totals row
totals_row = production_df.sum().rename('TOTAL')
production_df_with_total = pd.concat([production_df, totals_row.to_frame().T])

print("=== Production (PJ) ===")
print(production_df_with_total.to_string(float_format='{:,.1f}'.format))

# --- Emissions DataFrame with totals ---
emissions_df = pd.DataFrame({
    fuel: production_df[fuel] * conversion_factors[fuel]
    for fuel in ['oil', 'gas']
})
emissions_df.index.name = 'year'
emissions_df['total'] = emissions_df['oil'] + emissions_df['gas']

totals_row_em = emissions_df.sum().rename('TOTAL')
emissions_df_with_total = pd.concat([emissions_df, totals_row_em.to_frame().T])

print("\n=== Emissions (MtCO2) ===")
print(emissions_df_with_total.to_string(float_format='{:,.2f}'.format))

# Save as excel file
# production_df_with_total.to_csv(loc+'oil_gas_projections_2025_2100.csv')
# emissions_df_with_total.to_csv(loc+'oil_gas_projections_2025_2100.csv')
with pd.ExcelWriter(loc+'oil_gas_projections-2050.xlsx', engine='openpyxl') as writer:
    production_df_with_total.to_excel(writer, sheet_name='Production')
    emissions_df_with_total.to_excel(writer, sheet_name='Emissions')
    
# Now run for the IEA Europe decline rates: IEA NZE (European level), 2020-2050 from Welsby et al. UCL: https://www.ucl.ac.uk/bartlett/sites/bartlett/files/uk_oil_and_gas_in_a_1.5_degree_world_final_0.pdf

decline_rates = {
    'oil': 0.08,  # 8% per year
    'gas': 0.08   # 8% per year
}

for fuel in ['oil', 'gas']:
    result, diag = extrapolate_with_modelled_rate(
        real_data=df_real[fuel].dropna(),
        modelled_data=None,
        projection_years=projection_years,
        n_tail_years=n_tail_years,
        decline_rate=decline_rates[fuel]
    )
    results[fuel] = result
    diagnostics[fuel] = diag

# --- Production DataFrame with totals ---
production_df = pd.DataFrame({
    fuel: results[fuel][results[fuel]['source'] == 'projected']['value']
    for fuel in ['oil', 'gas']
})
production_df.index.name = 'year'
production_df['total'] = production_df['oil'] + production_df['gas']

# Append a totals row
totals_row = production_df.sum().rename('TOTAL')
production_df_with_total = pd.concat([production_df, totals_row.to_frame().T])

print("=== Production (PJ) ===")
print(production_df_with_total.to_string(float_format='{:,.1f}'.format))

# --- Emissions DataFrame with totals ---
emissions_df = pd.DataFrame({
    fuel: production_df[fuel] * conversion_factors[fuel]
    for fuel in ['oil', 'gas']
})
emissions_df.index.name = 'year'
emissions_df['total'] = emissions_df['oil'] + emissions_df['gas']

totals_row_em = emissions_df.sum().rename('TOTAL')
emissions_df_with_total = pd.concat([emissions_df, totals_row_em.to_frame().T])

print("\n=== Emissions (MtCO2) ===")
print(emissions_df_with_total.to_string(float_format='{:,.2f}'.format))

# Save as excel file
# production_df_with_total.to_csv(loc+'oil_gas_projections_2025_2100.csv')
# emissions_df_with_total.to_csv(loc+'oil_gas_projections_2025_2100.csv')
with pd.ExcelWriter(loc+'oil_gas_projections-IEA.xlsx', engine='openpyxl') as writer:
    production_df_with_total.to_excel(writer, sheet_name='Production')
    emissions_df_with_total.to_excel(writer, sheet_name='Emissions')