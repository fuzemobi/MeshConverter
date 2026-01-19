# MeshConverter_v2

Convert mesh scans (STL files) to simplified CAD files with automatic outlier and artifact removal.

## Features

- ✅ **Outlier Removal** - Statistical and radius-based outlier detection
- ✅ **Artifact Removal** - Removes reconstruction artifacts using density filtering
- ✅ **Mesh Simplification** - Reduces triangle count while preserving shape
- ✅ **Cylinder Detection** - RANSAC-based primitive shape fitting
- ✅ **Surface Reconstruction** - Poisson reconstruction for clean meshes
- ✅ **Batch Processing** - Process multiple files efficiently

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
# Basic usage
python mesh_to_cad_converter.py battery.stl

# Specify output directory
python mesh_to_cad_converter.py battery.stl -o output/

# Adjust simplification level
python mesh_to_cad_converter.py battery.stl --target-triangles 10000

# Fine-tune voxel size
python mesh_to_cad_converter.py battery.stl --voxel-size 0.01
```

## Python API

```python
from mesh_to_cad_converter import MeshToCADConverter

# Create converter with default config
converter = MeshToCADConverter()

# Or with custom config
config = MeshToCADConverter.default_config()
config['voxel_size'] = 0.01
config['target_triangles'] = 10000
converter = MeshToCADConverter(config)

# Convert mesh
outputs = converter.convert('battery.stl', 'output/')

# Access results
print(outputs['simplified_mesh'])
print(outputs['statistics'])
```

## Pipeline Stages

### 1. Load Mesh
- Reads STL file
- Reports original mesh statistics

### 2. Convert to Point Cloud
- Samples points uniformly from mesh surface
- Default: 50,000 points

### 3. Downsample
- Voxel grid downsampling
- Default voxel size: 0.02m
- Reduces computational cost

### 4. Remove Statistical Outliers
- Removes points far from neighbors
- Default: 20 neighbors, 2.0 std ratio
- Eliminates noise

### 5. Remove Radius Outliers
- Removes sparse isolated points
- Default: 16 points within 0.05m radius
- Cleans up artifacts

### 6. Estimate Normals
- Calculates surface normals
- Orients normals consistently
- Required for reconstruction

### 7. Detect Cylinder (Optional)
- RANSAC cylinder fitting
- Extracts parametric dimensions
- Useful for cylindrical parts

### 8. Reconstruct Surface
- Poisson surface reconstruction
- Removes low-density vertices (artifacts)
- Creates watertight mesh

### 9. Simplify Mesh
- Quadric decimation
- Default: 5,000 triangles
- Preserves visual appearance

## Configuration Parameters

```python
{
    # Downsampling
    'voxel_size': 0.02,  # meters
    
    # Statistical outlier removal
    'stat_nb_neighbors': 20,
    'stat_std_ratio': 2.0,
    
    # Radius outlier removal
    'radius_nb_points': 16,
    'radius': 0.05,  # meters
    
    # Normal estimation
    'normal_radius': 0.1,
    'normal_max_nn': 30,
    
    # RANSAC cylinder detection
    'ransac_distance_threshold': 0.01,
    'ransac_n': 3,
    'ransac_iterations': 1000,
    
    # Poisson reconstruction
    'poisson_depth': 9,
    'density_quantile': 0.01,  # Remove lowest 1%
    
    # Mesh simplification
    'target_triangles': 5000,
    
    # Output
    'export_intermediates': True,
}
```

## Output Files

- `{name}_simplified.stl` - Cleaned and simplified mesh
- `{name}_cleaned.ply` - Cleaned point cloud (if enabled)
- `{name}_statistics.json` - Processing statistics

## Statistics JSON

```json
{
  "original_vertices": 86541,
  "original_triangles": 172722,
  "downsampled_points": 8234,
  "stat_outliers_removed": 123,
  "radius_outliers_removed": 45,
  "reconstructed_vertices": 15234,
  "reconstructed_triangles": 30456,
  "artifacts_removed": 234,
  "simplified_triangles": 5000,
  "cylinder_params": {
    "center": [0.0, 0.0, 0.0],
    "axis": [0.0, 0.0, 1.0],
    "radius": 0.025,
    "length": 0.085,
    "inliers": 7890,
    "inlier_ratio": 0.95
  }
}
```

## Advanced Usage

### Custom Outlier Removal

```python
converter = MeshToCADConverter({
    'stat_nb_neighbors': 30,  # More strict
    'stat_std_ratio': 1.5,     # More aggressive
    'radius_nb_points': 20,    # Denser requirement
    'radius': 0.03,            # Smaller radius
})
```

### High-Quality Reconstruction

```python
converter = MeshToCADConverter({
    'voxel_size': 0.01,        # Finer voxels
    'poisson_depth': 10,       # Higher detail
    'target_triangles': 20000, # More triangles
})
```

### Fast Processing

```python
converter = MeshToCADConverter({
    'voxel_size': 0.05,       # Coarser voxels
    'poisson_depth': 8,       # Lower detail
    'target_triangles': 2000, # Fewer triangles
    'export_intermediates': False,
})
```

## Troubleshooting

### Memory Issues
- Increase `voxel_size` to reduce points
- Reduce `target_triangles`
- Disable `export_intermediates`

### Too Much Detail Lost
- Decrease `voxel_size`
- Increase `poisson_depth`
- Increase `target_triangles`

### Artifacts Remain
- Increase `density_quantile` (remove more vertices)
- Adjust `stat_std_ratio` (lower = more aggressive)
- Reduce `radius` (smaller neighborhood)

### Over-Simplification
- Relax `stat_std_ratio` (higher value)
- Increase `radius_nb_points` (allow sparser areas)
- Lower `density_quantile`

## Research Sources

Based on comprehensive research from:

1. **Open3D** - Point cloud processing and outlier removal
   - https://www.open3d.org/docs/latest/tutorial/geometry/pointcloud_outlier_removal.html

2. **pyRANSAC-3D** - Primitive shape fitting
   - https://github.com/leomariga/pyRANSAC-3D

3. **point-cloud-utils** - Advanced mesh processing
   - https://github.com/fwilliams/point-cloud-utils

4. **meshoptimizer** - Mesh simplification
   - https://github.com/zeux/meshoptimizer

5. **Point2CAD** - AI-powered mesh to CAD
   - https://github.com/prs-eth/point2cad

## TODO

- [ ] Add STEP export using PythonOCC
- [ ] Implement batch processing script
- [ ] Add sphere and plane detection
- [ ] Support more input formats (OBJ, PLY)
- [ ] Add GUI interface
- [ ] Integrate AI-based shape recognition
- [ ] Add multi-threading for batch processing
- [ ] Create Docker container for easy deployment

## License

MIT License

## Author

MedTrackET Development Team

## Contributing

Pull requests welcome! Please ensure code follows PEP 8 style guidelines.
