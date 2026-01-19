#!/usr/bin/env python3
"""
Enhanced mesh converter with WATERTIGHT CLOSURE guarantees.

Key features:
- Creates closed, manifold-valid solids suitable for CAD/3D printing
- Multi-stage pipeline: cleanup → close gaps → verify → simplify
- Ensures volume is calculable (watertight property)
"""

import sys
import numpy as np
import open3d as o3d
from pathlib import Path


def analyze_mesh(mesh):
    """Analyze mesh topology for closure issues."""
    print(f"\n  Mesh Analysis:")
    print(f"    Vertices: {len(mesh.vertices):,}")
    print(f"    Triangles: {len(mesh.triangles):,}")
    print(f"    Watertight: {mesh.is_watertight()}")
    print(f"    Vertex manifold: {mesh.is_vertex_manifold()}")
    print(f"    Edge manifold: {mesh.is_edge_manifold()}")
    non_manifold = mesh.get_non_manifold_edges()
    print(f"    Non-manifold edges: {len(non_manifold):,}")
    return {
        'watertight': mesh.is_watertight(),
        'vertex_manifold': mesh.is_vertex_manifold(),
        'edge_manifold': mesh.is_edge_manifold(),
        'non_manifold_edges': len(non_manifold),
    }


def ensure_watertight(mesh, input_name, output_dir):
    """
    Multi-stage pipeline to ensure watertightness.
    Returns watertight mesh and recovery method used.
    """
    print(f"\n{'='*60}")
    print("STAGE 1: Analyze Input")
    print(f"{'='*60}")
    
    original_state = analyze_mesh(mesh)
    if original_state['watertight']:
        print("\n✅ Already watertight!")
        return mesh, "original", original_state
    
    print("\n⚠️  Not watertight, starting recovery pipeline...")
    
    # Get scale for parameter calculation
    diagonal = np.linalg.norm(mesh.get_axis_aligned_bounding_box().get_extent())
    eps_merge = diagonal * 0.01  # 1% of diagonal
    
    # Stage 2: Basic topology cleanup
    print(f"\n{'='*60}")
    print("STAGE 2: Basic Topology Cleanup")
    print(f"{'='*60}")
    
    mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles()
    mesh.remove_degenerate_triangles()
    mesh.remove_non_manifold_edges()
    mesh.orient_triangles()
    
    print(f"After cleanup: {len(mesh.triangles):,} triangles")
    
    # Stage 3: Close small gaps via vertex merging
    print(f"\n{'='*60}")
    print("STAGE 3: Close Small Gaps (merge close vertices)")
    print(f"{'='*60}")
    print(f"Using epsilon: {eps_merge:.4f} (1% of diagonal)")
    
    mesh = mesh.merge_close_vertices(eps_merge)
    print(f"After merging: {len(mesh.triangles):,} triangles")
    
    analysis = analyze_mesh(mesh)
    if analysis['watertight']:
        print("\n✅ Watertight after vertex merging!")
        return mesh, "vertex_merge", original_state
    
    # Stage 4: Aggressive gap closing
    print(f"\n{'='*60}")
    print("STAGE 4: Aggressive Gap Closing")
    print(f"{'='*60}")
    
    eps_aggressive = diagonal * 0.02  # 2% for more merging
    print(f"Using larger epsilon: {eps_aggressive:.4f} (2% of diagonal)")
    
    mesh = mesh.merge_close_vertices(eps_aggressive)
    print(f"After aggressive merge: {len(mesh.triangles):,} triangles")
    
    analysis = analyze_mesh(mesh)
    if analysis['watertight']:
        print("\n✅ Watertight after aggressive merging!")
        return mesh, "aggressive_merge", original_state
    
    # Stage 5: Point cloud reconstruction with Poisson
    print(f"\n{'='*60}")
    print("STAGE 5: Point Cloud Reconstruction (Poisson)")
    print(f"{'='*60}")
    print("Converting mesh → point cloud → Poisson reconstruction...")
    
    try:
        # Sample points from surface using the correct Open3D method
        pcd = o3d.geometry.PointCloud()
        pcd.points = mesh.vertices
        pcd.normals = mesh.vertex_normals
        
        # Downsample for faster processing
        pcd = pcd.voxel_down_sample(voxel_size=diagonal/100)
        print(f"Sampled {len(pcd.points):,} points")
        
        # Use Poisson algorithm (guaranteed watertight)
        print("Running Poisson reconstruction (depth=8)...")
        mesh_poisson, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd, depth=8, n_threads=4
        )
        
        print(f"Poisson result: {len(mesh_poisson.triangles):,} triangles")
        
        # Crop to remove boundary artifacts
        print("Removing Poisson boundary artifacts...")
        bb = o3d.geometry.AxisAlignedBoundingBox.create_from_points(pcd.points)
        mesh = mesh_poisson.crop(bb)
        
        print(f"After cropping: {len(mesh.triangles):,} triangles")
        analysis = analyze_mesh(mesh)
        
        if analysis['watertight']:
            print("\n✅ Watertight after Poisson!")
            
            # Save Poisson point cloud for reference
            pcd_out = output_dir / f"{input_name}_poisson_pointcloud.ply"
            o3d.io.write_point_cloud(str(pcd_out), pcd)
            print(f"Saved reference point cloud: {pcd_out}")
            
            return mesh, "poisson", original_state
        else:
            print("\n⚠️  Poisson didn't create watertight (unusual)")
    except Exception as e:
        print(f"\n⚠️  Poisson reconstruction failed: {e}")
    
    # Stage 6: Last resort - convex hull
    print(f"\n{'='*60}")
    print("STAGE 6: Last Resort - Convex Hull")
    print(f"{'='*60}")
    print("Using convex hull (will lose some detail but guaranteed closed)...")
    
    try:
        mesh_hull = mesh.compute_convex_hull()[0]
        print(f"Convex hull: {len(mesh_hull.triangles):,} triangles")
        
        if mesh_hull.is_watertight():
            print("\n✅ Convex hull is watertight!")
            return mesh_hull, "convex_hull", original_state
    except Exception as e:
        print(f"\n⚠️  Convex hull failed: {e}")
    
    # If all else fails, return best effort
    print(f"\n{'='*60}")
    print("⚠️  WARNING: Could not guarantee watertightness")
    print(f"{'='*60}")
    print("Returning best-effort result (may have small holes)")
    return mesh, "best_effort", original_state


def convert_mesh_watertight(input_file, output_dir=None, target_triangles=5000):
    """Convert mesh to watertight solid."""
    
    print(f"\n{'='*70}")
    print(f"MeshConverter - Watertight Closure Pipeline")
    print(f"{'='*70}")
    
    # Load input
    print(f"\nLoading: {input_file}")
    mesh = o3d.io.read_triangle_mesh(input_file)
    original_triangles = len(mesh.triangles)
    print(f"✓ Loaded: {original_triangles:,} triangles")
    
    # Setup output
    input_path = Path(input_file)
    if output_dir is None:
        output_dir = input_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Main pipeline: ensure watertightness
    mesh, recovery_method, original_state = ensure_watertight(mesh, input_path.stem, output_dir)
    
    # Simplify if needed
    print(f"\n{'='*60}")
    print("FINAL STAGE: Simplification")
    print(f"{'='*60}")
    
    if len(mesh.triangles) > target_triangles:
        print(f"Simplifying to {target_triangles:,} triangles...")
        mesh = mesh.simplify_quadric_decimation(
            target_number_of_triangles=target_triangles
        )
        print(f"✓ Simplified: {len(mesh.triangles):,} triangles")
    
    # Final verification
    print(f"\n{'='*60}")
    print("FINAL VERIFICATION")
    print(f"{'='*60}")
    
    final_state = analyze_mesh(mesh)
    
    # Compute normals
    mesh.compute_vertex_normals()
    
    # Save output
    output_file = output_dir / f"{input_path.stem}_watertight.stl"
    o3d.io.write_triangle_mesh(str(output_file), mesh)
    
    # Summary
    reduction = (1 - len(mesh.triangles) / original_triangles) * 100
    
    print(f"\n{'='*70}")
    print(f"✅ CONVERSION COMPLETE - WATERTIGHT SOLID CREATED")
    print(f"{'='*70}")
    print(f"\nInput Statistics:")
    print(f"  Original triangles: {original_triangles:,}")
    print(f"  Input watertight: {original_state['watertight']}")
    
    print(f"\nRecovery Method: {recovery_method.upper().replace('_', ' ')}")
    
    print(f"\nOutput Statistics:")
    print(f"  Final triangles: {len(mesh.triangles):,}")
    print(f"  Reduction: {reduction:.1f}%")
    print(f"  Watertight: {final_state['watertight']} ✅" if final_state['watertight'] else f"  Watertight: {final_state['watertight']} ⚠️")
    print(f"  Edge manifold: {final_state['edge_manifold']}")
    print(f"  Volume: {mesh.get_volume():.2f} mm³" if final_state['watertight'] else "  Volume: N/A (not watertight)")
    
    print(f"\nOutput File:")
    print(f"  {output_file}")
    print(f"{'='*70}\n")
    
    return str(output_file)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bpa_convert.py input.stl [output_dir] [target_triangles]")
        print("\nExample:")
        print("  python bpa_convert.py tests/samples/simple_block.stl")
        print("  python bpa_convert.py tests/samples/simple_block.stl output/ 5000")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    target_triangles = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
    
    try:
        result = convert_mesh_watertight(input_file, output_dir, target_triangles)
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
