#!/usr/bin/env python3
"""
Test script for vision-based layer analysis.

Demonstrates GPT-4 Vision analyzing individual layer cross-sections
to detect outliers and validate geometry.
"""

import sys
import os
import trimesh
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from meshconverter.reconstruction.vision_layer_analyzer import VisionLayerAnalyzer


def test_vision_layer_analysis(stl_path: str, n_sample_layers: int = 5):
    """
    Test vision-based layer analysis on a mesh.

    Args:
        stl_path: Path to STL file
        n_sample_layers: Number of layers to sample for analysis
    """
    print(f"\n{'='*70}")
    print(f"🔬 Vision-Based Layer Analysis Test")
    print(f"{'='*70}")
    print(f"Input: {stl_path}")
    print(f"Sample layers: {n_sample_layers}")

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='sk-...'")
        return

    # Load mesh
    print(f"\n📂 Loading mesh...")
    try:
        mesh = trimesh.load(stl_path)
        print(f"  ✅ Loaded: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        print(f"     Volume: {mesh.volume:.2f} mm³")
        print(f"     Bounds: {mesh.bounds}")
    except Exception as e:
        print(f"  ❌ Failed to load mesh: {e}")
        return

    # Initialize vision analyzer
    print(f"\n🤖 Initializing GPT-4 Vision analyzer...")
    try:
        analyzer = VisionLayerAnalyzer(api_key=api_key)
        print(f"  ✅ Vision analyzer ready")
    except Exception as e:
        print(f"  ❌ Failed to initialize: {e}")
        return

    # Sample layers across Z range
    bounds = mesh.bounds
    z_min, z_max = bounds[0, 2], bounds[1, 2]
    z_range = z_max - z_min

    # Select evenly spaced layers
    sample_z_values = np.linspace(z_min + z_range * 0.1, z_max - z_range * 0.1, n_sample_layers)

    print(f"\n📊 Analyzing {n_sample_layers} sample layers from Z={z_min:.2f} to {z_max:.2f} mm...")
    print(f"  Estimated cost: ~${0.01 * n_sample_layers:.3f}")
    print()

    results = []

    for i, z in enumerate(sample_z_values):
        print(f"\n{'-'*70}")
        print(f"Layer {i+1}/{n_sample_layers} - Z = {z:.2f} mm")
        print(f"{'-'*70}")

        # Slice mesh at this Z height
        section = mesh.section(
            plane_origin=[0, 0, z],
            plane_normal=[0, 0, 1]
        )

        if section is None or len(section.vertices) == 0:
            print(f"  ⚠️  No vertices at this height, skipping...")
            continue

        print(f"  Cross-section: {len(section.vertices)} vertices")

        # Analyze with vision
        try:
            result = analyzer.analyze_layer_for_outliers(
                section=section,
                z_height=z,
                layer_id=i,
                verbose=True
            )

            results.append({
                'layer_id': i,
                'z': z,
                'n_vertices': len(section.vertices),
                **result
            })

            # Print summary
            print(f"\n  📋 Analysis Summary:")
            print(f"     Shape: {result.get('shape_detected', 'unknown')}")
            print(f"     Confidence: {result.get('confidence', 0)}%")
            print(f"     Has outliers: {result.get('has_outliers', False)}")
            print(f"     Outlier %: {result.get('outlier_percentage', 0):.1f}%")
            print(f"     Reasoning: {result.get('reasoning', 'N/A')[:100]}...")

        except Exception as e:
            print(f"  ❌ Analysis failed: {e}")
            continue

    # Final summary
    print(f"\n{'='*70}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Layers analyzed: {len(results)}")

    if results:
        # Count shapes detected
        shapes = [r.get('shape_detected', 'unknown') for r in results]
        shape_counts = {}
        for shape in shapes:
            shape_counts[shape] = shape_counts.get(shape, 0) + 1

        print(f"\nShape distribution:")
        for shape, count in sorted(shape_counts.items(), key=lambda x: -x[1]):
            print(f"  {shape}: {count} layers ({100*count/len(results):.1f}%)")

        # Outlier statistics
        layers_with_outliers = sum(1 for r in results if r.get('has_outliers', False))
        avg_outlier_pct = np.mean([r.get('outlier_percentage', 0) for r in results])

        print(f"\nOutlier detection:")
        print(f"  Layers with outliers: {layers_with_outliers}/{len(results)} ({100*layers_with_outliers/len(results):.1f}%)")
        print(f"  Average outlier %: {avg_outlier_pct:.2f}%")

        # Confidence statistics
        avg_confidence = np.mean([r.get('confidence', 0) for r in results])
        print(f"\nConfidence:")
        print(f"  Average: {avg_confidence:.1f}%")

        # Recommendations
        print(f"\n💡 Recommendations:")
        if avg_outlier_pct > 5:
            print(f"  ⚠️  High outlier percentage detected ({avg_outlier_pct:.1f}%)")
            print(f"     Consider pre-processing to clean scan data")
        else:
            print(f"  ✅ Low outlier percentage ({avg_outlier_pct:.1f}%) - data looks clean")

        if avg_confidence < 70:
            print(f"  ⚠️  Low average confidence ({avg_confidence:.1f}%)")
            print(f"     Shape may be complex or irregular")
        else:
            print(f"  ✅ High confidence ({avg_confidence:.1f}%) - clear geometric shape")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test vision-based layer analysis")
    parser.add_argument("stl_file", help="Path to STL file")
    parser.add_argument(
        "-n", "--num-layers",
        type=int,
        default=5,
        help="Number of layers to sample (default: 5)"
    )

    args = parser.parse_args()

    test_vision_layer_analysis(args.stl_file, args.num_layers)
