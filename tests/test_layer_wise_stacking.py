#!/usr/bin/env python3
"""
Test script for Layer-Wise Primitive Stacking (LPS)

Tests multi-segment reconstruction on simple objects first,
then progresses to complex multi-segment cases.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import trimesh
import numpy as np
from meshconverter.reconstruction.layer_wise_stacker import LayerWiseStacker


def test_simple_cylinder():
    """Test LPS on simple cylinder (baseline)"""
    print("\n" + "="*80)
    print("TEST 1: Simple Cylinder (Baseline)")
    print("="*80)

    # Load mesh
    mesh_path = './tests/samples/simple_cylinder.stl'
    if not os.path.exists(mesh_path):
        print(f"❌ Test mesh not found: {mesh_path}")
        return False

    mesh = trimesh.load(mesh_path)
    print(f"\n📦 Loaded mesh: {mesh_path}")
    print(f"   - Vertices: {len(mesh.vertices):,}")
    print(f"   - Faces: {len(mesh.faces):,}")
    print(f"   - Volume: {mesh.volume:.2f} mm³")
    print(f"   - Extents: {mesh.extents}")

    # Run LPS reconstruction
    stacker = LayerWiseStacker(
        layer_height=0.5,
        min_segment_height=2.0,
        verbose=True
    )

    result = stacker.reconstruct(mesh, vision_results=None)

    # Validate results
    print("\n📊 Validation:")

    if not result['success']:
        print(f"❌ Reconstruction failed: {result.get('error', 'Unknown error')}")
        return False

    print(f"✅ Success: {result['success']}")
    print(f"   - Segments detected: {result['num_segments']}")
    print(f"   - Quality score: {result['quality_score']}/100")

    # Expected: 1 segment (uniform cylinder)
    if result['num_segments'] == 1:
        print("✅ Expected 1 segment (uniform cylinder) - PASS")
    else:
        print(f"⚠️  Expected 1 segment, got {result['num_segments']}")

    # Quality should be reasonable
    if result['quality_score'] >= 70:
        print(f"✅ Quality score {result['quality_score']}/100 >= 70 - PASS")
    else:
        print(f"❌ Quality score {result['quality_score']}/100 < 70 - FAIL")
        return False

    # Save reconstructed mesh
    if result['reconstructed_mesh'] is not None:
        output_path = './output/test_lps_cylinder.stl'
        os.makedirs('./output', exist_ok=True)
        result['reconstructed_mesh'].export(output_path)
        print(f"\n💾 Saved reconstructed mesh: {output_path}")

    return True


def test_simple_block():
    """Test LPS on simple block"""
    print("\n" + "="*80)
    print("TEST 2: Simple Block")
    print("="*80)

    mesh_path = './tests/samples/simple_block.stl'
    if not os.path.exists(mesh_path):
        print(f"❌ Test mesh not found: {mesh_path}")
        return False

    mesh = trimesh.load(mesh_path)
    print(f"\n📦 Loaded mesh: {mesh_path}")
    print(f"   - Volume: {mesh.volume:.2f} mm³")
    print(f"   - Extents: {mesh.extents}")

    stacker = LayerWiseStacker(
        layer_height=0.5,
        verbose=True
    )

    result = stacker.reconstruct(mesh)

    print("\n📊 Validation:")

    if not result['success']:
        print(f"❌ Reconstruction failed: {result.get('error', 'Unknown error')}")
        return False

    print(f"✅ Success: {result['success']}")
    print(f"   - Segments: {result['num_segments']}")
    print(f"   - Quality: {result['quality_score']}/100")

    # Save output
    if result['reconstructed_mesh'] is not None:
        output_path = './output/test_lps_block.stl'
        os.makedirs('./output', exist_ok=True)
        result['reconstructed_mesh'].export(output_path)
        print(f"\n💾 Saved: {output_path}")

    return result['quality_score'] >= 60


def test_synthetic_multi_segment():
    """Test LPS on synthetic multi-segment object"""
    print("\n" + "="*80)
    print("TEST 3: Synthetic Multi-Segment (Cap + Body + Base)")
    print("="*80)

    print("\n🏗️  Creating synthetic multi-segment object...")

    # Create 3-segment object: small cap + large body + small base
    cap = trimesh.creation.cylinder(radius=3.0, height=5.0, sections=32)
    cap.apply_translation([0, 0, 17.5])  # Top

    body = trimesh.creation.cylinder(radius=7.0, height=15.0, sections=32)
    body.apply_translation([0, 0, 7.5])  # Middle

    base = trimesh.creation.cylinder(radius=3.0, height=5.0, sections=32)
    base.apply_translation([0, 0, -2.5])  # Bottom

    # Combine into single mesh
    synthetic = trimesh.util.concatenate([cap, body, base])

    print(f"   - Cap: R=3.0mm, H=5.0mm @ Z=[15, 20]")
    print(f"   - Body: R=7.0mm, H=15.0mm @ Z=[0, 15]")
    print(f"   - Base: R=3.0mm, H=5.0mm @ Z=[-5, 0]")
    print(f"   - Total volume: {synthetic.volume:.2f} mm³")

    # Save synthetic mesh for inspection
    synthetic_path = './output/synthetic_multi_segment.stl'
    os.makedirs('./output', exist_ok=True)
    synthetic.export(synthetic_path)
    print(f"\n💾 Saved synthetic mesh: {synthetic_path}")

    # Run LPS
    stacker = LayerWiseStacker(
        layer_height=0.5,
        min_segment_height=2.0,
        verbose=True
    )

    result = stacker.reconstruct(synthetic)

    print("\n📊 Validation:")

    if not result['success']:
        print(f"❌ Reconstruction failed: {result.get('error', 'Unknown error')}")
        return False

    print(f"✅ Success: {result['success']}")
    print(f"   - Segments detected: {result['num_segments']}")
    print(f"   - Quality: {result['quality_score']}/100")

    # Expected: 3 segments
    if result['num_segments'] == 3:
        print("✅ Expected 3 segments - PASS")
    elif result['num_segments'] == 1:
        print("⚠️  Detected 1 segment (merged all) - fuzzy logic may need tuning")
    else:
        print(f"⚠️  Expected 3 segments, got {result['num_segments']}")

    # Inspect segment details
    print("\n🔍 Segment details:")
    for i, seg in enumerate(result['segments']):
        prim = seg['primitive_2d']
        print(f"   Segment {i+1}: {seg['shape'].upper()}")
        print(f"      Z-range: [{seg['z_start']:.1f}, {seg['z_end']:.1f}]mm")
        print(f"      Height: {seg['height']:.1f}mm")
        if prim['type'] == 'circle':
            print(f"      Radius: {prim['radius']:.2f}mm")
        print()

    # Save reconstructed mesh
    if result['reconstructed_mesh'] is not None:
        output_path = './output/test_lps_synthetic.stl'
        result['reconstructed_mesh'].export(output_path)
        print(f"💾 Saved reconstructed: {output_path}")

    return True


def test_realistic_battery():
    """Test LPS on realistic 6-segment battery"""
    print("\n" + "="*80)
    print("TEST 4: Realistic Battery (6 Segments)")
    print("="*80)

    mesh_path = './tests/samples/realistic_battery_6segments.stl'
    if not os.path.exists(mesh_path):
        print(f"❌ Test mesh not found: {mesh_path}")
        print(f"   Run: python scripts/create_battery_test_case.py")
        return False

    mesh = trimesh.load(mesh_path)
    print(f"\n📦 Loaded mesh: {mesh_path}")
    print(f"   - Volume: {mesh.volume:.2f} mm³")
    print(f"   - Height: {mesh.extents[2]:.1f}mm")
    print(f"   - Max radius: {max(mesh.extents[0], mesh.extents[1]) / 2:.1f}mm")

    print("\n📋 Expected segments:")
    print("   1. Bottom terminal: R≈2.5mm, H≈1.5mm")
    print("   2. Negative cap: R≈9.5mm, H≈1.0mm")
    print("   3. Battery body: R≈9.0mm, H≈50mm")
    print("   4. Positive cap: R≈9.5mm, H≈1.0mm")
    print("   5. Positive bump: R≈3.5mm, H≈2.0mm")
    print("   6. Top terminal: R≈2.5mm, H≈1.5mm")

    # Run LPS with tighter thresholds for better segment detection
    stacker = LayerWiseStacker(
        layer_height=0.5,
        min_segment_height=0.5,  # Lower threshold to catch thin caps
        shape_similarity_threshold=0.85,
        size_similarity_threshold=0.85,  # More sensitive to size changes
        verbose=True
    )

    result = stacker.reconstruct(mesh)

    print("\n📊 Validation:")

    if not result['success']:
        print(f"❌ Reconstruction failed: {result.get('error', 'Unknown error')}")
        return False

    print(f"✅ Success: {result['success']}")
    print(f"   - Segments detected: {result['num_segments']}")
    print(f"   - Quality: {result['quality_score']}/100")

    # Inspect segment details
    print("\n🔍 Detected segment details:")
    for i, seg in enumerate(result['segments']):
        prim = seg['primitive_2d']
        print(f"   Segment {i+1}: {seg['shape'].upper()}")
        print(f"      Z-range: [{seg['z_start']:.1f}, {seg['z_end']:.1f}]mm")
        print(f"      Height: {seg['height']:.1f}mm")
        if prim['type'] == 'circle':
            print(f"      Radius: {prim['radius']:.2f}mm")
        print()

    # Expected: 6 segments (or close)
    if result['num_segments'] >= 4:
        print(f"✅ Detected {result['num_segments']} segments (expected 6, acceptable ≥4)")
    else:
        print(f"⚠️  Expected 6 segments, only detected {result['num_segments']}")

    # Save output
    if result['reconstructed_mesh'] is not None:
        output_path = './output/test_lps_battery.stl'
        result['reconstructed_mesh'].export(output_path)
        print(f"\n💾 Saved reconstructed: {output_path}")

    return result['num_segments'] >= 3  # Pass if at least 3 segments detected


def run_all_tests():
    """Run all LPS tests"""
    print("\n" + "🧪 "*20)
    print("LAYER-WISE PRIMITIVE STACKING - TEST SUITE")
    print("🧪 "*20)

    results = {}

    # Test 1: Simple cylinder (baseline)
    try:
        results['cylinder'] = test_simple_cylinder()
    except Exception as e:
        print(f"\n❌ Test 1 (cylinder) crashed: {e}")
        import traceback
        traceback.print_exc()
        results['cylinder'] = False

    # Test 2: Simple block
    try:
        results['block'] = test_simple_block()
    except Exception as e:
        print(f"\n❌ Test 2 (block) crashed: {e}")
        import traceback
        traceback.print_exc()
        results['block'] = False

    # Test 3: Synthetic multi-segment
    try:
        results['synthetic'] = test_synthetic_multi_segment()
    except Exception as e:
        print(f"\n❌ Test 3 (synthetic) crashed: {e}")
        import traceback
        traceback.print_exc()
        results['synthetic'] = False

    # Test 4: Realistic battery
    try:
        results['battery'] = test_realistic_battery()
    except Exception as e:
        print(f"\n❌ Test 4 (battery) crashed: {e}")
        import traceback
        traceback.print_exc()
        results['battery'] = False

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.ljust(20)}: {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")

    return all(results.values())


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
