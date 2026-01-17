#!/usr/bin/env python3
"""
Mesh decomposition into constituent primitives.

This module handles:
- Spatial clustering to identify separate components
- Connected component analysis
- Pattern matching against known primitive signatures
- Multi-primitive fitting and reporting
"""

import numpy as np
import trimesh
from typing import List, Dict, Tuple, Any
from scipy.spatial import cKDTree

try:
    from sklearn.cluster import DBSCAN
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class MeshDecomposer:
    """Decompose complex meshes into constituent primitives."""

    def __init__(self, 
                 spatial_threshold: float = 25.0,
                 min_cluster_size: int = 100,
                 eigenvalue_threshold: float = 0.5):
        """
        Initialize decomposer.

        Args:
            spatial_threshold: Distance threshold for clustering (mm)
            min_cluster_size: Minimum vertices per cluster
            eigenvalue_threshold: PCA eigenvalue ratio threshold
        """
        self.spatial_threshold = spatial_threshold
        self.min_cluster_size = min_cluster_size
        self.eigenvalue_threshold = eigenvalue_threshold

    def decompose(self, mesh: trimesh.Trimesh) -> List[Dict[str, Any]]:
        """
        Decompose mesh into constituent primitive components.

        Args:
            mesh: Input trimesh object

        Returns:
            List of component dictionaries with:
            - mesh: trimesh object for component
            - vertices_count: Number of vertices
            - bbox_ratio: Bounding box ratio metric
            - center: Component center (mm)
            - estimated_type: 'cylinder', 'box', 'sphere', or 'complex'
            - confidence: Confidence in type classification
        """
        print("\n🔍 Decomposing mesh into primitives...")

        # Step 1: Identify connected components
        components = self._find_connected_components(mesh)
        print(f"  Found {len(components)} connected component(s)")

        if len(components) <= 1:
            # Try spatial clustering
            components = self._spatial_cluster_mesh(mesh)
            print(f"  Spatial clustering found {len(components)} region(s)")

        # Step 2: Extract and analyze each component
        results = []
        for i, (face_indices, vertex_indices) in enumerate(components):
            if len(vertex_indices) < self.min_cluster_size:
                print(f"  ⊘ Component {i+1}: Too small ({len(vertex_indices)} vertices), skipping")
                continue

            result = self._analyze_component(
                mesh,
                face_indices,
                vertex_indices,
                component_id=i
            )
            results.append(result)

        print(f"✅ Decomposition complete: {len(results)} valid component(s)")
        return results

    def _find_connected_components(
        self,
        mesh: trimesh.Trimesh
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Find connected components using vertex/face connectivity.

        Returns:
            List of (face_indices, vertex_indices) tuples
        """
        # Build face adjacency
        face_adj = mesh.face_adjacency
        
        if len(face_adj) == 0:
            # Disconnected or single component
            return [(np.arange(len(mesh.faces)), np.arange(len(mesh.vertices)))]

        # Find connected components in face graph
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import connected_components

        n_faces = len(mesh.faces)
        
        # Build adjacency matrix
        adjacency = csr_matrix(
            (np.ones(len(face_adj)), (face_adj[:, 0], face_adj[:, 1])),
            shape=(n_faces, n_faces)
        )
        
        n_components, labels = connected_components(adjacency, directed=False)
        
        if n_components <= 1:
            # All connected
            return [(np.arange(n_faces), np.arange(len(mesh.vertices)))]

        # Extract each component
        components = []
        for comp_id in range(n_components):
            face_mask = labels == comp_id
            face_indices = np.where(face_mask)[0]
            
            # Get vertices used by these faces
            vertex_set = set()
            for fi in face_indices:
                vertex_set.update(mesh.faces[fi])
            
            vertex_indices = np.array(sorted(vertex_set))
            components.append((face_indices, vertex_indices))

        return components

    def _spatial_cluster_mesh(
        self,
        mesh: trimesh.Trimesh
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Use spatial clustering (DBSCAN) to find distinct regions.

        Returns:
            List of (face_indices, vertex_indices) tuples
        """
        if not HAS_SKLEARN:
            # Fallback: use simple distance-based clustering
            return self._simple_distance_clustering(mesh)
        
        # Cluster vertices by spatial proximity
        clustering = DBSCAN(
            eps=self.spatial_threshold,
            min_samples=self.min_cluster_size
        ).fit(mesh.vertices)
        
        labels = clustering.labels_
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

        if n_clusters <= 1:
            # Single cluster
            return [(np.arange(len(mesh.faces)), np.arange(len(mesh.vertices)))]

        # Extract faces for each cluster
        components = []
        for cluster_id in range(n_clusters):
            vertex_mask = labels == cluster_id
            vertex_indices = np.where(vertex_mask)[0]
            
            # Find faces that belong to this cluster
            face_indices = []
            for fi, face in enumerate(mesh.faces):
                if np.all(vertex_mask[face]):
                    face_indices.append(fi)
            
            if len(face_indices) > 0:
                components.append((np.array(face_indices), vertex_indices))

        return components

    def _simple_distance_clustering(
        self,
        mesh: trimesh.Trimesh
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Simple distance-based clustering (fallback when sklearn unavailable).
        Uses greedy nearest-neighbor approach.
        """
        vertices = mesh.vertices
        n_vertices = len(vertices)
        
        # Build KD-tree for fast neighbor queries
        tree = cKDTree(vertices)
        
        # Find neighbors within threshold for each vertex
        visited = set()
        clusters = []
        
        for start_v in range(n_vertices):
            if start_v in visited:
                continue
            
            # BFS to find connected component
            cluster_vertices = set()
            queue = [start_v]
            
            while queue:
                v = queue.pop(0)
                if v in visited:
                    continue
                visited.add(v)
                cluster_vertices.add(v)
                
                # Find neighbors
                neighbors = tree.query_ball_point(vertices[v], self.spatial_threshold)
                for neighbor in neighbors:
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            # Find faces for this cluster
            vertex_indices = np.array(sorted(cluster_vertices))
            if len(vertex_indices) >= self.min_cluster_size:
                vertex_set = set(vertex_indices)
                face_indices = []
                for fi, face in enumerate(mesh.faces):
                    if all(v in vertex_set for v in face):
                        face_indices.append(fi)
                
                if len(face_indices) > 0:
                    clusters.append((np.array(face_indices), vertex_indices))
        
        return clusters if clusters else [(np.arange(len(mesh.faces)), np.arange(n_vertices))]

    def _analyze_component(
        self,
        source_mesh: trimesh.Trimesh,
        face_indices: np.ndarray,
        vertex_indices: np.ndarray,
        component_id: int = 0
    ) -> Dict[str, Any]:
        """
        Analyze a single component to estimate primitive type.

        Args:
            source_mesh: Original mesh
            face_indices: Indices of faces in this component
            vertex_indices: Indices of vertices in this component
            component_id: Component identifier

        Returns:
            Analysis dictionary
        """
        # Extract component mesh
        component_mesh = source_mesh.submesh(
            [face_indices],
            only_watertight=False
        )[0]

        if len(component_mesh.vertices) < 4:
            return {
                'mesh': component_mesh,
                'vertices_count': len(component_mesh.vertices),
                'faces_count': len(component_mesh.faces),
                'bbox_ratio': 0,
                'center': component_mesh.centroid.copy(),
                'estimated_type': 'unknown',
                'confidence': 0,
                'component_id': component_id,
                'valid': False
            }

        # Calculate metrics
        volume = component_mesh.volume
        bbox = component_mesh.bounding_box
        bbox_volume = bbox.volume if bbox.volume > 0 else 1e-6
        bbox_ratio = volume / bbox_volume if bbox_volume > 0 else 0

        # PCA analysis
        vertices_centered = component_mesh.vertices - component_mesh.centroid
        if HAS_SKLEARN and len(vertices_centered) >= 3:
            pca = PCA(n_components=3)
            pca.fit(vertices_centered)
            eigenvalues = pca.explained_variance_
        else:
            # Fallback: use covariance eigenvalues
            cov = np.cov(vertices_centered.T)
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = np.sort(eigenvalues)[::-1]
        
        # Eigenvalue ratios
        if eigenvalues[2] > 1e-6:
            pca_ratio = eigenvalues[1] / eigenvalues[2]
        else:
            pca_ratio = float('inf')

        # Estimate type
        estimated_type, confidence = self._classify_component(
            bbox_ratio,
            pca_ratio,
            eigenvalues
        )

        print(f"  Component {component_id + 1}:")
        print(f"    Vertices: {len(component_mesh.vertices)}")
        print(f"    Bbox Ratio: {bbox_ratio:.3f}")
        print(f"    PCA Ratio: {pca_ratio:.3f}")
        print(f"    Type: {estimated_type} ({confidence:.0f}%)")

        return {
            'mesh': component_mesh,
            'vertices_count': len(component_mesh.vertices),
            'faces_count': len(component_mesh.faces),
            'volume': volume,
            'bbox_ratio': bbox_ratio,
            'pca_ratio': pca_ratio,
            'eigenvalues': eigenvalues.tolist(),
            'center': component_mesh.centroid.copy(),
            'estimated_type': estimated_type,
            'confidence': confidence,
            'component_id': component_id,
            'valid': True
        }

    def _classify_component(
        self,
        bbox_ratio: float,
        pca_ratio: float,
        eigenvalues: np.ndarray
    ) -> Tuple[str, float]:
        """
        Classify component by metrics.

        Returns:
            (shape_type, confidence_percent)
        """
        # Solid box: high bbox ratio, high eigenvalues
        if 0.85 <= bbox_ratio <= 1.05:
            return 'box', 85

        # Hollow/thin box: low bbox ratio, high eigenvalues
        if 0.15 <= bbox_ratio < 0.50:
            return 'box', 75

        # Cylinder: medium bbox ratio (π/4), PCA ratio ~1.0
        if 0.35 <= bbox_ratio <= 0.85:
            if 0.75 <= pca_ratio <= 1.35:
                return 'cylinder', 80
            else:
                return 'complex', 50

        # Sphere: bbox ratio ~π/6, all eigenvalues similar
        if 0.48 <= bbox_ratio <= 0.56:
            if pca_ratio > 0.9:
                return 'sphere', 75

        # Cone: low bbox ratio, elongated
        if 0.15 <= bbox_ratio <= 0.30:
            if pca_ratio > 1.5:
                return 'cone', 60

        return 'complex', 40

    def estimate_assembly_structure(
        self,
        components: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze relationships between components to infer assembly structure.

        Args:
            components: List of component analyses

        Returns:
            Assembly structure analysis
        """
        print("\n🔗 Analyzing assembly structure...")

        assembly = {
            'total_components': len(components),
            'by_type': {},
            'relationships': [],
            'total_volume': 0,
            'total_surface_area': 0
        }

        # Count by type
        for comp in components:
            if not comp['valid']:
                continue

            comp_type = comp['estimated_type']
            if comp_type not in assembly['by_type']:
                assembly['by_type'][comp_type] = []
            assembly['by_type'][comp_type].append(comp['component_id'])

            assembly['total_volume'] += comp.get('volume', 0)
            assembly['total_surface_area'] += comp['mesh'].area

        # Analyze component distances
        centers = np.array([c['center'] for c in components if c['valid']])
        if len(centers) > 1:
            for i in range(len(centers)):
                for j in range(i + 1, len(centers)):
                    distance = np.linalg.norm(centers[i] - centers[j])
                    assembly['relationships'].append({
                        'component1': i,
                        'component2': j,
                        'distance_mm': float(distance)
                    })

        print(f"  Components by type: {assembly['by_type']}")
        print(f"  Total volume: {assembly['total_volume']:.2f} mm³")

        return assembly


def decompose_mesh(mesh: trimesh.Trimesh,
                   spatial_threshold: float = 25.0) -> Dict[str, Any]:
    """
    Convenience function to decompose a mesh.

    Args:
        mesh: Input trimesh object
        spatial_threshold: Distance threshold for spatial clustering (mm)

    Returns:
        Dictionary with:
        - components: List of component analyses
        - assembly: Assembly structure analysis
        - total_components: Total count
    """
    decomposer = MeshDecomposer(spatial_threshold=spatial_threshold)
    components = decomposer.decompose(mesh)
    assembly = decomposer.estimate_assembly_structure(components)

    return {
        'components': components,
        'assembly': assembly,
        'total_components': len(components)
    }
