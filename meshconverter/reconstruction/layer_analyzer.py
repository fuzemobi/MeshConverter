#!/usr/bin/env python3
"""
Layer-by-layer mesh reconstruction for axis-aligned structures.

This module implements your "line-by-line" reconstruction idea:
- Slice mesh horizontally at regular intervals
- Analyze each slice as 2D contours
- Extract bounding boxes from each layer
- Reconstruct clean 3D boxes from layer analysis
"""

import trimesh
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from scipy.spatial import ConvexHull
from scipy.ndimage import label as ndimage_label
from PIL import Image
import io


class LayerAnalyzer:
    """Analyze and reconstruct meshes layer-by-layer."""

    def __init__(self,
                 layer_height: float = 1.0,
                 min_area_threshold: float = 10.0):
        """
        Initialize layer analyzer.

        Args:
            layer_height: Height of each layer (mm) - default 1.0
            min_area_threshold: Minimum area for valid layer region (mm²)
        """
        self.layer_height = layer_height
        self.min_area_threshold = min_area_threshold

    def analyze_layers(self,
                      mesh: trimesh.Trimesh,
                      verbose: bool = True) -> Dict[str, Any]:
        """
        Analyze mesh by slicing it into layers.

        Args:
            mesh: Input trimesh
            verbose: Print progress

        Returns:
            {
                'n_layers': int,
                'detected_boxes': List[Dict],  # Reconstructed boxes
                'confidence': int,
                'reasoning': str
            }
        """
        if verbose:
            print("\n📋 Analyzing mesh by layers...")

        bounds = mesh.bounds
        z_min, z_max = bounds[0, 2], bounds[1, 2]
        z_range = z_max - z_min

        # Generate layer heights
        n_layers = int(np.ceil(z_range / self.layer_height))
        layer_z_values = np.linspace(z_min, z_max, n_layers)

        if verbose:
            print(f"  Z range: {z_min:.2f} to {z_max:.2f} mm ({z_range:.2f} mm)")
            print(f"  Layers: {n_layers} (height {self.layer_height}mm each)")

        # Slice mesh at each layer
        layer_data = []
        for i, z in enumerate(layer_z_values):
            # Get cross-section at this Z height
            section = mesh.section(
                plane_origin=[0, 0, z],
                plane_normal=[0, 0, 1]
            )

            if section is None or len(section.vertices) == 0:
                continue

            # Analyze this layer (may return multiple regions)
            layer_regions = self._analyze_layer(section, z, i)
            if layer_regions:
                layer_data.extend(layer_regions)  # Add all regions from this layer

        if verbose:
            print(f"  Valid layer regions: {len(layer_data)}")

        # Group layers into boxes
        boxes = self._group_layers_into_boxes(layer_data, verbose=verbose)

        if verbose:
            print(f"  ✅ Detected {len(boxes)} boxes from layer analysis")

        confidence = 90 if len(boxes) > 1 else 70
        reasoning = f"Layer analysis detected {len(boxes)} distinct boxes"

        return {
            'n_layers': n_layers,
            'valid_layers': len(layer_data),
            'detected_boxes': boxes,
            'confidence': confidence,
            'reasoning': reasoning,
            'method': 'layer-slicing'
        }

    def _analyze_layer(self, section: trimesh.Path3D, z: float, layer_id: int) -> Optional[List[Dict]]:
        """
        Analyze a single layer (2D cross-section) and detect separate regions.

        Uses 2D clustering to find separate blocks within a single layer.

        Args:
            section: Cross-section mesh (Path3D)
            z: Z coordinate of this layer
            layer_id: Layer index

        Returns:
            List of layer data dicts (one per detected region) or None if invalid
        """
        try:
            # Convert to 2D (drop Z)
            points_2d = section.vertices[:, :2]

            if len(points_2d) < 4:
                return None

            # Use 2D DBSCAN to cluster separate regions in this layer
            try:
                from sklearn.cluster import DBSCAN
                
                # Cluster points in 2D
                clustering = DBSCAN(eps=3.0, min_samples=5).fit(points_2d)
                labels = clustering.labels_

                # Analyze each cluster
                layer_regions = []
                for cluster_id in set(labels):
                    if cluster_id == -1:  # Noise points
                        continue

                    cluster_points = points_2d[labels == cluster_id]

                    # Get bounding box
                    x_min, y_min = cluster_points.min(axis=0)
                    x_max, y_max = cluster_points.max(axis=0)

                    width = x_max - x_min
                    height = y_max - y_min
                    area = width * height

                    if area < self.min_area_threshold:
                        continue

                    layer_regions.append({
                        'z': z,
                        'layer_id': layer_id,
                        'cluster_id': cluster_id,
                        'bounds': np.array([[x_min, y_min], [x_max, y_max]]),
                        'width': width,
                        'height': height,
                        'area': area,
                        'center': np.array([(x_min + x_max) / 2, (y_min + y_max) / 2])
                    })

                return layer_regions if layer_regions else None

            except ImportError:
                # Fallback if sklearn unavailable: simple bounding box
                x_min, y_min = points_2d.min(axis=0)
                x_max, y_max = points_2d.max(axis=0)

                width = x_max - x_min
                height = y_max - y_min
                area = width * height

                if area < self.min_area_threshold:
                    return None

                return [{
                    'z': z,
                    'layer_id': layer_id,
                    'cluster_id': 0,
                    'bounds': np.array([[x_min, y_min], [x_max, y_max]]),
                    'width': width,
                    'height': height,
                    'area': area,
                    'center': np.array([(x_min + x_max) / 2, (y_min + y_max) / 2])
                }]

        except Exception:
            return None

    def _group_layers_into_boxes(self,
                                 layer_data: List[Dict],
                                 verbose: bool = False) -> List[Dict]:
        """
        Group consecutive layers with similar bounding boxes into 3D boxes.

        Uses more aggressive separation strategy to detect individual blocks.

        Args:
            layer_data: List of layer analysis results
            verbose: Print progress

        Returns:
            List of reconstructed boxes
        """
        if not layer_data:
            return []

        boxes = []
        current_group = [layer_data[0]]

        for i in range(1, len(layer_data)):
            layer = layer_data[i]
            prev_layer = layer_data[i - 1]

            # Check if layers belong to same box (similar bounding box)
            bbox_similarity = self._compute_bbox_similarity(
                prev_layer['bounds'],
                layer['bounds']
            )

            # More aggressive: require high similarity to group
            # Also check for significant jumps in box position/size
            position_change = np.linalg.norm(layer['center'] - prev_layer['center'])
            size_change = abs(layer['area'] - prev_layer['area']) / (prev_layer['area'] + 1e-6)

            # Layer continuity check (should be close in Z)
            z_gap = layer['z'] - prev_layer['z']
            layer_continuous = z_gap <= self.layer_height * 2.0

            # Stricter grouping: high similarity AND small position/size changes
            should_group = (
                bbox_similarity > 0.8 and
                layer_continuous and
                position_change < 5.0 and
                size_change < 0.15
            )

            if should_group:
                # Same box, add to group
                current_group.append(layer)
            else:
                # Different box, finalize current group if large enough
                if len(current_group) > 2:  # Need at least 3 layers for a box
                    box = self._finalize_box(current_group)
                    if box['dimensions'].sum() > 10:  # Minimum size check
                        boxes.append(box)

                current_group = [layer]

        # Finalize last group
        if len(current_group) > 2:
            box = self._finalize_box(current_group)
            if box['dimensions'].sum() > 10:
                boxes.append(box)

        return boxes

    def _compute_bbox_similarity(self,
                                bbox1: np.ndarray,
                                bbox2: np.ndarray) -> float:
        """
        Compute similarity between two 2D bounding boxes.

        Args:
            bbox1: [[x_min, y_min], [x_max, y_max]]
            bbox2: [[x_min, y_min], [x_max, y_max]]

        Returns:
            Similarity score 0-1
        """
        # Calculate IoU (Intersection over Union)
        x_min1, y_min1 = bbox1[0]
        x_max1, y_max1 = bbox1[1]
        x_min2, y_min2 = bbox2[0]
        x_max2, y_max2 = bbox2[1]

        # Intersection
        x_inter_min = max(x_min1, x_min2)
        x_inter_max = min(x_max1, x_max2)
        y_inter_min = max(y_min1, y_min2)
        y_inter_max = min(y_max1, y_max2)

        if x_inter_max < x_inter_min or y_inter_max < y_inter_min:
            return 0.0

        inter_area = (x_inter_max - x_inter_min) * (y_inter_max - y_inter_min)

        # Union
        area1 = (x_max1 - x_min1) * (y_max1 - y_min1)
        area2 = (x_max2 - x_min2) * (y_max2 - y_min2)
        union_area = area1 + area2 - inter_area

        iou = inter_area / union_area if union_area > 0 else 0.0
        return iou

    def _finalize_box(self, layer_group: List[Dict]) -> Dict:
        """
        Reconstruct a 3D box from a group of layers.

        Args:
            layer_group: List of layer analysis dicts

        Returns:
            Reconstructed box parameters
        """
        # Average the bounding box across layers
        all_bounds = np.array([layer['bounds'] for layer in layer_group])
        avg_bounds = np.mean(all_bounds, axis=0)

        # Z range
        z_values = [layer['z'] for layer in layer_group]
        z_min = min(z_values)
        z_max = max(z_values)
        z_height = z_max - z_min

        # XY dimensions
        x_min, y_min = avg_bounds[0]
        x_max, y_max = avg_bounds[1]
        x_width = x_max - x_min
        y_width = y_max - y_min

        # Center
        center = np.array([
            (x_min + x_max) / 2,
            (y_min + y_max) / 2,
            (z_min + z_max) / 2
        ])

        return {
            'center': center,
            'dimensions': np.array([x_width, y_width, z_height]),
            'z_range': [z_min, z_max],
            'n_layers': len(layer_group),
            'shape_type': 'box',
            'confidence': 95
        }


def analyze_mesh_layers(mesh: trimesh.Trimesh,
                       layer_height: float = 1.0,
                       verbose: bool = True) -> Dict[str, Any]:
    """
    Convenience function to analyze mesh by layers.

    Args:
        mesh: Input trimesh
        layer_height: Height of each layer (mm)
        verbose: Print progress

    Returns:
        Analysis result with detected boxes
    """
    try:
        analyzer = LayerAnalyzer(layer_height=layer_height)
        return analyzer.analyze_layers(mesh, verbose=verbose)
    except Exception as e:
        if verbose:
            print(f"❌ Layer analysis failed: {e}")
        return {
            'n_layers': 0,
            'valid_layers': 0,
            'detected_boxes': [],
            'confidence': 0,
            'reasoning': f'Error: {str(e)}',
            'method': 'error'
        }
