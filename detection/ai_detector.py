#!/usr/bin/env python3
"""
AI-based shape detector using OpenAI with few-shot learning.

Falls back to heuristic detection if API unavailable.
"""

from typing import Dict, Any, Optional
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from core.bbox_utils import get_mesh_stats
from detection.simple_detector import SimpleDetector
import trimesh


class AIDetector:
    """AI-powered shape detection with fallback."""

    def __init__(self):
        """Initialize AI detector."""
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = None

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"⚠️  OpenAI client initialization failed: {e}")

    def detect(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        Detect shape using AI or fallback to heuristic.

        Args:
            mesh: Input mesh

        Returns:
            Detection result dict
        """
        # Try AI detection first
        if self.client:
            try:
                return self._ai_detect(mesh)
            except Exception as e:
                print(f"⚠️  AI detection failed: {e}")
                print("   Falling back to heuristic detection...")

        # Fallback to heuristic
        return SimpleDetector.detect(mesh)

    def _ai_detect(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        AI-based detection using OpenAI.

        Args:
            mesh: Input mesh

        Returns:
            Detection result
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

        # Get mesh statistics
        stats = get_mesh_stats(mesh)
        heuristic = SimpleDetector.detect(mesh)

        # Create prompt
        prompt = f"""Analyze these 3D mesh statistics and determine the most likely geometric shape.

Mesh Statistics:
- Volume: {stats['volume']:.2f} mm³
- Surface Area: {stats['surface_area']:.2f} mm²
- Vertices: {stats['vertices_count']}
- Faces: {stats['faces_count']}
- Bounding Box Ratio (key metric): {stats['bbox_ratio']:.3f}
- Bounding Box Extents: {stats['bbox_extents'][0]:.1f} x {stats['bbox_extents'][1]:.1f} x {stats['bbox_extents'][2]:.1f} mm
- Aspect Ratios: {stats['aspect_ratio_1']:.2f} and {stats['aspect_ratio_2']:.2f}
- Watertight: {stats['is_watertight']}

Reference Ranges for Bounding Box Ratio:
- Solid Box: 0.95-1.05
- Hollow Box: 0.15-0.40  
- Cylinder: 0.40-0.85
- Sphere: 0.50-0.55
- Cone: 0.20-0.35

Based on these statistics, determine the shape. Respond with JSON:
{{
  "shape_type": "box|cylinder|sphere|cone|complex",
  "confidence": 0-100,
  "reasoning": "brief explanation"
}}

Only respond with valid JSON, no other text."""

        # Call OpenAI
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        try:
            response_text = response.content[0].text
            result = json.loads(response_text)

            return {
                'shape_type': result.get('shape_type', heuristic['shape_type']),
                'confidence': result.get('confidence', heuristic['confidence']),
                'reason': result.get('reasoning', 'AI-based detection'),
                'bbox_ratio': stats['bbox_ratio'],
                'stats': stats,
                'method': 'AI'
            }
        except Exception as e:
            print(f"   Failed to parse AI response: {e}")
            heuristic['method'] = 'heuristic'
            return heuristic
