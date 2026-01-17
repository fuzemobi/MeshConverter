#!/usr/bin/env python3
"""
Abstract base class for geometric primitives.

All primitive types (Box, Cylinder, Sphere, Cone) inherit from this class.
Provides common interface for fitting, quality evaluation, and export.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
import trimesh


class Primitive(ABC):
    """Abstract base class for geometric primitives."""

    def __init__(self):
        """Initialize primitive."""
        self.quality_score: float = 0.0
        self.fitted: bool = False
        self.mesh: trimesh.Trimesh = None

    @abstractmethod
    def fit(self, mesh: trimesh.Trimesh) -> 'Primitive':
        """
        Fit primitive to mesh.

        Args:
            mesh: Input mesh to fit to

        Returns:
            self (for method chaining)
        """
        pass

    @abstractmethod
    def generate_mesh(self, resolution: int = 32) -> trimesh.Trimesh:
        """
        Generate a clean mesh for the primitive.

        Args:
            resolution: Detail level (higher = finer mesh)

        Returns:
            Generated mesh
        """
        pass

    def calculate_quality_score(self, original_mesh: trimesh.Trimesh) -> float:
        """
        Calculate fit quality using Hausdorff distance and volume error.

        For hollow structures, focus on shape matching rather than volume.

        Args:
            original_mesh: Original mesh to compare against

        Returns:
            Quality score 0-100
        """
        if not self.fitted or self.mesh is None:
            return 0.0

        generated = self.generate_mesh()

        # Hausdorff distance (primary metric - shape matching)
        try:
            max_dist, mean_dist = self._hausdorff_distance(original_mesh, generated)
            bounds = original_mesh.bounds
            mesh_size = np.max(bounds[1] - bounds[0])
            relative_dist = max_dist / (mesh_size + 1e-6)
            relative_dist = min(relative_dist, 1.0)  # Cap at 100%
            fit_error = relative_dist
        except:
            fit_error = 0.5

        # Volume error (secondary metric)
        original_volume = original_mesh.volume
        generated_volume = generated.volume

        # For hollow structures, allow wider tolerance on volume
        if original_volume < 1e-6:
            volume_error = 0.0  # Ignore volume for near-zero volume meshes
        else:
            volume_error = abs(original_volume - generated_volume) / (original_volume + 1e-6)
            volume_error = min(volume_error, 1.0)

        # Weight fit quality heavily (80%), volume (20%)
        self.quality_score = 100 * (1.0 - 0.8 * fit_error - 0.2 * volume_error)
        self.quality_score = max(0, min(100, self.quality_score))

        return self.quality_score

    @staticmethod
    def _hausdorff_distance(
        mesh1: trimesh.Trimesh,
        mesh2: trimesh.Trimesh,
        num_samples: int = 5000
    ) -> tuple:
        """
        Calculate Hausdorff distance between two meshes.

        Args:
            mesh1: First mesh
            mesh2: Second mesh
            num_samples: Number of points to sample

        Returns:
            Tuple of (max_distance, mean_distance)
        """
        from scipy.spatial import cKDTree

        points1 = mesh1.sample(num_samples)
        points2 = mesh2.sample(num_samples)

        tree1 = cKDTree(points1)
        tree2 = cKDTree(points2)

        distances_1_to_2 = tree2.query(points1)[0]
        distances_2_to_1 = tree1.query(points2)[0]

        max_distance = max(distances_1_to_2.max(), distances_2_to_1.max())
        mean_distance = (distances_1_to_2.mean() + distances_2_to_1.mean()) / 2

        return max_distance, mean_distance

    def to_dict(self) -> Dict[str, Any]:
        """
        Export primitive parameters as dict.

        Returns:
            Dictionary representation
        """
        return {
            'quality_score': self.quality_score,
            'fitted': self.fitted
        }

    def export_stl(self, filepath: str) -> None:
        """
        Export primitive as STL file.

        Args:
            filepath: Output file path
        """
        if not self.fitted or self.mesh is None:
            raise RuntimeError("Primitive not fitted yet")

        generated = self.generate_mesh()
        generated.export(filepath)

    def export_metadata(self) -> Dict[str, Any]:
        """
        Export metadata about the primitive.

        Returns:
            Metadata dictionary
        """
        return {
            'type': self.__class__.__name__,
            'fitted': self.fitted,
            'quality_score': self.quality_score,
            'parameters': self.to_dict()
        }
