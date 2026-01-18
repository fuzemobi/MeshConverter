#!/usr/bin/env python3
"""
Voxelization-based mesh classification and decomposition.

Uses voxel grids and morphological operations to separate components.
"""

import trimesh
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.decomposer import decompose_via_voxelization
from detection.simple_detector import SimpleDetector
from scipy import ndimage


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
                'component_meshes': List[trimesh.Trimesh],  # Individual meshes
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
                'component_meshes': [],
                'method': 'voxel'
            }

        # Extract individual meshes and classify each
        n_components = len(components)
        component_meshes = [comp['mesh'] for comp in components]

        # Classify each component independently
        detector = SimpleDetector()
        component_classifications = []
        
        for i, comp_mesh in enumerate(component_meshes):
            try:
                # Classify individual component
                classification = detector.classify(comp_mesh, verbose=False)
                component_classifications.append(classification)
                
                if verbose:
                    comp_type = classification.get('shape_type', 'unknown')
                    conf = classification.get('confidence', 0)
                    print(f"  Component {i+1}: {comp_type} ({conf}%)")
            except Exception as e:
                if verbose:
                    print(f"  Component {i+1}: Classification error - {e}")
                component_classifications.append({'shape_type': 'unknown', 'confidence': 0})

        # Determine overall shape type
        if n_components == 1:
            # Single component - use its classification
            comp = components[0]
            shape_type = component_classifications[0].get('shape_type', 'complex')
            confidence = component_classifications[0].get('confidence', 50)
            reasoning = f"Single voxelized component: {shape_type}"
        else:
            # Multiple components
            shape_type = 'assembly'
            confidence = 85
            types = [c.get('shape_type', 'unknown') for c in component_classifications]
            type_counts = {}
            for t in types:
                type_counts[t] = type_counts.get(t, 0) + 1
            type_summary = ', '.join([f"{count}× {shape}" for shape, count in sorted(type_counts.items())])
            reasoning = f"Multi-component assembly ({n_components} parts): {type_summary}"

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
            'component_meshes': component_meshes,
            'component_classifications': component_classifications,
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
