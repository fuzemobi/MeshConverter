# MeshConverter V2 - Claude Code Standards

**Version:** 2.0.0
**Date:** 2026-01-17
**Project Type:** Python 3D Mesh Analysis & CAD Conversion Tool

---

## Project Overview

MeshConverter V2 is a complete rewrite of the mesh-to-CAD converter with a focus on:
- **Multi-primitive detection** (box, cylinder, sphere, cone, not just cylinder)
- **Robust algorithms** (PCA, oriented bounding boxes, Hausdorff distance validation)
- **Production-ready architecture** (modular, tested, documented)
- **Medical device focus** (accuracy, validation, HIPAA-ready metadata)

**Key Insight from V1 Failures:**
> "The current approach assumes every mesh is a cylinder. This is fundamentally wrong.
> Medical devices are ASSEMBLIES of multiple primitives. We need hierarchical decomposition,
> multi-hypothesis testing, and validation at every stage."

---

## 🎯 Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.8+ | Core language |
| **Mesh Processing** | trimesh | latest | Mesh loading & manipulation |
| **Numerical** | numpy | latest | Matrix operations |
| **ML/Analysis** | scikit-learn | latest | PCA, clustering |
| **Geometry** | scipy | latest | Spatial transformations |
| **Simplification** | fast-simplification | latest | Quadric decimation |
| **CAD Generation** | cadquery | 2.x | Parametric CAD scripting |
| **Config** | PyYAML | latest | Configuration management |
| **Testing** | pytest | latest | Unit & integration tests |

---

## 📐 Mathematical Foundation

### Bounding Box Ratio - The Key Metric

**Formula:** `bbox_ratio = mesh_volume / bounding_box_volume`

**Why it works:**

| Shape | Theoretical Ratio | Formula | Real Range |
|-------|-------------------|---------|------------|
| **Solid Box** | 1.0 | V/V = 1 | 0.95-1.05 |
| **Hollow Box** | 0.2-0.4 | Thin walls | 0.15-0.40 |
| **Cylinder** | 0.7854 (π/4) | πr²h/(2r)²h = π/4 | 0.40-0.85 |
| **Sphere** | 0.5236 (π/6) | (4/3πr³)/(2r)³ = π/6 | 0.50-0.55 |
| **Cone** | 0.2618 (π/12) | (1/3πr²h)/(2r)²h = π/12 | 0.20-0.30 |

**Empirical Validation (from V1 testing):**
- `simple_block.stl` → 0.297 → **Hollow Box** ✅
- `simple_cylinder.stl` → 0.426 → **Cylinder** ✅
- `sample.stl` → 0.300 → **Complex/Hollow** ✅

### PCA for Cylinder Detection

**Principal Component Analysis reveals natural axes of variation:**

```python
# For a true cylinder:
PC1 >> PC2 ≈ PC3  # One long axis, two equal short axes

# Validation check:
pca_ratio = eigenvalues[1] / eigenvalues[2]
is_cylinder = 0.8 <= pca_ratio <= 1.2  # Circular cross-section
```

**Why this works:**
- PC1 = cylinder axis (direction of maximum variation)
- PC2, PC3 = radius directions (perpendicular, equal magnitude)
- Non-circular cross-sections → PC2 ≠ PC3

---

## 🏗️ Architecture

### Core Principles

1. **No Assumptions** - Test multiple hypotheses, choose best fit
2. **Validation Always** - Measure quality at every stage
3. **Modular Design** - Each component testable independently
4. **Medical-Grade** - Accuracy targets: <5% volume error, >80 quality score

### Pipeline Stages

```
[1] Mesh Loading & Cleaning
    └─ Repair normals, fill holes, remove duplicates
    └─ Calculate statistics (volume, bbox_ratio, etc.)
    └─ Validate mesh quality

[2] Normalization (optional but recommended)
    └─ Center at origin
    └─ Scale to [-1, 1] (isotropic or anisotropic)
    └─ Store transform for reverse conversion

[3] Shape Detection
    └─ Calculate bbox_ratio
    └─ Compare against thresholds
    └─ Route to appropriate primitive fitter

[4] Primitive Fitting
    ├─ Box: Oriented bounding box
    ├─ Cylinder: PCA-based axis detection
    ├─ Sphere: Least squares fitting
    └─ Cone: Apex + base detection

[5] Quality Validation
    └─ Hausdorff distance (max deviation)
    └─ Volume error (percentage)
    └─ Quality score (0-100)

[6] Export
    ├─ Simplified STL mesh
    ├─ CadQuery Python script
    ├─ Metadata JSON
    └─ STEP file (future)
```

---

## 📁 File Structure

```
v2/
├── CLAUDE.md                   # This file
├── README.md                   # User documentation
├── config.yaml                 # Configuration
├── requirements.txt            # Python dependencies
│
├── core/                       # Core infrastructure
│   ├── __init__.py
│   ├── mesh_loader.py          # Load, clean, repair meshes
│   ├── normalizer.py           # Normalize to canonical space
│   └── bbox_utils.py           # Bounding box calculations
│
├── primitives/                 # Geometric primitives
│   ├── __init__.py
│   ├── base.py                 # Abstract Primitive class
│   ├── box.py                  # Box primitive (OBB-based)
│   ├── cylinder.py             # Cylinder primitive (PCA-based)
│   ├── sphere.py               # Sphere primitive
│   └── cone.py                 # Cone primitive
│
├── detection/                  # Shape detection
│   ├── __init__.py
│   └── simple_detector.py      # Heuristic bbox_ratio detector
│
├── validation/                 # Quality validation
│   ├── __init__.py
│   └── validator.py            # Hausdorff, volume error, quality score
│
├── mesh_to_primitives.py       # Main CLI script
│
├── tests/                      # Unit tests
│   ├── __init__.py
│   ├── test_loader.py
│   ├── test_primitives.py
│   └── test_detector.py
│
├── output/                     # Generated outputs
└── docs/                       # Additional documentation
    ├── IMPLEMENTATION_PLAN.md  # Detailed implementation steps
    └── ARCHITECTURE.md         # System architecture deep dive
```

---

## 🔧 Implementation Standards

### Code Quality Requirements

✅ **MANDATORY:**
- Type hints for all function signatures
- Docstrings (Google style) for all public functions
- Unit tests for all primitives
- Integration tests for full pipeline
- PEP 8 compliance (use black formatter)
- No magic numbers (use named constants)

### Example: Proper Function Signature

```python
#!/usr/bin/env python3
"""
Box primitive using Oriented Bounding Box
"""

import trimesh
import numpy as np
from typing import Dict, Any, Tuple
from .base import Primitive


class BoxPrimitive(Primitive):
    """
    Rectangular box primitive (solid or hollow).

    Uses oriented bounding box (OBB) for best fit,
    which handles rotated boxes correctly.
    """

    def __init__(self) -> None:
        super().__init__()
        self.center: np.ndarray = None
        self.extents: np.ndarray = None  # [length, width, height]
        self.transform: np.ndarray = None  # 4x4 transformation matrix
        self.is_hollow: bool = False

    def fit(self, mesh: trimesh.Trimesh) -> 'BoxPrimitive':
        """
        Fit oriented bounding box to mesh.

        Args:
            mesh: Input mesh to fit box to

        Returns:
            self (for method chaining)

        Raises:
            ValueError: If mesh is invalid or empty
        """
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("mesh must be trimesh.Trimesh instance")

        if len(mesh.vertices) < 4:
            raise ValueError("Mesh must have at least 4 vertices")

        # Implementation...
        return self
```

### Error Handling

```python
# Good error handling
try:
    mesh = trimesh.load(filepath)
except FileNotFoundError:
    print(f"❌ File not found: {filepath}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error loading mesh: {e}")
    sys.exit(1)

# Validate before processing
if not mesh.is_watertight:
    print("⚠️  Warning: Mesh is not watertight. Results may be inaccurate.")

if mesh.volume <= 0:
    print("❌ Error: Mesh has non-positive volume. Cannot process.")
    sys.exit(1)
```

---

## 🧪 Testing Requirements

### Unit Tests

**Every primitive must have tests:**

```python
# tests/test_box.py

import pytest
import trimesh
import numpy as np
from primitives.box import BoxPrimitive


def test_box_fit_on_cube():
    """Test box fitting on perfect cube"""
    # Create perfect cube
    cube = trimesh.creation.box(extents=[10, 10, 10])

    # Fit box
    box = BoxPrimitive()
    box.fit(cube)

    # Validate dimensions
    assert np.allclose(box.extents, [10, 10, 10], atol=0.1)
    assert box.is_hollow == False  # Solid cube

    # Validate quality
    quality = box.calculate_quality_score(cube)
    assert quality > 95  # Should be near-perfect

def test_box_fit_on_hollow_box():
    """Test box fitting on hollow box"""
    # Create hollow box (shell)
    outer = trimesh.creation.box(extents=[20, 15, 10])
    inner = trimesh.creation.box(extents=[18, 13, 8])
    hollow = outer.difference(inner)

    # Fit box
    box = BoxPrimitive()
    box.fit(hollow)

    # Should detect as hollow
    assert box.is_hollow == True

    # Dimensions should match outer box
    assert np.allclose(box.extents, [20, 15, 10], atol=0.5)
```

### Integration Tests

```python
# tests/test_pipeline.py

def test_end_to_end_cylinder():
    """Test full pipeline on cylinder"""
    from core.mesh_loader import MeshLoader
    from detection.simple_detector import SimpleDetector

    # Load
    loader = MeshLoader(config)
    result = loader.load('simple_cylinder.stl')

    # Detect
    detector = SimpleDetector(config)
    primitive, shape_type, confidence = detector.detect(
        result['mesh'],
        result['stats']
    )

    # Assertions
    assert shape_type == 'cylinder'
    assert confidence > 0.7
    assert primitive.quality_score > 80
```

---

## 📊 Performance Targets

| Operation | Target Time | Max Memory | Status |
|-----------|-------------|------------|--------|
| Load 100k vertex mesh | <1s | <100MB | ✅ |
| Calculate bbox ratio | <0.1s | <50MB | ✅ |
| PCA analysis | <2s | <200MB | ✅ |
| Simplify mesh (100k→1k faces) | <5s | <500MB | ✅ |
| Full pipeline | <15s | <1GB | 🎯 Target |

---

## 🎓 Key Algorithms Explained

### Algorithm 1: Oriented Bounding Box for Boxes

```python
def fit_box_to_mesh(mesh: trimesh.Trimesh) -> Dict[str, Any]:
    """
    Fit oriented bounding box to mesh.

    Why OBB vs AABB?
    - OBB handles rotated boxes correctly
    - AABB (axis-aligned) fails on tilted objects

    Returns:
        Dict with center, extents, transform, is_hollow
    """
    # Get oriented bounding box (built into trimesh)
    obb = mesh.bounding_box_oriented

    # Extract parameters
    center = obb.centroid
    extents = obb.extents  # [length, width, height]
    transform = obb.primitive.transform  # 4x4 rotation+translation

    # Detect hollow vs solid
    bbox_volume = obb.volume
    mesh_volume = mesh.volume
    volume_ratio = mesh_volume / bbox_volume if bbox_volume > 0 else 0

    is_hollow = volume_ratio < 0.5  # Heuristic threshold

    return {
        'center': center,
        'extents': extents,
        'transform': transform,
        'is_hollow': is_hollow,
        'volume_ratio': volume_ratio
    }
```

### Algorithm 2: PCA-Based Cylinder Fitting

```python
def fit_cylinder_to_mesh(mesh: trimesh.Trimesh) -> Dict[str, Any]:
    """
    Fit cylinder using PCA for axis detection.

    PCA reveals principal axes of variation:
    - PC1: Longest axis → cylinder axis
    - PC2, PC3: Perpendicular axes → radius directions

    For true cylinder: PC1 >> PC2 ≈ PC3
    """
    from sklearn.decomposition import PCA

    vertices = mesh.vertices
    center = vertices.mean(axis=0)
    centered = vertices - center

    # Apply PCA
    pca = PCA(n_components=3)
    pca.fit(centered)

    # Extract axis (first principal component)
    axis = pca.components_[0]
    eigenvalues = pca.explained_variance_

    # Validate cylinder assumption
    pca_ratio = eigenvalues[1] / eigenvalues[2]
    if not (0.8 <= pca_ratio <= 1.2):
        print(f"⚠️  Warning: Non-circular cross-section (ratio={pca_ratio:.2f})")

    # Project vertices onto principal axes
    projected = pca.transform(centered)

    # Calculate length (range along axis)
    length = projected[:, 0].max() - projected[:, 0].min()

    # Calculate radius (distance from axis)
    perpendicular_distances = np.sqrt(projected[:, 1]**2 + projected[:, 2]**2)
    radius = np.median(perpendicular_distances)  # Median is robust to outliers

    return {
        'center': center,
        'axis': axis,
        'radius': radius,
        'length': length,
        'pca_ratio': pca_ratio
    }
```

### Algorithm 3: Hausdorff Distance for Validation

```python
def calculate_hausdorff_distance(
    mesh1: trimesh.Trimesh,
    mesh2: trimesh.Trimesh,
    num_samples: int = 10000
) -> Tuple[float, float]:
    """
    Calculate Hausdorff distance between two meshes.

    Hausdorff distance = max deviation between surfaces

    Returns:
        (max_distance, mean_distance)
    """
    from scipy.spatial import cKDTree

    # Sample points from both meshes
    points1 = mesh1.sample(num_samples)
    points2 = mesh2.sample(num_samples)

    # Build KD-trees for fast nearest-neighbor search
    tree1 = cKDTree(points1)
    tree2 = cKDTree(points2)

    # Distance from mesh1 to mesh2
    distances_1_to_2 = tree2.query(points1)[0]

    # Distance from mesh2 to mesh1
    distances_2_to_1 = tree1.query(points2)[0]

    # Hausdorff = max of both directions
    max_distance = max(distances_1_to_2.max(), distances_2_to_1.max())

    # Mean distance (average deviation)
    mean_distance = (distances_1_to_2.mean() + distances_2_to_1.mean()) / 2

    return max_distance, mean_distance
```

---

## 🚀 Development Workflow

### Step 1: Setup

```bash
cd v2
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_box.py::test_box_fit_on_cube -v

# Run with coverage
pytest --cov=. tests/
```

### Step 3: Test on Real Data

```bash
# Test on examples
python mesh_to_primitives.py ../simple_block.stl -o output/block
python mesh_to_primitives.py ../simple_cylinder.stl -o output/cylinder

# Expected output:
# simple_block.stl → BOX (hollow), quality: 90+/100
# simple_cylinder.stl → CYLINDER, quality: 90+/100
```

### Step 4: Code Quality

```bash
# Format code
black .

# Type checking
mypy mesh_to_primitives.py

# Linting
pylint primitives/ core/ detection/
```

---

## 🎯 Success Criteria

### Must Pass Before Merge

- [ ] All unit tests passing
- [ ] simple_block.stl detected as BOX (not cylinder!)
- [ ] simple_cylinder.stl detected as CYLINDER
- [ ] Quality scores >80/100 for both
- [ ] Volume error <10% for both
- [ ] CadQuery scripts generated and valid
- [ ] Documentation complete (this file + README)
- [ ] Code formatted with black
- [ ] No pylint errors (warnings acceptable)

### Quality Metrics

```python
# Quality score calculation
quality_score = 100 * (1 - volume_error) * (1 - normalized_fit_error)

# Acceptance criteria
if quality_score >= 90:
    print("✅ Excellent quality")
elif quality_score >= 80:
    print("✅ Good quality")
elif quality_score >= 60:
    print("⚠️  Acceptable quality")
else:
    print("❌ Poor quality - needs refinement")
```

---

## 📚 References

### Internal Documentation
- [README.md](README.md) - User guide and quick start
- [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) - Detailed implementation steps
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture deep dive

### External Resources
- [trimesh documentation](https://trimsh.org/)
- [CadQuery tutorial](https://cadquery.readthedocs.io/)
- [scikit-learn PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)
- [STEP file format (ISO 10303)](https://en.wikipedia.org/wiki/ISO_10303)

### Academic References
- Quadric decimation: Garland & Heckbert (1997)
- PCA for shape analysis: Jolliffe (2002)
- Hausdorff distance: Rockafellar & Wets (1998)

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-01-17 | Complete rewrite with multi-primitive support |
| 1.1.0 | 2026-01-17 | Added AI classification, few-shot learning |
| 1.0.0 | 2026-01-15 | Initial cylinder-only implementation |

---

**This is production-grade medical device software. Quality and accuracy are paramount.**
