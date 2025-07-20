# Python 3.11+ Upgrade Guide

## 🚀 Modern Python 3.11+ Edition

The Salesforce AI Colleague project has been fully modernized to leverage Python 3.11+ features and best practices. This upgrade brings significant improvements in performance, type safety, and developer experience.

## 🆕 What's New

### Python Version Requirements
- **Minimum Python Version**: 3.11+
- **Recommended Version**: Python 3.11 or 3.12
- **Enhanced Features**: Modern async/await, improved type annotations, performance optimizations

### 📦 Dependency Management
- **Primary**: Poetry for robust dependency management
- **Fallback**: pip with precise version constraints
- **Version Constraints**: All packages pinned with upper bounds for stability

### 🔧 Modern Tooling
- **Ruff**: Ultra-fast Python linter and formatter (replaces flake8)
- **Black**: Code formatting with Python 3.11+ target
- **mypy**: Strict type checking with Python 3.11 features
- **pre-commit**: Automated code quality enforcement

### 🎯 Type Safety Improvements
- **`from __future__ import annotations`**: Forward-compatible type annotations
- **Strict mypy configuration**: Comprehensive type checking
- **Modern typing**: Leverages Python 3.11+ typing improvements

## 🛠️ Setup Instructions

### Quick Setup
```bash
# Run the automated setup script
python3 setup_python3.py
```

### Manual Setup

#### 1. Python Installation
**macOS (Homebrew):**
```bash
brew install python@3.11
python3.11 -m pip install --upgrade pip
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv
```

**Windows:**
Download Python 3.11+ from [python.org](https://www.python.org/downloads/)

#### 2. Poetry Setup (Recommended)
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Install optional LLM providers
poetry install --extras "all-llm"

# Activate environment
poetry shell
```

#### 3. Pip Setup (Alternative)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## 📋 Migration Guide

### For Existing Users

#### Update Python Version
1. Install Python 3.11+
2. Run the setup script: `python3 setup_python3.py`
3. Update your IDE/editor to use Python 3.11+

#### Update Dependencies
```bash
# With Poetry
poetry install

# With pip
pip install -r requirements.txt --upgrade
```

#### Code Quality Setup
```bash
# Install pre-commit hooks
pre-commit install

# Run all checks
pre-commit run --all-files
```

## 🔍 Quality Assurance

### Automated Checks
- **Code Formatting**: Black with Python 3.11+ target
- **Import Sorting**: isort with Black profile
- **Linting**: Ruff (replaces flake8, faster and more comprehensive)
- **Type Checking**: mypy with strict configuration
- **Security**: Bandit security linter
- **Documentation**: pydocstyle with Google convention

### Running Checks Manually
```bash
# Format code
black src/

# Sort imports
isort src/

# Lint with Ruff
ruff check src/

# Type check
mypy src/

# Security check
bandit -r src/

# Run all pre-commit hooks
pre-commit run --all-files
```

## 🚀 Performance Improvements

### Python 3.11+ Benefits
- **25% faster** execution compared to Python 3.10
- **Improved error messages** with better traceability
- **Enhanced async performance** for future async features
- **Better memory efficiency** for large metadata processing

### Modern Dependencies
- **Pydantic 2.x**: Up to 20x faster than v1
- **Rich 13.x**: Enhanced terminal output performance
- **NetworkX 3.x**: Improved graph algorithms
- **Pandas 2.x**: Better performance and memory usage

## 🛡️ Type Safety

### Enhanced Type Annotations
All major modules now use:
```python
from __future__ import annotations

# Modern type annotations
def process_metadata(data: dict[str, Any]) -> ComponentAnalysis | None:
    ...

# Generic types
class GenericProcessor[T]:
    def process(self, item: T) -> T:
        ...
```

### Strict mypy Configuration
```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
disallow_untyped_defs = true
```

## 📚 Best Practices

### Code Style
- **Line Length**: 88 characters (Black default)
- **String Quotes**: Double quotes preferred
- **Import Organization**: stdlib, third-party, local (isort)
- **Type Annotations**: Required for all public functions

### Documentation
- **Docstring Style**: Google format
- **Type Hints**: Comprehensive for all public APIs
- **Comments**: Focused on "why" not "what"

### Testing
- **Framework**: pytest with async support
- **Coverage**: Aim for >90% test coverage
- **Type Coverage**: 100% for core modules

## 🔧 Development Workflow

### Daily Development
1. **Activate Environment**: `poetry shell` or `source venv/bin/activate`
2. **Install Dependencies**: Handled automatically by Poetry
3. **Code**: Write modern Python 3.11+ code
4. **Check**: Pre-commit runs automatically on commit
5. **Test**: `pytest` or `poetry run pytest`

### Adding Dependencies
```bash
# With Poetry
poetry add package-name

# For development only
poetry add --group dev package-name

# Optional dependencies
poetry add --optional package-name
```

### Environment Variables
Update `.env` file with Python 3.11+ template:
```bash
# Created automatically by setup script
cp .env.template .env
# Edit with your credentials
```

## 🐛 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Check Python version
python --version

# Verify environment
which python
```

#### Poetry Issues
```bash
# Clear cache
poetry cache clear pypi --all

# Reinstall
poetry install --no-cache
```

#### Pre-commit Issues
```bash
# Update hooks
pre-commit autoupdate

# Clean and reinstall
pre-commit clean
pre-commit install
```

### Platform-Specific Notes

#### macOS
- Use Homebrew for Python installation
- May need to update Xcode command line tools

#### Windows
- Use official Python installer
- Enable "Add Python to PATH" during installation
- Use PowerShell or Windows Terminal

#### Linux
- Install python3.11-dev for some packages
- May need build-essential for compiled dependencies

## 📊 Compatibility Matrix

| Component | Python 3.11 | Python 3.12 | Notes |
|-----------|--------------|--------------|-------|
| Core Features | ✅ | ✅ | Full support |
| LLM Providers | ✅ | ✅ | All providers tested |
| Neo4j | ✅ | ✅ | Latest driver |
| Salesforce CLI | ✅ | ✅ | Node.js dependency |
| Development Tools | ✅ | ✅ | All tools updated |

## 🎯 Next Steps

1. **Run Setup**: `python3 setup_python3.py`
2. **Verify Installation**: `python src/main.py status`
3. **Configure Credentials**: Edit `.env` file
4. **Start Development**: Begin using modern Python 3.11+ features!

---

## 📞 Support

If you encounter issues with the Python 3.11+ upgrade:

1. **Check the setup script output** for specific error messages
2. **Verify Python version**: `python --version` should show 3.11+
3. **Review dependencies**: All packages should install without conflicts
4. **Run diagnostics**: `python src/main.py status` shows system health

The upgrade to Python 3.11+ ensures the project leverages the latest language features while maintaining compatibility with the Salesforce AI Colleague's advanced metadata analysis capabilities. 