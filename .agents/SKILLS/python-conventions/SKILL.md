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

App modules (package)
```
from app import gametypes  # NOT from app.gametypes import ...
from app import schema
gametypes.VibemonT  # use gametypes.TypeName
```

## Libraries

- Use `niquests` instead of `httpx`
- Use `cattrs`/`attrs` instead of `pydantic`/`dataclasses`
- Use `structlog` instead of `logging`