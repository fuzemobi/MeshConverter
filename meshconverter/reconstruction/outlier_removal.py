#!/usr/bin/env python3
"""
Phase 2: Vision-Guided Outlier Removal

Uses GPT-4o Vision analysis results to intelligently filter scan noise and outliers.
"""

import trimesh
import numpy as np
from typing import Dict, Any, Optional, Tuple
from scipy.spatial import KDTree
from sklearn.cluster import DBSCAN


def remove_outliers_statistical(
    mesh: trimesh.Trimesh,
    outlier_percentage: float,
    method: str = 'distance',
    verbose: bool = True
) -> trimesh.Trimesh:
    """
    Remove outliers using statistical methods based on vision-detected percentage.

    Args:
        mesh: Input mesh
        outlier_percentage: Percentage of outliers (0-100) from vision analysis
        method: 'distance' or 'density' or 'isolation'
        verbose: Print progress

    Returns:
        Cleaned mesh with outliers removed
    """
    if verbose:
        print(f"\n🧹 Removing outliers ({outlier_percentage:.1f}% detected)...")

    vertices = mesh.vertices
    faces = mesh.faces

    if outlier_percentage < 1.0:
        if verbose:
            print(f"  ℹ️  Very low outlier percentage, skipping removal")
        return mesh

    # Calculate number of vertices to remove
    n_outliers = int(len(vertices) * (outlier_percentage / 100))

    if method == 'distance':
        # Remove vertices farthest from centroid
        centroid = vertices.mean(axis=0)
        distances = np.linalg.norm(vertices - centroid, axis=1)

        # Get indices of vertices to keep (lowest distances)
        threshold_idx = np.argsort(distances)[:-n_outliers]
        clean_vertices = vertices[threshold_idx]

        if verbose:
            print(f"  ✅ Distance-based: {len(vertices)} → {len(clean_vertices)} vertices")

    elif method == 'density':
        # Remove low-density regions using KDTree
        tree = KDTree(vertices)

        # Calculate local density (neighbors within radius)
        radius = np.percentile(np.linalg.norm(vertices - vertices.mean(axis=0), axis=1), 75) * 0.1
        densities = np.array([len(tree.query_ball_point(v, radius)) for v in vertices])

        # Keep high-density vertices
        threshold = np.percentile(densities, outlier_percentage)
        clean_mask = densities >= threshold
        clean_vertices = vertices[clean_mask]

        if verbose:
            print(f"  ✅ Density-based: {len(vertices)} → {len(clean_vertices)} vertices")

    elif method == 'isolation':
        # Use DBSCAN to find main cluster
        try:
            # Estimate eps from data
            centroid = vertices.mean(axis=0)
            distances = np.linalg.norm(vertices - centroid, axis=1)
            eps = np.percentile(distances, 25) * 0.5

            clustering = DBSCAN(eps=eps, min_samples=10).fit(vertices)
            labels = clustering.labels_

            # Find largest cluster
            unique_labels, counts = np.unique(labels[labels >= 0], return_counts=True)

            if len(unique_labels) > 0:
                main_cluster_label = unique_labels[np.argmax(counts)]
                clean_mask = labels == main_cluster_label
                clean_vertices = vertices[clean_mask]

                if verbose:
                    print(f"  ✅ DBSCAN clustering: {len(vertices)} → {len(clean_vertices)} vertices")
                    print(f"     Found {len(unique_labels)} clusters, kept largest")
            else:
                if verbose:
                    print(f"  ⚠️  No clusters found, keeping all vertices")
                clean_vertices = vertices

        except Exception as e:
            if verbose:
                print(f"  ⚠️  Clustering failed: {e}, using distance method")
            # Fallback to distance method
            centroid = vertices.mean(axis=0)
            distances = np.linalg.norm(vertices - centroid, axis=1)
            threshold_idx = np.argsort(distances)[:-n_outliers]
            clean_vertices = vertices[threshold_idx]

    else:
        raise ValueError(f"Unknown method: {method}")

    # Reconstruct mesh from clean vertices
    # Create vertex index mapping
    vertex_map = {old_idx: new_idx for new_idx, old_idx in enumerate(np.where(
        np.isin(np.arange(len(vertices)),
                [np.where((vertices == v).all(axis=1))[0][0] for v in clean_vertices])
    )[0])}

    # Filter faces that reference removed vertices
    clean_faces = []
    for face in faces:
        if all(v_idx < len(vertices) and v_idx in vertex_map for v_idx in face):
            try:
                new_face = [vertex_map[v_idx] for v_idx in face]
                clean_faces.append(new_face)
            except KeyError:
                continue

    if len(clean_faces) == 0:
        if verbose:
            print(f"  ⚠️  No valid faces after filtering, returning original mesh")
        return mesh

    try:
        clean_mesh = trimesh.Trimesh(vertices=clean_vertices, faces=clean_faces)

        if verbose:
            print(f"  📊 Result: {len(clean_mesh.vertices):,} vertices, {len(clean_mesh.faces):,} faces")
            volume_change = abs(clean_mesh.volume - mesh.volume) / mesh.volume * 100 if mesh.volume > 0 else 0
            print(f"     Volume change: {volume_change:.2f}%")

        return clean_mesh

    except Exception as e:
        if verbose:
            print(f"  ⚠️  Mesh reconstruction failed: {e}, returning original")
        return mesh


def remove_outliers_from_layers(
    mesh: trimesh.Trimesh,
    layer_vision_results: list,
    aggressive: bool = False,
    verbose: bool = True
) -> trimesh.Trimesh:
    """
    Remove outliers based on layer-by-layer vision analysis.

    Args:
        mesh: Input mesh
        layer_vision_results: List of vision analysis results per layer
        aggressive: If True, use stricter filtering
        verbose: Print progress

    Returns:
        Cleaned mesh
    """
    if not layer_vision_results:
        return mesh

    # Calculate average outlier percentage across layers
    outlier_percentages = [r.get('outlier_percentage', 0) for r in layer_vision_results]
    avg_outlier_pct = np.mean(outlier_percentages)
    max_outlier_pct = np.max(outlier_percentages)

    if verbose:
        print(f"\n📊 Layer-based outlier analysis:")
        print(f"  Average outliers: {avg_outlier_pct:.2f}%")
        print(f"  Maximum outliers: {max_outlier_pct:.2f}%")
        print(f"  Layers with outliers: {sum(1 for p in outlier_percentages if p > 5)}/{len(outlier_percentages)}")

    # Decide on cleaning strategy
    if avg_outlier_pct < 3.0:
        if verbose:
            print(f"  ✅ Low outlier rate, no cleaning needed")
        return mesh

    elif avg_outlier_pct < 10.0:
        # Moderate cleaning
        method = 'density'
        target_pct = avg_outlier_pct if not aggressive else avg_outlier_pct * 1.5

    else:
        # Aggressive cleaning
        method = 'isolation'
        target_pct = avg_outlier_pct if not aggressive else max_outlier_pct

    if verbose:
        print(f"  🎯 Strategy: {method} method, target {target_pct:.1f}% removal")

    return remove_outliers_statistical(mesh, target_pct, method=method, verbose=verbose)


def validate_cleaning_quality(
    original_mesh: trimesh.Trimesh,
    cleaned_mesh: trimesh.Trimesh,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Validate that outlier removal didn't damage the mesh.

    Args:
        original_mesh: Original mesh before cleaning
        cleaned_mesh: Mesh after outlier removal
        verbose: Print results

    Returns:
        Validation metrics
    """
    metrics = {
        'vertex_reduction_pct': (1 - len(cleaned_mesh.vertices) / len(original_mesh.vertices)) * 100,
        'face_reduction_pct': (1 - len(cleaned_mesh.faces) / len(original_mesh.faces)) * 100,
        'volume_change_pct': abs(cleaned_mesh.volume - original_mesh.volume) / original_mesh.volume * 100 if original_mesh.volume > 0 else 0,
        'is_watertight': cleaned_mesh.is_watertight,
        'has_valid_volume': cleaned_mesh.volume > 0
    }

    # Quality score (lower volume change = better)
    if metrics['volume_change_pct'] < 5:
        metrics['cleaning_quality'] = 'excellent'
    elif metrics['volume_change_pct'] < 15:
        metrics['cleaning_quality'] = 'good'
    elif metrics['volume_change_pct'] < 30:
        metrics['cleaning_quality'] = 'acceptable'
    else:
        metrics['cleaning_quality'] = 'poor'

    if verbose:
        print(f"\n📈 Cleaning Validation:")
        print(f"  Vertices removed: {metrics['vertex_reduction_pct']:.1f}%")
        print(f"  Faces removed: {metrics['face_reduction_pct']:.1f}%")
        print(f"  Volume change: {metrics['volume_change_pct']:.2f}%")
        print(f"  Watertight: {'YES' if metrics['is_watertight'] else 'NO'}")
        print(f"  Quality: {metrics['cleaning_quality'].upper()}")

    return metrics


def smart_outlier_removal(
    mesh: trimesh.Trimesh,
    vision_result: Optional[Dict] = None,
    conservative: bool = True,
    verbose: bool = True
) -> Tuple[trimesh.Trimesh, Dict[str, Any]]:
    """
    Intelligently remove outliers using vision guidance.

    Args:
        mesh: Input mesh
        vision_result: Vision analysis result with layer data
        conservative: If True, use conservative filtering (default)
        verbose: Print progress

    Returns:
        (cleaned_mesh, metrics_dict)
    """
    if vision_result is None or 'layer_results' not in vision_result:
        if verbose:
            print("  ℹ️  No vision data for outlier removal")
        return mesh, {'cleaned': False, 'reason': 'no_vision_data'}

    # Extract layer results
    layer_results = vision_result.get('layer_results', [])

    if not layer_results:
        return mesh, {'cleaned': False, 'reason': 'no_layer_data'}

    # Perform cleaning
    cleaned_mesh = remove_outliers_from_layers(
        mesh,
        layer_results,
        aggressive=not conservative,
        verbose=verbose
    )

    # Validate
    if cleaned_mesh is not mesh:  # Cleaning was performed
        validation = validate_cleaning_quality(original_mesh, cleaned_mesh, verbose)
        validation['cleaned'] = True

        # Rollback if quality is poor
        if validation['cleaning_quality'] == 'poor':
            if verbose:
                print(f"\n  ⚠️  Poor cleaning quality, reverting to original mesh")
            return mesh, {'cleaned': False, 'reason': 'poor_quality', 'attempted': validation}

        return cleaned_mesh, validation
    else:
        return mesh, {'cleaned': False, 'reason': 'not_needed'}
