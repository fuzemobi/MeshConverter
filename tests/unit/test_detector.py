#!/usr/bin/env python3
"""
Unit tests for shape detection.
"""

import pytest
from pathlib import Path

from core.mesh_loader import MeshLoader
from detection.simple_detector import SimpleDetector
from core.bbox_utils import calculate_bbox_ratio


class TestSimpleDetector:
    """Test simple heuristic shape detector."""

    @pytest.fixture
    def simple_block_path(self):
        """Path to simple_block.stl."""
        sample_dir = Path(__file__).parent / "samples"
        return str(sample_dir / "simple_block.stl")

    @pytest.fixture
    def simple_cylinder_path(self):
        """Path to simple_cylinder.stl."""
        sample_dir = Path(__file__).parent / "samples"
        return str(sample_dir / "simple_cylinder.stl")

    def test_detect_box(self, simple_block_path):
        """Test detecting box shape."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        detection = SimpleDetector.detect(mesh)

        assert detection['shape_type'] == 'box'
        assert detection['confidence'] > 0
        print(f"✓ Detected box with confidence: {detection['confidence']}%")

    def test_detect_cylinder(self, simple_cylinder_path):
        """Test detecting cylinder shape."""
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']

        detection = SimpleDetector.detect(mesh)

        assert detection['shape_type'] == 'cylinder'
        assert detection['confidence'] > 0
        print(f"✓ Detected cylinder with confidence: {detection['confidence']}%")

    def test_detection_has_required_fields(self, simple_block_path):
        """Test detection result has required fields."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        detection = SimpleDetector.detect(mesh)

        required_fields = ['shape_type', 'confidence', 'reason', 'bbox_ratio', 'stats']
        for field in required_fields:
            assert field in detection, f"Missing field: {field}"

    def test_bbox_ratio_classification(self):
        """Test bbox ratio classification thresholds."""
        # Test known bbox ratios
        shape, conf = SimpleDetector._classify_by_bbox_ratio(0.97)  # Solid box
        assert shape == 'box'
        assert conf >= 90

        shape, conf = SimpleDetector._classify_by_bbox_ratio(0.52)  # Sphere
        assert shape == 'sphere'
        assert conf >= 80

        shape, conf = SimpleDetector._classify_by_bbox_ratio(0.60)  # Cylinder
        assert shape == 'cylinder'
        assert conf >= 75

        shape, conf = SimpleDetector._classify_by_bbox_ratio(0.25)  # Hollow box or cone
        assert shape in ['box', 'cone']

    def test_confidence_scores(self, simple_block_path):
        """Test confidence scores are in valid range."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        detection = SimpleDetector.detect(mesh)

        assert 0 <= detection['confidence'] <= 100
