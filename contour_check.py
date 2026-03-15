import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import string

# ==============================================================================
# CONFIGURATION
# ==============================================================================
input_csv = "efd_normalized_final.csv"
output_dir = "publication_figures_final"

# Visual Style
COLOR_MALE = '#1f77b4'   # Blue
COLOR_FEMALE = '#d62728' # Red

# Line Styles (Mean = Priority, Individuals = Quality Check Shadow)
ALPHA_INDIVIDUAL = 0.1   
LW_INDIVIDUAL = 0.5      
ALPHA_MEAN = 1.0         
LW_MEAN = 2.0            
LINESTYLE_MEAN = '-'     

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def reconstruct_contour(coeffs, num_points=250):
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
    for col in df_subset.columns:
        if col[0] in ['a','b','c','d'] and col[1:].isdigit():
            means[col] = df_subset[col].mean()
    return means

# ==============================================================================
# PLOTTING
# ==============================================================================

def plot_publication_ready(df):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Clean up strings just in case there are trailing spaces in the CSV
    df['cell_type'] = df['cell_type'].str.strip()
    df['species'] = df['species'].str.strip()
    df['locality'] = df['locality'].str.strip()
    df['sex'] = df['sex'].str.strip()

    # Get a MASTER LIST of all (species, locality) pairs across the entire dataset
    unique_pops = df[['species', 'locality']].drop_duplicates().sort_values(by=['species', 'locality'])
    pop_list = list(zip(unique_pops['species'], unique_pops['locality']))
    
    n_pops = len(pop_list)
    cols = 3
    rows = int(np.ceil(n_pops / cols))
    
    # Figure Size optimized for wide shapes to minimize vertical gaps
    fig_width = cols * 3.5
    fig_height = rows * 1.3 
    
    labels = list(string.ascii_lowercase) # 'a', 'b', 'c', ...
    
    cell_types = df['cell_type'].unique()

    for cell in cell_types:
        subset = df[df['cell_type'] == cell].copy()
        
        # Create a fresh figure for each cell type
        fig, axes = plt.subplots(rows, cols, figsize=(fig_width, fig_height))
        axes = axes.flatten()
        
        for i, (spec, loc) in enumerate(pop_list):
            ax = axes[i]
            pop_data = subset[(subset['species'] == spec) & (subset['locality'] == loc)]
            
            # --- 1. PLOT INDIVIDUALS (Layer 1: Faint Shadow) ---
            for _, row in pop_data.iterrows():
                row_dict = row.to_dict()
                ix, iy = reconstruct_contour(row_dict)
                c = COLOR_MALE if row['sex'] == 'Male' else COLOR_FEMALE
                ax.plot(ix, iy, color=c, alpha=ALPHA_INDIVIDUAL, linewidth=LW_INDIVIDUAL, zorder=1)

            # --- 2. PLOT MEANS (Layer 2: Bold Priority) ---
            for s_label, s_color in [('Male', COLOR_MALE), ('Female', COLOR_FEMALE)]:
                sex_data = pop_data[pop_data['sex'] == s_label]
                if not sex_data.empty:
                    m_coeffs = get_mean_coeffs(sex_data)
                    mx, my = reconstruct_contour(m_coeffs)
                    ax.plot(mx, my, color=s_color, alpha=ALPHA_MEAN, linewidth=LW_MEAN, 
                            linestyle=LINESTYLE_MEAN, zorder=2)

            # --- 3. SUBPLOT LABELS (a, b, c...) ---
            if i < len(labels):
                ax.text(0.02, 0.95, f"({labels[i]})", transform=ax.transAxes, 
                        fontsize=12, fontweight='bold', va='top', ha='left')
            
            ax.axis('off')
            ax.set_aspect('equal')

        # Cleanup unused axes
        for j in range(n_pops, len(axes)):
            axes[j].axis('off')

        # Tight spacing to eliminate vertical and horizontal gaps
        plt.subplots_adjust(wspace=0.05, hspace=0.02, left=0.02, right=0.98, bottom=0.02, top=0.98)
        
        # --- MODIFIED EXPORT SECTION ---
        base_filename = os.path.join(output_dir, f"Fig_{cell}_QC_style")
        
        # 1. Small HD PNG (300 DPI) - Best for LaTeX compiling
        plt.savefig(f"{base_filename}_Small_300dpi.png", dpi=300, bbox_inches='tight')
        
        # 2. Large HD PNG (600 DPI) - Best for final journal submission
        plt.savefig(f"{base_filename}_Large_600dpi.png", dpi=600, bbox_inches='tight')
        
        # 3. Vector PDF - Warning: Can crash LaTeX due to thousands of individual paths
        plt.savefig(f"{base_filename}_Vector.pdf", bbox_inches='tight')
        
        print(f"Generated 300dpi, 600dpi, and PDF versions for {cell.upper()}")
        plt.close(fig)

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()

    file_path = os.path.join(script_dir, input_csv)

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please ensure the CSV is in the same folder.")
    else:
        print("Loading data...")
        df_in = pd.read_csv(file_path)
        df_in.columns = [c.lower() for c in df_in.columns]
        plot_publication_ready(df_in)
        print("Done!")