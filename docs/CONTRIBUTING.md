# Contributing to MeshConverter

Thank you for your interest in contributing to MeshConverter! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup Steps

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/fuzemobi/MeshConverter.git
   cd MeshConverter
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Install optional dependencies** (if needed)
   ```bash
   python scripts/setup_environment.py --all
   ```

5. **Verify installation**
   ```bash
   pytest tests/
   ```

## Code Standards

### Python Style
- **PEP 8 compliance**: Follow Python's style guide
- **Type hints required**: All function signatures must have type hints
- **Docstrings required**: All public functions must have Google-style docstrings
- **Line length**: Maximum 100 characters
- **Use Black formatter**: Run `black .` before committing

### Code Quality Tools

| Tool | Purpose | Command |
|------|---------|---------|
| `black` | Code formatting | `black .` |
| `pylint` | Linting | `pylint meshconverter/` |
| `mypy` | Type checking | `mypy meshconverter/` |
| `pytest` | Testing | `pytest tests/` |
| `pytest-cov` | Coverage | `pytest --cov=meshconverter tests/` |

### Testing Standards

- **Test coverage target**: ≥80%
- **Write tests first**: TDD encouraged
- **Unit tests**: Place in `tests/unit/`
- **Integration tests**: Place in `tests/integration/`
- **Test naming**: `test_<functionality>_<scenario>`

Example test:
```python
def test_cylinder_detection_on_simple_mesh():
    """Test cylinder detection on known cylindrical mesh."""
    mesh = trimesh.creation.cylinder(radius=10.0, height=50.0)
    result = classify_mesh_with_voxel(mesh)
    assert result['shape_type'] == 'cylinder'
    assert result['confidence'] > 80
```

## Pull Request Process

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Write code following the standards above
- Add/update tests
- Update documentation

### 3. Run Quality Checks
```bash
# Format code
black .

# Type check
mypy meshconverter/

# Lint
pylint meshconverter/

# Run tests
pytest tests/ --cov=meshconverter

# All tests must pass before submitting PR
```

### 4. Commit Changes
```bash
git add -A
git commit -m "feat: Add your feature description

- Detailed change 1
- Detailed change 2
- Testing: All tests passing
- Coverage: X% (if changed)
"
```

**Commit Message Format:**
- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- First line: Brief description (<50 chars)
- Body: Detailed explanation of changes
- Include test status

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub with:
- Clear description of changes
- Reference any related issues
- Screenshots/examples if applicable
- Confirmation that tests pass

## Project Structure

```
MeshConverter/
├── meshconverter/          # Main package
│   ├── core/              # Core utilities
│   ├── primitives/        # Geometric primitives
│   ├── detection/         # Shape detection
│   ├── validation/        # Quality validation
│   ├── classification/    # Classification methods
│   └── cli.py            # CLI interface
│
├── scripts/               # Utility scripts
├── tests/                 # All tests
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
│
└── docs/                  # Documentation
    ├── guides/           # User guides
    ├── api/              # API documentation
    └── dev/              # Developer docs
```

## Types of Contributions

### Bug Reports
- Use GitHub Issues
- Include minimal reproduction example
- Provide system information (OS, Python version)
- Include error messages and stack traces

### Feature Requests
- Use GitHub Issues
- Describe use case and benefit
- Provide examples if possible
- Be open to discussion

### Code Contributions
- Bug fixes
- New features
- Performance improvements
- Documentation improvements
- Test coverage improvements

### Documentation
- Fix typos and errors
- Improve clarity
- Add examples
- Translate documentation

## Adding New Classification Methods

If you want to add a new classification method:

1. Create new classifier in `meshconverter/classification/`
2. Implement interface:
   ```python
   def classify_mesh(
       mesh: trimesh.Trimesh,
       verbose: bool = True
   ) -> Dict[str, Any]:
       """
       Returns:
           {
               'shape_type': str,
               'confidence': int (0-100),
               'n_components': int,
               'reasoning': str,
               'method': str
           }
       """
   ```
3. Add to `meshconverter/classification/__init__.py`
4. Add CLI option in `meshconverter/cli.py`
5. Write tests in `tests/integration/`
6. Update documentation

## Adding New Geometric Primitives

To add a new primitive (e.g., torus, pyramid):

1. Create `meshconverter/primitives/your_primitive.py`
2. Inherit from `Primitive` base class
3. Implement `fit()` method
4. Implement `to_cadquery()` method
5. Add tests in `tests/unit/test_primitives.py`
6. Update documentation

## Code Review Guidelines

When reviewing PRs:
- ✅ Code follows PEP 8 and project standards
- ✅ Type hints present and correct
- ✅ Docstrings complete and clear
- ✅ Tests written and passing
- ✅ No decrease in test coverage
- ✅ Documentation updated
- ✅ No hardcoded values or magic numbers
- ✅ Error handling appropriate
- ✅ Performance considerations addressed

## Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the Code of Conduct (TODO: add CoC)

## Questions?

- Open a GitHub Discussion for questions
- Check existing issues and documentation first
- Tag issues appropriately

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to MeshConverter! 🚀
