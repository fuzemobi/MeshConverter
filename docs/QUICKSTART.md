# MeshConverter Quick Start Guide

Get up and running in 5 minutes!

## ⚡ 30-Second Setup

```bash
# 1. Navigate to project
cd /path/to/MeshConverter_v2

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Convert a mesh!
python -m meshconverter.cli output/block/simple_block_output.stl -o output/block/
```

Done! ✅

---

## 🎯 Basic Commands

### Convert with Default (Voxel) Classifier

```bash
python -m meshconverter.cli your_mesh.stl -o output/
```

**Automatic Output (Everything Generated):**
1. **`your_mesh_parametric.stl`** — Simplified mesh ready for CAD (1000-5000 faces)
2. **`your_mesh_metadata.json`** — Classification results with detected parameters
3. **`your_mesh_cadquery.py`** — Editable Python script (for STEP export or customization)

**How it works:**
- Mesh is automatically analyzed
- Shape type detected (cylinder, box, sphere, complex)
- Simplified mesh generated with clean geometry
- Script template created with extracted parameters
- **Ready to use immediately!** Just open the STL in FreeCAD or CAD software

**Example output:**
```
💾 Saving outputs to: output/your_mesh
  ✅ Metadata: output/your_mesh/your_mesh_metadata.json
  ✅ STL: output/your_mesh/your_mesh_parametric.stl
  ✅ Script: output/your_mesh/your_mesh_cadquery.py

📌 Results:
  Shape: CYLINDER
  Confidence: 85%
  Method: voxel

📁 Files ready to use:
  • metadata: Classification results + parameters
  • stl: Production-ready simplified mesh
  • script: Customizable parametric template
```

**Optional: Generate STEP for Parametric CAD:**
```bash
# If you want a parametric model in FreeCAD/Fusion360:
cd output/your_mesh
python your_mesh_cadquery.py
# Creates: your_mesh_parametric.step
```

### Convert with Heuristic Classifier (Fast, No API)

```bash
python -m meshconverter.cli your_mesh.stl --classifier heuristic -o output/
```

**Best for:** Quick prototyping, offline environments, batch processing

**Heuristic Method:** Uses bounding box ratio:
- **0.95-1.05**: Solid box
- **0.15-0.40**: Hollow box
- **0.40-0.85**: Cylinder
- **~0.52**: Sphere

### Convert with Layer-Slicing Classifier (Fast, Accurate, Axis-Aligned)

```bash
python -m meshconverter.cli your_mesh.stl --classifier layer-slicing -o output/
```

**Best for:** Multi-component assemblies, stacked boxes, mechanical parts

**How it works:**
- Slices mesh horizontally at regular intervals
- Detects separate regions in each layer
- Reconstructs 3D boxes from layer analysis
- Perfect for CAD-designed parts

**Options:**
```bash
# Adjust layer height (smaller = more detail, slower)
python -m meshconverter.cli your_mesh.stl --classifier layer-slicing --layer-height 1.0

# Default layer height is 2.0 mm
```

**Example Results:**
```
✅ Multi-box assembly: Detected 2 boxes (85% confidence)
✅ Cylinder: Detected 1 box (90% confidence)
✅ Speed: ~500ms
```

### Convert with Voxel Classifier (Analyzes Structure)

```bash
python -m meshconverter.cli your_mesh.stl --classifier voxel -o output/
```

**Best for:** Complex shapes, organic geometry

**Options:**
```bash
# Adjust voxel size (smaller = more detail, slower)
python -m meshconverter.cli your_mesh.stl --classifier voxel --voxel-size 0.5

# Add erosion (helps separate components)
python -m meshconverter.cli your_mesh.stl --classifier voxel --erosion 3
```

### Convert with GPT-4 Vision (Accurate, Requires API)

```bash
# Set API key first
export OPENAI_API_KEY=sk-...

# Then run
python -m meshconverter.cli your_mesh.stl --classifier gpt4-vision -o output/
```

**Best for:** Medical devices, high-stakes applications

**Cost:** ~$0.01 per mesh (renders 6 views @ $0.01/image)

**Setup:**
1. Get API key: https://platform.openai.com/api-keys
2. Create `.env` file (or set environment variable)
3. Run command above

### Compare All Classifiers

```bash
python -m meshconverter.cli your_mesh.stl --classifier all -o output/
```

**Output:** Shows heuristic, layer-slicing, voxel, and GPT-4 Vision results side-by-side

**Example comparison output:**
```
Method               Shape Type      Confidence   Status
----------------------------------------------------------------------
heuristic            complex         60%         ⚠️
layer-slicing        assembly        85%         ✅ BEST
voxel                unknown         0%         ⚠️
gpt4-vision          error           0%         ⚠️
```

---

## 📂 Test the Examples

We include two sample meshes in the `output/` directory:

### Block (Hollow Box)

```bash
# Quick analysis
python -m meshconverter.cli tests/samples/simple_block.stl --classifier heuristic

# Expected output:
# ✅ Classification: complex (60%)
# ✅ Loaded 36,346 vertices, 72,688 faces
# ✅ Volume: 32,178.42 mm³
```

### Cylinder

```bash
python -m meshconverter.cli tests/samples/simple_cylinder.stl --classifier heuristic

# Expected output:
# ✅ Classification: cylinder (85%)
# ✅ Loaded 10,533 vertices, 21,070 faces
# ✅ Volume: 7,884.23 mm³
# ✅ Bounding box ratio: 0.426
```

---

## 📊 Understanding Results

After conversion, check the console output:

```
======================================================================
MeshConverter v2.0.0 - Mesh to CAD Primitive Converter
======================================================================
Input: output/block/simple_block_output.stl
Classifier: heuristic
======================================================================

📂 Loading mesh: output/block/simple_block_output.stl
  ✅ Loaded 8 vertices, 12 faces
     Volume: 131095.38 mm³
     Bounding box: [53.58 51.90 70.74]

📐 Classifying with heuristic (bbox_ratio)...
  ✅ Classification: cylinder (85%)
     Reasoning: Medium bbox_ratio (0.666) indicates cylinder

======================================================================
✅ Classification complete!
======================================================================
```

**What it means:**
- **Loaded X vertices, Y faces**: Mesh complexity
- **Volume**: 3D size in mm³
- **Bounding box**: Dimensions (length × width × height)
- **Classification**: Detected shape type
- **Confidence %**: How sure the detector is
- **Reasoning**: Why it chose that classification

---

## 🔍 Detailed Analysis

To see more detailed statistics:

```bash
python -m meshconverter.cli your_mesh.stl -o output/

# Then inspect the metadata file:
cat output/your_mesh_metadata.json | jq
```

**Metadata contents:**
```json
{
  "classifier": "heuristic",
  "shape_type": "cylinder",
  "confidence": 85,
  "bbox_ratio": 0.415,
  "volume_mm3": 7839.52,
  "bounding_box": [17.46, 20.88, 51.85],
  "reasoning": "Medium bbox_ratio (0.415) indicates cylinder"
}
```

---

## ⚙️ Configuration

### Edit `config.yaml` to Customize

```yaml
# Mesh Preprocessing
preprocessing:
  repair:
    fix_normals: true
    fill_holes: true
    remove_duplicates: true

# Primitive Detection
detection:
  method: "heuristic"  # Can also be: voxel, gpt4-vision
  
  # Thresholds for heuristic classifier
  bbox_ratio_thresholds:
    solid_box: [0.95, 1.05]
    hollow_box: [0.15, 0.40]
    cylinder: [0.40, 0.85]
    sphere: [0.48, 0.56]

# Mesh Simplification
simplification:
  enabled: true
  target_face_count: 1000

# Validation
validation:
  max_volume_error: 0.05    # 5%
  min_quality_score: 80     # 0-100
```

---

## 🚀 Advanced Usage

### Batch Convert Multiple Files

```bash
# Convert all STL files in a directory
for f in *.stl; do
    echo "Converting $f..."
    python -m meshconverter.cli "$f" --classifier heuristic -o output/
done
```

### Use Custom Config

```bash
python -m meshconverter.cli your_mesh.stl --config my_config.yaml -o output/
```

### Adjust Voxel Parameters

```bash
# Finer voxel grid (slower, more accurate for small features)
python -m meshconverter.cli your_mesh.stl --classifier voxel --voxel-size 0.5

# Coarser voxel grid (faster, smoother results)
python -m meshconverter.cli your_mesh.stl --classifier voxel --voxel-size 2.0

# With erosion to separate components
python -m meshconverter.cli your_mesh.stl --classifier voxel --erosion 2
```

---

## ❓ Common Questions

### Q: Which classifier should I use?

**A:**
- **Layer-slicing (NEW)** — Best for multi-component assemblies, stacked boxes, mechanical parts. Fast (~500ms) and accurate (85-95% confidence).
  ```bash
  python -m meshconverter.cli multi_box.stl --classifier layer-slicing --layer-height 2.0 -o output/
  ```

- **Heuristic** — Fastest fallback for single shapes. Free, no setup. Works when axis-aligned geometry detected.

- **Voxel** — For complex organic shapes or dense component clusters (slower, more thorough).

- **GPT-4 Vision** — Highest accuracy for medical devices and irregular shapes. Requires OpenAI API key.

- **Compare with `all`** — To benchmark all methods and see which performs best:
  ```bash
  python -m meshconverter.cli your_mesh.stl --classifier all -o output/
  ```
  Layer-slicing typically outperforms others for mechanical/assembly geometry.

### Q: How do I set my OpenAI API key?

**A:** Three options:

```bash
# Option 1: Environment variable (temporary)
export OPENAI_API_KEY=sk-...
python -m meshconverter.cli your_mesh.stl --classifier gpt4-vision

# Option 2: .env file (permanent for this project)
echo "OPENAI_API_KEY=sk-..." > .env

# Option 3: In your shell profile (~/.zshrc or ~/.bash_profile)
echo "export OPENAI_API_KEY=sk-..." >> ~/.zshrc
source ~/.zshrc
```

### Q: What's the bounding box ratio?

**A:** It's the most reliable single metric for shape classification:

```
bbox_ratio = mesh_volume / bounding_box_volume

Why it works:
- Cylinder: 0.4-0.8 (empty space around circular cross-section)
- Solid Box: 0.95-1.0 (fills its bounding box completely)
- Hollow Box: 0.2-0.4 (mostly empty inside)
- Sphere: ~0.52 (π/6, mathematically constant)
```

### Q: Can I edit the generated files?

**A:** Yes! The output includes:
- `*_metadata.json` — Detected parameters (editable)
- `*_cadquery.py` — Python script for parametric design (fully editable)
- `*_output.stl` — Simplified mesh (can edit in CAD software)

### Q: Why is my accuracy low?

**A:** Try these:

1. **Use `--classifier voxel`** instead of heuristic
2. **Increase voxel detail:** `--voxel-size 0.5`
3. **Use GPT-4 Vision:** `--classifier gpt4-vision`
4. **Adjust detection thresholds** in `config.yaml`

---

## 🛠️ Troubleshooting

### Error: "No module named 'meshconverter'"

**Solution:**
```bash
# Make sure you activated the virtual environment
source venv/bin/activate

# Or try using Python module syntax
python -m meshconverter.cli your_mesh.stl
```

### Error: "OPENAI_API_KEY not set"

**Solution:**
```bash
export OPENAI_API_KEY=sk-...
# Then run again
```

### Error: "File not found"

**Solution:**
```bash
# Use absolute path or check filename
python -m meshconverter.cli /absolute/path/to/your_mesh.stl
```

### Slow performance with voxel classifier

**Solution:**
```bash
# Use larger voxel size (trades detail for speed)
python -m meshconverter.cli your_mesh.stl --classifier voxel --voxel-size 2.0

# Or use heuristic classifier (instant)
python -m meshconverter.cli your_mesh.stl --classifier heuristic
```

---

## 📚 Next Steps

- **Full README:** [README.md](../README.md)
- **API Documentation:** [docs/api/](api/)
- **Development Guide:** [docs/dev/](dev/)
- **GitHub:** https://github.com/fuzemobi/MeshConverter

---

## ✅ Verification Checklist

After setup, verify everything works:

```bash
# ✅ Test heuristic classifier
python -m meshconverter.cli output/block/simple_block_output.stl --classifier heuristic

# ✅ Test voxel classifier
python -m meshconverter.cli output/cylinder/simple_cylinder_output.stl --classifier voxel

# ✅ Show help
python -m meshconverter.cli -h

# ✅ Check version
python -m meshconverter.cli --version
```

All tests passing? You're ready to convert your meshes! 🎉
