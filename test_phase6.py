#!/usr/bin/env python3
"""Test Phase 6 decomposition and pattern recognition."""

import sys
sys.path.insert(0, '/Users/chadrosenbohm/Development/MedTrackET/meshconverter/MeshConverter_v2')

import trimesh
from core.decomposer import decompose_mesh
from core.pattern_matcher import ShapePatternMatcher, BatterySignatureMatcher

print("\n" + "="*70)
print("PHASE 6 TEST: Mesh Decomposition & Pattern Recognition")
print("="*70)

# Test 1: Simple Cylinder (AA Battery)
print("\n\n[TEST 1] Simple Cylinder (AA Battery Scan)")
print("-" * 70)
cylinder_mesh = trimesh.load('tests/samples/simple_cylinder.stl')
print(f"Input: {len(cylinder_mesh.vertices):,} vertices, {len(cylinder_mesh.faces):,} faces")

decomp_cyl = decompose_mesh(cylinder_mesh)
print(f"\nDecomposition Result: {decomp_cyl['total_components']} component(s)")

if decomp_cyl['components']:
    comp = decomp_cyl['components'][0]
    print(f"  Type: {comp['estimated_type']}")
    print(f"  Confidence: {comp['confidence']:.0f}%")
    print(f"  Vertices: {comp['vertices_count']}")
    
    # Pattern matching
    matcher = ShapePatternMatcher()
    shape_name, confidence, details = matcher.match(comp['mesh'])
    print(f"\nPattern Match:")
    print(f"  Shape: {shape_name}")
    print(f"  Confidence: {confidence:.0f}%")
    
    # Battery signature
    battery_features = BatterySignatureMatcher.extract_battery_features(comp['mesh'])
    print(f"\nBattery Signature:")
    print(f"  Battery-like: {battery_features.get('battery_like', False)}")
    print(f"  Aspect Ratio: {battery_features.get('aspect_ratio', 0):.1f}")
    print(f"  Circular: {battery_features.get('is_circular', False)}")

# Test 2: Composite Blocks
print("\n\n[TEST 2] Composite Blocks (Puzzle Pattern)")
print("-" * 70)
block_mesh = trimesh.load('tests/samples/simple_block.stl')
print(f"Input: {len(block_mesh.vertices):,} vertices, {len(block_mesh.faces):,} faces")

decomp_block = decompose_mesh(block_mesh)
print(f"\nDecomposition Result: {decomp_block['total_components']} component(s)")

for i, comp in enumerate(decomp_block['components']):
    if not comp['valid']:
        continue
    print(f"\n  Component {i+1}:")
    print(f"    Type: {comp['estimated_type']}")
    print(f"    Confidence: {comp['confidence']:.0f}%")
    print(f"    Vertices: {comp['vertices_count']}")
    print(f"    BBox Ratio: {comp['bbox_ratio']:.3f}")
    print(f"    Volume: {comp['volume']:.2f} mm³")

# Assembly analysis
assembly = decomp_block['assembly']
print(f"\nAssembly Structure:")
print(f"  Components by type: {assembly['by_type']}")
print(f"  Total volume: {assembly['total_volume']:.2f} mm³")
print(f"  Relationships: {len(assembly['relationships'])} pairs")

print("\n" + "="*70)
print("✅ Phase 6 Testing Complete")
print("="*70 + "\n")
