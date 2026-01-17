#!/usr/bin/env python3
"""
Cylinder primitive implementation using PCA-based axis detection.

Detects cylinder axis using Principal Component Analysis and fits
radius and length to mesh.
"""

from typing import Dict, Any
import numpy as np
import trimesh
from sklearn.decomposition import PCA
from .base import Primitive


class CylinderPrimitive(Primitive):
    """
    Cylinder primitive using PCA-based axis detection.

    PCA reveals principal axes of variation:
    - PC1: Longest axis → cylinder axis
    - PC2, PC3: Perpendicular axes → radius directions
    """

    def __init__(self):
        """Initialize cylinder primitive."""
        super().__init__()
        self.center: np.ndarray = None
        self.axis: np.ndarray = None
        self.radius: float = None
        self.length: float = None
        self.pca_ratio: float = None

    def fit(self, mesh: trimesh.Trimesh) -> 'CylinderPrimitive':
        """
        Fit cylinder using PCA analysis.

        Args:
            mesh: Input mesh

        Returns:
            self (for method chaining)

        Raises:
            ValueError: If mesh is invalid
        """
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("mesh must be trimesh.Trimesh instance")

        if len(mesh.vertices) < 10:
            raise ValueError("Mesh must have at least 10 vertices")

        self.mesh = mesh

        vertices = mesh.vertices
        self.center = vertices.mean(axis=0)
        centered = vertices - self.center

        # Apply PCA
        pca = PCA(n_components=3)
        pca.fit(centered)

        # Extract axis (first principal component)
        self.axis = pca.components_[0]
        eigenvalues = pca.explained_variance_

        # Validate cylinder assumption (PC1 >> PC2 ≈ PC3)
        if eigenvalues[2] > 1e-6:
            self.pca_ratio = eigenvalues[1] / eigenvalues[2]
        else:
            self.pca_ratio = 1.0

        # Project vertices onto principal axes
        projected = pca.transform(centered)

        # Calculate length (range along axis)
        self.length = projected[:, 0].max() - projected[:, 0].min()

        # Calculate radius (distance from axis, use median for robustness)
        perpendicular_distances = np.sqrt(projected[:, 1]**2 + projected[:, 2]**2)
        self.radius = np.median(perpendicular_distances)

        self.fitted = True

        is_valid_cylinder = 0.8 <= self.pca_ratio <= 1.2
        validity_marker = "✓" if is_valid_cylinder else "⚠"

        print(f"✅ Cylinder fitted:")
        print(f"   Center: [{self.center[0]:.2f}, {self.center[1]:.2f}, {self.center[2]:.2f}]")
        print(f"   Axis: [{self.axis[0]:.3f}, {self.axis[1]:.3f}, {self.axis[2]:.3f}]")
        print(f"   Radius: {self.radius:.2f} mm")
        print(f"   Length: {self.length:.2f} mm")
        print(f"   PCA Ratio: {self.pca_ratio:.3f} {validity_marker}")

        return self

    def generate_mesh(self, resolution: int = 32) -> trimesh.Trimesh:
        """
        Generate a clean cylinder mesh.

        Args:
            resolution: Number of segments around cylinder

        Returns:
            Cylinder mesh
        """
        if not self.fitted:
            raise RuntimeError("Primitive not fitted yet")

        # Create cylinder along Z-axis at origin
        cylinder = trimesh.creation.cylinder(
            radius=self.radius,
            height=self.length,
            sections=resolution
        )

        # Rotate to align with detected axis
        # Cylinder is initially along Z, so we need to rotate to self.axis
        z_axis = np.array([0, 0, 1])

        # Calculate rotation to align Z with self.axis
        if not np.allclose(z_axis, self.axis, atol=1e-3):
            # Rotation axis is perpendicular to both z_axis and self.axis
            rotation_axis = np.cross(z_axis, self.axis)
            rotation_axis = rotation_axis / (np.linalg.norm(rotation_axis) + 1e-6)

            # Rotation angle
            cos_angle = np.dot(z_axis, self.axis)
            cos_angle = np.clip(cos_angle, -1, 1)
            angle = np.arccos(cos_angle)

            # Apply rotation
            from scipy.spatial.transform import Rotation
            rotation = Rotation.from_rotvec(rotation_axis * angle)
            transform = rotation.as_matrix()

            # Apply to cylinder
            cylinder.apply_transform(np.vstack([np.hstack([transform, [[0], [0], [0]]]), [0, 0, 0, 1]]))

        # Translate to center
        cylinder.apply_translation(self.center)

        return cylinder

    def to_dict(self) -> Dict[str, Any]:
        """Export cylinder parameters."""
        if not self.fitted:
            raise RuntimeError("Primitive not fitted yet")

        return {
            'type': 'cylinder',
            'center': self.center.tolist(),
            'axis': self.axis.tolist(),
            'radius': float(self.radius),
            'length': float(self.length),
            'pca_ratio': float(self.pca_ratio),
            'quality_score': self.quality_score
        }

    def generate_cadquery_script(self, variable_name: str = 'cylinder') -> str:
        """
        Generate CadQuery Python script to create this cylinder.

        Args:
            variable_name: Variable name for the cylinder

        Returns:
            CadQuery Python code
        """
        if not self.fitted:
            raise RuntimeError("Primitive not fitted yet")

        cx, cy, cz = self.center[0], self.center[1], self.center[2]
        ax, ay, az = self.axis[0], self.axis[1], self.axis[2]
        radius = self.radius
        length = self.length

        script = f'''#!/usr/bin/env python3
"""
Auto-generated CadQuery script for cylinder primitive.
Generated from mesh fitting analysis.
Quality Score: {self.quality_score:.1f}/100
"""

import cadquery as cq
from cadquery import Plane
import math

# Cylinder parameters (mm)
RADIUS = {radius:.2f}
LENGTH = {length:.2f}

CENTER = ({cx:.2f}, {cy:.2f}, {cz:.2f})
AXIS = ({ax:.3f}, {ay:.3f}, {az:.3f})

# Create cylinder
{variable_name} = cq.Workplane("XY").cylinder(LENGTH, RADIUS)

# Note: Rotation to align with detected axis may be needed
# depending on the original mesh orientation

if __name__ == "__main__":
    # Display the cylinder
    show_object({variable_name})
'''
        return script
