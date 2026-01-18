# Vision-Based Layer Analysis - User Guide

**AI-powered outlier detection and shape validation using GPT-4o**

---

## 🚀 Quick Start

### Prerequisites
```bash
# 1. Install dependencies (if not already done)
pip install openai pillow trimesh

# 2. Set your OpenAI API key
export OPENAI_API_KEY='sk-...'
```

### Basic Usage

```bash
# Analyze a mesh with 5 sample layers (recommended)
python test_vision_layer_analysis.py your_mesh.stl --num-layers 5

# Quick analysis (3 layers, ~$0.03)
python test_vision_layer_analysis.py your_mesh.stl --num-layers 3

# Thorough analysis (10 layers, ~$0.10)
python test_vision_layer_analysis.py your_mesh.stl --num-layers 10
```

---

## 📖 Python API Usage

### Standalone Layer Analysis

```python
from meshconverter.reconstruction.vision_layer_analyzer import analyze_layer_with_vision
import trimesh

# Load mesh
mesh = trimesh.load('your_mesh.stl')

# Slice at specific height
section = mesh.section(
    plane_origin=[0, 0, 400.0],  # Z height
    plane_normal=[0, 0, 1]       # Vertical slice
)

# Analyze with vision
result = analyze_layer_with_vision(
    section=section,
    z_height=400.0,
    layer_id=0
)

print(f"Shape: {result['shape_detected']}")
print(f"Outliers: {result['has_outliers']} ({result['outlier_percentage']}%)")
print(f"Confidence: {result['confidence']}%")
```

### Using the VisionLayerAnalyzer Class

```python
from meshconverter.reconstruction.vision_layer_analyzer import VisionLayerAnalyzer
import trimesh
import os

# Initialize analyzer
analyzer = VisionLayerAnalyzer(api_key=os.getenv('OPENAI_API_KEY'))

# Load and slice mesh
mesh = trimesh.load('cylinder.stl')
section = mesh.section(plane_origin=[0, 0, 400], plane_normal=[0, 0, 1])

# Analyze for outliers
result = analyzer.analyze_layer_for_outliers(
    section=section,
    z_height=400.0,
    layer_id=5,
    verbose=True
)

# Act on results
if result['has_outliers'] and result['outlier_percentage'] > 5:
    print(f"⚠️  Warning: {result['outlier_percentage']:.1f}% outliers detected!")
    print(f"   Reasoning: {result['reasoning']}")
    # TODO: Apply outlier filtering
```

### Multi-View Validation (Original vs Reconstructed)

```python
from meshconverter.reconstruction.vision_layer_analyzer import VisionLayerAnalyzer
import trimesh

analyzer = VisionLayerAnalyzer()

original_mesh = trimesh.load('scanned_part.stl')
reconstructed_mesh = trimesh.creation.cylinder(radius=10, height=50)

validation = analyzer.analyze_multi_view_validation(
    original_mesh=original_mesh,
    reconstructed_mesh=reconstructed_mesh,
    verbose=True
)

print(f"Similarity: {validation['similarity_score']}/100")
print(f"Quality: {validation['reconstruction_quality']}")
print(f"Differences: {validation['differences_noted']}")
```

---

## 📊 Understanding Results

### Result Dictionary Structure

```python
{
    'has_outliers': bool,              # True if outliers detected
    'outlier_percentage': float,       # 0-100% of points that are outliers
    'shape_detected': str,             # 'rectangle', 'circle', 'ellipse', 'irregular', 'multiple'
    'shape_count': int,                # Number of distinct shapes (1, 2, 3+)
    'confidence': int,                 # 0-100% confidence score
    'reasoning': str,                  # GPT-4o's explanation
    'main_region_bounds': dict         # Bounding box of main shape (optional)
}
```

### Shape Types

| Shape Type | Description | Example Use Case |
|------------|-------------|------------------|
| `rectangle` | 4-sided polygon, right angles | Box cross-sections |
| `circle` | Circular outline | Cylinder cross-sections |
| `ellipse` | Oval shape | Angled cylinder or compressed shape |
| `irregular` | Non-standard geometry | Complex parts, hollow structures |
| `multiple` | 2+ separate shapes | Assemblies, multi-part scans |

### Interpreting Confidence Scores

| Confidence | Interpretation | Action |
|------------|----------------|--------|
| **90-100%** | Very certain | Trust the classification |
| **70-89%** | Fairly confident | Generally reliable, verify if critical |
| **50-69%** | Uncertain | Manual review recommended |
| **0-49%** | Low confidence | Likely complex/ambiguous shape |

---

## 💰 Cost Estimation

### OpenAI Pricing (as of Jan 2026)
- **GPT-4o**: ~$0.01 per image analysis
- **Each layer**: 1 image = ~$0.01

### Sample Cost Breakdown

| Analysis Type | Layers | Cost | Use Case |
|---------------|--------|------|----------|
| **Quick check** | 3 | ~$0.03 | Initial validation |
| **Standard** | 5 | ~$0.05 | Normal quality check |
| **Thorough** | 10 | ~$0.10 | Medical device validation |
| **Complete** | 50 | ~$0.50 | Full scan analysis |
| **Multi-view validation** | - | ~$0.06 | Original vs reconstructed (6 images) |

### Cost Optimization Tips

1. **Sample strategically**: Analyze evenly-spaced layers, not every layer
2. **Start small**: Test with 3-5 layers first
3. **Use thresholds**: Only analyze critical regions
4. **Cache results**: Save vision results to avoid re-analyzing

---

## 🔧 Advanced Configuration

### Custom Prompts

You can customize the analysis prompt by modifying the `analyze_layer_for_outliers` method:

```python
# In vision_layer_analyzer.py, modify the prompt:
prompt = f"""Analyze this 2D cross-section...

**CUSTOM INSTRUCTIONS:**
- Focus on medical device components
- Flag any geometric irregularities >2mm
- Prioritize safety-critical features

**Answer in JSON format:**
...
"""
```

### Image Rendering Settings

```python
# Adjust resolution (higher = more detail, slower)
img_bytes = analyzer.render_2d_section_to_image(
    section=section,
    resolution=1024,  # Default: 512
    padding=0.15      # Default: 0.1 (10% padding)
)
```

### API Parameters

```python
response = self.client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    max_tokens=300,      # Adjust for longer responses
    temperature=0.0      # 0 = deterministic, 1 = creative
)
```

---

## 🎯 Use Cases

### 1. **Outlier Detection Before Reconstruction**

```python
# Check for scan noise before processing
result = analyze_layer_with_vision(section, z, layer_id)

if result['outlier_percentage'] > 10:
    print("⚠️  High noise detected, applying cleanup...")
    # Apply statistical filtering or RANSAC
```

### 2. **Shape Validation During Layer Analysis**

```python
# Verify expected shape consistency
shapes = []
for i, z in enumerate(z_values):
    section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    result = analyze_layer_with_vision(section, z, i)
    shapes.append(result['shape_detected'])

# Check consistency
if len(set(shapes)) > 2:
    print("⚠️  Inconsistent shapes detected across layers")
```

### 3. **Assembly Detection**

```python
# Detect multi-part assemblies
result = analyze_layer_with_vision(section, z, layer_id)

if result['shape_count'] > 1:
    print(f"✅ Assembly detected: {result['shape_count']} parts")
    # Route to multi-primitive reconstruction
```

### 4. **Quality Assurance Report**

```python
# Generate validation report
layers_analyzed = []
for i in range(n_layers):
    result = analyze_layer_with_vision(sections[i], z_values[i], i)
    layers_analyzed.append(result)

# Statistics
avg_confidence = np.mean([r['confidence'] for r in layers_analyzed])
outlier_count = sum(1 for r in layers_analyzed if r['has_outliers'])

print(f"Quality Report:")
print(f"  Average confidence: {avg_confidence:.1f}%")
print(f"  Layers with outliers: {outlier_count}/{n_layers}")
```

---

## ⚠️ Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'openai'"

**Solution:**
```bash
pip install openai pillow
```

### Issue: "OPENAI_API_KEY not set"

**Solution:**
```bash
# Set temporarily
export OPENAI_API_KEY='sk-your-key-here'

# Or set permanently in ~/.bashrc or ~/.zshrc
echo "export OPENAI_API_KEY='sk-your-key-here'" >> ~/.bashrc
source ~/.bashrc
```

### Issue: "Model 'gpt-4-vision-preview' not found"

**Solution:**
Update to GPT-4o (already done in latest code):
```python
model="gpt-4o"  # Not "gpt-4-vision-preview"
```

### Issue: "Failed to render view"

**Possible causes:**
- Empty cross-section (no vertices at that Z height)
- Invalid mesh geometry

**Solution:**
```python
if section is None or len(section.vertices) == 0:
    print("⚠️  Skipping empty layer")
    continue
```

### Issue: "API rate limit exceeded"

**Solution:**
Add delays between requests:
```python
import time
for i, z in enumerate(z_values):
    result = analyze_layer_with_vision(...)
    time.sleep(1)  # 1 second delay
```

---

## 📈 Performance Tips

### 1. **Batch Processing**

```python
# Process multiple meshes efficiently
meshes = ['part1.stl', 'part2.stl', 'part3.stl']
analyzer = VisionLayerAnalyzer()  # Reuse instance

for mesh_path in meshes:
    mesh = trimesh.load(mesh_path)
    # ... analyze layers
```

### 2. **Caching Results**

```python
import json

# Save results
results = analyze_layer_with_vision(...)
with open('layer_analysis_cache.json', 'w') as f:
    json.dump(results, f)

# Load cached results
with open('layer_analysis_cache.json', 'r') as f:
    results = json.load(f)
```

### 3. **Parallel Processing** (Future Enhancement)

```python
# TODO: Process multiple layers in parallel
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(analyze_layer_with_vision, section, z, i)
               for i, (section, z) in enumerate(layers)]
    results = [f.result() for f in futures]
```

---

## 🔐 Security & Privacy

### API Key Security
- ✅ **Use environment variables** (never hardcode keys)
- ✅ **Add `.env` to `.gitignore`**
- ✅ **Rotate keys** periodically
- ❌ **Never commit** API keys to version control

### Data Privacy
- 🔒 Images are sent to OpenAI API (see [OpenAI Privacy Policy](https://openai.com/policies/privacy-policy))
- 🔒 For HIPAA compliance: Use OpenAI's Business tier with BAA
- 🔒 For sensitive designs: Consider on-premise AI alternatives

---

## 📚 Further Reading

- **OpenAI GPT-4o Documentation**: https://platform.openai.com/docs/guides/vision
- **Trimesh Documentation**: https://trimsh.org/
- **PIL/Pillow Image Library**: https://pillow.readthedocs.io/

---

## 🤝 Contributing

Found a bug or have a feature request?
1. Check existing issues
2. Create a new issue with details
3. Submit a pull request

---

## 📄 License

MIT License - See [LICENSE](../LICENSE) file for details

---

**Questions?** Open an issue or contact the MeshConverter team.
