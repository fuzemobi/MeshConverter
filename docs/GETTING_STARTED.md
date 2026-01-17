# Getting Started with MeshConverter V2

**Quick setup guide for new developers**

---

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- git
- 500MB free disk space

---

## Step 1: Installation (5 minutes)

```bash
# Navigate to v2 directory
cd meshconverter/v2

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import trimesh; import numpy; import sklearn; print('✅ All dependencies installed!')"
```

---

## Step 2: Understand The Project (10 minutes)

### Read These First:
1. [README.md](../README.md) - What the project does
2. [CLAUDE.md](../CLAUDE.md) - Development standards

### Key Concepts:

**Bounding Box Ratio = The Magic Number:**
```
ratio = mesh_volume / bounding_box_volume

0.297 → Hollow Box
0.426 → Cylinder
0.523 → Sphere
```

**Pipeline:**
```
Load → Normalize → Detect Shape → Fit Primitive → Validate → Export
```

---

## Step 3: Run Your First Conversion (2 minutes)

```bash
# Test on cylinder example
python mesh_to_primitives.py ../simple_cylinder.stl -o output/test1

# Expected output:
# 🔍 Detecting: CYLINDER (bbox_ratio: 0.426)
# ✅ Quality: 94/100
# 📤 Exported to output/test1/

# Check results
ls output/test1/
# simple_cylinder_primitive.stl
# simple_cylinder_cadquery.py
# simple_cylinder_metadata.json
```

---

## Step 4: Understand The Code (30 minutes)

### Core Modules

**1. core/mesh_loader.py**
```python
# Loads STL files, repairs them, calculates bbox_ratio
loader = MeshLoader(config)
result = loader.load('file.stl')
print(result['stats']['bbox_ratio'])  # The key metric!
```

**2. primitives/box.py**
```python
# Fits oriented bounding box to mesh
box = BoxPrimitive()
box.fit(mesh)
print(box.extents)  # [length, width, height]
```

**3. detection/simple_detector.py**
```python
# Routes to correct primitive based on bbox_ratio
detector = SimpleDetector(config)
primitive, shape_type, confidence = detector.detect(mesh, stats)
```

---

## Step 5: Run Tests (5 minutes)

```bash
# Run all tests
pytest tests/ -v

# Expected output:
# tests/test_loader.py::test_load_valid_mesh PASSED
# tests/test_box.py::test_box_fit_on_cube PASSED
# tests/test_cylinder.py::test_cylinder_fit PASSED
# ==================== X passed in Y.YYs ====================
```

---

## Step 6: Make Your First Change (15 minutes)

### Exercise: Add a Print Statement

**File:** `core/mesh_loader.py`

**Before:**
```python
def _calculate_stats(self, mesh):
    """Calculate mesh statistics"""
    bounds = mesh.bounds
    # ...
```

**After:**
```python
def _calculate_stats(self, mesh):
    """Calculate mesh statistics"""
    bounds = mesh.bounds
    print(f"🔍 Calculating stats for mesh with {len(mesh.vertices)} vertices")
    # ...
```

**Test:**
```bash
python mesh_to_primitives.py ../simple_block.stl
# Should see: 🔍 Calculating stats for mesh with 36346 vertices
```

---

## Step 7: Development Workflow

### Daily Workflow:

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Pull latest changes (if working with team)
git pull

# 3. Create feature branch
git checkout -b feature/my-improvement

# 4. Make changes, run tests
pytest tests/ -v

# 5. Format code
black .

# 6. Commit
git add -A
git commit -m "feat: add sphere primitive detection"

# 7. Push
git push origin feature/my-improvement
```

---

## Common Tasks

### Add a New Primitive

**1. Create file:** `primitives/sphere.py`

**2. Inherit from base:**
```python
from .base import Primitive

class SpherePrimitive(Primitive):
    def fit(self, mesh):
        # Fit sphere to mesh
        pass

    def to_trimesh(self):
        # Generate trimesh sphere
        pass
```

**3. Add to detector:** `detection/simple_detector.py`
```python
if sphere_range[0] <= bbox_ratio <= sphere_range[1]:
    primitive_class = SpherePrimitive
```

**4. Write tests:** `tests/test_sphere.py`

**5. Run tests:** `pytest tests/test_sphere.py -v`

---

## Debugging Tips

### Enable Verbose Output

```bash
# Set log level in config.yaml
debug:
  verbose: true
  show_plots: true  # If matplotlib installed
```

### Check Intermediate Results

```python
# In mesh_to_primitives.py, add:
print(f"Mesh stats: {result['stats']}")
print(f"BBox ratio: {result['stats']['bbox_ratio']}")

# Or use debugger
import pdb; pdb.set_trace()
```

### Common Issues

**1. "ModuleNotFoundError: No module named 'trimesh'"**
```bash
# Forgot to activate venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. "File not found: simple_block.stl"**
```bash
# Wrong directory - examples are in parent folder
python mesh_to_primitives.py ../simple_block.stl  # Note the ../
```

**3. "Quality score: 45/100"**
```bash
# Wrong primitive type detected
# Check bbox_ratio in output
# May need to adjust thresholds in config.yaml
```

---

## Next Steps

Once you're comfortable:

1. **Read the full docs:**
   - [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Detailed implementation
   - [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture

2. **Implement a feature:**
   - Sphere primitive
   - Cone primitive
   - STEP file export
   - Thumbnail generation

3. **Improve quality:**
   - Better simplification strategy
   - Multi-primitive decomposition
   - Feature detection (holes, fillets)

---

## Resources

**Documentation:**
- [trimesh docs](https://trimsh.org/)
- [CadQuery tutorial](https://cadquery.readthedocs.io/)
- [scikit-learn PCA](https://scikit-learn.org/stable/modules/decomposition.html)

**Learning:**
- Computational geometry basics
- PCA for 3D shape analysis
- CAD file formats (STEP, STL, IGES)

---

## Questions?

1. Check [README.md](../README.md) FAQ section
2. Read [CLAUDE.md](../CLAUDE.md) for coding standards
3. Look at existing code examples
4. Ask in team chat/GitHub issues

---

**Welcome to MeshConverter V2! 🎉**

You're now ready to start contributing to production-grade CAD software for medical devices!
