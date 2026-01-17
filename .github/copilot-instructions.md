# MeshConverter - AI Agent Instructions

## Project Overview

MeshConverter converts **complex noisy 3D scans into simple, clean geometric shapes** (STL files) that are easy to manipulate in CAD software like FreeCAD.

**Core Mission:** Given a scanned mesh (10k-100k+ vertices), intelligently detect what simple shape(s) it represents (cylinder, box, sphere), then output a clean simplified mesh with parameters you can edit in any CAD tool.

**Value Prop:** No more wrestling with noisy scan data in FreeCAD. Get production-ready parametric geometry automatically.

---

## Architecture & Data Flow

### How It Works (Pipeline)

```
Noisy Input STL (10k-100k vertices)
   ↓
[Step 1] Analyze Geometry
   ├─ Extract volume, surface area, bounds
   ├─ Calculate bounding box ratio (MAGIC METRIC)
   └─ Compute aspect ratios & PCA axes
   ↓
[Step 2] Classify Shape (AI + Heuristic)
   ├─ Query similar training examples (few-shot learning)
   ├─ Send mesh stats to OpenAI for classification
   ├─ Fall back to heuristic if API unavailable
   └─ Output: { shape_type: "cylinder|box|sphere", confidence: 0-100 }
   ↓
[Step 3] Fit Geometry to Shape
   ├─ For cylinder: Use PCA to find axis, measure radius
   ├─ For box: Use oriented bounding box
   └─ For sphere: Fit to vertices using least squares
   ↓
[Step 4] Simplify Mesh
   ├─ Quadric edge decimation (target: 1000-5000 faces)
   └─ Preserve detected shape during simplification
   ↓
Clean Output STL + Parameters
```

### The Magic Metric: Bounding Box Ratio

**Formula:** `mesh_volume / bounding_box_volume`

This single metric is the most reliable way to classify shapes because:
- **Cylinder:** 0.4-0.8 (empty space around circular cross-section)
- **Solid Box:** 0.95-1.0 (fills its bounding box)
- **Hollow Box:** 0.2-0.4 (mostly empty inside)
- **Sphere:** ~0.52 (π/6, mathematically constant)

### Training & Few-Shot Learning

**TrainingManager** (`training_manager.py`):
- Loads `training_data.json` with 3+ known examples (cylinders, boxes)
- Given a new mesh, finds the 3 most similar examples via similarity matching
- Sends those examples to OpenAI as context for shape classification
- Falls back to heuristic classification (bbox ratio + PCA) if API unavailable
- Stores validation results to continuously improve accuracy

---

## Critical Workflows & Commands

### Development Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux; Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify key imports
python3 -c "import trimesh; import sklearn; print('✅ Ready')"
```

### Main Workflow: Converting a 3D Scan

```bash
# Step 1: Run AI shape classification (to see what shape it detected)
python mesh_to_cad_v2.py your_scanned_part.stl --train

# This outputs:
# - Console: Detected shape, confidence, reasoning
# - *_classification.json: Full classification details
# - If cylinder: Shows detected radius, length

# Step 2: Convert to clean parametric model
python mesh_to_cad.py your_scanned_part.stl output_clean.stl

# This outputs:
# - output_clean_parametric.stl (simplified: ~1000 faces, easy to edit in CAD)
# - output_clean_parametric_cadquery.py (parametric script with dimensions)
```

### Understanding the Two Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `mesh_to_cad_v2.py` | **Classify shape type** using AI + training data | Any STL | Classification JSON, console output |
| `mesh_to_cad.py` | **Convert to CAD** (simplified mesh + CadQuery script) | STL | `*_parametric.stl`, `*_cadquery.py` |

### Training Data Management

```bash
# Add a known-good example to training data
python training_manager.py add your_part.stl cylinder

# View all training examples
python training_manager.py list

# Show statistics
python training_manager.py stats

# Test accuracy across all training examples
python train_and_test.py test --evaluate
```

### Batch Processing

```bash
# Convert all STL files in directory
for f in *.stl; do
    echo "Converting $f..."
    python mesh_to_cad_v2.py "$f" --train
    python mesh_to_cad.py "$f"
done
```

---

## Code Patterns & Conventions

### Type Hints & Documentation (Mandatory)

```python
def fit_cylinder_to_mesh(mesh: trimesh.Trimesh) -> dict[str, Any]:
    """
    Fit a cylinder to mesh using PCA analysis.
    
    Args:
        mesh: Input trimesh object
    
    Returns:
        Dict with keys: radius, length, center (np.ndarray), axis (np.ndarray)
    
    Raises:
        ValueError: If mesh is empty or invalid
    """
```

All public functions require:
- Type hints on parameters and return values
- Google-style docstrings with Args/Returns/Raises
- Clear variable names (no abbreviations)

### Shape Fitting Algorithm Pattern

```python
def fit_<shape>_to_mesh(mesh: trimesh.Trimesh) -> dict[str, Any]:
    print(f"\nFitting {shape} to mesh...")
    
    # 1. Extract key geometry
    # 2. Apply algorithm (PCA, bounding box, etc.)
    # 3. Extract parameters
    # 4. Validate results
    print(f"  Detected {shape}:")
    print(f"    Param1: {value1:.2f} mm")
    print(f"    Param2: {value2:.2f} mm")
    
    return { 'param1': value1, 'param2': value2, ... }
```

**Validation Rules:**
- All dimensions in millimeters (mm)
- Axis vectors should be unit vectors (norm ≈ 1.0)
- Print progress to console for user feedback

### Heuristic Shape Classification (Required Fallback)

Always provide a working fallback when AI/API unavailable:

```python
def heuristic_shape_classification(mesh_stats: dict) -> dict:
    """Classify shape using bbox ratio + PCA (no AI required)"""
    bbox_ratio = mesh_stats.get('bbox_to_mesh_ratio', 1.0)
    
    # Solid box: fills bounding box
    if 0.9 <= bbox_ratio <= 1.05:
        return {"shape_type": "box", "confidence": 90}
    
    # Sphere: special mathematical ratio
    elif 0.48 <= bbox_ratio <= 0.56:
        return {"shape_type": "sphere", "confidence": 90}
    
    # Cylinder: medium ratio + elongated
    elif 0.4 <= bbox_ratio <= 0.85 and mesh_stats.get('is_elongated'):
        return {"shape_type": "cylinder", "confidence": 80}
    
    # Fallback to complex
    else:
        return {"shape_type": "complex", "confidence": 60}
```

### Console Output Standards

Every script should print clear progress:

```
🔍 Loading mesh from battery.stl...
Original mesh stats:
  Vertices: 86,541
  Faces: 173,078
  Volume: 12,861.69 mm³
  Bounding Box Ratio: 0.623

🤖 AI Shape Classification with Few-Shot Learning...
  Found 3 similar training examples
✅ Shape Classification:
  Shape Type: CYLINDER
  Confidence: 95%
  Reasoning: Bounding box ratio 0.623 indicates cylinder

💾 Classification saved to: battery_classification.json
```

---

## Integration Points & Dependencies

### Essential Libraries (in requirements.txt)

| Library | Purpose | Why We Need It |
|---------|---------|----------------|
| `trimesh` | Mesh loading & manipulation | Load STL, simplify, export |
| `numpy` | Numerical computing | Matrix operations, PCA |
| `scikit-learn` | PCA for axis detection | Find principal axes for cylinders |
| `scipy` | Scientific computing | Rotation transformations |
| `fast-simplification` | Mesh decimation | Reduce faces while preserving shape |
| `openai` | AI shape classification | Optional; project works without it |
| `python-dotenv` | Load `.env` for API keys | Secure API key management |

**Critical Notes:**
- CadQuery and open3d are commented out (Python 3.12+ compatibility issues)
- OpenAI API key loaded from `.env` file (never committed to git)
- Core functionality works offline (heuristic fallback for no API)
- All imports at module level with error handling

### MeshXL Integration (Training Data Only)

**Purpose:** Extract diverse ShapeNet examples to improve AI classification

**Data Location:** `MeshXL/data/shapenet_*/` (.npz compressed mesh format)

**Workflow:**
```bash
python meshxl_extractor.py --input MeshXL/data --output training_data/stl --samples 20
```

**What it does:**
- Converts `.npz` files → `.stl` format
- Calculates bbox ratios + PCA axes for classification
- Adds metadata to training library
- Enables few-shot learning with diverse examples

---

## Project-Specific Conventions

### Naming Conventions

- **Files:** `snake_case.py` (Python); `*_parametric.stl` for outputs; `*_cadquery.py` for scripts
- **Variables:** `descriptive_names` (no abbreviations); geometry params use full names (`radius`, `length`, not `r`, `l`)
- **Functions:** `action_noun_phrase()` like `fit_cylinder_to_mesh()`, `calculate_bbox_ratio()`
- **Constants:** `UPPERCASE_WITH_UNDERSCORES` (e.g., `END_SAMPLE_PERCENTAGE = 0.15`)

### Output Dimensions

**Always use millimeters (mm)** as the unit:
```python
# ✅ CORRECT
radius = 10.5  # mm
# ❌ WRONG
radius = 10.5  # Could be mm, inches, or undefined
```

Console output includes units:
```
Detected cylinder:
  Radius: 10.5 mm
  Length: 50.0 mm
  Center: [0.0, 0.0, 25.0] mm
```

### Error Handling & Fallbacks

```python
# AI shape classification with graceful degradation
client = get_openai_client()
if not client:
    print("⚠️  OpenAI not available, using heuristic classification")
    return heuristic_shape_classification(mesh_stats)
```

Always provide fallback behavior (heuristic algorithms) when AI/API unavailable.

---

## Key Files to Reference

- **[CLAUDE.md](../CLAUDE.md)** — Detailed code standards, algorithm specs, geometry formulas
- **[mesh_to_cad_v2.py](../mesh_to_cad_v2.py)** — Main orchestrator + AI integration
- **[training_manager.py](../training_manager.py)** — Few-shot learning system
- **[meshxl_extractor.py](../meshxl_extractor.py)** — ShapeNet data extraction + heuristic classification
- **[training_data.json](../training_data.json)** — Labeled examples for learning
- **[requirements.txt](../requirements.txt)** — Complete dependency list

---

## Common Tasks for AI Agents

### Adding a New Shape Type

1. Create `fit_<shape>_to_mesh()` function following algorithm pattern
2. Add detection heuristic to `heuristic_shape_classification()`
3. Update `TrainingManager` schema if new parameters needed
4. Add test cases to validate accuracy
5. Update few-shot learning prompts in `ai_classify_shape()`

### Improving Classification Accuracy

1. Review failing cases in console output
2. Add new training examples with ground truth dimensions
3. Adjust detection heuristics (bbox ratio thresholds, PCA ratios)
4. Run `python train_and_test.py test --evaluate`
5. Verify >80% confidence before commit

### Debugging Shape Detection

1. Check console output for detected parameters and bbox ratio
2. Compare bbox ratio against known ranges (0.95+ for box, 0.4-0.8 for cylinder, ~0.52 for sphere)
3. Verify PCA axes are correctly aligned
4. Add debug saves: `mesh.export('debug_before.stl')`
5. Check volume: `mesh.volume` should be positive and reasonable

---

## Dependency & Environment Notes

- **Python Version:** 3.8+ required (3.10+ recommended); 3.12+ may need CadQuery updates
- **Virtual Environment:** Always use `venv` or `conda` to isolate dependencies
- **OpenAI API:** Optional; project works without it (heuristic fallback)
- **MeshXL Data:** 5+ GB; download only needed for training data enrichment
- **macOS-Specific:** Use `source venv/bin/activate` (not `.\\venv\\Scripts\\activate`)
