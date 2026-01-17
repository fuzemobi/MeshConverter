#!/usr/bin/env python3
"""
Validation and quality assessment for fitted primitives.

Calculates metrics like Hausdorff distance, volume error, and quality scores.
"""

from typing import Dict, Any, Tuple
import numpy as np
import trimesh
from scipy.spatial import cKDTree


class MeshValidator:
    """Validate fitted primitives against original mesh."""

    @staticmethod
    def validate_fit(
        original_mesh: trimesh.Trimesh,
        fitted_mesh: trimesh.Trimesh,
        primitive_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate how well fitted mesh matches original.

        Args:
            original_mesh: Original input mesh
            fitted_mesh: Generated primitive mesh
            primitive_params: Optional primitive parameters

        Returns:
            Dict with validation metrics
        """
        if not isinstance(original_mesh, trimesh.Trimesh):
            raise TypeError("original_mesh must be trimesh.Trimesh")

        if not isinstance(fitted_mesh, trimesh.Trimesh):
            raise TypeError("fitted_mesh must be trimesh.Trimesh")

        # Calculate metrics
        volume_error = MeshValidator.calculate_volume_error(original_mesh, fitted_mesh)
        surface_error = MeshValidator.calculate_surface_error(original_mesh, fitted_mesh)
        hausdorff_max, hausdorff_mean = MeshValidator.calculate_hausdorff_distance(
            original_mesh, fitted_mesh
        )

        # Normalize Hausdorff to mesh size
        bounds = original_mesh.bounds
        mesh_size = np.max(bounds[1] - bounds[0])
        hausdorff_relative = hausdorff_max / (mesh_size + 1e-6) if mesh_size > 0 else 0

        # Calculate quality score
        quality_score = MeshValidator.calculate_quality_score(
            volume_error, hausdorff_relative
        )

        return {
            'volume_error_percent': float(volume_error * 100),
            'surface_error_percent': float(surface_error * 100),
            'hausdorff_max_mm': float(hausdorff_max),
            'hausdorff_mean_mm': float(hausdorff_mean),
            'hausdorff_relative': float(hausdorff_relative),
            'mesh_size_mm': float(mesh_size),
            'quality_score': float(quality_score),
            'quality_level': MeshValidator._get_quality_level(quality_score)
        }

    @staticmethod
    def calculate_volume_error(mesh1: trimesh.Trimesh, mesh2: trimesh.Trimesh) -> float:
        """
        Calculate volume error between two meshes.

        Args:
            mesh1: First mesh (reference)
            mesh2: Second mesh

        Returns:
            Error as fraction (0.0 to 1.0)
        """
        vol1 = mesh1.volume
        vol2 = mesh2.volume

        if vol1 <= 0:
            return 0.0

        error = abs(vol1 - vol2) / vol1
        return min(error, 1.0)

    @staticmethod
    def calculate_surface_error(mesh1: trimesh.Trimesh, mesh2: trimesh.Trimesh) -> float:
        """
        Calculate surface area error between two meshes.

        Args:
            mesh1: First mesh (reference)
            mesh2: Second mesh

        Returns:
            Error as fraction (0.0 to 1.0)
        """
        area1 = mesh1.area
        area2 = mesh2.area

        if area1 <= 0:
            return 0.0

        error = abs(area1 - area2) / area1
        return min(error, 1.0)

    @staticmethod
    def calculate_hausdorff_distance(
        mesh1: trimesh.Trimesh,
        mesh2: trimesh.Trimesh,
        num_samples: int = 5000
    ) -> Tuple[float, float]:
        """
        Calculate Hausdorff distance between meshes.

        Hausdorff distance = maximum deviation between surfaces

        Args:
            mesh1: First mesh
            mesh2: Second mesh
            num_samples: Number of points to sample from each mesh

        Returns:
            Tuple of (max_distance, mean_distance) in mm
        """
        # Sample points from both meshes
        try:
            points1 = mesh1.sample(num_samples)
            points2 = mesh2.sample(num_samples)
        except:
            # Fallback if sampling fails
            points1 = mesh1.vertices[::max(1, len(mesh1.vertices) // num_samples)]
            points2 = mesh2.vertices[::max(1, len(mesh2.vertices) // num_samples)]

        # Build KD-trees for fast nearest-neighbor search
        tree1 = cKDTree(points1)
        tree2 = cKDTree(points2)

        # Distance from mesh1 to mesh2
        distances_1_to_2, _ = tree2.query(points1)

        # Distance from mesh2 to mesh1
        distances_2_to_1, _ = tree1.query(points2)

        # Hausdorff = max of both directions
        max_distance = float(max(distances_1_to_2.max(), distances_2_to_1.max()))

        # Mean distance
        mean_distance = float((distances_1_to_2.mean() + distances_2_to_1.mean()) / 2)

        return max_distance, mean_distance

    @staticmethod
    def calculate_quality_score(volume_error: float, fit_error: float) -> float:
        """
        Calculate overall quality score (0-100).

        Args:
            volume_error: Volume error as fraction
            fit_error: Fit error as fraction

        Returns:
            Quality score 0-100
        """
        # Combine metrics: volume 60%, fit 40%
        score = 100 * (1.0 - 0.6 * volume_error - 0.4 * fit_error)
        score = max(0, min(100, score))
        return float(score)

    @staticmethod
    def _get_quality_level(score: float) -> str:
        """Get quality level label."""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 60:
            return "Fair"
        else:
            return "Poor"
