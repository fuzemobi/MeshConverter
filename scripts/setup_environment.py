#!/usr/bin/env python3
"""
Setup script for MeshConverter optional dependencies.

Usage:
    python scripts/setup_environment.py --gpt4-vision
    python scripts/setup_environment.py --dev
    python scripts/setup_environment.py --all
"""

import subprocess
import sys
import argparse
import os


def install_gpt4_vision():
    """Install GPT-4 Vision dependencies."""
    print("📦 Installing GPT-4 Vision dependencies...")
    print("=" * 60)

    packages = [
        "openai>=1.0.0",
        "pillow>=10.0.0"
    ]

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install"
        ] + packages)
        print("=" * 60)
        print("✅ GPT-4 Vision dependencies installed successfully!")
        print("\nNext steps:")
        print("1. Set your OpenAI API key:")
        print("   export OPENAI_API_KEY='your-key-here'")
        print("2. Test with: mc input.stl --classifier gpt4-vision")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False


def install_dev_dependencies():
    """Install development dependencies."""
    print("📦 Installing development dependencies...")
    print("=" * 60)

    req_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "requirements-dev.txt"
    )

    if not os.path.exists(req_file):
        print(f"⚠️  Warning: {req_file} not found")
        print("Installing basic dev tools...")

        packages = [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "pylint>=2.17.0",
            "mypy>=1.0.0"
        ]

        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install"
            ] + packages)
        except subprocess.CalledProcessError as e:
            print(f"❌ Installation failed: {e}")
            return False
    else:
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "-r", req_file
            ])
        except subprocess.CalledProcessError as e:
            print(f"❌ Installation failed: {e}")
            return False

    print("=" * 60)
    print("✅ Development dependencies installed successfully!")
    print("\nAvailable commands:")
    print("  pytest tests/              # Run all tests")
    print("  black .                    # Format code")
    print("  pylint meshconverter/      # Lint code")
    print("  mypy meshconverter/        # Type check")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup MeshConverter environment with optional dependencies"
    )
    parser.add_argument(
        "--gpt4-vision",
        action="store_true",
        help="Install GPT-4 Vision dependencies (openai, pillow)"
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Install development dependencies (pytest, black, etc.)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install all optional dependencies"
    )

    args = parser.parse_args()

    if not any([args.gpt4_vision, args.dev, args.all]):
        parser.print_help()
        print("\n❌ Error: Please specify at least one option")
        sys.exit(1)

    print("\n🚀 MeshConverter Environment Setup")
    print("=" * 60)

    success = True

    if args.all or args.gpt4_vision:
        print("\n[1/2] GPT-4 Vision Dependencies" if args.all else "\nGPT-4 Vision Dependencies")
        if not install_gpt4_vision():
            success = False

    if args.all or args.dev:
        print("\n[2/2] Development Dependencies" if args.all else "\nDevelopment Dependencies")
        if not install_dev_dependencies():
            success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ All installations completed successfully!")
    else:
        print("⚠️  Some installations failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
