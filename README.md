# MeshConverter 🔷→📐

**Convert complex 3D mesh scans to simple parametric CAD primitives**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production](https://img.shields.io/badge/status-production-green.svg)]()

---

## 📋 What Is This?

MeshConverter takes noisy 3D scans (STL files with thousands of triangles) and converts them to clean, parametric CAD models (boxes, cylinders, spheres).

**Core Mission:** Given a scanned mesh (10k-100k+ vertices), intelligently detect what simple shape(s) it represents, then output a clean simplified mesh with parameters you can edit in any CAD tool.

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

        ↓  MeshConverter  ↓

AFTER (simple_cylinder_parametric.stl):
├─ ~1,000 clean faces
├─ Detected as CYLINDER
├─ Radius: 12.45 mm, Length: 78.32 mm
├─ Quality Score: 94/100
├─ 6 KB file size
└─ + Editable Python script with dimensions!
```

---

## 🚀 Quick Start

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux; Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Classify shape type and analyze
python meshconverter/cli.py your_scanned_part.stl --analyze

# This outputs:
# - Console: Detected shape, confidence, reasoning
# - *_classification.json: Full classification details

# Convert to clean parametric model
python meshconverter/cli.py your_scanned_part.stl --output output_clean.stl

# This outputs:
# - output_clean_parametric.stl (simplified, easy to edit)
# - output_clean_metadata.json (parameters & quality metrics)
```

### Expected Output

```
output/
├── simple_block_parametric.stl      # Simplified mesh (~1,000 faces)
├── simple_block_metadata.json       # Detection results & parameters
└── simple_block_cadquery.py         # Editable parametric script (if enabled)
```

---

## 🎯 Features

### ✅ What MeshConverter Can Do

| Feature | Status | Description |
|---------|--------|-------------|
| **Box Detection** | ✅ | Oriented bounding box (OBB) fitting |
| **Cylinder Detection** | ✅ | PCA-based axis detection + radius fitting |
| **Sphere Detection** | ✅ | Least-squares sphere fitting |
| **Mesh Simplification** | ✅ | Quadric decimation (preserves shape) |
| **Hollow Detection** | ✅ | Distinguishes hollow vs. solid shapes |
| **Quality Validation** | ✅ | Volume error, fit accuracy, quality scores |
| **Few-Shot AI Classification** | ✅ | OpenAI integration with training examples |
| **GPT-4 Vision (Optional)** | ✅ | Multi-angle mesh rendering for visual analysis |
| **Parametric Export** | ✅ | CadQuery Python scripts for easy editing |

### 🔍 Shape Classification

MeshConverter supports **multiple classification methods**:

#### The Magic Metric: Bounding Box Ratio

**Formula:** `mesh_volume / bounding_box_volume`

This single metric is the most reliable way to classify shapes:

```python
# Classification thresholds:
0.95-1.05  → Solid Box
0.15-0.40  → Hollow Box  
0.40-0.85  → Cylinder
~0.52      → Sphere (π/6, mathematically constant)
```

**Why It Works:**
- **Cylinder:** 0.4-0.8 (empty space around circular cross-section)
- **Solid Box:** 0.95-1.0 (fills its bounding box)
- **Hollow Box:** 0.2-0.4 (mostly empty inside)
- **Sphere:** ~0.52 (pi/6)

#### 1. Heuristic Detection (Fast, Free, Always Available)

Uses bounding box ratio + PCA analysis for robust shape detection:

```bash
$ python meshconverter/cli.py simple_block.stl --analyze

🔍 Analyzing mesh geometry...
Original mesh stats:
  Vertices: 2,541
  Faces: 5,078
  Volume: 101,645.32 mm³
  Bounding Box Ratio: 0.297

✅ Shape Classification (Heuristic):
  Shape Type: BOX (HOLLOW)
  Confidence: 85%
  Reasoning: BBox ratio 0.297 indicates hollow box

💾 Classification saved to: simple_block_classification.json
```

#### 2. Few-Shot AI Classification (Accurate, Contextual) 🆕

Uses OpenAI with training examples for improved accuracy:

```bash
$ python meshconverter/cli.py simple_cylinder.stl --analyze --train

🤖 AI Shape Classification with Few-Shot Learning...
  Found 3 similar training examples
  Sending to OpenAI with context...

✅ Shape Classification (AI):
  Shape Type: CYLINDER
  Confidence: 95%
  Reasoning: Detected axis elongation + circular cross-section

  Detected Parameters:
  - Radius: 12.45 mm
  - Length: 78.32 mm
  - Axis: [0.0, 0.0, 1.0]

💾 Classification saved to: simple_cylinder_classification.json
```

**Key Benefits:**
- **Higher Accuracy**: Few-shot learning with similar examples
- **Contextual**: Learns from your training data
- **Parametric Output**: Extracts shape parameters automatically

**Requirements:**
```bash
# Set API key in .env
export OPENAI_API_KEY=sk-...
```

**Cost:** ~$0.01-0.05 per mesh (optional feature)

---

## 📐 Supported Primitives

### Box (Solid & Hollow)

**Detection:** Oriented Bounding Box (OBB) with hollow volume analysis

**Parameters:**
- Length, Width, Height (mm)
- Center position
- Rotation matrix
- Hollow flag (if applicable)

**Generated Output:**
```python
# auto-generated parametric script
import cadquery as cq

LENGTH = 58.86
WIDTH = 43.27
HEIGHT = 42.48
IS_HOLLOW = True

result = (cq.Workplane("XY")
    .box(LENGTH, WIDTH, HEIGHT))

if IS_HOLLOW:
    result = result.faces(">Z").shell(-3.0)  # 3mm walls
```

### Cylinder

**Detection:** PCA analysis for axis, median distance for radius

**Parameters:**
- Radius (mm)
- Length (mm)
- Axis direction (unit vector)
- Center position

**Generated Output:**
```python
# auto-generated parametric script
import cadquery as cq

RADIUS = 12.45
LENGTH = 78.32

result = cq.Workplane("XY").circle(RADIUS).extrude(LENGTH)
```

### Sphere

**Detection:** Least-squares fitting to all vertices

**Parameters:**
- Radius (mm)
- Center position

**Generated Output:**
```python
# auto-generated parametric script
import cadquery as cq

RADIUS = 25.0

result = cq.Workplane("XY").sphere(RADIUS)
```

---

## 🧪 Testing

### Test On Example Files

Example STL files are included in `output/` subdirectories:

```bash
# Test on hollow box
python meshconverter/cli.py output/block/simple_block_metadata.json --analyze

# Expected:
# ✅ Shape: box_hollow
# ✅ Quality: 90-95/100
# ✅ Volume error: <5%

# Test on cylinder
python meshconverter/cli.py output/cylinder/simple_cylinder_metadata.json --analyze

# Expected:
# ✅ Shape: cylinder
# ✅ Radius: ~12.45 mm
# ✅ Quality: 90-95/100
```

### Run Unit Tests

```bash
# All tests
pytest tests/ -v

# Specific test module
pytest tests/unit/test_primitives.py -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest --cov=meshconverter tests/
```

### Batch Processing

```bash
# Convert all STL files in a directory
for f in *.stl; do
    echo "Converting $f..."
    python meshconverter/cli.py "$f" --train
done
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
  method: "heuristic"  # Can use "ai" for OpenAI classification
  
  bbox_ratio_thresholds:
    solid_box: [0.95, 1.05]
    hollow_box: [0.15, 0.40]
    cylinder: [0.40, 0.85]
    sphere: [0.48, 0.56]

# Validation
validation:
  max_volume_error: 0.05    # 5%
  min_quality_score: 80     # 0-100
  max_hausdorff_distance: 1.0  # 1mm for medical devices

# Mesh Simplification
simplification:
  enabled: true
  target_face_count: 1000
  preserve_volume: true
```

---

## 📊 Quality Metrics

### How Quality Is Measured

```
quality_score = 100 × (1 - volume_error) × (1 - normalized_hausdorff_distance)

Interpretation:
  90-100: Excellent (production-ready)
   80-89: Good (acceptable for most uses)
   60-79: Fair (review results carefully)
    0-59: Poor (manual inspection recommended)
```

### Validation Methods

1. **Volume Error:**
   ```
   error = |V_original - V_fitted| / V_original
   Target: <5% for most applications
   ```

2. **Hausdorff Distance:**
   ```
   max_deviation = maximum distance between surfaces
   Target: <1mm for medical devices
   ```

3. **Surface Area Error:**
   ```
   error = |A_original - A_fitted| / A_original
   Target: <10%
   ```

---

## 🏗️ Architecture

### Pipeline Stages

```
[1] Load & Repair
    ├─ Load STL file
    ├─ Fix normals and mesh integrity
    └─ Calculate initial statistics

[2] Normalize (optional)
    ├─ Center at origin
    ├─ Scale to [-1, 1] range
    └─ Store reverse transform for later

[3] Classify Shape
    ├─ Calculate bounding box ratio
    ├─ Apply heuristic classification
    ├─ Query similar training examples (if AI enabled)
    └─ Output: {shape_type, confidence, parameters}

[4] Fit Primitive
    ├─ Box → Oriented bounding box fitting
    ├─ Cylinder → PCA axis + radius detection
    ├─ Sphere → Least-squares sphere fitting
    └─ Extract parametric dimensions

[5] Simplify Mesh
    ├─ Apply quadric edge decimation
    ├─ Target: 1000-5000 faces
    └─ Preserve shape during simplification

[6] Validate & Export
    ├─ Calculate quality metrics
    ├─ Generate metadata JSON
    ├─ Export simplified STL
    └─ Create parametric CadQuery script
```

### File Structure

```
.
├── meshconverter/
│   ├── __init__.py
│   ├── cli.py                     # Command-line interface
│   └── classification/
│       ├── vision_classifier.py   # GPT-4 Vision integration
│       └── voxel_classifier.py    # Voxel-based classification
│
├── core/
│   ├── mesh_loader.py             # Load & repair meshes
│   ├── normalizer.py              # Coordinate transforms
│   ├── bbox_utils.py              # Bounding box calculations
│   ├── decomposer.py              # Multi-primitive decomposition
│   └── pattern_matcher.py         # Training data similarity
│
├── detection/
│   ├── ai_detector.py             # OpenAI few-shot classification
│   └── simple_detector.py         # Heuristic detection fallback
│
├── primitives/
│   ├── base.py                    # Abstract primitive class
│   ├── box.py                     # Box primitive implementation
│   ├── cylinder.py                # Cylinder primitive implementation
│   └── __init__.py
│
├── validation/
│   └── validator.py               # Quality metrics & validation
│
├── config.yaml                    # Configuration
├── requirements.txt               # Dependencies
└── training_data.json             # Training examples for few-shot learning
```

---

## 🔬 Algorithms

### The Magic Metric: Bounding Box Ratio

**Why this works:**
- Extremely fast to compute
- Geometrically meaningful
- Doesn't require fitting
- Handles noise well

```python
bbox_ratio = mesh.volume / bounding_box.volume

# Interpretation:
# 0.95+: Shape fills its box → Likely SOLID BOX
# 0.15-0.40: Mostly empty → Likely HOLLOW BOX
# 0.40-0.85: Moderately filled → Likely CYLINDER
# ~0.52: Special case (π/6) → Likely SPHERE
```

### PCA-Based Cylinder Detection

**Principal Component Analysis** reveals natural axes of variation:

```python
# For a perfect cylinder:
# PC1 >> PC2 ≈ PC3
# (one long axis, two equal short axes)

# Cylinder parameters:
axis_direction = PC1 eigenvector
length = range along PC1
radius = median distance from axis to vertices
```

### Oriented Bounding Box (OBB) for Boxes

**Why OBB > Axis-Aligned Bounding Box (AABB):**
- Handles rotated boxes correctly
- Tighter fit (less wasted space)
- More accurate volume estimation
- Extracts rotation information

```python
# OBB fitting:
obb = calculate_oriented_bounding_box(mesh)
dimensions = obb.extents  # [length, width, height]
rotation = obb.rotation_matrix
center = obb.center
```

### Quadric Mesh Simplification

**Fast-Simplification** reduces face count while preserving shape:

```
Before: 173,078 faces
After:  1,000 faces
Volume Error: <5%
Time: ~2 seconds

Algorithm: Iteratively removes least-important vertices
preserving edges and features
```

---

## 🎓 Examples

### Example 1: Battery Cylinder

```bash
$ python meshconverter/cli.py battery_scan.stl --analyze --train

🔍 Analyzing mesh...
Original mesh stats:
  Vertices: 8,432
  Faces: 16,861
  Volume: 1,247.56 mm³
  Bounding Box Ratio: 0.427

✅ Shape Classification:
  Type: CYLINDER
  Confidence: 95%
  
Detected Parameters:
  Radius: 5.50 mm
  Length: 25.30 mm
  Volume: 1,241.50 mm³
  Volume Error: 0.5%

💾 Output:
  - battery_scan_parametric.stl (simplified, 1,204 faces)
  - battery_scan_metadata.json (parameters & metrics)
  - battery_scan_cadquery.py (editable Python script)
```

**Generated CadQuery Script:**
```python
import cadquery as cq

RADIUS = 5.50
LENGTH = 25.30

result = cq.Workplane("XY").circle(RADIUS).extrude(LENGTH)
result.exportStep("battery_scan.step")
```

### Example 2: Sensor Housing (Hollow Box)

```bash
$ python meshconverter/cli.py sensor_housing.stl --analyze --train

🔍 Analyzing mesh...
Original mesh stats:
  Vertices: 3,241
  Faces: 6,472
  Volume: 4,156.32 mm³
  Bounding Box Ratio: 0.312

✅ Shape Classification:
  Type: BOX (HOLLOW)
  Confidence: 92%
  
Detected Parameters:
  Length: 45.00 mm
  Width: 35.00 mm
  Height: 20.00 mm
  Wall Thickness: 3.00 mm
  Volume Error: 2.1%

💾 Output:
  - sensor_housing_parametric.stl (simplified)
  - sensor_housing_metadata.json
  - sensor_housing_cadquery.py
```

**Generated CadQuery Script:**
```python
import cadquery as cq

LENGTH = 45.0
WIDTH = 35.0
HEIGHT = 20.0
WALL_THICKNESS = 3.0

result = (cq.Workplane("XY")
    .box(LENGTH, WIDTH, HEIGHT)
    .faces(">Z").shell(-WALL_THICKNESS))

result.exportStep("sensor_housing.step")
```

---

## ❓ FAQ

### Q: How do I use MeshConverter for my scan?

**A:** Three simple steps:
```bash
# 1. Analyze what shape it is
python meshconverter/cli.py your_scan.stl --analyze

# 2. Review the classification and parameters
# (look at the console output and metadata JSON)

# 3. Convert to clean, editable model
python meshconverter/cli.py your_scan.stl --output clean_model.stl
```

### Q: What if my shape isn't detected correctly?

**A:** Try these steps:
1. Check the bounding box ratio (printed to console)
2. Review the `*_classification.json` file for reasoning
3. Use `--train` flag to enable AI classification with examples:
   ```bash
   python meshconverter/cli.py your_scan.stl --analyze --train
   ```

### Q: Can I edit the generated CadQuery scripts?

**A:** Yes! That's the whole point. Example:
```python
# Edit parameters
RADIUS = 15.0  # Changed from 12.45
LENGTH = 100.0  # Changed from 78.32

# Modify geometry
result = result.edges("|Z").fillet(2.0)  # Add 2mm fillets
result.exportStep("modified_part.step")
```

### Q: What's the quality score and when should I trust it?

**A:**
- **90-100**: Excellent, production-ready
- **80-89**: Good for most applications
- **60-79**: Review carefully, may need manual tweaking
- **<60**: Shape likely doesn't fit primitive well, consider manual modeling

### Q: How does the AI training work?

**A:** MeshConverter uses **few-shot learning**:
1. You provide training examples (STL + shape type)
2. System stores their geometry stats
3. When analyzing new mesh, it finds similar examples
4. Sends those examples to OpenAI with the new mesh
5. AI makes classification based on learned patterns

This requires an OpenAI API key set in `.env`.

### Q: Do I need an OpenAI API key?

**A:** No! MeshConverter works perfectly without it:
- Uses fast, free heuristic detection by default
- Optional AI classification with `--train` flag
- Falls back to heuristic if API unavailable

### Q: What file formats are supported?

**A:** Currently:
- **Input:** STL (binary and ASCII)
- **Output:** STL, JSON metadata, Python CadQuery scripts
- **Future:** STEP, IGES, 3MF

---

## 🛠️ Troubleshooting

### Issue: "Mesh has non-positive volume"

**Causes:** Inverted normals, self-intersections, or degenerate faces

**Solutions:**
```bash
# Auto-repair with fix_normals enabled (default in config.yaml)
python meshconverter/cli.py your_scan.stl --repair

# Or manually fix in Meshmixer/Blender:
# - Mesh > Cleanup > Normalize mesh
# - Export as STL
```

### Issue: Low quality score (<60)

**Possible causes:**
- Wrong primitive type (complex shape forced into simple primitive)
- Noisy scan data
- Hollow structure not correctly detected

**Solutions:**
```yaml
# Adjust detection thresholds in config.yaml
detection:
  bbox_ratio_thresholds:
    hollow_box: [0.10, 0.45]  # Wider range
```

### Issue: Shape classification is wrong

**Solutions:**
1. Check `*_classification.json` for reasoning
2. Enable AI classification:
   ```bash
   python meshconverter/cli.py your_scan.stl --analyze --train
   ```
3. Add training examples to improve accuracy
4. Review console output for bounding box ratio

### Issue: Mesh simplification changes the shape too much

**Solutions:**
```yaml
# Adjust simplification settings in config.yaml
simplification:
  target_face_count: 5000  # More faces = more detail
  preserve_volume: true    # Strict volume preservation
```

### Issue: OpenAI API errors

**Solutions:**
```bash
# Check API key
echo $OPENAI_API_KEY

# Verify .env file
cat .env | grep OPENAI

# Use heuristic-only (no AI)
python meshconverter/cli.py your_scan.stl --no-train
```

---

## 🚧 Roadmap

### v1.1 (Next Release)
- [ ] Improved sphere detection accuracy
- [ ] Multi-primitive decomposition (detect assemblies)
- [ ] STEP file export
- [ ] Visual quality preview images

### v1.2 (Near-term)
- [ ] Real-time mesh analysis in web interface
- [ ] Batch processing dashboard
- [ ] Custom training data management

### v2.0 (Long-term)
- [ ] Full CAD software plugin (FreeCAD, Fusion 360)
- [ ] Advanced feature recognition (holes, fillets, chamfers)
- [ ] Mesh comparison and validation tools
- [ ] Cloud-based processing for large batches

---

## 📚 Documentation

Detailed documentation is available in the `docs/` directory:

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute
- **[docs/dev/](docs/dev/)** - Development guides and technical notes
- **[docs/guides/](docs/guides/)** - User guides and tutorials
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - AI development guidelines

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Read [.github/copilot-instructions.md](.github/copilot-instructions.md) for coding standards
2. Write tests for new features
3. Ensure all tests pass: `pytest tests/ -v`
4. Format code with black: `black .`
5. Submit pull request

---

## 📧 Support

**Questions?** Open an issue on GitHub

**Medical device validation:** Always validate outputs meet your accuracy and regulatory requirements

---

**Built for the MedTrackET medical device tracking platform**

**Status:** Production-ready for boxes and cylinders. Sphere support available. AI classification optional.

**Version:** 1.0.0 | Last Updated: 2026-01-17
