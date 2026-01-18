# Quick Start: Multi-Segment Reconstruction

**Phase 4A: Layer-Wise Primitive Stacking with CV Validation**

---

## Overview

Multi-segment reconstruction allows you to convert complex assemblies (batteries, sensors, multi-part devices) into multiple primitive segments instead of forcing them into a single shape.

---

## Installation

### 1. Install Dependencies

```bash
# Navigate to project root
cd MeshConverter_v2

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install CV dependencies (if not already installed)
pip install opencv-python>=4.8.0 scikit-image>=0.21.0 mapbox-earcut>=1.0.0
```

### 2. Verify Installation

```bash
python -c "import cv2, skimage, earcut; print('✅ All dependencies installed')"
```

---

## Usage Methods

### Method 1: Standalone Script (Recommended for Testing)

```bash
# Basic usage
python scripts/demo_multisegment_reconstruction.py <mesh.stl>

# Example
python scripts/demo_multisegment_reconstruction.py tests/samples/simple_block.stl
```

**Output:**
- Segment breakdown with parameters
- Quality score and volume error
- CV validation confidence scores
- Reconstructed mesh saved to `output/demo/`
- Visual comparison report (PNG)

### Method 2: Direct Python API

```python
import trimesh
from meshconverter.reconstruction.layer_wise_stacker import LayerWiseStacker

# Load mesh
mesh = trimesh.load('battery.stl')

# Create stacker with CV validation enabled
stacker = LayerWiseStacker(
    layer_height=0.5,              # 0.5mm layer spacing
    min_segment_height=2.0,        # Minimum 2mm per segment
    use_cv_validation=True,        # Enable CV metrics
    cv_confidence_threshold=0.70,  # 70% confidence threshold
    verbose=True                   # Print progress
)

# Reconstruct
result = stacker.reconstruct(mesh)

# Check results
print(f"Segments: {result['num_segments']}")
print(f"Quality: {result['quality_score']}/100")
print(f"Volume Error: {result.get('volume_error', 0)*100:.2f}%")

# Access reconstructed mesh
reconstructed_mesh = result['reconstructed_mesh']
reconstructed_mesh.export('battery_reconstructed.stl')

# Access segment details
for i, seg in enumerate(result['segments'], 1):
    prim = seg['primitive_2d']
    print(f"Segment {i}: {prim['type'].upper()}")
    print(f"  Height: {seg['height']:.1f}mm")
    if prim['type'] == 'circle':
        print(f"  Radius: {prim['radius']:.2f}mm")
```

### Method 3: Main CLI (Integrated)

```bash
# Use layer-slicing classifier
python meshconverter/cli.py battery.stl --classifier layer-slicing --layer-height 0.5

# Compare all methods
python meshconverter/cli.py battery.stl --classifier all
```

---

## Configuration Options

### LayerWiseStacker Parameters

```python
LayerWiseStacker(
    layer_height=0.5,              # Slice spacing (mm)
                                   # Smaller = more detail, slower
                                   # Typical: 0.2-1.0mm

    min_segment_height=2.0,        # Minimum segment height (mm)
                                   # Filters out noise/artifacts
                                   # Typical: 1.0-5.0mm

    use_cv_validation=True,        # Enable CV quality metrics
                                   # True = better quality, 60% slower
                                   # False = faster, less accurate

    cv_confidence_threshold=0.70,  # Confidence cutoff (0-1)
                                   # >0.70 = use fitted primitive
                                   # <0.70 = use polygon extrusion
                                   # Lower = more polygon extrusion

    verbose=True                   # Print progress messages
)
```

### When to Adjust Parameters

**Layer Height:**
- **Decrease (0.2-0.3mm):** Fine details, gradual transitions
- **Increase (1.0-2.0mm):** Coarse features, faster processing

**Min Segment Height:**
- **Decrease (1.0mm):** Capture small features (threads, grooves)
- **Increase (5.0mm):** Ignore noise, focus on major sections

**CV Threshold:**
- **Lower (0.60):** More aggressive hollow detection, more polygon extrusion
- **Higher (0.80):** Prefer fitted primitives, accept some error

---

## Example Workflows

### Workflow 1: Battery (6 Segments)

```bash
# Create test case (if needed)
python scripts/create_battery_test_case.py

# Reconstruct
python scripts/demo_multisegment_reconstruction.py \
    tests/samples/realistic_battery_6segments.stl
```

**Expected Output:**
```
✅ Reconstruction Complete!

📊 Summary:
   - Segments: 4-6
   - Quality Score: 90+/100
   - Volume Error: <10%

📋 Segment Breakdown:
   Segment 1: CYLINDER (R=2.5mm, H=1.5mm) - Bottom terminal
   Segment 2: CYLINDER (R=9.5mm, H=1.0mm) - Negative cap
   Segment 3: CYLINDER (R=9.0mm, H=50mm) - Battery body
   ...
```

### Workflow 2: Hollow Block

```bash
python scripts/demo_multisegment_reconstruction.py \
    tests/samples/simple_block.stl
```

**Expected Output:**
```
✅ Reconstruction Complete!

📊 Summary:
   - Segments: 3
   - Quality Score: 78/100
   - Volume Error: 21.59%

📋 Segment Breakdown:
   Segment 1: CIRCLE (using polygon extrusion - low confidence)
   Segment 2: RECTANGLE (using polygon extrusion - hollow detected)
   Segment 3: RECTANGLE (fitted primitive - high confidence)
```

### Workflow 3: Visual Comparison

```bash
# Generate comparison reports for multiple test cases
python scripts/test_visual_comparison.py

# Output saved to:
# - output/block_comparison_report.png
# - output/battery_comparison_report.png
```

---

## Understanding Output

### Segment Information

Each segment contains:
```python
{
    'z_start': 0.0,           # Bottom Z coordinate (mm)
    'z_end': 10.0,            # Top Z coordinate (mm)
    'height': 10.0,           # Segment height (mm)
    'shape': 'circle',        # Detected shape type
    'primitive_2d': {         # 2D primitive parameters
        'type': 'circle',
        'center': [0, 0],
        'radius': 5.0,
        'cv_validation': {    # CV quality metrics
            'confidence': 0.85,
            'ssim': 0.92,
            'iou': 0.88,
            'contour_similarity': 0.75
        },
        'use_polygon_extrusion': False  # Strategy flag
    },
    'layers': [...]           # Individual layer data
}
```

### Quality Metrics

**Quality Score (0-100):**
- 90-100: Excellent (production-ready)
- 80-89: Good (acceptable for most uses)
- 60-79: Fair (review carefully)
- <60: Poor (manual inspection recommended)

**Volume Error:**
- <5%: Excellent match
- 5-10%: Good match
- 10-25%: Acceptable for hollow structures
- >25%: Investigate (likely wrong primitive type)

**CV Confidence (0-1):**
- >0.85: High confidence → Use fitted primitive
- 0.70-0.85: Medium confidence → Use with caution
- 0.50-0.70: Low confidence → Try alternative
- <0.50: Very low confidence → Use polygon extrusion

---

## Troubleshooting

### Issue: Too Many Segments (Over-Segmentation)

**Symptoms:** 10+ segments for simple object

**Solutions:**
```python
# Increase minimum segment height
stacker = LayerWiseStacker(
    min_segment_height=5.0  # Increased from 2.0
)

# Increase layer height (less granular)
stacker = LayerWiseStacker(
    layer_height=1.0  # Increased from 0.5
)
```

### Issue: Too Few Segments (Under-Segmentation)

**Symptoms:** Battery showing as 1 segment instead of 6

**Solutions:**
```python
# Decrease layer height (more granular)
stacker = LayerWiseStacker(
    layer_height=0.3  # Decreased from 0.5
)

# Fine-tune fuzzy logic thresholds (advanced)
# This requires editing layer_wise_stacker.py
# See docs/PHASE_4A_CV_ENHANCEMENT.md for details
```

### Issue: Hollow Structures Showing as Solid

**Symptoms:** Volume error >20%, reconstructed mesh oversized

**Solutions:**
```python
# Lower CV threshold to trigger more polygon extrusion
stacker = LayerWiseStacker(
    cv_confidence_threshold=0.60  # Decreased from 0.70
)
```

### Issue: CV Validation Not Running

**Symptoms:** All confidence scores show 0.0

**Check:**
```bash
# Verify OpenCV installed
python -c "import cv2; print(cv2.__version__)"

# Verify scikit-image installed
python -c "import skimage; print(skimage.__version__)"

# Check if CV is available
python -c "from meshconverter.validation.cv_validator import CVValidator; print('✅ CV Available')"
```

### Issue: Hu Moments Always 0

**Status:** Known issue (OpenCV compatibility)

**Impact:** Contour similarity metric not contributing to confidence

**Workaround:** SSIM + IoU still provide reliable validation

**Fix Plan:** Next release (v1.1)

---

## Performance Tuning

### For Speed (Sacrifice Quality)

```python
stacker = LayerWiseStacker(
    layer_height=1.0,              # Coarser slicing
    use_cv_validation=False,       # Disable CV (60% faster)
    verbose=False                  # Less console output
)
```

**Expected:** ~5s for 100-layer mesh

### For Quality (Sacrifice Speed)

```python
stacker = LayerWiseStacker(
    layer_height=0.3,              # Finer slicing
    use_cv_validation=True,        # Enable CV
    cv_confidence_threshold=0.60,  # More polygon extrusion
    verbose=True
)
```

**Expected:** ~12s for 100-layer mesh

### Balanced (Production)

```python
stacker = LayerWiseStacker(
    layer_height=0.5,              # Default
    use_cv_validation=True,        # Default
    cv_confidence_threshold=0.70,  # Default
    verbose=False
)
```

**Expected:** ~8s for 100-layer mesh

---

## Testing Your Meshes

### Quick Test

```bash
# Test on your mesh
python scripts/demo_multisegment_reconstruction.py your_mesh.stl
```

### Detailed Analysis

```python
import trimesh
from meshconverter.reconstruction.layer_wise_stacker import LayerWiseStacker
from meshconverter.validation.visual_comparator import compare_reconstruction

# Load
mesh = trimesh.load('your_mesh.stl')

# Reconstruct
stacker = LayerWiseStacker(verbose=True)
result = stacker.reconstruct(mesh)

# Generate visual report
compare_reconstruction(
    original=mesh,
    reconstructed=result['reconstructed_mesh'],
    segments=result['segments'],
    output_path='your_mesh_comparison.png'
)
```

---

## Unit Testing

```bash
# Run all LPS tests
pytest tests/test_layer_wise_stacking.py -v

# Run specific test
pytest tests/test_layer_wise_stacking.py::test_simple_block -v

# Run with coverage
pytest tests/test_layer_wise_stacking.py --cov=meshconverter.reconstruction -v
```

---

## Next Steps

1. **Test on your meshes** - Try the demo script on your STL files
2. **Review output** - Check quality scores and segment breakdown
3. **Tune parameters** - Adjust layer height and thresholds as needed
4. **Generate reports** - Use visual comparison for validation
5. **Integrate into workflow** - Use Python API or CLI as needed

---

## Additional Resources

- **Full Documentation:** [PHASE_4A_CV_ENHANCEMENT.md](PHASE_4A_CV_ENHANCEMENT.md)
- **Implementation Summary:** [PHASE_4A_SUMMARY.md](PHASE_4A_SUMMARY.md)
- **Changelog:** [CHANGELOG.md](../CHANGELOG.md)
- **Main README:** [README.md](../README.md)

---

## Support

**Issues?** Check [Troubleshooting](#troubleshooting) section or open a GitHub issue.

**Questions?** See [PHASE_4A_CV_ENHANCEMENT.md](PHASE_4A_CV_ENHANCEMENT.md) for detailed technical explanation.

---

**Version:** 2.1.0
**Status:** Production-ready
**Last Updated:** 2026-01-18
