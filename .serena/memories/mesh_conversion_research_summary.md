# Mesh to CAD Conversion Research Summary

## Project Goal
Convert mesh scans (STL files) to simplified CAD files with no artifacts or outliers for MedTrackET project.

## Top Solutions Found

### 1. **Open3D** - Best for Point Cloud Processing & Outlier Removal
**GitHub**: https://www.open3d.org/docs/latest/tutorial/geometry/pointcloud_outlier_removal.html

**Key Features**:
- Statistical outlier removal
- Radius outlier removal  
- RANSAC plane/cylinder detection
- Voxel downsampling
- Surface reconstruction (Poisson, Ball Pivoting)

**Code Example**:
```python
import open3d as o3d
import numpy as np

# Load mesh
mesh = o3d.io.read_triangle_mesh("battery.stl")
pcd = mesh.sample_points_uniformly(number_of_points=10000)

# Downsample
pcd = pcd.voxel_down_sample(voxel_size=0.02)

# Remove statistical outliers
cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
pcd_clean = pcd.select_by_index(ind)

# Remove radius outliers
cl, ind = pcd_clean.remove_radius_outlier(nb_points=16, radius=0.05)
pcd_final = pcd_clean.select_by_index(ind)

# Estimate normals
pcd_final.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30)
)

# RANSAC cylinder detection
cylinder_params = fit_cylinder_ransac(pcd_final)

# Surface reconstruction
mesh_clean, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd_final, depth=9)
```

### 2. **point-cloud-utils** - Advanced Mesh Processing
**GitHub**: https://github.com/fwilliams/point-cloud-utils

**Key Features**:
- Mesh decimation
- Deduplicate vertices
- Chamfer distances
- Mesh smoothing
- Fast Winding Numbers for signed distances
- Watertight mesh generation

### 3. **pyRANSAC-3D** - Primitive Shape Fitting
**GitHub**: https://github.com/leomariga/pyRANSAC-3D

**Key Features**:
- Fit planes, cylinders, spheres to point clouds
- Specifically designed for 3D SLAM and reconstruction
- Clean API for shape detection

**Code Example**:
```python
import pyransac3d as pyrsc

# Cylinder fitting
cyl = pyrsc.Cylinder()
center, axis, radius, inliers = cyl.fit(points, thresh=0.01)

# Plane fitting
plane = pyrsc.Plane()
equation, inliers = plane.fit(points, thresh=0.01)
```

### 4. **meshoptimizer** - Mesh Simplification
**GitHub**: https://github.com/zeux/meshoptimizer

**Key Features**:
- Point cloud simplification
- Mesh decimation
- Preserves appearance while reducing points
- Supports color preservation

### 5. **PythonOCC-CAD-Converter** - STL to STEP Conversion
**GitHub**: https://github.com/DalessandroJ/PythonOCC-CAD-Converter

**Key Features**:
- Convert STL to STEP/IGES/BREP
- Batch conversion
- GUI interface
- No external CAD software required

### 6. **Point2CAD** - AI-Powered Mesh to CAD
**GitHub**: https://github.com/prs-eth/point2cad

**Key Features**:
- Reconstructs surfaces, edges, corners from point clouds
- Research-grade AI model
- Specifically for reverse engineering

### 7. **stl2step** - Intelligent STL to STEP Conversion
**GitHub**: https://github.com/TheTesla/stl2step

**Key Features**:
- Segments mesh into basic shapes
- Non-trivial conversion approach
- Generates parametric STEP files

## Recommended Workflow

### Phase 1: Clean & Simplify Mesh
```python
import open3d as o3d
import numpy as np

# Load STL
mesh = o3d.io.read_triangle_mesh("battery.stl")

# Convert to point cloud
pcd = mesh.sample_points_uniformly(number_of_points=50000)

# Voxel downsample
pcd = pcd.voxel_down_sample(voxel_size=0.02)

# Statistical outlier removal
cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
pcd_clean = pcd.select_by_index(ind)

# Radius outlier removal
cl, ind = pcd_clean.remove_radius_outlier(nb_points=16, radius=0.05)
pcd_final = pcd_clean.select_by_index(ind)

# Estimate normals
pcd_final.estimate_normals()
pcd_final.orient_normals_towards_camera_location(pcd_final.get_center())
```

### Phase 2: Detect Geometric Primitives
```python
import pyransac3d as pyrsc

points = np.asarray(pcd_final.points)

# For cylindrical objects (like battery)
cyl = pyrsc.Cylinder()
center, axis, radius, inliers = cyl.fit(points, thresh=0.01, maxIteration=1000)

# For plane detection
plane = pyrsc.Plane()
equation, inliers = plane.fit(points, thresh=0.01)
```

### Phase 3: Reconstruct Clean Mesh
```python
# Poisson reconstruction
mesh_clean, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd_final, 
    depth=9
)

# Remove low-density vertices (artifacts)
vertices_to_remove = densities < np.quantile(densities, 0.01)
mesh_clean.remove_vertices_by_mask(vertices_to_remove)

# Simplify mesh
mesh_clean = mesh_clean.simplify_quadric_decimation(target_number_of_triangles=5000)

# Export
o3d.io.write_triangle_mesh("battery_clean.stl", mesh_clean)
```

### Phase 4: Convert to STEP (Parametric CAD)
```python
from OCC.Core.STEPControl import STEPControl_Writer
from OCC.Extend.DataExchange import read_stl_file

# Using PythonOCC
shape = read_stl_file("battery_clean.stl")
step_writer = STEPControl_Writer()
step_writer.Transfer(shape, STEPControl_AsIs)
step_writer.Write("battery.step")
```

## Installation Requirements

```bash
pip install open3d
pip install numpy
pip install scikit-learn
pip install pyransac3d
pip install trimesh
pip install scipy
pip install matplotlib

# For STEP conversion
conda install -c conda-forge pythonocc-core
```

## Additional Tools

### Instant Meshes (External)
- Website: https://github.com/wjakob/instant-meshes
- Auto-retopology tool
- Creates quad meshes from triangle meshes
- Mentioned in Fusion 360 discussions as "lifesaver"

### FreeCAD Python Scripts
- Forum discussion with working STL to STEP scripts
- Uses mesh-to-shape with sewing and tolerance control
- Creates solid bodies from meshes

## Best Practices

1. **Always downsample first** - Reduces computational cost
2. **Use statistical outlier removal** - Removes noise
3. **Use radius outlier removal** - Removes sparse points
4. **Estimate normals** - Required for surface reconstruction
5. **Orient normals consistently** - Prevents inside-out surfaces
6. **Remove low-density vertices** - Eliminates reconstruction artifacts
7. **Simplify final mesh** - Reduces file size while preserving shape

## Next Steps

1. Test Open3D pipeline on battery.stl
2. Implement RANSAC cylinder detection for parametric extraction
3. Create automated pipeline script
4. Add STEP export capability
5. Test on various MedTrackET device scans
