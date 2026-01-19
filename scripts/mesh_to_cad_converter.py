#!/usr/bin/env python3
"""
Mesh to Parametric CAD Converter
Converts STL mesh scans to simplified CAD files with outlier removal

Based on research from:
- Open3D for point cloud processing and outlier removal
- pyRANSAC-3D for primitive shape fitting
- PythonOCC for STEP export

Author: MedTrackET Team
Project: MeshConverter_v2
"""

import numpy as np
import open3d as o3d
from pathlib import Path
import argparse
import sys
from typing import Tuple, Dict, Optional
import json


class MeshToCADConverter:
    """
    Comprehensive mesh to CAD converter with outlier removal
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize converter with configuration
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self.default_config()
        self.statistics = {}
        
    @staticmethod
    def default_config() -> Dict:
        """Default configuration parameters"""
        return {
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
            
            # RANSAC parameters
            'ransac_distance_threshold': 0.01,
            'ransac_n': 3,
            'ransac_iterations': 1000,
            
            # Poisson reconstruction
            'poisson_depth': 9,
            'density_quantile': 0.01,  # Remove lowest 1% density vertices
            
            # Mesh simplification
            'target_triangles': 5000,
            
            # Output
            'export_intermediates': True,
        }
    
    def load_mesh(self, filepath: str) -> o3d.geometry.TriangleMesh:
        """
        Load mesh from file
        
        Args:
            filepath: Path to STL file
            
        Returns:
            Open3D TriangleMesh
        """
        print(f"\n{'='*60}")
        print(f"LOADING MESH: {filepath}")
        print(f"{'='*60}")
        
        mesh = o3d.io.read_triangle_mesh(filepath)
        
        if not mesh.has_vertices():
            raise ValueError(f"Failed to load mesh from {filepath}")
        
        self.statistics['original_vertices'] = len(mesh.vertices)
        self.statistics['original_triangles'] = len(mesh.triangles)
        
        print(f"✓ Loaded mesh:")
        print(f"  Vertices: {len(mesh.vertices):,}")
        print(f"  Triangles: {len(mesh.triangles):,}")
        print(f"  Bounds: {mesh.get_min_bound()} to {mesh.get_max_bound()}")
        
        return mesh
    
    def mesh_to_pointcloud(
        self, 
        mesh: o3d.geometry.TriangleMesh, 
        num_points: int = 50000
    ) -> o3d.geometry.PointCloud:
        """
        Convert mesh to point cloud
        
        Args:
            mesh: Input triangle mesh
            num_points: Number of points to sample
            
        Returns:
            Point cloud
        """
        print(f"\n{'='*60}")
        print("CONVERTING MESH TO POINT CLOUD")
        print(f"{'='*60}")
        
        pcd = mesh.sample_points_uniformly(number_of_points=num_points)
        
        print(f"✓ Sampled {len(pcd.points):,} points from mesh")
        
        return pcd
    
    def downsample(
        self, 
        pcd: o3d.geometry.PointCloud
    ) -> o3d.geometry.PointCloud:
        """
        Downsample point cloud using voxel grid
        
        Args:
            pcd: Input point cloud
            
        Returns:
            Downsampled point cloud
        """
        print(f"\n{'='*60}")
        print("DOWNSAMPLING POINT CLOUD")
        print(f"{'='*60}")
        
        voxel_size = self.config['voxel_size']
        pcd_down = pcd.voxel_down_sample(voxel_size=voxel_size)
        
        reduction = (1 - len(pcd_down.points) / len(pcd.points)) * 100
        
        print(f"✓ Voxel size: {voxel_size}m")
        print(f"✓ Points: {len(pcd.points):,} → {len(pcd_down.points):,}")
        print(f"✓ Reduction: {reduction:.1f}%")
        
        self.statistics['downsampled_points'] = len(pcd_down.points)
        
        return pcd_down
    
    def remove_statistical_outliers(
        self, 
        pcd: o3d.geometry.PointCloud
    ) -> o3d.geometry.PointCloud:
        """
        Remove statistical outliers
        
        Args:
            pcd: Input point cloud
            
        Returns:
            Cleaned point cloud
        """
        print(f"\n{'='*60}")
        print("REMOVING STATISTICAL OUTLIERS")
        print(f"{'='*60}")
        
        nb_neighbors = self.config['stat_nb_neighbors']
        std_ratio = self.config['stat_std_ratio']
        
        cl, ind = pcd.remove_statistical_outlier(
            nb_neighbors=nb_neighbors,
            std_ratio=std_ratio
        )
        pcd_clean = pcd.select_by_index(ind)
        
        removed = len(pcd.points) - len(pcd_clean.points)
        
        print(f"✓ Neighbors: {nb_neighbors}, Std ratio: {std_ratio}")
        print(f"✓ Removed: {removed:,} outliers")
        print(f"✓ Remaining: {len(pcd_clean.points):,} points")
        
        self.statistics['stat_outliers_removed'] = removed
        
        return pcd_clean
    
    def remove_radius_outliers(
        self, 
        pcd: o3d.geometry.PointCloud
    ) -> o3d.geometry.PointCloud:
        """
        Remove radius outliers
        
        Args:
            pcd: Input point cloud
            
        Returns:
            Cleaned point cloud
        """
        print(f"\n{'='*60}")
        print("REMOVING RADIUS OUTLIERS")
        print(f"{'='*60}")
        
        nb_points = self.config['radius_nb_points']
        radius = self.config['radius']
        
        cl, ind = pcd.remove_radius_outlier(
            nb_points=nb_points,
            radius=radius
        )
        pcd_clean = pcd.select_by_index(ind)
        
        removed = len(pcd.points) - len(pcd_clean.points)
        
        print(f"✓ Min neighbors: {nb_points}, Radius: {radius}m")
        print(f"✓ Removed: {removed:,} sparse points")
        print(f"✓ Remaining: {len(pcd_clean.points):,} points")
        
        self.statistics['radius_outliers_removed'] = removed
        
        return pcd_clean
    
    def estimate_normals(
        self, 
        pcd: o3d.geometry.PointCloud
    ) -> o3d.geometry.PointCloud:
        """
        Estimate and orient point cloud normals
        
        Args:
            pcd: Input point cloud
            
        Returns:
            Point cloud with normals
        """
        print(f"\n{'='*60}")
        print("ESTIMATING NORMALS")
        print(f"{'='*60}")
        
        radius = self.config['normal_radius']
        max_nn = self.config['normal_max_nn']
        
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=radius,
                max_nn=max_nn
            )
        )
        
        # Orient normals consistently
        pcd.orient_normals_towards_camera_location(pcd.get_center())
        
        print(f"✓ Search radius: {radius}m, Max neighbors: {max_nn}")
        print(f"✓ Estimated normals for {len(pcd.normals):,} points")
        print(f"✓ Oriented normals towards center")
        
        return pcd
    
    def detect_cylinder(
        self, 
        pcd: o3d.geometry.PointCloud
    ) -> Optional[Dict]:
        """
        Detect cylinder using RANSAC
        
        Args:
            pcd: Input point cloud
            
        Returns:
            Dictionary with cylinder parameters or None
        """
        print(f"\n{'='*60}")
        print("DETECTING CYLINDER GEOMETRY")
        print(f"{'='*60}")
        
        try:
            import pyransac3d as pyrsc
            
            points = np.asarray(pcd.points)
            
            # Fit cylinder
            cyl = pyrsc.Cylinder()
            center, axis, radius, inliers = cyl.fit(
                points,
                thresh=self.config['ransac_distance_threshold'],
                maxIteration=self.config['ransac_iterations']
            )
            
            # Calculate length by projecting points onto axis
            projections = np.dot(points - center, axis)
            length = projections.max() - projections.min()
            
            cylinder_params = {
                'center': center.tolist(),
                'axis': axis.tolist(),
                'radius': float(radius),
                'length': float(length),
                'inliers': len(inliers),
                'inlier_ratio': len(inliers) / len(points)
            }
            
            print(f"✓ Detected cylinder:")
            print(f"  Center: {center}")
            print(f"  Axis: {axis}")
            print(f"  Radius: {radius:.3f}m")
            print(f"  Length: {length:.3f}m")
            print(f"  Inliers: {len(inliers):,} ({cylinder_params['inlier_ratio']:.1%})")
            
            self.statistics['cylinder_params'] = cylinder_params
            
            return cylinder_params
            
        except ImportError:
            print("⚠ pyRANSAC-3D not installed. Skipping cylinder detection.")
            print("  Install with: pip install pyransac3d")
            return None
    
    def reconstruct_surface(
        self, 
        pcd: o3d.geometry.PointCloud
    ) -> o3d.geometry.TriangleMesh:
        """
        Reconstruct surface from point cloud using Poisson
        
        Args:
            pcd: Input point cloud with normals
            
        Returns:
            Reconstructed mesh
        """
        print(f"\n{'='*60}")
        print("RECONSTRUCTING SURFACE (POISSON)")
        print(f"{'='*60}")
        
        depth = self.config['poisson_depth']
        
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd,
            depth=depth
        )
        
        print(f"✓ Poisson depth: {depth}")
        print(f"✓ Reconstructed mesh:")
        print(f"  Vertices: {len(mesh.vertices):,}")
        print(f"  Triangles: {len(mesh.triangles):,}")
        
        # Remove low-density vertices (artifacts)
        densities = np.asarray(densities)
        density_threshold = np.quantile(densities, self.config['density_quantile'])
        vertices_to_remove = densities < density_threshold
        
        mesh.remove_vertices_by_mask(vertices_to_remove)
        
        removed = vertices_to_remove.sum()
        print(f"✓ Removed {removed:,} low-density vertices (artifacts)")
        print(f"✓ Final mesh:")
        print(f"  Vertices: {len(mesh.vertices):,}")
        print(f"  Triangles: {len(mesh.triangles):,}")
        
        self.statistics['reconstructed_vertices'] = len(mesh.vertices)
        self.statistics['reconstructed_triangles'] = len(mesh.triangles)
        self.statistics['artifacts_removed'] = int(removed)
        
        return mesh
    
    def simplify_mesh(
        self, 
        mesh: o3d.geometry.TriangleMesh
    ) -> o3d.geometry.TriangleMesh:
        """
        Simplify mesh using quadric decimation
        
        Args:
            mesh: Input mesh
            
        Returns:
            Simplified mesh
        """
        print(f"\n{'='*60}")
        print("SIMPLIFYING MESH")
        print(f"{'='*60}")
        
        target_triangles = self.config['target_triangles']
        
        mesh_simplified = mesh.simplify_quadric_decimation(
            target_number_of_triangles=target_triangles
        )
        
        reduction = (1 - len(mesh_simplified.triangles) / len(mesh.triangles)) * 100
        
        print(f"✓ Target triangles: {target_triangles:,}")
        print(f"✓ Triangles: {len(mesh.triangles):,} → {len(mesh_simplified.triangles):,}")
        print(f"✓ Reduction: {reduction:.1f}%")
        
        self.statistics['simplified_triangles'] = len(mesh_simplified.triangles)
        
        return mesh_simplified
    
    def export_mesh(
        self, 
        mesh: o3d.geometry.TriangleMesh, 
        output_path: str
    ):
        """
        Export mesh to file
        
        Args:
            mesh: Mesh to export
            output_path: Output file path
        """
        success = o3d.io.write_triangle_mesh(output_path, mesh)
        
        if success:
            print(f"✓ Exported mesh to: {output_path}")
        else:
            print(f"✗ Failed to export mesh to: {output_path}")
    
    def export_pointcloud(
        self, 
        pcd: o3d.geometry.PointCloud, 
        output_path: str
    ):
        """
        Export point cloud to file
        
        Args:
            pcd: Point cloud to export
            output_path: Output file path
        """
        success = o3d.io.write_point_cloud(output_path, pcd)
        
        if success:
            print(f"✓ Exported point cloud to: {output_path}")
        else:
            print(f"✗ Failed to export point cloud to: {output_path}")
    
    def export_statistics(self, output_path: str):
        """
        Export processing statistics to JSON
        
        Args:
            output_path: Output JSON file path
        """
        with open(output_path, 'w') as f:
            json.dump(self.statistics, f, indent=2)
        
        print(f"✓ Exported statistics to: {output_path}")
    
    def convert(
        self, 
        input_path: str, 
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        Complete conversion pipeline
        
        Args:
            input_path: Path to input STL file
            output_dir: Output directory (default: same as input)
            
        Returns:
            Dictionary with output file paths
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Setup output directory
        if output_dir is None:
            output_dir = input_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = input_path.stem
        
        # Load mesh
        mesh = self.load_mesh(str(input_path))
        
        # Convert to point cloud
        pcd = self.mesh_to_pointcloud(mesh)
        
        # Downsample
        pcd_down = self.downsample(pcd)
        
        # Remove statistical outliers
        pcd_clean1 = self.remove_statistical_outliers(pcd_down)
        
        # Remove radius outliers
        pcd_clean2 = self.remove_radius_outliers(pcd_clean1)
        
        # Estimate normals
        pcd_final = self.estimate_normals(pcd_clean2)
        
        # Detect cylinder (optional)
        cylinder_params = self.detect_cylinder(pcd_final)
        
        # Reconstruct surface
        mesh_reconstructed = self.reconstruct_surface(pcd_final)
        
        # Simplify mesh
        mesh_simplified = self.simplify_mesh(mesh_reconstructed)
        
        # Export results
        print(f"\n{'='*60}")
        print("EXPORTING RESULTS")
        print(f"{'='*60}")
        
        outputs = {}
        
        # Export cleaned point cloud
        if self.config['export_intermediates']:
            pcd_path = output_dir / f"{base_name}_cleaned.ply"
            self.export_pointcloud(pcd_final, str(pcd_path))
            outputs['pointcloud'] = str(pcd_path)
        
        # Export simplified mesh
        mesh_path = output_dir / f"{base_name}_simplified.stl"
        self.export_mesh(mesh_simplified, str(mesh_path))
        outputs['simplified_mesh'] = str(mesh_path)
        
        # Export statistics
        stats_path = output_dir / f"{base_name}_statistics.json"
        self.export_statistics(str(stats_path))
        outputs['statistics'] = str(stats_path)
        
        # Print summary
        print(f"\n{'='*60}")
        print("CONVERSION COMPLETE")
        print(f"{'='*60}")
        print(f"✓ Original: {self.statistics['original_vertices']:,} vertices, "
              f"{self.statistics['original_triangles']:,} triangles")
        print(f"✓ Simplified: {self.statistics['simplified_triangles']:,} triangles")
        print(f"✓ Outliers removed: {self.statistics.get('stat_outliers_removed', 0) + self.statistics.get('radius_outliers_removed', 0):,}")
        print(f"✓ Artifacts removed: {self.statistics.get('artifacts_removed', 0):,}")
        
        if cylinder_params:
            print(f"✓ Detected cylinder: radius={cylinder_params['radius']:.3f}m, "
                  f"length={cylinder_params['length']:.3f}m")
        
        return outputs


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='Convert mesh scans to simplified CAD files with outlier removal'
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Input STL file path'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output directory (default: same as input)'
    )
    
    parser.add_argument(
        '--voxel-size',
        type=float,
        default=0.02,
        help='Voxel size for downsampling (default: 0.02)'
    )
    
    parser.add_argument(
        '--target-triangles',
        type=int,
        default=5000,
        help='Target number of triangles (default: 5000)'
    )
    
    parser.add_argument(
        '--no-intermediates',
        action='store_true',
        help='Do not export intermediate files'
    )
    
    args = parser.parse_args()
    
    # Setup configuration
    config = MeshToCADConverter.default_config()
    config['voxel_size'] = args.voxel_size
    config['target_triangles'] = args.target_triangles
    config['export_intermediates'] = not args.no_intermediates
    
    # Create converter
    converter = MeshToCADConverter(config)
    
    # Run conversion
    try:
        outputs = converter.convert(args.input, args.output)
        
        print(f"\n{'='*60}")
        print("OUTPUT FILES:")
        print(f"{'='*60}")
        for key, path in outputs.items():
            print(f"  {key}: {path}")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
