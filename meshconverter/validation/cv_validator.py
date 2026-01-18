#!/usr/bin/env python3
"""
CV-Based Reconstruction Validator

Uses OpenCV and image metrics to validate geometric primitive fitting
and suggest alternative strategies when quality is low.
"""

import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional
from shapely.geometry import Polygon as ShapelyPolygon
from skimage.metrics import structural_similarity as ssim
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import io


class CVValidator:
    """
    Computer Vision validator for mesh reconstruction.

    Validates primitive fitting using image-based metrics:
    - SSIM (Structural Similarity Index)
    - Contour matching (Hu moments)
    - Edge detection comparison
    """

    def __init__(self, image_size: int = 256, verbose: bool = False):
        """
        Args:
            image_size: Resolution for rendered images (pixels)
            verbose: Print validation details
        """
        self.image_size = image_size
        self.verbose = verbose

    def polygon_to_image(self, polygon: ShapelyPolygon, normalize: bool = True) -> np.ndarray:
        """
        Render shapely polygon to binary image.

        Args:
            polygon: Shapely polygon
            normalize: Normalize coordinates to fit image

        Returns:
            Binary image (uint8, 0 or 255)
        """
        # Get coordinates
        coords = np.array(polygon.exterior.coords[:-1])

        if normalize:
            # Normalize to fit in image with padding
            min_coords = coords.min(axis=0)
            max_coords = coords.max(axis=0)
            range_coords = max_coords - min_coords

            # Add 10% padding
            padding = 0.1
            scale = (self.image_size * (1 - 2*padding)) / range_coords.max()

            coords_normalized = (coords - min_coords) * scale + self.image_size * padding
            coords = coords_normalized.astype(np.int32)
        else:
            coords = coords.astype(np.int32)

        # Create blank image
        img = np.zeros((self.image_size, self.image_size), dtype=np.uint8)

        # Draw filled polygon
        cv2.fillPoly(img, [coords], 255)

        return img

    def calculate_ssim(
        self,
        polygon_original: ShapelyPolygon,
        polygon_fitted: ShapelyPolygon
    ) -> float:
        """
        Calculate Structural Similarity Index between original and fitted shapes.

        SSIM ranges from -1 to 1, where 1 = perfect match.

        Args:
            polygon_original: Original polygon from mesh cross-section
            polygon_fitted: Fitted primitive polygon

        Returns:
            SSIM score (0-1 range, normalized)
        """
        # Render both to images
        img_orig = self.polygon_to_image(polygon_original)
        img_fitted = self.polygon_to_image(polygon_fitted)

        # Calculate SSIM
        score, _ = ssim(img_orig, img_fitted, full=True)

        # Normalize to 0-1
        score_normalized = (score + 1) / 2

        return score_normalized

    def calculate_contour_similarity(
        self,
        polygon_original: ShapelyPolygon,
        polygon_fitted: ShapelyPolygon
    ) -> float:
        """
        Calculate contour similarity using Hu moments.

        Hu moments are rotation/scale invariant shape descriptors.

        Args:
            polygon_original: Original polygon
            polygon_fitted: Fitted primitive polygon

        Returns:
            Similarity score (0-1, where 1 = perfect match)
        """
        # Render to images
        img_orig = self.polygon_to_image(polygon_original)
        img_fitted = self.polygon_to_image(polygon_fitted)

        # Find contours
        contours_orig, _ = cv2.findContours(img_orig, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_fitted, _ = cv2.findContours(img_fitted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours_orig) == 0 or len(contours_fitted) == 0:
            return 0.0

        # Calculate Hu moments
        moments_orig = cv2.moments(contours_orig[0])
        moments_fitted = cv2.moments(contours_fitted[0])

        hu_orig = cv2.HuMoments(moments_orig).flatten()
        hu_fitted = cv2.HuMoments(moments_fitted).flatten()

        # Log transform for better comparison
        hu_orig = -np.sign(hu_orig) * np.log10(np.abs(hu_orig) + 1e-10)
        hu_fitted = -np.sign(hu_fitted) * np.log10(np.abs(hu_fitted) + 1e-10)

        # Calculate normalized distance
        distance = np.linalg.norm(hu_orig - hu_fitted)

        # Convert to similarity (0-1)
        # Typical good matches have distance < 1.0
        similarity = max(0, 1 - distance / 2.0)

        return similarity

    def calculate_area_overlap(
        self,
        polygon_original: ShapelyPolygon,
        polygon_fitted: ShapelyPolygon
    ) -> float:
        """
        Calculate Intersection over Union (IoU) for area overlap.

        Args:
            polygon_original: Original polygon
            polygon_fitted: Fitted primitive polygon

        Returns:
            IoU score (0-1)
        """
        try:
            intersection = polygon_original.intersection(polygon_fitted).area
            union = polygon_original.union(polygon_fitted).area

            if union == 0:
                return 0.0

            iou = intersection / union
            return iou
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Area overlap calculation failed: {e}")
            return 0.0

    def validate_primitive_fit(
        self,
        polygon_original: ShapelyPolygon,
        primitive_2d: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate how well a fitted primitive matches the original cross-section.

        Args:
            polygon_original: Original polygon from mesh
            primitive_2d: Fitted primitive parameters

        Returns:
            Validation result with metrics and recommendations
        """
        # Reconstruct primitive polygon
        polygon_fitted = self._primitive_to_polygon(primitive_2d)

        if polygon_fitted is None:
            return {
                'valid': False,
                'confidence': 0.0,
                'ssim': 0.0,
                'contour_similarity': 0.0,
                'iou': 0.0,
                'recommendation': 'use_polygon_extrusion'
            }

        # Calculate metrics
        ssim_score = self.calculate_ssim(polygon_original, polygon_fitted)
        contour_sim = self.calculate_contour_similarity(polygon_original, polygon_fitted)
        iou = self.calculate_area_overlap(polygon_original, polygon_fitted)

        # Combined confidence score (weighted average)
        confidence = 0.4 * ssim_score + 0.3 * contour_sim + 0.3 * iou

        # Determine recommendation
        if confidence > 0.85:
            recommendation = 'use_primitive'  # High confidence, use fitted primitive
            valid = True
        elif confidence > 0.70:
            recommendation = 'use_primitive_with_caution'  # Moderate confidence
            valid = True
        elif confidence > 0.50:
            recommendation = 'try_alternative_primitive'  # Low confidence, try different shape
            valid = False
        else:
            recommendation = 'use_polygon_extrusion'  # Very low confidence, use actual polygon
            valid = False

        result = {
            'valid': valid,
            'confidence': confidence,
            'ssim': ssim_score,
            'contour_similarity': contour_sim,
            'iou': iou,
            'recommendation': recommendation,
            'primitive_type': primitive_2d['type']
        }

        if self.verbose:
            print(f"  CV Validation: {primitive_2d['type']}")
            print(f"    SSIM: {ssim_score:.3f}")
            print(f"    Contour: {contour_sim:.3f}")
            print(f"    IoU: {iou:.3f}")
            print(f"    Confidence: {confidence:.3f}")
            print(f"    → {recommendation}")

        return result

    def _primitive_to_polygon(self, primitive_2d: Dict[str, Any]) -> Optional[ShapelyPolygon]:
        """
        Convert fitted primitive parameters back to polygon for comparison.

        Args:
            primitive_2d: Primitive parameters

        Returns:
            Shapely polygon or None if failed
        """
        try:
            center = primitive_2d['center']
            prim_type = primitive_2d['type']

            if prim_type == 'circle':
                radius = primitive_2d['radius']
                # Generate circle points
                theta = np.linspace(0, 2*np.pi, 64, endpoint=False)
                x = center[0] + radius * np.cos(theta)
                y = center[1] + radius * np.sin(theta)
                coords = np.column_stack([x, y])
                return ShapelyPolygon(coords)

            elif prim_type == 'rectangle':
                width = primitive_2d['width']
                height = primitive_2d['height']
                rotation = np.radians(primitive_2d['rotation'])

                # Rectangle corners (centered at origin)
                corners = np.array([
                    [-width/2, -height/2],
                    [width/2, -height/2],
                    [width/2, height/2],
                    [-width/2, height/2]
                ])

                # Rotation matrix
                rot_matrix = np.array([
                    [np.cos(rotation), -np.sin(rotation)],
                    [np.sin(rotation), np.cos(rotation)]
                ])

                # Rotate and translate
                rotated = corners @ rot_matrix.T
                translated = rotated + center

                return ShapelyPolygon(translated)

            elif prim_type == 'ellipse':
                major = primitive_2d['major_axis'] / 2
                minor = primitive_2d['minor_axis'] / 2
                rotation = np.radians(primitive_2d['rotation'])

                # Generate ellipse points
                theta = np.linspace(0, 2*np.pi, 64, endpoint=False)
                x = major * np.cos(theta)
                y = minor * np.sin(theta)

                # Rotation matrix
                rot_matrix = np.array([
                    [np.cos(rotation), -np.sin(rotation)],
                    [np.sin(rotation), np.cos(rotation)]
                ])

                # Rotate and translate
                coords = np.column_stack([x, y])
                rotated = coords @ rot_matrix.T
                translated = rotated + center

                return ShapelyPolygon(translated)

            else:
                return None

        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Primitive to polygon conversion failed: {e}")
            return None

    def visualize_comparison(
        self,
        polygon_original: ShapelyPolygon,
        primitive_2d: Dict[str, Any],
        save_path: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """
        Create visualization comparing original polygon to fitted primitive.

        Args:
            polygon_original: Original polygon
            primitive_2d: Fitted primitive
            save_path: Optional path to save image

        Returns:
            RGB image array or None
        """
        polygon_fitted = self._primitive_to_polygon(primitive_2d)
        if polygon_fitted is None:
            return None

        # Render both
        img_orig = self.polygon_to_image(polygon_original)
        img_fitted = self.polygon_to_image(polygon_fitted)

        # Create RGB visualization
        # Original = blue, Fitted = red, Overlap = magenta
        img_rgb = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
        img_rgb[:, :, 2] = img_orig  # Blue channel = original
        img_rgb[:, :, 0] = img_fitted  # Red channel = fitted

        if save_path:
            cv2.imwrite(save_path, img_rgb)

        return img_rgb


# Convenience function
def validate_reconstruction_cv(
    polygon_original: ShapelyPolygon,
    primitive_2d: Dict[str, Any],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Validate primitive fit using computer vision metrics.

    Args:
        polygon_original: Original cross-section polygon
        primitive_2d: Fitted primitive parameters
        verbose: Print validation details

    Returns:
        Validation result
    """
    validator = CVValidator(verbose=verbose)
    return validator.validate_primitive_fit(polygon_original, primitive_2d)
