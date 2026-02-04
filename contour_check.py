import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import os

# ==============================================================================
# CONFIGURATION
# ==============================================================================
input_csv = "efd_normalized_final.csv"

# ==============================================================================
# 1. HELPER FUNCTIONS
# ==============================================================================

def reconstruct_contour(coeffs, num_points=200):
    t = np.linspace(0, 2 * np.pi, num_points)
    xt = np.zeros(num_points)
    yt = np.zeros(num_points)
    n_harmonics = 10

    for n in range(1, n_harmonics + 1):
        an = coeffs.get(f'a{n}', 0)
        bn = coeffs.get(f'b{n}', 0)
        cn = coeffs.get(f'c{n}', 0)
        dn = coeffs.get(f'd{n}', 0)
        
        xt += an * np.cos(n * t) + bn * np.sin(n * t)
        yt += cn * np.cos(n * t) + dn * np.sin(n * t)

    return xt, yt

def get_mean_coeffs(df_subset):
    means = {}
    for char in ['a', 'b', 'c', 'd']:
        for n in range(1, 11):
            col = f"{char}{n}"
            if col in df_subset.columns:
                means[col] = df_subset[col].mean()
            else:
                means[col] = 0
    return means

def generate_shape_grid(df, cell_type_name, output_filename):
    print(f"Generating balanced plot for {cell_type_name}...")
    
    subset = df[df['cell_type'] == cell_type_name].copy()
    if len(subset) == 0: return

    unique_groups = sorted(subset['species_locality'].unique())
    n_groups = len(unique_groups)
    
    n_cols = 4
    n_rows = math.ceil(n_groups / n_cols)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 4, n_rows * 3.5))
    axes = axes.flatten()
    
    for i, group_name in enumerate(unique_groups):
        ax = axes[i]
        group_data = subset[subset['species_locality'] == group_name]
        
        males = group_data[group_data['sex'].str.lower() == 'male']
        females = group_data[group_data['sex'].str.lower() == 'female']
        
        # --- 1. PLOT INDIVIDUALS (Background) ---
        # Increased alpha to 0.2 (visible) and using standard Blue/Red
        
        for idx, row in males.iterrows():
            ix, iy = reconstruct_contour(row)
            ix = np.append(ix, ix[0])
            iy = np.append(iy, iy[0])
            ax.plot(ix, iy, color='blue', alpha=0.2, linewidth=0.5)

        for idx, row in females.iterrows():
            ix, iy = reconstruct_contour(row)
            ix = np.append(ix, ix[0])
            iy = np.append(iy, iy[0])
            ax.plot(ix, iy, color='red', alpha=0.2, linewidth=0.5)

        # --- 2. PLOT MEANS (Foreground) ---
        # Thick bright lines
        
        if len(males) > 0:
            m_coeffs = get_mean_coeffs(males)
            mx, my = reconstruct_contour(m_coeffs)
            mx = np.append(mx, mx[0])
            my = np.append(my, my[0])
            # Bright Blue
            ax.plot(mx, my, color='blue', linewidth=2.5, label=f'Male (n={len(males)})')
            
        if len(females) > 0:
            f_coeffs = get_mean_coeffs(females)
            fx, fy = reconstruct_contour(f_coeffs)
            fx = np.append(fx, fx[0])
            fy = np.append(fy, fy[0])
            # Bright Red
            ax.plot(fx, fy, color='red', linewidth=2.5, linestyle='--', label=f'Female (n={len(females)})')

        ax.set_title(group_name, fontsize=10, fontweight='bold')
        ax.axis('equal')
        ax.axis('off')
        
        # Legend Logic (Robust for all Matplotlib versions)
        leg = ax.legend(fontsize=7, loc='lower right', frameon=False)
        for line in leg.get_lines():
            line.set_alpha(1.0) # Force legend icons to be opaque

    for j in range(i + 1, len(axes)):
        axes[j].axis('off')
        
    fig.suptitle(f"Wing Shape Variance: {cell_type_name}\n(Bold=Mean, Faint=Individuals)", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    plt.savefig(output_filename, dpi=300)
    print(f"Saved: {output_filename}")
    plt.close()

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.getcwd()

file_path = os.path.join(script_dir, input_csv)

if not os.path.exists(file_path):
    print(f"Error: {input_csv} not found.")
    exit()

print("Loading data...")
df = pd.read_csv(file_path)

df.columns = [c.lower() for c in df.columns]
if 'genus_species' in df.columns and 'species' not in df.columns:
    df.rename(columns={'genus_species': 'species'}, inplace=True)

df['species_clean'] = df['species'].astype(str).str.replace('_', ' ')
df['species_locality'] = df['species_clean'] + "\n(" + df['locality'].astype(str) + ")"

generate_shape_grid(df, "dm", os.path.join(script_dir, "contour_check_dm_final.png"))
generate_shape_grid(df, "pa2r", os.path.join(script_dir, "contour_check_pa2r_final.png"))

print("Done.")