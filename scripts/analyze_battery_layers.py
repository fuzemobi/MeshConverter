#!/usr/bin/env python3
"""
Analyze battery layers to understand why segments aren't being detected.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import trimesh
import numpy as np
from meshconverter.reconstruction.layer_wise_stacker import LayerWiseStacker


def analyze_battery_layers():
    """Analyze layer-by-layer radius changes"""

    mesh_path = './tests/samples/realistic_battery_6segments.stl'
    mesh = trimesh.load(mesh_path)

    print("\n🔍 Analyzing battery layers...")
    print("="*80)

    # Create stacker
    stacker = LayerWiseStacker(layer_height=0.5, verbose=False)

    # Detect axis and slice
    axis, axis_name = stacker.detect_primary_axis(mesh)
    layers = stacker.slice_mesh(mesh, axis, 0.5)

    print(f"\n📊 Extracted {len(layers)} layers")
    print("\n Layer-by-layer analysis (showing every 5th layer):\n")
    print(f"{'Layer':<8} {'Z (mm)':<10} {'Area (mm²)':<15} {'Radius (mm)':<15} {'Δ Radius':<15}")
    print("-"*80)

    prev_radius = None
    transitions = []

    for i, layer in enumerate(layers):
        area = layer['area']
        # Estimate radius from area (A = πr²)
        radius = np.sqrt(area / np.pi)

        delta = ""
        if prev_radius is not None:
            delta_val = abs(radius - prev_radius)
            delta = f"{delta_val:+.2f}"

            # Detect sharp transitions (>15% change)
            pct_change = delta_val / prev_radius
            if pct_change > 0.15:
                transitions.append({
                    'layer': i,
                    'z': layer['z_height'],
                    'old_radius': prev_radius,
                    'new_radius': radius,
                    'delta': delta_val,
                    'pct_change': pct_change * 100
                })

        # Show every 5th layer or first/last
        if i % 5 == 0 or i == 0 or i == len(layers) - 1:
            print(f"{i:<8} {layer['z_height']:<10.1f} {area:<15.1f} {radius:<15.2f} {delta:<15}")

        prev_radius = radius

    # Show detected transitions
    print("\n"+"="*80)
    print(f"\n🔔 Detected {len(transitions)} sharp transitions (>15% radius change):\n")

    for trans in transitions:
        print(f"  Layer {trans['layer']} @ Z={trans['z']:.1f}mm:")
        print(f"    R: {trans['old_radius']:.2f}mm → {trans['new_radius']:.2f}mm")
        print(f"    Δ: {trans['delta']:.2f}mm ({trans['pct_change']:.1f}% change)")
        print()

    # Expected segments
    print("="*80)
    print("\n📋 Expected segment boundaries:")
    print("  1. Z=0-1.5mm: Bottom terminal (R=2.5mm)")
    print("  2. Z=1.5-2.5mm: Negative cap (R=9.5mm) ← 280% increase")
    print("  3. Z=2.5-52.5mm: Battery body (R=9.0mm) ← 5% decrease")
    print("  4. Z=52.5-53.5mm: Positive cap (R=9.5mm) ← 5% increase")
    print("  5. Z=53.5-55.5mm: Positive bump (R=3.5mm) ← 63% decrease")
    print("  6. Z=55.5-57mm: Top terminal (R=2.5mm) ← 29% decrease")

    print("\n💡 Insight:")
    print("  Current fuzzy logic uses 0.85 size threshold (15% tolerance).")
    print("  Transitions #2 and #5 should be detected (>15% change).")
    print("  But the algorithm may smooth over transitions if area_ratio")
    print("  calculation is using max/min ratio instead of percent change.")

    print("\n🔧 Recommendation:")
    print("  Modify fuzzy_size_match() to be more sensitive to sharp transitions.")
    print("  Consider using percent change instead of simple ratio.")


if __name__ == '__main__':
    analyze_battery_layers()
