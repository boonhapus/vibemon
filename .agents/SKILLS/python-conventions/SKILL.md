---
name: python-conventions
description: >
  Python conventions for this project.
---

## Imports

Prefer standard `import` syntax, do not use `from X import Y` or `import as Z` unless noted below.

Standard library
```
from typing import ...
import datetime as dt
import functools as ft
```

Third party
```
import sqlalchemy as sa
```

Local
```
from vibemon import schema
```

## Libraries

- Use `niquests` instead of `httpx`
- Use `cattrs`/`attrs` instead of `pydantic`/`dataclasses`
- Use `structlog` instead of `logging`