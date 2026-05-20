#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Climate tests and heatmap table

Created on Thu Feb 26 13:19:25 2026

@author: danielhorengreenford
"""
import pandas as pd
# import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ============================================================================
# LOAD TEST_SUBJECTS SHEET FROM EXCEL
# ============================================================================

# UPDATE THIS PATH
loc = "/Users/danielhorengreenford/Documents/Research/Paper 2 - climate tests/"
excel_file = pd.ExcelFile(loc + 'Data-Climate_tests-clean.xlsx')

# Load test_subjects sheet
test_subjects = pd.read_excel(excel_file, sheet_name='test_subjects')

# Clean up whitespace
for col in test_subjects.columns:
    if test_subjects[col].dtype == 'object':
        test_subjects[col] = test_subjects[col].apply(lambda x: x.replace('\xa0', '').strip() if isinstance(x, str) else x)

print("✓ Loaded test_subjects sheet")
print(f"  Columns: {list(test_subjects.columns)}")

# ============================================================================
# LOAD BENCHMARK DATA
# ============================================================================

# UPDATE THIS PATH to your benchmark CSV
loc = "/Users/danielhorengreenford/Documents/Research/Paper 2 - climate tests/"

benchmark_csv_path = loc+"benchmarks-MtCO2-2025_2100.csv"
benchmark_df = pd.read_csv(benchmark_csv_path)

print("Benchmark data loaded:")
print(benchmark_df)

# ============================================================================
# LOAD TEST SUBJECT DATA FROM CSVs
# ============================================================================

# UPDATE THIS PATH to your data directory
data_dir = loc+"outputs/"  # or specify a different path
output_dir = data_dir
# Load the 6 test subject CSV files that were saved earlier
oil_central_df = pd.read_csv(data_dir + 'oil_central_test_subjects.csv', index_col=0)
oil_eia_df = pd.read_csv(data_dir + 'oil_eia_test_subjects.csv', index_col=0)
oil_upper_df = pd.read_csv(data_dir + 'oil_upper_test_subjects.csv', index_col=0)

gas_central_df = pd.read_csv(data_dir + 'gas_central_test_subjects.csv', index_col=0)
gas_eia_df = pd.read_csv(data_dir + 'gas_eia_test_subjects.csv', index_col=0)
gas_upper_df = pd.read_csv(data_dir + 'gas_upper_test_subjects.csv', index_col=0)

print("\n✓ Loaded test subject data")
print(f"Oil central scenarios: {list(oil_central_df.index)}")
print(f"Gas central scenarios: {list(gas_central_df.index)}")

# ============================================================================
# GET STACKING ORDER FOR EACH SCENARIO
# ============================================================================

def get_stacking_order_for_scenario(scenario_name):
    """Get the stacking order from test_subjects sheet"""
    stacking_order = []
    
    for idx, (item, cat) in enumerate(zip(test_subjects[scenario_name], 
                                          test_subjects.iloc[:, test_subjects.columns.get_loc(scenario_name) + 1])):
        if pd.isna(item):
            break
        item = str(item).strip()
        cat = str(cat).strip() if not pd.isna(cat) else ''
        
        # Parse items
        if item == 'Reserves':
            stacking_order.append('Reserves')
        elif item == 'Producing fields' or 'Producing fields' in item and not item.startswith('w/ '):
            stacking_order.append('Producing fields')
        elif item == 'Proposed new developments' or ('Proposed new developments' in item and not item.startswith('w/ ')):
            stacking_order.append('Proposed new developments')
        elif item == 'Licensed marginal discoveries' or ('Licensed marginal' in item and 'Unlicensed' not in item):
            stacking_order.append('Licensed marginal discoveries')
        elif item == 'Unlicensed marginal discoveries' or 'Unlicensed marginal' in item:
            stacking_order.append('Unlicensed marginal discoveries')
        elif 'Rosebank (Phase 1)' in item or 'Rosebank 1' in item:
            stacking_order.append('Rosebank (Phase 1)')
        elif 'Jackdaw' in item:
            stacking_order.append('Jackdaw')
        elif 'Cambo' in item:
            stacking_order.append('Cambo')
        elif 'Rosebank (Phase 2)' in item or 'Rosebank 2' in item:
            stacking_order.append('Rosebank (Phase 2)')
    
    return stacking_order

# ============================================================================
# CALCULATE CUMULATIVE RATIOS FOR ONE SCENARIO
# ============================================================================

def calculate_cumulative_ratios(scenario_name, test_df, benchmark_df, fuel_type):
    """
    Calculate cumulative emissions ratios for one test scenario
    
    Returns: DataFrame with rows=cumulative positions, columns=benchmarks
    """
    
    # Get the stacking order
    stacking_order = get_stacking_order_for_scenario(scenario_name)
    
    # Get the test subject row
    test_row = test_df.loc[scenario_name]
    
    # Calculate cumulative emissions at each position
    cumulative_emissions = []
    cumulative_labels = []
    cumulative_sum = 0
    
    for position_num, component in enumerate(stacking_order, start=1):
        # Get the emission value for this component
        value = test_row.get(component, 0)
        if pd.isna(value):
            value = 0
        
        cumulative_sum += value
        cumulative_emissions.append(cumulative_sum)
        
        # Create label (without hard-coded numbers)
        short_label = component.replace('Reserves', 'Reserves')\
                               .replace('Rosebank (Phase 1)', 'Rosebank 1')\
                               .replace('Jackdaw', 'Jackdaw')\
                               .replace('Producing fields', 'Producing')\
                               .replace('Cambo', 'Cambo')\
                               .replace('Rosebank (Phase 2)', 'Rosebank 2')\
                               .replace('Proposed new developments', 'Proposed')\
                               .replace('Licensed marginal discoveries', 'Licensed')\
                               .replace('Unlicensed marginal discoveries', 'Unlicensed')
        
        # Add position number prefix dynamically
        numbered_label = f"{position_num}. {short_label}"
        cumulative_labels.append(numbered_label)
    
    # Now calculate ratios for each benchmark
    ratios = {}
    
    for idx, bench_row in benchmark_df.iterrows():
        benchmark_label = f"{bench_row['Benchmarks']}\n{bench_row['Target']}"
        benchmark_emission = bench_row[fuel_type]
        
        if benchmark_emission == 0 or pd.isna(benchmark_emission):
            continue
        
        # Calculate ratios for all cumulative positions
        benchmark_ratios = [cum_em / benchmark_emission for cum_em in cumulative_emissions]
        ratios[benchmark_label] = benchmark_ratios
    
    # Create DataFrame
    ratio_df = pd.DataFrame(ratios, index=cumulative_labels)
    
    ratio_df = ratio_df.T  # Transpose: benchmarks as rows, cumulative positions as columns
    return ratio_df

# ============================================================================
# CREATE HEATMAP FOR ONE SCENARIO - COMPACT VERSION
# ============================================================================
def create_heatmap_for_scenario(ratio_df, scenario_name, fuel_type, prod_scenario):
    """Create heatmap for one test scenario"""
    
    # Get data dimensions
    n_rows, n_cols = ratio_df.shape
    
    # Dynamically size based on data (cell size approach)
    cell_height = 0.1  # Height per cell in inches
    cell_width = 0.17   # Width per cell in inches
    
    # Calculate figure size with minimal margins
    fig_width = n_cols * cell_width + 4  
    fig_height = n_rows * cell_height + 3.5 
        
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # Define color function
    def get_color(value):
        if pd.isna(value):
            return '#FFFFFF'
        elif value <= 0.9:
            return '#FFFF00'  # Yellow: Pass
        elif value < 1.1:
            return '#FFA500'  # Orange: Near Pass
        elif value < 2:
            return '#FF0000'  # Red: Failure
        else:
            return '#8B0000'  # Dark Red: Major Failure
    
    # Get data
    table_data = ratio_df.values
    
    # Create colored grid
    for i in range(n_rows):
        for j in range(n_cols):
            value = table_data[i, j]
            color = get_color(value)
            
            # Draw rectangle
            rect = mpatches.Rectangle((j-0.5, i-0.5), 1, 1, 
                                     facecolor=color, edgecolor='black', linewidth=1)
            ax.add_patch(rect)
            
            # Add text
            if not pd.isna(value):
                ax.text(j, i, f'{value:.1f}', ha='center', va='center',
                       fontsize=11, fontweight='bold')
    
    # Set labels
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(ratio_df.columns, fontsize=11, rotation=45, ha='right')
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(ratio_df.index, fontsize=11)
    
    ax.set_xlim(-0.5, n_cols-0.5)
    ax.set_ylim(n_rows-0.5, -0.5)
    
    ax.set_xlabel('Cumulative Position (bottom to top)', fontsize=11, fontweight='bold')
    
    ax.set_ylabel('Benchmarks', fontsize=11, fontweight='bold')
    
   # Set labels with grey background for 1.7°C benchmarks
    ax.set_yticks(range(n_rows))
    ytick_labels = []
    for label in ratio_df.index:
        if '1.7°C' in label or '1.7ºC' in label:
            ytick_labels.append(label)
            # Will set bbox after
        else:
            ytick_labels.append(label)
    
    ax.set_yticklabels(ytick_labels, fontsize=11)
    
    # Add grey background to 1.7°C labels
    for i, label in enumerate(ratio_df.index):
        if '1.7°C' in label or '1.7ºC' in label:
            ax.get_yticklabels()[i].set_bbox(dict(facecolor='#CCCCCC', edgecolor='none', 
                                                  alpha=0.6, pad=2))
        
    ax.set_title(f'{fuel_type.upper()} - {scenario_name} - {prod_scenario.upper()}\n' +
                 'Cumulative Ratios (Test Subject / Benchmark)',
                 fontsize=11, fontweight='bold')
    
    ax.tick_params(which='both', length=0)
    
    # Tight layout with minimal padding
    # plt.tight_layout(pad=0.1)
    # Manual margin control for maximum compactness
    # Maximum compactness
    fig.subplots_adjust(left=0.18, right=0.99, top=0.93, bottom=0.08)
    
    return fig

# ============================================================================
# GENERATE ALL HEATMAPS
# ============================================================================

# Set Nature journal style with better font size
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']#, 'Helvetica', 'DejaVu Sans']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.major.width'] = 0.8
plt.rcParams['ytick.major.width'] = 0.8

print("\nGenerating cumulative ratio heatmaps...")

scenario_names = sorted(oil_central_df.index)

for scenario_name in scenario_names:
    print(f"\nProcessing {scenario_name}...")
    
    # Oil - Central
    oil_central_ratios = calculate_cumulative_ratios(scenario_name, oil_central_df, benchmark_df, 'Oil')
    fig = create_heatmap_for_scenario(oil_central_ratios, scenario_name, 'Oil', 'Central')
    # plt.savefig(f"{output_dir}{scenario_name}_oil_central_heatmap.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{output_dir}{scenario_name}_oil_central_heatmap.pdf", format='pdf', bbox_inches='tight')
    plt.close()
    
    # Oil - EIA
    oil_eia_ratios = calculate_cumulative_ratios(scenario_name, oil_eia_df, benchmark_df, 'Oil')
    fig = create_heatmap_for_scenario(oil_eia_ratios, scenario_name, 'Oil', 'EIA')
    # plt.savefig(f"{output_dir}{scenario_name}_oil_eia_heatmap.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{output_dir}{scenario_name}_oil_eia_heatmap.pdf", format='pdf', bbox_inches='tight')
    plt.close()
    
    # Oil - Upper
    oil_upper_ratios = calculate_cumulative_ratios(scenario_name, oil_upper_df, benchmark_df, 'Oil')
    fig = create_heatmap_for_scenario(oil_upper_ratios, scenario_name, 'Oil', 'Upper')
    # plt.savefig(f"{output_dir}{scenario_name}_oil_upper_heatmap.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{output_dir}{scenario_name}_oil_upper_heatmap.pdf", format='pdf', bbox_inches='tight')
    plt.close()
    
    # Gas - Central
    gas_central_ratios = calculate_cumulative_ratios(scenario_name, gas_central_df, benchmark_df, 'Gas')
    fig = create_heatmap_for_scenario(gas_central_ratios, scenario_name, 'Gas', 'Central')
    # plt.savefig(f"{output_dir}{scenario_name}_gas_central_heatmap.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{output_dir}{scenario_name}_gas_central_heatmap.pdf", format='pdf', bbox_inches='tight')
    plt.close()
    
    # Gas - EIA
    gas_eia_ratios = calculate_cumulative_ratios(scenario_name, gas_eia_df, benchmark_df, 'Gas')
    fig = create_heatmap_for_scenario(gas_eia_ratios, scenario_name, 'Gas', 'EIA')
    # plt.savefig(f"{output_dir}{scenario_name}_gas_eia_heatmap.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{output_dir}{scenario_name}_gas_eia_heatmap.pdf", format='pdf', bbox_inches='tight')
    plt.close()
    
    # Gas - Upper
    gas_upper_ratios = calculate_cumulative_ratios(scenario_name, gas_upper_df, benchmark_df, 'Gas')
    fig = create_heatmap_for_scenario(gas_upper_ratios, scenario_name, 'Gas', 'Upper')
    # plt.savefig(f"{output_dir}{scenario_name}_gas_upper_heatmap.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{output_dir}{scenario_name}_gas_upper_heatmap.pdf", format='pdf', bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Generated 6 heatmaps for {scenario_name}")

print(f"\n✓ All heatmaps generated! Total: {len(scenario_names) * 6} heatmaps")

# Create legend
def create_legend_table(figsize=(10, 1.5)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('off')
    
    # Note: Pass and Fail categories represent clear/unambiguous passes and fails
    legend_labels = ['Pass (≤0.9)', 'Precautionary \nFailure (0.9-1.1)', 'Failure (1.1-2)', 'Major Failure (≥2)'] # Alt: Near Pass/Fail, Cuatious Failure 
    legend_colors = ['#FFFF00', '#FFA500', '#FF0000', '#8B0000']
    
    n_items = len(legend_labels)
    box_width = 0.8 / n_items
    
    for i, (label, color) in enumerate(zip(legend_labels, legend_colors)):
        x = i * box_width
        rect = mpatches.Rectangle((x, 0.3), box_width*0.95, 0.4, 
                                 facecolor=color, edgecolor='black', linewidth=2,
                                 transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(x + box_width*0.475, 0.5, label, ha='center', va='center',
               fontsize=11, fontweight='bold', transform=ax.transAxes)
    
    plt.tight_layout()
    # plt.savefig(output_dir + 'heatmap_legend.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir + 'heatmap_legend.pdf', format='pdf', bbox_inches='tight')
    plt.close()

create_legend_table()
print("✓ Legend created!")

# ============================================================================
# SAVE ALL HEATMAP DATA TO ONE SHEET
# ============================================================================

print("\n" + "="*80)
print("SAVING ALL HEATMAP DATA TO SINGLE SHEET")
print("="*80)

scenario_names = sorted(oil_central_df.index)

all_data = []

for scenario_name in scenario_names:
    print(f"Processing {scenario_name}...")
    
    # Process each combination
    for fuel_type, fuel_central, fuel_eia, fuel_upper in [
        ('Oil', oil_central_df, oil_eia_df, oil_upper_df),
        ('Gas', gas_central_df, gas_eia_df, gas_upper_df)
    ]:
        for prod_scenario, fuel_df in [
            ('Central', fuel_central),
            ('EIA', fuel_eia),
            ('Upper', fuel_upper)
        ]:
            # Calculate ratios
            ratio_df = calculate_cumulative_ratios(scenario_name, fuel_df, benchmark_df, fuel_type)
            
            # Add metadata columns
            ratio_df_copy = ratio_df.copy()
            ratio_df_copy.insert(0, 'Production_Scenario', prod_scenario)
            ratio_df_copy.insert(0, 'Fuel', fuel_type)
            ratio_df_copy.insert(0, 'Scenario', scenario_name)
            
            # Reset index to make Benchmark a column
            ratio_df_copy = ratio_df_copy.reset_index()
            ratio_df_copy = ratio_df_copy.rename(columns={'index': 'Benchmark'})
            
            all_data.append(ratio_df_copy)

# Combine all data
combined_df = pd.concat(all_data, ignore_index=True)

# Save to Excel
excel_filename = f"{output_dir}all_heatmap_data.xlsx"
combined_df.to_excel(excel_filename, sheet_name='All_Data', index=False)

print("\n✓ Saved: all_heatmap_data.xlsx")
print(f"  Total rows: {len(combined_df)}")
print(f"  Columns: {', '.join(combined_df.columns[:7])}... (and {len(combined_df.columns)-7} cumulative position columns)")
print("="*80)
