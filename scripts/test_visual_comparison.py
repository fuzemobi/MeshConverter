#!/usr/bin/env python3
"""
Test visual comparison tool on block reconstruction
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import trimesh
from meshconverter.reconstruction.layer_wise_stacker import LayerWiseStacker
from meshconverter.validation.visual_comparator import compare_reconstruction


def test_block_visual_comparison():
    """Test visual comparison on simple_block.stl"""

    print("\n" + "="*80)
    print("VISUAL COMPARISON TEST - SIMPLE_BLOCK.STL")
    print("="*80)

    # Load mesh
    mesh_path = './tests/samples/simple_block.stl'
    mesh = trimesh.load(mesh_path)

    print(f"\n📦 Original mesh:")
    print(f"   - Volume: {mesh.volume:.2f} mm³")
    print(f"   - Faces: {len(mesh.faces):,}")

    # Reconstruct with LPS
    print(f"\n🏗️  Running LPS reconstruction...")
    stacker = LayerWiseStacker(layer_height=0.5, verbose=False)
    result = stacker.reconstruct(mesh)

    if not result['success']:
        print(f"❌ Reconstruction failed: {result.get('error')}")
        return

    print(f"  ✅ Success!")
    print(f"   - Segments: {result['num_segments']}")
    print(f"   - Quality: {result['quality_score']}/100")

    # Shape distribution
    from collections import Counter
    shapes = [seg['shape'] for seg in result['segments']]
    shape_counts = Counter(shapes)

    print(f"\n📊 Shape distribution:")
    for shape, count in shape_counts.most_common():
        pct = (count / len(shapes)) * 100
        print(f"   {shape}: {count} ({pct:.0f}%)")

    # Generate visual comparison report
    print(f"\n📸 Generating visual comparison report...")

    os.makedirs('./output', exist_ok=True)
    comparison_result = compare_reconstruction(
        original=mesh,
        reconstructed=result['reconstructed_mesh'],
        segments=result['segments'],
        output_path='./output/block_comparison_report.png',
        verbose=True
    )

    print(f"\n✅ Visual comparison complete!")
    print(f"   Volume error: {comparison_result['volume_error']:.2f}%")
    print(f"   Report: {comparison_result['report_path']}")


def test_battery_visual_comparison():
    """Test visual comparison on battery"""

    print("\n" + "="*80)
    print("VISUAL COMPARISON TEST - BATTERY (6 SEGMENTS)")
    print("="*80)

    mesh_path = './tests/samples/realistic_battery_6segments.stl'
    if not os.path.exists(mesh_path):
        print(f"❌ Battery test case not found. Run:")
        print(f"   python scripts/create_battery_test_case.py")
        return

    mesh = trimesh.load(mesh_path)

    print(f"\n🔋 Original mesh:")
    print(f"   - Volume: {mesh.volume:.2f} mm³")
    print(f"   - Height: {mesh.extents[2]:.1f}mm")

    # Reconstruct
    print(f"\n🏗️  Running LPS reconstruction...")
    stacker = LayerWiseStacker(layer_height=0.5, verbose=False)
    result = stacker.reconstruct(mesh)

    print(f"  ✅ {result['num_segments']} segments detected")
    print(f"   - Quality: {result['quality_score']}/100")

    # Generate report
    comparison_result = compare_reconstruction(
        original=mesh,
        reconstructed=result['reconstructed_mesh'],
        segments=result['segments'],
        output_path='./output/battery_comparison_report.png',
        verbose=True
    )

    print(f"\n✅ Visual comparison complete!")
    print(f"   Volume error: {comparison_result['volume_error']:.2f}%")


if __name__ == '__main__':
    test_block_visual_comparison()
    print("\n")
    test_battery_visual_comparison()

    print("\n" + "="*80)
    print("📁 Visual reports saved to ./output/")
    print("   - block_comparison_report.png")
    print("   - battery_comparison_report.png")
    print("="*80)
