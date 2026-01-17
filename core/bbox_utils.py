#!/usr/bin/env python3
"""
Bounding Box utilities for mesh analysis.

The bounding box ratio is the core metric for shape classification:
bbox_ratio = mesh_volume / bounding_box_volume

This single metric reliably distinguishes shapes because:
- Solid Box: 0.95-1.05 (fills its bounding box)
- Hollow Box: 0.15-0.40 (mostly empty inside)
- Cylinder: 0.40-0.85 (empty space around circular cross-section)
- Sphere: 0.50-0.55 (π/6 ≈ 0.524, mathematically constant)
"""

from typing import Dict, Any, Tuple
import numpy as np
import trimesh


def calculate_bbox_ratio(mesh: trimesh.Trimesh) -> float:
    """
    Calculate the ratio of mesh volume to bounding box volume.

    This is the PRIMARY metric for shape classification.

    Args:
        mesh: Input trimesh object

    Returns:
        Ratio as float (0.0 to 1.0+)

    Raises:
        ValueError: If mesh is invalid or has zero volume
    """
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("mesh must be trimesh.Trimesh instance")

    if len(mesh.vertices) < 4:
        raise ValueError("Mesh must have at least 4 vertices")

    mesh_volume = mesh.volume
    if mesh_volume <= 0:
        raise ValueError(f"Mesh has invalid volume: {mesh_volume}")

    # Get axis-aligned bounding box
    bounds = mesh.bounds  # [[min_x, min_y, min_z], [max_x, max_y, max_z]]
    bbox_extents = bounds[1] - bounds[0]
    bbox_volume = np.prod(bbox_extents)

    if bbox_volume <= 0:
        raise ValueError("Bounding box has zero or negative volume")

    ratio = mesh_volume / bbox_volume
    return float(ratio)


def calculate_oriented_bbox_ratio(mesh: trimesh.Trimesh) -> float:
    """
    Calculate bbox ratio using oriented bounding box (OBB).

    OBB is more accurate for rotated objects but slower to compute.

    Args:
        mesh: Input trimesh object

    Returns:
        Ratio as float (0.0 to 1.0+)

    Raises:
        ValueError: If mesh is invalid
    """
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("mesh must be trimesh.Trimesh instance")

    mesh_volume = mesh.volume
    if mesh_volume <= 0:
        raise ValueError(f"Mesh has invalid volume: {mesh_volume}")

    # Get oriented bounding box
    obb = mesh.bounding_box_oriented
    obb_volume = obb.volume

    if obb_volume <= 0:
        raise ValueError("OBB has zero or negative volume")

    ratio = mesh_volume / obb_volume
    return float(ratio)


def get_bbox_extents(mesh: trimesh.Trimesh) -> np.ndarray:
    """
    Get the extents of the axis-aligned bounding box.

    Args:
        mesh: Input trimesh object

    Returns:
        Array [width, depth, height] in mm
    """
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("mesh must be trimesh.Trimesh instance")

    bounds = mesh.bounds
    extents = bounds[1] - bounds[0]
    return extents


def get_obb_properties(mesh: trimesh.Trimesh) -> Dict[str, Any]:
    """
    Get oriented bounding box properties.

    Args:
        mesh: Input trimesh object

    Returns:
        Dict with keys: center, extents, transform, volume
    """
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("mesh must be trimesh.Trimesh instance")

    obb = mesh.bounding_box_oriented
    return {
        'center': obb.centroid,
        'extents': obb.extents,
        'transform': obb.primitive.transform,
        'volume': obb.volume
    }


def get_mesh_stats(mesh: trimesh.Trimesh) -> Dict[str, Any]:
    """
    Calculate comprehensive mesh statistics.

    Args:
        mesh: Input trimesh object

    Returns:
        Dict with comprehensive geometry stats
    """
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("mesh must be trimesh.Trimesh instance")

    volume = mesh.volume
    bbox_ratio = calculate_bbox_ratio(mesh)
    bbox_extents = get_bbox_extents(mesh)
    obb_props = get_obb_properties(mesh)

    # Calculate aspect ratios
    sorted_extents = np.sort(bbox_extents)
    aspect_ratio_1 = sorted_extents[1] / sorted_extents[0] if sorted_extents[0] > 0 else 0
    aspect_ratio_2 = sorted_extents[2] / sorted_extents[1] if sorted_extents[1] > 0 else 0

    return {
        'volume': volume,
        'surface_area': mesh.area,
        'vertices_count': len(mesh.vertices),
        'faces_count': len(mesh.faces),
        'bbox_ratio': bbox_ratio,
        'bbox_extents': bbox_extents.tolist(),
        'bbox_volume': np.prod(bbox_extents),
        'obb_center': obb_props['center'].tolist(),
        'obb_extents': obb_props['extents'].tolist(),
        'obb_volume': obb_props['volume'],
        'aspect_ratio_1': aspect_ratio_1,
        'aspect_ratio_2': aspect_ratio_2,
        'is_watertight': mesh.is_watertight,
        'is_valid': len(mesh.vertices) > 0 and len(mesh.faces) > 0
    }
