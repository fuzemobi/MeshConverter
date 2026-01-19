#!/usr/bin/env python3
"""
Mesh converter using Ball Pivoting Algorithm (BPA)
More robust than Poisson for complex meshes
"""

import sys
import numpy as np
import open3d as o3d
from pathlib import Path

def convert_mesh(input_file, output_dir=None):
    """Convert mesh using Ball Pivoting Algorithm"""
    
    print(f"\n{'='*60}")
    print(f"Loading: {input_file}")
    print(f"{'='*60}")
    
    # Load mesh
    mesh = o3d.io.read_triangle_mesh(input_file)
    print(f"Original mesh:")
    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Triangles: {len(mesh.triangles):,}")
    
    # Get diagonal for scaling
    bbox = mesh.get_axis_aligned_bounding_box()
    extent = bbox.get_extent()
    diagonal = np.linalg.norm(extent)
    
    print(f"  Bounding box diagonal: {diagonal:.3f}")
    
    # Method 1: Direct mesh simplification (fastest, most reliable)
    print(f"\n{'='*60}")
    print("METHOD 1: Direct Mesh Simplification")
    print(f"{'='*60}")
    
    # Clean up the mesh first
    mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles()
    mesh.remove_degenerate_triangles()
    mesh.remove_non_manifold_edges()
    
    print(f"After cleanup:")
    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Triangles: {len(mesh.triangles):,}")
    
    # Simplify
    target_triangles = 5000
    print(f"\nSimplifying to ~{target_triangles:,} triangles...")
    mesh_simple = mesh.simplify_quadric_decimation(
        target_number_of_triangles=target_triangles
    )
    
    reduction = (1 - len(mesh_simple.triangles) / len(mesh.triangles)) * 100
    print(f"→ Simplified: {len(mesh_simple.triangles):,} triangles ({reduction:.1f}% reduction)")

    # Compute normals before saving
    mesh_simple.compute_vertex_normals()

    # Export Method 1 result
    input_path = Path(input_file)
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    output_file_method1 = output_dir / f"{input_path.stem}_simplified_direct.stl"
    o3d.io.write_triangle_mesh(str(output_file_method1), mesh_simple)
    print(f"✓ Saved: {output_file_method1}")
    
    # Method 2: Point cloud reconstruction (slower, more aggressive cleaning)
    print(f"\n{'='*60}")
    print("METHOD 2: Point Cloud Reconstruction")
    print(f"{'='*60}")
    
    voxel_size = diagonal / 200
    print(f"Voxel size: {voxel_size:.4f}")
    
    # Sample points
    print("Sampling 50,000 points...")
    pcd = mesh.sample_points_uniformly(number_of_points=50000)
    
    # Downsample
    print("Downsampling...")
    pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    print(f"→ {len(pcd.points):,} points")
    
    # Light statistical cleaning
    print("Removing outliers...")
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=3.0)
    pcd = pcd.select_by_index(ind)
    print(f"→ {len(pcd.points):,} points remaining")
    
    # Estimate normals
    print("Estimating normals...")
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=voxel_size * 5, 
            max_nn=30
        )
    )
    pcd.orient_normals_towards_camera_location(pcd.get_center())
    
    # Try Ball Pivoting Algorithm instead of Poisson
    print("Reconstructing with Ball Pivoting Algorithm...")
    
    # BPA needs multiple radii to work well
    radii = [voxel_size * 2, voxel_size * 4, voxel_size * 8]
    mesh_bpa = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
        pcd,
        o3d.utility.DoubleVector(radii)
    )
    
    print(f"→ Reconstructed: {len(mesh_bpa.vertices):,} vertices, {len(mesh_bpa.triangles):,} triangles")
    
    if len(mesh_bpa.triangles) > 0:
        # Clean and simplify
        mesh_bpa.remove_duplicated_vertices()
        mesh_bpa.remove_duplicated_triangles()
        mesh_bpa.remove_degenerate_triangles()
        
        print(f"After cleanup: {len(mesh_bpa.triangles):,} triangles")
        
        if len(mesh_bpa.triangles) > target_triangles:
            mesh_bpa = mesh_bpa.simplify_quadric_decimation(
                target_number_of_triangles=target_triangles
            )
            print(f"After simplification: {len(mesh_bpa.triangles):,} triangles")
        
        output_file_method2 = output_dir / f"{input_path.stem}_simplified_bpa.stl"
        o3d.io.write_triangle_mesh(str(output_file_method2), mesh_bpa)
        print(f"✓ Saved: {output_file_method2}")
    else:
        print("⚠ BPA reconstruction failed (0 triangles)")
        output_file_method2 = None
    
    # Save point cloud for inspection
    pcd_output = output_dir / f"{input_path.stem}_pointcloud.ply"
    o3d.io.write_point_cloud(str(pcd_output), pcd)
    print(f"✓ Saved point cloud: {pcd_output}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✓ COMPLETE!")
    print(f"{'='*60}")
    print(f"\nFiles created:")
    print(f"  1. {output_file_method1.name}")
    print(f"     → Direct simplification (RECOMMENDED)")
    print(f"     → {len(mesh_simple.triangles):,} triangles")
    
    if output_file_method2:
        print(f"  2. {output_file_method2.name}")
        print(f"     → Point cloud reconstruction")
        print(f"     → {len(mesh_bpa.triangles):,} triangles")
    
    print(f"  3. {pcd_output.name}")
    print(f"     → Point cloud for inspection")
    print(f"     → {len(pcd.points):,} points")
    
    print(f"\nOriginal mesh: {len(mesh.triangles):,} triangles")
    print(f"Reduction: {reduction:.1f}%")
    
    return str(output_file_method1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bpa_convert.py input.stl [output_dir]")
        print("\nExample:")
        print("  python bpa_convert.py tests/samples/simple_block.stl")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = convert_mesh(input_file, output_dir)
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)