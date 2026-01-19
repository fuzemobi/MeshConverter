#!/usr/bin/env python3
"""
Visualize mesh conversion results

Usage:
    python visualize_results.py original.stl simplified.stl
    python visualize_results.py --pointcloud cleaned.ply
"""

import sys
import argparse
import open3d as o3d
import numpy as np
from pathlib import Path


def visualize_comparison(
    original_path: str,
    simplified_path: str
):
    """
    Visualize original and simplified meshes side by side
    
    Args:
        original_path: Path to original mesh
        simplified_path: Path to simplified mesh
    """
    print("Loading meshes...")
    
    # Load meshes
    original = o3d.io.read_triangle_mesh(original_path)
    simplified = o3d.io.read_triangle_mesh(simplified_path)
    
    # Compute statistics
    orig_verts = len(original.vertices)
    orig_tris = len(original.triangles)
    simp_verts = len(simplified.vertices)
    simp_tris = len(simplified.triangles)
    
    reduction = (1 - simp_tris / orig_tris) * 100
    
    print(f"\nOriginal:")
    print(f"  Vertices: {orig_verts:,}")
    print(f"  Triangles: {orig_tris:,}")
    
    print(f"\nSimplified:")
    print(f"  Vertices: {simp_verts:,}")
    print(f"  Triangles: {simp_tris:,}")
    print(f"  Reduction: {reduction:.1f}%")
    
    # Color meshes differently
    original.paint_uniform_color([0.7, 0.7, 0.7])  # Gray
    simplified.paint_uniform_color([0.2, 0.6, 0.9])  # Blue
    
    # Compute normals for shading
    original.compute_vertex_normals()
    simplified.compute_vertex_normals()
    
    # Translate simplified mesh for side-by-side view
    bbox = original.get_axis_aligned_bounding_box()
    width = bbox.get_max_bound()[0] - bbox.get_min_bound()[0]
    simplified.translate([width * 1.2, 0, 0])
    
    print("\nVisualization controls:")
    print("  Mouse: Rotate view")
    print("  Scroll: Zoom")
    print("  Shift + Mouse: Pan")
    print("  H: Help menu")
    print("  Q: Quit")
    
    # Visualize
    o3d.visualization.draw_geometries(
        [original, simplified],
        window_name="Mesh Comparison: Original (Gray) vs Simplified (Blue)",
        width=1920,
        height=1080
    )


def visualize_pointcloud(
    pcd_path: str
):
    """
    Visualize point cloud with normals
    
    Args:
        pcd_path: Path to point cloud file
    """
    print("Loading point cloud...")
    
    pcd = o3d.io.read_point_cloud(pcd_path)
    
    print(f"\nPoint cloud:")
    print(f"  Points: {len(pcd.points):,}")
    print(f"  Has normals: {pcd.has_normals()}")
    print(f"  Has colors: {pcd.has_colors()}")
    
    # Estimate normals if not present
    if not pcd.has_normals():
        print("Estimating normals...")
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=0.1,
                max_nn=30
            )
        )
    
    print("\nVisualization controls:")
    print("  Mouse: Rotate view")
    print("  Scroll: Zoom")
    print("  Shift + Mouse: Pan")
    print("  N: Toggle normal visualization")
    print("  H: Help menu")
    print("  Q: Quit")
    
    # Visualize
    o3d.visualization.draw_geometries(
        [pcd],
        window_name="Point Cloud Visualization",
        width=1920,
        height=1080,
        point_show_normal=True
    )


def visualize_mesh(
    mesh_path: str
):
    """
    Visualize single mesh
    
    Args:
        mesh_path: Path to mesh file
    """
    print("Loading mesh...")
    
    mesh = o3d.io.read_triangle_mesh(mesh_path)
    
    print(f"\nMesh:")
    print(f"  Vertices: {len(mesh.vertices):,}")
    print(f"  Triangles: {len(mesh.triangles):,}")
    
    # Compute normals
    mesh.compute_vertex_normals()
    
    # Color mesh
    mesh.paint_uniform_color([0.7, 0.7, 0.7])
    
    print("\nVisualization controls:")
    print("  Mouse: Rotate view")
    print("  Scroll: Zoom")
    print("  Shift + Mouse: Pan")
    print("  H: Help menu")
    print("  Q: Quit")
    
    # Visualize
    o3d.visualization.draw_geometries(
        [mesh],
        window_name=f"Mesh: {Path(mesh_path).name}",
        width=1920,
        height=1080
    )


def main():
    """CLI for visualization"""
    parser = argparse.ArgumentParser(
        description='Visualize mesh conversion results'
    )
    
    parser.add_argument(
        'files',
        nargs='+',
        help='Mesh or point cloud files to visualize'
    )
    
    parser.add_argument(
        '--pointcloud',
        action='store_true',
        help='Visualize as point cloud'
    )
    
    args = parser.parse_args()
    
    if args.pointcloud:
        # Visualize point cloud
        if len(args.files) != 1:
            print("✗ Point cloud mode requires exactly one file")
            return 1
        
        visualize_pointcloud(args.files[0])
        
    elif len(args.files) == 2:
        # Compare two meshes
        visualize_comparison(args.files[0], args.files[1])
        
    elif len(args.files) == 1:
        # Visualize single mesh
        visualize_mesh(args.files[0])
        
    else:
        print("✗ Provide 1 file (single view) or 2 files (comparison)")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
