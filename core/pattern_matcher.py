import numpy as np
import trimesh
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class ShapeSignature:
    """Signature for shape matching."""
    name: str
    bbox_ratio_range: Tuple[float, float]
    pca_ratio_range: Tuple[float, float]
    volume_to_surface_range: Tuple[float, float]
    features: Dict[str, Any]


class ShapePatternMatcher:
    """Match mesh components against known primitive signatures."""

    def __init__(self):
        """Initialize with standard primitive signatures."""
        self.signatures = self._build_standard_signatures()

    def _build_standard_signatures(self) -> Dict[str, ShapeSignature]:
        """
        Build reference signatures for standard primitives.

        Returns:
            Dictionary mapping shape names to signatures
        """
        return {
            'cylinder': ShapeSignature(
                name='cylinder',
                bbox_ratio_range=(0.35, 0.90),
                pca_ratio_range=(0.75, 1.35),
                volume_to_surface_range=(1.0, 15.0),
                features={
                    'circular_cross_section': True,
                    'elongated': True,
                    'symmetric': True
                }
            ),
            'solid_box': ShapeSignature(
                name='solid_box',
                bbox_ratio_range=(0.85, 1.10),
                pca_ratio_range=(0.0, 3.0),
                volume_to_surface_range=(2.0, 50.0),
                features={
                    'fills_bbox': True,
                    'rectilinear': True
                }
            ),
            'hollow_box': ShapeSignature(
                name='hollow_box',
                bbox_ratio_range=(0.15, 0.50),
                pca_ratio_range=(0.0, 3.0),
                volume_to_surface_range=(0.1, 5.0),
                features={
                    'thin_walls': True,
                    'rectilinear': True
                }
            ),
            'sphere': ShapeSignature(
                name='sphere',
                bbox_ratio_range=(0.48, 0.56),
                pca_ratio_range=(0.85, 1.15),
                volume_to_surface_range=(1.5, 3.0),
                features={
                    'isotropic': True,
                    'smooth': True
                }
            ),
            'cone': ShapeSignature(
                name='cone',
                bbox_ratio_range=(0.15, 0.35),
                pca_ratio_range=(1.5, 3.0),
                volume_to_surface_range=(0.5, 8.0),
                features={
                    'tapered': True,
                    'elongated': True
                }
            ),
        }

    def match(self, mesh: trimesh.Trimesh) -> Tuple[str, float, Dict[str, Any]]:
        """
        Match mesh against known signatures.

        Args:
            mesh: Input trimesh object

        Returns:
            Tuple of (shape_name, confidence_score, details_dict)
        """
        features = self._extract_features(mesh)
        
        best_match = None
        best_confidence = 0.0
        
        for sig_name, signature in self.signatures.items():
            confidence = self._compute_match_confidence(features, signature)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = sig_name

        details = {
            'features': features,
            'matched_signature': best_match,
            'confidence_score': best_confidence,
            'signatures_compared': len(self.signatures)
        }

        return best_match or 'unknown', best_confidence, details

    def _extract_features(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        Extract signature features from mesh.

        Args:
            mesh: Input trimesh

        Returns:
            Dictionary of extracted features
        """
        if len(mesh.vertices) < 4:
            return {}

        # Volume and surface area
        volume = mesh.volume
        surface_area = mesh.area

        # Bounding box metrics
        bbox = mesh.bounding_box
        bbox_volume = bbox.volume if bbox.volume > 0 else 1e-6
        bbox_ratio = volume / bbox_volume

        # PCA analysis
        vertices_centered = mesh.vertices - mesh.centroid
        if len(vertices_centered) >= 3:
            cov = np.cov(vertices_centered.T)
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = np.sort(eigenvalues)[::-1]  # Descending
            
            if eigenvalues[2] > 1e-6:
                pca_ratio = eigenvalues[1] / eigenvalues[2]
            else:
                pca_ratio = float('inf')

            elongation = eigenvalues[0] / (eigenvalues[1] + 1e-6)
            isotropy = eigenvalues[2] / (eigenvalues[0] + 1e-6)
        else:
            pca_ratio = 0
            elongation = 0
            isotropy = 0

        # Volume to surface ratio (size indicator)
        vs_ratio = volume / (surface_area + 1e-6)

        # Surface smoothness (count low-angle faces)
        face_normals = mesh.face_normals
        face_angles = []
        for edge_pair in mesh.edges_unique:
            faces_on_edge = []
            for fi, face in enumerate(mesh.faces):
                if edge_pair[0] in face and edge_pair[1] in face:
                    faces_on_edge.append(fi)
            
            if len(faces_on_edge) == 2:
                normal1 = face_normals[faces_on_edge[0]]
                normal2 = face_normals[faces_on_edge[1]]
                angle = np.arccos(np.clip(np.dot(normal1, normal2), -1, 1))
                face_angles.append(angle)

        smoothness = float(np.mean(face_angles)) if face_angles else 0

        return {
            'volume': float(volume),
            'surface_area': float(surface_area),
            'bbox_ratio': float(bbox_ratio),
            'pca_ratio': float(pca_ratio),
            'elongation': float(elongation),
            'isotropy': float(isotropy),
            'vs_ratio': float(vs_ratio),
            'smoothness': float(smoothness),
            'vertex_count': len(mesh.vertices),
            'face_count': len(mesh.faces)
        }

    def _compute_match_confidence(
        self,
        features: Dict[str, Any],
        signature: ShapeSignature
    ) -> float:
        """
        Compute match confidence between features and signature.

        Confidence scoring (0-100):
        - 100 = perfect match (all metrics in range)
        - Deductions for each metric outside range
        - Bonus for matching features
        """
        if not features:
            return 0.0

        confidence = 100.0
        metrics_checked = 0

        # Check bbox_ratio
        bbox_ratio = features.get('bbox_ratio', 0)
        if not (signature.bbox_ratio_range[0] <= bbox_ratio <= signature.bbox_ratio_range[1]):
            # Calculate how far outside range
            deviation = min(
                abs(bbox_ratio - signature.bbox_ratio_range[0]),
                abs(bbox_ratio - signature.bbox_ratio_range[1])
            )
            max_range = signature.bbox_ratio_range[1] - signature.bbox_ratio_range[0]
            penalty = min(50, (deviation / max_range) * 50)  # Up to 50 point penalty
            confidence -= penalty
        metrics_checked += 1

        # Check PCA ratio
        pca_ratio = features.get('pca_ratio', 0)
        if not np.isinf(pca_ratio):
            if not (signature.pca_ratio_range[0] <= pca_ratio <= signature.pca_ratio_range[1]):
                deviation = min(
                    abs(pca_ratio - signature.pca_ratio_range[0]),
                    abs(pca_ratio - signature.pca_ratio_range[1])
                )
                max_range = signature.pca_ratio_range[1] - signature.pca_ratio_range[0]
                penalty = min(30, (deviation / max_range) * 30)
                confidence -= penalty
        metrics_checked += 1

        # Check volume-to-surface ratio
        vs_ratio = features.get('vs_ratio', 0)
        if not (signature.volume_to_surface_range[0] <= vs_ratio <= signature.volume_to_surface_range[1]):
            # Less strict penalty for this metric
            confidence -= 10

        # Normalize confidence to 0-100 range
        confidence = max(0, min(100, confidence))

        return confidence


class BatterySignatureMatcher:
    """Specialized matcher for battery-like cylindrical objects."""

    @staticmethod
    def extract_battery_features(mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        Extract features specific to battery-like shapes.

        AA batteries typically have:
        - Circular cylindrical body
        - Terminal contacts (small protrusions)
        - High aspect ratio (length >> radius)
        """
        if len(mesh.vertices) < 100:
            return {}

        vertices_centered = mesh.vertices - mesh.centroid
        cov = np.cov(vertices_centered.T)
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = np.sort(eigenvalues)[::-1]

        # Aspect ratio
        aspect_ratio = eigenvalues[0] / (eigenvalues[2] + 1e-6)

        # Check for high elongation (typical for batteries)
        is_elongated = aspect_ratio > 3.0

        # Radial symmetry (how circular is the cross-section?)
        radial_ratio = eigenvalues[1] / (eigenvalues[2] + 1e-6)
        is_circular = 0.8 <= radial_ratio <= 1.2

        return {
            'aspect_ratio': float(aspect_ratio),
            'is_elongated': bool(is_elongated),
            'radial_ratio': float(radial_ratio),
            'is_circular': bool(is_circular),
            'battery_like': is_elongated and is_circular
        }
