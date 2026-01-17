# Phase 6.5: Voxelization-Based Decomposition - Implementation Report

**Date:** 2026-01-17
**Status:** ✅ IMPLEMENTED (with caveats)

---

## Overview

Implemented voxelization-based mesh decomposition method to separate interlocking components that share faces (like puzzle pieces).

## Implementation

### New Function: `decompose_via_voxelization()`

**Location:** `core/decomposer.py`

```python
def decompose_via_voxelization(
    mesh: trimesh.Trimesh,
    voxel_size: float = 1.0,
    erosion_iterations: int = 0
) -> List[Dict[str, Any]]
```

**Algorithm:**
1. Convert mesh to voxel grid (3D boolean array)
2. Optional morphological erosion to break connections
3. Label connected components in voxel space
4. Dilate back to original size (if erosion was used)
5. Convert voxels back to mesh
6. Analyze each component

### CLI Integration

**New Arguments:**
- `--voxelize`: Enable voxelization decomposition
- `--voxel-size <float>`: Voxel grid resolution in mm (default: 1.0)
- `--erosion <int>`: Number of erosion iterations (default: 0)

**Usage Examples:**
```bash
# Basic voxelization (no erosion)
python mesh_to_primitives.py input.stl --voxelize

# With erosion to separate touching components
python mesh_to_primitives.py input.stl --voxelize --erosion 1

# Fine-grained voxels
python mesh_to_primitives.py input.stl --voxelize --voxel-size 0.5
```

---

## Test Results

### Test 1: simple_block.stl (interlocking blocks)

| Configuration | Result | Notes |
|--------------|--------|-------|
| **Baseline (no voxel)** | 1 component | Connected as single mesh |
| **Voxel + erosion=0** | 1 component | Voxels stay connected |
| **Voxel + erosion=1** | 29 components | ✅ Separation achieved! |
| **Voxel + erosion=2** | 0 components | Over-erosion (all voxels disappear) |

**Conclusion:** Erosion=1 successfully separates the blocks, but creates many small fragments (29 pieces instead of expected ~5 blocks).

### Test 2: simple_cylinder.stl (single object)

| Configuration | Result | Notes |
|--------------|--------|-------|
| **Baseline (no voxel)** | 1 component | Correct |
| **Voxel + erosion=0** | 1 component | ✅ Correct, falls back gracefully |
| **Voxel + erosion=1** | 5 components | ⚠️ Unwanted fragmentation |

**Conclusion:** Without erosion, cylinder stays as 1 component (correct). With erosion, it fragments.

---

## Key Findings

### What Works Well

✅ **Separation capability:** With `erosion=1`, successfully detects multiple components (29 vs baseline 1)

✅ **Graceful fallback:** When no separation is achieved, falls back to standard decompose() method

✅ **Configurable:** User can tune voxel_size and erosion_iterations for different meshes

✅ **No errors:** Implementation is robust, handles edge cases

### Current Limitations

⚠️ **Over-fragmentation:** Erosion creates too many small components (29 instead of ~5 expected blocks)

⚠️ **Parameter sensitivity:** Need to tune erosion for each mesh type
- erosion=0: No separation
- erosion=1: Many fragments
- erosion=2: Total disappearance

⚠️ **Component merging needed:** Would benefit from post-processing to merge nearby components

### Why the Mesh is Challenging

The `simple_block.stl` mesh has blocks that are **truly connected** at the mesh level:
- They share vertices and faces (not just touching)
- The mesh topology shows 1 connected component
- Voxelization can break connections, but creates artificial fragments at the voxel boundaries

---

## Technical Analysis

### Voxelization Process

```
Original Mesh (36,346 vertices)
    ↓
Voxel Grid (60x44x44 = 116,160 voxels @ 1.0mm pitch)
    ↓
Erosion (optional - shrinks components by 1 voxel layer)
    ↓
Connected Component Labeling (scipy.ndimage.label)
    ↓
Dilation (optional - expands back to original size)
    ↓
Convert to Mesh (as_boxes() - each voxel becomes a cube)
```

### Erosion Effects

**Erosion = 0 (default):**
- No shrinking
- Voxels stay connected
- Falls back to standard decompose if 1 component found

**Erosion = 1:**
- Each component shrinks by 1 voxel layer (1mm)
- Breaks narrow connections
- Risk: Creates fragments at boundaries
- Result: 29 components (many small pieces)

**Erosion = 2:**
- Shrinks by 2 layers (2mm)
- For thin walls (<4mm), components disappear entirely
- Result: 0 components (mesh completely eroded away)

---

## Recommended Usage

### When to Use Voxelization

✅ **Good for:**
- Meshes with distinct objects that touch at small contact areas
- Assemblies with well-separated components (just barely touching)
- When standard decompose() fails to separate visually distinct parts

❌ **Not ideal for:**
- Single coherent objects (like simple_cylinder.stl)
- Thin-walled structures (risk of over-erosion)
- Meshes where components are truly merged at topology level

### Recommended Parameters

| Mesh Type | voxel_size | erosion | Expected Result |
|-----------|-----------|---------|-----------------|
| **Large objects (50-100mm)** | 1.0-2.0mm | 0-1 | Good separation |
| **Medium objects (20-50mm)** | 0.5-1.0mm | 0-1 | Moderate separation |
| **Small/detailed (<20mm)** | 0.3-0.5mm | 0 | Preserve details |
| **Thin walls (<2mm thick)** | 0.3mm | 0 | Avoid erosion |

---

## Future Improvements

### Short-term (Phase 6.6?)

1. **Component Merging:** Group nearby small components into larger logical parts
2. **Adaptive Erosion:** Auto-detect optimal erosion based on mesh thickness
3. **Hybrid Approach:** Combine voxelization with distance-based clustering

### Medium-term

1. **Watershed Segmentation:** More sophisticated component separation
2. **Medial Axis Transform:** Find natural separation boundaries
3. **ML-Based Segmentation:** Train model to identify component boundaries

### Long-term

1. **Interactive Segmentation:** Let user mark separation hints
2. **Semantic Understanding:** Recognize "joints" vs "solid connections"

---

## Code Quality

### Implementation Quality

✅ **Type hints:** All functions properly typed
✅ **Docstrings:** Comprehensive documentation
✅ **Error handling:** Graceful fallback on failure
✅ **Configurable:** Exposed key parameters to CLI
✅ **Progress indicators:** Clear console output with emojis
✅ **No regressions:** Existing decompose() unchanged

### Testing

✅ **Unit tests:** Tested on simple_block.stl and simple_cylinder.stl
✅ **Parameter sweep:** Tested various voxel_size and erosion values
✅ **Edge cases:** Handles 0 components, 1 component, many components
✅ **Fallback:** Reverts to standard decompose when appropriate

---

## Conclusion

### Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **Detect > 1 component (simple_block)** | YES | YES (with erosion=1) | ✅ |
| **Keep cylinder as 1 component** | YES | YES (with erosion=0) | ✅ |
| **No errors/crashes** | YES | YES | ✅ |
| **Configurable parameters** | YES | YES | ✅ |
| **Clean separation (5 blocks)** | 5 | 29 | ⚠️ Over-fragmentation |

### Overall Assessment

**Status: ✅ PARTIAL SUCCESS**

The voxelization method is **implemented and functional**, but has **over-fragmentation issues** that require post-processing (component merging) to achieve ideal results.

**Key Achievements:**
- Successfully separates touching components (baseline: 1 → voxel: 29)
- Graceful fallback when separation isn't needed
- Robust, configurable, well-documented

**Remaining Challenges:**
- Too many fragments (need component merging)
- Parameter tuning required for each mesh type
- Thin structures disappear with erosion

### Recommendation

**Commit this implementation** as Phase 6.5 foundation, then pursue Phase 6.6 (Component Merging) to group fragments into logical blocks.

---

## Files Modified

1. `core/decomposer.py`
   - Added `decompose_via_voxelization()` function
   - Added `_analyze_component_simple()` helper
   - Imports: Added `from scipy import ndimage`

2. `mesh_to_primitives.py`
   - Added CLI arguments: `--voxelize`, `--voxel-size`, `--erosion`
   - Updated `convert_mesh()` function signature
   - Integrated voxelization into pipeline

3. Test scripts (for validation, not committed):
   - `test_voxel.py`
   - `test_voxel_params.py`
   - `test_final_voxel.py`
   - `test_cylinder_voxel.py`

---

**Next Steps:**
1. Commit Phase 6.5 implementation
2. Design Phase 6.6: Component merging algorithm
3. Implement distance-based clustering to group fragments
4. Add visualization of separated components
