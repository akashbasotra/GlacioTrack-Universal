"""GlacioTrack - Final Version with RGI Shapefile Upload"""
import streamlit as st
import pandas as pd
import numpy as np
import os
from pathlib import Path
import rasterio
from engine import UniversalGlacierTracker
from rgi_shapefile_handler import RGIShapefileHandler, ShapefileProcessor
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="GlacioTrack - Glacier Velocity", page_icon="🏔️", layout="wide")

st.markdown("# 🏔️ GlacioTrack: Universal Glacier Velocity Estimation")
st.markdown("### Upload RGI Shapefile | Select Glacier | Monitor Velocity")

if 'results' not in st.session_state:
    st.session_state.results = None
if 'glacier_info' not in st.session_state:
    st.session_state.glacier_info = None

# SIDEBAR
with st.sidebar:
    st.markdown("## 🏔️ Glacier Selection via RGI Shapefile")
    st.markdown("### 📤 Upload RGI Shapefile")
    
    uploaded_shp = st.file_uploader("Upload .shp file", type=['shp'], key='shp')
    uploaded_shx = st.file_uploader("Upload .shx file", type=['shx'], key='shx')
    uploaded_dbf = st.file_uploader("Upload .dbf file", type=['dbf'], key='dbf')
    uploaded_prj = st.file_uploader("Upload .prj file (optional)", type=['prj'], key='prj')
    
    if uploaded_shp and uploaded_shx and uploaded_dbf:
        temp_dir = "./temp_shapefiles"
        os.makedirs(temp_dir, exist_ok=True)
        
        base_name = uploaded_shp.name.replace('.shp', '')
        shp_path = f"{temp_dir}/{base_name}.shp"
        shx_path = f"{temp_dir}/{base_name}.shx"
        dbf_path = f"{temp_dir}/{base_name}.dbf"
        
        with open(shp_path, 'wb') as f:
            f.write(uploaded_shp.getbuffer())
        with open(shx_path, 'wb') as f:
            f.write(uploaded_shx.getbuffer())
        with open(dbf_path, 'wb') as f:
            f.write(uploaded_dbf.getbuffer())
        if uploaded_prj:
            prj_path = f"{temp_dir}/{base_name}.prj"
            with open(prj_path, 'wb') as f:
                f.write(uploaded_prj.getbuffer())
        
        st.success("✓ Shapefile loaded")
        
        try:
            processor = ShapefileProcessor(shp_path)
            glacier_dict = processor.get_glacier_for_streamlit()
            
            st.write(f"**Glaciers:** {len(glacier_dict)}")
            
            st.markdown("### 🔍 Select Glacier")
            selected = st.selectbox("Choose glacier:", options=list(glacier_dict.keys()))
            
            if selected:
                glacier_idx = glacier_dict[selected]
                glacier_info = processor.get_glacier_details(glacier_idx)
                st.session_state.glacier_info = glacier_info
                
                st.markdown("### 📌 Selected")
                st.write(f"**{glacier_info['name']}**")
                st.write(f"RGI: {glacier_info['rgi_id']}")
                st.write(f"Area: {glacier_info['area_km2']} km²")
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("👆 Upload .shp, .shx, .dbf files")
    
    # Parameters
    st.markdown("---")
    st.markdown("## ⚙️ Parameters")
    glacier_type = st.selectbox("Glacier Type", ['valley', 'ice_sheet', 'mountain', 'outlet'])
    pixel_size = st.number_input("Pixel Size (m)", 30.0, 10.0, 100.0)
    time_interval = st.number_input("Time Interval (days)", 12, 1, 365)
    window_size = st.slider("Window Size", 32, 128, 64, 16)
    enable_dem = st.checkbox("DEM Filtering", True)
    compute_uncertainty = st.checkbox("Uncertainty", True)

# MAIN
if st.session_state.glacier_info:
    g = st.session_state.glacier_info
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Glacier", g['name'][:15])
    with col2: st.metric("RGI", g['rgi_id'])
    with col3: st.metric("Area", f"{g['area_km2']} km²")
    with col4: st.metric("Lat/Lon", f"{g['lat']:.2f}°")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Process", "🗺️ Results", "📈 Stats", "💾 Export"])

with tab1:
    st.markdown("## Upload Satellite Images")
    col1, col2 = st.columns(2)
    with col1:
        master_file = st.file_uploader("Master Image (GeoTIFF)", type=['tif'], key='master')
        if master_file: st.success(f"✓ {master_file.name}")
    with col2:
        slave_file = st.file_uploader("Slave Image (GeoTIFF)", type=['tif'], key='slave')
        if slave_file: st.success(f"✓ {slave_file.name}")
    
    dem_file = st.file_uploader("DEM (optional)", type=['tif'], key='dem')
    if dem_file: st.success(f"✓ {dem_file.name}")
    
    if st.button("🚀 Start Processing", use_container_width=True):
        if not master_file or not slave_file or not st.session_state.glacier_info:
            st.error("❌ Upload images and select glacier")
        else:
            with st.spinner("Processing..."):
                temp_dir = "./temp"
                os.makedirs(temp_dir, exist_ok=True)
                
                master_path = f"{temp_dir}/master.tif"
                slave_path = f"{temp_dir}/slave.tif"
                dem_path = f"{temp_dir}/dem.tif" if dem_file else None
                
                with open(master_path, 'wb') as f:
                    f.write(master_file.getbuffer())
                with open(slave_path, 'wb') as f:
                    f.write(slave_file.getbuffer())
                if dem_file:
                    with open(dem_path, 'wb') as f:
                        f.write(dem_file.getbuffer())
                
                try:
                    tracker = UniversalGlacierTracker(pixel_size, time_interval, glacier_type)
                    master, slave, meta, crs, transform = tracker.load_satellite_images(master_path, slave_path)
                    
                    if master is not None:
                        master_proc = tracker.preprocess_image(master, 'SAR')
                        slave_proc = tracker.preprocess_image(slave, 'SAR')
                        velocity_map, confidence_map, offsets = tracker.estimate_velocity(master_proc, slave_proc)
                        
                        if dem_file and enable_dem:
                            with rasterio.open(dem_path) as src:
                                dem_data = src.read(1)
                            velocity_map = tracker.apply_terrain_filtering(velocity_map, dem_data)
                        
                        uncertainty = None
                        if compute_uncertainty:
                            uncertainty = tracker.bootstrap_uncertainty(velocity_map)
                        
                        st.session_state.results = {
                            'tracker': tracker,
                            'velocity_map': velocity_map,
                            'confidence_map': confidence_map,
                            'offsets': offsets,
                            'uncertainty': uncertainty,
                            'meta': meta,
                            'crs': crs,
                            'transform': transform
                        }
                        
                        st.success("✅ Complete!")
                        st.balloons()
                        
                        valid_pixels = np.sum(~np.isnan(velocity_map))
                        mean_velocity = np.nanmean(velocity_map)
                        col1, col2, col3 = st.columns(3)
                        with col1: st.metric("Valid Pixels", f"{valid_pixels:,}")
                        with col2: st.metric("Mean Velocity", f"{mean_velocity:.2f} m/yr")
                        with col3: st.metric("Max Velocity", f"{np.nanmax(velocity_map):.2f} m/yr")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab2:
    if st.session_state.results:
        results = st.session_state.results
        velocity_map = results['velocity_map']
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Velocity Map")
            valid_data = velocity_map[~np.isnan(velocity_map)]
            if len(valid_data) > 0:
                fig = go.Figure(data=go.Heatmap(z=velocity_map, colorscale='Jet'))
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### Distribution")
            if len(valid_data) > 0:
                fig = go.Figure(data=go.Histogram(x=valid_data.flatten(), nbinsx=50))
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👈 Process images first")

with tab3:
    if st.session_state.results:
        results = st.session_state.results
        velocity_map = results['velocity_map']
        valid_data = velocity_map[~np.isnan(velocity_map)]
        
        st.markdown("### Statistics")
        stats_df = pd.DataFrame({
            'Metric': ['Mean', 'Median', 'Std Dev', 'Min', 'Max'],
            'Value (m/yr)': [
                f"{np.mean(valid_data):.3f}",
                f"{np.median(valid_data):.3f}",
                f"{np.std(valid_data):.3f}",
                f"{np.min(valid_data):.3f}",
                f"{np.max(valid_data):.3f}"
            ]
        })
        st.dataframe(stats_df, use_container_width=True)
    else:
        st.info("👈 Process images first")

with tab4:
    if st.session_state.results and st.session_state.glacier_info:
        results = st.session_state.results
        glacier = st.session_state.glacier_info
        output_dir = "./outputs"
        os.makedirs(output_dir, exist_ok=True)
        filename = glacier['rgi_id'].replace('-', '_')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 GeoTIFF"):
                tracker = results['tracker']
                path, _ = tracker.save_outputs(results['velocity_map'], output_dir, filename, results['crs'], results['transform'])
                st.success(f"✓ Saved")
        with col2:
            if st.button("📊 CSV"):
                df = pd.DataFrame(results['offsets'])
                path = f"{output_dir}/{filename}_offsets.csv"
                df.to_csv(path, index=False)
                st.success(f"✓ Saved")
        with col3:
            if st.button("📋 Metadata"):
                import json
                meta = {'Glacier': glacier['name'], 'RGI': glacier['rgi_id'], 'Area': glacier['area_km2']}
                path = f"{output_dir}/{filename}_metadata.json"
                with open(path, 'w') as f:
                    json.dump(meta, f, indent=2)
                st.success(f"✓ Saved")
    else:
        st.info("👈 Process images first")

st.markdown("---")
st.markdown("<div style='text-align: center'><p>🏔️ <b>GlacioTrack</b> - Universal Glacier Velocity Estimation</p></div>", unsafe_allow_html=True)
