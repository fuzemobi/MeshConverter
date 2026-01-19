#!/usr/bin/env python3
"""
Demo script for hybrid multi-view reconstruction

Combines multi-view contour extraction with primitive fitting for accurate
reconstruction without the complexity of layer-wise stacking.

Usage:
    python scripts/demo_hybrid_reconstruction.py <mesh.stl>

Examples:
    python scripts/demo_hybrid_reconstruction.py tests/samples/simple_block.stl
    python scripts/demo_hybrid_reconstruction.py tests/samples/simple_cylinder.stl
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import trimesh
import numpy as np
import matplotlib.pyplot as plt
from meshconverter.reconstruction.hybrid_reconstructor import HybridReconstructor


def visualize_comparison(
    original: trimesh.Trimesh,
    reconstructed: trimesh.Trimesh,
    result: dict,
    output_path: str = None
):
    """
    Create side-by-side visualization of original vs reconstructed mesh.

    Args:
        original: Original mesh
        reconstructed: Reconstructed mesh
        result: Reconstruction result dictionary
        output_path: Path to save visualization
    """
    fig = plt.figure(figsize=(16, 8))

    # Original mesh
    ax1 = fig.add_subplot(121, projection='3d')
    ax1.plot_trisurf(
        original.vertices[:, 0],
        original.vertices[:, 1],
        original.vertices[:, 2],
        triangles=original.faces,
        alpha=0.7,
        edgecolor='none',
        color='lightblue'
    )
    ax1.set_title(f"Original Mesh\n{len(original.vertices):,} vertices, {len(original.faces):,} faces",
                  fontsize=14, fontweight='bold')
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    ax1.set_zlabel('Z')

    # Reconstructed mesh
    ax2 = fig.add_subplot(122, projection='3d')
    if reconstructed is not None and len(reconstructed.faces) > 0:
        ax2.plot_trisurf(
            reconstructed.vertices[:, 0],
            reconstructed.vertices[:, 1],
            reconstructed.vertices[:, 2],
            triangles=reconstructed.faces,
            alpha=0.7,
            edgecolor='none',
            color='lightgreen'
        )

    shape = result.get('shape', 'unknown')
    method = result.get('method', 'unknown')
    quality = result.get('quality_score', 0)

    title = f"Reconstructed ({shape.upper()})\n"
    title += f"Method: {method}\n"
    title += f"Quality: {quality:.1f}/100"

    ax2.set_title(title, fontsize=14, fontweight='bold')
    ax2.set_xlabel('X')
    ax2.set_ylabel('Y')
    ax2.set_zlabel('Z')

    # Add summary text
    fig.suptitle(
        'Hybrid Multi-View Reconstruction Comparison',
        fontsize=16,
        fontweight='bold',
        y=0.98
    )

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n💾 Visualization saved: {output_path}")
    else:
        plt.show()

    plt.close()


def demo_reconstruction(mesh_path: str, verbose: bool = True):
    """
    Demonstrate hybrid reconstruction on a mesh file.

    Args:
        mesh_path: Path to STL file
        verbose: Print detailed output
    """
    if not os.path.exists(mesh_path):
        print(f"❌ Error: File not found: {mesh_path}")
        return False

    print("\n" + "="*80)
    print("HYBRID MULTI-VIEW RECONSTRUCTION DEMO")
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

    # Reconstruct with hybrid approach
    print(f"\n🔬 Running Hybrid Reconstruction...")

    reconstructor = HybridReconstructor(
        layer_height=0.5,
        min_segment_height=2.0,
        image_size=512,
        verbose=verbose
    )

    result = reconstructor.reconstruct(mesh)

    if not result['success']:
        print(f"❌ Reconstruction failed: {result.get('error')}")
        return False

    # Print results
    print(f"\n✅ Reconstruction Complete!")

    shape_class = result.get('shape_classification', {})
    print(f"\n📊 Shape Classification:")
    print(f"   - Detected Shape: {shape_class.get('shape', 'unknown').upper()}")
    print(f"   - Confidence: {shape_class.get('confidence', 0):.2f}")

    print(f"\n📋 Reconstruction Details:")
    print(f"   - Method: {result.get('method', 'unknown')}")
    print(f"   - Shape: {result.get('shape', 'unknown')}")
    print(f"   - Segments: {result.get('num_segments', 0)}")

    if 'parameters' in result:
        print(f"\n🔧 Primitive Parameters:")
        for key, value in result['parameters'].items():
            print(f"   - {key.capitalize()}: {value:.2f} mm")

    # Calculate quality metrics
    reconstructed_mesh = result.get('reconstructed_mesh')
    if reconstructed_mesh is not None:
        metrics = reconstructor.calculate_quality_metrics(mesh, reconstructed_mesh)

        print(f"\n📈 Quality Metrics:")
        print(f"   - Original Volume: {metrics['volume_original']:.2f} mm³")
        print(f"   - Reconstructed Volume: {metrics['volume_reconstructed']:.2f} mm³")
        print(f"   - Volume Error: {metrics['volume_error']*100:.2f}%")
        print(f"   - Quality Score: {metrics['quality_score']:.1f}/100")

        # Update result with metrics
        result['quality_score'] = metrics['quality_score']
        result['volume_error'] = metrics['volume_error']

    # Multi-view details
    views = result.get('views', [])
    if len(views) > 0:
        print(f"\n🔍 Multi-View Analysis:")
        for view in views:
            prim = view.primitive
            if prim.get('valid'):
                print(f"   {view.name.capitalize()} view: {prim['type'].upper()} "
                      f"(confidence: {prim.get('confidence', 0):.2f})")

    # Save output
    output_dir = Path('./output/hybrid')
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh_name = Path(mesh_path).stem

    # Save reconstructed mesh
    if reconstructed_mesh is not None and len(reconstructed_mesh.faces) > 0:
        output_mesh_path = output_dir / f"{mesh_name}_hybrid_reconstructed.stl"
        reconstructed_mesh.export(str(output_mesh_path))
        print(f"\n💾 Reconstructed mesh saved: {output_mesh_path}")

    # Generate visualization
    try:
        print(f"\n📸 Generating comparison visualization...")
        viz_path = output_dir / f"{mesh_name}_hybrid_comparison.png"
        visualize_comparison(
            original=mesh,
            reconstructed=reconstructed_mesh,
            result=result,
            output_path=str(viz_path)
        )
    except Exception as e:
        print(f"   ⚠️  Visualization failed: {e}")

    print("\n" + "="*80)
    print("✅ HYBRID RECONSTRUCTION COMPLETE")
    print("="*80)

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/demo_hybrid_reconstruction.py <mesh.stl>")
        print("\nExamples:")
        print("  python scripts/demo_hybrid_reconstruction.py tests/samples/simple_block.stl")
        print("  python scripts/demo_hybrid_reconstruction.py tests/samples/simple_cylinder.stl")
        sys.exit(1)

    mesh_path = sys.argv[1]
    demo_reconstruction(mesh_path, verbose=True)


if __name__ == '__main__':
    main()
