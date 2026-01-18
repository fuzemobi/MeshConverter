#!/usr/bin/env python3
"""
Sphere primitive using least-squares fitting.

Fits a sphere to point cloud data using algebraic method.
"""

import trimesh
import numpy as np
from typing import Optional
from .base import Primitive


class SpherePrimitive(Primitive):
    """
    Sphere primitive fitted to mesh.

    Uses least-squares fitting to find optimal sphere parameters.
    """

    def __init__(self):
        super().__init__()
        self.center: Optional[np.ndarray] = None
        self.radius: Optional[float] = None

    def fit(self, mesh: trimesh.Trimesh) -> 'SpherePrimitive':
        """
        Fit sphere to mesh using least-squares method.

        Args:
            mesh: Input trimesh

        Returns:
            self (for method chaining)
        """
        vertices = mesh.vertices

        # Initial guess: centroid and average distance
        center_guess = vertices.mean(axis=0)
        distances = np.linalg.norm(vertices - center_guess, axis=1)
        radius_guess = distances.mean()

        # Least-squares fitting
        # Minimize: sum((||p - c|| - r)^2)
        # Using algebraic method for speed

        # Set up linear system
        # For each point p: ||p - c||^2 = r^2
        # Expand: p·p - 2p·c + c·c = r^2
        # Rearrange: 2p·c - (p·p) = c·c - r^2

        A = 2 * vertices
        b = (vertices ** 2).sum(axis=1)

        # Solve for center (overdetermined system)
        try:
            from scipy.linalg import lstsq
            center, residuals, rank, s = lstsq(A, b)
        except ImportError:
            # Fallback to numpy
            center, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)

        # Calculate radius from fitted center
        distances = np.linalg.norm(vertices - center, axis=1)
        radius = distances.mean()

        self.center = center
        self.radius = radius

        # Calculate quality metrics
        self._calculate_quality(mesh)

        return self

    def _calculate_quality(self, original_mesh: trimesh.Trimesh):
        """Calculate fit quality metrics."""
        # Generate sphere mesh for comparison
        fitted_mesh = self.generate_mesh()

        # Volume error
        original_vol = original_mesh.volume
        fitted_vol = fitted_mesh.volume
        self.volume_error = abs(fitted_vol - original_vol) / original_vol if original_vol > 0 else 1.0

        # Surface error (RMS distance from points to sphere surface)
        vertices = original_mesh.vertices
        distances = np.linalg.norm(vertices - self.center, axis=1)
        surface_errors = np.abs(distances - self.radius)
        self.surface_rms_error = np.sqrt((surface_errors ** 2).mean())

        # Quality score
        self.quality_score = int(100 * (1 - self.volume_error))

    def generate_mesh(self, subdivisions: int = 3) -> trimesh.Trimesh:
        """
        Generate sphere mesh.

        Args:
            subdivisions: Number of subdivisions (higher = smoother, default: 3)

        Returns:
            Sphere trimesh
        """
        # Create sphere
        sphere = trimesh.creation.icosphere(subdivisions=subdivisions, radius=self.radius)

        # Translate to center
        sphere.apply_translation(self.center - sphere.centroid)

        return sphere

    def to_dict(self) -> dict:
        """Export parameters as dictionary."""
        return {
            'type': 'sphere',
            'center': self.center.tolist() if self.center is not None else None,
            'radius': float(self.radius) if self.radius is not None else None,
            'quality_score': self.quality_score,
            'volume_error': float(self.volume_error) if hasattr(self, 'volume_error') else None
        }

    def __repr__(self) -> str:
        if self.center is None or self.radius is None:
            return "SpherePrimitive(not fitted)"
        return f"SpherePrimitive(center={self.center}, radius={self.radius:.2f}mm)"
