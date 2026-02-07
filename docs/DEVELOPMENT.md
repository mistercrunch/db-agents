# Code Quality Setup

This project uses `ruff` for linting and formatting, with `pre-commit` hooks to ensure code quality.

## Tools Configured

### Ruff

Fast Python linter and formatter written in Rust.

**Configuration:** `pyproject.toml`

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = []
```

**Rules enabled:**
- `E` - pycodestyle errors
- `F` - pyflakes
- `I` - isort (import sorting)
- `N` - pep8-naming
- `W` - pycodestyle warnings
- `UP` - pyupgrade (modern Python syntax)

### Pre-commit

Git hooks for automatic code quality checks before commits.

**Configuration:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## Usage

### Manual Checks

```bash
# Lint and auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/

# Check without modifying files
ruff check src/ tests/
ruff format --check src/ tests/
```

### Pre-commit Hooks

Pre-commit hooks are installed and will run automatically on `git commit`.

```bash
# Install hooks (already done)
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run manually on staged files
pre-commit run
```

### What Gets Auto-Fixed

Ruff automatically fixes:
- Import sorting and organization
- Trailing whitespace
- Missing/extra blank lines
- Modern Python syntax (e.g., `list[str]` instead of `List[str]`)
- String quote normalization
- Line length violations (by reformatting)

## Current Status

✅ **All files passing:**
- 9 Python files formatted
- 0 linting errors
- Pre-commit hooks installed and working

## Initial Cleanup

When ruff was first run on this codebase:
- **39 issues auto-fixed** (imports, whitespace, syntax upgrades)
- **1 manual fix** (line too long in utils.py)
- **6 files reformatted** for consistent style

## CI/CD Integration

To run these checks in CI/CD:

```yaml
# GitHub Actions example
- name: Check code quality
  run: |
    pip install ruff
    ruff check src/ tests/
    ruff format --check src/ tests/
```

## Editor Integration

### VS Code

Install the official Ruff extension:

```json
{
  "ruff.enable": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  }
}
```

### PyCharm

1. Go to Settings → Tools → External Tools
2. Add Ruff as external tool
3. Configure File Watcher for automatic formatting

### Vim/Neovim

Use `null-ls.nvim` or `nvim-lint` with ruff support.

## Development Workflow

1. **Write code** - Focus on functionality
2. **Save file** - Editor auto-formats (if configured)
3. **Commit** - Pre-commit hooks run automatically
4. **If hooks fail** - Review changes, stage fixes, commit again

## Benefits

- **Fast** - Ruff is 10-100x faster than traditional Python linters
- **Comprehensive** - Combines multiple tools (Black, isort, pyupgrade, etc.)
- **Automatic** - Pre-commit hooks prevent bad commits
- **Consistent** - All contributors follow same code style
- **Modern** - Encourages modern Python best practices
