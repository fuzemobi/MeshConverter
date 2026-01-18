#!/usr/bin/env python3
"""
Cone primitive using PCA and apex detection.

Fits a cone to mesh data by detecting axis, apex, base, and angle.
"""

import trimesh
import numpy as np
from typing import Optional, Tuple
from .base import Primitive


class ConePrimitive(Primitive):
    """
    Cone primitive fitted to mesh.

    Uses PCA for axis detection and geometric analysis for apex/base.
    """

    def __init__(self):
        super().__init__()
        self.apex: Optional[np.ndarray] = None
        self.base_center: Optional[np.ndarray] = None
        self.axis: Optional[np.ndarray] = None
        self.base_radius: Optional[float] = None
        self.height: Optional[float] = None
        self.apex_angle: Optional[float] = None  # Half-angle in degrees

    def fit(self, mesh: trimesh.Trimesh) -> 'ConePrimitive':
        """
        Fit cone to mesh.

        Args:
            mesh: Input trimesh

        Returns:
            self (for method chaining)
        """
        from sklearn.decomposition import PCA

        vertices = mesh.vertices
        center = vertices.mean(axis=0)

        # PCA to find principal axis
        pca = PCA(n_components=3)
        pca.fit(vertices - center)

        # Assume first component is cone axis
        axis = pca.components_[0]

        # Project vertices onto axis
        centered = vertices - center
        projections = centered @ axis

        # Find apex (minimum projection) and base (maximum projection)
        min_proj_idx = projections.argmin()
        max_proj_idx = projections.argmax()

        apex_candidate = vertices[min_proj_idx]
        base_candidate = vertices[max_proj_idx]

        # Height is distance along axis
        height = projections.max() - projections.min()

        # Base center is the point with maximum projection
        base_center = center + axis * projections.max()

        # Base radius: average distance from base_center to vertices near the base
        # Select vertices in the top 10% of projections
        base_threshold = projections.max() - 0.1 * height
        base_vertices = vertices[projections > base_threshold]

        if len(base_vertices) > 0:
            # Calculate distances from base_center perpendicular to axis
            base_vecs = base_vertices - base_center
            perp_distances = np.linalg.norm(base_vecs - (base_vecs @ axis)[:, None] * axis, axis=1)
            base_radius = np.median(perp_distances)
        else:
            base_radius = 10.0  # Default fallback

        # Apex is opposite end
        apex = center + axis * projections.min()

        # Calculate apex angle
        if height > 0 and base_radius > 0:
            apex_angle = np.degrees(np.arctan(base_radius / height))
        else:
            apex_angle = 45.0  # Default

        self.apex = apex
        self.base_center = base_center
        self.axis = axis
        self.base_radius = base_radius
        self.height = height
        self.apex_angle = apex_angle

        # Calculate quality
        self._calculate_quality(mesh)

        return self

    def _calculate_quality(self, original_mesh: trimesh.Trimesh):
        """Calculate fit quality."""
        fitted_mesh = self.generate_mesh()

        original_vol = original_mesh.volume
        fitted_vol = fitted_mesh.volume

        self.volume_error = abs(fitted_vol - original_vol) / original_vol if original_vol > 0 else 1.0
        self.quality_score = int(100 * (1 - self.volume_error))

    def generate_mesh(self, segments: int = 32) -> trimesh.Trimesh:
        """
        Generate cone mesh.

        Args:
            segments: Number of segments around circumference

        Returns:
            Cone trimesh
        """
        # Create cone using trimesh
        cone = trimesh.creation.cone(
            radius=self.base_radius,
            height=self.height,
            segments=segments
        )

        # Cone is created along Z-axis, need to align to our axis
        # Calculate rotation to align [0, 0, 1] with self.axis
        z_axis = np.array([0, 0, 1])

        # Rotation axis is cross product
        rotation_axis = np.cross(z_axis, self.axis)
        rotation_axis_norm = np.linalg.norm(rotation_axis)

        if rotation_axis_norm > 1e-6:  # Not parallel
            rotation_axis = rotation_axis / rotation_axis_norm

            # Rotation angle
            cos_angle = np.dot(z_axis, self.axis)
            angle = np.arccos(np.clip(cos_angle, -1, 1))

            # Apply rotation
            rotation_matrix = trimesh.transformations.rotation_matrix(
                angle, rotation_axis
            )
            cone.apply_transform(rotation_matrix)

        # Translate to correct position
        # Cone is centered at origin, apex at z=0, base at z=height
        # We want apex at self.apex
        cone.apply_translation(self.apex - cone.bounds[0])

        return cone

    def to_dict(self) -> dict:
        """Export parameters as dictionary."""
        return {
            'type': 'cone',
            'apex': self.apex.tolist() if self.apex is not None else None,
            'base_center': self.base_center.tolist() if self.base_center is not None else None,
            'axis': self.axis.tolist() if self.axis is not None else None,
            'base_radius': float(self.base_radius) if self.base_radius is not None else None,
            'height': float(self.height) if self.height is not None else None,
            'apex_angle': float(self.apex_angle) if self.apex_angle is not None else None,
            'quality_score': self.quality_score,
            'volume_error': float(self.volume_error) if hasattr(self, 'volume_error') else None
        }

    def __repr__(self) -> str:
        if self.base_radius is None or self.height is None:
            return "ConePrimitive(not fitted)"
        return f"ConePrimitive(radius={self.base_radius:.2f}mm, height={self.height:.2f}mm, angle={self.apex_angle:.1f}°)"
