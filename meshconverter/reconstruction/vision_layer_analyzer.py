#!/usr/bin/env python3
"""
Vision-enhanced layer analysis for outlier detection and validation.

Integrates GPT-4 Vision with layer-by-layer mesh reconstruction to:
- Detect and remove scan noise/outliers
- Validate layer shapes and geometry
- Provide confidence scores for reconstruction
"""

import trimesh
import numpy as np
import base64
import io
import os
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ImageDraw
import json
import re

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class VisionLayerAnalyzer:
    """Analyze 2D layer cross-sections using GPT-4 Vision for outlier detection."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize vision layer analyzer.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)

        Raises:
            ImportError: If openai package not installed
            ValueError: If API key not provided
        """
        if not HAS_OPENAI:
            raise ImportError("openai package required: pip install openai")

        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required (set OPENAI_API_KEY or pass api_key)")

        self.client = OpenAI(api_key=self.api_key)

    def render_2d_section_to_image(
        self,
        section: trimesh.Path2D,
        resolution: int = 512,
        padding: float = 0.1
    ) -> bytes:
        """
        Render 2D cross-section to PNG image.

        Args:
            section: 2D path from mesh.section()
            resolution: Image size in pixels
            padding: Padding around shape (fraction of size)

        Returns:
            PNG image as bytes
        """
        # Get 2D vertices
        if hasattr(section, 'vertices'):
            vertices_2d = section.vertices[:, :2]
        else:
            # If it's a Path3D, project to 2D
            vertices_2d = np.array(section)[:, :2]

        if len(vertices_2d) == 0:
            raise ValueError("No vertices in section")

        # Calculate bounds with padding
        min_coords = vertices_2d.min(axis=0)
        max_coords = vertices_2d.max(axis=0)
        range_coords = max_coords - min_coords

        # Add padding
        pad = range_coords * padding
        min_coords -= pad
        max_coords += pad
        range_coords = max_coords - min_coords

        # Create image
        img = Image.new('RGB', (resolution, resolution), color='white')
        draw = ImageDraw.Draw(img)

        # Normalize vertices to image coordinates
        def to_image_coords(point):
            # Flip Y axis (image coords have Y down, mesh has Y up)
            normalized = (point - min_coords) / range_coords
            x = int(normalized[0] * (resolution - 1))
            y = int((1 - normalized[1]) * (resolution - 1))  # Flip Y
            return (x, y)

        # Draw vertices as small circles
        for vertex in vertices_2d:
            img_coord = to_image_coords(vertex)
            radius = 2
            draw.ellipse(
                [img_coord[0] - radius, img_coord[1] - radius,
                 img_coord[0] + radius, img_coord[1] + radius],
                fill='blue',
                outline='darkblue'
            )

        # Try to draw edges if available
        if hasattr(section, 'entities') and len(section.entities) > 0:
            for entity in section.entities:
                if hasattr(entity, 'points'):
                    points = [to_image_coords(vertices_2d[i]) for i in entity.points]
                    if len(points) >= 2:
                        draw.line(points, fill='black', width=1)

        # Convert to PNG bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()

    def analyze_layer_for_outliers(
        self,
        section: trimesh.Path2D,
        z_height: float,
        layer_id: int,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a single 2D layer cross-section for outliers using GPT-4 Vision.

        Args:
            section: 2D cross-section from mesh slicing
            z_height: Z coordinate of this layer
            layer_id: Layer index number
            verbose: Print progress messages

        Returns:
            {
                'has_outliers': bool,
                'outlier_percentage': float (0-100),
                'clean_regions': List[Dict],  # Bounding boxes of clean regions
                'shape_detected': str,  # 'rectangle', 'circle', 'ellipse', etc.
                'confidence': int (0-100),
                'reasoning': str
            }
        """
        if verbose:
            print(f"  🔍 Analyzing layer {layer_id} at Z={z_height:.2f}mm with GPT-4 Vision...")

        # Render layer to image
        try:
            img_bytes = self.render_2d_section_to_image(section)
        except Exception as e:
            if verbose:
                print(f"    ⚠️  Failed to render layer: {e}")
            return {
                'has_outliers': False,
                'outlier_percentage': 0.0,
                'clean_regions': [],
                'shape_detected': 'unknown',
                'confidence': 0,
                'reasoning': f'Render error: {str(e)}'
            }

        # Encode to base64
        b64_img = base64.b64encode(img_bytes).decode('utf-8')

        # Prepare prompt for outlier detection
        prompt = f"""Analyze this 2D cross-section from a 3D mesh scan at height Z={z_height:.2f}mm (layer {layer_id}).

**TASK:** Identify scan noise, outliers, and the main geometric shape.

**Answer in JSON format:**
{{
  "has_outliers": true/false,
  "outlier_percentage": 0-100,
  "shape_detected": "rectangle" | "circle" | "ellipse" | "irregular" | "multiple",
  "shape_count": <number of distinct shapes, e.g., 1, 2, 3>,
  "confidence": 0-100,
  "reasoning": "<brief explanation of what you see>",
  "main_region_bounds": {{"x_min": 0, "y_min": 0, "x_max": 512, "y_max": 512}}
}}

**Guidelines:**
- Outliers: Scattered points far from the main shape, isolated clusters, noise
- Main shape: The primary geometric pattern (usually a rectangle or circle for simple objects)
- Confidence: How certain you are about the shape classification
- Shape count: Number of separate objects in this layer (e.g., 2 for an assembly)

**Important:**
- Blue dots are vertices from the 3D scan
- Look for the PRIMARY geometric pattern
- Outliers are typically <5% of points, scattered randomly
- For assemblies, you may see 2+ distinct shapes

Return ONLY valid JSON, no other text."""

        # Call GPT-4 Vision
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Updated from deprecated gpt-4-vision-preview
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_img}",
                                "detail": "high"
                            }
                        }
                    ]
                }],
                max_tokens=300,
                temperature=0.0
            )

            response_text = response.choices[0].message.content

            if verbose:
                print(f"    GPT-4 Response: {response_text[:100]}...")

            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))

                    if verbose:
                        outlier_status = "YES" if result.get('has_outliers', False) else "NO"
                        outlier_pct = result.get('outlier_percentage', 0)
                        shape = result.get('shape_detected', 'unknown')
                        conf = result.get('confidence', 0)
                        print(f"    ✅ Shape: {shape}, Outliers: {outlier_status} ({outlier_pct:.1f}%), Confidence: {conf}%")

                    return result

                except json.JSONDecodeError as e:
                    if verbose:
                        print(f"    ⚠️  JSON parse error: {e}")

            # Fallback parsing
            return {
                'has_outliers': 'outlier' in response_text.lower() or 'noise' in response_text.lower(),
                'outlier_percentage': 5.0 if 'outlier' in response_text.lower() else 0.0,
                'clean_regions': [],
                'shape_detected': 'unknown',
                'confidence': 50,
                'reasoning': response_text
            }

        except Exception as e:
            if verbose:
                print(f"    ❌ Vision API error: {e}")
            return {
                'has_outliers': False,
                'outlier_percentage': 0.0,
                'clean_regions': [],
                'shape_detected': 'unknown',
                'confidence': 0,
                'reasoning': f'API error: {str(e)}'
            }

    def analyze_multi_view_validation(
        self,
        original_mesh: trimesh.Trimesh,
        reconstructed_mesh: trimesh.Trimesh,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Compare original vs reconstructed mesh using multi-view rendering.

        Args:
            original_mesh: Original scanned mesh
            reconstructed_mesh: Reconstructed parametric mesh
            verbose: Print progress

        Returns:
            {
                'similarity_score': 0-100,
                'differences_noted': List[str],
                'reconstruction_quality': 'excellent'|'good'|'fair'|'poor',
                'reasoning': str
            }
        """
        if verbose:
            print("\n🔍 Validating reconstruction with GPT-4 Vision...")

        # Render both meshes from same viewpoints
        angles = [(0, 0), (90, 0), (0, 90)]  # Front, side, top

        original_images = []
        reconstructed_images = []

        for azimuth, elevation in angles:
            # Render original
            scene_orig = original_mesh.scene()
            az_rad = np.radians(azimuth)
            el_rad = np.radians(elevation)
            distance = original_mesh.bounding_sphere.primitive.radius * 3.0
            x = distance * np.cos(el_rad) * np.cos(az_rad)
            y = distance * np.cos(el_rad) * np.sin(az_rad)
            z = distance * np.sin(el_rad)
            camera_pos = np.array([x, y, z])
            scene_orig.camera_transform = scene_orig.camera.look_at(
                points=[original_mesh.centroid],
                center=camera_pos
            )
            orig_bytes = scene_orig.save_image(resolution=[512, 512])
            original_images.append(base64.b64encode(orig_bytes).decode('utf-8'))

            # Render reconstructed
            scene_recon = reconstructed_mesh.scene()
            scene_recon.camera_transform = scene_recon.camera.look_at(
                points=[reconstructed_mesh.centroid],
                center=camera_pos
            )
            recon_bytes = scene_recon.save_image(resolution=[512, 512])
            reconstructed_images.append(base64.b64encode(recon_bytes).decode('utf-8'))

        # Prepare comparison prompt
        prompt = """Compare these two 3D objects shown from 3 angles (front, side, top).

LEFT COLUMN: Original scanned mesh (noisy, many triangles)
RIGHT COLUMN: Reconstructed parametric CAD model (clean, simplified)

**TASK:** Assess how well the reconstruction matches the original.

**Answer in JSON format:**
{
  "similarity_score": 0-100,
  "reconstruction_quality": "excellent" | "good" | "fair" | "poor",
  "differences_noted": ["difference 1", "difference 2"],
  "reasoning": "<explanation>"
}

**Scoring Guide:**
- 90-100: Excellent - nearly identical geometry
- 80-89: Good - minor differences, captures main shape well
- 60-79: Fair - noticeable differences but recognizable
- 0-59: Poor - significant geometry mismatch

Return ONLY valid JSON."""

        # Build content with paired images
        content = [{"type": "text", "text": prompt}]
        for i in range(len(angles)):
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{original_images[i]}", "detail": "high"}
            })
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{reconstructed_images[i]}", "detail": "high"}
            })

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Updated from deprecated gpt-4-vision-preview
                messages=[{"role": "user", "content": content}],
                max_tokens=400,
                temperature=0.0
            )

            response_text = response.choices[0].message.content

            if verbose:
                print(f"  GPT-4 Validation Response:")
                print(f"  {response_text}")

            # Parse JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                if verbose:
                    quality = result.get('reconstruction_quality', 'unknown')
                    score = result.get('similarity_score', 0)
                    print(f"\n  ✅ Reconstruction Quality: {quality.upper()} (Score: {score}/100)")
                return result

            # Fallback
            return {
                'similarity_score': 50,
                'differences_noted': [],
                'reconstruction_quality': 'fair',
                'reasoning': response_text
            }

        except Exception as e:
            if verbose:
                print(f"  ❌ Validation failed: {e}")
            return {
                'similarity_score': 0,
                'differences_noted': [],
                'reconstruction_quality': 'unknown',
                'reasoning': f'Error: {str(e)}'
            }


def analyze_layer_with_vision(
    section: trimesh.Path2D,
    z_height: float,
    layer_id: int,
    api_key: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to analyze a single layer with vision.

    Args:
        section: 2D cross-section
        z_height: Z coordinate
        layer_id: Layer number
        api_key: OpenAI API key (optional)
        verbose: Print progress

    Returns:
        Analysis result dictionary
    """
    try:
        analyzer = VisionLayerAnalyzer(api_key=api_key)
        return analyzer.analyze_layer_for_outliers(section, z_height, layer_id, verbose=verbose)
    except Exception as e:
        if verbose:
            print(f"❌ Vision analysis failed: {e}")
        return {
            'has_outliers': False,
            'outlier_percentage': 0.0,
            'clean_regions': [],
            'shape_detected': 'unknown',
            'confidence': 0,
            'reasoning': f'Error: {str(e)}'
        }
