#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test subject emissions

Created on Fri Feb 20 15:41:01 2026

@author: danielhorengreenford
"""
"""
COMPLETE EMISSIONS COMBINATIONS ANALYSIS
Generates all category assignments × orderings × scenarios for oil and gas
"""
import pandas as pd
# import numpy as np
from itertools import product, permutations
import os


# ============================================================================
# LOAD DATA FROM EXCEL
# ============================================================================

print("="*80)
print("LOADING DATA")
print("="*80)

loc = "/Users/danielhorengreenford/Documents/Research/Paper 2 - climate tests/"

# Load the Excel file
excel_file = pd.ExcelFile(loc + 'Data-Climate_tests-clean.xlsx')

# Load specific sheets
oil_emissions = pd.read_excel(excel_file, sheet_name='oil_emissions', index_col=0)
gas_emissions = pd.read_excel(excel_file, sheet_name='gas_emissions', index_col=0)
foi_oil_emissions = pd.read_excel(excel_file, sheet_name='foi_oil_emissions')
foi_gas_emissions = pd.read_excel(excel_file, sheet_name='foi_gas_emissions')
test_subjects = pd.read_excel(excel_file, sheet_name='test_subjects')

print(f"✓ Loaded oil_emissions: {oil_emissions.shape}")
print(f"✓ Loaded gas_emissions: {gas_emissions.shape}")
print(f"✓ Loaded foi_oil_emissions: {foi_oil_emissions.shape}")
print(f"✓ Loaded foi_gas_emissions: {foi_gas_emissions.shape}")
print(f"✓ Loaded test_subjects: {test_subjects.shape}")

# Clean up field names and category strings
for foi_df in [foi_oil_emissions, foi_gas_emissions]:
    foi_df['Field_name'] = foi_df['Field_name'].str.replace('\xa0', '').str.strip()
    # Clean up extra quotes in category column
    foi_df['category'] = foi_df['category'].str.replace('""', '"')
    foi_df['category'] = foi_df['category'].str.strip()

del foi_df

print("✓ Cleaned FoI data")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_categories(foi_df):
    """Extract possible categories for each field"""
    field_categories = {}
    for idx, row in foi_df.iterrows():
        field = row['Field_name']
        cat_string = row['category']
        # Parse "Cat1", "Cat2" string
        categories = [c.strip().strip('"').strip("'") for c in cat_string.split(',')]
        field_categories[field] = categories
    return field_categories

def normalize_category(cat):
    """Normalize category names to match base emissions index"""
    mapping = {
        'Reserves': 'Reserves',
        'Contingent resources in producing fields': 'Producing fields',
        'Contingent resources in proposed new developments': 'Proposed new developments',
        'Licensed marginal discoveries': 'Licensed marginal discoveries',
        'Unlicensed marginal discoveries': 'Unlicensed marginal discoveries'
    }
    return mapping.get(cat, cat)

def generate_category_assignments(field_categories):
    """Generate all possible ways to assign fields to categories"""
    fields = list(field_categories.keys())
    options = [field_categories[field] for field in fields]
    assignments = []
    for combo in product(*options):
        assignment = dict(zip(fields, combo))
        assignments.append(assignment)
    return assignments

def generate_orderings_for_assignment(assignment):
    """Generate all possible orderings of fields within each category"""
    # Group fields by category
    category_to_fields = {}
    for field, cat in assignment.items():
        normalized_cat = normalize_category(cat)
        if normalized_cat not in category_to_fields:
            category_to_fields[normalized_cat] = []
        category_to_fields[normalized_cat].append(field)
    
    # Get all permutations for each category
    category_permutations = {}
    for cat, fields in category_to_fields.items():
        perms = list(permutations(fields))
        category_permutations[cat] = perms
    
    categories_with_fields = list(category_permutations.keys())
    
    if not categories_with_fields:
        return [{}]
    
    # Combine permutations across categories
    perm_lists = [category_permutations[cat] for cat in categories_with_fields]
    
    all_orderings = []
    for perm_combo in product(*perm_lists):
        ordering = {}
        for cat, field_order in zip(categories_with_fields, perm_combo):
            ordering[cat] = list(field_order)
        all_orderings.append(ordering)
    
    return all_orderings

def get_base_emissions(base_emissions, scenario):
    """Get base emissions for a scenario"""
    if scenario == 'central':
        return base_emissions['Med'].copy()
    elif scenario == 'upper':
        return base_emissions['High'].copy()
    elif scenario == 'eia':
        base = pd.Series(dtype=float)
        base['Reserves'] = base_emissions.loc['Reserves', 'Med']
        for cat in base_emissions.index:
            if cat != 'Reserves':
                base[cat] = base_emissions.loc[cat, 'High']
        return base
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

def create_ordered_emissions(base_emissions, foi_df, assignment, ordering, scenario):
    """Create ordered emissions for one combination"""
    
    # Get base emissions
    base = get_base_emissions(base_emissions, scenario)
    
    # Get FoI emissions - ALWAYS use P10 for worst-case assessment (except Central)
    foi_values = {}
    for field in assignment.keys():
        foi_row = foi_df[foi_df['Field_name'] == field]
        if len(foi_row) > 0:
            if scenario == 'central':
                foi_values[field] = foi_row.iloc[0]['P50']
            else:  # 'upper' or 'eia' - worst-case assessment
                foi_values[field] = foi_row.iloc[0]['P10']
    
    # Subtract FoI from assigned categories (avoid double counting)
    # Need to subtract what's already IN the base, not what we're adding
    for field, category in assignment.items():
        if field in foi_values:
            normalized_cat = normalize_category(category)
            if normalized_cat in base.index:
                foi_row = foi_df[foi_df['Field_name'] == field]
                
                # Determine what to subtract based on what's in the base category
                if scenario == 'eia' and normalized_cat == 'Reserves':
                    # Reserves base uses P50, so subtract P50
                    subtraction_amount = foi_row.iloc[0]['P50']
                else:
                    # For all other cases, subtract what we're adding back
                    subtraction_amount = foi_values[field]
                
                base[normalized_cat] -= subtraction_amount
    
    # Build ordered result
    result = {}
    
    category_order = [
        'Reserves',
        'Producing fields',
        'Proposed new developments',
        'Licensed marginal discoveries',
        'Unlicensed marginal discoveries'
    ]
    
    for cat in category_order:
        # Add fields in this category (in specified order)
        if cat in ordering:
            for field in ordering[cat]:
                if field in foi_values:
                    result[field] = foi_values[field]
        
        # Add base category (with FoI subtracted)
        result[cat] = base[cat]
    
    return result

# ============================================================================
# PROCESS ONE FUEL TYPE
# ============================================================================

def process_fuel_type(base_emissions, foi_df, fuel_type):
    """
    Process one fuel type through all combinations
    
    Parameters:
    -----------
    base_emissions : pd.DataFrame
        Base emissions (oil_emissions or gas_emissions)
    foi_df : pd.DataFrame
        Fields of interest emissions (foi_oil_emissions or foi_gas_emissions)
    fuel_type : str
        'oil' or 'gas' (for display purposes)
    
    Returns:
    --------
    dict : {scenario: DataFrame}
    """
    
    print(f"\n{'='*80}")
    print(f"PROCESSING {fuel_type.upper()}")
    print('='*80)
    
    # Parse categories
    field_categories = parse_categories(foi_df)
    print(f"✓ Fields: {list(field_categories.keys())}")
    print(f"✓ Parsed {len(field_categories)} fields with category options")
    
    # Generate category assignments
    category_assignments = generate_category_assignments(field_categories)
    print(f"✓ Generated {len(category_assignments)} category assignments")
    
    # Process each scenario
    results_dict = {}
    scenarios = ['central', 'upper', 'eia']
    
    for scenario in scenarios:
        print(f"\n  Processing {scenario.upper()} scenario...")
        
        all_results = []
        
        for assign_idx, assignment in enumerate(category_assignments):
            # Get all orderings for this assignment
            orderings = generate_orderings_for_assignment(assignment)
            
            for order_idx, ordering in enumerate(orderings):
                # Create ordered emissions
                emissions = create_ordered_emissions(
                    base_emissions=base_emissions,
                    foi_df=foi_df,
                    assignment=assignment,
                    ordering=ordering,
                    scenario=scenario
                )
                
                # Store result
                result = {
                    'assignment_id': assign_idx,
                    'ordering_id': order_idx,
                    'assignment': str(assignment),
                    'ordering': str(ordering),
                    **emissions,
                    'TOTAL': sum(emissions.values())
                }
                
                all_results.append(result)
            
            # Progress update
            if (assign_idx + 1) % 2 == 0 or (assign_idx + 1) == len(category_assignments):
                print(f"    Processed {assign_idx + 1}/{len(category_assignments)} assignments...")
        
        # Convert to DataFrame
        results_df = pd.DataFrame(all_results)
        results_dict[scenario] = results_df
        
        print(f"    ✓ Generated {len(results_df)} combinations")
        print(f"    Total range: {results_df['TOTAL'].min():.2f} - {results_df['TOTAL'].max():.2f} MtCO2")
    
    return results_dict

# ============================================================================
# MAIN PROCESSING
# ============================================================================

# Process oil
oil_results = process_fuel_type(
    base_emissions=oil_emissions,
    foi_df=foi_oil_emissions,
    fuel_type='oil'
)

# Process gas
gas_results = process_fuel_type(
    base_emissions=gas_emissions,
    foi_df=foi_gas_emissions,
    fuel_type='gas'
)

# ============================================================================
# SAVE RESULTS
# ============================================================================

print("\n" + "="*80)
print("SAVING RESULTS")
print("="*80)

output_dir = loc + 'outputs/'
os.makedirs(output_dir, exist_ok=True)

# Save oil results
for scenario, df in oil_results.items():
    filename = f'{output_dir}oil_{scenario}_all_combinations.csv'
    df.to_csv(filename, index=False)
    print(f"✓ Saved: oil_{scenario}_all_combinations.csv ({len(df)} rows)")

# Save gas results
for scenario, df in gas_results.items():
    filename = f'{output_dir}gas_{scenario}_all_combinations.csv'
    df.to_csv(filename, index=False)
    print(f"✓ Saved: gas_{scenario}_all_combinations.csv ({len(df)} rows)")

# Save summary
summary_data = []
for fuel in ['oil', 'gas']:
    results = oil_results if fuel == 'oil' else gas_results
    for scenario, df in results.items():
        summary_data.append({
            'fuel': fuel,
            'scenario': scenario,
            'n_combinations': len(df),
            'min_total': df['TOTAL'].min(),
            'max_total': df['TOTAL'].max(),
            'mean_total': df['TOTAL'].mean()
        })

summary_df = pd.DataFrame(summary_data)
summary_df.to_csv(f'{output_dir}summary.csv', index=False)
print("\n✓ Saved: summary.csv")

print("\n" + "="*80)
print("COMPLETE!")
print("="*80)
print(f"\nAll results saved to: {output_dir}")
print("\nSummary:")
print(summary_df.to_string(index=False))
print("\nResults dictionaries available:")
print("  - oil_results['central'], oil_results['upper'], oil_results['eia']")
print("  - gas_results['central'], gas_results['upper'], gas_results['eia']")

# ============================================================================
# PARSE TEST SUBJECTS WITH CATEGORY COLUMNS (FIXED)
# ============================================================================

def denormalize_category(normalized_cat):
    """Convert normalized category name back to full name"""
    reverse_mapping = {
        'Reserves': 'Reserves',
        'Producing fields': 'Contingent resources in producing fields',
        'Proposed new developments': 'Contingent resources in proposed new developments',
        'Licensed marginal discoveries': 'Licensed marginal discoveries',
        'Unlicensed marginal discoveries': 'Unlicensed marginal discoveries'
    }
    return reverse_mapping.get(normalized_cat, normalized_cat)

def parse_test_subject_with_categories(test_subjects_df, scenario_name):
    """
    Parse test subject using both the scenario column and category column
    
    Returns:
    --------
    tuple : (assignment, ordering)
        assignment uses FULL category names
        ordering uses NORMALIZED category names
    """
    
    # Get the scenario column and its corresponding category column
    scenario_col = test_subjects_df[scenario_name]
    
    # Find the category column (should be next column after scenario)
    scenario_idx = test_subjects_df.columns.get_loc(scenario_name)
    category_col_name = test_subjects_df.columns[scenario_idx + 1]
    category_col = test_subjects_df[category_col_name]
    
    # Parse each row
    assignment = {}
    category_field_order = {}  # {normalized_category: [fields in order]}
    
    for idx, (item, cat) in enumerate(zip(scenario_col, category_col)):
        if pd.isna(item):
            continue
            
        item = str(item).strip()
        cat = str(cat).strip() if not pd.isna(cat) else ''
        
        # Check if this is a field (has a category specified)
        if cat and cat != 'category':  # Skip header row
            # Clean up the item
            item_clean = item.replace('\xa0', '').strip()
            
            # Find matching field from FoI
            matched_field = None
            for field in foi_oil_emissions['Field_name']:
                field_clean = field.strip()
                if field_clean in item_clean or item_clean in field_clean:
                    matched_field = field_clean
                    break
            
            if matched_field:
                # Convert category to full name for assignment
                full_cat = denormalize_category(cat)
                assignment[matched_field] = full_cat
                
                # Track ordering (keep normalized for consistency)
                normalized_cat = normalize_category(full_cat)
                if normalized_cat not in category_field_order:
                    category_field_order[normalized_cat] = []
                category_field_order[normalized_cat].append(matched_field)
    
    # Convert to ordering format
    ordering = {cat: fields for cat, fields in category_field_order.items() if fields}
    
    return assignment, ordering

# ============================================================================
# IDENTIFY TEST SUBJECT SCENARIOS (ALL OF THEM)
# ============================================================================

print("\n" + "="*80)
print("IDENTIFYING ALL TEST SUBJECT SCENARIOS")
print("="*80)

# Find all scenario columns (columns that start with "Scenario_")
scenario_columns = [col for col in test_subjects.columns if col.startswith('Scenario_')]
print(f"Found {len(scenario_columns)} scenarios: {scenario_columns}")

test_subject_matches = {}

for scenario_name in scenario_columns:
    print(f"\n{scenario_name}:")
    
    # Parse this scenario
    assignment, ordering = parse_test_subject_with_categories(
        test_subjects,
        scenario_name
    )
    
    print(f"  Assignment: {assignment}")
    print(f"  Ordering: {ordering}")
    
    # Find matching combination in results
    match_idx = None
    for idx, row in oil_results['central'].iterrows():
        row_assignment = eval(row['assignment'])
        row_ordering = eval(row['ordering'])
        
        if row_assignment == assignment and row_ordering == ordering:
            match_idx = idx
            break
    
    if match_idx is not None:
        match_row = oil_results['central'].iloc[match_idx]
        test_subject_matches[scenario_name] = {
            'assignment_id': match_row['assignment_id'],
            'ordering_id': match_row['ordering_id'],
            'row_index': match_idx,
            'assignment': assignment,
            'ordering': ordering
        }
        print(f"  ✓ Found match: Row {match_idx}")
        print(f"    assignment_id={match_row['assignment_id']}, ordering_id={match_row['ordering_id']}")
        print(f"    Total (central): {match_row['TOTAL']:.2f} MtCO2")
    else:
        print("  ✗ No match found")
        test_subject_matches[scenario_name] = None

print("\n" + "="*80)
matched_count = len([v for v in test_subject_matches.values() if v is not None])
print(f"MATCHED {matched_count}/{len(scenario_columns)} SCENARIOS")
print("="*80)

# If we have matches, show summary
if matched_count > 0:
    print("\nMatched scenarios summary:")
    for scenario_name, match_info in test_subject_matches.items():
        if match_info:
            print(f"  {scenario_name}: assignment_id={match_info['assignment_id']}, ordering_id={match_info['ordering_id']}")
            
# ============================================================================
# EXTRACT TEST SUBJECT SCENARIOS FOR OIL AND GAS
# ============================================================================

print("\n" + "="*80)
print("EXTRACTING TEST SUBJECT SCENARIOS FOR OIL AND GAS")
print("="*80)

def extract_test_subjects(foi_df, results_dict, test_subjects_df, fuel_type):
    """
    Extract test subject scenarios for one fuel type
    
    Parameters:
    -----------
    foi_df : pd.DataFrame
        FoI emissions dataframe
    results_dict : dict
        Results dictionary with scenarios
    test_subjects_df : pd.DataFrame
        Test subjects dataframe
    fuel_type : str
        'oil' or 'gas'
    
    Returns:
    --------
    dict : {scenario: {scenario_name: DataFrame with extracted rows}}
    """
    
    print(f"\n{fuel_type.upper()}:")
    
    # Find all scenario columns
    scenario_columns = [col for col in test_subjects_df.columns if col.startswith('Scenario_')]
    print(f"  Found {len(scenario_columns)} test scenarios")
    
    extracted_scenarios = {}
    
    for prod_scenario in ['central', 'upper', 'eia']:
        print(f"\n  Production scenario: {prod_scenario.upper()}")
        extracted_scenarios[prod_scenario] = {}
        
        for scenario_name in scenario_columns:
            # Parse this scenario
            assignment, ordering = parse_test_subject_with_categories(
                test_subjects_df,
                scenario_name
            )
            
            # Find matching combination
            match_idx = None
            for idx, row in results_dict[prod_scenario].iterrows():
                row_assignment = eval(row['assignment'])
                row_ordering = eval(row['ordering'])
                
                if row_assignment == assignment and row_ordering == ordering:
                    match_idx = idx
                    break
            
            if match_idx is not None:
                # Extract this row
                extracted_scenarios[prod_scenario][scenario_name] = results_dict[prod_scenario].iloc[match_idx]
                print(f"    ✓ {scenario_name}: Found (Total={results_dict[prod_scenario].iloc[match_idx]['TOTAL']:.2f})")
            else:
                print(f"    ✗ {scenario_name}: Not found")
    
    return extracted_scenarios

# Extract for oil
oil_test_subjects = extract_test_subjects(
    foi_oil_emissions,
    oil_results,
    test_subjects,
    'oil'
)

# Extract for gas
gas_test_subjects = extract_test_subjects(
    foi_gas_emissions,
    gas_results,
    test_subjects,
    'gas'
)

print("\n" + "="*80)
print("EXTRACTION COMPLETE")
print("="*80)

# ============================================================================
# CREATE PLOTS WITH SHARED Y-AXES - NATURE STYLE, GtCO2
# ============================================================================

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np

# Set Nature journal style with better font size
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']#, 'Helvetica', 'DejaVu Sans']
plt.rcParams['font.size'] = 11  # Increased from 8, for better visibility, though Nature uses font size 8? But scale changes in vector graphic?
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.major.width'] = 0.8
plt.rcParams['ytick.major.width'] = 0.8

def create_oil_gas_panel_plot(oil_dict, gas_dict, scenario_name, figsize=(12, 6)):
    """
    Create 1x2 panel plot with shared y-axes in GtCO2
    """
    
    fig, axes = plt.subplots(1, 2, figsize=figsize, sharey=True) #Toggle sharey=False/True to share y-axis
    
    # Define base category colors - NEUTRAL PALETTE
    category_colors = {
        'Reserves': '#4E79A7',
        'Producing fields': '#59A14F',
        'Proposed new developments': '#E15759',
        'Licensed marginal discoveries': '#F28E2B',
        'Unlicensed marginal discoveries': '#B07AA1'
    }
    
    # metadata_cols = ['assignment_id', 'ordering_id', 'assignment', 'ordering', 'TOTAL']
    
    # Production scenarios in order: Central, EIA, Upper
    prod_scenarios = ['central', 'eia', 'upper']
    prod_labels = ['Central', 'EIA', 'Upper']
    
    # Get the stacking order from test_subjects
    stacking_order = []
    category_mapping = {}
    
    for idx, (item, cat) in enumerate(zip(test_subjects[scenario_name], test_subjects.iloc[:, test_subjects.columns.get_loc(scenario_name) + 1])):
        if pd.isna(item):
            break
        item = str(item).strip()
        cat = str(cat).strip() if not pd.isna(cat) else ''
        
        # Parse items
        if item == 'Reserves':
            stacking_order.append(('Reserves', 'base'))
        elif item == 'Producing fields' or 'Producing fields' in item and not item.startswith('w/ '):
            stacking_order.append(('Producing fields', 'base'))
        elif item == 'Proposed new developments' or ('Proposed new developments' in item and not item.startswith('w/ ')):
            stacking_order.append(('Proposed new developments', 'base'))
        elif item == 'Licensed marginal discoveries' or ('Licensed marginal' in item and 'Unlicensed' not in item):
            stacking_order.append(('Licensed marginal discoveries', 'base'))
        elif item == 'Unlicensed marginal discoveries' or 'Unlicensed marginal' in item:
            stacking_order.append(('Unlicensed marginal discoveries', 'base'))
        elif 'Rosebank (Phase 1)' in item or 'Rosebank 1' in item:
            stacking_order.append(('Rosebank (Phase 1)', 'foi'))
            category_mapping['Rosebank (Phase 1)'] = cat
        elif 'Jackdaw' in item:
            stacking_order.append(('Jackdaw', 'foi'))
            category_mapping['Jackdaw'] = cat
        elif 'Cambo' in item:
            stacking_order.append(('Cambo', 'foi'))
            category_mapping['Cambo'] = cat
        elif 'Rosebank (Phase 2)' in item or 'Rosebank 2' in item:
            stacking_order.append(('Rosebank (Phase 2)', 'foi'))
            category_mapping['Rosebank (Phase 2)'] = cat
    
    # Process both oil and gas
    for panel_idx, (fuel_type, test_subjects_dict) in enumerate([('Oil', oil_dict), ('Gas', gas_dict)]):
        ax = axes[panel_idx]
        
        x_positions = np.arange(len(prod_scenarios)) * 0.6  # Multiply by 0.6 to bring closer
        bar_width = 0.35  # Changed from 0.7 to match benchmark
        
        panel_max_height = 0
        foi_labels = {}  # Only track FoI fields
        
        for x_idx, prod_scenario in enumerate(prod_scenarios):
            row_data = test_subjects_dict[prod_scenario][scenario_name]
            
            bottom = 0
            
            # Build stack in EXACT test_subjects order
            for stack_item, item_type in stacking_order:
                value = None
                color = None
                is_foi = (item_type == 'foi')
                
                if item_type == 'base':
                    # Base category
                    value = row_data.get(stack_item)
                    if value is None or pd.isna(value):
                        continue
                    value = value / 1000  # Convert to GtCO2
                    color = category_colors.get(stack_item, '#808080')
                    
                else:  # foi
                    # Find the FoI value
                    for col in row_data.index:
                        if col.strip() == stack_item.strip():
                            value = row_data[col]
                            break
                    
                    if value is None or pd.isna(value) or value <= 0:
                        continue
                    
                    value = value / 1000  # Convert to GtCO2
                    
                    # Get color based on assigned category
                    assigned_cat = category_mapping.get(stack_item)
                    base_color = category_colors.get(assigned_cat, '#808080')
                    rgba = mcolors.to_rgba(base_color)
                    color = tuple([0.4 + 0.6 * c for c in rgba[:3]]) + (0.9,)
                
                # Draw segment
                ax.bar(x_positions[x_idx], value, bar_width, bottom=bottom,
                       color=color, edgecolor='white', linewidth=0.8)
                
                segment_center = bottom + value / 2
                
                # Only track FoI fields for labeling on the rightmost bar of GAS panel only
                if is_foi and x_idx == 2 and panel_idx == 0:  # panel_idx = 0 for oil and 1 for gas; Only for Upper scenario AND Oil/Gas panel
                    label_text = stack_item.replace('Rosebank (Phase 1)', 'Rosebank (Phase 1)')\
                                       .replace('Rosebank (Phase 2)', 'Rosebank (Phase 2)')\
                                       .replace('Jackdaw', 'Jackdaw')\
                                       .replace('Cambo', 'Cambo')
                    
                    if label_text not in foi_labels:
                        foi_labels[label_text] = {
                            'x': x_positions[x_idx],
                            'y': segment_center
                        }
                    
                bottom += value
            
            # Track the actual total for this bar
            panel_max_height = max(panel_max_height, row_data['TOTAL'] / 1000)
        
        # # Set y-axis for THIS panel only
        # y_max = panel_max_height * 1.15
        # ax.set_ylim(0, y_max)
        
        # Add labels only for FoI fields on the rightmost bar (Gas panel only)
        if panel_idx == 0 and foi_labels:  # Only for Oil (panel_idx= 0) or Gas (panel_idx= 1) panel
            # num_labels = len(foi_labels)
            # label_y_spacing = panel_max_height * 0.15
            # label_y_start = panel_max_height * 0.3
            
            # for i, (field_name, pos_info) in enumerate(foi_labels.items()):
            #     label_x = 1.4  # Adjusted for new bar positions  # Fixed position inside plot
            #     label_y = label_y_start + (i * label_y_spacing)
            
            # for i, (field_name, pos_info) in enumerate(foi_labels.items()):
            #     label_x = 1.4  # Adjusted for new bar positions
            #     # label_y = pos_info['y']  # Align with segment center
            #     label_y = pos_info['y'] + (i - len(foi_labels)/2) * 0.05  # Slight vertical spread
                
            #     # Draw connector line
            #     ax.plot([pos_info['x'] + bar_width/2, label_x], 
            #            [pos_info['y'], label_y],
            #            'k-', linewidth=0.5, alpha=0.4)
                
            #     ax.plot(pos_info['x'] + bar_width/2, pos_info['y'], 
            #            'ko', markersize=2, alpha=0.5)
                
            #     # Add label
            #     ax.text(label_x, label_y, field_name,
            #            ha='left', va='center', fontsize=8,
            #            bbox=dict(boxstyle='round,pad=0.3', 
            #                    facecolor='white', edgecolor='gray', 
            #                    alpha=0.95, linewidth=0.7))
       
    
            for i, (field_name, pos_info) in enumerate(foi_labels.items()):
                label_x = 1.4  # Adjusted for new bar positions
                
                # Alternate offset: odd indices down, even indices up
                if i % 2 == 0:  # First (0), third (2) - offset down
                    offset = -0.12
                else:  # Second (1), fourth (3) - offset up
                    offset = 0.12
                
                label_y = pos_info['y'] + offset
                
                # Draw connector line
                ax.plot([pos_info['x'] + bar_width/2, label_x], 
                       [pos_info['y'], label_y],
                       'k-', linewidth=0.5, alpha=0.4)
                
                ax.plot(pos_info['x'] + bar_width/2, pos_info['y'], 
                       'ko', markersize=2, alpha=0.5)
                
                # Add label
                ax.text(label_x, label_y, field_name,
                       ha='left', va='center', fontsize=11,
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor='white', edgecolor='gray', 
                               alpha=0.95, linewidth=0.7))
        
        # Formatting - Nature style
        ax.set_xlabel('Production Scenario', fontsize=11, fontweight='normal')
        ax.set_title(f"{fuel_type}", fontsize=11, fontweight='bold', pad=10)
        
        ax.set_xticks(x_positions)
        ax.set_xticklabels(prod_labels, fontsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
        
        # Set very tight x-axis limits to match benchmark spacing
        ax.set_xlim(-0.4, 1.6)  # Adjusted for positions at 0, 0.6, 1.2
        
        # Only left panel gets y-label
        if panel_idx == 0:
            ax.set_ylabel('Downstream test subject emissions (GtCO$_2$)', fontsize=11, fontweight='normal')
    
    # Legend - Nature style
    legend_elements = []
    
    category_labels = {
        'Reserves': 'Reserves',
        'Producing fields': 'Producing fields',
        'Proposed new developments': 'Proposed new developments',
        'Licensed marginal discoveries': 'Licensed marginal discoveries',
        'Unlicensed marginal discoveries': 'Unlicensed marginal discoveries'
    }
    
    for cat, color in category_colors.items():
        legend_elements.append(mpatches.Patch(facecolor=color, edgecolor='white', 
                                              label=category_labels[cat]))
    
    legend_elements.append(mpatches.Patch(facecolor='lightgray', edgecolor='black',
                                         label='Fields under regulatory scrutiny (lighter)', alpha=0.7))
    
    fig.legend(handles=legend_elements,
              loc='lower center', bbox_to_anchor=(0.5, -0.1),
              ncol=3, frameon=True, fontsize=11,
              title='Categories (solid) | Fields under regulatory scrutiny (lighter shades of assigned category)',
              title_fontsize=11)
    
    plt.suptitle(f"{scenario_name.replace('Scenario_', 'Scenario ')}", 
                fontsize=12, fontweight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    
    return fig

# Generate all plots
print("\nGenerating plots with Nature style in GtCO2...")

scenario_names = sorted(oil_test_subjects['central'].keys())

for scenario_name in scenario_names:
    fig = create_oil_gas_panel_plot(oil_test_subjects, gas_test_subjects, scenario_name)
    base_filename = f"{output_dir}{scenario_name}_oil_gas-share_y"
    
    # plt.savefig(f"{base_filename}.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{base_filename}.svg", format='svg', bbox_inches='tight')
    # plt.savefig(f"{base_filename}.pdf", format='pdf', bbox_inches='tight')
    
    print(f"  ✓ Saved: {scenario_name}_oil_gas (.png, .svg, .pdf)")
    plt.close()

print("\n✓ All plots generated!")

# ============================================================================
# SAVE EXTRACTED TEST SUBJECTS TO CSV
# ============================================================================

print("\n" + "="*80)
print("SAVING EXTRACTED TEST SUBJECTS")
print("="*80)

# Convert to DataFrames and save
for fuel_type, test_subjects_dict in [('oil', oil_test_subjects), ('gas', gas_test_subjects)]:
    for prod_scenario, scenarios in test_subjects_dict.items():
        if scenarios:
            # Convert dict of Series to DataFrame
            df = pd.DataFrame(scenarios).T  # Transpose so scenarios are rows
            df.index.name = 'scenario'
            
            filename = f'{output_dir}{fuel_type}_{prod_scenario}_test_subjects.csv'
            df.to_csv(filename)
            print(f"✓ Saved: {fuel_type}_{prod_scenario}_test_subjects.csv ({len(df)} scenarios)")

print("\n✓ All test subject scenarios saved!")            
