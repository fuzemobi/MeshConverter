#!/usr/bin/env python3
"""
Demo script for multi-segment reconstruction using Layer-Wise Primitive Stacking

Usage:
    python scripts/demo_multisegment_reconstruction.py <mesh.stl>

Examples:
    python scripts/demo_multisegment_reconstruction.py tests/samples/simple_block.stl
    python scripts/demo_multisegment_reconstruction.py tests/samples/realistic_battery_6segments.stl
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import trimesh
from meshconverter.reconstruction.layer_wise_stacker import LayerWiseStacker


def demo_reconstruction(mesh_path: str, verbose: bool = True):
    """
    Demonstrate multi-segment reconstruction on a mesh file.

    Args:
        mesh_path: Path to STL file
        verbose: Print detailed output
    """
    if not os.path.exists(mesh_path):
        print(f"❌ Error: File not found: {mesh_path}")
        return False

    print("\n" + "="*80)
    print("MULTI-SEGMENT RECONSTRUCTION DEMO")
    print("="*80)
    print(f"\n📂 Input: {mesh_path}")

    # Load mesh
    try:
        mesh = trimesh.load(mesh_path)
        print(f"\n📦 Original mesh:")
        print(f"   - Vertices: {len(mesh.vertices):,}")
        print(f"   - Faces: {len(mesh.faces):,}")
        print(f"   - Volume: {mesh.volume:.2f} mm³")
        print(f"   - Bounding box: {mesh.extents}")
    except Exception as e:
        print(f"❌ Error loading mesh: {e}")
        return False

    # Reconstruct with LPS
    print(f"\n🏗️  Running Layer-Wise Primitive Stacking...")
    print(f"   CV Validation: ENABLED")
    print(f"   Confidence Threshold: 0.70")

    stacker = LayerWiseStacker(
        layer_height=0.5,
        min_segment_height=2.0,
        use_cv_validation=True,
        cv_confidence_threshold=0.70,
        verbose=verbose
    )

    result = stacker.reconstruct(mesh)

    if not result['success']:
        print(f"❌ Reconstruction failed: {result.get('error')}")
        return False

    # Print results
    print(f"\n✅ Reconstruction Complete!")
    print(f"\n📊 Summary:")
    print(f"   - Segments: {result['num_segments']}")
    print(f"   - Quality Score: {result['quality_score']}/100")
    print(f"   - Volume Error: {result.get('volume_error', 0)*100:.2f}%")

    # Segment breakdown
    print(f"\n📋 Segment Breakdown:")
    for i, seg in enumerate(result['segments'], 1):
        prim = seg['primitive_2d']
        print(f"\n   Segment {i}: {prim['type'].upper()}")
        print(f"     Z-Range: {seg['z_start']:.1f} → {seg['z_end']:.1f}mm (H={seg['height']:.1f}mm)")

        if prim['type'] == 'circle':
            print(f"     Radius: {prim['radius']:.2f}mm")
        elif prim['type'] == 'rectangle':
            print(f"     Dimensions: {prim['width']:.2f} × {prim['height']:.2f}mm")
            print(f"     Rotation: {prim['rotation']:.1f}°")
        elif prim['type'] == 'ellipse':
            print(f"     Axes: {prim['major_axis']:.2f} × {prim['minor_axis']:.2f}mm")

        # CV validation details
        if 'cv_validation' in prim:
            cv = prim['cv_validation']
            print(f"     CV Confidence: {cv['confidence']:.3f}")
            print(f"       SSIM: {cv['ssim']:.3f} | IoU: {cv['iou']:.3f} | Contour: {cv['contour_similarity']:.3f}")
            if prim.get('use_polygon_extrusion'):
                print(f"       ⚠️  Using polygon extrusion (low confidence)")

    # Save output
    output_dir = Path('./output/demo')
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh_name = Path(mesh_path).stem
    output_path = output_dir / f"{mesh_name}_reconstructed.stl"

    print(f"\n💾 Saving reconstructed mesh...")
    result['reconstructed_mesh'].export(str(output_path))
    print(f"   ✅ Saved to: {output_path}")

    # Visual comparison (optional)
    try:
        print(f"\n📸 Generating visual comparison report...")
        from meshconverter.validation.visual_comparator import compare_reconstruction

        report_path = output_dir / f"{mesh_name}_comparison.png"
        compare_reconstruction(
            original=mesh,
            reconstructed=result['reconstructed_mesh'],
            segments=result['segments'],
            output_path=str(report_path),
            verbose=False
        )
        print(f"   ✅ Report saved: {report_path}")
    except Exception as e:
        print(f"   ⚠️  Visual comparison skipped: {e}")

    print("\n" + "="*80)
    print("✅ DEMO COMPLETE")
    print("="*80)

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/demo_multisegment_reconstruction.py <mesh.stl>")
        print("\nExamples:")
        print("  python scripts/demo_multisegment_reconstruction.py tests/samples/simple_block.stl")
        print("  python scripts/demo_multisegment_reconstruction.py tests/samples/realistic_battery_6segments.stl")
        sys.exit(1)

    mesh_path = sys.argv[1]
    demo_reconstruction(mesh_path, verbose=False)


if __name__ == '__main__':
    main()
