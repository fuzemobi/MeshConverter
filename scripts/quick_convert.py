#!/usr/bin/env python3
"""
Quick mesh converter with auto-scaling
Automatically detects mesh units and adjusts parameters
"""

import sys
import numpy as np
import open3d as o3d
from pathlib import Path

def convert_mesh(input_file, output_dir=None):
    """Convert mesh with auto-scaled parameters"""
    
    print(f"\n{'='*60}")
    print(f"Loading: {input_file}")
    print(f"{'='*60}")
    
    # Load mesh
    mesh = o3d.io.read_triangle_mesh(input_file)
    print(f"Vertices: {len(mesh.vertices):,}")
    print(f"Triangles: {len(mesh.triangles):,}")
    
    # Detect scale by looking at bounding box
    bbox = mesh.get_axis_aligned_bounding_box()
    extent = bbox.get_extent()
    max_extent = max(extent)
    
    print(f"Bounding box extent: {extent}")
    print(f"Max dimension: {max_extent:.2f}")
    
    # Auto-detect if mesh is in mm or m
    if max_extent > 100:
        print("→ Detected: Mesh in MILLIMETERS")
        voxel_size = max_extent / 50  # ~2% of largest dimension
        radius = max_extent / 20      # ~5% of largest dimension
    else:
        print("→ Detected: Mesh in METERS")
        voxel_size = max_extent / 500  # ~0.2% of largest dimension
        radius = max_extent / 200      # ~0.5% of largest dimension
    
    print(f"Auto-scaled voxel size: {voxel_size:.3f}")
    print(f"Auto-scaled radius: {radius:.3f}")
    
    # Convert to point cloud
    print("\nSampling points...")
    pcd = mesh.sample_points_uniformly(number_of_points=50000)
    
    # Downsample
    print(f"Downsampling (voxel={voxel_size:.3f})...")
    pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    print(f"→ {len(pcd.points):,} points")
    
    # Statistical outlier removal
    print("Removing statistical outliers...")
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    pcd = pcd.select_by_index(ind)
    print(f"→ {len(pcd.points):,} points remaining")
    
    # Radius outlier removal (gentler)
    print(f"Removing radius outliers (radius={radius:.3f})...")
    cl, ind = pcd.remove_radius_outlier(nb_points=10, radius=radius)
    pcd = pcd.select_by_index(ind)
    print(f"→ {len(pcd.points):,} points remaining")
    
    if len(pcd.points) == 0:
        print("✗ ERROR: All points removed! Mesh may be too sparse.")
        return None
    
    # Estimate normals
    print("Estimating normals...")
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=radius*2, 
            max_nn=30
        )
    )
    pcd.orient_normals_towards_camera_location(pcd.get_center())
    print(f"→ Normals estimated")
    
    # Reconstruct surface
    print("Reconstructing surface...")
    mesh_recon, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=9
    )
    print(f"→ {len(mesh_recon.vertices):,} vertices, {len(mesh_recon.triangles):,} triangles")
    
    # Remove low-density artifacts
    densities = np.asarray(densities)
    density_threshold = np.quantile(densities, 0.01)
    vertices_to_remove = densities < density_threshold
    mesh_recon.remove_vertices_by_mask(vertices_to_remove)
    print(f"→ Removed {vertices_to_remove.sum():,} artifact vertices")
    
    # Simplify
    print("Simplifying mesh...")
    mesh_simple = mesh_recon.simplify_quadric_decimation(target_number_of_triangles=5000)
    print(f"→ {len(mesh_simple.triangles):,} triangles")
    
    # Export
    input_path = Path(input_file)
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{input_path.stem}_simplified.stl"
    o3d.io.write_triangle_mesh(str(output_file), mesh_simple)
    
    print(f"\n{'='*60}")
    print(f"✓ SUCCESS!")
    print(f"{'='*60}")
    print(f"Output: {output_file}")
    print(f"Original: {len(mesh.triangles):,} triangles")
    print(f"Simplified: {len(mesh_simple.triangles):,} triangles")
    
    return str(output_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quick_convert.py input.stl [output_dir]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        convert_mesh(input_file, output_dir)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)