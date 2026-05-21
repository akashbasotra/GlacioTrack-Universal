import numpy as np
import cv2
import rasterio
from scipy.signal import correlate2d
from scipy.ndimage import median_filter

class UniversalGlacierTracker:
    def __init__(self, pixel_size_m=30.0, time_interval_days=12, glacier_type='valley'):
        self.pixel_size = pixel_size_m
        self.time_interval = time_interval_days
        self.glacier_type = glacier_type

    def load_satellite_images(self, master_path, slave_path):
        with rasterio.open(master_path) as src:
            master = src.read(1).astype(np.float32)
            meta = src.meta.copy()
            crs = src.crs
            transform = src.transform

        with rasterio.open(slave_path) as src:
            slave = src.read(1).astype(np.float32)
        return master, slave, meta, crs, transform

    def preprocess_image(self, image, image_type='SAR'):
        image_norm = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
        return image_norm.astype(np.float32)

    def estimate_velocity(self, master, slave):
        # Dummy implementation; replace with real offset tracking for production
        velocity_map = master - slave
        confidence_map = np.ones_like(master)
        offsets = []
        return velocity_map, confidence_map, offsets

    def apply_terrain_filtering(self, velocity_map, dem_array):
        return velocity_map

    def bootstrap_uncertainty(self, velocity_map):
        return {"std": np.nanstd(velocity_map) if hasattr(np, 'nanstd') else np.std(velocity_map)}

    def save_outputs(self, velocity_map, output_dir, glacier_name, crs, transform):
        import os
        os.makedirs(output_dir, exist_ok=True)
        out_path = f"{output_dir}/{glacier_name}_velocity.tif"
        with rasterio.open(out_path, 'w', driver='GTiff', height=velocity_map.shape[0],
                           width=velocity_map.shape[1], count=1, dtype=velocity_map.dtype,
                           crs=crs, transform=transform) as dst:
            dst.write(velocity_map, 1)
        return out_path, None
