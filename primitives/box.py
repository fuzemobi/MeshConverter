#!/usr/bin/env python3
"""
Box primitive implementation using Oriented Bounding Box (OBB).

Fits a rectangular box to mesh data using oriented bounding box,
which correctly handles rotated boxes.
"""

from typing import Dict, Any
import numpy as np
import trimesh
from .base import Primitive


class BoxPrimitive(Primitive):
    """
    Rectangular box primitive (solid or hollow).

    Uses oriented bounding box (OBB) for best fit.
    """

    def __init__(self):
        """Initialize box primitive."""
        super().__init__()
        self.center: np.ndarray = None
        self.extents: np.ndarray = None  # [length, width, height]
        self.transform: np.ndarray = None  # 4x4 transformation
        self.is_hollow: bool = False
        self.volume_ratio: float = 1.0

    def fit(self, mesh: trimesh.Trimesh) -> 'BoxPrimitive':
        """
        Fit oriented bounding box to mesh.

        Args:
            mesh: Input mesh

        Returns:
            self (for method chaining)

        Raises:
            ValueError: If mesh is invalid
        """
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("mesh must be trimesh.Trimesh instance")

        if len(mesh.vertices) < 4:
            raise ValueError("Mesh must have at least 4 vertices")

        self.mesh = mesh

        # Get oriented bounding box
        obb = mesh.bounding_box_oriented
        self.center = obb.centroid
        self.extents = obb.extents
        self.transform = obb.primitive.transform

        # Detect hollow vs solid
        bbox_volume = obb.volume
        mesh_volume = mesh.volume
        self.volume_ratio = mesh_volume / bbox_volume if bbox_volume > 0 else 0

        # Heuristic: if volume ratio < 0.5, likely hollow
        self.is_hollow = self.volume_ratio < 0.5

        self.fitted = True

        print(f"✅ Box fitted:")
        print(f"   Center: [{self.center[0]:.2f}, {self.center[1]:.2f}, {self.center[2]:.2f}]")
        print(f"   Extents: [{self.extents[0]:.2f}, {self.extents[1]:.2f}, {self.extents[2]:.2f}] mm")
        print(f"   Volume Ratio: {self.volume_ratio:.3f}")
        print(f"   Hollow: {self.is_hollow}")

        return self

    def generate_mesh(self, resolution: int = 32) -> trimesh.Trimesh:
        """
        Generate a clean box mesh.

        Args:
            resolution: Unused for box (always generates simple 8-vertex mesh)

        Returns:
            Box mesh
        """
        if not self.fitted:
            raise RuntimeError("Primitive not fitted yet")

        # Create box at origin
        box = trimesh.creation.box(extents=self.extents)

        # Apply transform (rotation and translation)
        box.apply_transform(self.transform)

        return box

    def to_dict(self) -> Dict[str, Any]:
        """Export box parameters."""
        if not self.fitted:
            raise RuntimeError("Primitive not fitted yet")

        return {
            'type': 'box',
            'center': self.center.tolist(),
            'extents': self.extents.tolist(),
            'is_hollow': self.is_hollow,
            'volume_ratio': float(self.volume_ratio),
            'quality_score': self.quality_score
        }

    def generate_cadquery_script(self, variable_name: str = 'box') -> str:
        """
        Generate CadQuery Python script to create this box.

        Args:
            variable_name: Variable name for the box

        Returns:
            CadQuery Python code
        """
        if not self.fitted:
            raise RuntimeError("Primitive not fitted yet")

        # Extract dimensions
        length, width, height = self.extents[0], self.extents[1], self.extents[2]
        cx, cy, cz = self.center[0], self.center[1], self.center[2]

        script = f'''#!/usr/bin/env python3
"""
Auto-generated CadQuery script for box primitive.
Generated from mesh fitting analysis.
Quality Score: {self.quality_score:.1f}/100
"""

import cadquery as cq

# Box parameters (mm)
LENGTH = {length:.2f}
WIDTH = {width:.2f}
HEIGHT = {height:.2f}

CENTER_X = {cx:.2f}
CENTER_Y = {cy:.2f}
CENTER_Z = {cz:.2f}

# Create box centered at origin
{variable_name} = cq.Workplane("XY").box(LENGTH, WIDTH, HEIGHT)

# Translate to detected center (if needed)
# {variable_name} = {variable_name}.translate((CENTER_X, CENTER_Y, CENTER_Z))

if __name__ == "__main__":
    # Display the box
    show_object({variable_name})
'''
        return script
