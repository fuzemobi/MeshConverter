#!/usr/bin/env python3
"""
Robust mesh converter - works with any scale
"""

import sys
import numpy as np
import open3d as o3d
from pathlib import Path

def convert_mesh(input_file, output_dir=None):
    """Convert mesh with robust parameters"""
    
    print(f"\n{'='*60}")
    print(f"Loading: {input_file}")
    print(f"{'='*60}")
    
    # Load mesh
    mesh = o3d.io.read_triangle_mesh(input_file)
    print(f"Vertices: {len(mesh.vertices):,}")
    print(f"Triangles: {len(mesh.triangles):,}")
    
    # Get bounding box
    bbox = mesh.get_axis_aligned_bounding_box()
    extent = bbox.get_extent()
    max_extent = max(extent)
    diagonal = np.linalg.norm(extent)
    
    print(f"Bounding box: {extent}")
    print(f"Max dimension: {max_extent:.3f}")
    print(f"Diagonal: {diagonal:.3f}")
    
    # Scale parameters based on diagonal (most robust)
    voxel_size = diagonal / 200       # 0.5% of diagonal
    
    print(f"\nUsing voxel size: {voxel_size:.4f}")
    
    # Convert to point cloud
    print("\nSampling 50,000 points...")
    pcd = mesh.sample_points_uniformly(number_of_points=50000)
    
    # Downsample
    print(f"Downsampling...")
    pcd_down = pcd.voxel_down_sample(voxel_size=voxel_size)
    print(f"→ {len(pcd_down.points):,} points after downsampling")
    
    # Statistical outlier removal (gentle)
    print("Removing statistical outliers...")
    cl, ind = pcd_down.remove_statistical_outlier(nb_neighbors=20, std_ratio=3.0)
    pcd_clean = pcd_down.select_by_index(ind)
    removed = len(pcd_down.points) - len(pcd_clean.points)
    print(f"→ Removed {removed:,} outliers")
    print(f"→ {len(pcd_clean.points):,} points remaining")
    
    if len(pcd_clean.points) < 100:
        print("✗ ERROR: Too few points remaining! Skipping radius outlier removal.")
        pcd_final = pcd_clean
    else:
        # SKIP radius outlier removal - it's too aggressive
        print("Skipping radius outlier removal (using only statistical)")
        pcd_final = pcd_clean
    
    if len(pcd_final.points) == 0:
        print("✗ ERROR: No points remaining!")
        return None
    
    # Estimate normals
    print("Estimating normals...")
    search_radius = voxel_size * 5  # 5x voxel size
    pcd_final.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=search_radius, 
            max_nn=30
        )
    )
    pcd_final.orient_normals_towards_camera_location(pcd_final.get_center())
    print(f"→ Normals estimated (search radius: {search_radius:.4f})")
    
    # Reconstruct surface
    print("Reconstructing surface with Poisson...")
    mesh_recon, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd_final, depth=9
    )
    print(f"→ Reconstructed: {len(mesh_recon.vertices):,} vertices, {len(mesh_recon.triangles):,} triangles")
    
    # Remove low-density artifacts
    densities = np.asarray(densities)
    density_threshold = np.quantile(densities, 0.01)
    vertices_to_remove = densities < density_threshold
    mesh_recon.remove_vertices_by_mask(vertices_to_remove)
    print(f"→ Removed {vertices_to_remove.sum():,} low-density vertices")
    print(f"→ Clean mesh: {len(mesh_recon.vertices):,} vertices, {len(mesh_recon.triangles):,} triangles")
    
    # Simplify
    target_triangles = 5000
    print(f"Simplifying to ~{target_triangles:,} triangles...")
    mesh_simple = mesh_recon.simplify_quadric_decimation(
        target_number_of_triangles=target_triangles
    )
    reduction = (1 - len(mesh_simple.triangles) / len(mesh.triangles)) * 100
    print(f"→ Simplified: {len(mesh_simple.triangles):,} triangles ({reduction:.1f}% reduction)")
    
    # Export
    input_path = Path(input_file)
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{input_path.stem}_simplified.stl"
    o3d.io.write_triangle_mesh(str(output_file), mesh_simple)
    
    # Also export the point cloud for inspection
    pcd_output = output_dir / f"{input_path.stem}_pointcloud.ply"
    o3d.io.write_point_cloud(str(pcd_output), pcd_final)
    
    print(f"\n{'='*60}")
    print(f"✓ SUCCESS!")
    print(f"{'='*60}")
    print(f"Simplified mesh: {output_file}")
    print(f"Point cloud: {pcd_output}")
    print(f"\nStatistics:")
    print(f"  Original: {len(mesh.triangles):,} triangles")
    print(f"  Simplified: {len(mesh_simple.triangles):,} triangles")
    print(f"  Outliers removed: {removed:,}")
    print(f"  Artifacts removed: {vertices_to_remove.sum():,}")
    
    return str(output_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python robust_convert.py input.stl [output_dir]")
        print("\nExample:")
        print("  python robust_convert.py tests/samples/simple_block.stl")
        print("  python robust_convert.py mesh.stl output/")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = convert_mesh(input_file, output_dir)
        if result:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)