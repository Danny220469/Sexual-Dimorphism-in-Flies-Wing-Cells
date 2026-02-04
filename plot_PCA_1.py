import pandas as pd
import plotly.express as px
import os

# ==============================================================================
# 1. SETUP PATHS
# ==============================================================================
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.getcwd()

def get_path(filename):
    return os.path.join(script_dir, filename)

# Files
pca_file = get_path("pca_results_90percent.csv")
variance_file = get_path("pca_variance_90percent.csv")
output_dm = get_path("pca_plot_dm_final.html")
output_pa2r = get_path("pca_plot_pa2r_final.html")

# ==============================================================================
# 2. LOAD DATA
# ==============================================================================
if not os.path.exists(pca_file):
    print(f"Error: '{pca_file}' not found. Run the R script first.")
    exit()

df = pd.read_csv(pca_file)

# Load Variance Data
if os.path.exists(variance_file):
    var_df = pd.read_csv(variance_file)
    def get_var(pc_name):
        row = var_df[var_df['PC'] == pc_name]
        return round(row['Explained_Variance'].values[0] * 100, 2) if not row.empty else "?"
    var_pc1, var_pc2, var_pc3 = get_var("PC1"), get_var("PC2"), get_var("PC3")
else:
    var_pc1, var_pc2, var_pc3 = ("?", "?", "?")

# ==============================================================================
# 3. PREPARE DATA
# ==============================================================================
if 'species' in df.columns:
    df['species_display'] = df['species'].str.replace('_', ' ')
else:
    df['species_display'] = "Unknown"

# Create Grouping: Species + (Locality)
df['species_locality'] = df['species_display'] + " (" + df['locality'].astype(str) + ")"
df = df.sort_values(by=['species_locality'])

# Colors
unique_groups = sorted(df['species_locality'].unique())
palette = px.colors.qualitative.Dark24 + px.colors.qualitative.Alphabet
color_map = {group: palette[i % len(palette)] for i, group in enumerate(unique_groups)}

# ==============================================================================
# 4. JAVASCRIPT & CSS
# ==============================================================================
custom_html_block = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,300;0,400;0,700;1,400&display=swap');
    
    body, .js-plotly-plot, .plot-container, text, .title, .xtitle, .ytitle, .ztitle, .hovertext {
        font-family: 'Lato', sans-serif !important;
    }
    .legendtext {
        font-family: 'Lato', sans-serif !important;
        font-size: 13px !important;
    }
    i, em { font-family: 'Lato', sans-serif !important; font-style: italic; }
    b, strong { font-family: 'Lato', sans-serif !important; font-weight: bold; }
    .plotly-graph-div { position: relative !important; }
    .hovertext { display: none !important; }
</style>

<script>
    var plot_div = document.getElementsByClassName('plotly-graph-div')[0];
    
    // --- 1. Info Panel ---
    var infoPanel = document.createElement('div');
    infoPanel.style.cssText = `
        position: absolute; bottom: 20px; right: 20px; padding: 15px;
        background-color: rgba(255, 255, 255, 0.95);
        border: 1px solid #ccc; border-radius: 5px;
        font-family: 'Lato', sans-serif; font-size: 14px;
        z-index: 100; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        min-width: 200px; pointer-events: none;
    `;
    infoPanel.innerHTML = '<b>Click a point for details</b>';
    plot_div.appendChild(infoPanel);

    // --- 2. Smooth Hover Logic ---
    var isUpdatePending = false;

    plot_div.on('plotly_hover', function(data){
        if (isUpdatePending) return;
        isUpdatePending = true;
        
        requestAnimationFrame(function() {
            var hoveredPoint = data.points[0];
            var targetGroup = hoveredPoint.data.legendgroup;
            
            var indices = [];
            var opacities = [];

            for (var i = 0; i < plot_div.data.length; i++) {
                indices.push(i);
                if (plot_div.data[i].legendgroup === targetGroup) {
                    opacities.push(0.9);
                } else {
                    opacities.push(0.1);
                }
            }

            Plotly.restyle(plot_div, {'marker.opacity': opacities}, indices).then(function() {
                isUpdatePending = false;
            });
        });
    });

    // --- 3. Unhover Logic ---
    plot_div.on('plotly_unhover', function(data){
        setTimeout(function() {
            var indices = [];
            var opacities = [];
            for (var i = 0; i < plot_div.data.length; i++) {
                indices.push(i);
                opacities.push(0.8);
            }
            Plotly.restyle(plot_div, {'marker.opacity': opacities}, indices);
        }, 50);
    });

    // --- 4. Click Logic ---
    plot_div.on('plotly_click', function(data){
        var point = data.points[0];
        var species = point.customdata[0];
        var sex = point.customdata[1];
        var locality = point.customdata[2];
        var id = point.hovertext;

        var content = `
            <div style="border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-bottom: 5px;">
                <b>${id}</b>
            </div>
            <b>Species:</b> <i>${species}</i><br>
            <b>Locality:</b> ${locality}<br>
            <b>Sex:</b> ${sex}<br>
            <div style="margin-top: 5px; font-size: 0.85em; color: #666;">
                PC1: ${point.x.toFixed(3)} | PC2: ${point.y.toFixed(3)} | PC3: ${point.z.toFixed(3)}
            </div>
        `;
        infoPanel.innerHTML = content;
    });
</script>
"""

# ==============================================================================
# 5. PLOTTING FUNCTION
# ==============================================================================
def generate_plot(sub_df, cell_type_name, output_filename):
    if len(sub_df) == 0: return

    print(f"Generating plot for: {cell_type_name}...")
    sub_df['sex'] = sub_df['sex'].astype(str).str.capitalize()

    fig = px.scatter_3d(
        sub_df,
        x='PC1', y='PC2', z='PC3',
        color='species_locality',
        symbol='sex',
        hover_name='image_id',
        color_discrete_map=color_map,
        symbol_map={'Male': 'circle', 'Female': 'cross'},
        custom_data=['species_display', 'sex', 'locality']
    )

    # --- TRACE CONFIGURATION ---
    for trace in fig.data:
        species_name = trace.customdata[0][0]
        locality_name = trace.customdata[0][2]
        
        group_id_plain = f"{species_name} ({locality_name})"
        legend_label_html = f"<i>{species_name}</i> ({locality_name})"

        trace.legendgroup = group_id_plain
        trace.name = legend_label_html
        trace.hoverinfo = 'none'
        
        is_male = (trace.marker.symbol == 'circle')
        
        # --- SIZE ADJUSTMENT HERE ---
        if is_male:
            trace.showlegend = True
            trace.marker.size = 7  # Standard size for Circles
        else:
            trace.showlegend = False
            trace.marker.size = 10 # Larger size for Crosses
            
        trace.marker.opacity = 0.8
        trace.marker.line = dict(width=0.5, color='Black' if is_male else 'DarkSlateGrey')

    # --- LAYOUT CONFIGURATION ---
    fig.update_layout(
        title=dict(
            text=f"<b>PCA of Fly Wing ({cell_type_name})</b>", 
            font=dict(family="Lato", size=22)
        ),
        scene=dict(
            xaxis=dict(title=f"PC1 ({var_pc1}%)", title_font=dict(family="Lato", size=14)),
            yaxis=dict(title=f"PC2 ({var_pc2}%)", title_font=dict(family="Lato", size=14)),
            zaxis=dict(title=f"PC3 ({var_pc3}%)", title_font=dict(family="Lato", size=14)),
            aspectmode='cube',
            bgcolor='white'
        ),
        legend=dict(
            title_text="<b>Population</b><br><span style='font-size:12px'>(Male ●, Female ×)</span>",
            font=dict(family="Lato", size=13),
            itemsizing='constant',
            yanchor="top", y=0.9, xanchor="left", x=1.02
        ),
        font=dict(family="Lato"),
        margin=dict(l=0, r=0, b=0, t=50)
    )

    fig.write_html(output_filename, include_plotlyjs='cdn')
    
    with open(output_filename, "a", encoding="utf-8") as f:
        f.write(custom_html_block)
        
    print(f"Saved: {output_filename}")

# ==============================================================================
# 6. EXECUTE
# ==============================================================================
df_dm = df[df['cell_type'] == 'dm'].copy()
generate_plot(df_dm, "dm", output_dm)

df_pa2r = df[df['cell_type'] == 'pa2r'].copy()
generate_plot(df_pa2r, "pa2r", output_pa2r)

print("\nProcessing Complete.")
