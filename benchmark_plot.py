#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark plot 
Created on Wed Feb 25 20:36:35 2026

@author: danielhorengreenford
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import matplotlib.patches as mpatches

# Output directory
output_dir = "/Users/danielhorengreenford/Documents/Research/Paper 2 - climate tests/"

# Read the CSV file
csv_path = "/Users/danielhorengreenford/Documents/Research/Paper 2 - climate tests/benchmarks-GtCO2-2025_2100.csv"  
df = pd.read_csv(csv_path)

# Print to check the data
print("Data loaded:")
print(df)
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")

# Check backend
print(f"\nMatplotlib backend: {plt.get_backend()}")

# Set font for Nature journal style (Arial/Helvetica)
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']#, 'Helvetica', 'DejaVu Sans']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.major.width'] = 0.8
plt.rcParams['ytick.major.width'] = 0.8

# Read the CSV file
# csv_path = "/path/to/your/file.csv"  # UPDATE THIS PATH
# df = pd.read_csv(csv_path)

# Create figure
print("Creating figure...")
fig, ax = plt.subplots(figsize=(10, 6))
# fig, ax = plt.subplots(figsize=(7, 4))

# Define colors matching the benchmarks
color_map = {
    'Cost-optimal': '#2a2aff',
    'Current trends': '#ffbca0',
    'Equity via partial reallocation': '#e91da1',
    'Equity via tax on wealthy producers': '#be00dd',
    'Equity via full reallocation': '#be00dd'
}

# Prepare data
n_groups = len(df)
x = np.arange(n_groups)
width = 0.35

# Get oil and gas values
oil_values = df['Oil'].values
gas_values = df['Gas'].values

# Get colors for each bar based on Benchmark
colors = [color_map.get(benchmark, '#808080') for benchmark in df['Benchmarks']]

# Create bars
print("Creating bars...")
bars_oil = ax.bar(x - width/2, oil_values, width, color=colors, 
                  edgecolor='white', linewidth=0.8, label='Oil')
bars_gas = ax.bar(x + width/2, gas_values, width, color=colors,
                  edgecolor='white', linewidth=0.8, label='Gas')

# Add target labels centered between oil and gas bars
print("Adding labels...")
# Add target labels centered between oil and gas bars
for i, (oil_bar, gas_bar) in enumerate(zip(bars_oil, bars_gas)):
    # Get the max height between oil and gas
    max_height = max(oil_bar.get_height(), gas_bar.get_height())
    
    # Center position between the two bars
    center_x = x[i]
    
    # Get target label
    target = df['Target'].iloc[i]
    
    # Add label above the taller bar with white background box
    ax.text(center_x, 0.5*max_height, target,  # Moved down 
           ha='center', va='bottom', fontsize=11,  # Increased from 7
           rotation=90,
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                    edgecolor='none', alpha=0.8))  # White box with no border

# Formatting
print("Setting up axes...")

ax.set_ylim(0, 1.5)
# Use mathtext for subscript - this works with any font
ax.set_ylabel('Downstream benchmark emissions (GtCO$_2$)', fontweight='normal') #fontsize=11,
ax.grid(axis='y', alpha=0.3, linestyle='-', linewidth=0.5)
ax.set_axisbelow(True)

# Remove x-axis labels
ax.set_xticks(x)
ax.set_xticklabels([])

# # Add text labels for Oil and Gas at bottom
# ax.text(0.25, -0.12, 'Oil', transform=ax.transAxes, fontsize=8, 
#         ha='center', weight='bold')
# ax.text(0.75, -0.12, 'Gas', transform=ax.transAxes, fontsize=8, 
#         ha='center', weight='bold')

# Create custom legend
print("Adding legend...")
legend_elements = [
    mpatches.Patch(facecolor='#2a2aff',  label='Cost-optimal'),#edgecolor='black',
    mpatches.Patch(facecolor='#ffbca0',  label='Current trends'),
    mpatches.Patch(facecolor='#e91da1',  label='Equity via partial reallocation'),
    # mpatches.Patch(facecolor='#be00dd', edgecolor='black', label='Equity via tax on wealthy producers'),
    mpatches.Patch(facecolor='#be00dd',  label='Equity via full reallocation')
]

# Add legend in top right corner
ax.legend(handles=legend_elements, loc='upper right', frameon=True, 
          title='Benchmarks', title_fontsize=11) #          fontsize=9

# Save at high resolution for publication
# plt.savefig(output_dir + 'benchmark_nature-4.png', dpi=300, bbox_inches='tight')
plt.savefig(output_dir + 'benchmark_nature-4.pdf', format='pdf', bbox_inches='tight')
plt.savefig(output_dir + 'benchmark_nature-4.svg', format='svg', bbox_inches='tight')
print("About to show...")
plt.show()
print("Plot shown!")
print("✓ Nature-style benchmark plot created!")

# # To check available fonts on your system:
# print("\nAvailable fonts with 'Arial' or 'Helvetica':")
# from matplotlib import font_manager
# fonts = [f.name for f in font_manager.fontManager.ttflist if 'Arial' in f.name or 'Helvetica' in f.name]
# print(set(fonts))
