```markdown
# roman-voparquet Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill documents the development patterns and coding conventions used in the `roman-voparquet` Python repository. It covers file naming, import/export styles, commit patterns, and testing approaches. Use this guide to maintain consistency and efficiency when contributing to or maintaining the codebase.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `data_processor.py`, `utils/helper_functions.py`

### Import Style
- Use **relative imports** for modules within the repository.
  - Example:
    ```python
    from .utils import helper_function
    ```

### Export Style
- Use **named exports** (explicitly define what is exported from a module).
  - Example:
    ```python
    __all__ = ['MyClass', 'my_function']
    ```

### Commit Patterns
- Commit messages are freeform, with no strict prefixing.
- Average commit message length: ~40 characters.
  - Example: `fix data parsing in parquet loader`

## Workflows

_No automated workflows were detected in this repository._

## Testing Patterns

- **Framework:** Unknown (not explicitly detected).
- **Test File Pattern:** Test files use the `.test.ts` extension, suggesting some TypeScript-based testing may exist alongside Python code.
  - Example test file: `parquet_loader.test.ts`
- **Note:** If writing new tests, follow the existing `.test.ts` naming convention, even if the main codebase is Python.

## Commands

| Command | Purpose |
|---------|---------|
| /coding-conventions | Review file naming, import, and export styles |
| /commit-patterns    | See examples and guidelines for commit messages |
| /testing-patterns   | Get information on how to structure and name test files |

```