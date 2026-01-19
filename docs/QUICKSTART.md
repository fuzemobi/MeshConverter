# Quick Start Guide

## 5-Minute Setup

### Step 1: Install (Choose Your Platform)

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

### Step 2: Activate Environment

**Linux/Mac:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### Step 3: Convert Your First Mesh

```bash
python mesh_to_cad_converter.py your_file.stl
```

That's it! Your cleaned mesh will be in the same directory as your input file.

---

## Common Tasks

### Convert Multiple Files
```bash
python batch_convert.py input_folder/ -o output_folder/
```

### Compare Before/After
```bash
python visualize_results.py original.stl output/original_simplified.stl
```

### Custom Quality Level
```bash
# High quality (slower)
python mesh_to_cad_converter.py file.stl --voxel-size 0.01 --target-triangles 20000

# Fast preview (faster)
python mesh_to_cad_converter.py file.stl --voxel-size 0.05 --target-triangles 2000
```

---

## Understanding the Output

You'll get 3 files:
1. `{name}_simplified.stl` - Your cleaned mesh (use this!)
2. `{name}_cleaned.ply` - Point cloud (optional, for inspection)
3. `{name}_statistics.json` - Processing stats (how much was cleaned)

---

## Troubleshooting

**"Module not found"**
→ Run `pip install -r requirements.txt`

**"Out of memory"**
→ Use `--voxel-size 0.05` to reduce points

**"Lost too much detail"**
→ Use `--voxel-size 0.01 --target-triangles 20000`

**"Still has artifacts"**
→ The mesh may need manual cleanup in CAD software

---

## Next Steps

1. ✅ Read `README.md` for detailed options
2. ✅ Check `examples.py` for usage patterns
3. ✅ Review `PROJECT_SUMMARY.md` for technical details
4. ✅ Run `python test_converter.py` to verify installation

---

## Need Help?

- Check `README.md` for detailed documentation
- Review `PROJECT_SUMMARY.md` for troubleshooting
- Look at `examples.py` for more use cases
- Read the research summary in memory: `mesh_conversion_research_summary`
