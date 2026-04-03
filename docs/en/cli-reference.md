# CLI Reference

[User Guide Home](/Users/eastl/MLObservability/Stream/docs/USER_GUIDE.en.md)

This page is the command-line reference for `Stream`. It documents the installed `stream-cli` entry point, the available subcommands, the shared filter options, the JSON output shapes, and the operational meaning of each command.

If you want task-oriented explanation first, read the concept pages before this one. If you already know what kind of store action you need and want the exact command shape, this is the page to keep open.

## CLI Entry Points

`Stream` exposes the CLI through the console script declared in [`pyproject.toml`](/Users/eastl/MLObservability/Stream/pyproject.toml):

- `stream-cli`

You can also invoke the same entry point through the module:

- `python -m stream.cli`

The examples in this page use `stream-cli`, but the subcommands and options are the same for both forms.

## Global Shape

Every command starts with a required store path:

```bash
stream-cli --store .stream-store <command> [options]
```

Global arguments:

- `--store`
  - required
  - path to the local `Stream` store root

The CLI opens the store through `StreamStore.open(StoreConfig(root_path=Path(args.store)))`, so the command line is always operating on one local store root at a time.

## Shared Filter Options

The `scan`, `replay`, and `export` commands all build the same `ScanFilter` object internally.

Shared filter options:

- `--run-ref`
  - filters by canonical `run_ref`
- `--stage-ref`
  - filters by canonical `stage_execution_ref`
- `--record-type`
  - filters by canonical `record_type`
- `--start-time`
  - lower bound for time-based filtering
- `--end-time`
  - upper bound for time-based filtering

The important point is that CLI filtering is intentionally practical rather than arbitrary. The CLI is designed around common inspection and replay questions, not around ad hoc query language features.

## Common Conventions

Several behaviors are consistent across commands:

- command output is JSON or line-oriented JSON
- canonical history still lives in `segments/`, not in command output
- replay-oriented commands use explicit replay mode semantics
- maintenance commands report state rather than hiding operational risk

This matters because the CLI is meant for inspection and operations, not for inventing a second storage model beside the store itself.

## `scan`

Use `scan` when you want matching stored records directly.

Basic form:

```bash
stream-cli --store .stream-store scan [filters]
```

Supported options:

- `--run-ref`
- `--stage-ref`
- `--record-type`
- `--start-time`
- `--end-time`

Example:

```bash
stream-cli --store .stream-store scan --run-ref run/eval-1
```

Output behavior:

- prints one JSON object per matching stored record
- prints `record.record`, not the full `StoredRecord` envelope
- returns records in append order

Example output:

```json
{"completeness_marker":"complete","correlation_refs":{"trace_id":"trace/eval-1"},"degradation_marker":"none","observed_at":"2026-04-03T00:10:00Z","operation_context_ref":"op/evaluate-open","payload":{"event_key":"evaluation.started","level":"info","message":"Evaluation started."},"producer_ref":"scribe.python.local","record_ref":"record/eval-start","record_type":"structured_event","recorded_at":"2026-04-03T00:10:00Z","run_ref":"run/eval-1","schema_version":"1.0.0","stage_execution_ref":"stage/evaluate"}
```

What `scan` does not include:

- `sequence`
- `segment_id`
- `offset`
- replay warnings
- integrity classification

That is intentional. `scan` is a direct stored-record inspection path, not an integrity-aware summary surface.

Read [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md) if you need the conceptual distinction between direct scan and replay.

## `replay`

Use `replay` when you want an integrity-aware read of stored history.

Basic form:

```bash
stream-cli --store .stream-store replay [filters] [--mode strict|tolerant]
```

Supported options:

- `--run-ref`
- `--stage-ref`
- `--record-type`
- `--start-time`
- `--end-time`
- `--mode`
  - allowed values: `strict`, `tolerant`
  - default: `strict`

Example:

```bash
stream-cli --store .stream-store replay --run-ref run/eval-1 --mode strict
```

Output shape:

```json
{
  "known_gaps": [],
  "mode": "strict",
  "record_count": 1,
  "records": [
    {
      "completeness_marker": "complete",
      "correlation_refs": {"trace_id": "trace/eval-1"},
      "degradation_marker": "none",
      "observed_at": "2026-04-03T00:10:00Z",
      "operation_context_ref": "op/evaluate-open",
      "payload": {
        "event_key": "evaluation.started",
        "level": "info",
        "message": "Evaluation started."
      },
      "producer_ref": "scribe.python.local",
      "record_ref": "record/eval-start",
      "record_type": "structured_event",
      "recorded_at": "2026-04-03T00:10:00Z",
      "run_ref": "run/eval-1",
      "schema_version": "1.0.0",
      "stage_execution_ref": "stage/evaluate"
    }
  ],
  "warnings": []
}
```

Output fields:

- `mode`
  - replay mode used by the command
- `record_count`
  - number of returned records
- `warnings`
  - replay warnings, typically meaningful in `tolerant` mode
- `known_gaps`
  - explicit damaged-history gaps surfaced by tolerant replay
- `records`
  - canonical record payloads only

Operational notes:

- `strict` replay can fail when the store is corrupted
- `tolerant` replay allows damaged history to be read with explicit warnings
- replay output returns canonical record mappings, not `StoredRecord` placement metadata

This matters because replay is about safe interpretation, not just retrieval.

Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) if you need the full meaning of `warnings`, `known_gaps`, and strict replay failure.

## `export`

Use `export` when another tool needs replayed history as JSONL.

Basic form:

```bash
stream-cli --store .stream-store export --output exports/run-eval-1.jsonl [filters] [--mode strict|tolerant]
```

Supported options:

- `--run-ref`
- `--stage-ref`
- `--record-type`
- `--start-time`
- `--end-time`
- `--mode`
  - allowed values: `strict`, `tolerant`
  - default: `strict`
- `--output`
  - required destination path

Example:

```bash
stream-cli --store .stream-store export --run-ref run/eval-1 --mode strict --output exports/run-eval-1.jsonl
```

Output shape:

```json
{"mode":"strict","output":"exports/run-eval-1.jsonl","record_count":1}
```

Output fields:

- `output`
  - destination path that was written
- `mode`
  - replay mode used for export
- `record_count`
  - number of exported records

Operational notes:

- export is built on replay semantics
- export does not create a new source of truth
- if strict replay is not justified, export should not silently flatten that risk away

The canonical history is still in the store, not in the export file.

## `integrity`

Use `integrity` when you need an operator-facing health report for the local store.

Basic form:

```bash
stream-cli --store .stream-store integrity
```

Example:

```bash
stream-cli --store .stream-store integrity
```

Output shape:

```json
{
  "healthy": true,
  "issues": [],
  "record_count": 1,
  "recommendations": [],
  "segment_count": 1,
  "state": "healthy"
}
```

Output fields:

- `healthy`
  - top-level boolean summary
- `state`
  - `healthy`, `degraded`, or `corrupted`
- `segment_count`
  - observed segment count
- `record_count`
  - count of successfully read canonical records
- `issues`
  - detailed issue list
- `recommendations`
  - suggested next actions

Each issue is serialized from `IntegrityIssue` and can include:

- `severity`
- `code`
- `message`
- `segment_id`
- `line_number`

This command is the right place to begin when a store looks suspicious. It should usually come before `rebuild-indexes` or `repair`.

## `rebuild-indexes`

Use `rebuild-indexes` to reconstruct derivative helper indexes from canonical segments.

Basic form:

```bash
stream-cli --store .stream-store rebuild-indexes
```

Example:

```bash
stream-cli --store .stream-store rebuild-indexes
```

Output shape:

```json
{
  "integrity_state": "healthy",
  "notes": ["Derivative indexes were rebuilt from canonical segments."],
  "quarantined_paths": [],
  "rebuilt_indexes": true,
  "repaired_segments": [],
  "success": true,
  "warnings": []
}
```

Output fields:

- `success`
  - `true` when the store was healthy at rebuild time
- `repaired_segments`
  - always empty for rebuild-only runs
- `quarantined_paths`
  - always empty for rebuild-only runs
- `rebuilt_indexes`
  - whether index rebuild happened
- `integrity_state`
  - integrity state observed while rebuilding
- `notes`
  - explanatory notes
- `warnings`
  - warnings such as rebuilding from a damaged store

Operational notes:

- rebuild only touches derivative indexes
- rebuild can still warn if the canonical store has integrity issues
- rebuild does not make corrupted canonical history healthy

This is the right first maintenance action when helper state drift is the problem.

## `repair`

Use `repair` to repair truncated segment tails and rebuild derivative indexes afterward.

Basic form:

```bash
stream-cli --store .stream-store repair
```

Example:

```bash
stream-cli --store .stream-store repair
```

Output shape:

```json
{
  "integrity_state": "healthy",
  "notes": [
    "trimmed damaged tail from segment 3",
    "Derivative indexes were rebuilt from canonical segments."
  ],
  "quarantined_paths": [".stream-store/quarantine/segment-000003.jsonl"],
  "rebuilt_indexes": true,
  "repaired_segments": [3],
  "success": true,
  "warnings": []
}
```

Output fields:

- `success`
  - whether the store was healthy after repair
- `repaired_segments`
  - segments whose damaged tails were trimmed
- `quarantined_paths`
  - backup copies written to `quarantine/`
- `rebuilt_indexes`
  - whether indexes were rebuilt after repair
- `integrity_state`
  - resulting integrity state after the repair pass
- `notes`
  - action summaries
- `warnings`
  - repair or post-repair warnings

Operational notes:

- this command is intentionally narrow
- it repairs truncated JSON tails the store knows how to handle
- it is not a general-purpose history rewrite command
- it should feel more serious than `rebuild-indexes`

Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) before using this in production workflows.

## Exit Behavior

The CLI currently returns:

- `0` for successful command execution
- `2` when argparse rejects invalid command shape

Other failures surface as ordinary Python errors, such as:

- `ReplayError` when strict replay is not allowed
- `RecordValidationError` or `AppendError` if library behavior is extended into future write-oriented CLI commands
- filesystem-related exceptions if paths are invalid or not writable

The important point is that command success means the command completed. It does not automatically mean the store is healthy. For that, use `integrity` and read the resulting payload.

## Which Page To Read Next

- Read [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md) for the difference between `scan`, `replay`, and `export`.
- Read [Layout and Storage](/Users/eastl/MLObservability/Stream/docs/en/layout-and-storage.md) for what the CLI is operating on.
- Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) for the operational meaning of health checks, rebuilds, and repairs.
