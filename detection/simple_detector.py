#!/usr/bin/env python3
"""
Simple heuristic shape detector based on bounding box ratio.

This is the PRIMARY detection method using the core metric from CLAUDE.md:
bbox_ratio = mesh_volume / bounding_box_volume
"""

from typing import Dict, Any, Tuple
import numpy as np
import trimesh
from core.bbox_utils import calculate_bbox_ratio, get_mesh_stats


class SimpleDetector:
    """Detect shape type using bbox ratio heuristic."""

    # Classification thresholds based on CLAUDE.md
    BBOX_RATIO_THRESHOLDS = {
        'solid_box': (0.90, 1.05),      # Fills bounding box
        'hollow_box': (0.15, 0.50),     # Mostly empty
        'cylinder': (0.40, 0.85),       # π/4 ≈ 0.785
        'sphere': (0.48, 0.56),         # π/6 ≈ 0.524
        'cone': (0.20, 0.35)            # π/12 ≈ 0.262
    }

    @staticmethod
    def detect(mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        Detect shape type using bbox ratio and heuristics.

        Args:
            mesh: Input mesh

        Returns:
            Dict with keys: shape_type, confidence, reason, bbox_ratio
        """
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("mesh must be trimesh.Trimesh instance")

        # Calculate key metrics
        bbox_ratio = calculate_bbox_ratio(mesh)
        stats = get_mesh_stats(mesh)

        # Use bbox ratio as primary classifier
        shape_type, confidence = SimpleDetector._classify_by_bbox_ratio(bbox_ratio)

        reason = SimpleDetector._get_reason(shape_type, bbox_ratio, stats)

        return {
            'shape_type': shape_type,
            'confidence': confidence,
            'reason': reason,
            'bbox_ratio': bbox_ratio,
            'stats': stats
        }

    @staticmethod
    def _classify_by_bbox_ratio(bbox_ratio: float) -> Tuple[str, int]:
        """
        Classify shape based on bbox ratio.

        Args:
            bbox_ratio: Volume to bbox volume ratio

        Returns:
            Tuple of (shape_type, confidence_0_to_100)
        """
        thresholds = SimpleDetector.BBOX_RATIO_THRESHOLDS

        # Check solid box first (highest threshold)
        if thresholds['solid_box'][0] <= bbox_ratio <= thresholds['solid_box'][1]:
            return 'box', 95

        # Check sphere (narrow range, high confidence)
        if thresholds['sphere'][0] <= bbox_ratio <= thresholds['sphere'][1]:
            return 'sphere', 85

        # Check cylinder (medium range)
        if thresholds['cylinder'][0] <= bbox_ratio <= thresholds['cylinder'][1]:
            return 'cylinder', 80

        # Check hollow box
        if thresholds['hollow_box'][0] <= bbox_ratio <= thresholds['hollow_box'][1]:
            return 'box', 75  # Hollow box, but still a box

        # Check cone
        if thresholds['cone'][0] <= bbox_ratio <= thresholds['cone'][1]:
            return 'cone', 70

        # Default to complex
        return 'complex', 50

    @staticmethod
    def _get_reason(shape_type: str, bbox_ratio: float, stats: Dict) -> str:
        """
        Generate human-readable reason for classification.

        Args:
            shape_type: Detected shape type
            bbox_ratio: Calculated bbox ratio
            stats: Mesh statistics

        Returns:
            Explanation string
        """
        aspect_ratio_1 = stats.get('aspect_ratio_1', 1.0)
        aspect_ratio_2 = stats.get('aspect_ratio_2', 1.0)

        reason = f"bbox_ratio={bbox_ratio:.3f}"

        if shape_type == 'box':
            reason += " → Fills bounding box"
        elif shape_type == 'cylinder':
            reason += f" → Cylindrical; aspect ratios: {aspect_ratio_1:.2f}, {aspect_ratio_2:.2f}"
        elif shape_type == 'sphere':
            reason += " → Near-spherical volume ratio"
        elif shape_type == 'cone':
            reason += " → Conical ratio"
        else:
            reason += " → Complex shape"

        return reason
