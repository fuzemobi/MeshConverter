#!/usr/bin/env python3
"""
MeshConverter CLI - Command-line interface for mesh-to-CAD conversion.

Usage:
    mc input.stl                          # Use voxel classifier (default)
    mc input.stl --classifier voxel       # Explicit voxel classifier
    mc input.stl --classifier gpt4-vision # Use GPT-4 Vision
    mc input.stl --classifier heuristic   # Use bbox_ratio heuristic
    mc input.stl --classifier all         # Compare all methods
"""

import sys
import argparse
import os
from pathlib import Path
import trimesh
import yaml
from typing import Dict, Any, Optional, List

# Import classification methods
from meshconverter.classification import (
    classify_mesh_with_voxel,
    classify_mesh_with_vision
)

# Import core modules
from core.mesh_loader import MeshLoader
from detection.simple_detector import SimpleDetector


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file (default: ./config.yaml)

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

    if not Path(config_path).exists():
        print(f"⚠️  Warning: Config file not found: {config_path}")
        print("Using default configuration")
        return {}

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config or {}
    except Exception as e:
        print(f"⚠️  Warning: Failed to load config: {e}")
        return {}


def classify_heuristic(mesh: trimesh.Trimesh, config: Dict) -> Dict[str, Any]:
    """
    Classify using heuristic bbox_ratio method.

    Args:
        mesh: Input trimesh
        config: Configuration dictionary

    Returns:
        Classification result
    """
    print("\n📐 Classifying with heuristic (bbox_ratio)...")

    # Calculate bbox ratio
    bbox_volume = mesh.bounding_box.volume
    mesh_volume = mesh.volume
    bbox_ratio = mesh_volume / bbox_volume if bbox_volume > 0 else 0

    # Classify based on thresholds
    if bbox_ratio >= 0.85:
        shape_type = 'box'
        confidence = 90
        reasoning = f'High bbox_ratio ({bbox_ratio:.3f}) indicates solid/hollow box'
    elif 0.40 <= bbox_ratio <= 0.85:
        shape_type = 'cylinder'
        confidence = 85
        reasoning = f'Medium bbox_ratio ({bbox_ratio:.3f}) indicates cylinder'
    elif 0.50 <= bbox_ratio <= 0.55:
        shape_type = 'sphere'
        confidence = 80
        reasoning = f'Bbox_ratio ({bbox_ratio:.3f}) near π/6 indicates sphere'
    else:
        shape_type = 'complex'
        confidence = 60
        reasoning = f'Bbox_ratio ({bbox_ratio:.3f}) suggests complex geometry'

    print(f"  ✅ Classification: {shape_type} ({confidence}%)")
    print(f"     Reasoning: {reasoning}")

    return {
        'shape_type': shape_type,
        'confidence': confidence,
        'n_components': 1,
        'reasoning': reasoning,
        'bbox_ratio': bbox_ratio,
        'method': 'heuristic'
    }


def classify_mesh(
    mesh: trimesh.Trimesh,
    method: str,
    config: Dict[str, Any],
    voxel_size: float = 1.0,
    erosion_iterations: int = 0
) -> Dict[str, Any]:
    """
    Classify mesh using specified method.

    Args:
        mesh: Input trimesh
        method: Classification method ('voxel', 'gpt4-vision', 'heuristic', 'all')
        config: Configuration dictionary
        voxel_size: Voxel size for voxel method
        erosion_iterations: Erosion iterations for voxel method

    Returns:
        Classification result or list of results if method='all'
    """
    if method == 'voxel':
        return classify_mesh_with_voxel(
            mesh,
            voxel_size=voxel_size,
            erosion_iterations=erosion_iterations,
            verbose=True
        )

    elif method == 'gpt4-vision':
        # Check for API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ Error: OPENAI_API_KEY environment variable not set")
            print("   Set it with: export OPENAI_API_KEY='your-key-here'")
            sys.exit(1)

        return classify_mesh_with_vision(mesh, api_key=api_key, verbose=True)

    elif method == 'heuristic':
        return classify_heuristic(mesh, config)

    elif method == 'all':
        print("\n🔍 Running all classification methods for comparison...\n")
        print("=" * 70)

        results = []

        # Heuristic
        try:
            heuristic_result = classify_heuristic(mesh, config)
            results.append(heuristic_result)
        except Exception as e:
            print(f"⚠️  Heuristic failed: {e}")

        # Voxel
        try:
            voxel_result = classify_mesh_with_voxel(
                mesh, voxel_size=voxel_size,
                erosion_iterations=erosion_iterations,
                verbose=True
            )
            results.append(voxel_result)
        except Exception as e:
            print(f"⚠️  Voxel failed: {e}")

        # GPT-4 Vision (if API key available)
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                vision_result = classify_mesh_with_vision(mesh, api_key=api_key, verbose=True)
                results.append(vision_result)
            except Exception as e:
                print(f"⚠️  GPT-4 Vision failed: {e}")
        else:
            print("\n⊘ GPT-4 Vision skipped (no OPENAI_API_KEY)")

        # Print comparison
        print("\n" + "=" * 70)
        print("\n📊 Classification Method Comparison")
        print("=" * 70)
        print(f"{'Method':<20} {'Shape Type':<15} {'Confidence':<12} {'Status'}")
        print("-" * 70)

        for result in results:
            method_name = result.get('method', 'unknown')
            shape_type = result.get('shape_type', 'unknown')
            confidence = result.get('confidence', 0)
            status = "✅" if confidence >= 80 else "⚠️"
            print(f"{method_name:<20} {shape_type:<15} {confidence}%{' ' * 8} {status}")

        print("=" * 70)

        # Check agreement
        shape_types = [r.get('shape_type') for r in results]
        if len(set(shape_types)) == 1:
            print(f"\n✅ Agreement: All methods agree on '{shape_types[0]}'")
        else:
            print(f"\n⚠️  Disagreement: Methods suggest different shapes: {set(shape_types)}")

        # Return highest confidence result
        best_result = max(results, key=lambda r: r.get('confidence', 0))
        print(f"📌 Recommended: {best_result['method']} (highest confidence: {best_result['confidence']}%)")

        return {'all_results': results, 'best_result': best_result}

    else:
        print(f"❌ Error: Unknown classification method: {method}")
        print("   Available methods: voxel, gpt4-vision, heuristic, all")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MeshConverter - Convert 3D meshes to parametric CAD primitives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mc input.stl                          # Use voxel classifier (default)
  mc input.stl --classifier voxel       # Explicit voxel classifier
  mc input.stl --classifier gpt4-vision # Use GPT-4 Vision
  mc input.stl --classifier heuristic   # Use bbox_ratio heuristic
  mc input.stl --classifier all         # Compare all methods

For more information: https://github.com/medtracket/meshconverter
        """
    )

    parser.add_argument(
        'input',
        type=str,
        help='Input STL mesh file'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output directory (default: ./output/<basename>)'
    )

    parser.add_argument(
        '-c', '--classifier',
        type=str,
        choices=['voxel', 'gpt4-vision', 'heuristic', 'all'],
        default='voxel',
        help='Classification method (default: voxel)'
    )

    parser.add_argument(
        '--voxel-size',
        type=float,
        default=1.0,
        help='Voxel size in mm for voxel classifier (default: 1.0)'
    )

    parser.add_argument(
        '--erosion',
        type=int,
        default=0,
        help='Erosion iterations for voxel classifier (default: 0)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to config.yaml file (default: ./config.yaml)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 2.0.0'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Check input file
    if not os.path.exists(args.input):
        print(f"❌ Error: Input file not found: {args.input}")
        sys.exit(1)

    # Print header
    print("\n" + "=" * 70)
    print("MeshConverter v2.0.0 - Mesh to CAD Primitive Converter")
    print("=" * 70)
    print(f"Input: {args.input}")
    print(f"Classifier: {args.classifier}")
    print("=" * 70)

    # Load mesh
    print(f"\n📂 Loading mesh: {args.input}")
    try:
        mesh = trimesh.load(args.input)
        print(f"  ✅ Loaded {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        print(f"     Volume: {mesh.volume:.2f} mm³")
        print(f"     Bounding box: {mesh.bounding_box.extents}")
    except Exception as e:
        print(f"❌ Error loading mesh: {e}")
        sys.exit(1)

    # Classify mesh
    try:
        result = classify_mesh(
            mesh,
            method=args.classifier,
            config=config,
            voxel_size=args.voxel_size,
            erosion_iterations=args.erosion
        )

        # TODO: Generate outputs (simplified STL, CadQuery script, etc.)
        # For now, just print results

        print("\n" + "=" * 70)
        print("✅ Classification complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error during classification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
