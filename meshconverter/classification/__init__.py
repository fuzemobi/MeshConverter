"""
Mesh classification methods for MeshConverter.

Available classifiers:
- VoxelMeshClassifier: Voxelization-based decomposition (default, free, local)
- GPT4VisionMeshClassifier: AI-powered visual classification (requires API key)
"""

from .voxel_classifier import VoxelMeshClassifier, classify_mesh_with_voxel
from .vision_classifier import GPT4VisionMeshClassifier, classify_mesh_with_vision

__all__ = [
    'VoxelMeshClassifier',
    'classify_mesh_with_voxel',
    'GPT4VisionMeshClassifier',
    'classify_mesh_with_vision',
]
