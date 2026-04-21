---
name: python-conventions
description: >
  Python rules (must) and conventions (should) for the vibemon backend.
---

## What this skill is for

It tells you which Python libraries to use and how to write imports in `backend/app`.

---

## Rules (must follow)

Do not switch these libraries unless a human says so in a ticket or doc.

**HTTP**

- Use: niquests
- Do not use: httpx (for new code)

**Data classes and parsing**

- Use: attrs and cattrs
- Do not use: Pydantic or stdlib dataclasses for the same job (for new code)

**Logging**

- Use: structlog
- Do not use: stdlib `logging` as the main API (for new code)

---

## Conventions (should follow)

### Rule of thumb for imports

1. Import the **module**.
2. Use the **module name** before each symbol.

Good:

```python
from app import types
from app import schema

x = types.VibemonTypeT
y = schema.BattleVibemon
```

Avoid for app code (unless the file already does it and you are only making a small edit):

```python
from app.types import VibemonTypeT
```

### Standard library

These patterns are fine:

```python
from typing import ...
import datetime as dt
import functools as ft
```

### Other third-party libs

Example of a short import name for a big lib:

```python
import sqlalchemy as sa
```

Copy the same style as other files in the repo.

---

## If you are unsure

- Editing an old file: match that file’s import style.
- New file: use the rules and conventions above.
