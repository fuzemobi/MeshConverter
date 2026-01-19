#!/usr/bin/env python3
"""
Baseline Multi-View Analysis using OpenCV

Strategy:
1. Render the mesh from multiple angles (top, front, side, etc.)
2. Use OpenCV to extract contours and key points
3. Create a normalized point cloud representation
4. Use fuzzy logic to merge similar views into a common model
5. Compare original vs simplified representation

This provides a clean baseline for mesh simplification without
the complexity of layer-wise stacking.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import trimesh
import numpy as np
import cv2
from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
from PIL import Image


class MultiViewAnalyzer:
    """
    Analyze mesh from multiple viewpoints and create normalized representation.
    """

    def __init__(self, image_size: int = 512, verbose: bool = True):
        """
        Args:
            image_size: Resolution for rendered views (pixels)
            verbose: Print progress messages
        """
        self.image_size = image_size
        self.verbose = verbose

    def render_view(
        self,
        mesh: trimesh.Trimesh,
        azimuth: float,
        elevation: float
    ) -> np.ndarray:
        """
        Render mesh from a specific viewpoint to binary image.

        Args:
            mesh: Input mesh
            azimuth: Rotation around Z axis (degrees)
            elevation: Rotation around X axis (degrees)

        Returns:
            Binary image (0 or 255)
        """
        # Create rotation matrix
        az_rad = np.radians(azimuth)
        el_rad = np.radians(elevation)

        # Rotate mesh
        mesh_copy = mesh.copy()

        # Rotate around Z (azimuth)
        rot_z = trimesh.transformations.rotation_matrix(az_rad, [0, 0, 1])
        mesh_copy.apply_transform(rot_z)

        # Rotate around X (elevation)
        rot_x = trimesh.transformations.rotation_matrix(el_rad, [1, 0, 0])
        mesh_copy.apply_transform(rot_x)

        # Project to 2D (orthographic projection - just drop Z coordinate)
        vertices_2d = mesh_copy.vertices[:, :2]  # Take X, Y only

        # Normalize to image space
        min_coords = vertices_2d.min(axis=0)
        max_coords = vertices_2d.max(axis=0)
        range_coords = max_coords - min_coords

        if range_coords.max() == 0:
            # Degenerate case
            return np.zeros((self.image_size, self.image_size), dtype=np.uint8)

        # Add 10% padding
        padding = 0.1
        scale = (self.image_size * (1 - 2*padding)) / range_coords.max()

        vertices_normalized = (vertices_2d - min_coords) * scale + self.image_size * padding
        vertices_pixels = vertices_normalized.astype(np.int32)

        # Create binary image by drawing filled triangles
        img = np.zeros((self.image_size, self.image_size), dtype=np.uint8)

        for face in mesh_copy.faces:
            pts = vertices_pixels[face]
            cv2.fillConvexPoly(img, pts, 255)

        return img

    def extract_contour_points(self, binary_image: np.ndarray) -> np.ndarray:
        """
        Extract contour points from binary image using OpenCV.

        Args:
            binary_image: Binary image (0 or 255)

        Returns:
            Array of contour points (Nx2)
        """
        # Find contours
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if len(contours) == 0:
            return np.array([])

        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)

        # Simplify contour (Douglas-Peucker algorithm)
        epsilon = 0.01 * cv2.arcLength(largest_contour, True)
        simplified = cv2.approxPolyDP(largest_contour, epsilon, True)

        # Extract points
        points = simplified.reshape(-1, 2)

        return points

    def analyze_multi_view(
        self,
        mesh: trimesh.Trimesh,
        views: List[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """
        Analyze mesh from multiple viewpoints.

        Args:
            mesh: Input mesh
            views: List of (azimuth, elevation) tuples
                  Default: 6 standard views (front, back, left, right, top, bottom)

        Returns:
            Dictionary with analysis results
        """
        if views is None:
            # Standard 6 views
            views = [
                (0, 0),      # Front
                (180, 0),    # Back
                (90, 0),     # Right
                (270, 0),    # Left
                (0, 90),     # Top
                (0, -90),    # Bottom
            ]

        if self.verbose:
            print(f"\n🔍 Multi-View Analysis")
            print(f"   Analyzing {len(views)} viewpoints...")

        results = {
            'views': [],
            'total_points': 0,
            'mesh_info': {
                'vertices': len(mesh.vertices),
                'faces': len(mesh.faces),
                'volume': mesh.volume,
                'extents': mesh.extents.tolist()
            }
        }

        for i, (azimuth, elevation) in enumerate(views):
            if self.verbose:
                print(f"   View {i+1}/{len(views)}: azimuth={azimuth}°, elevation={elevation}°")

            # Render view
            img = self.render_view(mesh, azimuth, elevation)

            # Extract contour points
            points = self.extract_contour_points(img)

            # Calculate view metrics
            view_data = {
                'azimuth': azimuth,
                'elevation': elevation,
                'image': img,
                'contour_points': points,
                'num_points': len(points),
                'area': cv2.countNonZero(img),
                'perimeter': cv2.arcLength(points.reshape(-1, 1, 2), True) if len(points) > 0 else 0
            }

            results['views'].append(view_data)
            results['total_points'] += len(points)

        if self.verbose:
            print(f"   ✅ Extracted {results['total_points']} total contour points")

        return results

    def create_normalized_model(
        self,
        analysis_results: Dict[str, Any],
        fuzzy_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Create normalized point cloud model using fuzzy logic to merge similar views.

        Args:
            analysis_results: Results from analyze_multi_view()
            fuzzy_threshold: Similarity threshold for merging (0-1)

        Returns:
            Normalized model dictionary
        """
        if self.verbose:
            print(f"\n🧠 Creating normalized model (fuzzy threshold: {fuzzy_threshold})")

        views = analysis_results['views']

        # Find most representative views (largest area)
        view_areas = [v['area'] for v in views]
        max_area = max(view_areas)

        # Select views with area > threshold of max
        representative_views = []
        for view in views:
            area_ratio = view['area'] / max_area if max_area > 0 else 0
            if area_ratio >= fuzzy_threshold:
                representative_views.append(view)
                if self.verbose:
                    print(f"   Selected view: azimuth={view['azimuth']}°, "
                          f"area_ratio={area_ratio:.2f}")

        # Combine points from representative views
        all_points = []
        for view in representative_views:
            if len(view['contour_points']) > 0:
                all_points.append(view['contour_points'])

        if len(all_points) > 0:
            combined_points = np.vstack(all_points)
        else:
            combined_points = np.array([])

        normalized_model = {
            'representative_views': len(representative_views),
            'total_views': len(views),
            'combined_points': combined_points,
            'num_points': len(combined_points),
            'original_mesh_info': analysis_results['mesh_info']
        }

        if self.verbose:
            print(f"   ✅ Normalized model: {len(representative_views)}/{len(views)} views, "
                  f"{len(combined_points)} points")

        return normalized_model

    def visualize_comparison(
        self,
        mesh: trimesh.Trimesh,
        analysis_results: Dict[str, Any],
        output_path: str = None
    ) -> None:
        """
        Create visualization comparing original mesh views.

        Args:
            mesh: Original mesh
            analysis_results: Results from analyze_multi_view()
            output_path: Path to save image (optional)
        """
        views = analysis_results['views']

        # Create figure with grid of views
        n_views = len(views)
        cols = 3
        rows = (n_views + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(15, 5*rows))
        axes = axes.flatten() if n_views > 1 else [axes]

        fig.suptitle('Multi-View Analysis - Baseline Comparison', fontsize=16, fontweight='bold')

        for i, view in enumerate(views):
            ax = axes[i]

            # Display binary image with contour overlay
            img_rgb = cv2.cvtColor(view['image'], cv2.COLOR_GRAY2RGB)

            # Draw contour points in red
            if len(view['contour_points']) > 0:
                for pt in view['contour_points']:
                    cv2.circle(img_rgb, tuple(pt), 3, (255, 0, 0), -1)

            ax.imshow(img_rgb)
            ax.set_title(f"View {i+1}: az={view['azimuth']}°, el={view['elevation']}°\n"
                        f"{view['num_points']} points, area={view['area']} px")
            ax.axis('off')

        # Hide unused subplots
        for i in range(n_views, len(axes)):
            axes[i].axis('off')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            if self.verbose:
                print(f"\n💾 Visualization saved: {output_path}")

        plt.close()


def main():
    """Run baseline multi-view analysis on simple_block.stl"""

    print("\n" + "="*80)
    print("BASELINE MULTI-VIEW ANALYSIS")
    print("="*80)

    # Load mesh
    mesh_path = 'tests/samples/simple_block.stl'

    if not os.path.exists(mesh_path):
        print(f"❌ Error: File not found: {mesh_path}")
        print(f"   Please run from project root directory")
        return 1

    print(f"\n📂 Loading: {mesh_path}")
    mesh = trimesh.load(mesh_path)

    print(f"\n📊 Original Mesh:")
    print(f"   Vertices: {len(mesh.vertices):,}")
    print(f"   Faces: {len(mesh.faces):,}")
    print(f"   Volume: {mesh.volume:.2f} mm³")
    print(f"   Extents: {mesh.extents}")

    # Create analyzer
    analyzer = MultiViewAnalyzer(image_size=512, verbose=True)

    # Analyze from multiple views
    results = analyzer.analyze_multi_view(mesh)

    # Create normalized model
    normalized = analyzer.create_normalized_model(results, fuzzy_threshold=0.8)

    # Summary
    print(f"\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"\nOriginal Mesh:")
    print(f"   Vertices: {len(mesh.vertices):,}")
    print(f"   Faces: {len(mesh.faces):,}")

    print(f"\nNormalized Model:")
    print(f"   Representative Views: {normalized['representative_views']}/{normalized['total_views']}")
    print(f"   Total Contour Points: {normalized['num_points']}")
    print(f"   Reduction: {(1 - normalized['num_points']/len(mesh.vertices))*100:.1f}%")

    # Create visualization
    output_dir = Path('./output/baseline')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / 'multiview_analysis.png'

    analyzer.visualize_comparison(mesh, results, str(output_path))

    print(f"\n" + "="*80)
    print("✅ BASELINE ANALYSIS COMPLETE")
    print("="*80)
    print(f"\n📁 Output saved to: {output_path}")
    print(f"\nNext steps:")
    print(f"  1. Review the visualization to see contour extraction quality")
    print(f"  2. Adjust fuzzy_threshold (0.8) to include more/fewer views")
    print(f"  3. Use contour points to fit geometric primitives")
    print(f"  4. Compare this approach vs layer-wise stacking")

    return 0


if __name__ == '__main__':
    sys.exit(main())
