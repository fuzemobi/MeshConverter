#!/usr/bin/env python3
"""
Main CLI script for mesh-to-primitives conversion.

Orchestrates the complete pipeline: load → detect → fit → validate → export
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any
import trimesh
import numpy as np

from core.mesh_loader import MeshLoader
from core.normalizer import MeshNormalizer
from detection.simple_detector import SimpleDetector
from detection.ai_detector import AIDetector
from validation.validator import MeshValidator
from primitives.box import BoxPrimitive
from primitives.cylinder import CylinderPrimitive


def convert_mesh(
    input_file: str,
    output_dir: str = None,
    use_ai: bool = True,
    normalize: bool = True
) -> Dict[str, Any]:
    """
    Convert mesh to primitive shapes.

    Args:
        input_file: Path to input STL file
        output_dir: Output directory (default: input_file_output/)
        use_ai: Whether to use AI detection
        normalize: Whether to normalize mesh

    Returns:
        Results dictionary
    """
    # Setup
    input_path = Path(input_file)
    if not output_dir:
        output_dir = str(input_path.parent / f"{input_path.stem}_output")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"🔍 Loading mesh: {input_file}")
    print(f"{'='*70}\n")

    # Load
    try:
        result = MeshLoader.load(input_file, repair=True)
        mesh = result['mesh']
    except Exception as e:
        print(f"❌ Error loading mesh: {e}")
        return None

    # Print stats
    validation = MeshLoader.validate_mesh(mesh)
    print(f"Original mesh stats:")
    print(f"  Vertices: {validation['vertices_count']:,}")
    print(f"  Faces: {validation['faces_count']:,}")
    print(f"  Volume: {validation['volume']:,.2f} mm³")
    print(f"  Surface Area: {validation['surface_area']:,.2f} mm²")
    print(f"  Watertight: {validation['is_watertight']}")
    print()

    # Detect shape
    print(f"🤖 Detecting shape...")
    if use_ai:
        detector = AIDetector()
    else:
        detector = SimpleDetector()

    detection_result = detector.detect(mesh) if use_ai else SimpleDetector.detect(mesh)
    shape_type = detection_result['shape_type']
    confidence = detection_result['confidence']

    print(f"✅ Shape Classification:")
    print(f"  Type: {shape_type.upper()}")
    print(f"  Confidence: {confidence}%")
    print(f"  Reason: {detection_result['reason']}")
    print()

    # Fit appropriate primitive
    print(f"🔧 Fitting primitive...")
    primitive = None

    if shape_type == 'cylinder':
        primitive = CylinderPrimitive()
        primitive.fit(mesh)
    elif shape_type in ['box', 'hollow_box']:
        primitive = BoxPrimitive()
        primitive.fit(mesh)
    else:
        print(f"⚠️  Shape type '{shape_type}' not yet supported")
        return None

    print()

    # Validate
    print(f"✅ Validating fit...")
    generated = primitive.generate_mesh()
    validation_result = MeshValidator.validate_fit(mesh, generated)

    quality = validation_result['quality_score']
    quality_level = validation_result['quality_level']

    print(f"  Quality Score: {quality:.1f}/100 ({quality_level})")
    print(f"  Volume Error: {validation_result['volume_error_percent']:.1f}%")
    print(f"  Hausdorff Distance: {validation_result['hausdorff_max_mm']:.2f} mm")
    print()

    # Export results
    print(f"💾 Exporting results...")

    # STL
    stl_path = output_path / f"{input_path.stem}_output.stl"
    generated.export(str(stl_path))
    print(f"  STL: {stl_path}")

    # CadQuery script
    script_path = output_path / f"{input_path.stem}_cadquery.py"
    script = primitive.generate_cadquery_script()
    with open(script_path, 'w') as f:
        f.write(script)
    print(f"  Script: {script_path}")

    # Metadata
    metadata = {
        'input_file': str(input_path),
        'detection': {
            'shape_type': shape_type,
            'confidence': confidence,
            'method': detection_result.get('method', 'heuristic')
        },
        'primitive': primitive.to_dict(),
        'validation': validation_result,
        'output_files': {
            'stl': str(stl_path),
            'script': str(script_path)
        }
    }

    metadata_path = output_path / f"{input_path.stem}_metadata.json"
    with open(metadata_path, 'w') as f:
        # Custom JSON encoder to handle numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.bool_, np.integer, np.floating)):
                    return obj.item()
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        json.dump(metadata, f, indent=2, cls=NumpyEncoder)
    print(f"  Metadata: {metadata_path}")

    print()
    print(f"{'='*70}")
    print(f"✅ Conversion complete!")
    print(f"{'='*70}\n")

    return metadata


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert 3D scans to clean CAD-ready primitives'
    )
    parser.add_argument('input_file', help='Input STL file')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('--no-ai', action='store_true', help='Disable AI detection')
    parser.add_argument('--no-normalize', action='store_true', help='Disable mesh normalization')

    args = parser.parse_args()

    try:
        result = convert_mesh(
            args.input_file,
            output_dir=args.output,
            use_ai=not args.no_ai,
            normalize=not args.no_normalize
        )

        if result:
            print(f"Results saved to: {result['output_files']}")
            return 0
        else:
            return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
