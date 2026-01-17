#!/usr/bin/env python3
"""
Mesh normalization utilities.

Normalizes meshes to canonical coordinate space for consistent analysis
and fitting. Supports isotropic and anisotropic scaling.
"""

from typing import Dict, Any, Tuple
import numpy as np
import trimesh


class MeshNormalizer:
    """Normalize meshes to canonical space."""

    def __init__(self):
        """Initialize normalizer."""
        self.original_centroid: np.ndarray = None
        self.original_scale: float = None
        self.scale_vector: np.ndarray = None

    def normalize(
        self,
        mesh: trimesh.Trimesh,
        center: bool = True,
        scale: bool = True,
        target_scale: float = 100.0,
        isotropic: bool = True
    ) -> trimesh.Trimesh:
        """
        Normalize mesh to canonical space.

        Args:
            mesh: Input mesh
            center: Whether to center at origin
            scale: Whether to scale to target size
            target_scale: Target size after scaling
            isotropic: If True, scale uniformly; if False, scale per-axis

        Returns:
            Normalized mesh copy
        """
        normalized = mesh.copy()

        if center:
            self.original_centroid = normalized.centroid.copy()
            normalized.apply_translation(-self.original_centroid)

        if scale:
            bounds = normalized.bounds
            current_extents = bounds[1] - bounds[0]

            if isotropic:
                current_scale = np.max(current_extents)
                if current_scale > 0:
                    self.original_scale = current_scale
                    scale_factor = target_scale / current_scale
                    self.scale_vector = np.array([scale_factor, scale_factor, scale_factor])
                    normalized.apply_scale(scale_factor)
            else:
                self.scale_vector = np.ones(3)
                for i, extent in enumerate(current_extents):
                    if extent > 0:
                        s = target_scale / extent
                        self.scale_vector[i] = s

                # Apply non-uniform scale
                scale_matrix = np.diag([self.scale_vector[0], self.scale_vector[1], self.scale_vector[2], 1.0])
                normalized.apply_transform(scale_matrix)

        return normalized

    def denormalize(
        self,
        mesh: trimesh.Trimesh
    ) -> trimesh.Trimesh:
        """
        Reverse normalization to original space.

        Args:
            mesh: Normalized mesh

        Returns:
            Mesh in original coordinate space
        """
        denormalized = mesh.copy()

        # Reverse scale
        if self.scale_vector is not None:
            inv_scale = 1.0 / self.scale_vector
            scale_matrix = np.diag([inv_scale[0], inv_scale[1], inv_scale[2], 1.0])
            denormalized.apply_transform(scale_matrix)

        # Reverse translation
        if self.original_centroid is not None:
            denormalized.apply_translation(self.original_centroid)

        return denormalized

    @staticmethod
    def center_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        """
        Center mesh at origin.

        Args:
            mesh: Input mesh

        Returns:
            Centered mesh copy
        """
        centered = mesh.copy()
        centroid = mesh.centroid
        centered.apply_translation(-centroid)
        return centered

    @staticmethod
    def scale_mesh_isotropic(
        mesh: trimesh.Trimesh,
        target_scale: float = 100.0
    ) -> Tuple[trimesh.Trimesh, float]:
        """
        Scale mesh uniformly to target size.

        Args:
            mesh: Input mesh
            target_scale: Target size (uses max dimension)

        Returns:
            Tuple of (scaled_mesh, scale_factor)
        """
        scaled = mesh.copy()
        bounds = scaled.bounds
        current_scale = np.max(bounds[1] - bounds[0])

        if current_scale > 0:
            scale_factor = target_scale / current_scale
            scaled.apply_scale(scale_factor)
        else:
            scale_factor = 1.0

        return scaled, scale_factor

    @staticmethod
    def get_normalization_params(mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        Get parameters needed for normalization.

        Args:
            mesh: Input mesh

        Returns:
            Dict with normalization parameters
        """
        bounds = mesh.bounds
        extents = bounds[1] - bounds[0]
        centroid = mesh.centroid

        return {
            'centroid': centroid.tolist(),
            'bounds_min': bounds[0].tolist(),
            'bounds_max': bounds[1].tolist(),
            'extents': extents.tolist(),
            'max_extent': float(np.max(extents)),
            'volume': float(mesh.volume)
        }
