#!/usr/bin/env python3
"""
Create realistic multi-segment battery test case.

Battery structure:
- Bottom terminal (small cylinder)
- Negative cap (flat cylinder)
- Battery body (large cylinder)
- Positive cap (small cylinder with bump)
- Top terminal (tiny cylinder)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import trimesh
import numpy as np


def create_realistic_battery(
    body_radius: float = 9.0,
    body_height: float = 50.0,
    cap_radius: float = 9.5,
    cap_height: float = 1.0,
    terminal_radius: float = 2.5,
    terminal_height: float = 1.5,
    positive_bump_radius: float = 3.5,
    positive_bump_height: float = 2.0
) -> trimesh.Trimesh:
    """
    Create realistic AA battery with distinct segments.

    Structure (bottom to top):
    1. Bottom terminal (R=2.5mm, H=1.5mm) @ Z=[0, 1.5]
    2. Negative cap (R=9.5mm, H=1.0mm) @ Z=[1.5, 2.5]
    3. Battery body (R=9.0mm, H=50mm) @ Z=[2.5, 52.5]
    4. Positive cap (R=9.5mm, H=1.0mm) @ Z=[52.5, 53.5]
    5. Positive bump (R=3.5mm, H=2.0mm) @ Z=[53.5, 55.5]
    6. Top terminal (R=2.5mm, H=1.5mm) @ Z=[55.5, 57.0]

    Total height: 57mm
    """
    print("\n🔋 Creating realistic multi-segment battery...")

    segments = []

    # 1. Bottom terminal (negative)
    print("  📍 Segment 1: Bottom terminal (R=2.5mm, H=1.5mm)")
    bottom_terminal = trimesh.creation.cylinder(
        radius=terminal_radius,
        height=terminal_height,
        sections=32
    )
    bottom_terminal.apply_translation([0, 0, terminal_height / 2])
    segments.append(bottom_terminal)

    # 2. Negative cap
    print("  📍 Segment 2: Negative cap (R=9.5mm, H=1.0mm)")
    neg_cap = trimesh.creation.cylinder(
        radius=cap_radius,
        height=cap_height,
        sections=32
    )
    z_offset = terminal_height + cap_height / 2
    neg_cap.apply_translation([0, 0, z_offset])
    segments.append(neg_cap)

    # 3. Battery body (main cylinder)
    print("  📍 Segment 3: Battery body (R=9.0mm, H=50.0mm)")
    body = trimesh.creation.cylinder(
        radius=body_radius,
        height=body_height,
        sections=32
    )
    z_offset = terminal_height + cap_height + body_height / 2
    body.apply_translation([0, 0, z_offset])
    segments.append(body)

    # 4. Positive cap
    print("  📍 Segment 4: Positive cap (R=9.5mm, H=1.0mm)")
    pos_cap = trimesh.creation.cylinder(
        radius=cap_radius,
        height=cap_height,
        sections=32
    )
    z_offset = terminal_height + cap_height + body_height + cap_height / 2
    pos_cap.apply_translation([0, 0, z_offset])
    segments.append(pos_cap)

    # 5. Positive bump (small protrusion)
    print("  📍 Segment 5: Positive bump (R=3.5mm, H=2.0mm)")
    pos_bump = trimesh.creation.cylinder(
        radius=positive_bump_radius,
        height=positive_bump_height,
        sections=32
    )
    z_offset = terminal_height + cap_height + body_height + cap_height + positive_bump_height / 2
    pos_bump.apply_translation([0, 0, z_offset])
    segments.append(pos_bump)

    # 6. Top terminal (positive)
    print("  📍 Segment 6: Top terminal (R=2.5mm, H=1.5mm)")
    top_terminal = trimesh.creation.cylinder(
        radius=terminal_radius,
        height=terminal_height,
        sections=32
    )
    z_offset = terminal_height + cap_height + body_height + cap_height + positive_bump_height + terminal_height / 2
    top_terminal.apply_translation([0, 0, z_offset])
    segments.append(top_terminal)

    # Combine all segments
    print("\n  🔗 Combining segments...")
    battery = trimesh.util.concatenate(segments)

    print(f"\n✅ Battery created:")
    print(f"   - Total height: {battery.extents[2]:.1f}mm")
    print(f"   - Max radius: {max(battery.extents[0], battery.extents[1]) / 2:.1f}mm")
    print(f"   - Total volume: {battery.volume:.2f}mm³")
    print(f"   - Segments: 6 distinct regions")

    return battery


def main():
    """Create and save battery test case"""

    # Create battery
    battery = create_realistic_battery()

    # Save to tests/samples directory
    output_dir = './tests/samples'
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, 'realistic_battery_6segments.stl')
    battery.export(output_path)

    print(f"\n💾 Saved: {output_path}")

    # Also save visualization copy
    viz_path = './output/realistic_battery_6segments.stl'
    os.makedirs('./output', exist_ok=True)
    battery.export(viz_path)
    print(f"💾 Saved (viz): {viz_path}")

    print("\n📋 Expected segment detection:")
    print("   1. Bottom terminal: CIRCLE (R≈2.5mm)")
    print("   2. Negative cap: CIRCLE (R≈9.5mm)")
    print("   3. Battery body: CIRCLE (R≈9.0mm)")
    print("   4. Positive cap: CIRCLE (R≈9.5mm)")
    print("   5. Positive bump: CIRCLE (R≈3.5mm)")
    print("   6. Top terminal: CIRCLE (R≈2.5mm)")

    print("\n🧪 Next step: Run LPS test on this battery:")
    print("   python tests/test_layer_wise_stacking.py")


if __name__ == '__main__':
    main()
