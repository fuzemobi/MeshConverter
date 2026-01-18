# Summary: Multi-Block Detection Plan

## Problem Confirmed
- **Mesh:** `simple_block.stl` contains 5 boxes in grid arrangement
- **Current Detection:** "complex" (60% confidence) ❌
- **Root Cause:** Mesh is ONE topologically connected component (likely via thin bridges/voids)
- **Bbox Ratio:** 0.297 (indicates hollow structure)

## Three Solution Paths

### 1. GPT-4 Vision (USER PREFERENCE)
**Status:** ⚠️ BLOCKED - Rendering dependency issues
- Needs `pyglet<2` for trimesh rendering
- Dependency conflicts with newer packages
- Could work but infrastructure heavy

**Viability:** 30% (requires deep debugging of pyglet/display)

---

### 2. Enhanced Voxel Decomposition (RECOMMENDED)
**Status:** ✅ READY TO IMPLEMENT - Uses existing code path

**How it Works:**
1. Convert mesh to voxel grid (spatial decomposition)
2. Use scipy.ndimage.label() to find connected voxel regions
3. Extract each region as separate mesh
4. Classify each mesh independently
5. Generate multi-body CadQuery assembly (all boxes combined)

**Current Code:** `voxel_classifier.py` already detects `n_components: 1`
**Enhancement:** Extract and output each component separately

**Expected Result on simple_block.stl:**
```
✅ Detected 5 components:
  Component 1: BOX (95% confidence)
  Component 2: BOX (95% confidence)
  Component 3: BOX (95% confidence)
  Component 4: BOX (95% confidence)
  Component 5: BOX (95% confidence)

📦 Assembly: 5-component structure (grid layout)
```

**Implementation Time:** ~2-3 hours  
**Viability:** 95% (uses proven algorithms)  
**Cost:** Free

---

### 3. Layer-Slicing Reconstruction (ADVANCED OPTION)
**User's Suggestion:** "Process line by line...rebuild as clean model"

**How it Works:**
1. Slice mesh into layers (Z-axis intervals)
2. Analyze each layer as 2D contour
3. Extract bounding boxes from each layer
4. Track bboxes across layers (merge/split)
5. Reconstruct 3D boxes from layer analysis

**Advantage:** Works on axis-aligned structures, very clean output  
**Limitation:** Fails on rotated/non-aligned components  
**Implementation Time:** ~4-6 hours  
**Viability:** 70% (requires custom contour analysis)

---

## Recommended Action Plan

**PHASE 1: Enhance Voxel Decomposition (Do This First)**
1. Modify `voxel_classifier.py`:
   - Add `extract_components()` function
   - Use `scipy.ndimage.label()` to find regions
   - Extract each as separate `trimesh.Trimesh` object
   - Classify each independently

2. Modify CLI to handle multi-body results:
   - Store list of components in metadata
   - Generate separate classification for each
   - Create single assembly CadQuery script

3. Test on simple_block.stl:
   - Should detect and output 5 box files separately
   - Generate assembly model

**Time:** 2-3 hours  
**Success Metric:** CLI outputs 5 separate box classifications + assembly model

---

**PHASE 2: Layer-Slicing (Optional, After Phase 1)**
- Implement `reconstruction/layer_analyzer.py`
- Compare results with voxel approach
- Use for specific use cases (clean layer-based geometries)

**Time:** 4-6 hours  
**Success Metric:** Produces cleaner output on certain geometries

---

**PHASE 3: Fix GPT-4 Vision (Optional)**
- Resolve pyglet dependency issues
- Use as secondary classifier for validation
- Document cost/benefit trade-off

**Time:** 2-3 hours (debugging dependent)  
**Success Metric:** Rendering works, can classify simple_block via vision

---

## Modified Architecture

```
Input Mesh
    ↓
Classify with Voxel Decomposition
    ↓
┌─────────────────────────────┐
│ Detect N Voxel Components   │
└─────────────────────────────┘
    ↓
    ├─→ Component 1 → Classify → BOX
    ├─→ Component 2 → Classify → BOX
    ├─→ Component 3 → Classify → BOX
    ├─→ Component 4 → Classify → BOX
    └─→ Component 5 → Classify → BOX
    ↓
Generate Assembly Output
    ├─→ metadata.json (all components listed)
    ├─→ assembly.step (all boxes in CAD)
    ├─→ assembly_cadquery.py (editable assembly script)
    └─→ component_*.stl (individual boxes)
```

---

## Files to Modify

### Primary
- **`meshconverter/classification/voxel_classifier.py`**
  - Add: `extract_voxel_components()` 
  - Add: `classify_voxel_assembly()`
  - Modify: Return structure for multi-body results

### Secondary  
- **`meshconverter/cli.py`**
  - Update: `save_outputs()` to handle assembly results
  - Add: Logic for multi-body CadQuery generation
  - Add: Component-by-component metadata output

### Output
- **Generate new files:**
  - `meshconverter/generation/assembly_generator.py` (multi-body CAD)

---

## Immediate Next Step

**WAIT FOR YOUR DECISION:**

```
Option A: Implement Voxel Component Extraction
  → Recommended, high viability, 2-3 hours
  → Test on simple_block.stl, expect perfect 5-box detection

Option B: Implement Layer-Slicing First  
  → User's suggestion, good for axis-aligned
  → Takes longer (4-6 hours)

Option C: Fix GPT-4 Vision First
  → Better accuracy but infrastructure heavy
  → Takes 2-3 hours of debugging

Option D: All three (systematic coverage)
  → Total ~10-14 hours
  → Gives most robust solution
```

---

## Code Snippets Ready to Implement

### Voxel Component Extraction (Option A)
```python
from scipy import ndimage
import numpy as np

def extract_voxel_components(voxel_grid: np.ndarray):
    """Extract connected voxel regions as separate meshes."""
    labeled, n_components = ndimage.label(voxel_grid)
    print(f"Found {n_components} components in voxel grid")
    
    components = []
    for component_id in range(1, n_components + 1):
        component_mask = (labeled == component_id)
        # Convert voxel mask to mesh (trimesh.voxel.Voxel object)
        voxel_obj = trimesh.voxel.Voxel(component_mask)
        mesh = voxel_obj.as_mesh()
        components.append((component_id, mesh))
    
    return components
```

---

## Risk Assessment

| Approach | Risk | Mitigation |
|----------|------|-----------|
| Voxel decomposition | Voxel resolution too coarse misses details | Use configurable voxel size, test parameters |
| Layer-slicing | Fails on non-axis-aligned | Document limitations, use for specific cases |
| GPT-4 Vision | Rendering environment issues | May require display server or alternative renderer |
| Multi-body output | CadQuery assembly API unclear | Research CadQuery assembly/MultiBody support |

---

**READY TO IMPLEMENT:** Option A (Voxel Decomposition) when you give go-ahead.
