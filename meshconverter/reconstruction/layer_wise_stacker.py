#!/usr/bin/env python3
"""
Phase 4A: Layer-Wise Primitive Stacking (LPS)

Decomposes complex 3D meshes into stacks of parametric primitives by:
1. Slicing mesh into layers
2. Analyzing each layer cross-section (shape, dimensions)
3. Grouping similar layers into segments
4. Fitting 2D primitives to each segment
5. Extruding primitives to reconstruct 3D model

This mirrors the manual CAD workflow: slice → inspect → draw → extrude → combine
"""

import trimesh
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from sklearn.decomposition import PCA
from scipy.optimize import minimize
from shapely.geometry import Polygon as ShapelyPolygon
import warnings

# Suppress deprecation warnings from trimesh
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Import CV validator
try:
    from meshconverter.validation.cv_validator import CVValidator
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False


class LayerWiseStacker:
    """
    Multi-segment reconstruction via layer-wise primitive stacking.

    Decomposes complex objects (e.g., battery with cap, body, terminals)
    into stacks of different-sized primitives.
    """

    def __init__(
        self,
        layer_height: float = 0.5,
        min_segment_height: float = 2.0,
        shape_similarity_threshold: float = 0.85,
        size_similarity_threshold: float = 0.90,
        centroid_tolerance_mm: float = 2.0,
        use_cv_validation: bool = True,
        cv_confidence_threshold: float = 0.70,  # Use 0.70 for quality; lower causes issues with hollow structures
        verbose: bool = True
    ):
        """
        Initialize Layer-Wise Stacker.

        Args:
            layer_height: Distance between slices (mm)
            min_segment_height: Minimum height for a segment (mm)
            shape_similarity_threshold: Min similarity for shape matching (0-1)
            size_similarity_threshold: Min area ratio for size matching (0-1)
            centroid_tolerance_mm: Max centroid distance for alignment (mm)
            use_cv_validation: Enable CV-based validation (requires opencv)
            cv_confidence_threshold: Minimum CV confidence to use primitive (0-1)
            verbose: Print progress messages
        """
        self.layer_height = layer_height
        self.min_segment_height = min_segment_height
        self.shape_threshold = shape_similarity_threshold
        self.size_threshold = size_similarity_threshold
        self.centroid_tolerance = centroid_tolerance_mm
        self.use_cv_validation = use_cv_validation and CV_AVAILABLE
        self.cv_threshold = cv_confidence_threshold
        self.verbose = verbose

        # Initialize CV validator if enabled
        if self.use_cv_validation:
            self.cv_validator = CVValidator(verbose=False)
            if self.verbose:
                print("  ✅ CV validation enabled")
        else:
            self.cv_validator = None
            if self.verbose and use_cv_validation and not CV_AVAILABLE:
                print("  ⚠️  CV validation requested but opencv not available")

    def detect_primary_axis(self, mesh: trimesh.Trimesh) -> Tuple[np.ndarray, str]:
        """
        Detect primary axis of mesh for slicing.

        Strategy: Slice along the SHORTEST axis to maximize cross-section area.
        This gives the most representative 2D profiles.

        For a 60×40×20mm box:
        - Slicing along Z (shortest, 20mm) → 60×40mm cross-sections ✓
        - Slicing along Y (40mm) → 60×20mm cross-sections
        - Slicing along X (longest, 60mm) → 40×20mm cross-sections

        Args:
            mesh: Input mesh

        Returns:
            (axis_vector, axis_name)
        """
        # Use bounding box dimensions
        extents = mesh.extents

        # CRITICAL FIX: Use SHORTEST axis (argmin) for maximum cross-section
        min_extent_idx = extents.argmin()

        axis_names = ['X', 'Y', 'Z']
        axis_vectors = [
            np.array([1, 0, 0]),
            np.array([0, 1, 0]),
            np.array([0, 0, 1])
        ]

        return axis_vectors[min_extent_idx], axis_names[min_extent_idx]

    def slice_mesh(
        self,
        mesh: trimesh.Trimesh,
        axis: np.ndarray,
        layer_height: float
    ) -> List[Dict[str, Any]]:
        """
        Slice mesh into layers perpendicular to axis.

        Args:
            mesh: Input mesh
            axis: Slicing axis (unit vector)
            layer_height: Distance between slices

        Returns:
            List of layer dictionaries with z_height and polygon
        """
        # Project mesh bounds onto axis to get range
        vertices_proj = mesh.vertices @ axis
        z_min, z_max = vertices_proj.min(), vertices_proj.max()

        # Generate slice heights
        num_layers = int((z_max - z_min) / layer_height)
        heights = np.linspace(z_min + layer_height, z_max - layer_height, num_layers)

        layers = []

        for i, z in enumerate(heights):
            # Create slicing plane
            plane_origin = axis * z
            plane_normal = axis

            try:
                # Slice mesh
                section = mesh.section(
                    plane_origin=plane_origin,
                    plane_normal=plane_normal
                )

                if section is None:
                    continue

                # Convert to 2D (returns Path2D object)
                path2d, _ = section.to_planar()

                # Convert Path2D to Shapely Polygon
                # Path2D has entities (lines/arcs) that form closed loops
                if path2d is None or len(path2d.entities) == 0:
                    continue

                # Get discrete points from path
                # to_polygon() converts path to shapely polygon
                try:
                    polygon_2d = path2d.polygons_full[0]  # Get largest polygon
                except (IndexError, AttributeError):
                    # Fallback: manually extract vertices
                    vertices_2d = path2d.vertices
                    if len(vertices_2d) < 3:
                        continue
                    polygon_2d = ShapelyPolygon(vertices_2d)

                # Validate: non-empty, closed contour
                if polygon_2d.is_empty or not polygon_2d.is_valid:
                    continue

                layers.append({
                    'layer_id': i,
                    'z_height': float(z),
                    'polygon': polygon_2d,
                    'area': polygon_2d.area,
                    'centroid': np.array(polygon_2d.centroid.coords[0])
                })

            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️  Layer {i} @ Z={z:.1f}mm failed: {e}")
                continue

        return layers

    def fit_circle_2d(self, polygon: ShapelyPolygon) -> Dict[str, Any]:
        """
        Fit circle to 2D polygon using least-squares.

        Args:
            polygon: shapely Polygon

        Returns:
            Dictionary with type='circle', center, radius, fit_quality
        """
        # Get exterior coordinates
        coords = np.array(polygon.exterior.coords[:-1])  # Exclude duplicate last point

        # Initial guess from centroid
        center_guess = polygon.centroid.coords[0]
        distances = np.linalg.norm(coords - center_guess, axis=1)
        radius_guess = distances.mean()

        # Least-squares circle fitting
        def circle_error(params):
            cx, cy, r = params
            dists = np.sqrt((coords[:, 0] - cx)**2 + (coords[:, 1] - cy)**2)
            return ((dists - r)**2).sum()

        result = minimize(
            circle_error,
            x0=[center_guess[0], center_guess[1], radius_guess],
            method='Nelder-Mead'
        )

        cx, cy, r = result.x

        # Calculate RMS error
        dists = np.sqrt((coords[:, 0] - cx)**2 + (coords[:, 1] - cy)**2)
        rms_error = np.sqrt(((dists - r)**2).mean())

        # Fit quality: 1 - (RMS / radius)
        fit_quality = max(0, 1 - (rms_error / r)) if r > 0 else 0

        return {
            'type': 'circle',
            'center': np.array([cx, cy]),
            'radius': float(r),
            'rms_error': float(rms_error),
            'fit_quality': float(fit_quality)
        }

    def fit_rectangle_2d(self, polygon: ShapelyPolygon) -> Dict[str, Any]:
        """
        Fit oriented bounding rectangle to 2D polygon.

        Args:
            polygon: shapely Polygon

        Returns:
            Dictionary with type='rectangle', center, width, height, rotation
        """
        # Minimum rotated rectangle
        min_rect = polygon.minimum_rotated_rectangle

        # Get corners
        coords = np.array(min_rect.exterior.coords[:-1])

        # Calculate dimensions
        edge1 = coords[1] - coords[0]
        edge2 = coords[2] - coords[1]
        width = np.linalg.norm(edge1)
        height = np.linalg.norm(edge2)

        # Rotation angle (degrees)
        angle = np.degrees(np.arctan2(edge1[1], edge1[0]))

        # Fit quality: polygon_area / rectangle_area
        fit_quality = polygon.area / min_rect.area if min_rect.area > 0 else 0

        return {
            'type': 'rectangle',
            'center': np.array(polygon.centroid.coords[0]),
            'width': float(width),
            'height': float(height),
            'rotation': float(angle),
            'fit_quality': float(fit_quality),
            'rectangularity': float(fit_quality)  # Same as fit_quality for rectangles
        }

    def fit_ellipse_2d(self, polygon: ShapelyPolygon) -> Dict[str, Any]:
        """
        Fit ellipse to 2D polygon using PCA.

        Args:
            polygon: shapely Polygon

        Returns:
            Dictionary with type='ellipse', center, major_axis, minor_axis, rotation
        """
        coords = np.array(polygon.exterior.coords[:-1])
        center = polygon.centroid.coords[0]

        # PCA on centered coordinates
        centered = coords - center
        pca = PCA(n_components=2)
        pca.fit(centered)

        # Project onto principal axes
        projected = pca.transform(centered)

        # Major and minor axes (ranges along principal components)
        major_axis = projected[:, 0].max() - projected[:, 0].min()
        minor_axis = projected[:, 1].max() - projected[:, 1].min()

        # Rotation angle
        angle = np.degrees(np.arctan2(pca.components_[0, 1], pca.components_[0, 0]))

        # Fit quality (heuristic)
        # Ellipse area = π * (major/2) * (minor/2)
        ellipse_area = np.pi * (major_axis / 2) * (minor_axis / 2)
        fit_quality = min(polygon.area / ellipse_area, ellipse_area / polygon.area) if ellipse_area > 0 else 0

        return {
            'type': 'ellipse',
            'center': np.array(center),
            'major_axis': float(major_axis),
            'minor_axis': float(minor_axis),
            'rotation': float(angle),
            'fit_quality': float(fit_quality)
        }

    def calculate_shape_metrics(self, polygon: ShapelyPolygon) -> Dict[str, float]:
        """
        Calculate geometric metrics to help discriminate shapes.

        Returns:
            Dictionary with circularity, compactness, rectangularity metrics
        """
        area = polygon.area
        perimeter = polygon.length

        # Circularity = 4π * area / perimeter²
        # Perfect circle = 1.0, square ≈ 0.785, rectangle < 0.785
        circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0

        # Get minimum rotated rectangle (OBB)
        min_rect = polygon.minimum_rotated_rectangle
        rect_area = min_rect.area

        # Rectangularity = polygon_area / bounding_rect_area
        # Perfect rectangle = 1.0, circle ≈ 0.785
        rectangularity = area / rect_area if rect_area > 0 else 0

        # Aspect ratio of bounding rectangle
        coords = np.array(min_rect.exterior.coords[:-1])
        edge1 = np.linalg.norm(coords[1] - coords[0])
        edge2 = np.linalg.norm(coords[2] - coords[1])
        aspect_ratio = max(edge1, edge2) / min(edge1, edge2) if min(edge1, edge2) > 0 else 1.0

        return {
            'circularity': circularity,
            'rectangularity': rectangularity,
            'aspect_ratio': aspect_ratio
        }

    def classify_and_fit_2d(
        self,
        polygon: ShapelyPolygon,
        shape_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classify 2D polygon shape and fit best primitive.

        Uses geometric metrics to discriminate between shapes:
        - Circularity: circle=1.0, square=0.785, rectangle<0.785
        - Rectangularity: rectangle=1.0, circle=0.785
        - Aspect ratio: square=1.0, rectangle>1.2

        Args:
            polygon: shapely Polygon
            shape_hint: Optional hint ('circle', 'rectangle', 'ellipse')

        Returns:
            Best-fitting primitive parameters
        """
        # Calculate shape metrics
        metrics = self.calculate_shape_metrics(polygon)

        # Try all primitives
        candidates = []

        # Circle
        circle = self.fit_circle_2d(polygon)
        # Boost circle quality if high circularity
        if metrics['circularity'] > 0.90:
            circle['fit_quality'] *= 1.2  # 20% bonus
        elif metrics['circularity'] < 0.80:
            circle['fit_quality'] *= 0.7  # 30% penalty for non-circular
        circle['metrics'] = metrics
        candidates.append(circle)

        # Rectangle
        rectangle = self.fit_rectangle_2d(polygon)
        # Boost rectangle quality if high rectangularity
        if metrics['rectangularity'] > 0.95:
            rectangle['fit_quality'] *= 1.3  # 30% bonus for rectangular
        elif metrics['rectangularity'] < 0.85:
            rectangle['fit_quality'] *= 0.8  # 20% penalty
        rectangle['metrics'] = metrics
        candidates.append(rectangle)

        # Ellipse
        ellipse = self.fit_ellipse_2d(polygon)
        # Boost ellipse if elongated (high aspect ratio)
        if metrics['aspect_ratio'] > 1.5:
            ellipse['fit_quality'] *= 1.1  # 10% bonus
        ellipse['metrics'] = metrics
        candidates.append(ellipse)

        # Select best based on fit_quality (with shape-aware adjustments)
        best = None

        if shape_hint:
            # Prefer hinted shape if quality is reasonable
            for candidate in candidates:
                if candidate['type'] == shape_hint and candidate['fit_quality'] > 0.7:
                    best = candidate
                    break

        # Shape discrimination logic based on metrics (if no hint match)
        if best is None:
            # Rule 1: High rectangularity + low circularity → Rectangle
            if metrics['rectangularity'] > 0.90 and metrics['circularity'] < 0.82:
                for candidate in candidates:
                    if candidate['type'] == 'rectangle':
                        best = candidate
                        break

            # Rule 2: High circularity + low rectangularity → Circle
            elif metrics['circularity'] > 0.90 and metrics['rectangularity'] < 0.85:
                for candidate in candidates:
                    if candidate['type'] == 'circle':
                        best = candidate
                        break

            # Rule 3: For ambiguous cases (both moderate), prefer rectangle if rectangularity is higher
            elif metrics['rectangularity'] > metrics['circularity'] + 0.10:
                for candidate in candidates:
                    if candidate['type'] == 'rectangle':
                        best = candidate
                        break

        # Otherwise, select highest quality
        if best is None:
            best = max(candidates, key=lambda x: x['fit_quality'])

        # CV validation (if enabled)
        if self.use_cv_validation and self.cv_validator is not None:
            cv_result = self.cv_validator.validate_primitive_fit(polygon, best)
            best['cv_validation'] = cv_result

            # If CV confidence is low, flag for polygon extrusion
            if cv_result['confidence'] < self.cv_threshold:
                if self.verbose:
                    print(f"  ⚠️  Low CV confidence ({cv_result['confidence']:.2f}) for {best['type']}")
                    print(f"      Recommendation: {cv_result['recommendation']}")

                # Mark for polygon extrusion instead
                best['use_polygon_extrusion'] = True
            else:
                best['use_polygon_extrusion'] = False
        else:
            # No CV validation, use geometric heuristics
            rectangularity = best.get('rectangularity', 1.0)
            best['use_polygon_extrusion'] = (rectangularity < 0.75)

        return best

    def fuzzy_size_match(self, area_ratio: float) -> float:
        """
        Fuzzy membership: how similar are sizes?

        Sharp transition detection:
        - area_ratio = min_area / max_area
        - For 280% increase: ratio = 0.26 → very different
        - For 15% change: ratio = 0.87 → borderline
        - For 5% change: ratio = 0.95 → very similar

        Relaxed thresholds to reduce over-segmentation while still
        detecting major transitions.
        """
        if area_ratio > 0.95:
            return 1.0  # Very similar (< 5% change)
        elif area_ratio > 0.85:
            return 0.8  # Similar (< 15% change)
        elif area_ratio > 0.70:
            return 0.6  # Somewhat similar (< 30% change)
        elif area_ratio > 0.50:
            return 0.3  # Different (< 50% change)
        else:
            return 0.0  # Very different (> 50% change) - SPLIT

    def fuzzy_shape_match(self, shape_a: str, shape_b: str) -> float:
        """Fuzzy membership: how similar are shapes?"""
        if shape_a == shape_b:
            return 1.0
        elif (shape_a == 'circle' and shape_b == 'ellipse') or \
             (shape_a == 'ellipse' and shape_b == 'circle'):
            return 0.7  # Related shapes
        elif (shape_a == 'rectangle' and shape_b == 'ellipse') or \
             (shape_a == 'ellipse' and shape_b == 'rectangle'):
            return 0.5  # Somewhat related (increased from 0.4)
        elif (shape_a == 'circle' and shape_b == 'rectangle') or \
             (shape_a == 'rectangle' and shape_b == 'circle'):
            return 0.4  # Allow circle-rectangle merging for thin caps
        else:
            return 0.1  # Different

    def fuzzy_alignment(self, centroid_dist: float, avg_radius: float) -> float:
        """Fuzzy membership: how well aligned are centroids?"""
        if avg_radius == 0:
            return 0.5

        ratio = centroid_dist / avg_radius
        if ratio < 0.05:
            return 1.0  # Perfectly aligned
        elif ratio < 0.10:
            return 0.8  # Well aligned
        elif ratio < 0.20:
            return 0.5  # Moderately aligned
        else:
            return 0.2  # Misaligned

    def should_merge_segments(
        self,
        seg_a: Dict[str, Any],
        seg_b: Dict[str, Any]
    ) -> Tuple[bool, str, float]:
        """
        Fuzzy logic decision: should these segments be merged?

        Args:
            seg_a, seg_b: Segment dictionaries

        Returns:
            (should_merge, confidence_level, merge_score)
        """
        # Extract representative primitives
        prim_a = seg_a['primitive_2d']
        prim_b = seg_b['primitive_2d']

        # Size similarity (area ratio)
        area_a = seg_a['layers'][0]['area']
        area_b = seg_b['layers'][0]['area']
        area_ratio = min(area_a, area_b) / max(area_a, area_b) if max(area_a, area_b) > 0 else 0

        # Shape similarity
        shape_match = self.fuzzy_shape_match(prim_a['type'], prim_b['type'])

        # Centroid alignment
        centroid_a = seg_a['layers'][0]['centroid']
        centroid_b = seg_b['layers'][0]['centroid']
        centroid_dist = np.linalg.norm(centroid_a - centroid_b)

        # Average "radius" for normalization
        if prim_a['type'] == 'circle':
            radius_a = prim_a['radius']
        elif prim_a['type'] == 'rectangle':
            radius_a = (prim_a['width'] + prim_a['height']) / 4
        elif prim_a['type'] == 'ellipse':
            radius_a = (prim_a['major_axis'] + prim_a['minor_axis']) / 4
        else:
            radius_a = np.sqrt(area_a / np.pi)

        if prim_b['type'] == 'circle':
            radius_b = prim_b['radius']
        elif prim_b['type'] == 'rectangle':
            radius_b = (prim_b['width'] + prim_b['height']) / 4
        elif prim_b['type'] == 'ellipse':
            radius_b = (prim_b['major_axis'] + prim_b['minor_axis']) / 4
        else:
            radius_b = np.sqrt(area_b / np.pi)

        avg_radius = (radius_a + radius_b) / 2

        alignment = self.fuzzy_alignment(centroid_dist, avg_radius)

        # Weighted fuzzy aggregation
        size_match = self.fuzzy_size_match(area_ratio)
        merge_score = (
            0.40 * size_match +
            0.35 * shape_match +
            0.25 * alignment
        )

        # Decision thresholds (relaxed to reduce over-segmentation)
        if merge_score > 0.70:
            return True, "high_confidence", merge_score
        elif merge_score > 0.50:
            return True, "medium_confidence", merge_score
        elif merge_score > 0.35:
            return True, "low_confidence", merge_score
        else:
            return False, "split_segments", merge_score

    def _filter_boundary_artifacts(self, layers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove tiny artifact layers at mesh boundaries.

        These occur at the start/end of slicing where the plane just barely
        intersects the mesh, creating unrealistically small cross-sections.

        Args:
            layers: List of layer dictionaries

        Returns:
            Filtered list without boundary artifacts
        """
        if len(layers) < 5:
            return layers  # Too few layers to filter

        # Calculate median area (representative of actual cross-section)
        areas = [layer['area'] for layer in layers]
        median_area = np.median(areas)

        if median_area == 0:
            return layers  # Can't filter

        # Find first stable layer (area > 10% of median)
        start_idx = 0
        threshold = 0.10 * median_area

        for i, layer in enumerate(layers):
            if layer['area'] > threshold:
                start_idx = i
                break

        # Find last stable layer (area > 10% of median)
        end_idx = len(layers) - 1
        for i in range(len(layers) - 1, -1, -1):
            if layers[i]['area'] > threshold:
                end_idx = i
                break

        # Only filter if we're actually removing artifacts (not cutting too much)
        if start_idx > len(layers) * 0.2 or (len(layers) - end_idx - 1) > len(layers) * 0.2:
            # Would remove >20% of layers, probably not artifacts
            return layers

        filtered = layers[start_idx:end_idx + 1]

        if self.verbose and (start_idx > 0 or end_idx < len(layers) - 1):
            print(f"  🔧 Filtered boundary artifacts: removed {start_idx} start + {len(layers) - end_idx - 1} end layers")
            print(f"     Median area: {median_area:.1f}mm², threshold: {threshold:.1f}mm²")

        return filtered if len(filtered) > 0 else layers

    def group_similar_layers(
        self,
        layers: List[Dict[str, Any]],
        vision_results: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Group consecutive layers into segments using fuzzy logic.

        Args:
            layers: List of layer dictionaries
            vision_results: Optional vision analysis results for hints

        Returns:
            List of segment dictionaries
        """
        if len(layers) == 0:
            return []

        # CRITICAL FIX: Remove startup/shutdown artifacts
        # These are tiny layers at the beginning/end caused by mesh boundaries
        filtered_layers = self._filter_boundary_artifacts(layers)

        if len(filtered_layers) == 0:
            return []

        segments = []
        current_segment_layers = [filtered_layers[0]]

        # Classify first layer
        shape_hint = None
        if vision_results and len(vision_results) > 0:
            shape_hint = vision_results[0].get('shape_detected')

        first_primitive = self.classify_and_fit_2d(filtered_layers[0]['polygon'], shape_hint)

        for i in range(1, len(filtered_layers)):
            prev_layer = filtered_layers[i-1]
            curr_layer = filtered_layers[i]

            # Get vision hint for current layer
            shape_hint_curr = None
            if vision_results and i < len(vision_results):
                shape_hint_curr = vision_results[i].get('shape_detected')

            # Fit primitive to current layer
            curr_primitive = self.classify_and_fit_2d(curr_layer['polygon'], shape_hint_curr)
            prev_primitive = self.classify_and_fit_2d(prev_layer['polygon'])

            # Create temporary segments for comparison
            temp_seg_prev = {
                'primitive_2d': prev_primitive,
                'layers': [prev_layer]
            }
            temp_seg_curr = {
                'primitive_2d': curr_primitive,
                'layers': [curr_layer]
            }

            # Fuzzy decision
            should_merge, confidence, score = self.should_merge_segments(temp_seg_prev, temp_seg_curr)

            if should_merge:
                # Continue current segment
                current_segment_layers.append(curr_layer)
            else:
                # End current segment, start new one
                # Fit primitive to representative layer (middle)
                mid_idx = len(current_segment_layers) // 2
                rep_layer = current_segment_layers[mid_idx]

                shape_hint_rep = None
                if vision_results:
                    rep_vision_idx = layers.index(rep_layer)
                    if rep_vision_idx < len(vision_results):
                        shape_hint_rep = vision_results[rep_vision_idx].get('shape_detected')

                segment_primitive = self.classify_and_fit_2d(rep_layer['polygon'], shape_hint_rep)

                # Calculate proper height including layer thickness
                z_start = current_segment_layers[0]['z_height']
                z_end = current_segment_layers[-1]['z_height']
                num_layers = len(current_segment_layers)
                # Height = span + layer_height (to account for thickness)
                height = (z_end - z_start) + self.layer_height

                segments.append({
                    'z_start': z_start,
                    'z_end': z_end,
                    'height': height,
                    'num_layers': num_layers,
                    'layers': current_segment_layers,
                    'primitive_2d': segment_primitive,
                    'shape': segment_primitive['type']
                })

                # Start new segment
                current_segment_layers = [curr_layer]

        # Add final segment
        if current_segment_layers:
            mid_idx = len(current_segment_layers) // 2
            rep_layer = current_segment_layers[mid_idx]

            shape_hint_final = None
            if vision_results:
                final_vision_idx = layers.index(rep_layer)
                if final_vision_idx < len(vision_results):
                    shape_hint_final = vision_results[final_vision_idx].get('shape_detected')

            segment_primitive = self.classify_and_fit_2d(rep_layer['polygon'], shape_hint_final)

            # Calculate proper height including layer thickness
            z_start = current_segment_layers[0]['z_height']
            z_end = current_segment_layers[-1]['z_height']
            num_layers = len(current_segment_layers)
            # Height = span + layer_height (to account for thickness)
            height = (z_end - z_start) + self.layer_height

            segments.append({
                'z_start': z_start,
                'z_end': z_end,
                'height': height,
                'num_layers': num_layers,
                'layers': current_segment_layers,
                'primitive_2d': segment_primitive,
                'shape': segment_primitive['type']
            })

        # Post-process: Merge segments shorter than min_segment_height
        # with adjacent compatible segments
        merged = True
        iteration = 0
        max_iterations = 10  # Prevent infinite loops

        while merged and iteration < max_iterations:
            merged = False
            iteration += 1
            new_segments = []
            i = 0

            while i < len(segments):
                seg = segments[i]

                # If segment is too short, try to merge with neighbors
                if seg['height'] < self.min_segment_height:
                    merged_this = False

                    # Try merging with next segment
                    if i < len(segments) - 1:
                        next_seg = segments[i + 1]
                        should_merge, _, _ = self.should_merge_segments(
                            {'primitive_2d': seg['primitive_2d'], 'layers': seg['layers']},
                            {'primitive_2d': next_seg['primitive_2d'], 'layers': next_seg['layers']}
                        )

                        if should_merge or seg['shape'] == next_seg['shape']:
                            # Merge with next
                            combined_layers = seg['layers'] + next_seg['layers']
                            mid_idx = len(combined_layers) // 2
                            rep_layer = combined_layers[mid_idx]
                            combined_primitive = self.classify_and_fit_2d(rep_layer['polygon'])

                            z_start = combined_layers[0]['z_height']
                            z_end = combined_layers[-1]['z_height']
                            height = (z_end - z_start) + self.layer_height

                            new_segments.append({
                                'z_start': z_start,
                                'z_end': z_end,
                                'height': height,
                                'num_layers': len(combined_layers),
                                'layers': combined_layers,
                                'primitive_2d': combined_primitive,
                                'shape': combined_primitive['type']
                            })
                            i += 2  # Skip both current and next
                            merged = True
                            merged_this = True

                    # Try merging with previous segment if not merged yet
                    if not merged_this and len(new_segments) > 0:
                        prev_seg = new_segments[-1]
                        should_merge, _, _ = self.should_merge_segments(
                            {'primitive_2d': prev_seg['primitive_2d'], 'layers': prev_seg['layers']},
                            {'primitive_2d': seg['primitive_2d'], 'layers': seg['layers']}
                        )

                        if should_merge or prev_seg['shape'] == seg['shape']:
                            # Merge with previous
                            combined_layers = prev_seg['layers'] + seg['layers']
                            mid_idx = len(combined_layers) // 2
                            rep_layer = combined_layers[mid_idx]
                            combined_primitive = self.classify_and_fit_2d(rep_layer['polygon'])

                            z_start = combined_layers[0]['z_height']
                            z_end = combined_layers[-1]['z_height']
                            height = (z_end - z_start) + self.layer_height

                            # Replace previous segment
                            new_segments[-1] = {
                                'z_start': z_start,
                                'z_end': z_end,
                                'height': height,
                                'num_layers': len(combined_layers),
                                'layers': combined_layers,
                                'primitive_2d': combined_primitive,
                                'shape': combined_primitive['type']
                            }
                            i += 1
                            merged = True
                            merged_this = True

                    if not merged_this:
                        # Couldn't merge, keep as-is
                        new_segments.append(seg)
                        i += 1
                else:
                    # Segment is long enough, keep it
                    new_segments.append(seg)
                    i += 1

            segments = new_segments

        if self.verbose and iteration > 1:
            print(f"  Merged short segments in {iteration} iteration(s): {len(segments)} final segments")

        return segments

    def extrude_segment(
        self,
        segment: Dict[str, Any],
        axis: np.ndarray,
        axis_name: str
    ) -> Optional[trimesh.Trimesh]:
        """
        Extrude 2D primitive to 3D mesh.

        Args:
            segment: Segment dictionary with primitive_2d and height
            axis: Extrusion axis (unit vector)
            axis_name: Axis name ('X', 'Y', 'Z')

        Returns:
            3D trimesh primitive or None if failed
        """
        prim_2d = segment['primitive_2d']
        height = segment['height']
        z_center = (segment['z_start'] + segment['z_end']) / 2

        try:
            if prim_2d['type'] == 'circle':
                # Circle → Cylinder
                radius = prim_2d['radius']
                cylinder = trimesh.creation.cylinder(
                    radius=radius,
                    height=height,
                    sections=32
                )

                # Position at correct height
                center_2d = prim_2d['center']

                # Translate based on axis
                if axis_name == 'Z':
                    translation = [center_2d[0], center_2d[1], z_center]
                elif axis_name == 'Y':
                    translation = [center_2d[0], z_center, center_2d[1]]
                else:  # X
                    translation = [z_center, center_2d[0], center_2d[1]]

                cylinder.apply_translation(translation)
                return cylinder

            elif prim_2d['type'] == 'rectangle':
                # Check if we should use actual polygon extrusion instead
                # (flagged by CV validation or geometric heuristics)
                use_polygon = prim_2d.get('use_polygon_extrusion', False)

                if use_polygon:
                    # Use actual polygon extrusion for better accuracy
                    if self.verbose:
                        cv_info = prim_2d.get('cv_validation', {})
                        if cv_info:
                            print(f"  ⚠️  CV flagged for polygon extrusion (confidence: {cv_info.get('confidence', 0):.2f})")
                        else:
                            rectangularity = prim_2d.get('rectangularity', 1.0)
                            print(f"  ⚠️  Low rectangularity ({rectangularity:.2f}) - using polygon extrusion")

                    # Get the representative layer polygon
                    if 'layers' in segment and len(segment['layers']) > 0:
                        mid_idx = len(segment['layers']) // 2
                        rep_layer = segment['layers'][mid_idx]
                        polygon = rep_layer['polygon']

                        # Extrude polygon to mesh
                        extruded = trimesh.creation.extrude_polygon(
                            polygon,
                            height=height
                        )

                        # Position based on axis
                        if axis_name == 'Z':
                            translation = [0, 0, z_center - height/2]
                        elif axis_name == 'Y':
                            # Rotate to align with Y axis
                            rotation = trimesh.transformations.rotation_matrix(
                                np.pi/2, [1, 0, 0]
                            )
                            extruded.apply_transform(rotation)
                            translation = [0, z_center, 0]
                        else:  # X
                            # Rotate to align with X axis
                            rotation = trimesh.transformations.rotation_matrix(
                                np.pi/2, [0, 1, 0]
                            )
                            extruded.apply_transform(rotation)
                            translation = [z_center, 0, 0]

                        extruded.apply_translation(translation)
                        return extruded

                # High rectangularity - use solid box primitive
                width = prim_2d['width']
                depth = prim_2d['height']

                box = trimesh.creation.box(extents=[width, depth, height])

                # Position and rotate
                center_2d = prim_2d['center']
                rotation_angle = np.radians(prim_2d['rotation'])

                # Apply rotation around Z-axis (in 2D plane)
                rotation_matrix = trimesh.transformations.rotation_matrix(
                    rotation_angle,
                    [0, 0, 1]
                )
                box.apply_transform(rotation_matrix)

                # Translate based on axis
                if axis_name == 'Z':
                    translation = [center_2d[0], center_2d[1], z_center]
                elif axis_name == 'Y':
                    translation = [center_2d[0], z_center, center_2d[1]]
                else:  # X
                    translation = [z_center, center_2d[0], center_2d[1]]

                box.apply_translation(translation)
                return box

            elif prim_2d['type'] == 'ellipse':
                # Ellipse → Scaled cylinder
                major = prim_2d['major_axis'] / 2
                minor = prim_2d['minor_axis'] / 2

                # Create cylinder with radius = average
                avg_radius = (major + minor) / 2
                cylinder = trimesh.creation.cylinder(
                    radius=avg_radius,
                    height=height,
                    sections=32
                )

                # Scale to ellipse
                scale_x = major / avg_radius
                scale_y = minor / avg_radius
                scale_matrix = np.diag([scale_x, scale_y, 1.0, 1.0])
                cylinder.apply_transform(scale_matrix)

                # Rotate
                rotation_angle = np.radians(prim_2d['rotation'])
                rotation_matrix = trimesh.transformations.rotation_matrix(
                    rotation_angle,
                    [0, 0, 1]
                )
                cylinder.apply_transform(rotation_matrix)

                # Translate
                center_2d = prim_2d['center']
                if axis_name == 'Z':
                    translation = [center_2d[0], center_2d[1], z_center]
                elif axis_name == 'Y':
                    translation = [center_2d[0], z_center, center_2d[1]]
                else:  # X
                    translation = [z_center, center_2d[0], center_2d[1]]

                cylinder.apply_translation(translation)
                return cylinder

            else:
                if self.verbose:
                    print(f"  ⚠️  Unknown primitive type: {prim_2d['type']}")
                return None

        except Exception as e:
            if self.verbose:
                print(f"  ❌ Extrusion failed: {e}")
            return None

    def combine_primitives(
        self,
        primitives: List[trimesh.Trimesh]
    ) -> Optional[trimesh.Trimesh]:
        """
        Combine multiple primitives into single mesh using concatenation.

        Note: Using concatenation instead of boolean union because:
        - Boolean union requires blender or manifold (external dependencies)
        - For stacked primitives (non-overlapping), concatenation is sufficient
        - Faster and more reliable

        Args:
            primitives: List of trimesh primitives

        Returns:
            Combined mesh or None if failed
        """
        if len(primitives) == 0:
            return None

        if len(primitives) == 1:
            return primitives[0]

        try:
            # Simple concatenation for non-overlapping primitives
            if self.verbose:
                print(f"  🔗 Concatenating {len(primitives)} primitives...")

            combined = trimesh.util.concatenate(primitives)

            # Validate result
            if self.verbose:
                if not combined.is_watertight:
                    print(f"  ⚠️  Warning: Combined mesh is not watertight")
                else:
                    print(f"  ✅ Combined mesh is watertight")

            return combined

        except Exception as e:
            if self.verbose:
                print(f"  ❌ Concatenation failed: {e}")
            return None

    def calculate_quality(
        self,
        original: trimesh.Trimesh,
        reconstructed: trimesh.Trimesh
    ) -> float:
        """
        Calculate reconstruction quality score (0-100).

        Args:
            original: Original mesh
            reconstructed: Reconstructed mesh

        Returns:
            Quality score
        """
        try:
            # Volume error
            vol_orig = original.volume
            vol_recon = reconstructed.volume
            vol_error = abs(vol_orig - vol_recon) / vol_orig if vol_orig > 0 else 1.0

            # Simplified quality: 1 - volume_error
            quality = max(0, 1 - vol_error)

            return int(quality * 100)

        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Quality calculation failed: {e}")
            return 0

    def reconstruct(
        self,
        mesh: trimesh.Trimesh,
        vision_results: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Reconstruct mesh as stack of primitives.

        Args:
            mesh: Input mesh
            vision_results: Optional vision analysis results

        Returns:
            Reconstruction result dictionary
        """
        if self.verbose:
            print("\n🏗️  Layer-Wise Primitive Stacking (LPS)")
            print("="*70)

        # Step 1: Detect primary axis
        axis, axis_name = self.detect_primary_axis(mesh)
        if self.verbose:
            print(f"\n📐 Primary axis: {axis_name}")

        # Step 2: Slice mesh
        if self.verbose:
            print(f"\n🔪 Slicing mesh (layer height: {self.layer_height}mm)...")

        layers = self.slice_mesh(mesh, axis, self.layer_height)

        if self.verbose:
            print(f"  ✅ {len(layers)} valid layers extracted")

        if len(layers) == 0:
            return {
                'success': False,
                'error': 'No valid layers could be extracted',
                'segments': [],
                'reconstructed_mesh': None,
                'quality_score': 0
            }

        # Step 3: Group layers into segments
        if self.verbose:
            print(f"\n🔗 Grouping similar layers into segments...")

        segments = self.group_similar_layers(layers, vision_results)

        if self.verbose:
            print(f"  ✅ Detected {len(segments)} segment(s):")
            for i, seg in enumerate(segments):
                print(f"     Segment {i+1}: {seg['shape'].upper()} @ Z=[{seg['z_start']:.1f}, {seg['z_end']:.1f}]mm (H={seg['height']:.1f}mm)")

        # Step 4: Extrude segments to 3D primitives
        if self.verbose:
            print(f"\n⬆️  Extruding segments to 3D primitives...")

        primitives = []
        for i, segment in enumerate(segments):
            primitive_3d = self.extrude_segment(segment, axis, axis_name)
            if primitive_3d is not None:
                primitives.append(primitive_3d)
                segment['primitive_3d'] = primitive_3d
                if self.verbose:
                    print(f"  ✅ Segment {i+1} extruded: {segment['shape']} (V={primitive_3d.volume:.1f}mm³)")
            else:
                if self.verbose:
                    print(f"  ❌ Segment {i+1} extrusion failed")

        if len(primitives) == 0:
            return {
                'success': False,
                'error': 'No primitives could be extruded',
                'segments': segments,
                'reconstructed_mesh': None,
                'quality_score': 0
            }

        # Step 5: Combine primitives
        if self.verbose:
            print(f"\n🔗 Combining {len(primitives)} primitive(s)...")

        reconstructed = self.combine_primitives(primitives)

        if reconstructed is None:
            return {
                'success': False,
                'error': 'Boolean union failed',
                'segments': segments,
                'reconstructed_mesh': None,
                'quality_score': 0
            }

        # Step 6: Calculate quality
        if self.verbose:
            print(f"\n📊 Calculating quality...")

        quality_score = self.calculate_quality(mesh, reconstructed)

        if self.verbose:
            print(f"  ✅ Quality Score: {quality_score}/100")
            print(f"\n{'='*70}")
            print(f"✅ Reconstruction complete!")
            print(f"   - {len(segments)} segment(s) detected")
            print(f"   - {len(primitives)} primitive(s) generated")
            print(f"   - Quality: {quality_score}/100")

        return {
            'success': True,
            'axis': axis,
            'axis_name': axis_name,
            'num_layers': len(layers),
            'num_segments': len(segments),
            'segments': segments,
            'reconstructed_mesh': reconstructed,
            'quality_score': quality_score
        }


# Convenience function
def reconstruct_layerwise(
    mesh: trimesh.Trimesh,
    layer_height: float = 0.5,
    vision_results: Optional[List[Dict]] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Reconstruct mesh using layer-wise primitive stacking.

    Args:
        mesh: Input mesh
        layer_height: Distance between slices (mm)
        vision_results: Optional vision analysis results
        verbose: Print progress

    Returns:
        Reconstruction result
    """
    stacker = LayerWiseStacker(layer_height=layer_height, verbose=verbose)
    return stacker.reconstruct(mesh, vision_results)
