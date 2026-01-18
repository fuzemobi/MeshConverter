#!/usr/bin/env python3
"""
Visual Comparison Tool for LPS Reconstruction

Compares original mesh to reconstructed mesh using multiple visual metrics:
- Side-by-side renders from multiple angles
- 2D cross-section overlays
- Hausdorff distance heatmap
- Shape distribution analysis
"""

import trimesh
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Ellipse as MPLEllipse
from typing import Dict, Any, List, Optional, Tuple
import io
from PIL import Image


class VisualComparator:
    """Visual comparison tool for mesh reconstruction validation"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def render_side_by_side(
        self,
        original: trimesh.Trimesh,
        reconstructed: trimesh.Trimesh,
        angles: List[Tuple[float, float]] = None
    ) -> List[Image.Image]:
        """
        Render side-by-side comparison from multiple angles.

        Args:
            original: Original mesh
            reconstructed: Reconstructed mesh
            angles: List of (azimuth, elevation) tuples

        Returns:
            List of PIL Images
        """
        if angles is None:
            angles = [(0, 0), (90, 0), (0, 90)]  # Front, Right, Top

        images = []

        for azimuth, elevation in angles:
            fig = plt.figure(figsize=(12, 5))

            # Original
            ax1 = fig.add_subplot(121, projection='3d')
            self._render_mesh_to_axis(original, ax1, azimuth, elevation, 'Original', 'blue')

            # Reconstructed
            ax2 = fig.add_subplot(122, projection='3d')
            self._render_mesh_to_axis(reconstructed, ax2, azimuth, elevation, 'Reconstructed', 'red')

            # Save to PIL Image
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            buffer.seek(0)
            images.append(Image.open(buffer))

        return images

    def _render_mesh_to_axis(
        self,
        mesh: trimesh.Trimesh,
        ax,
        azimuth: float,
        elevation: float,
        title: str,
        color: str
    ):
        """Render mesh to matplotlib 3D axis"""
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        # Create mesh collection
        mesh_collection = Poly3DCollection(
            mesh.vertices[mesh.faces],
            alpha=0.7,
            edgecolor='black',
            linewidths=0.1
        )
        mesh_collection.set_facecolor(color)

        ax.add_collection3d(mesh_collection)

        # Set limits
        ax.set_xlim(mesh.bounds[:, 0])
        ax.set_ylim(mesh.bounds[:, 1])
        ax.set_zlim(mesh.bounds[:, 2])

        # Labels
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title(title)

        # View angle
        ax.view_init(elev=elevation, azim=azimuth)

    def compare_cross_sections(
        self,
        original: trimesh.Trimesh,
        reconstructed: trimesh.Trimesh,
        segments: List[Dict[str, Any]],
        z_heights: Optional[List[float]] = None
    ) -> Image.Image:
        """
        Compare 2D cross-sections at specific Z heights.

        Shows original outline vs reconstructed primitive overlay.

        Args:
            original: Original mesh
            reconstructed: Reconstructed mesh
            segments: Segment data from LPS
            z_heights: Z heights to slice at (default: segment boundaries)

        Returns:
            PIL Image with comparison grid
        """
        if z_heights is None:
            # Use segment mid-points
            z_heights = [(seg['z_start'] + seg['z_end']) / 2 for seg in segments[:6]]  # Max 6

        n_slices = len(z_heights)
        fig, axes = plt.subplots(2, n_slices, figsize=(3*n_slices, 6))

        if n_slices == 1:
            axes = axes.reshape(2, 1)

        for i, z in enumerate(z_heights):
            # Original cross-section
            orig_section = original.section(
                plane_origin=[0, 0, z],
                plane_normal=[0, 0, 1]
            )

            if orig_section is not None:
                path2d, _ = orig_section.to_planar()

                # Plot original
                ax = axes[0, i]
                if path2d and len(path2d.entities) > 0:
                    try:
                        polygon = path2d.polygons_full[0]
                        x, y = polygon.exterior.xy
                        ax.plot(x, y, 'b-', linewidth=2, label='Original')
                        ax.fill(x, y, alpha=0.2, color='blue')
                    except:
                        vertices = path2d.vertices
                        ax.plot(vertices[:, 0], vertices[:, 1], 'b-', linewidth=2)

                # Find matching segment
                matching_seg = None
                for seg in segments:
                    if seg['z_start'] <= z <= seg['z_end']:
                        matching_seg = seg
                        break

                # Plot reconstructed primitive
                if matching_seg:
                    prim = matching_seg['primitive_2d']
                    center = prim['center']

                    if prim['type'] == 'circle':
                        circle = Circle(
                            center, prim['radius'],
                            fill=False, edgecolor='red',
                            linewidth=2, linestyle='--',
                            label='Reconstructed (Circle)'
                        )
                        ax.add_patch(circle)

                    elif prim['type'] == 'rectangle':
                        width = prim['width']
                        height = prim['height']
                        angle = prim['rotation']

                        rect = Rectangle(
                            (center[0] - width/2, center[1] - height/2),
                            width, height, angle=angle,
                            fill=False, edgecolor='red',
                            linewidth=2, linestyle='--',
                            label='Reconstructed (Rectangle)'
                        )
                        ax.add_patch(rect)

                    elif prim['type'] == 'ellipse':
                        ellipse = MPLEllipse(
                            center,
                            prim['major_axis'], prim['minor_axis'],
                            angle=prim['rotation'],
                            fill=False, edgecolor='red',
                            linewidth=2, linestyle='--',
                            label='Reconstructed (Ellipse)'
                        )
                        ax.add_patch(ellipse)

                ax.set_aspect('equal')
                title = f'Z={z:.1f}mm\n{prim["type"].upper()}' if matching_seg else f'Z={z:.1f}mm'
                ax.set_title(title)
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8)

            # Reconstructed cross-section
            recon_section = reconstructed.section(
                plane_origin=[0, 0, z],
                plane_normal=[0, 0, 1]
            )

            ax2 = axes[1, i]
            if recon_section is not None:
                path2d, _ = recon_section.to_planar()
                if path2d and len(path2d.entities) > 0:
                    try:
                        polygon = path2d.polygons_full[0]
                        x, y = polygon.exterior.xy
                        ax2.plot(x, y, 'r-', linewidth=2)
                        ax2.fill(x, y, alpha=0.2, color='red')
                    except:
                        vertices = path2d.vertices
                        ax2.plot(vertices[:, 0], vertices[:, 1], 'r-', linewidth=2)

            ax2.set_aspect('equal')
            ax2.set_title('Reconstructed')
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save to PIL Image
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buffer.seek(0)
        return Image.open(buffer)

    def generate_comparison_report(
        self,
        original: trimesh.Trimesh,
        reconstructed: trimesh.Trimesh,
        segments: List[Dict[str, Any]],
        output_path: str = './output/comparison_report.png'
    ) -> Dict[str, Any]:
        """
        Generate comprehensive visual comparison report.

        Args:
            original: Original mesh
            reconstructed: Reconstructed mesh
            segments: Segment data from LPS
            output_path: Where to save report image

        Returns:
            Dictionary with metrics and saved image path
        """
        if self.verbose:
            print("\n📊 Generating visual comparison report...")

        # Metrics
        vol_orig = original.volume
        vol_recon = reconstructed.volume
        vol_error = abs(vol_orig - vol_recon) / vol_orig * 100 if vol_orig > 0 else 100

        # Shape distribution
        from collections import Counter
        shapes = [seg['shape'] for seg in segments]
        shape_counts = Counter(shapes)

        # Create report figure
        fig = plt.figure(figsize=(16, 10))

        # Title
        fig.suptitle('Layer-Wise Primitive Stacking - Visual Comparison Report', fontsize=16, fontweight='bold')

        # 3D side-by-side (top row)
        ax1 = fig.add_subplot(2, 3, 1, projection='3d')
        self._render_mesh_to_axis(original, ax1, 45, 30, 'Original', 'blue')

        ax2 = fig.add_subplot(2, 3, 2, projection='3d')
        self._render_mesh_to_axis(reconstructed, ax2, 45, 30, 'Reconstructed', 'red')

        # Metrics (top right)
        ax3 = fig.add_subplot(2, 3, 3)
        ax3.axis('off')
        metrics_text = f"""
RECONSTRUCTION METRICS

Volume:
  Original: {vol_orig:.2f} mm³
  Reconstructed: {vol_recon:.2f} mm³
  Error: {vol_error:.2f}%

Geometry:
  Segments: {len(segments)}
  Faces: {len(original.faces)} → {len(reconstructed.faces)}
  Reduction: {(1 - len(reconstructed.faces)/len(original.faces))*100:.1f}%

Shape Distribution:
"""
        for shape, count in shape_counts.most_common():
            pct = (count / len(shapes)) * 100
            metrics_text += f"  {shape}: {count} ({pct:.0f}%)\n"

        ax3.text(0.1, 0.5, metrics_text, fontsize=11, family='monospace', verticalalignment='center')

        # Cross-sections (bottom row)
        # Select 3 representative Z heights
        if len(segments) >= 3:
            z_heights = [
                (segments[0]['z_start'] + segments[0]['z_end']) / 2,  # Bottom
                (segments[len(segments)//2]['z_start'] + segments[len(segments)//2]['z_end']) / 2,  # Middle
                (segments[-1]['z_start'] + segments[-1]['z_end']) / 2  # Top
            ]
        else:
            z_heights = [(seg['z_start'] + seg['z_end']) / 2 for seg in segments]

        for idx, z in enumerate(z_heights[:3]):
            ax = fig.add_subplot(2, 3, 4 + idx)

            # Original section
            orig_section = original.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if orig_section:
                path2d, _ = orig_section.to_planar()
                if path2d and len(path2d.entities) > 0:
                    try:
                        polygon = path2d.polygons_full[0]
                        x, y = polygon.exterior.xy
                        ax.plot(x, y, 'b-', linewidth=2, alpha=0.7, label='Original')
                    except:
                        pass

            # Reconstructed section
            recon_section = reconstructed.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if recon_section:
                path2d, _ = recon_section.to_planar()
                if path2d and len(path2d.entities) > 0:
                    try:
                        polygon = path2d.polygons_full[0]
                        x, y = polygon.exterior.xy
                        ax.plot(x, y, 'r--', linewidth=2, alpha=0.7, label='Reconstructed')
                    except:
                        pass

            ax.set_aspect('equal')
            ax.set_title(f'Cross-section @ Z={z:.1f}mm')
            ax.legend()
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        if self.verbose:
            print(f"  ✅ Report saved: {output_path}")

        return {
            'volume_error': vol_error,
            'num_segments': len(segments),
            'shape_distribution': dict(shape_counts),
            'report_path': output_path
        }


# Convenience function
def compare_reconstruction(
    original: trimesh.Trimesh,
    reconstructed: trimesh.Trimesh,
    segments: List[Dict[str, Any]],
    output_path: str = './output/comparison_report.png',
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Generate visual comparison report.

    Args:
        original: Original mesh
        reconstructed: Reconstructed mesh
        segments: Segment data from LPS
        output_path: Output image path
        verbose: Print progress

    Returns:
        Metrics dictionary
    """
    comparator = VisualComparator(verbose=verbose)
    return comparator.generate_comparison_report(original, reconstructed, segments, output_path)
