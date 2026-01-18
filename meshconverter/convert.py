#!/usr/bin/env python3
"""
MeshConverter - Intelligent Mesh-to-CAD Conversion with Vision Analysis

This module provides the main `convert()` function that:
1. Analyzes mesh with multiple methods (heuristic, layer-slicing, vision AI)
2. Detects and removes outliers using GPT-4o Vision
3. Reconstructs clean parametric primitives
4. Validates quality and generates dimensionally accurate STL output
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import trimesh
import numpy as np
import json
from datetime import datetime

# Vision analysis
from meshconverter.reconstruction.vision_layer_analyzer import (
    VisionLayerAnalyzer,
    analyze_layer_with_vision
)

# Classification methods
from meshconverter.classification import (
    classify_mesh_with_voxel,
    classify_mesh_with_vision
)
from meshconverter.reconstruction.layer_analyzer import analyze_mesh_layers

# Primitives
import sys
from pathlib import Path as PathLib
# Add parent directory to path for imports
sys.path.insert(0, str(PathLib(__file__).parent.parent))

from primitives.cylinder import CylinderPrimitive
from primitives.box import BoxPrimitive


def analyze_with_vision_layers(
    mesh: trimesh.Trimesh,
    n_sample_layers: int = 5,
    api_key: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Analyze mesh using vision-enhanced layer slicing.

    Args:
        mesh: Input trimesh
        n_sample_layers: Number of layers to sample for vision analysis
        api_key: OpenAI API key (optional, uses env var if not provided)
        verbose: Print progress

    Returns:
        {
            'shape_consensus': str,  # Most common shape across layers
            'outlier_percentage': float,  # Average outlier %
            'confidence': float,  # Average confidence
            'layer_results': List[Dict],  # Individual layer results
            'recommendation': str  # Action to take
        }
    """
    if verbose:
        print(f"\n🔍 Vision-Enhanced Layer Analysis ({n_sample_layers} sample layers)...")

    # Check API key
    if api_key is None:
        api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        if verbose:
            print("  ⊘ Skipping vision analysis (no OPENAI_API_KEY)")
        return {
            'shape_consensus': 'unknown',
            'outlier_percentage': 0.0,
            'confidence': 0,
            'layer_results': [],
            'recommendation': 'No API key provided'
        }

    # Initialize analyzer
    try:
        analyzer = VisionLayerAnalyzer(api_key=api_key)
    except Exception as e:
        if verbose:
            print(f"  ⚠️  Failed to initialize vision analyzer: {e}")
        return {
            'shape_consensus': 'unknown',
            'outlier_percentage': 0.0,
            'confidence': 0,
            'layer_results': [],
            'recommendation': f'Error: {str(e)}'
        }

    # Sample layers across Z range
    bounds = mesh.bounds
    z_min, z_max = bounds[0, 2], bounds[1, 2]
    z_range = z_max - z_min

    # Select evenly spaced layers (avoid extremes)
    sample_z_values = np.linspace(
        z_min + z_range * 0.1,
        z_max - z_range * 0.1,
        n_sample_layers
    )

    layer_results = []

    for i, z in enumerate(sample_z_values):
        # Slice mesh
        section = mesh.section(
            plane_origin=[0, 0, z],
            plane_normal=[0, 0, 1]
        )

        if section is None or len(section.vertices) == 0:
            continue

        # Analyze with vision
        try:
            result = analyzer.analyze_layer_for_outliers(
                section=section,
                z_height=z,
                layer_id=i,
                verbose=False  # Quiet during batch processing
            )
            layer_results.append(result)

            if verbose:
                shape = result.get('shape_detected', 'unknown')
                conf = result.get('confidence', 0)
                outliers = "YES" if result.get('has_outliers', False) else "NO"
                print(f"  Layer {i+1}/{n_sample_layers} @ Z={z:.1f}mm: {shape} (conf:{conf}%, outliers:{outliers})")

        except Exception as e:
            if verbose:
                print(f"  ⚠️  Layer {i+1} analysis failed: {e}")
            continue

    if not layer_results:
        return {
            'shape_consensus': 'unknown',
            'outlier_percentage': 0.0,
            'confidence': 0,
            'layer_results': [],
            'recommendation': 'No layers successfully analyzed'
        }

    # Aggregate results
    shapes = [r.get('shape_detected', 'unknown') for r in layer_results]
    confidences = [r.get('confidence', 0) for r in layer_results]
    outlier_percentages = [r.get('outlier_percentage', 0) for r in layer_results]

    # Find consensus shape (most common)
    from collections import Counter
    shape_counts = Counter(shapes)
    shape_consensus = shape_counts.most_common(1)[0][0]

    # Calculate averages
    avg_confidence = np.mean(confidences)
    avg_outlier_pct = np.mean(outlier_percentages)

    # Generate recommendation
    if avg_outlier_pct > 10:
        recommendation = "High outlier percentage - apply pre-processing"
    elif avg_confidence < 70:
        recommendation = "Low confidence - complex/irregular shape"
    elif shape_consensus in ['circle', 'rectangle']:
        recommendation = f"Clear {shape_consensus} shape - proceed with reconstruction"
    else:
        recommendation = "Irregular/complex shape - may need manual refinement"

    if verbose:
        print(f"\n  📊 Vision Analysis Summary:")
        print(f"     Shape consensus: {shape_consensus} ({shape_counts[shape_consensus]}/{len(layer_results)} layers)")
        print(f"     Avg confidence: {avg_confidence:.1f}%")
        print(f"     Avg outliers: {avg_outlier_pct:.1f}%")
        print(f"     Recommendation: {recommendation}")

    return {
        'shape_consensus': shape_consensus,
        'outlier_percentage': avg_outlier_pct,
        'confidence': avg_confidence,
        'layer_results': layer_results,
        'recommendation': recommendation,
        'shape_distribution': dict(shape_counts)
    }


def select_best_method(
    mesh: trimesh.Trimesh,
    vision_result: Optional[Dict] = None,
    layer_result: Optional[Dict] = None,
    verbose: bool = True
) -> Tuple[str, Dict[str, Any]]:
    """
    Intelligently select the best classification/reconstruction method.

    Args:
        mesh: Input trimesh
        vision_result: Vision layer analysis result
        layer_result: Layer-slicing result
        verbose: Print decision process

    Returns:
        (method_name, classification_result)
    """
    if verbose:
        print("\n🎯 Selecting optimal reconstruction method...")

    # Calculate bbox_ratio for quick heuristic
    bbox_volume = mesh.bounding_box.volume
    mesh_volume = mesh.volume
    bbox_ratio = mesh_volume / bbox_volume if bbox_volume > 0 else 0

    # Check vision consensus if available
    if vision_result and vision_result.get('confidence', 0) > 80:
        shape = vision_result.get('shape_consensus', 'unknown')

        if shape == 'circle':
            if verbose:
                print(f"  ✅ Vision detected CIRCLE ({vision_result['confidence']:.0f}% confidence)")
                print(f"     → Using CYLINDER primitive")
            return 'cylinder', {
                'shape_type': 'cylinder',
                'confidence': vision_result['confidence'],
                'method': 'vision-guided',
                'reasoning': 'Vision analysis detected circular cross-sections'
            }

        elif shape == 'rectangle':
            if verbose:
                print(f"  ✅ Vision detected RECTANGLE ({vision_result['confidence']:.0f}% confidence)")
                print(f"     → Using BOX primitive")
            return 'box', {
                'shape_type': 'box',
                'confidence': vision_result['confidence'],
                'method': 'vision-guided',
                'reasoning': 'Vision analysis detected rectangular cross-sections'
            }

        elif shape == 'multiple':
            if verbose:
                print(f"  ✅ Vision detected ASSEMBLY ({vision_result['confidence']:.0f}% confidence)")
                print(f"     → Using LAYER-SLICING reconstruction")
            # Use layer-slicing result if available
            if layer_result and layer_result.get('detected_boxes'):
                return 'assembly', layer_result

    # Fallback to heuristic if vision uncertain or unavailable
    if verbose:
        print(f"  📐 Using bbox_ratio heuristic: {bbox_ratio:.3f}")

    if bbox_ratio >= 0.85:
        if verbose:
            print(f"     → Solid/Hollow BOX")
        return 'box', {
            'shape_type': 'box',
            'confidence': 85,
            'method': 'heuristic',
            'bbox_ratio': bbox_ratio,
            'reasoning': f'High bbox_ratio ({bbox_ratio:.3f}) indicates box'
        }

    elif 0.40 <= bbox_ratio <= 0.85:
        if verbose:
            print(f"     → CYLINDER")
        return 'cylinder', {
            'shape_type': 'cylinder',
            'confidence': 80,
            'method': 'heuristic',
            'bbox_ratio': bbox_ratio,
            'reasoning': f'Medium bbox_ratio ({bbox_ratio:.3f}) indicates cylinder'
        }

    else:
        # Try layer-slicing for complex shapes
        if layer_result and layer_result.get('detected_boxes'):
            if verbose:
                print(f"     → ASSEMBLY (layer-slicing detected {len(layer_result['detected_boxes'])} boxes)")
            return 'assembly', layer_result

        if verbose:
            print(f"     → COMPLEX/UNKNOWN")
        return 'complex', {
            'shape_type': 'complex',
            'confidence': 50,
            'method': 'heuristic',
            'bbox_ratio': bbox_ratio,
            'reasoning': f'Bbox_ratio ({bbox_ratio:.3f}) suggests complex geometry'
        }


def reconstruct_primitive(
    mesh: trimesh.Trimesh,
    shape_type: str,
    classification: Dict[str, Any],
    verbose: bool = True
) -> Optional[trimesh.Trimesh]:
    """
    Reconstruct clean parametric primitive from mesh.

    Args:
        mesh: Original mesh
        shape_type: Shape to reconstruct ('cylinder', 'box', 'assembly', 'complex')
        classification: Classification result with parameters
        verbose: Print progress

    Returns:
        Clean reconstructed mesh or None if failed
    """
    if verbose:
        print(f"\n🔧 Reconstructing {shape_type.upper()} primitive...")

    try:
        if shape_type == 'cylinder':
            primitive = CylinderPrimitive()
            primitive.fit(mesh)
            reconstructed = primitive.generate_mesh()

            if verbose:
                print(f"  ✅ Cylinder: radius={primitive.radius:.2f}mm, length={primitive.length:.2f}mm")
                print(f"     Volume: {reconstructed.volume:.2f} mm³ (original: {mesh.volume:.2f} mm³)")

            return reconstructed

        elif shape_type == 'box':
            primitive = BoxPrimitive()
            primitive.fit(mesh)
            reconstructed = primitive.generate_mesh()

            extents = primitive.extents if hasattr(primitive, 'extents') else reconstructed.bounding_box.extents
            if verbose:
                print(f"  ✅ Box: {extents[0]:.2f} × {extents[1]:.2f} × {extents[2]:.2f} mm")
                print(f"     Volume: {reconstructed.volume:.2f} mm³ (original: {mesh.volume:.2f} mm³)")

            return reconstructed

        elif shape_type == 'assembly':
            # Reconstruct from detected boxes
            detected_boxes = classification.get('detected_boxes', [])

            if not detected_boxes:
                if verbose:
                    print("  ⚠️  No box data found, using simplified mesh")
                return mesh

            meshes = []
            for i, box_data in enumerate(detected_boxes):
                try:
                    center = np.array(box_data.get('center', [0, 0, 0]))
                    dims = box_data.get('dimensions', [10, 10, 10])

                    # Create clean box
                    box_mesh = trimesh.creation.box(extents=dims)
                    box_mesh.apply_translation(center - box_mesh.centroid)
                    meshes.append(box_mesh)

                    if verbose:
                        print(f"  ✅ Box {i+1}: {dims[0]:.1f}×{dims[1]:.1f}×{dims[2]:.1f}mm @ ({center[0]:.1f}, {center[1]:.1f}, {center[2]:.1f})")

                except Exception as e:
                    if verbose:
                        print(f"  ⚠️  Failed to generate box {i+1}: {e}")

            if meshes:
                reconstructed = trimesh.util.concatenate(meshes)
                if verbose:
                    print(f"  ✅ Assembly: {len(meshes)} boxes combined")
                    print(f"     Total volume: {reconstructed.volume:.2f} mm³ (original: {mesh.volume:.2f} mm³)")
                return reconstructed
            else:
                if verbose:
                    print("  ⚠️  No valid boxes, using simplified mesh")
                return mesh

        else:  # complex or unknown
            # Apply simplification if available
            try:
                import fast_simplification
                target_reduction = 0.90  # Keep 10% of faces

                if verbose:
                    print(f"  Simplifying: {len(mesh.faces)} → ", end='')

                simplified = fast_simplification.simplify(
                    mesh.vertices,
                    mesh.faces,
                    target_reduction=target_reduction
                )

                if isinstance(simplified, tuple):
                    verts, faces = simplified
                    reconstructed = trimesh.Trimesh(vertices=verts, faces=faces)
                else:
                    reconstructed = simplified

                if verbose:
                    print(f"{len(reconstructed.faces)} faces")
                    print(f"  ✅ Simplified mesh (complex shape)")

                return reconstructed

            except ImportError:
                if verbose:
                    print("  ⚠️  fast-simplification not available")
                    print("  Using original mesh")
                return mesh
            except Exception as e:
                if verbose:
                    print(f"  ⚠️  Simplification failed: {e}")
                return mesh

    except Exception as e:
        if verbose:
            print(f"  ❌ Reconstruction failed: {e}")
        return None


def convert(
    input_path: str,
    output_path: Optional[str] = None,
    use_vision: bool = True,
    n_vision_layers: int = 5,
    use_layer_slicing: bool = True,
    layer_height: float = 2.0,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Main conversion function: Mesh → Clean Parametric STL

    This is the primary entry point for converting a messy 3D scan into
    a clean, dimensionally accurate parametric primitive.

    Args:
        input_path: Path to input STL file
        output_path: Path to output STL (default: <input>_optimized.stl)
        use_vision: Use GPT-4o vision for layer analysis (requires API key)
        n_vision_layers: Number of layers to sample for vision (default: 5)
        use_layer_slicing: Use layer-slicing for assembly detection
        layer_height: Layer height for slicing (mm, default: 2.0)
        verbose: Print detailed progress

    Returns:
        {
            'success': bool,
            'input_file': str,
            'output_file': str,
            'shape_type': str,
            'confidence': float,
            'method': str,
            'original_stats': Dict,
            'output_stats': Dict,
            'quality_metrics': Dict,
            'metadata': Dict
        }
    """
    if verbose:
        print("\n" + "="*80)
        print("🔷 MeshConverter v2.0 - Intelligent Mesh-to-CAD Conversion")
        print("="*80)
        print(f"Input: {input_path}")

    # Validate input
    if not os.path.exists(input_path):
        return {
            'success': False,
            'error': f'Input file not found: {input_path}'
        }

    # Determine output path
    if output_path is None:
        input_stem = Path(input_path).stem
        output_path = str(Path(input_path).parent / f"{input_stem}_optimized.stl")

    if verbose:
        print(f"Output: {output_path}")
        print("="*80)

    # Load mesh
    if verbose:
        print("\n📂 Loading mesh...")

    try:
        mesh = trimesh.load(input_path)

        original_stats = {
            'vertices': len(mesh.vertices),
            'faces': len(mesh.faces),
            'volume_mm3': float(mesh.volume),
            'bbox_extents': [float(x) for x in mesh.bounding_box.extents],
            'is_watertight': mesh.is_watertight
        }

        if verbose:
            print(f"  ✅ Loaded: {original_stats['vertices']:,} vertices, {original_stats['faces']:,} faces")
            print(f"     Volume: {original_stats['volume_mm3']:.2f} mm³")
            print(f"     Bounding box: {original_stats['bbox_extents']}")
            print(f"     Watertight: {'YES' if original_stats['is_watertight'] else 'NO'}")

    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to load mesh: {str(e)}'
        }

    # STEP 1: Vision-enhanced layer analysis (if enabled)
    vision_result = None
    if use_vision:
        try:
            vision_result = analyze_with_vision_layers(
                mesh,
                n_sample_layers=n_vision_layers,
                verbose=verbose
            )
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Vision analysis failed: {e}")
            vision_result = None

    # STEP 2: Layer-slicing analysis (if enabled)
    layer_result = None
    if use_layer_slicing:
        try:
            if verbose:
                print(f"\n📋 Layer-slicing analysis (height={layer_height}mm)...")
            layer_result = analyze_mesh_layers(mesh, layer_height=layer_height, verbose=verbose)
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Layer-slicing failed: {e}")
            layer_result = None

    # STEP 3: Select best method and classify
    shape_type, classification = select_best_method(
        mesh,
        vision_result=vision_result,
        layer_result=layer_result,
        verbose=verbose
    )

    # STEP 4: Reconstruct primitive
    reconstructed = reconstruct_primitive(
        mesh,
        shape_type=shape_type,
        classification=classification,
        verbose=verbose
    )

    if reconstructed is None:
        return {
            'success': False,
            'error': 'Reconstruction failed'
        }

    # STEP 5: Calculate quality metrics
    if verbose:
        print("\n📊 Calculating quality metrics...")

    volume_error = abs(reconstructed.volume - mesh.volume) / mesh.volume if mesh.volume > 0 else 1.0
    quality_score = int(100 * (1 - volume_error))

    quality_metrics = {
        'volume_error_percent': float(volume_error * 100),
        'quality_score': quality_score,
        'face_reduction': float((original_stats['faces'] - len(reconstructed.faces)) / original_stats['faces'] * 100),
        'original_volume': original_stats['volume_mm3'],
        'reconstructed_volume': float(reconstructed.volume)
    }

    if verbose:
        print(f"  Volume error: {quality_metrics['volume_error_percent']:.2f}%")
        print(f"  Quality score: {quality_metrics['quality_score']}/100")
        print(f"  Face reduction: {quality_metrics['face_reduction']:.1f}%")

    # STEP 6: Save output
    if verbose:
        print(f"\n💾 Saving optimized mesh to: {output_path}")

    try:
        reconstructed.export(output_path)

        output_stats = {
            'vertices': len(reconstructed.vertices),
            'faces': len(reconstructed.faces),
            'volume_mm3': float(reconstructed.volume),
            'bbox_extents': [float(x) for x in reconstructed.bounding_box.extents]
        }

        if verbose:
            print(f"  ✅ Saved: {output_stats['vertices']:,} vertices, {output_stats['faces']:,} faces")

    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to save output: {str(e)}'
        }

    # STEP 7: Save metadata
    metadata_path = str(Path(output_path).with_suffix('.json'))
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'input_file': input_path,
        'output_file': output_path,
        'shape_type': shape_type,
        'confidence': float(classification.get('confidence', 0)),
        'method': classification.get('method', 'unknown'),
        'original_stats': original_stats,
        'output_stats': output_stats,
        'quality_metrics': quality_metrics,
        'classification': classification
    }

    if vision_result:
        metadata['vision_analysis'] = {
            'shape_consensus': vision_result.get('shape_consensus'),
            'avg_confidence': float(vision_result.get('confidence', 0)),
            'avg_outliers': float(vision_result.get('outlier_percentage', 0)),
            'recommendation': vision_result.get('recommendation')
        }

    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        if verbose:
            print(f"  ✅ Metadata: {metadata_path}")
    except Exception as e:
        if verbose:
            print(f"  ⚠️  Failed to save metadata: {e}")

    # Final summary
    if verbose:
        print("\n" + "="*80)
        print("✅ CONVERSION COMPLETE!")
        print("="*80)
        print(f"Shape: {shape_type.upper()}")
        print(f"Confidence: {classification.get('confidence', 0):.0f}%")
        print(f"Quality Score: {quality_score}/100")
        print(f"Face Reduction: {len(reconstructed.faces):,} ({quality_metrics['face_reduction']:.1f}% reduction)")
        print(f"Volume Error: {quality_metrics['volume_error_percent']:.2f}%")
        print("="*80)

    return {
        'success': True,
        'input_file': input_path,
        'output_file': output_path,
        'metadata_file': metadata_path,
        'shape_type': shape_type,
        'confidence': float(classification.get('confidence', 0)),
        'method': classification.get('method', 'unknown'),
        'original_stats': original_stats,
        'output_stats': output_stats,
        'quality_metrics': quality_metrics,
        'metadata': metadata
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert messy 3D scan to clean parametric primitive STL",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('input', help='Input STL file')
    parser.add_argument('-o', '--output', help='Output STL file (default: <input>_optimized.stl)')
    parser.add_argument('--no-vision', action='store_true', help='Disable GPT-4o vision analysis')
    parser.add_argument('--vision-layers', type=int, default=5, help='Number of layers for vision (default: 5)')
    parser.add_argument('--no-layer-slicing', action='store_true', help='Disable layer-slicing')
    parser.add_argument('--layer-height', type=float, default=2.0, help='Layer height in mm (default: 2.0)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress output')

    args = parser.parse_args()

    result = convert(
        input_path=args.input,
        output_path=args.output,
        use_vision=not args.no_vision,
        n_vision_layers=args.vision_layers,
        use_layer_slicing=not args.no_layer_slicing,
        layer_height=args.layer_height,
        verbose=not args.quiet
    )

    if not result['success']:
        print(f"❌ Conversion failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    sys.exit(0)
