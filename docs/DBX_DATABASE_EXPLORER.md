# DBX-inspired database explorer

This feature adds a native `ish dbx` command family for local SQLite inspection. It is inspired by DBX's database workflow, but it is **not** the upstream DBX desktop app and does not claim DBX's 100+ database drivers.

## Commands

```sh
ish dbx capabilities
ish dbx doctor
ish dbx tables @myworkspace
ish dbx views ./app.db
ish dbx indexes ./app.db
ish dbx schema ./app.db users --format json
ish dbx query ./app.db --sql 'SELECT id, name FROM users' --limit 100
ish dbx query ./app.db --sql 'SELECT name FROM users WHERE id = ?' --params-file params.json
ish dbx query ./app.db --file ./query.sql --format csv
```

Database references use the existing workspace resolver, so `@workspace_name` is supported. A database must already exist; this command does not silently create one.

## Safety defaults

- Queries are read-only by default.
- Exactly one SQL statement is accepted.
- Bind values using `--params-file` instead of interpolating user data into SQL.
- Result output is bounded by `--limit` (default 1,000; maximum 100,000).
- SQLite progress callbacks enforce a best-effort query deadline (default 5 seconds; maximum 300 seconds).
- Writes require both `--write` and `--allow-destructive`. These flags are intentionally explicit; use disposable data while learning.
- The existing SQLite authorizer remains the enforcement boundary.
- Connection errors are summarized to avoid accidentally echoing database values or paths.

For example, create a disposable database with the existing command, then inspect it:

```sh
ish db init ./practice.db
ish dbx tables ./practice.db
ish dbx query ./practice.db --sql 'SELECT 1 AS ready'
```

## Output

- `--format json` is available for object-list and schema commands.
- Query output supports newline-delimited JSON (`jsonl`, default) and CSV.
- Binary SQLite values are represented as hexadecimal data in JSON output.

## Current scope and limitations

Implemented: local SQLite tables, views, indexes, table schema, foreign keys, bounded query output, parameter binding, CSV/JSONL output, read-only defaults and capability diagnostics.

Not implemented yet: PostgreSQL/MySQL adapters, persistent remote connection profiles, upstream DBX CLI bridging, MCP integration, AI-generated query execution, database synchronization or cloud database provisioning. `ish dbx capabilities` reports this boundary explicitly.

The upstream DBX CLI has its own runtime and platform requirements. Do not download or execute a DBX binary automatically on iSH. A future adapter must first verify architecture, version, protocol and permissions.
