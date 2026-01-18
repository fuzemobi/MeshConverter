#!/usr/bin/env python3
"""
MeshConverter v2.1 - All-Shapes Conversion

Enhanced version that evaluates ALL primitive shapes (box, cylinder, sphere, cone)
and automatically selects the best fit based on quality metrics.

Usage:
    python convert_mesh_allshapes.py input.stl
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent  # Go up one level from scripts/ to project root
sys.path.insert(0, str(project_root))

import trimesh
import numpy as np
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from collections import Counter

# Import ALL primitives
from primitives.cylinder import CylinderPrimitive
from primitives.box import BoxPrimitive
from primitives.sphere import SpherePrimitive
from primitives.cone import ConePrimitive
from meshconverter.reconstruction.layer_analyzer import analyze_mesh_layers
from meshconverter.reconstruction.outlier_removal import smart_outlier_removal
from meshconverter.reconstruction.layer_wise_stacker import LayerWiseStacker
from meshconverter.validation.multiview_validator import validate_reconstruction


def test_all_primitives(
    mesh: trimesh.Trimesh,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Test ALL primitive shapes and return quality scores.

    This is the key innovation: instead of guessing the shape first,
    we FIT ALL SHAPES and let the quality metrics decide.

    Args:
        mesh: Input trimesh
        verbose: Print progress

    Returns:
        List of results, sorted by quality score (best first)
    """
    if verbose:
        print("\n🧪 Testing ALL primitive shapes...")

    results = []

    # Test 1: BOX
    try:
        if verbose:
            print("  Testing BOX...", end=" ")
        box = BoxPrimitive()
        box.fit(mesh)
        box_mesh = box.generate_mesh()

        vol_error = abs(box_mesh.volume - mesh.volume) / mesh.volume if mesh.volume > 0 else 1.0
        quality = int(100 * (1 - vol_error))

        results.append({
            'shape': 'box',
            'primitive': box,
            'mesh': box_mesh,
            'quality_score': quality,
            'volume_error': vol_error * 100,
            'confidence': min(quality, 95)
        })

        if verbose:
            print(f"Quality: {quality}/100")

    except Exception as e:
        if verbose:
            print(f"Failed: {e}")

    # Test 2: CYLINDER
    try:
        if verbose:
            print("  Testing CYLINDER...", end=" ")
        cylinder = CylinderPrimitive()
        cylinder.fit(mesh)
        cyl_mesh = cylinder.generate_mesh()

        vol_error = abs(cyl_mesh.volume - mesh.volume) / mesh.volume if mesh.volume > 0 else 1.0
        quality = int(100 * (1 - vol_error))

        results.append({
            'shape': 'cylinder',
            'primitive': cylinder,
            'mesh': cyl_mesh,
            'quality_score': quality,
            'volume_error': vol_error * 100,
            'confidence': min(quality, 95)
        })

        if verbose:
            print(f"Quality: {quality}/100")

    except Exception as e:
        if verbose:
            print(f"Failed: {e}")

    # Test 3: SPHERE
    try:
        if verbose:
            print("  Testing SPHERE...", end=" ")
        sphere = SpherePrimitive()
        sphere.fit(mesh)
        sphere_mesh = sphere.generate_mesh()

        vol_error = abs(sphere_mesh.volume - mesh.volume) / mesh.volume if mesh.volume > 0 else 1.0
        quality = int(100 * (1 - vol_error))

        results.append({
            'shape': 'sphere',
            'primitive': sphere,
            'mesh': sphere_mesh,
            'quality_score': quality,
            'volume_error': vol_error * 100,
            'confidence': min(quality, 95)
        })

        if verbose:
            print(f"Quality: {quality}/100")

    except Exception as e:
        if verbose:
            print(f"Failed: {e}")

    # Test 4: CONE
    try:
        if verbose:
            print("  Testing CONE...", end=" ")
        cone = ConePrimitive()
        cone.fit(mesh)
        cone_mesh = cone.generate_mesh()

        vol_error = abs(cone_mesh.volume - mesh.volume) / mesh.volume if mesh.volume > 0 else 1.0
        quality = int(100 * (1 - vol_error))

        results.append({
            'shape': 'cone',
            'primitive': cone,
            'mesh': cone_mesh,
            'quality_score': quality,
            'volume_error': vol_error * 100,
            'confidence': min(quality, 95)
        })

        if verbose:
            print(f"Quality: {quality}/100")

    except Exception as e:
        if verbose:
            print(f"Failed: {e}")

    # Sort by quality score (best first)
    results.sort(key=lambda x: x['quality_score'], reverse=True)

    if verbose and results:
        print(f"\n  📊 Best fit: {results[0]['shape'].upper()} ({results[0]['quality_score']}/100)")

    return results


def analyze_with_vision(
    mesh: trimesh.Trimesh,
    n_layers: int = 5,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """Analyze mesh layers with GPT-4o Vision."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        if verbose:
            print("  ⊘ Vision analysis skipped (no OPENAI_API_KEY)")
        return None

    try:
        from meshconverter.reconstruction.vision_layer_analyzer import VisionLayerAnalyzer

        analyzer = VisionLayerAnalyzer(api_key=api_key)

        bounds = mesh.bounds
        z_min, z_max = bounds[0, 2], bounds[1, 2]
        z_range = z_max - z_min
        sample_z = np.linspace(z_min + z_range * 0.1, z_max - z_range * 0.1, n_layers)

        results = []
        for i, z in enumerate(sample_z):
            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if section is None or len(section.vertices) == 0:
                continue

            result = analyzer.analyze_layer_for_outliers(section, z, i, verbose=False)
            results.append(result)

            if verbose:
                shape = result.get('shape_detected', '?')
                conf = result.get('confidence', 0)
                print(f"  Layer {i+1}/{n_layers} @ Z={z:.1f}mm: {shape} ({conf}%)")

        if not results:
            return None

        shapes = [r.get('shape_detected', 'unknown') for r in results]
        confidences = [r.get('confidence', 0) for r in results]

        shape_counts = Counter(shapes)
        consensus = shape_counts.most_common(1)[0][0]

        if verbose:
            print(f"  Vision consensus: {consensus} ({shape_counts[consensus]}/{len(results)} layers)")

        return {
            'shape_consensus': consensus,
            'confidence': np.mean(confidences),
            'layer_results': results
        }

    except Exception as e:
        if verbose:
            print(f"  ⚠️  Vision analysis failed: {e}")
        return None


def reconstruct_layerwise_multi_segment(
    mesh: trimesh.Trimesh,
    layer_height: float = 0.5,
    vision_results: Optional[List[Dict]] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Reconstruct mesh using Layer-Wise Primitive Stacking (LPS).

    This is the Phase 4A multi-segment reconstruction approach that:
    1. Slices mesh into layers
    2. Fits 2D primitives to each layer
    3. Groups similar layers into segments using fuzzy logic
    4. Extrudes segments to 3D primitives
    5. Combines into final reconstruction

    Args:
        mesh: Input mesh
        layer_height: Distance between slices (mm)
        vision_results: Optional vision analysis results
        verbose: Print progress

    Returns:
        Result dictionary with reconstructed mesh and metadata
    """
    if verbose:
        print("\n🏗️  Using Layer-Wise Primitive Stacking (LPS)...")

    stacker = LayerWiseStacker(
        layer_height=layer_height,
        min_segment_height=0.5,
        verbose=verbose
    )

    result = stacker.reconstruct(mesh, vision_results)

    if not result['success']:
        return {
            'shape': 'multi-segment',
            'quality_score': 0,
            'confidence': 0,
            'method': 'layer-slicing',
            'error': result.get('error', 'Unknown error'),
            'mesh': None
        }

    # Format result for convert() compatibility
    return {
        'shape': 'multi-segment',
        'quality_score': result['quality_score'],
        'confidence': 85,  # Fixed confidence for LPS
        'method': 'layer-slicing',
        'mesh': result['reconstructed_mesh'],
        'num_segments': result['num_segments'],
        'segments': result['segments'],
        'primitive': None  # LPS doesn't have a single primitive
    }


def select_best_shape(
    all_results: List[Dict],
    vision_result: Optional[Dict] = None,
    layer_result: Optional[Dict] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Intelligently select best shape using quality metrics + vision guidance.

    Strategy:
    1. If vision is confident AND quality score is good → use vision-guided shape
    2. Else: use highest quality score from all-shapes test
    3. Special case: assembly detection overrides everything
    """
    if verbose:
        print("\n🎯 Selecting optimal shape...")

    # Check for assembly first (overrides everything)
    if layer_result and layer_result.get('detected_boxes') and len(layer_result['detected_boxes']) > 1:
        if verbose:
            print(f"  ✅ ASSEMBLY detected ({len(layer_result['detected_boxes'])} boxes) - overrides primitive fitting")
        return {
            'shape': 'assembly',
            'quality_score': 85,
            'confidence': 90,
            'method': 'layer-slicing',
            'data': layer_result
        }

    # Vision guidance (if confident)
    if vision_result and vision_result['confidence'] > 75:
        consensus = vision_result['shape_consensus']

        # Map vision shapes to primitives
        vision_to_primitive = {
            'circle': 'cylinder',
            'rectangle': 'box',
            'ellipse': 'cylinder',  # Treat as angled cylinder
        }

        if consensus in vision_to_primitive:
            suggested_shape = vision_to_primitive[consensus]

            # Find this shape in all_results
            for result in all_results:
                if result['shape'] == suggested_shape:
                    # Only use if quality is reasonable
                    if result['quality_score'] >= 60:
                        if verbose:
                            print(f"  ✅ Vision guided: {consensus.upper()} → {suggested_shape.upper()}")
                            print(f"     Quality: {result['quality_score']}/100, Confidence: {vision_result['confidence']:.0f}%")
                        result['method'] = 'vision-guided'
                        result['confidence'] = int(vision_result['confidence'])
                        return result

    # Fallback: Best quality score
    if all_results:
        best = all_results[0]  # Already sorted by quality
        if verbose:
            print(f"  ✅ Best fit by quality: {best['shape'].upper()}")
            print(f"     Quality: {best['quality_score']}/100")

        best['method'] = 'best-fit'
        return best

    # Last resort
    return {
        'shape': 'unknown',
        'quality_score': 0,
        'confidence': 0,
        'method': 'failed'
    }


def convert(
    input_path: str,
    output_path: Optional[str] = None,
    classifier: str = 'single-primitive',
    use_vision: bool = True,
    n_vision_layers: int = 5,
    use_layer_slicing: bool = True,
    layer_height: float = 0.5,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convert mesh to best-fitting primitive (ALL SHAPES TESTED).

    Args:
        input_path: Input STL
        output_path: Output STL (default: <input>_optimized.stl)
        classifier: Classifier type ('single-primitive' or 'layer-slicing')
        use_vision: Enable GPT-4o vision
        n_vision_layers: Vision sample layers
        use_layer_slicing: Enable assembly detection (for single-primitive mode)
        layer_height: Layer height (mm) for layer-slicing classifier
        verbose: Print progress

    Returns:
        Result dictionary
    """
    if verbose:
        print("\n" + "="*80)
        print(f"🔷 MeshConverter v2.1 - Classifier: {classifier.upper()}")
        print("="*80)
        print(f"Input: {input_path}")

    # Validate
    if not os.path.exists(input_path):
        return {'success': False, 'error': f'File not found: {input_path}'}

    if output_path is None:
        stem = Path(input_path).stem
        output_path = str(Path(input_path).parent / f"{stem}_optimized.stl")

    if verbose:
        print(f"Output: {output_path}")
        print("="*80)

    # Load
    if verbose:
        print("\n📂 Loading mesh...")

    try:
        mesh = trimesh.load(input_path)
        orig_stats = {
            'vertices': len(mesh.vertices),
            'faces': len(mesh.faces),
            'volume': float(mesh.volume)
        }
        if verbose:
            print(f"  ✅ {orig_stats['vertices']:,} vertices, {orig_stats['faces']:,} faces")
            print(f"     Volume: {orig_stats['volume']:.2f} mm³")
    except Exception as e:
        return {'success': False, 'error': f'Load failed: {e}'}

    # Vision
    vision_result = None
    if use_vision:
        if verbose:
            print(f"\n🔍 Vision analysis ({n_vision_layers} layers)...")
        vision_result = analyze_with_vision(mesh, n_vision_layers, verbose)

    # Phase 2: Vision-guided outlier removal
    cleaned_mesh = mesh
    outlier_metrics = None
    if vision_result and vision_result.get('layer_results'):
        if verbose:
            print(f"\n🧹 Phase 2: Vision-guided outlier removal...")
        try:
            cleaned_mesh, outlier_metrics = smart_outlier_removal(
                mesh,
                vision_result,
                conservative=True,  # Use conservative filtering by default
                verbose=verbose
            )
            if outlier_metrics.get('cleaned'):
                if verbose:
                    print(f"  ✅ Cleaning completed: {outlier_metrics.get('cleaning_quality', 'unknown')} quality")
            else:
                if verbose:
                    reason = outlier_metrics.get('reason', 'unknown')
                    print(f"  ℹ️  Cleaning skipped: {reason}")
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Outlier removal failed: {e}")
            cleaned_mesh = mesh  # Fallback to original

    # Branch based on classifier type
    all_results = []  # Initialize for metadata
    if classifier == 'layer-slicing':
        # Use Layer-Wise Primitive Stacking (LPS) for multi-segment reconstruction
        if verbose:
            print(f"\n🏗️  Using LAYER-SLICING classifier (Phase 4A)")

        vision_layer_results = vision_result.get('layer_results', []) if vision_result else None
        best = reconstruct_layerwise_multi_segment(
            cleaned_mesh,
            layer_height=layer_height,
            vision_results=vision_layer_results,
            verbose=verbose
        )

    else:
        # Default: single-primitive classification
        # Layer-slicing (for assembly detection)
        layer_result = None
        if use_layer_slicing:
            try:
                if verbose:
                    print(f"\n📋 Layer-slicing (height={layer_height}mm)...")
                layer_result = analyze_mesh_layers(cleaned_mesh, layer_height, verbose)
            except Exception as e:
                if verbose:
                    print(f"  ⚠️  Failed: {e}")

        # TEST ALL SHAPES (on cleaned mesh)
        all_results = test_all_primitives(cleaned_mesh, verbose)

        # Select best
        best = select_best_shape(all_results, vision_result, layer_result, verbose)

    # Handle assembly case
    if best['shape'] == 'assembly':
        # Reconstruct from boxes
        boxes = layer_result.get('detected_boxes', [])
        if boxes:
            meshes = []
            for box in boxes:
                center = np.array(box.get('center', [0, 0, 0]))
                dims = box.get('dimensions', [10, 10, 10])
                box_mesh = trimesh.creation.box(extents=dims)
                box_mesh.apply_translation(center - box_mesh.centroid)
                meshes.append(box_mesh)
            reconstructed = trimesh.util.concatenate(meshes)
        else:
            reconstructed = mesh
    elif 'mesh' in best:
        reconstructed = best['mesh']
    else:
        reconstructed = mesh

    # Phase 3: Multi-view validation (original vs reconstructed)
    validation_result = None
    if use_vision and os.getenv('OPENAI_API_KEY'):
        if verbose:
            print(f"\n🔍 Phase 3: Multi-view validation...")
        try:
            validation_result = validate_reconstruction(
                original=mesh,  # Compare against original (not cleaned)
                reconstructed=reconstructed,
                verbose=verbose
            )
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Validation failed: {e}")

    # Quality
    vol_error = abs(reconstructed.volume - mesh.volume) / mesh.volume if mesh.volume > 0 else 1.0
    quality_score = int(100 * (1 - vol_error))

    # Override quality score with validation score if available
    if validation_result and 'similarity_score' in validation_result:
        validation_score = validation_result['similarity_score']
        if verbose:
            print(f"\n📊 Quality Metrics:")
            print(f"  Volume error: {vol_error * 100:.2f}%")
            print(f"  Geometric quality: {quality_score}/100")
            print(f"  Visual similarity (GPT-4o): {validation_score}/100")
            print(f"  Reconstruction quality: {validation_result.get('reconstruction_quality', 'unknown').upper()}")

        # Use weighted average: 60% visual, 40% geometric
        combined_quality = int(0.6 * validation_score + 0.4 * quality_score)
        quality_score = combined_quality

        if verbose:
            print(f"  Combined quality score: {quality_score}/100")
    else:
        if verbose:
            print(f"\n📊 Quality:")
            print(f"  Volume error: {vol_error * 100:.2f}%")
            print(f"  Quality score: {quality_score}/100")

    metrics = {
        'volume_error_pct': float(vol_error * 100),
        'quality_score': quality_score,
        'face_reduction_pct': float((orig_stats['faces'] - len(reconstructed.faces)) / orig_stats['faces'] * 100)
    }

    # Add validation metrics if available
    if validation_result:
        metrics['validation'] = {
            'similarity_score': validation_result.get('similarity_score', 0),
            'reconstruction_quality': validation_result.get('reconstruction_quality', 'unknown'),
            'shape_match': validation_result.get('shape_match', 'unknown'),
            'dimension_accuracy': validation_result.get('dimension_accuracy', 'unknown'),
            'recommended_action': validation_result.get('recommended_action', 'unknown')
        }

    if verbose:
        print(f"  Faces: {len(reconstructed.faces):,} ({metrics['face_reduction_pct']:.1f}% reduction)")

    # Save
    if verbose:
        print(f"\n💾 Saving to {output_path}...")

    try:
        reconstructed.export(output_path)
        out_stats = {
            'vertices': len(reconstructed.vertices),
            'faces': len(reconstructed.faces),
            'volume': float(reconstructed.volume)
        }
        if verbose:
            print(f"  ✅ Saved!")
    except Exception as e:
        return {'success': False, 'error': f'Save failed: {e}'}

    # Metadata
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'input': input_path,
        'output': output_path,
        'shape': best['shape'],
        'confidence': float(best.get('confidence', 0)),
        'method': best.get('method', 'unknown'),
        'original': orig_stats,
        'output': out_stats,
        'metrics': metrics,
        'all_tested_shapes': [
            {'shape': r['shape'], 'quality': r['quality_score']}
            for r in all_results
        ] if all_results else [],
        'outlier_removal': outlier_metrics if outlier_metrics else None,
        'validation': validation_result if validation_result else None
    }

    metadata_path = str(Path(output_path).with_suffix('.json'))
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    except:
        pass

    # Summary
    if verbose:
        print("\n" + "="*80)
        print("✅ CONVERSION COMPLETE")
        print("="*80)
        print(f"Shape: {best['shape'].upper()}")
        print(f"Confidence: {best.get('confidence', 0):.0f}%")
        print(f"Quality: {quality_score}/100")

        if all_results:
            print(f"\nAll shapes tested (sorted by quality):")
            for r in all_results:
                print(f"  • {r['shape']:<12} {r['quality_score']}/100")

        print("="*80)

    return {
        'success': True,
        'input': input_path,
        'output': output_path,
        'metadata': metadata_path,
        'shape': best['shape'],
        'confidence': float(best.get('confidence', 0)),
        'metrics': metrics,
        'all_results': all_results
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert 3D mesh by testing ALL primitive shapes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Classifier Options:
  single-primitive    Test all shapes (box, cylinder, sphere, cone) and select best fit (default)
  layer-slicing       Multi-segment reconstruction using Layer-Wise Primitive Stacking (Phase 4A)

Examples:
  # Single-primitive mode (default)
  python convert_mesh_allshapes.py input.stl

  # Multi-segment reconstruction
  python convert_mesh_allshapes.py input.stl --classifier layer-slicing

  # Multi-segment with custom layer height
  python convert_mesh_allshapes.py battery.stl --classifier layer-slicing --layer-height 0.5
        """
    )
    parser.add_argument('input', help='Input STL file')
    parser.add_argument('-o', '--output', help='Output STL')
    parser.add_argument('--classifier',
                        choices=['single-primitive', 'layer-slicing'],
                        default='single-primitive',
                        help='Classifier type (default: single-primitive)')
    parser.add_argument('--no-vision', action='store_true', help='Disable vision')
    parser.add_argument('--vision-layers', type=int, default=5, help='Vision layers (default: 5)')
    parser.add_argument('--no-layer-slicing', action='store_true',
                        help='Disable assembly detection (single-primitive mode only)')
    parser.add_argument('--layer-height', type=float, default=0.5,
                        help='Layer height in mm (default: 0.5)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')

    args = parser.parse_args()

    result = convert(
        input_path=args.input,
        output_path=args.output,
        classifier=args.classifier,
        use_vision=not args.no_vision,
        n_vision_layers=args.vision_layers,
        use_layer_slicing=not args.no_layer_slicing,
        layer_height=args.layer_height,
        verbose=not args.quiet
    )

    if not result['success']:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    sys.exit(0)
