#!/usr/bin/env python3
"""
Integration tests for end-to-end pipeline.
"""

import pytest
import json
from pathlib import Path

from core.mesh_loader import MeshLoader
from detection.simple_detector import SimpleDetector
from primitives.box import BoxPrimitive
from primitives.cylinder import CylinderPrimitive
from validation.validator import MeshValidator


class TestPipeline:
    """Test complete conversion pipeline."""

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

    def test_end_to_end_box_pipeline(self, simple_block_path):
        """Test complete box conversion pipeline."""
        # Load
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        # Detect
        detection = SimpleDetector.detect(mesh)
        assert detection['shape_type'] == 'box'

        # Fit
        primitive = BoxPrimitive()
        primitive.fit(mesh)
        assert primitive.fitted

        # Generate
        generated = primitive.generate_mesh()
        assert generated.volume > 0

        # Validate
        validation = MeshValidator.validate_fit(mesh, generated)
        # For hollow box, quality may be lower
        assert validation['quality_score'] > 15

        print(f"✓ Box pipeline: quality={validation['quality_score']:.1f}/100")

    def test_end_to_end_cylinder_pipeline(self, simple_cylinder_path):
        """Test complete cylinder conversion pipeline."""
        # Load
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']

        # Detect
        detection = SimpleDetector.detect(mesh)
        assert detection['shape_type'] == 'cylinder'

        # Fit
        primitive = CylinderPrimitive()
        primitive.fit(mesh)
        assert primitive.fitted

        # Generate
        generated = primitive.generate_mesh()
        assert generated.volume > 0

        # Validate
        validation = MeshValidator.validate_fit(mesh, generated)
        assert validation['quality_score'] > 60

        print(f"✓ Cylinder pipeline: quality={validation['quality_score']:.1f}/100")

    def test_quality_validation_metrics(self, simple_block_path):
        """Test all quality validation metrics."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        primitive = BoxPrimitive()
        primitive.fit(mesh)
        generated = primitive.generate_mesh()

        validation = MeshValidator.validate_fit(mesh, generated)

        # Check all metrics exist and are valid
        required_metrics = [
            'volume_error_percent', 'hausdorff_max_mm', 'hausdorff_mean_mm',
            'hausdorff_relative', 'quality_score', 'quality_level'
        ]
        for metric in required_metrics:
            assert metric in validation, f"Missing metric: {metric}"
            assert validation[metric] is not None

        # Hausdorff distance should be finite
        assert validation['hausdorff_max_mm'] > 0
        assert validation['hausdorff_max_mm'] < 1000

    def test_metadata_export(self, simple_block_path):
        """Test metadata export contains all expected fields."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        primitive = BoxPrimitive()
        primitive.fit(mesh)

        metadata = primitive.export_metadata()

        assert 'type' in metadata
        assert 'fitted' in metadata
        assert 'quality_score' in metadata
        assert 'parameters' in metadata

        # Verify types
        assert isinstance(metadata['fitted'], bool)
        assert isinstance(metadata['quality_score'], (int, float))
