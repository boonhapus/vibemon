"""Inspect the configured database or run ad-hoc SQL interactively."""

import asyncio
import sys

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine
import cyclopts
import sqlalchemy as sa

from app.storage.database import engine as db_engine
from scripts import _common

app = cyclopts.App(
    help=(
        "List tables or query the database from repo-root `.env`.\n\n"
        "Examples:\n"
        "  db_shell.py\n"
        "  db_shell.py --counts\n"
        '  db_shell.py --sql "SELECT id, username FROM trainer LIMIT 5"\n'
        "  db_shell.py --shell"
    ),
    help_format="markdown",
)


def _format_rows(columns: list[str], rows: list[tuple[object, ...]]) -> None:
    if not rows:
        print("(0 rows)")
        return
    widths = [len(col) for col in columns]
    rendered: list[list[str]] = []
    for row in rows:
        cells = ["" if value is None else str(value) for value in row]
        rendered.append(cells)
        for idx, cell in enumerate(cells):
            widths[idx] = max(widths[idx], len(cell))
    header = " | ".join(col.ljust(widths[idx]) for idx, col in enumerate(columns))
    print(header)
    print("-+-".join("-" * width for width in widths))
    for cells in rendered:
        print(" | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(cells)))
    print(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})")


async def _list_tables(engine: AsyncEngine, *, counts: bool) -> None:
    async with engine.connect() as conn:

        def table_names(sync_conn: sa.Connection) -> list[str]:
            return inspect(sync_conn).get_table_names()

        tables = sorted(await conn.run_sync(table_names))
        if not tables:
            print("No tables found.")
            return

        print(f"Database: {_common.load_script_settings().storage.database}")
        print(f"Tables ({len(tables)}):")
        for name in tables:
            if not counts:
                print(f"  {name}")
                continue
            result = await conn.execute(sa.text(f'SELECT COUNT(*) FROM "{name}"'))
            row_count = result.scalar_one()
            print(f"  {name}: {row_count}")


async def _run_sql(engine: AsyncEngine, sql: str) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(sa.text(sql))
        if result.returns_rows:
            rows = result.fetchall()
            _format_rows(list(result.keys()), [tuple(row) for row in rows])
        else:
            print(f"OK ({result.rowcount} row(s) affected)")


async def _repl(engine: AsyncEngine) -> None:
    database_url = _common.load_script_settings().storage.database
    print(f"Connected to {database_url}")
    print("Enter SQL (end with ;). Empty line or Ctrl-D exits.")
    print("Examples: SELECT * FROM trainer LIMIT 5;  \\dt")
    buffer: list[str] = []
    while True:
        try:
            prompt = "sql> " if not buffer else "...> "
            line = input(prompt)
        except EOFError:
            print()
            break
        stripped = line.strip()
        if not stripped and not buffer:
            break
        if stripped == "\\dt":
            await _list_tables(engine, counts=False)
            continue
        if stripped == "\\d":
            await _list_tables(engine, counts=True)
            continue
        buffer.append(line)
        if ";" not in line:
            continue
        sql = "\n".join(buffer).strip()
        buffer.clear()
        if sql.endswith(";"):
            sql = sql[:-1].strip()
        if not sql:
            continue
        try:
            await _run_sql(engine, sql)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)


@app.default
async def main(
    *,
    counts: bool = False,
    sql: str | None = None,
    shell: bool = False,
    database_url: str | None = None,
) -> None:
    """List tables, run one SQL statement, or open an interactive prompt."""
    storage = _common.load_script_settings(database_url=database_url)
    db_engine.ensure_sqlite_parent_dir(storage.storage.database)
    engine = db_engine.create_async_database_engine(storage.storage.database)
    try:
        if shell:
            await _repl(engine)
        elif sql is not None:
            await _run_sql(engine, sql)
        else:
            await _list_tables(engine, counts=counts)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(app())
