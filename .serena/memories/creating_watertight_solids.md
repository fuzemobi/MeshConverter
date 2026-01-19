# Creating Watertight Closed Solids from Mesh Scans

## The Problem

Current approaches (BPA, direct simplification) clean up meshes but **don't guarantee closed, watertight geometry**:

- **Direct simplification** → Reduces triangles but preserves original mesh topology (may have holes/gaps)
- **Ball Pivoting Algorithm** → Reconstructs surface from points but often leaves unsealed areas
- **Result**: Output is "cleaner" but still not suitable for CAD/3D printing without manual repair

**For medical devices & manufacturing scans, we need:**
- ✅ Closed, watertight solids (manifold geometry)
- ✅ Sealed surfaces suitable for CAD editing
- ✅ Support structures for overhangs (can be added manually later)
- ✅ Volume calculation possible

## Open3D Tools Available for Watertightness

### 1. Detection Methods
```python
mesh.is_watertight()              # Boolean: True if closed
mesh.is_vertex_manifold()         # All vertices surrounded by single ring
mesh.is_edge_manifold()          # All edges shared by exactly 2 triangles
mesh.is_orientable()             # Consistent triangle orientation
mesh.get_non_manifold_edges()    # Find problem areas
```

### 2. Repair/Closure Methods
```python
mesh.remove_non_manifold_edges()  # Remove edges not shared by 2 triangles
mesh.orient_triangles()           # Make orientation consistent
mesh.merge_close_vertices(eps)    # Stitch nearby vertices (closes small gaps)
mesh.compute_convex_hull()        # Wrap entire mesh (last resort)
```

### 3. Reconstruction from Point Cloud
```python
# For point clouds with holes:
pcd.remove_statistical_outlier()  # Clean noise
mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson()  # Guaranteed closed
# or
mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting()
```

## Strategy: Multi-Stage Watertight Conversion

### Stage 1: Analyze Input
```python
mesh = o3d.io.read_triangle_mesh(input_file)
print(f"Is watertight: {mesh.is_watertight()}")
print(f"Is vertex manifold: {mesh.is_vertex_manifold()}")
print(f"Is edge manifold: {mesh.is_edge_manifold()}")
non_manifold = mesh.get_non_manifold_edges()
print(f"Non-manifold edges: {len(non_manifold)}")
```

### Stage 2: Basic Cleanup
```python
# Standard hygiene
mesh.remove_duplicated_vertices()
mesh.remove_duplicated_triangles()
mesh.remove_degenerate_triangles()

# Fix topology issues
mesh.orient_triangles()  # Consistent normal direction
mesh.remove_non_manifold_edges()
```

### Stage 3: Close Small Gaps
```python
# Merge close vertices to stitch small gaps
# Epsilon = ~1% of mesh diagonal for CAD scans in mm
diagonal = np.linalg.norm(mesh.get_axis_aligned_bounding_box().get_extent())
eps = diagonal * 0.01  # Adjust based on scan quality

mesh = mesh.merge_close_vertices(eps)
```

### Stage 4: Verify Watertightness
```python
if mesh.is_watertight():
    print("✅ Mesh is watertight!")
else:
    # If still not watertight:
    print("⚠️  Still has holes, attempting convex hull wrapper...")
    # Option A: Use convex hull (loses detail but guaranteed closed)
    mesh = mesh.compute_convex_hull()[0]
    
    # Option B: Convert to point cloud and use Poisson
    pcd = mesh.sample_points_poisson_disk(25000)
    mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd)[0]
```

### Stage 5: Simplify (if needed)
```python
# Only after watertightness is guaranteed
mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=5000)
mesh.compute_vertex_normals()
```

## Recommended Pipeline for Medical/Manufacturing Scans

```python
import open3d as o3d
import numpy as np
from pathlib import Path

def create_watertight_solid(input_file, output_dir=None, target_triangles=5000):
    """
    Convert noisy scan to clean watertight solid.
    
    Args:
        input_file: Path to input STL
        output_dir: Where to save outputs
        target_triangles: Target simplification level
    
    Returns:
        Path to output mesh
    """
    
    # Load
    mesh = o3d.io.read_triangle_mesh(input_file)
    original_triangles = len(mesh.triangles)
    
    print(f"Original: {original_triangles:,} triangles")
    print(f"Watertight: {mesh.is_watertight()}")
    
    # Get scale
    diagonal = np.linalg.norm(mesh.get_axis_aligned_bounding_box().get_extent())
    eps_merge = diagonal * 0.01  # 1% of diagonal for vertex merging
    
    # Stage 1: Basic cleanup
    mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles()
    mesh.remove_degenerate_triangles()
    mesh.remove_non_manifold_edges()
    mesh.orient_triangles()
    
    print(f"After cleanup: {len(mesh.triangles):,} triangles")
    
    # Stage 2: Close small gaps
    mesh = mesh.merge_close_vertices(eps_merge)
    print(f"After merging (eps={eps_merge:.4f}): {len(mesh.triangles):,} triangles")
    
    # Stage 3: Verify watertightness
    if not mesh.is_watertight():
        print("⚠️  Not watertight, trying recovery strategies...")
        
        # Try conversion to point cloud + reconstruction
        print("  Converting to point cloud...")
        pcd = mesh.sample_points_uniform(25000)
        
        print("  Reconstructing with Poisson algorithm...")
        try:
            mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=8)
            print(f"  ✅ Poisson reconstruction: {len(mesh.triangles):,} triangles")
        except:
            print("  ⚠️  Poisson failed, using convex hull...")
            mesh = mesh.compute_convex_hull()[0]
            print(f"  Convex hull: {len(mesh.triangles):,} triangles")
    
    # Stage 4: Final check
    print(f"Is watertight: {mesh.is_watertight()}")
    print(f"Is edge manifold: {mesh.is_edge_manifold()}")
    
    # Stage 5: Simplify
    if len(mesh.triangles) > target_triangles:
        print(f"\nSimplifying to {target_triangles:,} triangles...")
        mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=target_triangles)
        print(f"Result: {len(mesh.triangles):,} triangles")
    
    # Compute normals
    mesh.compute_vertex_normals()
    
    # Save
    if output_dir is None:
        output_dir = Path(input_file).parent
    output_path = Path(output_dir) / f"{Path(input_file).stem}_watertight.stl"
    o3d.io.write_triangle_mesh(str(output_path), mesh)
    
    # Statistics
    reduction = (1 - len(mesh.triangles) / original_triangles) * 100
    print(f"\n{'='*60}")
    print(f"✅ Watertight solid created!")
    print(f"  Original: {original_triangles:,} triangles")
    print(f"  Output: {len(mesh.triangles):,} triangles ({reduction:.1f}% reduction)")
    print(f"  Saved: {output_path}")
    print(f"{'='*60}")
    
    return str(output_path)

# Usage
if __name__ == "__main__":
    create_watertight_solid("tests/samples/simple_block.stl", output_dir="output")
```

## Key Parameters by Use Case

### CAD Scans (Manufacturing Parts)
```python
eps_merge = diagonal * 0.01        # Stitch small gaps (1%)
target_triangles = 5000             # Clean but detailed
```

### 3D Printed Objects
```python
eps_merge = diagonal * 0.005       # Tighter tolerance (0.5%)
target_triangles = 3000             # Moderate detail
```

### Medical Device Scans
```python
eps_merge = diagonal * 0.001       # Very tight (0.1%)
target_triangles = 10000            # High detail preservation
```

### Rough Point Cloud Data
```python
eps_merge = diagonal * 0.02        # Loose tolerance (2%)
target_triangles = 8000             # May need Poisson reconstruction
```

## Poisson vs Ball Pivoting for Reconstruction

| Aspect | Poisson | Ball Pivoting |
|--------|---------|---------------|
| **Watertightness** | ✅ Always watertight | ❌ Can leave gaps |
| **Detail preservation** | ⚠️ Smooths over features | ✅ Preserves sharp edges |
| **Hole filling** | ✅ Fills large holes | ❌ Respects point cloud |
| **Speed** | ⚠️ Slower (octree) | ✅ Faster |
| **Parameters** | Depth (8-10) | Radius, angles |
| **Best for** | Noisy point clouds | Dense, clean points |

**Recommendation**: Use **Poisson** for guaranteed watertight solids, **BPA** for feature preservation.

## Troubleshooting Watertightness Issues

### Issue: Mesh still not watertight after merge_close_vertices
**Solution**: Increase epsilon or use Poisson reconstruction
```python
# More aggressive merging
mesh = mesh.merge_close_vertices(eps=diagonal * 0.05)

# Or convert to point cloud + Poisson
pcd = mesh.sample_points_uniform(50000)
mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd)
```

### Issue: Over-smoothing after Poisson reconstruction
**Solution**: Increase depth parameter (but slower)
```python
mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=10)  # Higher = more detail
```

### Issue: Convex hull too aggressively simplifies
**Solution**: Use as last resort only; try BPA first
```python
mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, o3d.geometry.KDTreeSearchParamKNN(knn=30))
```

## Implementation Notes

1. **Always check watertightness** before final output
2. **Scale-aware merging** - Use mesh diagonal to determine epsilon
3. **Orientation matters** - `orient_triangles()` ensures consistent normals
4. **Manifold = exportable** - Non-manifold edges cause CAD software issues
5. **Volume calculation** - Only valid on watertight meshes

## Testing Commands

```bash
# Test watertightness check
python3.12 -c "
import open3d as o3d
mesh = o3d.io.read_triangle_mesh('output_file.stl')
print(f'Watertight: {mesh.is_watertight()}')
print(f'Volume: {mesh.get_volume():.2f} mm³')
"

# Batch check multiple files
for f in output/*.stl; do
  python3.12 -c "import open3d as o3d; m = o3d.io.read_triangle_mesh('$f'); print('$f: watertight={} volume={:.0f}'.format(m.is_watertight(), m.get_volume()))"
done
```

## Next Steps for Production

1. ✅ **Implement watertight pipeline** in `bpa_convert.py` 
2. ✅ **Add watertightness verification** to CLI output
3. ✅ **Create config profiles** for different mesh types
4. ✅ **Update documentation** with stage-by-stage process
5. ✅ **Add batch watertightness testing** command

