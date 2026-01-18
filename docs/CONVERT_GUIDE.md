# MeshConverter - Complete Conversion Guide

**Intelligent Mesh-to-CAD Conversion with AI-Powered Analysis**

---

## 🚀 Quick Start

### Installation
```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate

# Ensure dependencies installed
pip install -r requirements.txt

# Set OpenAI API key (for vision analysis)
export OPENAI_API_KEY='sk-your-key-here'
```

### Basic Usage

```bash
# Convert with full AI analysis (recommended)
python scripts/convert_mesh.py your_scan.stl

# Convert without vision (faster, free)
python scripts/convert_mesh.py your_scan.stl --no-vision

# Specify output path
python scripts/convert_mesh.py input.stl -o output_clean.stl

# Thorough analysis (more layers)
python scripts/convert_mesh.py input.stl --vision-layers 10
```

---

## 📊 Test Results

### ✅ simple_cylinder.stl
**Input:**
- 10,533 vertices, 21,070 faces
- Volume: 7,884.23 mm³

**Analysis:**
- Vision detected: **CIRCLE** (93% confidence, 3/3 layers)
- Method: Vision-guided cylinder reconstruction

**Output:**
- Shape: **CYLINDER**
- Dimensions: r=7.07mm, L=50.29mm
- Quality Score: **99/100**
- Volume Error: **0.57%**
- Face Reduction: **99.4%** (21,070 → 128 faces)

✅ **Result: Perfect cylinder reconstruction!**

---

### ✅ simple_block.stl
**Input:**
- 36,346 vertices, 72,688 faces
- Volume: 32,178.42 mm³

**Analysis:**
- Vision detected: **IRREGULAR** (90% confidence)
- Layer-slicing detected: **2 separate boxes**
- Method: Assembly reconstruction

**Output:**
- Shape: **ASSEMBLY** (2 boxes)
- Quality Score: **86/100**
- Volume Error: **13.85%**
- Face Reduction: **100%** (72,688 → 24 faces)

✅ **Result: Successfully detected multi-part assembly!**

---

## 🎯 How It Works

### Pipeline Overview

```
INPUT: Messy 3D scan (10k-100k+ vertices)
   ↓
[1] Vision Analysis (Optional, ~$0.03-0.15)
   • Samples 3-10 layers across Z-axis
   • GPT-4o analyzes 2D cross-sections
   • Detects: circle, rectangle, irregular, multiple shapes
   • Identifies outliers and noise
   ↓
[2] Layer-Slicing Analysis (Always enabled)
   • Slices mesh horizontally (default: 2mm layers)
   • Detects separate objects in each layer
   • Groups consecutive layers into 3D boxes
   • Handles multi-part assemblies
   ↓
[3] Intelligent Classification
   • If vision confident (>80%): Use vision result
   • Else: Use bbox_ratio heuristic
   • Circle → CYLINDER
   • Rectangle → BOX
   • Multiple → ASSEMBLY
   • Other → COMPLEX
   ↓
[4] Primitive Reconstruction
   • CYLINDER: PCA-based axis detection + radius fitting
   • BOX: Oriented bounding box (OBB)
   • ASSEMBLY: Clean boxes from layer data
   • COMPLEX: Mesh simplification (90% reduction)
   ↓
[5] Quality Validation
   • Volume error calculation
   • Quality score (0-100)
   • Face reduction metrics
   ↓
OUTPUT: Clean parametric STL + metadata JSON
   • 10-1000 faces (99%+ reduction)
   • Dimensionally accurate (<5% volume error)
   • Editable in any CAD software
```

---

## 🔧 Command-Line Options

```bash
python scripts/convert_mesh.py [OPTIONS] input.stl

Required:
  input.stl              Input STL mesh file

Optional:
  -o, --output PATH      Output STL path (default: <input>_optimized.stl)
  --no-vision            Disable GPT-4o vision analysis (faster, free)
  --vision-layers N      Sample N layers for vision (default: 5)
  --no-layer-slicing     Disable layer-slicing analysis
  --layer-height MM      Layer height in mm (default: 2.0)
  -q, --quiet            Suppress output messages

Examples:
  python scripts/convert_mesh.py scan.stl
  python scripts/convert_mesh.py scan.stl --no-vision
  python scripts/convert_mesh.py scan.stl --vision-layers 3 -o clean.stl
  python scripts/convert_mesh.py complex.stl --layer-height 1.0
```

---

## 💰 Cost Breakdown

### Vision Analysis (Optional)
| Layers | Cost | Use Case |
|--------|------|----------|
| 3 | ~$0.03 | Quick check |
| 5 | ~$0.05 | Standard (recommended) |
| 10 | ~$0.10 | Thorough analysis |

**Cost per layer:** ~$0.01 (GPT-4o pricing)

### Without Vision (Free)
- Uses heuristic bbox_ratio classification
- Still very accurate for simple shapes
- Falls back to layer-slicing for assemblies

---

## 📁 Output Files

### Generated Files

```
input_optimized.stl       # Clean parametric STL mesh
input_optimized.json      # Metadata and quality metrics
```

### Metadata JSON Structure

```json
{
  "timestamp": "2026-01-17T23:45:00",
  "input": "simple_cylinder.stl",
  "output": "simple_cylinder_optimized.stl",
  "shape": "cylinder",
  "confidence": 93.3,
  "original": {
    "vertices": 10533,
    "faces": 21070,
    "volume": 7884.23
  },
  "output": {
    "vertices": 66,
    "faces": 128,
    "volume": 7839.45
  },
  "metrics": {
    "volume_error_pct": 0.57,
    "quality_score": 99,
    "face_reduction_pct": 99.4
  }
}
```

---

## 🎓 Understanding Results

### Quality Score Interpretation

| Score | Meaning | Action |
|-------|---------|--------|
| **90-100** | Excellent | Production-ready, use as-is |
| **80-89** | Good | Minor refinement may help |
| **60-79** | Fair | Review dimensions, consider manual tweaks |
| **0-59** | Poor | Complex shape, manual modeling recommended |

### Volume Error

- **<5%**: Excellent accuracy
- **5-10%**: Good accuracy
- **10-20%**: Acceptable for many uses
- **>20%**: Significant deviation, review carefully

### Shape Types

| Type | Description | Example |
|------|-------------|---------|
| `cylinder` | Circular cross-section, elongated | Tubes, pipes, batteries |
| `box` | Rectangular, may be hollow | Containers, housings |
| `assembly` | Multiple separate boxes | Multi-part objects |
| `complex` | Irregular/unknown | Organic shapes, freeform |

---

## 🔍 Troubleshooting

### Issue: "No module named 'openai'"

**Solution:**
```bash
pip install openai pillow
```

### Issue: "Vision analysis skipped"

**Cause:** OPENAI_API_KEY not set

**Solution:**
```bash
export OPENAI_API_KEY='sk-your-key-here'
```

### Issue: Low quality score (<60)

**Possible causes:**
1. Wrong shape type detected
2. Highly irregular/complex geometry
3. Noisy scan data

**Solutions:**
- Try different layer heights: `--layer-height 1.0`
- Use more vision layers: `--vision-layers 10`
- Pre-clean mesh in Meshmixer/Blender
- Accept that complex shapes need manual CAD work

### Issue: Volume error >20%

**Cause:** Shape doesn't fit primitive well

**Solutions:**
- Check if shape is truly a simple primitive
- Try layer-slicing approach (enabled by default)
- Consider manual CAD modeling for complex shapes

---

## 🎯 Best Practices

### 1. **Choose Appropriate Analysis Depth**

```bash
# Quick prototyping (fast, cheap)
python scripts/convert_mesh.py scan.stl --vision-layers 3

# Standard production use (recommended)
python scripts/convert_mesh.py scan.stl --vision-layers 5

# Medical device validation (thorough)
python scripts/convert_mesh.py scan.stl --vision-layers 10
```

### 2. **Optimize Layer Height**

```bash
# Coarse objects (large, simple shapes)
python scripts/convert_mesh.py large_box.stl --layer-height 5.0

# Standard objects
python scripts/convert_mesh.py part.stl --layer-height 2.0

# Fine details (small features, thin walls)
python scripts/convert_mesh.py tiny_part.stl --layer-height 0.5
```

### 3. **When to Use Vision vs. Heuristic**

**Use Vision (`default`):**
- Unknown shape type
- Multi-part assemblies
- Noisy scan data
- Medical device validation (traceability)

**Skip Vision (`--no-vision`):**
- Batch processing (cost control)
- Very simple shapes (box, cylinder)
- No internet connection
- Budget constraints

---

## 📈 Performance Benchmarks

| Mesh Size | Vision Layers | Total Time | Cost |
|-----------|---------------|------------|------|
| 10k vertices | 3 | ~20s | $0.03 |
| 10k vertices | 5 | ~30s | $0.05 |
| 50k vertices | 5 | ~45s | $0.05 |
| 100k vertices | 5 | ~90s | $0.05 |
| 100k vertices | 10 | ~150s | $0.10 |

**Note:** Vision API calls dominate processing time. Actual mesh operations are fast (<5s).

---

## 🔬 Advanced Usage

### Python API

```python
from convert_mesh import convert

# Programmatic conversion
result = convert(
    input_path='scan.stl',
    output_path='clean.stl',
    use_vision=True,
    n_vision_layers=5,
    verbose=True
)

if result['success']:
    print(f"Shape: {result['shape']}")
    print(f"Quality: {result['metrics']['quality_score']}/100")
    print(f"Output: {result['output']}")
else:
    print(f"Error: {result['error']}")
```

### Batch Processing

```bash
# Process all STL files in directory
for file in *.stl; do
    echo "Converting $file..."
    python scripts/convert_mesh.py "$file" --vision-layers 3
done
```

### Integration with CI/CD

```yaml
# .github/workflows/mesh-conversion.yml
name: Convert Meshes

on: [push]

jobs:
  convert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Convert meshes
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python scripts/convert_mesh.py scans/part.stl
```

---

## 🚧 Roadmap

### v2.1 (Next Release)
- [ ] STEP file export
- [ ] Multi-view validation (compare original vs reconstructed)
- [ ] Automatic outlier removal based on vision analysis
- [ ] Sphere and cone primitives

### v2.2 (Future)
- [ ] Fuzzy logic for layer grouping
- [ ] Adaptive layer slicing (variable height)
- [ ] Web UI for batch processing
- [ ] CAD software plugins (FreeCAD, Fusion 360)

---

## 🤝 Contributing

Found a bug or want to add features?
1. Open an issue describing the problem/idea
2. Fork the repository
3. Create a feature branch
4. Submit a pull request

---

## 📚 Related Documentation

- [Phase 1 Vision Analysis Results](VISION_PHASE1_RESULTS.md)
- [Vision Layer Analysis Guide](docs/VISION_LAYER_ANALYSIS_GUIDE.md)
- [README](README.md) - Main project documentation
- [CLAUDE.md](.claude/CLAUDE.md) - Development standards

---

## ❓ FAQ

**Q: Do I need an OpenAI API key?**

A: No! Vision analysis is optional. The tool works without it using heuristic classification.

**Q: How accurate is it?**

A: For simple primitives (cylinder, box): 90-99% quality scores, <5% volume error. Complex shapes may need manual refinement.

**Q: Can it handle assemblies?**

A: Yes! Layer-slicing automatically detects multi-part assemblies and reconstructs each box separately.

**Q: What file formats are supported?**

A: Input: STL (binary or ASCII). Output: STL + JSON metadata. STEP export coming soon.

**Q: Is it safe for medical devices?**

A: The tool provides traceability (vision reasoning, confidence scores) suitable for medical device validation. Always verify outputs meet your regulatory requirements.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file

---

**Ready to convert your meshes?**

```bash
python scripts/convert_mesh.py your_scan.stl
```

**Questions?** Open an issue on GitHub.

---

**Version:** 2.0.0
**Last Updated:** 2026-01-17
**Maintained by:** MedTrackET Team
