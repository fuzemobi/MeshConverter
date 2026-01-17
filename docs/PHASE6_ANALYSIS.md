# Phase 6 Analysis: Composite Block Decomposition Challenge

**Document**: Analysis and Solutions for separating interlocking puzzle blocks  
**Date**: January 17, 2026  
**Status**: Problem Identified - Solutions Ready for Implementation

---

## Executive Summary

The simple_block.stl contains 5 interlocking puzzle blocks but decomposes as 1 connected component. This is **correct behavior** given the mesh topology (blocks share faces), but **not the desired user outcome**.

### Why This Happens

```
Physical reality: 5 separate physical blocks
  ↓
But in mesh file: Connected via shared face vertices
  ↓
Connected Component Algorithm: "This is 1 topology"
  ↓
Result: Cannot separate with standard graph algorithms
```

### Why Current Algorithms Can't Help

| Algorithm | Why It Fails |
|-----------|------------|
| Connected Component Analysis | Blocks ARE connected (touching faces) |
| DBSCAN Spatial Clustering | All vertices within spatial threshold |
| KD-tree Neighbors | All blocks within proximity |
| Convex Hull Analysis | Composite convex, not separable |

---

## The Core Issue: Topology vs Geometry

### Mesh Topology (Graph Structure)

```python
# Face-adjacency graph
Block1_Face1 ← shares vertices → Block2_Face3
Block2_Face6 ← shares vertices → Block3_Face2
Block3_Face4 ← shares vertices → Block4_Face5
Block4_Face7 ← shares vertices → Block5_Face1
Block5_Face8 ← shares vertices → Block1_Face2

# Graph traversal: Block1 → Block2 → Block3 → Block4 → Block5 → Block1
# Result: 1 strongly connected component
```

### Mesh Geometry (Vertex Positions)

```
Block1: [10, 20, 30] → [15, 30, 40]
Block2: [15, 20, 30] → [20, 30, 40]  ← Touching Block1 at x=15
Block3: [20, 20, 30] → [25, 30, 40]  ← Touching Block2 at x=20
Block4: [25, 20, 30] → [30, 30, 40]  ← Touching Block3 at x=25
Block5: [30, 20, 30] → [35, 30, 40]  ← Touching Block4 at x=30
└─→ All within 25mm DBSCAN threshold
```

### The Fundamental Problem

Connected Component Analysis requires **topological disconnection** (no shared vertices/faces), which doesn't exist in the puzzle mesh.

---

## Solutions Hierarchy

### ✅ Solution 1: VOXELIZATION (Recommended - Phase 6.5)

**Concept**: Convert mesh → voxel grid → identify gaps → extract separate voxel regions → convert back to mesh

**Process**:
```
mesh ← high resolution, all blocks connected
  ↓
[Voxelize] Convert to 3D grid (e.g., 0.5mm resolution)
  ├─ Block1 voxels (red)
  ├─ Block2 voxels (blue)
  ├─ Block3 voxels (green)
  ├─ Block4 voxels (yellow)
  └─ Block5 voxels (purple)
  ↓
[Erode] Slight erosion (0.3mm) to break surface connections
  └─ Touching faces now have gaps
  ↓
[Connected Component] Now works! Each color is separate component
  ↓
[Dilate] Expand back (0.3mm) to restore original size
  ↓
[Voxel → Mesh] Convert back to STL, now 5 separate components
```

**Implementation**:
```python
def voxelize_and_decompose(mesh, voxel_size=0.5, erosion_size=0.3):
    """
    Decompose mesh by converting to voxels and back.
    """
    # Step 1: Voxelize
    voxel_grid = mesh.voxelized(voxel_size)
    
    # Step 2: Erode (break surface connections)
    eroded = binary_erosion(voxel_grid, iterations=int(erosion_size/voxel_size))
    
    # Step 3: Find connected components in voxel space
    labeled_voxels = label(eroded)
    
    # Step 4: Dilate back
    dilated = binary_dilation(labeled_voxels, iterations=int(erosion_size/voxel_size))
    
    # Step 5: Extract each component as mesh
    components = []
    for component_id in np.unique(dilated):
        if component_id == 0:  # Skip background
            continue
        component_mesh = voxels_to_mesh(dilated == component_id)
        components.append(component_mesh)
    
    return components
```

**Pros**:
- ✅ Works on any topology
- ✅ Automatically finds gaps
- ✅ Preserves geometry
- ✅ Robust to noise

**Cons**:
- ❌ Computationally expensive (for very large meshes)
- ❌ May lose detail (voxel resolution trade-off)
- ❌ Requires scipy.ndimage (small dependency)

**Complexity**: O(V/voxel_size³) where V = mesh volume

**Estimated Time**: 2-5 seconds for typical mesh (100k vertices)

**Status**: Can implement immediately with trimesh.voxelized() + scipy.ndimage

---

### ✅ Solution 2: GRAPH-BASED GAP DETECTION (Alternative)

**Concept**: Detect "thin bridges" in face adjacency graph, break them

**Process**:
```
Analyze each face-adjacency edge:
  If 2 faces share vertices but have large normal angle (>120°)
    → Likely a bridge between separate blocks
    → Mark for removal
  
Break marked edges in graph
  ↓
Re-run connected components
  ↓
Result: 5 separate components
```

**Implementation**:
```python
def detect_bridges(mesh):
    """
    Find face-adjacency edges that are likely bridges.
    """
    bridges = []
    
    for i, face1 in enumerate(mesh.faces):
        normal1 = mesh.face_normals[i]
        
        for j, face2 in enumerate(mesh.faces):
            if i >= j:
                continue
            
            # Check if faces share vertices
            if not np.any(np.isin(face1, face2)):
                continue
            
            # Check angle between normals
            normal2 = mesh.face_normals[j]
            angle = np.arccos(np.dot(normal1, normal2))
            
            # Large angle = likely bridge
            if angle > 2.0:  # ~120 degrees
                bridges.append((i, j))
    
    return bridges
```

**Pros**:
- ✅ No new dependencies
- ✅ Preserves exact geometry
- ✅ Fast (O(F²) where F = faces)
- ✅ Works on curved boundaries

**Cons**:
- ❌ Requires tuning angle threshold (120° chosen for blocks)
- ❌ May miss subtle boundaries
- ❌ Fails on smooth curves

**Complexity**: O(F²) = O(172,688²) = ~30 billion operations (slow!)

**Status**: Feasible but graph-based, may need optimization

---

### ✅ Solution 3: USER HINTS (Pragmatic - Phase 6.5)

**Concept**: User provides hint (--estimated-components=5), system forces decomposition

**Process**:
```
User runs:
  python mesh_to_primitives.py simple_block.stl --components=5
  
System:
  1. Compute bounding box
  2. Use octree-based k-means to force 5 regions
  3. Assign faces to closest region center
  4. Extract each region as separate mesh
  5. Fit primitives per-region independently
  
Result: 5 separate components
```

**Implementation**:
```python
def decompose_with_hints(mesh, n_components):
    """
    Force decomposition into N components via k-means clustering.
    """
    # Get face centers
    face_centers = mesh.triangles_center
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_components, random_state=42)
    labels = kmeans.fit_predict(face_centers)
    
    # Extract each cluster as mesh
    components = []
    for cluster_id in range(n_components):
        cluster_faces = np.where(labels == cluster_id)[0]
        component_mesh = mesh.submesh([cluster_faces], append=True)
        components.append(component_mesh)
    
    return components
```

**Pros**:
- ✅ No algorithms needed (just k-means)
- ✅ Always produces N components
- ✅ Very fast (<1 second)
- ✅ User has control

**Cons**:
- ❌ Requires user knowledge of component count
- ❌ Boundaries may not match actual block edges
- ❌ Less "automatic"

**Complexity**: O(N_iter × F) ≈ O(100 × 70k) fast

**Status**: Can implement in 30 minutes

---

## Recommendation: Multi-Phase Approach

### Phase 6.5 (Next - 2 Weeks)

Implement **both Solution 1 (Voxelization) and Solution 3 (User Hints)** for maximum robustness:

```python
# mesh_to_primitives.py updated CLI
python mesh_to_primitives.py mesh.stl -o output/
  # NEW: Auto-detects composite structures
  # Tries voxel-based decomposition first
  
python mesh_to_primitives.py mesh.stl -o output/ --components=5
  # Manual override: User specifies count
  # Uses k-means clustering
```

### Phase 7 (Later - 4 Weeks)

Add Solution 2 (Graph-based) for real-time analysis of boundary angles.

### Phase 8+ (Future)

Machine learning-based decomposition using training data from ShapeNet (MeshXL).

---

## Implementation Plan: Phase 6.5

### Step 1: Voxelization Path

**File**: `core/decomposer.py` (add new method)

```python
def decompose_via_voxelization(
    mesh: trimesh.Trimesh,
    voxel_size: float = 0.5,
    erosion_size: float = 0.3,
    min_component_size: int = 100
) -> List[trimesh.Trimesh]:
    """
    Decompose mesh by voxelization and erosion.
    
    Args:
        mesh: Input mesh
        voxel_size: Voxel resolution (mm)
        erosion_size: Erosion radius for breaking connections (mm)
        min_component_size: Minimum voxel count per component
    
    Returns:
        List of separated component meshes
    """
    from scipy.ndimage import binary_erosion, binary_dilation, label
    
    # Voxelize
    voxel_grid = mesh.voxelized(voxel_size)
    
    # Erode to break connections
    erosion_iters = max(1, int(erosion_size / voxel_size))
    eroded = binary_erosion(voxel_grid.matrix, iterations=erosion_iters)
    
    # Label connected components
    labeled, n_components = label(eroded)
    
    # Dilate back
    dilated = binary_dilation(labeled, iterations=erosion_iters)
    
    # Extract components
    components = []
    for component_id in range(1, n_components + 1):
        component_voxels = (dilated == component_id)
        n_voxels = component_voxels.sum()
        
        if n_voxels < min_component_size:
            continue
        
        # Convert voxels back to mesh
        component_mesh = trimesh.voxel.VoxelGrid(component_voxels).as_mesh()
        components.append(component_mesh)
    
    return components
```

### Step 2: User Hints Path

**File**: `core/decomposer.py` (add new method)

```python
def decompose_with_component_hints(
    mesh: trimesh.Trimesh,
    n_components: int
) -> List[trimesh.Trimesh]:
    """
    Decompose mesh into N components using k-means clustering.
    
    Args:
        mesh: Input mesh
        n_components: Number of components to extract
    
    Returns:
        List of N component meshes
    """
    from sklearn.cluster import KMeans
    
    # Get face centers for clustering
    face_centers = mesh.triangles_center
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_components, random_state=42)
    labels = kmeans.fit_predict(face_centers)
    
    # Extract each cluster
    components = []
    for cluster_id in range(n_components):
        cluster_faces = np.where(labels == cluster_id)[0]
        
        if len(cluster_faces) == 0:
            continue
        
        # Create submesh from faces
        component_mesh = mesh.submesh([cluster_faces], append=True)
        components.append(component_mesh)
    
    return components
```

### Step 3: CLI Integration

**File**: `mesh_to_primitives.py`

```python
import argparse

parser = argparse.ArgumentParser()
# ... existing args ...
parser.add_argument(
    '--components',
    type=int,
    default=None,
    help='Force decomposition into N components (uses k-means)'
)
parser.add_argument(
    '--voxel-size',
    type=float,
    default=0.5,
    help='Voxel size for decomposition (mm)'
)

args = parser.parse_args()

# In pipeline
if args.components:
    components = decompose_with_component_hints(mesh, args.components)
    print(f"✅ Forced decomposition into {len(components)} components")
else:
    # Try voxelization first
    try:
        components = decompose_via_voxelization(
            mesh,
            voxel_size=args.voxel_size
        )
        if len(components) > 1:
            print(f"✅ Voxel decomposition: {len(components)} components found")
    except:
        # Fallback to existing method
        components = [mesh]
```

### Step 4: Testing

**File**: `test_phase6_decomposition.py`

```python
def test_voxelization_decomposition():
    """Test voxel-based decomposition on blocks"""
    mesh = trimesh.load('simple_block.stl')
    
    components = decompose_via_voxelization(
        mesh,
        voxel_size=0.5,
        erosion_size=0.3
    )
    
    # Expect 5 components
    assert len(components) == 5, f"Expected 5, got {len(components)}"
    
    # Each should be a block
    for i, component in enumerate(components):
        assert component.volume > 100, f"Component {i} too small"

def test_user_hints_decomposition():
    """Test k-means decomposition with user hints"""
    mesh = trimesh.load('simple_block.stl')
    
    components = decompose_with_component_hints(mesh, n_components=5)
    
    # Expect exactly 5 components
    assert len(components) == 5, f"Expected 5, got {len(components)}"
```

---

## Estimated Effort

| Component | Lines of Code | Time | Complexity |
|-----------|---------------|------|-----------|
| Voxelization | 30-50 | 2 hours | Medium |
| User Hints | 25-35 | 1 hour | Low |
| CLI Integration | 10-15 | 1 hour | Low |
| Testing | 40-60 | 2 hours | Medium |
| Documentation | 100-150 | 1 hour | Low |
| **TOTAL** | **205-310** | **7 hours** | **Medium** |

---

## Success Criteria

- [ ] `python mesh_to_primitives.py simple_block.stl` → detects 5 components (via voxelization)
- [ ] `python mesh_to_primitives.py simple_block.stl --components=5` → produces 5 components
- [ ] Each component classified as "box"
- [ ] Volume preserved: input_volume ≈ sum(component_volumes)
- [ ] 3 new unit tests all passing
- [ ] Documentation updated

---

## Conclusion

**Problem**: Composite blocks can't be separated via standard graph algorithms (they're topologically connected)

**Best Solution**: Voxelization + User Hints (dual approach)
- Voxelization: Automatic, robust, works without user input
- User Hints: Pragmatic fallback, requires user knowledge

**Implementation Timeline**: 
- Phase 6.5 (2 weeks): Both solutions
- Phase 7 (4 weeks): Graph-based optimization
- Phase 8+ (future): ML-based learning

**Status**: ✅ Ready for implementation

