#!/usr/bin/env python3
"""
Phase 3: Multi-View Validation

Uses GPT-4o Vision to compare original vs reconstructed meshes from multiple angles.
Provides visual quality assessment beyond numerical metrics.
"""

import trimesh
import numpy as np
import base64
import io
import os
from typing import Dict, Any, List, Optional
from PIL import Image

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class MultiViewValidator:
    """Validate reconstruction quality using GPT-4o Vision."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize validator with OpenAI API key."""
        if not HAS_OPENAI:
            raise ImportError("openai package required")

        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required")

        self.client = OpenAI(api_key=self.api_key)

    def render_comparison(
        self,
        original: trimesh.Trimesh,
        reconstructed: trimesh.Trimesh,
        views: List[tuple] = None,
        resolution: tuple = (512, 512)
    ) -> List[bytes]:
        """
        Render side-by-side comparison images.

        Args:
            original: Original mesh
            reconstructed: Reconstructed mesh
            views: List of (azimuth, elevation) angles
            resolution: Image resolution

        Returns:
            List of PNG image bytes (side-by-side comparisons)
        """
        if views is None:
            views = [
                (0, 0),      # Front
                (90, 0),     # Right
                (0, 90),     # Top
            ]

        comparison_images = []

        # Set offscreen rendering to avoid window popups
        import os
        os.environ['PYOPENGL_PLATFORM'] = 'osmesa'

        for azimuth, elevation in views:
            # Render original
            try:
                orig_scene = original.scene()
                az_rad = np.radians(azimuth)
                el_rad = np.radians(elevation)
                distance = original.bounding_sphere.primitive.radius * 3.0
                x = distance * np.cos(el_rad) * np.cos(az_rad)
                y = distance * np.cos(el_rad) * np.sin(az_rad)
                z = distance * np.sin(el_rad)
                camera_pos = np.array([x, y, z])

                orig_scene.camera_transform = orig_scene.camera.look_at(
                    points=[original.centroid],
                    center=camera_pos
                )
                orig_bytes = orig_scene.save_image(resolution=resolution, visible=False)

                # Render reconstructed (same camera)
                recon_scene = reconstructed.scene()
                recon_scene.camera_transform = recon_scene.camera.look_at(
                    points=[reconstructed.centroid],
                    center=camera_pos
                )
                recon_bytes = recon_scene.save_image(resolution=resolution, visible=False)
            except Exception as e:
                # Fallback: use matplotlib rendering
                import matplotlib.pyplot as plt
                from mpl_toolkits.mplot3d.art3d import Poly3DCollection

                fig = plt.figure(figsize=(10, 5))

                # Render original
                ax1 = fig.add_subplot(121, projection='3d')
                mesh_collection = Poly3DCollection(original.vertices[original.faces], alpha=0.7)
                mesh_collection.set_facecolor([0.5, 0.5, 1])
                ax1.add_collection3d(mesh_collection)
                ax1.set_xlim(original.bounds[:, 0])
                ax1.set_ylim(original.bounds[:, 1])
                ax1.set_zlim(original.bounds[:, 2])
                ax1.set_title('Original')
                ax1.view_init(elev=elevation, azim=azimuth)

                # Render reconstructed
                ax2 = fig.add_subplot(122, projection='3d')
                mesh_collection2 = Poly3DCollection(reconstructed.vertices[reconstructed.faces], alpha=0.7)
                mesh_collection2.set_facecolor([1, 0.5, 0.5])
                ax2.add_collection3d(mesh_collection2)
                ax2.set_xlim(reconstructed.bounds[:, 0])
                ax2.set_ylim(reconstructed.bounds[:, 1])
                ax2.set_zlim(reconstructed.bounds[:, 2])
                ax2.set_title('Reconstructed')
                ax2.view_init(elev=elevation, azim=azimuth)

                # Save to bytes
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                plt.close(fig)
                buffer.seek(0)
                combined_bytes = buffer.getvalue()
                comparison_images.append(combined_bytes)
                continue

            # Create side-by-side comparison
            orig_img = Image.open(io.BytesIO(orig_bytes))
            recon_img = Image.open(io.BytesIO(recon_bytes))

            # Combine images
            combined = Image.new('RGB', (resolution[0] * 2, resolution[1]))
            combined.paste(orig_img, (0, 0))
            combined.paste(recon_img, (resolution[0], 0))

            # Add labels
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(combined)

            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
            except:
                font = ImageFont.load_default()

            draw.text((10, 10), "Original", fill='white', font=font)
            draw.text((resolution[0] + 10, 10), "Reconstructed", fill='white', font=font)

            # Convert to bytes
            buffer = io.BytesIO()
            combined.save(buffer, format='PNG')
            comparison_images.append(buffer.getvalue())

        return comparison_images

    def validate(
        self,
        original: trimesh.Trimesh,
        reconstructed: trimesh.Trimesh,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Validate reconstruction using GPT-4o Vision.

        Args:
            original: Original mesh
            reconstructed: Reconstructed mesh
            verbose: Print progress

        Returns:
            Validation result with similarity score and assessment
        """
        if verbose:
            print("\n🔍 Multi-View Validation with GPT-4o Vision...")

        # Render comparisons
        comparison_images = self.render_comparison(original, reconstructed)

        if verbose:
            print(f"  Rendered {len(comparison_images)} comparison views")

        # Encode to base64
        encoded_images = []
        for img_bytes in comparison_images:
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            encoded_images.append(b64)

        # Prepare prompt
        prompt = """Compare these 3D object reconstructions from multiple views.

LEFT: Original scanned mesh (noisy, many triangles)
RIGHT: Reconstructed parametric model (clean, simplified)

**TASK:** Assess reconstruction quality across all views.

**Answer in JSON format:**
{
  "similarity_score": 0-100,
  "reconstruction_quality": "excellent" | "good" | "fair" | "poor",
  "shape_match": "perfect" | "good" | "approximate" | "poor",
  "dimension_accuracy": "accurate" | "minor_errors" | "significant_errors",
  "differences_noted": ["difference 1", "difference 2", ...],
  "overall_assessment": "<brief summary>",
  "recommended_action": "use_as_is" | "minor_refinement" | "major_revision" | "manual_modeling"
}

**Scoring Guide:**
- 95-100: Excellent - virtually identical
- 85-94: Good - captures main geometry well
- 70-84: Fair - recognizable but noticeable differences
- 0-69: Poor - significant geometry mismatch

**Focus on:**
- Overall shape accuracy
- Dimensional proportions
- Feature preservation (edges, curves)
- Volume/mass distribution

Return ONLY valid JSON."""

        # Build content with images
        content = [{"type": "text", "text": prompt}]
        for b64_img in encoded_images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64_img}",
                    "detail": "high"
                }
            })

        # Call GPT-4o Vision
        try:
            if verbose:
                print(f"  Sending to GPT-4o Vision API...")
                print(f"  (Cost estimate: ~${0.02 * len(comparison_images):.3f})")

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                max_tokens=500,
                temperature=0.0
            )

            response_text = response.choices[0].message.content

            if verbose:
                print(f"\n  📋 GPT-4o Assessment:")
                print(f"  {'-'*60}")
                print(f"  {response_text}")
                print(f"  {'-'*60}\n")

            # Parse JSON
            import json
            import re

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))

                if verbose:
                    quality = result.get('reconstruction_quality', 'unknown')
                    score = result.get('similarity_score', 0)
                    print(f"  ✅ Quality: {quality.upper()} (Similarity: {score}/100)")

                    if result.get('differences_noted'):
                        print(f"  📝 Noted differences:")
                        for diff in result['differences_noted']:
                            print(f"     • {diff}")

                return result

            # Fallback parsing
            return {
                'similarity_score': 75,
                'reconstruction_quality': 'fair',
                'shape_match': 'approximate',
                'dimension_accuracy': 'minor_errors',
                'differences_noted': [],
                'overall_assessment': response_text,
                'recommended_action': 'minor_refinement'
            }

        except Exception as e:
            if verbose:
                print(f"  ❌ Validation failed: {e}")

            return {
                'similarity_score': 0,
                'reconstruction_quality': 'error',
                'error': str(e)
            }


def validate_reconstruction(
    original: trimesh.Trimesh,
    reconstructed: trimesh.Trimesh,
    api_key: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for multi-view validation.

    Args:
        original: Original mesh
        reconstructed: Reconstructed mesh
        api_key: OpenAI API key (optional)
        verbose: Print progress

    Returns:
        Validation result dictionary
    """
    try:
        validator = MultiViewValidator(api_key=api_key)
        return validator.validate(original, reconstructed, verbose=verbose)
    except Exception as e:
        if verbose:
            print(f"❌ Multi-view validation failed: {e}")
        return {
            'similarity_score': 0,
            'reconstruction_quality': 'unavailable',
            'error': str(e)
        }
