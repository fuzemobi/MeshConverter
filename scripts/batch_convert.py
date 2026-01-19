#!/usr/bin/env python3
"""
Batch Mesh Converter
Process multiple STL files in parallel

Usage:
    python batch_convert.py input_folder/ output_folder/
    python batch_convert.py *.stl -o output/
"""

import sys
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict
import json
from mesh_to_cad_converter import MeshToCADConverter


def process_single_file(
    input_path: str,
    output_dir: str,
    config: Dict
) -> Dict:
    """
    Process a single mesh file
    
    Args:
        input_path: Input file path
        output_dir: Output directory
        config: Converter configuration
        
    Returns:
        Result dictionary with status and outputs
    """
    try:
        converter = MeshToCADConverter(config)
        outputs = converter.convert(input_path, output_dir)
        
        return {
            'input': input_path,
            'status': 'success',
            'outputs': outputs,
            'statistics': converter.statistics
        }
        
    except Exception as e:
        return {
            'input': input_path,
            'status': 'error',
            'error': str(e)
        }


def find_stl_files(paths: List[str]) -> List[Path]:
    """
    Find all STL files in given paths
    
    Args:
        paths: List of file paths or directories
        
    Returns:
        List of STL file paths
    """
    stl_files = []
    
    for path_str in paths:
        path = Path(path_str)
        
        if path.is_file() and path.suffix.lower() == '.stl':
            stl_files.append(path)
        elif path.is_dir():
            stl_files.extend(path.rglob('*.stl'))
            stl_files.extend(path.rglob('*.STL'))
    
    return sorted(set(stl_files))


def main():
    """Batch processing CLI"""
    parser = argparse.ArgumentParser(
        description='Batch convert mesh scans to simplified CAD files'
    )
    
    parser.add_argument(
        'inputs',
        nargs='+',
        help='Input STL files or directories'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output directory'
    )
    
    parser.add_argument(
        '-j', '--jobs',
        type=int,
        default=None,
        help='Number of parallel jobs (default: CPU count)'
    )
    
    parser.add_argument(
        '--voxel-size',
        type=float,
        default=0.02,
        help='Voxel size for downsampling (default: 0.02)'
    )
    
    parser.add_argument(
        '--target-triangles',
        type=int,
        default=5000,
        help='Target number of triangles (default: 5000)'
    )
    
    parser.add_argument(
        '--no-intermediates',
        action='store_true',
        help='Do not export intermediate files'
    )
    
    args = parser.parse_args()
    
    # Find all STL files
    print("Searching for STL files...")
    stl_files = find_stl_files(args.inputs)
    
    if not stl_files:
        print("✗ No STL files found!")
        return 1
    
    print(f"✓ Found {len(stl_files)} STL file(s)")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup configuration
    config = MeshToCADConverter.default_config()
    config['voxel_size'] = args.voxel_size
    config['target_triangles'] = args.target_triangles
    config['export_intermediates'] = not args.no_intermediates
    
    # Process files in parallel
    print(f"\nProcessing {len(stl_files)} files with {args.jobs or 'auto'} workers...")
    print(f"{'='*60}\n")
    
    results = []
    
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        # Submit all jobs
        futures = {
            executor.submit(
                process_single_file,
                str(stl_file),
                str(output_dir),
                config
            ): stl_file
            for stl_file in stl_files
        }
        
        # Process results as they complete
        for future in as_completed(futures):
            stl_file = futures[future]
            result = future.result()
            results.append(result)
            
            if result['status'] == 'success':
                print(f"✓ {stl_file.name}")
            else:
                print(f"✗ {stl_file.name}: {result['error']}")
    
    # Save batch summary
    summary_path = output_dir / 'batch_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = len(results) - success_count
    
    print(f"\n{'='*60}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"✓ Successful: {success_count}/{len(results)}")
    
    if error_count > 0:
        print(f"✗ Failed: {error_count}/{len(results)}")
        print("\nFailed files:")
        for result in results:
            if result['status'] == 'error':
                print(f"  - {Path(result['input']).name}: {result['error']}")
    
    print(f"\n✓ Summary saved to: {summary_path}")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
