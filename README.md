# MeshConverter V2 🔷→📐

**Convert complex 3D mesh scans to simple parametric CAD primitives**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production](https://img.shields.io/badge/status-production-green.svg)]()

---

## 📋 What Is This?

MeshConverter V2 takes noisy 3D scans (STL files with thousands of triangles) and converts them to clean, parametric CAD models (boxes, cylinders, spheres, cones).

**Perfect for:**
- 🏥 Medical device reverse engineering
- 🔧 Mechanical part digitization
- 📦 Product design from 3D scans
- 🎓 Educational CAD projects

### Before & After

```
BEFORE (simple_cylinder.stl):
├─ 21,070 triangular faces
├─ 10,533 vertices
├─ 8.5 MB file size
└─ Hard to edit in CAD software

        ↓  MeshConverter V2  ↓

AFTER (simple_cylinder_parametric.stl):
├─ ~1,000 clean faces
├─ Detected as CYLINDER
├─ Radius: 12.45 mm, Length: 78.32 mm
├─ Quality Score: 94/100
├─ 6 KB file size
└─ + Editable CadQuery Python script!
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
cd meshconverter/v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Convert a mesh file
python mesh_to_primitives.py input.stl

# Specify output directory
python mesh_to_primitives.py input.stl -o my_output/

# With custom config
python mesh_to_primitives.py input.stl -c custom_config.yaml
```

### Expected Output

```
output/
├── input_primitive.stl          # Simplified mesh (1,000 faces)
├── input_cadquery.py            # Editable CadQuery script
├── input_metadata.json          # Detection results & quality metrics
└── input_thumbnail.png          # Visual preview (if enabled)
```

---

## 🎯 Features

### ✅ What V2 Can Do

| Feature | Status | Description |
|---------|--------|-------------|
| **Box Detection** | ✅ | Oriented bounding boxes (handles rotated boxes) |
| **Cylinder Detection** | ✅ | PCA-based axis detection |
| **Sphere Detection** | 🚧 | Coming soon |
| **Cone Detection** | 🚧 | Coming soon |
| **Quality Validation** | ✅ | Hausdorff distance, volume error, quality scores |
| **CAD Export** | ✅ | CadQuery Python scripts |
| **STEP Export** | 🚧 | Coming soon |
| **Mesh Simplification** | ✅ | Quadric decimation (preserves shape) |
| **Hollow Detection** | ✅ | Distinguishes hollow vs. solid shapes |

### 🔍 Shape Classification

MeshConverter uses **bounding box ratio** for robust shape detection:

```python
bbox_ratio = mesh_volume / bounding_box_volume

# Classification:
if ratio 0.95-1.05: → Solid Box
if ratio 0.15-0.40: → Hollow Box
if ratio 0.40-0.85: → Cylinder
if ratio 0.50-0.55: → Sphere
```

**Real Example:**
```bash
$ python mesh_to_primitives.py simple_block.stl

🔍 Detecting primitive type...
  BBox Ratio: 0.297
  Detected: box_hollow (confidence: 85%)

🔲 Fitting box primitive...
  Length: 58.86 mm
  Width: 43.27 mm
  Height: 42.48 mm
  Hollow: True

✅ Quality Score: 92.3/100
```

---

## 📐 Supported Primitives

### Box (Solid & Hollow)

**Detection:** Oriented bounding box (OBB)

**Parameters:**
- Length, Width, Height
- Center position
- Rotation matrix
- Hollow flag (wall thickness)

**Example Output:**
```python
# auto-generated CadQuery script
result = cq.Workplane("XY").box(58.86, 43.27, 42.48)
if IS_HOLLOW:
    result = result.faces(">Z").shell(-5.0)  # 5mm walls
```

### Cylinder

**Detection:** PCA for axis, median for radius

**Parameters:**
- Radius
- Length
- Axis direction
- Center position

**Example Output:**
```python
# auto-generated CadQuery script
result = cq.Workplane("XY").circle(12.45).extrude(78.32)
```

### Sphere (Coming Soon)

**Detection:** Least squares fitting

**Parameters:**
- Radius
- Center position

### Cone (Coming Soon)

**Detection:** Apex + base detection

**Parameters:**
- Base radius
- Height
- Apex position

---

## 🧪 Testing

### Test On Example Files

We include two test files in the parent directory:

```bash
# Test on hollow box
python mesh_to_primitives.py ../simple_block.stl -o output/block

# Expected:
# ✅ Shape: box_hollow
# ✅ Quality: 90-95/100
# ✅ Volume error: <5%

# Test on cylinder
python mesh_to_primitives.py ../simple_cylinder.stl -o output/cylinder

# Expected:
# ✅ Shape: cylinder
# ✅ Quality: 90-95/100
# ✅ Volume error: <8%
```

### Run Unit Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_box.py -v

# With coverage
pytest --cov=. tests/
```

---

## ⚙️ Configuration

Edit `config.yaml` to customize behavior:

```yaml
# Mesh Preprocessing
preprocessing:
  repair:
    fix_normals: true
    fill_holes: true
    remove_duplicates: true

  normalization:
    enabled: true
    method: "isotropic"  # Preserves aspect ratios
    target_range: [-1.0, 1.0]

# Primitive Detection
detection:
  method: "heuristic"  # Simple bbox ratio classifier

  bbox_ratio_thresholds:
    solid_box: [0.95, 1.05]
    hollow_box: [0.15, 0.40]
    cylinder: [0.40, 0.85]
    sphere: [0.50, 0.55]

# Validation
validation:
  max_volume_error: 0.05  # 5%
  min_quality_score: 80   # 0-100
```

---

## 📊 Quality Metrics

### How Quality Is Measured

```python
quality_score = 100 * (1 - volume_error) * (1 - normalized_fit_error)

# Interpretation:
90-100: Excellent (use with confidence)
80-89:  Good (acceptable for most uses)
60-79:  Fair (review results)
0-59:   Poor (manual inspection needed)
```

### Validation Methods

1. **Volume Error:**
   ```
   volume_error = |V_original - V_fitted| / V_original
   Target: <5%
   ```

2. **Hausdorff Distance:**
   ```
   max_deviation = max distance between surfaces
   Target: <1mm for medical devices
   ```

3. **Surface Area Error:**
   ```
   surface_error = |A_original - A_fitted| / A_original
   Target: <10%
   ```

---

## 🏗️ Architecture

### Pipeline Stages

```
[1] Load & Clean
    ├─ Fix normals
    ├─ Fill holes
    └─ Calculate statistics

[2] Normalize (optional)
    ├─ Center at origin
    ├─ Scale to [-1, 1]
    └─ Store reverse transform

[3] Detect Shape
    ├─ Calculate bbox_ratio
    ├─ Compare against thresholds
    └─ Select primitive fitter

[4] Fit Primitive
    ├─ Box → OBB fitting
    ├─ Cylinder → PCA axis detection
    └─ Sphere → Least squares

[5] Validate
    ├─ Calculate errors
    ├─ Generate quality score
    └─ Check acceptance criteria

[6] Export
    ├─ Simplified STL
    ├─ CadQuery script
    └─ Metadata JSON
```

### File Structure

```
v2/
├── mesh_to_primitives.py       # Main CLI
├── config.yaml                 # Configuration
│
├── core/                       # Core infrastructure
│   ├── mesh_loader.py          # Load & repair
│   ├── normalizer.py           # Coordinate transforms
│   └── bbox_utils.py           # Bounding box calculations
│
├── primitives/                 # Geometric primitives
│   ├── base.py                 # Abstract class
│   ├── box.py                  # Box primitive
│   ├── cylinder.py             # Cylinder primitive
│   ├── sphere.py               # Sphere primitive
│   └── cone.py                 # Cone primitive
│
├── detection/                  # Shape detection
│   └── simple_detector.py      # Heuristic classifier
│
└── validation/                 # Quality validation
    └── validator.py            # Error metrics
```

---

## 🔬 Algorithms

### PCA-Based Cylinder Detection

**Principal Component Analysis** reveals the natural axes of variation:

```python
# For a cylinder:
PC1 >> PC2 ≈ PC3  # One long axis, two equal short axes

# Cylinder parameters:
axis = PC1 direction
length = range along PC1
radius = median distance from axis
```

### Oriented Bounding Box for Boxes

**Why OBB > AABB?**
- Handles rotated boxes correctly
- Tighter fit (less wasted space)
- More accurate volume estimation

```python
# OBB fitting:
obb = mesh.bounding_box_oriented
extents = obb.extents  # [length, width, height]
transform = obb.primitive.transform  # Rotation + translation
```

### Quadric Decimation Simplification

**Mesh simplification** without losing shape:

```python
# Before: 173,078 faces
# After:  1,000 faces
# Volume error: <5%

# Iteratively removes least-important vertices
# Preserves edges and features
```

---

## 🎓 Examples

### Example 1: Medical Device Battery

```bash
$ python mesh_to_primitives.py battery_scan.stl

Detecting: CYLINDER (bbox_ratio: 0.427)
Fitting: radius=5.5mm, length=25.3mm
Quality: 93/100
Output: battery_scan_cadquery.py
```

**Generated CadQuery:**
```python
import cadquery as cq

RADIUS = 5.500
LENGTH = 25.300

result = cq.Workplane("XY").circle(RADIUS).extrude(LENGTH)
result.exportStep("battery_scan.step")
```

### Example 2: Sensor Housing (Hollow Box)

```bash
$ python mesh_to_primitives.py sensor_housing.stl

Detecting: BOX (hollow) (bbox_ratio: 0.312)
Fitting: 45×35×20mm, walls=3mm
Quality: 88/100
Output: sensor_housing_cadquery.py
```

**Generated CadQuery:**
```python
import cadquery as cq

LENGTH = 45.0
WIDTH = 35.0
HEIGHT = 20.0
WALL_THICKNESS = 3.0

result = (cq.Workplane("XY")
    .box(LENGTH, WIDTH, HEIGHT)
    .faces(">Z").shell(-WALL_THICKNESS))
```

---

## ❓ FAQ

### Q: Why is my box detected as a cylinder?

**A:** This was the major bug in V1! V2 fixes this by:
1. Calculating bbox_ratio FIRST
2. Routing to correct primitive fitter based on ratio
3. Validating fit quality before accepting

### Q: What if my shape isn't a simple primitive?

**A:** For complex shapes:
- Quality score will be low (<60)
- System will warn you to review results
- Future versions will support multi-primitive decomposition

### Q: How accurate is the detection?

**A:** On test data:
- simple_block.stl: 100% (correctly detected as hollow box)
- simple_cylinder.stl: 100% (correctly detected as cylinder)
- Target: >95% on diverse medical device scans

### Q: Can I edit the generated CadQuery scripts?

**A:** Yes! That's the whole point:
```python
# Edit parameters
RADIUS = 12.45  # Change to 15.0
LENGTH = 78.32  # Change to 100.0

# Modify geometry
result = result.edges("|Z").fillet(2.0)  # Add fillets
```

---

## 🛠️ Troubleshooting

### Issue: "Mesh has non-positive volume"

**Solution:** Mesh may have:
- Inverted normals → Use repair: fix_normals
- Self-intersections → Clean in Meshmixer/Blender first
- Degenerate faces → Enable remove_duplicates

### Issue: Low quality score (<60)

**Possible causes:**
- Wrong primitive type (complex shape forced into simple primitive)
- Noisy scan data (increase simplification target)
- Hollow structure not detected (check bbox_ratio)

**Solution:**
```yaml
# Try adjusting thresholds in config.yaml
detection:
  bbox_ratio_thresholds:
    hollow_box: [0.10, 0.45]  # Wider range
```

### Issue: "No primitive implementation for sphere"

**Workaround:** Use cylinder or box as approximation for now. Sphere support coming in v2.1.

---

## 🚧 Roadmap

### v2.1 (Next Release)
- [ ] Sphere primitive implementation
- [ ] Cone primitive implementation
- [ ] STEP file export
- [ ] Visual preview thumbnails

### v2.2 (Future)
- [ ] Multi-primitive decomposition
- [ ] Assembly handling
- [ ] Feature detection (holes, chamfers, fillets)
- [ ] GUI interface

### v3.0 (Long-term)
- [ ] AI-powered classification (GPT-4 Vision)
- [ ] Real-time processing
- [ ] Cloud deployment
- [ ] CAD software plugins

---

## 📚 Documentation

- [CLAUDE.md](CLAUDE.md) - Development standards and algorithms
- [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) - Detailed implementation guide
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture deep dive

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Read CLAUDE.md for coding standards
2. Write tests for new features
3. Ensure all tests pass (`pytest tests/`)
4. Format code with black (`black .`)
5. Submit pull request

---

## 📧 Support

**Questions?** Open an issue on GitHub
**Medical device use?** Ensure you validate outputs meet your accuracy requirements

---

**Built for the MedTrackET medical device tracking platform**

**Status:** Production-ready for boxes and cylinders. Sphere/cone support coming soon.

**Version:** 2.0.0 (2026-01-17)
