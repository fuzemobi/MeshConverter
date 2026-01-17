#!/usr/bin/env python3
"""
AI-powered mesh classification using GPT-4 Vision.

Uses multi-view rendering to analyze 3D geometry visually.
"""

import trimesh
import numpy as np
import base64
import io
import os
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class GPT4VisionMeshClassifier:
    """Classify 3D meshes using GPT-4 Vision API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize classifier.

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

    def render_mesh_views(
        self,
        mesh: trimesh.Trimesh,
        resolution: Tuple[int, int] = (512, 512),
        n_views: int = 6
    ) -> List[bytes]:
        """
        Render mesh from multiple viewpoints.

        Args:
            mesh: Input trimesh
            resolution: Image resolution (width, height)
            n_views: Number of views (6 = all cardinal directions)

        Returns:
            List of PNG image bytes
        """
        print("  Rendering mesh from multiple angles...")

        images = []

        # Camera angles (azimuth, elevation in degrees)
        angles = [
            (0, 0),      # Front
            (180, 0),    # Back
            (90, 0),     # Right
            (270, 0),    # Left
            (0, 90),     # Top
            (0, -90)     # Bottom
        ][:n_views]

        for i, (azimuth, elevation) in enumerate(angles):
            # Create scene
            scene = mesh.scene()

            # Set camera parameters
            # Convert angles to radians for rotation
            az_rad = np.radians(azimuth)
            el_rad = np.radians(elevation)

            # Camera position (spherical coordinates)
            distance = mesh.bounding_sphere.primitive.radius * 3.0
            x = distance * np.cos(el_rad) * np.cos(az_rad)
            y = distance * np.cos(el_rad) * np.sin(az_rad)
            z = distance * np.sin(el_rad)

            camera_position = np.array([x, y, z])

            # Set camera transform
            scene.camera_transform = scene.camera.look_at(
                points=[mesh.centroid],
                center=camera_position
            )

            # Render to PNG bytes
            try:
                png_bytes = scene.save_image(resolution=resolution, visible=True)
                if png_bytes:
                    images.append(png_bytes)
            except Exception as e:
                print(f"    Warning: Failed to render view {i+1} ({azimuth}°, {elevation}°): {e}")
                continue

        print(f"  ✅ Successfully rendered {len(images)} views")
        return images

    def classify_mesh(
        self,
        mesh: trimesh.Trimesh,
        render_views: bool = True,
        n_views: int = 6,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Classify mesh using GPT-4 Vision.

        Args:
            mesh: Input trimesh
            render_views: If True, render multiple views
            n_views: Number of views to render
            verbose: Print progress messages

        Returns:
            Classification result:
            {
                'shape_type': 'cylinder'|'box'|'sphere'|'cone'|'complex',
                'confidence': 0-100,
                'n_components': int,
                'reasoning': str,
                'dimensions_estimate': str,
                'method': 'gpt4-vision'
            }
        """
        if verbose:
            print("\n🤖 Classifying with GPT-4 Vision...")

        # Render images
        if render_views:
            images = self.render_mesh_views(mesh, n_views=n_views)
        else:
            # Single view
            scene = mesh.scene()
            images = [scene.save_image(resolution=[512, 512])]

        if not images:
            raise RuntimeError("Failed to render any views")

        # Encode images to base64
        encoded_images = []
        for img_bytes in images:
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            encoded_images.append(b64)

        if verbose:
            print(f"  Encoded {len(encoded_images)} images for API")

        # Prepare prompt
        prompt = """Analyze this 3D object from multiple viewpoints.

**TASK:** Identify the geometric primitive(s) that best describe this object.

**Answer in JSON format:**
{
  "shape_type": "cylinder" | "box" | "sphere" | "cone" | "complex",
  "confidence": 0-100,
  "n_components": <number of separate parts>,
  "reasoning": "<brief explanation>",
  "dimensions_estimate": "<rough L x W x H or radius/length>"
}

**Guidelines:**
- cylinder: Elongated circular cross-section (like a battery, tube, can)
- box: Rectangular solid (may be hollow, like a container)
- sphere: Round in all directions
- cone: Tapered from base to apex
- complex: Multiple primitives or irregular shape

**Important:** Look at ALL views carefully. A cylinder looks circular from the ends but rectangular from the sides.

Be precise and analytical. Return ONLY valid JSON, no other text."""

        # Build messages with images
        content = [{"type": "text", "text": prompt}]
        for b64_img in encoded_images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64_img}",
                    "detail": "high"
                }
            })

        # Call GPT-4 Vision
        if verbose:
            print("  Sending to GPT-4 Vision API...")
            print(f"  (Cost estimate: ~${0.01 * len(images):.3f} @ $0.01/image)")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[{"role": "user", "content": content}],
                max_tokens=500,
                temperature=0.0  # Deterministic
            )

            # Parse response
            response_text = response.choices[0].message.content

            if verbose:
                print(f"\n  GPT-4 Vision Response:")
                print(f"  {'-'*60}")
                print(f"  {response_text}")
                print(f"  {'-'*60}\n")

            # Extract JSON from response
            import json
            import re

            # Try to find JSON object in response
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))

                    # Add method tag
                    result['method'] = 'gpt4-vision'

                    if verbose:
                        print(f"  ✅ Classification: {result['shape_type']} ({result['confidence']}%)")
                        print(f"     Reasoning: {result['reasoning']}")

                    return result

                except json.JSONDecodeError as e:
                    if verbose:
                        print(f"  ⚠️  JSON parse error: {e}")

            # Fallback: parse manually from text
            if verbose:
                print("  ⚠️  Could not parse JSON, using text analysis")

            # Simple text parsing as fallback
            shape_type = 'unknown'
            confidence = 50

            text_lower = response_text.lower()
            if 'cylinder' in text_lower:
                shape_type = 'cylinder'
                confidence = 70
            elif 'box' in text_lower or 'rectangular' in text_lower:
                shape_type = 'box'
                confidence = 70
            elif 'sphere' in text_lower or 'round' in text_lower:
                shape_type = 'sphere'
                confidence = 70
            elif 'cone' in text_lower:
                shape_type = 'cone'
                confidence = 70

            return {
                'shape_type': shape_type,
                'confidence': confidence,
                'n_components': 1,
                'reasoning': response_text,
                'dimensions_estimate': 'unknown',
                'method': 'gpt4-vision-fallback'
            }

        except Exception as e:
            if verbose:
                print(f"  ❌ API call failed: {e}")
            raise


def classify_mesh_with_vision(
    mesh: trimesh.Trimesh,
    api_key: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to classify mesh with GPT-4 Vision.

    Args:
        mesh: Input mesh
        api_key: OpenAI API key (optional)
        verbose: Print progress

    Returns:
        Classification result dictionary
    """
    try:
        classifier = GPT4VisionMeshClassifier(api_key=api_key)
        return classifier.classify_mesh(mesh, verbose=verbose)
    except Exception as e:
        if verbose:
            print(f"❌ Vision classification failed: {e}")
        return {
            'shape_type': 'unknown',
            'confidence': 0,
            'n_components': 1,
            'reasoning': f'Error: {str(e)}',
            'dimensions_estimate': 'unknown',
            'method': 'error'
        }
