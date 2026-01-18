#!/usr/bin/env python3
"""
Test script for Phase 3: Multi-View Validation

Tests the GPT-4o Vision-based validation of original vs reconstructed meshes.
"""

import sys
from pathlib import Path as PathLib

# Add parent directory to path for imports
sys.path.insert(0, str(PathLib(__file__).parent.parent))

import trimesh
import numpy as np
from meshconverter.validation.multiview_validator import validate_reconstruction
from primitives.cylinder import CylinderPrimitive
from primitives.box import BoxPrimitive


def test_cylinder_validation():
    """Test multi-view validation on cylinder reconstruction."""
    print("="*80)
    print("TEST 1: Cylinder Reconstruction Validation")
    print("="*80)

    # Load original mesh
    mesh_path = PathLib(__file__).parent / 'tests' / 'samples' / 'simple_cylinder.stl'
    original_mesh = trimesh.load(str(mesh_path))

    print(f"\n📂 Loaded: {mesh_path.name}")
    print(f"   Vertices: {len(original_mesh.vertices):,}")
    print(f"   Faces: {len(original_mesh.faces):,}")
    print(f"   Volume: {original_mesh.volume:.2f} mm³")

    # Fit cylinder primitive
    print("\n🔧 Fitting cylinder primitive...")
    cylinder = CylinderPrimitive()
    cylinder.fit(original_mesh)

    print(f"   Radius: {cylinder.radius:.2f} mm")
    print(f"   Length: {cylinder.length:.2f} mm")
    print(f"   Quality Score: {cylinder.quality_score}/100")

    # Generate reconstructed mesh
    reconstructed_mesh = cylinder.generate_mesh(resolution=32)

    print(f"\n✅ Reconstructed mesh:")
    print(f"   Vertices: {len(reconstructed_mesh.vertices):,}")
    print(f"   Faces: {len(reconstructed_mesh.faces):,}")
    print(f"   Volume: {reconstructed_mesh.volume:.2f} mm³")

    # Run multi-view validation
    print("\n" + "="*80)
    print("MULTI-VIEW VALIDATION")
    print("="*80)

    result = validate_reconstruction(
        original=original_mesh,
        reconstructed=reconstructed_mesh,
        verbose=True
    )

    # Print results
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)

    if 'error' in result:
        print(f"❌ Validation failed: {result['error']}")
        return False

    print(f"  Similarity Score: {result.get('similarity_score', 0)}/100")
    print(f"  Reconstruction Quality: {result.get('reconstruction_quality', 'unknown').upper()}")
    print(f"  Shape Match: {result.get('shape_match', 'unknown')}")
    print(f"  Dimension Accuracy: {result.get('dimension_accuracy', 'unknown')}")

    if result.get('differences_noted'):
        print(f"\n  📝 Noted Differences:")
        for diff in result['differences_noted']:
            print(f"     • {diff}")

    print(f"\n  💡 Overall Assessment: {result.get('overall_assessment', 'N/A')}")
    print(f"  🎯 Recommended Action: {result.get('recommended_action', 'unknown')}")

    return True


def test_box_validation():
    """Test multi-view validation on box reconstruction."""
    print("\n\n" + "="*80)
    print("TEST 2: Box Reconstruction Validation")
    print("="*80)

    # Load original mesh
    mesh_path = PathLib(__file__).parent / 'tests' / 'samples' / 'simple_block.stl'
    original_mesh = trimesh.load(str(mesh_path))

    print(f"\n📂 Loaded: {mesh_path.name}")
    print(f"   Vertices: {len(original_mesh.vertices):,}")
    print(f"   Faces: {len(original_mesh.faces):,}")
    print(f"   Volume: {original_mesh.volume:.2f} mm³")

    # Fit box primitive
    print("\n🔧 Fitting box primitive...")
    box = BoxPrimitive()
    box.fit(original_mesh)

    print(f"   Dimensions: {box.extents[0]:.2f} x {box.extents[1]:.2f} x {box.extents[2]:.2f} mm")
    print(f"   Quality Score: {box.quality_score}/100")

    # Generate reconstructed mesh
    reconstructed_mesh = box.generate_mesh()

    print(f"\n✅ Reconstructed mesh:")
    print(f"   Vertices: {len(reconstructed_mesh.vertices):,}")
    print(f"   Faces: {len(reconstructed_mesh.faces):,}")
    print(f"   Volume: {reconstructed_mesh.volume:.2f} mm³")

    # Run multi-view validation
    print("\n" + "="*80)
    print("MULTI-VIEW VALIDATION")
    print("="*80)

    result = validate_reconstruction(
        original=original_mesh,
        reconstructed=reconstructed_mesh,
        verbose=True
    )

    # Print results
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)

    if 'error' in result:
        print(f"❌ Validation failed: {result['error']}")
        return False

    print(f"  Similarity Score: {result.get('similarity_score', 0)}/100")
    print(f"  Reconstruction Quality: {result.get('reconstruction_quality', 'unknown').upper()}")
    print(f"  Shape Match: {result.get('shape_match', 'unknown')}")
    print(f"  Dimension Accuracy: {result.get('dimension_accuracy', 'unknown')}")

    if result.get('differences_noted'):
        print(f"\n  📝 Noted Differences:")
        for diff in result['differences_noted']:
            print(f"     • {diff}")

    print(f"\n  💡 Overall Assessment: {result.get('overall_assessment', 'N/A')}")
    print(f"  🎯 Recommended Action: {result.get('recommended_action', 'unknown')}")

    return True


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   MULTI-VIEW VALIDATION TEST SUITE                           ║
║                                                                              ║
║  Phase 3: GPT-4o Vision-based quality assessment                            ║
║  Compares original scanned mesh vs reconstructed parametric model           ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Check for OpenAI API key
    import os
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    print("✅ OPENAI_API_KEY detected")

    # Run tests
    success = True

    try:
        if not test_cylinder_validation():
            success = False
    except Exception as e:
        print(f"\n❌ Cylinder validation test failed with error: {e}")
        import traceback
        traceback.print_exc()
        success = False

    try:
        if not test_box_validation():
            success = False
    except Exception as e:
        print(f"\n❌ Box validation test failed with error: {e}")
        import traceback
        traceback.print_exc()
        success = False

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if success:
        print("✅ All multi-view validation tests PASSED")
        print("\n📊 Phase 3 is ready for integration into convert_mesh_allshapes.py")
    else:
        print("❌ Some tests FAILED - review errors above")

    print("\n" + "="*80)
