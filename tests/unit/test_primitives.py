#!/usr/bin/env python3
"""
Unit tests for primitive fitting.
"""

import pytest
import numpy as np
from pathlib import Path

from core.mesh_loader import MeshLoader
from primitives.box import BoxPrimitive
from primitives.cylinder import CylinderPrimitive
from validation.validator import MeshValidator


class TestBoxPrimitive:
    """Test box primitive fitting."""

    @pytest.fixture
    def simple_block_path(self):
        """Path to simple_block.stl."""
        sample_dir = Path(__file__).parent / "samples"
        return str(sample_dir / "simple_block.stl")

    def test_fit_box_to_simple_block(self, simple_block_path):
        """Test fitting box to simple_block.stl."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        box = BoxPrimitive()
        box.fit(mesh)

        # Verify fit
        assert box.fitted
        assert box.center is not None
        assert box.extents is not None
        assert all(e > 0 for e in box.extents)
        assert box.volume_ratio > 0

    def test_box_quality_score(self, simple_block_path):
        """Test box quality score calculation."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        box = BoxPrimitive()
        box.fit(mesh)

        # Generate clean mesh and validate
        generated = box.generate_mesh()
        quality = box.calculate_quality_score(mesh)

        assert quality >= 0
        assert quality <= 100
        # For hollow box, quality may be lower since we're fitting solid to hollow
        assert quality > 30, f"Quality too low: {quality}"
        print(f"✓ Box quality score: {quality:.1f}/100")

    def test_box_to_dict(self, simple_block_path):
        """Test box parameter export."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        box = BoxPrimitive()
        box.fit(mesh)
        params = box.to_dict()

        assert 'type' in params
        assert params['type'] == 'box'
        assert 'center' in params
        assert 'extents' in params
        assert 'quality_score' in params

    def test_box_generate_mesh(self, simple_block_path):
        """Test box mesh generation."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        box = BoxPrimitive()
        box.fit(mesh)
        generated = box.generate_mesh()

        assert generated is not None
        assert generated.volume > 0
        assert len(generated.vertices) > 0
        assert len(generated.faces) > 0

    def test_box_cadquery_script(self, simple_block_path):
        """Test CadQuery script generation."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']

        box = BoxPrimitive()
        box.fit(mesh)
        script = box.generate_cadquery_script()

        assert script is not None
        assert 'cadquery' in script.lower()
        assert 'box' in script.lower()


class TestCylinderPrimitive:
    """Test cylinder primitive fitting."""

    @pytest.fixture
    def simple_cylinder_path(self):
        """Path to simple_cylinder.stl."""
        sample_dir = Path(__file__).parent / "samples"
        return str(sample_dir / "simple_cylinder.stl")

    def test_fit_cylinder_to_simple_cylinder(self, simple_cylinder_path):
        """Test fitting cylinder to simple_cylinder.stl."""
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']

        cylinder = CylinderPrimitive()
        cylinder.fit(mesh)

        # Verify fit
        assert cylinder.fitted
        assert cylinder.center is not None
        assert cylinder.axis is not None
        assert cylinder.radius > 0
        assert cylinder.length > 0

    def test_cylinder_pca_ratio(self, simple_cylinder_path):
        """Test cylinder PCA ratio."""
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']

        cylinder = CylinderPrimitive()
        cylinder.fit(mesh)

        # For true cylinder, PCA ratio should be close to 1.0
        # (PC2 ≈ PC3, ratio of eigenvalues ≈ 1)
        assert 0.5 < cylinder.pca_ratio < 1.5, \
            f"PCA ratio suggests non-cylinder: {cylinder.pca_ratio}"
        print(f"✓ Cylinder PCA ratio: {cylinder.pca_ratio:.3f}")

    def test_cylinder_quality_score(self, simple_cylinder_path):
        """Test cylinder quality score."""
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']

        cylinder = CylinderPrimitive()
        cylinder.fit(mesh)

        generated = cylinder.generate_mesh()
        quality = cylinder.calculate_quality_score(mesh)

        assert quality >= 0
        assert quality <= 100
        assert quality > 60, f"Quality too low: {quality}"
        print(f"✓ Cylinder quality score: {quality:.1f}/100")

    def test_cylinder_to_dict(self, simple_cylinder_path):
        """Test cylinder parameter export."""
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']

        cylinder = CylinderPrimitive()
        cylinder.fit(mesh)
        params = cylinder.to_dict()

        assert 'type' in params
        assert params['type'] == 'cylinder'
        assert 'radius' in params
        assert 'length' in params
        assert params['radius'] > 0
        assert params['length'] > 0

    def test_cylinder_generate_mesh(self, simple_cylinder_path):
        """Test cylinder mesh generation."""
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']

        cylinder = CylinderPrimitive()
        cylinder.fit(mesh)
        generated = cylinder.generate_mesh()

        assert generated is not None
        assert generated.volume > 0
        assert len(generated.vertices) > 0
        assert len(generated.faces) > 0

    def test_cylinder_axis_is_unit_vector(self, simple_cylinder_path):
        """Test cylinder axis is a unit vector."""
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']

        cylinder = CylinderPrimitive()
        cylinder.fit(mesh)

        axis_norm = np.linalg.norm(cylinder.axis)
        assert 0.99 < axis_norm < 1.01, \
            f"Axis not unit vector: norm={axis_norm}"
