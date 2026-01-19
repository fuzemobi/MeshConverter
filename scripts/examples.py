#!/usr/bin/env python3
"""
Example usage of MeshConverter_v2

This script demonstrates various usage patterns and configurations
"""

from mesh_to_cad_converter import MeshToCADConverter
from pathlib import Path


def example_basic_conversion():
    """Example 1: Basic conversion with defaults"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Conversion")
    print("="*60)
    
    converter = MeshToCADConverter()
    
    # Convert a single file
    outputs = converter.convert(
        'battery.stl',
        'output/'
    )
    
    print(f"\nOutputs:")
    for key, path in outputs.items():
        print(f"  {key}: {path}")


def example_high_quality():
    """Example 2: High-quality conversion"""
    print("\n" + "="*60)
    print("EXAMPLE 2: High-Quality Conversion")
    print("="*60)
    
    # Custom config for high quality
    config = {
        'voxel_size': 0.01,           # Finer voxels
        'stat_nb_neighbors': 30,      # More neighbors
        'stat_std_ratio': 2.5,        # Less aggressive
        'radius_nb_points': 20,       # Denser requirement
        'radius': 0.03,               # Smaller radius
        'normal_radius': 0.08,        # Finer normal estimation
        'poisson_depth': 10,          # Higher detail
        'density_quantile': 0.005,    # Keep more vertices
        'target_triangles': 20000,    # More triangles
        'export_intermediates': True,
    }
    
    converter = MeshToCADConverter(config)
    outputs = converter.convert('battery.stl', 'output/high_quality/')
    
    print(f"\nStatistics:")
    for key, value in converter.statistics.items():
        print(f"  {key}: {value}")


def example_fast_processing():
    """Example 3: Fast processing for preview"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Fast Processing")
    print("="*60)
    
    # Config for speed
    config = {
        'voxel_size': 0.05,           # Coarser voxels
        'stat_nb_neighbors': 10,      # Fewer neighbors
        'stat_std_ratio': 1.5,        # More aggressive
        'poisson_depth': 7,           # Lower detail
        'target_triangles': 1000,     # Fewer triangles
        'export_intermediates': False, # Skip intermediates
    }
    
    converter = MeshToCADConverter(config)
    outputs = converter.convert('battery.stl', 'output/fast/')
    
    print(f"\nProcessing complete!")


def example_aggressive_cleaning():
    """Example 4: Aggressive outlier removal"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Aggressive Outlier Removal")
    print("="*60)
    
    # Config for heavy cleaning
    config = {
        'voxel_size': 0.02,
        'stat_nb_neighbors': 30,      # More neighbors
        'stat_std_ratio': 1.0,        # Very aggressive
        'radius_nb_points': 25,       # Dense requirement
        'radius': 0.02,               # Small radius
        'density_quantile': 0.05,     # Remove bottom 5%
        'target_triangles': 5000,
    }
    
    converter = MeshToCADConverter(config)
    outputs = converter.convert('noisy_scan.stl', 'output/clean/')
    
    removed = (
        converter.statistics.get('stat_outliers_removed', 0) +
        converter.statistics.get('radius_outliers_removed', 0) +
        converter.statistics.get('artifacts_removed', 0)
    )
    
    print(f"\nTotal outliers/artifacts removed: {removed:,}")


def example_batch_processing():
    """Example 5: Process multiple files"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Batch Processing")
    print("="*60)
    
    converter = MeshToCADConverter()
    
    input_files = [
        'scan1.stl',
        'scan2.stl',
        'scan3.stl',
    ]
    
    results = []
    
    for input_file in input_files:
        if not Path(input_file).exists():
            print(f"⚠ Skipping {input_file} (not found)")
            continue
        
        print(f"\nProcessing {input_file}...")
        try:
            outputs = converter.convert(input_file, 'output/batch/')
            results.append({
                'input': input_file,
                'status': 'success',
                'outputs': outputs
            })
            print(f"✓ Complete")
        except Exception as e:
            print(f"✗ Failed: {e}")
            results.append({
                'input': input_file,
                'status': 'error',
                'error': str(e)
            })
    
    print(f"\nProcessed {len(results)} files")


def example_with_cylinder_detection():
    """Example 6: Detect cylinder parameters"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Cylinder Detection")
    print("="*60)
    
    converter = MeshToCADConverter()
    outputs = converter.convert('battery.stl', 'output/')
    
    # Check for cylinder parameters
    cylinder = converter.statistics.get('cylinder_params')
    
    if cylinder:
        print(f"\nDetected cylinder:")
        print(f"  Radius: {cylinder['radius']:.3f}m")
        print(f"  Length: {cylinder['length']:.3f}m")
        print(f"  Center: {cylinder['center']}")
        print(f"  Axis: {cylinder['axis']}")
        print(f"  Inlier ratio: {cylinder['inlier_ratio']:.1%}")
        
        # Could use these parameters to create parametric CAD
        print(f"\nParametric CAD dimensions:")
        print(f"  Diameter: {cylinder['radius'] * 2 * 1000:.1f}mm")
        print(f"  Height: {cylinder['length'] * 1000:.1f}mm")
    else:
        print("\n⚠ Cylinder detection not available (pyRANSAC-3D not installed)")


def example_medical_device():
    """Example 7: Medical device scan (MedTrackET use case)"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Medical Device Scan")
    print("="*60)
    
    # Config optimized for medical device scans
    config = {
        'voxel_size': 0.01,           # High precision
        'stat_nb_neighbors': 25,      # Good noise removal
        'stat_std_ratio': 2.0,        # Balanced
        'radius_nb_points': 18,       # Clean edges
        'radius': 0.025,              # Fine detail
        'normal_radius': 0.05,        # Smooth surfaces
        'poisson_depth': 9,           # High quality
        'density_quantile': 0.01,     # Minimal artifact removal
        'target_triangles': 15000,    # Detailed model
        'export_intermediates': True,
    }
    
    converter = MeshToCADConverter(config)
    
    # Process device scan
    outputs = converter.convert(
        'medtrack_device_scan.stl',
        'output/medical_devices/'
    )
    
    print(f"\nMedical device processing complete!")
    print(f"Files ready for:")
    print(f"  - CAD software import")
    print(f"  - 3D printing preparation")
    print(f"  - Quality inspection")
    print(f"  - Documentation")


def main():
    """Run examples"""
    print("\n" + "="*60)
    print("MeshConverter_v2 Usage Examples")
    print("="*60)
    
    # Uncomment the examples you want to run:
    
    # example_basic_conversion()
    # example_high_quality()
    # example_fast_processing()
    # example_aggressive_cleaning()
    # example_batch_processing()
    # example_with_cylinder_detection()
    # example_medical_device()
    
    print("\n" + "="*60)
    print("To run examples:")
    print("  1. Edit examples.py")
    print("  2. Uncomment the example functions you want to run")
    print("  3. Make sure you have input STL files")
    print("  4. Run: python examples.py")
    print("="*60)


if __name__ == "__main__":
    main()
