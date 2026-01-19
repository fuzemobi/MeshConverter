#!/usr/bin/env python3
"""
Multi-View Primitive Detector

Uses OpenCV multi-view rendering and contour extraction to detect 2D primitives
from clean contours instead of noisy mesh cross-sections.

This provides significantly better accuracy than direct mesh slicing.
"""

import trimesh
import numpy as np
import cv2
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class View2D:
    """Represents a 2D view of the mesh"""
    name: str  # 'front', 'side', 'top'
    azimuth: float  # Rotation around Z axis (degrees)
    elevation: float  # Rotation around X axis (degrees)
    axis: str  # 'X', 'Y', or 'Z' - which axis is perpendicular to view
    image: np.ndarray = None  # Binary image
    contour_points: np.ndarray = None  # Extracted contour points
    primitive: Dict[str, Any] = None  # Fitted 2D primitive


class MultiViewPrimitiveDetector:
    """
    Detects 2D primitives using multi-view contour extraction.

    Strategy:
    1. Render mesh from 3 orthogonal views (XY plane, XZ plane, YZ plane)
    2. Extract clean contours using OpenCV
    3. Fit 2D primitives (circle, rectangle) to each contour
    4. Validate consistency across views
    5. Return best-fit primitives for 3D reconstruction
    """

    def __init__(self, image_size: int = 512, verbose: bool = True):
        """
        Args:
            image_size: Resolution for rendered views (pixels)
            verbose: Print progress messages
        """
        self.image_size = image_size
        self.verbose = verbose

        # Define 3 orthogonal views
        self.orthogonal_views = [
            View2D(name='top', azimuth=0, elevation=90, axis='Z'),      # Looking down Z axis (XY plane)
            View2D(name='front', azimuth=0, elevation=0, axis='Y'),     # Looking along Y axis (XZ plane)
            View2D(name='side', azimuth=90, elevation=0, axis='X'),     # Looking along X axis (YZ plane)
        ]

    def render_view(
        self,
        mesh: trimesh.Trimesh,
        azimuth: float,
        elevation: float
    ) -> np.ndarray:
        """
        Render mesh from a specific viewpoint to binary image.

        Args:
            mesh: Input mesh
            azimuth: Rotation around Z axis (degrees)
            elevation: Rotation around X axis (degrees)

        Returns:
            Binary image (0 or 255)
        """
        # Create rotation matrix
        az_rad = np.radians(azimuth)
        el_rad = np.radians(elevation)

        # Rotate mesh
        mesh_copy = mesh.copy()

        # Rotate around Z (azimuth)
        rot_z = trimesh.transformations.rotation_matrix(az_rad, [0, 0, 1])
        mesh_copy.apply_transform(rot_z)

        # Rotate around X (elevation)
        rot_x = trimesh.transformations.rotation_matrix(el_rad, [1, 0, 0])
        mesh_copy.apply_transform(rot_x)

        # Project to 2D (orthographic projection - just drop Z coordinate)
        vertices_2d = mesh_copy.vertices[:, :2]  # Take X, Y only

        # Normalize to image space
        min_coords = vertices_2d.min(axis=0)
        max_coords = vertices_2d.max(axis=0)
        range_coords = max_coords - min_coords

        if range_coords.max() == 0:
            # Degenerate case
            return np.zeros((self.image_size, self.image_size), dtype=np.uint8)

        # Add 10% padding
        padding = 0.1
        scale = (self.image_size * (1 - 2*padding)) / range_coords.max()

        vertices_normalized = (vertices_2d - min_coords) * scale + self.image_size * padding
        vertices_pixels = vertices_normalized.astype(np.int32)

        # Create binary image by drawing filled triangles
        img = np.zeros((self.image_size, self.image_size), dtype=np.uint8)

        for face in mesh_copy.faces:
            pts = vertices_pixels[face]
            cv2.fillConvexPoly(img, pts, 255)

        return img

    def extract_contour_points(self, binary_image: np.ndarray) -> np.ndarray:
        """
        Extract contour points from binary image using OpenCV.

        Args:
            binary_image: Binary image (0 or 255)

        Returns:
            Array of contour points (Nx2)
        """
        # Find contours
        contours, _ = cv2.findContours(
            binary_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if len(contours) == 0:
            return np.array([])

        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)

        # Simplify contour (Douglas-Peucker algorithm)
        epsilon = 0.01 * cv2.arcLength(largest_contour, True)
        simplified = cv2.approxPolyDP(largest_contour, epsilon, True)

        # Extract points
        points = simplified.reshape(-1, 2)

        return points

    def fit_circle_to_contour(self, contour_points: np.ndarray) -> Dict[str, Any]:
        """
        Fit circle to 2D contour points.

        Args:
            contour_points: Nx2 array of contour points

        Returns:
            Dictionary with circle parameters and fit quality
        """
        if len(contour_points) < 5:
            return {'type': 'circle', 'valid': False}

        # Use OpenCV minEnclosingCircle
        (center_x, center_y), radius = cv2.minEnclosingCircle(contour_points.astype(np.float32))

        # Calculate fit quality (how circular is the contour?)
        # Measure deviation of points from fitted circle
        center = np.array([center_x, center_y])
        distances = np.linalg.norm(contour_points - center, axis=1)
        deviation = np.std(distances) / radius if radius > 0 else float('inf')

        # Circularity check
        is_circular = deviation < 0.1  # Points should be within 10% std dev

        return {
            'type': 'circle',
            'center': center,
            'radius': radius,
            'deviation': deviation,
            'is_circular': is_circular,
            'valid': True,
            'confidence': 1.0 - min(deviation, 1.0)  # 0-1 scale
        }

    def fit_rectangle_to_contour(self, contour_points: np.ndarray) -> Dict[str, Any]:
        """
        Fit rectangle to 2D contour points.

        Args:
            contour_points: Nx2 array of contour points

        Returns:
            Dictionary with rectangle parameters and fit quality
        """
        if len(contour_points) < 4:
            return {'type': 'rectangle', 'valid': False}

        # Use OpenCV minAreaRect (oriented bounding box in 2D)
        rect = cv2.minAreaRect(contour_points.astype(np.float32))

        # rect = ((center_x, center_y), (width, height), angle)
        center = np.array(rect[0])
        width, height = rect[1]
        angle = rect[2]

        # Calculate fit quality (how rectangular is the contour?)
        # Get the 4 corner points of the fitted rectangle
        box_points = cv2.boxPoints(rect)

        # Calculate area ratio
        rect_area = width * height
        contour_area = cv2.contourArea(contour_points.astype(np.float32))
        area_ratio = contour_area / rect_area if rect_area > 0 else 0

        # Rectangularity check
        is_rectangular = 0.85 <= area_ratio <= 1.15  # Within 15% of rectangle area

        return {
            'type': 'rectangle',
            'center': center,
            'width': width,
            'height': height,
            'angle': angle,
            'area_ratio': area_ratio,
            'is_rectangular': is_rectangular,
            'valid': True,
            'confidence': min(area_ratio, 2.0 - area_ratio) if area_ratio <= 1.0 else max(0, 2.0 - area_ratio)
        }

    def fit_primitive_to_contour(self, contour_points: np.ndarray) -> Dict[str, Any]:
        """
        Fit best primitive (circle or rectangle) to contour.

        Args:
            contour_points: Nx2 array of contour points

        Returns:
            Best-fit primitive with type and parameters
        """
        if len(contour_points) < 4:
            return {'type': 'unknown', 'valid': False}

        # Try both circle and rectangle
        circle = self.fit_circle_to_contour(contour_points)
        rectangle = self.fit_rectangle_to_contour(contour_points)

        # Choose best fit based on confidence
        # CRITICAL: For complex shapes, rectangle should be strongly preferred
        # Use threshold-based selection instead of just comparing confidence
        if circle['valid'] and rectangle['valid']:
            # If circle confidence is very high (>0.9) and much better than rectangle
            if circle['is_circular'] and circle['confidence'] > 0.9 and circle['confidence'] > rectangle['confidence'] + 0.2:
                return circle
            # Otherwise prefer rectangle (more general, works for complex shapes)
            else:
                return rectangle
        elif circle['valid']:
            return circle
        elif rectangle['valid']:
            return rectangle
        else:
            return {'type': 'unknown', 'valid': False}

    def detect_from_mesh(self, mesh: trimesh.Trimesh) -> List[View2D]:
        """
        Detect 2D primitives from 3 orthogonal views of the mesh.

        Args:
            mesh: Input mesh to analyze

        Returns:
            List of View2D objects with detected primitives
        """
        if self.verbose:
            print(f"\n🔍 Multi-View Primitive Detection")
            print(f"   Analyzing 3 orthogonal views...")

        results = []

        for view in self.orthogonal_views:
            if self.verbose:
                print(f"   {view.name.capitalize()} view ({view.axis} axis): az={view.azimuth}°, el={view.elevation}°")

            # Render view
            view.image = self.render_view(mesh, view.azimuth, view.elevation)

            # Extract contour
            view.contour_points = self.extract_contour_points(view.image)

            if len(view.contour_points) < 4:
                if self.verbose:
                    print(f"      ⚠️  Failed to extract contour")
                view.primitive = {'type': 'unknown', 'valid': False}
            else:
                # Fit primitive
                view.primitive = self.fit_primitive_to_contour(view.contour_points)

                if self.verbose and view.primitive['valid']:
                    prim = view.primitive
                    print(f"      ✅ {prim['type'].upper()} detected (confidence: {prim['confidence']:.2f})")
                    if prim['type'] == 'circle':
                        print(f"         Radius: {prim['radius']:.1f}px")
                    elif prim['type'] == 'rectangle':
                        print(f"         Dimensions: {prim['width']:.1f} × {prim['height']:.1f}px")

            results.append(view)

        if self.verbose:
            print(f"   ✅ Multi-view detection complete")

        return results

    def validate_consistency(self, views: List[View2D]) -> Dict[str, Any]:
        """
        Validate consistency across views to determine overall shape.

        For example:
        - Circle in all 3 views → Sphere
        - Circle in 2 views, rectangle in 1 → Cylinder
        - Rectangle in all 3 views → Box

        Args:
            views: List of View2D objects with detected primitives

        Returns:
            Dictionary with overall shape classification and confidence
        """
        # Count primitive types
        primitive_types = [v.primitive['type'] for v in views if v.primitive['valid']]

        if len(primitive_types) == 0:
            return {'shape': 'unknown', 'confidence': 0.0}

        circle_count = primitive_types.count('circle')
        rectangle_count = primitive_types.count('rectangle')

        # Classify overall shape
        if circle_count == 3:
            shape = 'sphere'
            confidence = np.mean([v.primitive['confidence'] for v in views if v.primitive['type'] == 'circle'])
        elif circle_count == 2 and rectangle_count == 1:
            shape = 'cylinder'
            confidence = np.mean([v.primitive['confidence'] for v in views if v.primitive['valid']])
        elif rectangle_count == 3:
            shape = 'box'
            confidence = np.mean([v.primitive['confidence'] for v in views if v.primitive['type'] == 'rectangle'])
        elif rectangle_count >= 1:
            shape = 'box'  # Default to box for mixed cases
            confidence = np.mean([v.primitive['confidence'] for v in views if v.primitive['valid']])
        else:
            shape = 'complex'
            confidence = np.mean([v.primitive['confidence'] for v in views if v.primitive['valid']])

        if self.verbose:
            print(f"\n📊 Shape Classification:")
            print(f"   Detected: {shape.upper()} (confidence: {confidence:.2f})")
            print(f"   Views: {circle_count} circles, {rectangle_count} rectangles")

        return {
            'shape': shape,
            'confidence': confidence,
            'views': views
        }
