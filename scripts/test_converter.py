#!/usr/bin/env python3
"""
Test mesh converter installation and functionality

Usage:
    python test_converter.py
"""

import sys
import numpy as np
import open3d as o3d
from pathlib import Path


def test_imports():
    """Test that all required packages are installed"""
    print("\n" + "="*60)
    print("TESTING IMPORTS")
    print("="*60)
    
    try:
        import open3d
        print(f"✓ open3d {open3d.__version__}")
    except ImportError as e:
        print(f"✗ open3d not found: {e}")
        return False
    
    try:
        import numpy
        print(f"✓ numpy {numpy.__version__}")
    except ImportError as e:
        print(f"✗ numpy not found: {e}")
        return False
    
    try:
        import scipy
        print(f"✓ scipy {scipy.__version__}")
    except ImportError as e:
        print(f"✗ scipy not found: {e}")
        return False
    
    try:
        import sklearn
        print(f"✓ scikit-learn {sklearn.__version__}")
    except ImportError as e:
        print(f"✗ scikit-learn not found: {e}")
        return False
    
    try:
        import pyransac3d
        print(f"✓ pyransac3d (version unknown)")
    except ImportError as e:
        print(f"⚠ pyransac3d not found (optional): {e}")
    
    try:
        import matplotlib
        print(f"✓ matplotlib {matplotlib.__version__}")
    except ImportError as e:
        print(f"✗ matplotlib not found: {e}")
        return False
    
    return True


def test_mesh_operations():
    """Test basic mesh operations"""
    print("\n" + "="*60)
    print("TESTING MESH OPERATIONS")
    print("="*60)
    
    try:
        # Create a simple test mesh (cylinder)
        print("\n1. Creating test cylinder mesh...")
        mesh = o3d.geometry.TriangleMesh.create_cylinder(
            radius=0.5,
            height=2.0,
            resolution=20,
            split=4
        )
        print(f"   ✓ Created mesh with {len(mesh.vertices)} vertices")
        
        # Convert to point cloud
        print("\n2. Converting to point cloud...")
        pcd = mesh.sample_points_uniformly(number_of_points=10000)
        print(f"   ✓ Sampled {len(pcd.points)} points")
        
        # Downsample
        print("\n3. Downsampling...")
        pcd_down = pcd.voxel_down_sample(voxel_size=0.05)
        print(f"   ✓ Downsampled to {len(pcd_down.points)} points")
        
        # Estimate normals
        print("\n4. Estimating normals...")
        pcd_down.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=0.1,
                max_nn=30
            )
        )
        print(f"   ✓ Estimated {len(pcd_down.normals)} normals")
        
        # Statistical outlier removal
        print("\n5. Removing statistical outliers...")
        cl, ind = pcd_down.remove_statistical_outlier(
            nb_neighbors=20,
            std_ratio=2.0
        )
        pcd_clean = pcd_down.select_by_index(ind)
        removed = len(pcd_down.points) - len(pcd_clean.points)
        print(f"   ✓ Removed {removed} outliers")
        
        # Poisson reconstruction
        print("\n6. Reconstructing surface...")
        mesh_recon, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd_clean,
            depth=8
        )
        print(f"   ✓ Reconstructed mesh with {len(mesh_recon.vertices)} vertices")
        
        # Simplification
        print("\n7. Simplifying mesh...")
        mesh_simple = mesh_recon.simplify_quadric_decimation(
            target_number_of_triangles=1000
        )
        print(f"   ✓ Simplified to {len(mesh_simple.triangles)} triangles")
        
        print("\n✓ All mesh operations successful!")
        return True
        
    except Exception as e:
        print(f"\n✗ Mesh operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ransac():
    """Test RANSAC primitive fitting"""
    print("\n" + "="*60)
    print("TESTING RANSAC (optional)")
    print("="*60)
    
    try:
        import pyransac3d as pyrsc
        
        # Create test cylinder points
        print("\n1. Creating test cylinder points...")
        theta = np.linspace(0, 2*np.pi, 100)
        z = np.linspace(0, 1, 100)
        theta, z = np.meshgrid(theta, z)
        x = 0.5 * np.cos(theta).flatten()
        y = 0.5 * np.sin(theta).flatten()
        z = z.flatten()
        points = np.column_stack([x, y, z])
        
        print(f"   ✓ Created {len(points)} test points")
        
        # Fit cylinder
        print("\n2. Fitting cylinder with RANSAC...")
        cyl = pyrsc.Cylinder()
        center, axis, radius, inliers = cyl.fit(
            points,
            thresh=0.01,
            maxIteration=1000
        )
        
        print(f"   ✓ Detected cylinder:")
        print(f"     Center: {center}")
        print(f"     Axis: {axis}")
        print(f"     Radius: {radius:.3f}")
        print(f"     Inliers: {len(inliers)}/{len(points)}")
        
        # Verify result is reasonable
        if 0.45 < radius < 0.55:
            print("\n✓ RANSAC cylinder detection successful!")
            return True
        else:
            print(f"\n⚠ RANSAC result unexpected (radius={radius})")
            return False
        
    except ImportError:
        print("\n⚠ pyRANSAC-3D not installed (optional)")
        return True
    except Exception as e:
        print(f"\n✗ RANSAC test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_converter():
    """Test the mesh converter module"""
    print("\n" + "="*60)
    print("TESTING CONVERTER MODULE")
    print("="*60)
    
    try:
        from mesh_to_cad_converter import MeshToCADConverter
        
        print("\n1. Creating converter...")
        converter = MeshToCADConverter()
        print("   ✓ Converter created")
        
        print("\n2. Checking default config...")
        config = MeshToCADConverter.default_config()
        required_keys = [
            'voxel_size',
            'stat_nb_neighbors',
            'stat_std_ratio',
            'target_triangles'
        ]
        
        for key in required_keys:
            if key not in config:
                print(f"   ✗ Missing config key: {key}")
                return False
        
        print(f"   ✓ Config has all required keys")
        
        print("\n✓ Converter module working!")
        return True
        
    except Exception as e:
        print(f"\n✗ Converter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MESH CONVERTER TEST SUITE")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Mesh Operations", test_mesh_operations()))
    results.append(("RANSAC", test_ransac()))
    results.append(("Converter Module", test_converter()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✓ All tests passed! Ready to convert meshes.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
