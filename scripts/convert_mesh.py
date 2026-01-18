#!/usr/bin/env python3
"""
MeshConverter - Standalone Conversion Script

Simple, standalone script to convert messy 3D scans to clean parametric STL primitives.
Integrates vision-based layer analysis for intelligent shape detection.

Usage:
    python convert_mesh.py input.stl                    # Auto-convert with vision
    python convert_mesh.py input.stl --no-vision        # Convert without vision
    python convert_mesh.py input.stl -o output.stl      # Specify output path
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import trimesh
import numpy as np
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from collections import Counter

# Import primitives
from primitives.cylinder import CylinderPrimitive
from primitives.box import BoxPrimitive
from meshconverter.reconstruction.layer_analyzer import analyze_mesh_layers


def analyze_with_vision(
    mesh: trimesh.Trimesh,
    n_layers: int = 5,
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Analyze mesh layers with GPT-4o Vision.

    Returns vision analysis result or None if unavailable/failed.
    """
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        if verbose:
            print("  ⊘ Vision analysis skipped (no OPENAI_API_KEY)")
        return None

    try:
        from meshconverter.reconstruction.vision_layer_analyzer import VisionLayerAnalyzer

        analyzer = VisionLayerAnalyzer(api_key=api_key)

        # Sample layers
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

        # Aggregate
        shapes = [r.get('shape_detected', 'unknown') for r in results]
        confidences = [r.get('confidence', 0) for r in results]
        outliers = [r.get('outlier_percentage', 0) for r in results]

        shape_counts = Counter(shapes)
        consensus = shape_counts.most_common(1)[0][0]

        if verbose:
            print(f"  Vision consensus: {consensus} ({shape_counts[consensus]}/{len(results)} layers)")
            print(f"  Avg confidence: {np.mean(confidences):.1f}%")

        return {
            'shape_consensus': consensus,
            'confidence': np.mean(confidences),
            'outlier_percentage': np.mean(outliers),
            'layer_results': results
        }

    except Exception as e:
        if verbose:
            print(f"  ⚠️  Vision analysis failed: {e}")
        return None


def classify_mesh(
    mesh: trimesh.Trimesh,
    vision_result: Optional[Dict] = None,
    layer_result: Optional[Dict] = None,
    verbose: bool = True
) -> Tuple[str, Dict]:
    """
    Classify mesh shape using available analysis results.

    Returns: (shape_type, classification_dict)
    """
    if verbose:
        print("\n🎯 Classifying shape...")

    # Calculate bbox ratio
    bbox_vol = mesh.bounding_box.volume
    mesh_vol = mesh.volume
    bbox_ratio = mesh_vol / bbox_vol if bbox_vol > 0 else 0

    # Check vision consensus
    if vision_result and vision_result['confidence'] > 80:
        shape = vision_result['shape_consensus']

        if shape == 'circle':
            if verbose:
                print(f"  ✅ Vision: CIRCLE → CYLINDER ({vision_result['confidence']:.0f}%)")
            return 'cylinder', {'shape_type': 'cylinder', 'confidence': vision_result['confidence'], 'method': 'vision'}

        elif shape == 'rectangle':
            if verbose:
                print(f"  ✅ Vision: RECTANGLE → BOX ({vision_result['confidence']:.0f}%)")
            return 'box', {'shape_type': 'box', 'confidence': vision_result['confidence'], 'method': 'vision'}

        elif shape == 'multiple':
            if layer_result and layer_result.get('detected_boxes'):
                if verbose:
                    print(f"  ✅ Vision: ASSEMBLY → {len(layer_result['detected_boxes'])} boxes")
                return 'assembly', layer_result

    # Fallback to bbox heuristic
    if verbose:
        print(f"  📐 Heuristic (bbox_ratio={bbox_ratio:.3f})")

    if bbox_ratio >= 0.85:
        if verbose:
            print(f"     → BOX (solid/hollow)")
        return 'box', {'shape_type': 'box', 'confidence': 85, 'method': 'heuristic', 'bbox_ratio': bbox_ratio}

    elif 0.40 <= bbox_ratio <= 0.85:
        if verbose:
            print(f"     → CYLINDER")
        return 'cylinder', {'shape_type': 'cylinder', 'confidence': 80, 'method': 'heuristic', 'bbox_ratio': bbox_ratio}

    elif layer_result and layer_result.get('detected_boxes'):
        n_boxes = len(layer_result['detected_boxes'])
        if verbose:
            print(f"     → ASSEMBLY ({n_boxes} boxes)")
        return 'assembly', layer_result

    else:
        if verbose:
            print(f"     → COMPLEX")
        return 'complex', {'shape_type': 'complex', 'confidence': 50, 'method': 'heuristic', 'bbox_ratio': bbox_ratio}


def reconstruct(
    mesh: trimesh.Trimesh,
    shape_type: str,
    classification: Dict,
    verbose: bool = True
) -> Optional[trimesh.Trimesh]:
    """Reconstruct clean primitive from mesh."""
    if verbose:
        print(f"\n🔧 Reconstructing {shape_type.upper()}...")

    try:
        if shape_type == 'cylinder':
            prim = CylinderPrimitive()
            prim.fit(mesh)
            result = prim.generate_mesh()
            if verbose:
                print(f"  ✅ r={prim.radius:.2f}mm, L={prim.length:.2f}mm")
            return result

        elif shape_type == 'box':
            prim = BoxPrimitive()
            prim.fit(mesh)
            result = prim.generate_mesh()
            if verbose:
                ext = prim.extents if hasattr(prim, 'extents') else result.bounding_box.extents
                print(f"  ✅ {ext[0]:.1f}×{ext[1]:.1f}×{ext[2]:.1f}mm")
            return result

        elif shape_type == 'assembly':
            boxes = classification.get('detected_boxes', [])
            if not boxes:
                return mesh

            meshes = []
            for i, box in enumerate(boxes):
                center = np.array(box.get('center', [0, 0, 0]))
                dims = box.get('dimensions', [10, 10, 10])
                box_mesh = trimesh.creation.box(extents=dims)
                box_mesh.apply_translation(center - box_mesh.centroid)
                meshes.append(box_mesh)

            if verbose:
                print(f"  ✅ {len(meshes)} boxes combined")
            return trimesh.util.concatenate(meshes)

        else:  # complex
            try:
                import fast_simplification
                simplified = fast_simplification.simplify(
                    mesh.vertices, mesh.faces, target_reduction=0.90
                )
                if isinstance(simplified, tuple):
                    verts, faces = simplified
                    result = trimesh.Trimesh(vertices=verts, faces=faces)
                else:
                    result = simplified
                if verbose:
                    print(f"  ✅ Simplified: {len(mesh.faces)} → {len(result.faces)} faces")
                return result
            except:
                if verbose:
                    print(f"  ⚠️  Using original mesh")
                return mesh

    except Exception as e:
        if verbose:
            print(f"  ❌ Failed: {e}")
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
    Convert messy mesh to clean parametric STL.

    Main conversion function that orchestrates:
    1. Mesh loading
    2. Vision-based layer analysis (optional)
    3. Layer-slicing analysis (optional)
    4. Shape classification
    5. Primitive reconstruction
    6. Output generation

    Args:
        input_path: Input STL file path
        output_path: Output STL path (default: <input>_optimized.stl)
        use_vision: Enable GPT-4o vision analysis
        n_vision_layers: Number of layers for vision sampling
        use_layer_slicing: Enable layer-slicing for assemblies
        layer_height: Layer height in mm
        verbose: Print progress

    Returns:
        Result dictionary with success status, paths, metrics
    """
    if verbose:
        print("\n" + "="*80)
        print("🔷 MeshConverter v2.0 - Mesh-to-CAD Conversion")
        print("="*80)
        print(f"Input: {input_path}")

    # Validate input
    if not os.path.exists(input_path):
        return {'success': False, 'error': f'File not found: {input_path}'}

    # Determine output
    if output_path is None:
        stem = Path(input_path).stem
        output_path = str(Path(input_path).parent / f"{stem}_optimized.stl")

    if verbose:
        print(f"Output: {output_path}")
        print("="*80)

    # Load mesh
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

    # Vision analysis
    vision_result = None
    if use_vision:
        if verbose:
            print(f"\n🔍 Vision analysis ({n_vision_layers} layers)...")
        vision_result = analyze_with_vision(mesh, n_vision_layers, verbose)

    # Layer-slicing
    layer_result = None
    if use_layer_slicing:
        try:
            if verbose:
                print(f"\n📋 Layer-slicing (height={layer_height}mm)...")
            layer_result = analyze_mesh_layers(mesh, layer_height, verbose)
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Failed: {e}")

    # Classify
    shape_type, classification = classify_mesh(mesh, vision_result, layer_result, verbose)

    # Reconstruct
    reconstructed = reconstruct(mesh, shape_type, classification, verbose)

    if reconstructed is None:
        return {'success': False, 'error': 'Reconstruction failed'}

    # Quality metrics
    vol_error = abs(reconstructed.volume - mesh.volume) / mesh.volume if mesh.volume > 0 else 1.0
    quality_score = int(100 * (1 - vol_error))

    metrics = {
        'volume_error_pct': float(vol_error * 100),
        'quality_score': quality_score,
        'face_reduction_pct': float((orig_stats['faces'] - len(reconstructed.faces)) / orig_stats['faces'] * 100)
    }

    if verbose:
        print(f"\n📊 Quality:")
        print(f"  Volume error: {metrics['volume_error_pct']:.2f}%")
        print(f"  Quality score: {metrics['quality_score']}/100")
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
        'shape': shape_type,
        'confidence': float(classification.get('confidence', 0)),
        'original': orig_stats,
        'output': out_stats,
        'metrics': metrics
    }

    metadata_path = str(Path(output_path).with_suffix('.json'))
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    except:
        pass

    # Final summary
    if verbose:
        print("\n" + "="*80)
        print("✅ CONVERSION COMPLETE")
        print("="*80)
        print(f"Shape: {shape_type.upper()}")
        print(f"Confidence: {classification.get('confidence', 0):.0f}%")
        print(f"Quality: {quality_score}/100")
        print("="*80)

    return {
        'success': True,
        'input': input_path,
        'output': output_path,
        'metadata': metadata_path,
        'shape': shape_type,
        'confidence': float(classification.get('confidence', 0)),
        'metrics': metrics
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert 3D mesh to clean parametric STL primitive"
    )
    parser.add_argument('input', help='Input STL file')
    parser.add_argument('-o', '--output', help='Output STL (default: <input>_optimized.stl)')
    parser.add_argument('--no-vision', action='store_true', help='Disable vision analysis')
    parser.add_argument('--vision-layers', type=int, default=5, help='Vision sample layers (default: 5)')
    parser.add_argument('--no-layer-slicing', action='store_true', help='Disable layer-slicing')
    parser.add_argument('--layer-height', type=float, default=2.0, help='Layer height mm (default: 2.0)')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')

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
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    sys.exit(0)
