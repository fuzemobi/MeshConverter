#!/usr/bin/env python3
"""
Voxelization-based mesh classification and decomposition.

Uses voxel grids and morphological operations to separate components.
"""

import trimesh
import numpy as np
from typing import Dict, Any, List, Optional
from core.decomposer import decompose_via_voxelization


class VoxelMeshClassifier:
    """Classify and decompose meshes using voxelization."""

    def __init__(
        self,
        voxel_size: float = 1.0,
        erosion_iterations: int = 0,
        min_cluster_size: int = 100
    ):
        """
        Initialize voxel classifier.

        Args:
            voxel_size: Voxel grid resolution in mm (default: 1.0)
            erosion_iterations: Number of morphological erosion iterations
            min_cluster_size: Minimum vertices per component
        """
        self.voxel_size = voxel_size
        self.erosion_iterations = erosion_iterations
        self.min_cluster_size = min_cluster_size

    def classify_mesh(
        self,
        mesh: trimesh.Trimesh,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Classify mesh using voxelization-based decomposition.

        Args:
            mesh: Input trimesh
            verbose: Print progress messages

        Returns:
            Classification result:
            {
                'shape_type': 'cylinder'|'box'|'sphere'|'complex',
                'confidence': 0-100,
                'n_components': int,
                'reasoning': str,
                'components': List[Dict],  # Component details
                'method': 'voxel'
            }
        """
        if verbose:
            print("\n🔲 Classifying with voxelization...")

        # Decompose into components
        components = decompose_via_voxelization(
            mesh,
            voxel_size=self.voxel_size,
            erosion_iterations=self.erosion_iterations
        )

        if not components:
            return {
                'shape_type': 'unknown',
                'confidence': 0,
                'n_components': 0,
                'reasoning': 'Voxelization produced no valid components',
                'components': [],
                'method': 'voxel'
            }

        # Analyze components
        n_components = len(components)

        if n_components == 1:
            # Single component - classify based on bbox_ratio
            comp = components[0]
            shape_type = comp.get('estimated_type', 'complex')
            confidence = int(comp.get('confidence', 50))
            reasoning = f"Single component detected as {shape_type}"
        else:
            # Multiple components
            shape_type = 'complex'
            confidence = 85
            types = [c.get('estimated_type', 'unknown') for c in components]
            reasoning = f"Multi-component assembly: {', '.join(types)}"

        if verbose:
            print(f"  ✅ Classification: {shape_type} ({confidence}%)")
            print(f"     Components: {n_components}")
            print(f"     Reasoning: {reasoning}")

        return {
            'shape_type': shape_type,
            'confidence': confidence,
            'n_components': n_components,
            'reasoning': reasoning,
            'components': components,
            'method': 'voxel'
        }


def classify_mesh_with_voxel(
    mesh: trimesh.Trimesh,
    voxel_size: float = 1.0,
    erosion_iterations: int = 0,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to classify mesh with voxelization.

    Args:
        mesh: Input mesh
        voxel_size: Voxel grid resolution in mm
        erosion_iterations: Number of erosion iterations
        verbose: Print progress

    Returns:
        Classification result dictionary
    """
    try:
        classifier = VoxelMeshClassifier(
            voxel_size=voxel_size,
            erosion_iterations=erosion_iterations
        )
        return classifier.classify_mesh(mesh, verbose=verbose)
    except Exception as e:
        if verbose:
            print(f"❌ Voxel classification failed: {e}")
        return {
            'shape_type': 'unknown',
            'confidence': 0,
            'n_components': 0,
            'reasoning': f'Error: {str(e)}',
            'components': [],
            'method': 'error'
        }
