"""GlacioTrack RGI Shapefile Handler
Allows manual upload of RGI shapefiles for glacier boundary extraction
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import box, mapping
import warnings
warnings.filterwarnings('ignore')

class RGIShapefileHandler:
    """Handles RGI shapefile upload and glacier boundary extraction"""
    
    def __init__(self):
        self.shapefiles = {}
        self.glaciers = None
        self.selected_glacier = None
    
    def load_shapefile(self, shapefile_path):
        """Load RGI shapefile"""
        try:
            print(f"[RGI] Loading shapefile: {shapefile_path}")
            gdf = gpd.read_file(shapefile_path)
            print(f"[RGI] ✓ Loaded {len(gdf)} glaciers")
            self.glaciers = gdf
            return gdf
        except Exception as e:
            print(f"[RGI] Error: {e}")
            return None
    
    def search_glacier_in_shapefile(self, search_term, search_type='name'):
        """Search for glacier in shapefile"""
        if self.glaciers is None:
            return None
        
        if search_type == 'name':
            matches = self.glaciers[self.glaciers.get('Name', '').str.contains(search_term, case=False, na=False)]
        elif search_type == 'rgi_id':
            matches = self.glaciers[self.glaciers.get('RGIId', '').str.contains(search_term, case=False, na=False)]
        else:
            return None
        
        results = []
        for idx, row in matches.iterrows():
            results.append({
                'index': idx,
                'name': row.get('Name', 'Unknown'),
                'rgi_id': row.get('RGIId', 'N/A'),
                'area_km2': row.get('Area', 'N/A'),
                'lat': row.get('CenLat', 'N/A'),
                'lon': row.get('CenLon', 'N/A'),
                'geometry': row.geometry
            })
        
        return results if results else None
    
    def get_glacier_info_dict(self, glacier_index):
        """Get complete glacier information as dictionary"""
        glacier = self.glaciers.iloc[glacier_index]
        return {
            'index': glacier_index,
            'name': glacier.get('Name', 'Unknown'),
            'rgi_id': glacier.get('RGIId', 'N/A'),
            'area_km2': glacier.get('Area', 'N/A'),
            'lat': glacier.get('CenLat', 'N/A'),
            'lon': glacier.get('CenLon', 'N/A'),
            'geometry': glacier.geometry
        }
    
    def get_glacier_for_streamlit(self):
        """Prepare glacier list for Streamlit"""
        if self.glaciers is None:
            return {}
        
        glacier_dict = {}
        for idx, row in self.glaciers.iterrows():
            name = row.get('Name', f'Glacier {idx}')
            rgi_id = row.get('RGIId', 'Unknown')
            area = row.get('Area', 'N/A')
            display = f"{name} (RGI: {rgi_id}) [{area} km²]"
            glacier_dict[display] = idx
        
        return glacier_dict

class ShapefileProcessor:
    """Process uploaded shapefile for glacier extraction"""
    
    def __init__(self, shapefile_path):
        self.handler = RGIShapefileHandler()
        self.gdf = self.handler.load_shapefile(shapefile_path)
    
    def get_glacier_for_streamlit(self):
        return self.handler.get_glacier_for_streamlit()
    
    def get_glacier_by_display_name(self, display_name):
        glacier_dict = self.get_glacier_for_streamlit()
        return glacier_dict.get(display_name)
    
    def get_glacier_details(self, glacier_index):
        return self.handler.get_glacier_info_dict(glacier_index)
