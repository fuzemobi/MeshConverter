#!/bin/bash
# Setup script for MeshConverter_v2

set -e

echo "=================================="
echo "MeshConverter_v2 Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠ Virtual environment already exists"
    read -p "Remove and recreate? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo "✓ Created new virtual environment"
    else
        echo "✓ Using existing virtual environment"
    fi
else
    python3 -m venv venv
    echo "✓ Created virtual environment"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Run tests
echo "Running tests..."
python test_converter.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✓ Setup Complete!"
    echo "=================================="
    echo ""
    echo "To get started:"
    echo "  1. Activate the virtual environment:"
    echo "     source venv/bin/activate"
    echo ""
    echo "  2. Convert a mesh:"
    echo "     python mesh_to_cad_converter.py your_file.stl"
    echo ""
    echo "  3. Batch convert:"
    echo "     python batch_convert.py input_folder/ -o output/"
    echo ""
    echo "  4. Visualize results:"
    echo "     python visualize_results.py original.stl simplified.stl"
    echo ""
else
    echo ""
    echo "=================================="
    echo "✗ Setup Failed"
    echo "=================================="
    echo ""
    echo "Some tests failed. Please check the output above."
    echo "You may need to install additional system dependencies."
    echo ""
fi
