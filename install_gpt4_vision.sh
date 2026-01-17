#!/bin/bash
# Installation script for GPT-4 Vision dependencies

echo "========================================================================"
echo "Installing GPT-4 Vision Dependencies"
echo "========================================================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    echo "   Run: source .venv/bin/activate"
    echo ""
    exit 1
fi

echo "✅ Virtual environment: $VIRTUAL_ENV"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install openai>=1.0.0 pillow>=10.0.0 python-dotenv>=1.0.0

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependencies installed successfully"
else
    echo ""
    echo "❌ Installation failed"
    exit 1
fi

# Check for API key
echo ""
echo "========================================================================"
echo "Checking Configuration"
echo "========================================================================"
echo ""

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
    echo ""
    echo "   To use GPT-4 Vision, set your API key:"
    echo "   export OPENAI_API_KEY=sk-..."
    echo ""
    echo "   Or add to .env file:"
    echo "   echo 'OPENAI_API_KEY=sk-...' >> .env"
    echo ""
else
    echo "✅ OPENAI_API_KEY is set: ${OPENAI_API_KEY:0:20}..."
    echo ""
fi

# Run test
echo "========================================================================"
echo "Running Test"
echo "========================================================================"
echo ""

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Skipping test (no API key)"
    echo ""
    echo "To test manually:"
    echo "  export OPENAI_API_KEY=sk-..."
    echo "  python test_gpt4_vision.py"
    echo ""
else
    echo "Running GPT-4 Vision test suite..."
    echo ""
    python test_gpt4_vision.py
fi

echo ""
echo "========================================================================"
echo "Installation Complete"
echo "========================================================================"
echo ""
echo "Usage:"
echo "  python mesh_to_primitives.py <input.stl> --gpt4-vision"
echo ""
echo "Documentation:"
echo "  docs/GPT4_VISION_GUIDE.md"
echo ""
