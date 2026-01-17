#!/usr/bin/env python3
"""
Mesh loading, validation, and cleaning utilities.

Handles loading STL files, validating geometry, and preparing
meshes for shape analysis and fitting.
"""

from typing import Dict, Any, Tuple
from pathlib import Path
import trimesh
import numpy as np


class MeshLoader:
    """Load and validate STL meshes for processing."""

    @staticmethod
    def load(filepath: str, repair: bool = True) -> Dict[str, Any]:
        """
        Load an STL file and validate/repair if needed.

        Args:
            filepath: Path to STL file
            repair: Whether to automatically repair mesh issues

        Returns:
            Dict with keys: mesh, filepath, stats

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be loaded as valid mesh
        """
        filepath_obj = Path(filepath)

        if not filepath_obj.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        if filepath_obj.suffix.lower() != '.stl':
            raise ValueError(f"Expected .stl file, got: {filepath_obj.suffix}")

        try:
            mesh = trimesh.load(filepath)
        except Exception as e:
            raise ValueError(f"Failed to load STL file: {e}")

        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError("Loaded file is not a valid mesh")

        if len(mesh.vertices) == 0:
            raise ValueError("Mesh has no vertices")

        # Repair if requested
        if repair:
            MeshLoader.repair_mesh(mesh)

        # Validate
        if mesh.volume <= 0:
            raise ValueError(f"Mesh has invalid volume: {mesh.volume}")

        return {
            'mesh': mesh,
            'filepath': str(filepath),
            'filename': filepath_obj.name
        }

    @staticmethod
    def repair_mesh(mesh: trimesh.Trimesh) -> None:
        """
        Repair common mesh issues in-place.

        Issues fixed:
        - Duplicate vertices
        - Degenerate faces (zero area)
        - Non-manifold edges
        - Incorrect normals

        Args:
            mesh: Mesh to repair (modified in-place)
        """
        # Fix duplicate vertices
        mesh.merge_vertices()

        # Remove degenerate faces (zero area)
        if hasattr(mesh, 'remove_degenerate_faces'):
            mesh.remove_degenerate_faces()

        # Fix normals (ensure consistent)
        mesh.fix_normals()

        # Remove unreferenced vertices
        mesh.remove_unreferenced_vertices()

    @staticmethod
    def validate_mesh(mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        Validate mesh and return diagnostics.

        Args:
            mesh: Mesh to validate

        Returns:
            Dict with validation results
        """
        return {
            'is_valid': len(mesh.vertices) > 0 and len(mesh.faces) > 0,
            'is_watertight': mesh.is_watertight,
            'volume': mesh.volume,
            'surface_area': mesh.area,
            'vertices_count': len(mesh.vertices),
            'faces_count': len(mesh.faces),
            'has_duplicate_faces': len(mesh.duplicate_faces()) > 0 if hasattr(mesh, 'duplicate_faces') else False
        }

    @staticmethod
    def get_center(mesh: trimesh.Trimesh) -> np.ndarray:
        """
        Get centroid of mesh.

        Args:
            mesh: Input mesh

        Returns:
            [x, y, z] centroid coordinates
        """
        return mesh.centroid

    @staticmethod
    def get_bounds(mesh: trimesh.Trimesh) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get minimum and maximum bounds of mesh.

        Args:
            mesh: Input mesh

        Returns:
            Tuple of (min_point, max_point)
        """
        return mesh.bounds[0], mesh.bounds[1]
