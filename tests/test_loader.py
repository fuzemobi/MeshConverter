#!/usr/bin/env python3
"""
Unit tests for mesh loading and utilities.
"""

import pytest
import tempfile
import numpy as np
from pathlib import Path
import trimesh

from core.mesh_loader import MeshLoader
from core.bbox_utils import (
    calculate_bbox_ratio,
    get_bbox_extents,
    get_obb_properties,
    get_mesh_stats
)


class TestMeshLoader:
    """Test mesh loading utilities."""

    @pytest.fixture
    def sample_dir(self):
        """Get path to sample files."""
        return Path(__file__).parent / "samples"

    @pytest.fixture
    def simple_block_path(self, sample_dir):
        """Path to simple_block.stl."""
        return str(sample_dir / "simple_block.stl")

    @pytest.fixture
    def simple_cylinder_path(self, sample_dir):
        """Path to simple_cylinder.stl."""
        return str(sample_dir / "simple_cylinder.stl")

    def test_load_simple_block(self, simple_block_path):
        """Test loading simple_block.stl."""
        result = MeshLoader.load(simple_block_path)
        assert result is not None
        assert 'mesh' in result
        assert 'filepath' in result
        assert result['mesh'].volume > 0

    def test_load_simple_cylinder(self, simple_cylinder_path):
        """Test loading simple_cylinder.stl."""
        result = MeshLoader.load(simple_cylinder_path)
        assert result is not None
        assert 'mesh' in result
        assert result['mesh'].volume > 0

    def test_load_nonexistent_file(self):
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            MeshLoader.load("/nonexistent/file.stl")

    def test_load_invalid_extension(self):
        """Test loading non-STL file."""
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            with pytest.raises(ValueError):
                MeshLoader.load(f.name)

    def test_validate_mesh(self, simple_block_path):
        """Test mesh validation."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']
        validation = MeshLoader.validate_mesh(mesh)

        assert validation['is_valid']
        assert validation['volume'] > 0
        assert validation['vertices_count'] > 0
        assert validation['faces_count'] > 0


class TestBboxUtils:
    """Test bounding box utilities."""

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

    def test_bbox_ratio_block(self, simple_block_path):
        """Test bbox ratio on hollow block."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']
        ratio = calculate_bbox_ratio(mesh)

        # Hollow block should have low ratio
        assert 0.1 < ratio < 0.6, f"Expected hollow box ratio, got {ratio}"
        print(f"✓ simple_block bbox_ratio: {ratio:.3f}")

    def test_bbox_ratio_cylinder(self, simple_cylinder_path):
        """Test bbox ratio on cylinder."""
        result = MeshLoader.load(simple_cylinder_path)
        mesh = result['mesh']
        ratio = calculate_bbox_ratio(mesh)

        # Cylinder should have ratio ~0.4-0.85
        assert 0.3 < ratio < 1.0, f"Expected cylinder ratio, got {ratio}"
        print(f"✓ simple_cylinder bbox_ratio: {ratio:.3f}")

    def test_get_bbox_extents(self, simple_block_path):
        """Test getting bbox extents."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']
        extents = get_bbox_extents(mesh)

        assert len(extents) == 3
        assert all(e > 0 for e in extents)

    def test_get_obb_properties(self, simple_block_path):
        """Test getting OBB properties."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']
        props = get_obb_properties(mesh)

        assert 'center' in props
        assert 'extents' in props
        assert 'transform' in props
        assert 'volume' in props
        assert props['volume'] > 0

    def test_get_mesh_stats(self, simple_block_path):
        """Test getting comprehensive mesh stats."""
        result = MeshLoader.load(simple_block_path)
        mesh = result['mesh']
        stats = get_mesh_stats(mesh)

        required_keys = [
            'volume', 'surface_area', 'vertices_count', 'faces_count',
            'bbox_ratio', 'bbox_extents', 'is_watertight'
        ]
        for key in required_keys:
            assert key in stats, f"Missing key: {key}"

        assert stats['volume'] > 0
        assert stats['vertices_count'] > 0
        assert stats['faces_count'] > 0
