"""
MeshConverter - Convert 3D mesh files to parametric CAD primitives.

A Python tool for analyzing STL mesh files and converting them to
parametric CAD models (CadQuery scripts, STEP files, etc.).

Supports multiple classification methods:
- Voxelization-based (default, free, local)
- GPT-4 Vision (AI-powered, requires API key)
"""

__version__ = "2.0.0"
__author__ = "MedTrackET Team"

from .classification import (
    VoxelMeshClassifier,
    GPT4VisionMeshClassifier,
    classify_mesh_with_voxel,
    classify_mesh_with_vision,
)

__all__ = [
    '__version__',
    '__author__',
    'VoxelMeshClassifier',
    'GPT4VisionMeshClassifier',
    'classify_mesh_with_voxel',
    'classify_mesh_with_vision',
]
