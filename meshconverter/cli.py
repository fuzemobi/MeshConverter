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
import numpy as np
import yaml
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import classification methods
from meshconverter.classification import (
    classify_mesh_with_voxel,
    classify_mesh_with_vision
)
from meshconverter.reconstruction.layer_analyzer import analyze_mesh_layers

# Import core modules
from core.mesh_loader import MeshLoader
from detection.simple_detector import SimpleDetector
from primitives.cylinder import CylinderPrimitive
from primitives.box import BoxPrimitive


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
        'reasoning': reasoning,
        'bbox_ratio': bbox_ratio,
        'method': 'heuristic'
    }


def classify_layer_slicing(mesh: trimesh.Trimesh, layer_height: float = 2.0) -> Dict[str, Any]:
    """
    Classify using layer-slicing reconstruction method.

    Args:
        mesh: Input trimesh
        layer_height: Height of each layer slice (mm)

    Returns:
        Classification result
    """
    print("\n📋 Classifying with layer-slicing...")

    result = analyze_mesh_layers(mesh, layer_height=layer_height, verbose=True)

    # Convert to standard classification format
    n_boxes = len(result.get('detected_boxes', []))

    if n_boxes == 0:
        result['shape_type'] = 'unknown'
        result['confidence'] = 0
    elif n_boxes == 1:
        result['shape_type'] = 'box'
        result['confidence'] = 90
    else:
        result['shape_type'] = 'assembly'
        result['confidence'] = 85

    return result

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
    erosion_iterations: int = 0,
    layer_height: float = 2.0
) -> Dict[str, Any]:
    """
    Classify mesh using specified method.

    Args:
        mesh: Input trimesh
        method: Classification method ('voxel', 'gpt4-vision', 'heuristic', 'layer-slicing', 'all')
        config: Configuration dictionary
        voxel_size: Voxel size for voxel method
        erosion_iterations: Erosion iterations for voxel method
        layer_height: Layer height for layer-slicing method

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

    elif method == 'layer-slicing':
        return classify_layer_slicing(mesh, layer_height=layer_height)

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

        # Layer-slicing
        try:
            layer_result = classify_layer_slicing(mesh, layer_height=layer_height)
            results.append(layer_result)
        except Exception as e:
            print(f"⚠️  Layer-slicing failed: {e}")

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


def generate_step_file(
    mesh: trimesh.Trimesh,
    classification: Dict[str, Any],
    output_dir: Path
) -> Optional[str]:
    """
    Generate STEP file by running the CadQuery script.

    Args:
        mesh: Original mesh
        classification: Classification result
        output_dir: Output directory

    Returns:
        Path to saved STEP or None if generation failed
    """
    import subprocess
    
    try:
        # First, generate the script
        script_path = generate_cadquery_script(mesh, classification, output_dir)
        
        if not script_path:
            return None
        
        # Run the script to generate STEP
        result = subprocess.run(
            ['python', script_path],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Check if STEP file was created
            step_file = output_dir / f"{output_dir.name}_parametric.step"
            if step_file.exists():
                return str(step_file)
        else:
            # Script failed, but that's okay
            pass
        
        return None
    
    except subprocess.TimeoutExpired:
        print("⚠️  STEP generation timed out")
        return None
    except Exception as e:
        # Silently fail - STEP is optional
        return None


def generate_parametric_stl(
    mesh: trimesh.Trimesh,
    classification: Dict[str, Any],
    output_dir: Path
) -> Optional[str]:
    """
    Generate simplified parametric STL file.

    Args:
        mesh: Original mesh
        classification: Classification result
        output_dir: Output directory

    Returns:
        Path to saved STL or None if generation failed
    """
    shape_type = classification.get('shape_type', 'complex')
    
    try:
        if shape_type == 'cylinder':
            primitive = CylinderPrimitive()
            primitive.fit(mesh)
            generated = primitive.generate_mesh()
        elif shape_type == 'box':
            primitive = BoxPrimitive()
            primitive.fit(mesh)
            generated = primitive.generate_mesh()
        elif shape_type == 'assembly':
            # Reconstruct clean boxes from detected_boxes list (layer-slicing output)
            detected_boxes = classification.get('detected_boxes', [])
            if detected_boxes:
                meshes = []
                for box_idx, box_data in enumerate(detected_boxes):
                    try:
                        # Extract box parameters
                        center = np.array(box_data.get('center', [0, 0, 0]))
                        dims = box_data.get('dimensions', [10, 10, 10])
                        
                        # Create clean box directly
                        box_mesh = trimesh.creation.box(extents=dims)
                        # Translate to correct center
                        box_mesh.apply_translation(center - box_mesh.centroid)
                        meshes.append(box_mesh)
                    except Exception as e:
                        print(f"  ⚠️  Could not generate box {box_idx}: {e}")
                
                if meshes:
                    # Combine all boxes into single mesh
                    generated = trimesh.util.concatenate(meshes)
                else:
                    print("⚠️  No valid boxes found, using simplified original")
                    generated = mesh
            else:
                print("⚠️  No box data in assembly, using simplified original")
                generated = mesh
        else:
            # For other shapes, use fast-simplification if available
            try:
                import fast_simplification
                target_reduction = 0.9  # Reduce to 10% of original
                simplified = fast_simplification.simplify(
                    mesh.vertices,
                    mesh.faces,
                    target_reduction=target_reduction
                )
                # fast_simplification returns (vertices, faces) tuple
                if isinstance(simplified, tuple):
                    simplified_verts, simplified_faces = simplified
                    generated = trimesh.Trimesh(vertices=simplified_verts, faces=simplified_faces)
                else:
                    generated = simplified
            except ImportError:
                # Fallback: just copy the original mesh
                print("⚠️  fast-simplification not available, using original mesh")
                generated = mesh
        
        # Save simplified mesh
        output_path = output_dir / f"{output_dir.name}_parametric.stl"
        generated.export(str(output_path))
        return str(output_path)
    
    except Exception as e:
        print(f"⚠️  Could not generate parametric STL: {e}")
        return None


def generate_metadata_json(
    mesh: trimesh.Trimesh,
    classification: Dict[str, Any],
    output_dir: Path
) -> Optional[str]:
    """
    Generate metadata JSON file with classification results.

    Args:
        mesh: Original mesh
        classification: Classification result
        output_dir: Output directory

    Returns:
        Path to saved JSON or None if generation failed
    """
    try:
        # Clean classification dict to remove non-serializable objects
        clean_classification = {}
        for key, value in classification.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                clean_classification[key] = value
            elif isinstance(value, (list, dict)):
                # Try to convert to JSON-serializable format
                try:
                    json.dumps(value)
                    clean_classification[key] = value
                except (TypeError, ValueError):
                    clean_classification[key] = str(value)
            else:
                # Convert other types to string
                clean_classification[key] = str(value)
        
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "input_mesh": {
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
                "volume_mm3": float(mesh.volume),
                "bounding_box_mm": [float(x) for x in mesh.bounding_box.extents]
            },
            "classification": clean_classification,
            "output_files": {}
        }
        
        output_path = output_dir / f"{output_dir.name}_metadata.json"
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return str(output_path)
    
    except Exception as e:
        print(f"⚠️  Could not generate metadata JSON: {e}")
        return None


def generate_cadquery_script(
    mesh: trimesh.Trimesh,
    classification: Dict[str, Any],
    output_dir: Path
) -> Optional[str]:
    """
    Generate parametric CadQuery Python script.

    Args:
        mesh: Original mesh
        classification: Classification result
        output_dir: Output directory

    Returns:
        Path to saved Python script or None if generation failed
    """
    shape_type = classification.get('shape_type', 'complex')
    
    try:
        if shape_type == 'cylinder':
            primitive = CylinderPrimitive()
            primitive.fit(mesh)
            
            script = f'''#!/usr/bin/env python3
"""
Auto-generated parametric cylinder from MeshConverter.

Generated: {datetime.now().isoformat()}
Original mesh: {mesh.vertices.shape[0]} vertices, {mesh.faces.shape[0]} faces
Detected shape: CYLINDER
"""

import cadquery as cq

# Detected parameters (edit these to customize)
RADIUS = {primitive.radius:.2f}  # mm
LENGTH = {primitive.length:.2f}  # mm

# Optional: Rotation (Euler angles in degrees)
ROTATION_X = 0.0
ROTATION_Y = 0.0
ROTATION_Z = 0.0

# Optional: Translation
OFFSET_X = {primitive.center[0]:.2f}
OFFSET_Y = {primitive.center[1]:.2f}
OFFSET_Z = {primitive.center[2]:.2f}

# Create cylinder
result = (cq.Workplane("XY")
    .circle(RADIUS)
    .extrude(LENGTH)
)

# Apply transformations if needed
if any([ROTATION_X, ROTATION_Y, ROTATION_Z]):
    result = result.rotateAboutCenter((1, 0, 0), ROTATION_X)
    result = result.rotateAboutCenter((0, 1, 0), ROTATION_Y)
    result = result.rotateAboutCenter((0, 0, 1), ROTATION_Z)

# Export to STEP for CAD software
result.exportStep("{output_dir.name}_parametric.step")
print(f"✅ Generated: {{RADIUS}} mm radius × {{LENGTH}} mm length cylinder")
'''
        
        elif shape_type == 'box':
            primitive = BoxPrimitive()
            primitive.fit(mesh)
            
            extents = primitive.extents if hasattr(primitive, 'extents') else [50, 50, 50]
            hollow = primitive.hollow if hasattr(primitive, 'hollow') else False
            wall_thickness = primitive.wall_thickness if hasattr(primitive, 'wall_thickness') else 2.0
            
            script = f'''#!/usr/bin/env python3
"""
Auto-generated parametric box from MeshConverter.

Generated: {datetime.now().isoformat()}
Original mesh: {mesh.vertices.shape[0]} vertices, {mesh.faces.shape[0]} faces
Detected shape: BOX {'(HOLLOW)' if hollow else '(SOLID)'}
"""

import cadquery as cq

# Detected parameters (edit these to customize)
LENGTH = {extents[0]:.2f}  # mm
WIDTH = {extents[1]:.2f}   # mm
HEIGHT = {extents[2]:.2f}  # mm
IS_HOLLOW = {hollow}
WALL_THICKNESS = {wall_thickness:.2f}  # mm (only if hollow)

# Create box
result = (cq.Workplane("XY")
    .box(LENGTH, WIDTH, HEIGHT)
)

# Hollow out if needed
if IS_HOLLOW:
    result = result.faces(">Z").shell(-WALL_THICKNESS)

# Export to STEP for CAD software
result.exportStep("{output_dir.name}_parametric.step")
print(f"✅ Generated: {{LENGTH}} × {{WIDTH}} × {{HEIGHT}} mm box")
'''
        
        elif shape_type == 'assembly':
            # Generate script with multiple boxes
            detected_boxes = classification.get('detected_boxes', [])
            box_definitions = "\n".join([
                f"# Box {i}: center={[round(b['center'][j], 2) for j in range(3)]}, dims={[round(b['dimensions'][j], 2) for j in range(3)]}"
                for i, b in enumerate(detected_boxes)
            ])
            
            # Build BOXES list with proper formatting and commas
            boxes_list_items = []
            for i, b in enumerate(detected_boxes):
                box_str = f"    {{'center': ({b['center'][0]:.2f}, {b['center'][1]:.2f}, {b['center'][2]:.2f}), 'dimensions': ({b['dimensions'][0]:.2f}, {b['dimensions'][1]:.2f}, {b['dimensions'][2]:.2f})}}"
                boxes_list_items.append(box_str)
            boxes_list_str = ",\n".join(boxes_list_items)
            
            script = f'''#!/usr/bin/env python3
"""
Auto-generated parametric assembly from MeshConverter.

Generated: {datetime.now().isoformat()}
Original mesh: {mesh.vertices.shape[0]} vertices, {mesh.faces.shape[0]} faces
Detected shape: ASSEMBLY ({len(detected_boxes)} boxes)

Detected boxes:
{box_definitions}
"""

import cadquery as cq

# Individual box definitions (edit to customize)
BOXES = [
{boxes_list_str}
]

# Create assembly
result = cq.Workplane("XY")
for i, box in enumerate(BOXES):
    center = box['center']
    dims = box['dimensions']
    # Create individual box at its center location
    box_wp = (cq.Workplane("XY")
        .box(dims[0], dims[1], dims[2])
    )
    result = result.union(box_wp.translate(center))

# Export to STEP for CAD software
result.exportStep("{output_dir.name}_parametric.step")
print(f"✅ Generated: Assembly with {{len(BOXES)}} boxes")
'''
        
        else:
            # Generic complex shape template
            script = f'''#!/usr/bin/env python3
"""
Auto-generated parametric model from MeshConverter.

Generated: {datetime.now().isoformat()}
Original mesh: {mesh.vertices.shape[0]} vertices, {mesh.faces.shape[0]} faces
Detected shape: {shape_type.upper()}

NOTE: This is a template. Complex shapes require manual refinement.
      Edit dimensions below to match your design.
"""

import cadquery as cq
import trimesh

# For complex shapes, you may need to:
# 1. Load the simplified STL from {output_dir.name}_parametric.stl
# 2. Further refine in CAD software
# 3. Create a proper parametric model

# Example: Load and export simplified mesh
mesh = trimesh.load("{output_dir.name}_parametric.stl")
print(f"Loaded simplified mesh: {{len(mesh.vertices)}} vertices")
print(f"Note: Complex shapes are best refined manually in FreeCAD or Fusion 360")
'''
        
        output_path = output_dir / f"{output_dir.name}_cadquery.py"
        with open(output_path, 'w') as f:
            f.write(script)
        
        return str(output_path)
    
    except Exception as e:
        print(f"⚠️  Could not generate CadQuery script: {e}")
        return None


def save_outputs(
    mesh: trimesh.Trimesh,
    classification: Dict[str, Any],
    output_dir: Optional[str] = None,
    input_filename: str = "mesh"
) -> Dict[str, Optional[str]]:
    """
    Save all output files (STL, STEP, metadata, CadQuery template).

    Args:
        mesh: Original mesh
        classification: Classification result
        output_dir: Output directory (creates if doesn't exist)
        input_filename: Base name for output files

    Returns:
        Dictionary with paths to generated files
    """
    # Create output directory if needed
    if output_dir is None:
        output_dir = f"./output/{Path(input_filename).stem}"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n💾 Saving outputs to: {output_path}")
    
    # Generate all outputs
    outputs = {}
    
    # Metadata (always first)
    metadata_path = generate_metadata_json(mesh, classification, output_path)
    if metadata_path:
        print(f"  ✅ Metadata: {metadata_path}")
        outputs['metadata'] = metadata_path
    
    # STEP file (production-ready CAD file)
    step_path = generate_step_file(mesh, classification, output_path)
    if step_path:
        print(f"  ✅ CAD Model (STEP): {step_path}")
        outputs['step'] = step_path
    
    # Parametric STL (simplified mesh)
    stl_path = generate_parametric_stl(mesh, classification, output_path)
    if stl_path:
        print(f"  ✅ Simplified Mesh (STL): {stl_path}")
        outputs['stl'] = stl_path
    
    # CadQuery script (template for customization)
    script_path = generate_cadquery_script(mesh, classification, output_path)
    if script_path:
        print(f"  ✅ Script Template (editable): {script_path}")
        outputs['script'] = script_path
    
    return outputs


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
        choices=['voxel', 'gpt4-vision', 'heuristic', 'layer-slicing', 'all'],
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
        '--layer-height',
        type=float,
        default=2.0,
        help='Layer height in mm for layer-slicing classifier (default: 2.0)'
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
            erosion_iterations=args.erosion,
            layer_height=args.layer_height
        )

        # Extract best result if multiple methods were run
        if isinstance(result, dict) and 'best_result' in result:
            best_result = result['best_result']
        else:
            best_result = result

        # Save outputs
        input_basename = Path(args.input).stem
        outputs = save_outputs(
            mesh,
            best_result,
            output_dir=args.output,
            input_filename=args.input
        )

        print("\n" + "=" * 70)
        print("✅ Conversion complete!")
        print("=" * 70)
        print(f"\n📌 Results:")
        print(f"  Shape: {best_result.get('shape_type', 'unknown').upper()}")
        print(f"  Confidence: {best_result.get('confidence', 0)}%")
        print(f"  Method: {best_result.get('method', 'unknown')}")
        
        if outputs:
            print(f"\n📁 Files saved:")
            for file_type, path in outputs.items():
                if path:
                    print(f"  • {file_type}: {path}")

    except Exception as e:
        print(f"\n❌ Error during classification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
