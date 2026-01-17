#!/usr/bin/env python3
"""
Test script for GPT-4 Vision mesh classification.

Tests the new GPT-4 Vision classifier on sample meshes.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import trimesh
from core.ai_classifier import GPT4VisionMeshClassifier
from detection.simple_detector import SimpleDetector


def test_cylinder():
    """Test GPT-4 Vision on simple_cylinder.stl"""
    print("\n" + "="*70)
    print("TEST 1: simple_cylinder.stl")
    print("="*70)

    # Load mesh
    mesh_path = "tests/samples/simple_cylinder.stl"
    print(f"\nLoading: {mesh_path}")
    mesh = trimesh.load(mesh_path)

    # Heuristic detection
    print("\n📊 HEURISTIC DETECTION:")
    heuristic_result = SimpleDetector.detect(mesh)
    print(f"  Shape: {heuristic_result['shape_type']}")
    print(f"  Confidence: {heuristic_result['confidence']}%")
    print(f"  Reason: {heuristic_result['reason']}")

    # GPT-4 Vision detection
    print("\n🤖 GPT-4 VISION DETECTION:")
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return False

    try:
        classifier = GPT4VisionMeshClassifier(api_key=api_key)
        vision_result = classifier.classify_mesh(mesh, verbose=True)

        # Compare results
        print("\n📊 COMPARISON:")
        print(f"  Heuristic:    {heuristic_result['shape_type']:<12} ({heuristic_result['confidence']:>3}%)")
        print(f"  GPT-4 Vision: {vision_result['shape_type']:<12} ({vision_result['confidence']:>3}%)")

        # Check if GPT-4 Vision got it right
        if vision_result['shape_type'] == 'cylinder':
            print("\n✅ SUCCESS: GPT-4 Vision correctly identified cylinder!")
            if heuristic_result['shape_type'] != 'cylinder':
                print("   (Heuristic got it wrong - this proves AI is better!)")
            return True
        else:
            print(f"\n❌ FAILURE: GPT-4 Vision said '{vision_result['shape_type']}', expected 'cylinder'")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_block():
    """Test GPT-4 Vision on simple_block.stl"""
    print("\n" + "="*70)
    print("TEST 2: simple_block.stl")
    print("="*70)

    # Load mesh
    mesh_path = "tests/samples/simple_block.stl"
    print(f"\nLoading: {mesh_path}")
    mesh = trimesh.load(mesh_path)

    # Heuristic detection
    print("\n📊 HEURISTIC DETECTION:")
    heuristic_result = SimpleDetector.detect(mesh)
    print(f"  Shape: {heuristic_result['shape_type']}")
    print(f"  Confidence: {heuristic_result['confidence']}%")
    print(f"  Reason: {heuristic_result['reason']}")

    # GPT-4 Vision detection
    print("\n🤖 GPT-4 VISION DETECTION:")
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return False

    try:
        classifier = GPT4VisionMeshClassifier(api_key=api_key)
        vision_result = classifier.classify_mesh(mesh, verbose=True)

        # Compare results
        print("\n📊 COMPARISON:")
        print(f"  Heuristic:    {heuristic_result['shape_type']:<12} ({heuristic_result['confidence']:>3}%)")
        print(f"  GPT-4 Vision: {vision_result['shape_type']:<12} ({vision_result['confidence']:>3}%)")

        # Check if GPT-4 Vision got it right (should be box or hollow_box)
        if vision_result['shape_type'] in ['box', 'hollow_box']:
            print("\n✅ SUCCESS: GPT-4 Vision correctly identified box!")
            return True
        else:
            print(f"\n⚠️  GPT-4 Vision said '{vision_result['shape_type']}', expected 'box'")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("GPT-4 VISION MESH CLASSIFIER TEST SUITE")
    print("="*70)

    # Check API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY environment variable not set!")
        print("   Please set it: export OPENAI_API_KEY=sk-...")
        return 1

    print(f"\n✅ API key found: {api_key[:20]}...")

    # Run tests
    results = []

    print("\n" + "="*70)
    print("Running Tests...")
    print("="*70)

    results.append(("simple_cylinder.stl", test_cylinder()))
    results.append(("simple_block.stl", test_block()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
