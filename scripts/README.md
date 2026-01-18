# Scripts

Standalone conversion scripts and utilities for MeshConverter v2.

## Main Conversion Scripts

### convert_mesh_allshapes.py
**Complete Phase 1+2+3 pipeline** - Tests ALL primitive shapes, auto-selects best fit

**Usage**:
```bash
python scripts/convert_mesh_allshapes.py input.stl
python scripts/convert_mesh_allshapes.py input.stl --no-vision
python scripts/convert_mesh_allshapes.py input.stl --layer-height 1.0
```

**Features**:
- Phase 1: Vision-based layer analysis (GPT-4o)
- Phase 2: Vision-guided outlier removal
- Phase 3: Multi-view validation
- Tests: Box, Cylinder, Sphere, Cone
- Auto-selection with confidence scoring
- Assembly detection (layer-slicing)

**Output**:
- `input_optimized.stl` - Clean parametric mesh
- `input_optimized.json` - Complete metadata with quality metrics

---

### convert_mesh.py
**Legacy Phase 1 script** - Box/Cylinder only (superseded by convert_mesh_allshapes.py)

Use `convert_mesh_allshapes.py` for new projects.

---

## Directory Structure

```
scripts/
├── README.md                      # This file
├── convert_mesh_allshapes.py      # Main conversion script (Phase 1+2+3)
├── convert_mesh.py                # Legacy script (box/cylinder only)
├── examples/                      # Example usage scripts
└── utilities/                     # Helper utilities
```

---

## Development Scripts

Located in `scripts/utilities/` (when created):
- Batch conversion scripts
- Performance benchmarking
- Data generation utilities
- Testing helpers

---

## See Also

- [Complete Documentation](../docs/PHASE_INTEGRATION_GUIDE.md)
- [Conversion Guide](../docs/CONVERT_GUIDE.md)
- [All Shapes Guide](../docs/ALL_SHAPES_GUIDE.md)
