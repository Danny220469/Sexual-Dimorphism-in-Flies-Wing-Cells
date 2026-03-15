import pandas as pd
import plotly.graph_objects as go
import plotly.express as px 
import os
import colorsys

# ==============================================================================
# 1. SETUP PATHS
# ==============================================================================
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    script_dir = os.getcwd()

def get_path(filename):
    return os.path.join(script_dir, filename)

pca_file = get_path("pca_results_90percent.csv")
variance_file = get_path("pca_variance_90percent.csv")
output_dm = get_path("pca_plot_dm_final.html")
output_pa2r = get_path("pca_plot_pa2r_final.html")

# ==============================================================================
# 2. HELPER: COLOR TONING
# ==============================================================================
def adjust_color_lightness(hex_color, factor):
    """ Adjust lightness of a color (0.0=black, 1.0=original, >1.0=lighter) """
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = r/255.0, g/255.0, b/255.0
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    new_l = max(0.2, min(0.9, l * factor))
    r, g, b = colorsys.hls_to_rgb(h, new_l, s)
    return '#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255))

# ==============================================================================
# 3. LOAD DATA
# ==============================================================================
if not os.path.exists(pca_file):
    print(f"Error: '{pca_file}' not found.")
    exit()

df = pd.read_csv(pca_file)

variance_map = {}
if os.path.exists(variance_file):
    var_df = pd.read_csv(variance_file)
    for _, row in var_df.iterrows():
        variance_map[row['PC']] = round(row['Explained_Variance'] * 100, 1)

df['species'] = df['species'].fillna('Unknown')
df['sex'] = df['sex'].fillna('Unknown')
df['locality'] = df['locality'].fillna('Unknown')
available_pcs = [col for col in df.columns if col.startswith('PC')]

# ==============================================================================
# 4. PLOTTING FUNCTION
# ==============================================================================
def create_interactive_plot(cell_type_name, output_filename):
    subset = df[df['cell_type'] == cell_type_name].copy()
    if subset.empty: return

    # --- MARKER SIZES ---
    SIZE_MALE = 7      # ### ADJUST SIZE HERE ###
    SIZE_FEMALE = 9    # ### ADJUST SIZE HERE ###
    
    # --- COLOR MAPPING ---
    CUSTOM_COLORS = {
        'Calliphora_vicina':        '#1f77b4',  # Blue
        'Chrysomya_albiceps':       '#D4AC0D',  # Mustard Gold
        'Chrysomya_bezziana':       '#660000',  # Dark Maroon
        'Chrysomya_megacephala':    '#FF7F0E',  # Orange
        'Chrysomya_nigripes':       '#222222',  # Black/Dark Grey
        'Chrysomya_rufifacies':     '#9467bd',  # Purple
        'Hemipyrellia_liguriensis': '#FF1493',  # Deep Pink
        'Lucilia_cuprina':          '#8c564b',  # Copper Brown
        'Lucilia_sericata':         '#2ca02c',  # Bright Green
        'Parasarcophaga_dux':       '#FF0000',  # Bright Red
        'Synthesiomyia_nudiseta':   '#008080',  # Teal
    }
    
    fallback_pool = px.colors.qualitative.Dark24
    fig = go.Figure()
    
    subset = subset.sort_values(by=['species', 'locality', 'sex'])
    species_list = subset['species'].unique()

    # Assign Colors
    species_base_map = {}
    pool_index = 0
    for sp in species_list:
        manual_match = None
        if sp in CUSTOM_COLORS: manual_match = CUSTOM_COLORS[sp]
        else:
            for key in CUSTOM_COLORS:
                if key in sp: 
                    manual_match = CUSTOM_COLORS[key]
                    break
        if manual_match: species_base_map[sp] = manual_match
        else:
            species_base_map[sp] = fallback_pool[pool_index % len(fallback_pool)]
            pool_index += 1

    # Add Traces
    for species in species_list:
        clean_name = species.replace('_', ' ')
        base_color = species_base_map[species]
        localities = sorted(subset[subset['species'] == species]['locality'].unique())
        num_locs = len(localities)
        
        for loc_idx, locality in enumerate(localities):
            tone_factor = 1.0 if num_locs == 1 else 0.85 + (0.3 * (loc_idx / (num_locs - 1)))
            final_color = adjust_color_lightness(base_color, tone_factor)

            group_id = f"{species}_{locality}"
            # Legend Label
            legend_label = f"<i>{clean_name}</i> <span style='font-size:0.9em; color:#555'>({locality})</span>"

            for sex in ['Male', 'Female']:
                group_data = subset[(subset['species'] == species) & (subset['locality'] == locality) & (subset['sex'] == sex)]
                if group_data.empty: continue
                
                custom_data = group_data[['species', 'sex', 'locality']].values
                current_size = SIZE_MALE if sex == 'Male' else SIZE_FEMALE
                show_legend_item = (sex == 'Male')

                fig.add_trace(go.Scatter3d(
                    x=group_data['PC1'], y=group_data['PC2'], z=group_data['PC3'],
                    mode='markers',
                    marker=dict(
                        size=current_size, 
                        symbol='circle' if sex == 'Male' else 'cross',
                        color=final_color, opacity=0.9,
                        line=dict(width=1, color='DarkSlateGrey')
                    ),
                    name=legend_label, legendgroup=group_id, showlegend=show_legend_item,
                    customdata=custom_data, hoverinfo='none' 
                ))

    # --- SIDEBAR & LAYOUT ---
    btn_x = -0.18
    def make_buttons(axis_key):
        return [dict(method="restyle", label=f"{pc} ({variance_map.get(pc, '?')}%)",
                args=[{axis_key: [subset[(subset['species']==sp) & (subset['locality']==loc) & (subset['sex']==sx)][pc]
                for sp in species_list for loc in sorted(subset[subset['species']==sp]['locality'].unique())
                for sx in ['Male', 'Female']
                if not subset[(subset['species']==sp) & (subset['locality']==loc) & (subset['sex']==sx)].empty]}]) for pc in available_pcs]

    dropbox_font = dict(size=14) 
    
    # ---------------------------------------------------------
    # [SECTION] DROPDOWN MENUS (Fixed Defaults)
    # ---------------------------------------------------------
    updatemenus = [
        # X Axis: Set active=0 (PC1)
        dict(buttons=make_buttons("x"), x=btn_x, y=0.85, yanchor="top", xanchor="left", font=dropbox_font, active=0),
        
        # Y Axis: Set active=1 (PC2)
        dict(buttons=make_buttons("y"), x=btn_x, y=0.65, yanchor="top", xanchor="left", font=dropbox_font, active=1),
        
        # Z Axis: Set active=2 (PC3)
        dict(buttons=make_buttons("z"), x=btn_x, y=0.45, yanchor="top", xanchor="left", font=dropbox_font, active=2),
    ]

    fig.update_layout(
        title=dict(
            text=f"<b>3D Morphospace: {cell_type_name.upper()}</b>", 
            x=0.5, 
            font=dict(family="Lato", size=26)
        ),
        updatemenus=updatemenus,
        scene=dict(
            xaxis=dict(title="X Axis", title_font=dict(size=18), tickfont=dict(size=12)),
            yaxis=dict(title="Y Axis", title_font=dict(size=18), tickfont=dict(size=12)),
            zaxis=dict(title="Z Axis", title_font=dict(size=18), tickfont=dict(size=12)),
            bgcolor='white', aspectmode='cube'
        ),
        legend=dict(
            title_text="<b>Population</b><br><span style='font-size:0.85em'>Male(●) Female(+)</span>", 
            x=1.05, y=1.0, yanchor="top",
            font=dict(family="Lato", size=15), 
            itemsizing='constant', tracegroupgap=5
        ),
        margin=dict(l=200, r=250, b=20, t=100),
        font=dict(family="Lato", size=14),
        clickmode='event+select'
    )
    
    label_font_size = 16 
    
    fig.add_annotation(dict(text="<b>X Axis:</b>", x=btn_x, y=0.90, xref="paper", yref="paper", showarrow=False, xanchor="left", font=dict(size=label_font_size)))
    fig.add_annotation(dict(text="<b>Y Axis:</b>", x=btn_x, y=0.70, xref="paper", yref="paper", showarrow=False, xanchor="left", font=dict(size=label_font_size)))
    fig.add_annotation(dict(text="<b>Z Axis:</b>", x=btn_x, y=0.50, xref="paper", yref="paper", showarrow=False, xanchor="left", font=dict(size=label_font_size)))

    html_str = fig.to_html(include_plotlyjs='cdn', div_id='plot-div', full_html=True)

    # ---------------------------------------------------------
    # INFO BOX & CSS
    # ---------------------------------------------------------
    info_box_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,400;0,700;1,400&display=swap');
    body { font-family: 'Lato', sans-serif; overflow: hidden; }
    
    #info-box {
        position: absolute; 
        bottom: 20px; 
        right: 20px; 
        width: 300px;
        padding: 15px;
        font-size: 16px; /* Body Text Size */
        
        background-color: rgba(255, 255, 255, 0.95);
        border: 1px solid #ccc; 
        border-radius: 6px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        z-index: 1000; 
        display: none; 
    }
    #info-box h3 {
        margin-top: 0; 
        margin-bottom: 10px; 
        font-size: 18px; /* Title Size */
        
        color: #333; 
        border-bottom: 2px solid #007bff; 
        padding-bottom: 5px; 
        font-weight: 700;
    }
    .info-row { margin-bottom: 5px; }
    .info-label { font-weight: bold; color: #555; }
    #info-species { font-style: italic; }
    </style>
    """
    
    info_box_html = """
    <div id="info-box">
        <h3>Specimen Details</h3>
        <div class="info-row"><span class="info-label">Species:</span> <span id="info-species"></span></div>
        <div class="info-row"><span class="info-label">Sex:</span> <span id="info-sex"></span></div>
        <div class="info-row"><span class="info-label">Locality:</span> <span id="info-locality"></span></div>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 10px 0;">
        <div class="info-row"><span class="info-label">X:</span> <span id="info-x"></span></div>
        <div class="info-row"><span class="info-label">Y:</span> <span id="info-y"></span></div>
        <div class="info-row"><span class="info-label">Z:</span> <span id="info-z"></span></div>
    </div>
    """

    js_logic = """
    <script>
    var plotDiv = document.getElementById('plot-div');
    var infoBox = document.getElementById('info-box');
    var activeGroup = null; 
    var resetTimer = null;

    plotDiv.on('plotly_hover', function(data){
        clearTimeout(resetTimer);
        var group = data.points[0].fullData.legendgroup;
        if (group === activeGroup) return;
        activeGroup = group;

        var opacities = [];
        for (var i = 0; i < plotDiv.data.length; i++) {
            if (plotDiv.data[i].legendgroup === activeGroup) {
                opacities.push(1.0); 
            } else {
                opacities.push(0.05); 
            }
        }
        Plotly.restyle(plotDiv, {'marker.opacity': opacities});
    });

    plotDiv.on('plotly_unhover', function(data){
        resetTimer = setTimeout(function(){
            activeGroup = null;
            var opacities = [];
            for (var i = 0; i < plotDiv.data.length; i++) {
                opacities.push(0.9);
            }
            Plotly.restyle(plotDiv, {'marker.opacity': opacities});
        }, 50);
    });
    
    plotDiv.on('plotly_click', function(data){
        var pt = data.points[0];
        if (!pt.customdata) return;

        var species = pt.customdata[0];
        var sex = pt.customdata[1];
        var locality = pt.customdata[2];
        
        document.getElementById('info-species').innerText = species.replace('_', ' ');
        document.getElementById('info-sex').innerText = sex;
        document.getElementById('info-locality').innerText = locality;
        document.getElementById('info-x').innerText = pt.x.toFixed(2);
        document.getElementById('info-y').innerText = pt.y.toFixed(2);
        document.getElementById('info-z').innerText = pt.z.toFixed(2);
        
        infoBox.style.display = 'block';
    });
    </script>
    """
    
    html_str = html_str.replace('</body>', info_box_css + info_box_html + js_logic + '</body>')

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_str)
    print(f"Generated: {output_filename}")

# ==============================================================================
# 5. RUN
# ==============================================================================
create_interactive_plot('dm', output_dm)
create_interactive_plot('pa2r', output_pa2r)