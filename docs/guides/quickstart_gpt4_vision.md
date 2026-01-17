# GPT-4 Vision Quick Start Guide

## 🚀 60-Second Setup

```bash
# 1. Activate virtual environment
cd MeshConverter_V2
source .venv/bin/activate

# 2. Install dependencies
pip install openai pillow python-dotenv

# 3. Set API key (get from https://platform.openai.com/api-keys)
export OPENAI_API_KEY=sk-...

# 4. Test it!
python mesh_to_primitives.py tests/samples/simple_cylinder.stl --gpt4-vision
```

## 📊 What You'll See

```
🤖 Classifying with GPT-4 Vision...
  Rendering mesh from 6 angles...
  ✅ Successfully rendered 6 views
  Sending to GPT-4 Vision API...
  (Cost estimate: ~$0.060 @ $0.01/image)

  ✅ Classification: cylinder (95%)

📊 Comparison:
  Heuristic:    box      (75%)
  GPT-4 Vision: cylinder (95%)

  ✅ Using GPT-4 Vision classification (higher confidence)
```

## 🎯 When to Use It

| Scenario | Use Heuristic | Use GPT-4 Vision |
|----------|---------------|------------------|
| Quick prototyping | ✅ | ❌ |
| High-stakes medical device | ❌ | ✅ |
| Batch processing (1000+ meshes) | ✅ | ❌ |
| Ambiguous shapes (confidence < 80%) | ❌ | ✅ |
| Offline environment | ✅ | ❌ |
| Budget unlimited | ❌ | ✅ |

## 💰 Cost Calculator

| Meshes | Cost (GPT-4 Vision) | Cost (Heuristic) |
|--------|---------------------|------------------|
| 1 | $0.06 | $0.00 |
| 10 | $0.60 | $0.00 |
| 100 | $6.00 | $0.00 |
| 1000 | $60.00 | $0.00 |

**Hybrid Strategy (30% use GPT-4):**
- 1000 meshes: $18.00 (70% savings)
- Same accuracy as 100% GPT-4 Vision

## 🐛 Troubleshooting

**Error: "OPENAI_API_KEY not set"**
```bash
export OPENAI_API_KEY=sk-...
```

**Error: "No module named 'openai'"**
```bash
pip install openai pillow
```

**Error: "Rate limit exceeded"**
- Wait 60 seconds and retry
- Or upgrade OpenAI tier

**Warning: "Could not parse JSON"**
- Fallback parser will handle it automatically
- No action needed

## 📖 Full Documentation

- **Complete Guide:** [docs/GPT4_VISION_GUIDE.md](docs/GPT4_VISION_GUIDE.md)
- **Implementation Report:** [GPT4_VISION_IMPLEMENTATION.md](GPT4_VISION_IMPLEMENTATION.md)
- **Main README:** [README.md](README.md)

## 🤝 Support

Questions? Check the full guide or run the test suite:
```bash
python test_gpt4_vision.py
```
