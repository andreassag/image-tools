# Contributing to `image-tools`

Thank you for your interest in contributing to `image-tools`! We welcome contributions, bug fixes, feature proposals, and documentation improvements.

---

## Development Setup

`image-tools` uses [`uv`](https://docs.astral.sh/uv/) for fast and reliable Python dependency management.

### 1. Clone the repository
```bash
git clone https://github.com/andreassag/image-tools.git
cd image-tools
```

### 2. Create virtual environment and sync dependencies
```bash
# Sync dependencies including development and PDF extras
uv sync --extra dev --extra pdf
```

### 3. Run the test suite
```bash
uv run pytest
```

---

## Code Style & Guidelines

- **Python Version**: Requires Python 3.12 or newer.
- **Type Annotations**: Ensure all new functions and public APIs are typed. Type annotations are tracked with PEP 561 (`src/image_tools/py.typed`).
- **Formatting**: Keep code lines clean, readable, and under 100 characters.
- **Testing**: Every bug fix or new feature should be accompanied by corresponding unit tests in `tests/`.

---

## Pull Request Process

1. Fork the repository and create your feature branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Make your changes, ensuring existing and new tests pass:
   ```bash
   uv run pytest
   ```
3. Commit your changes with descriptive commit messages.
4. Push to your branch and open a Pull Request against `main`.
