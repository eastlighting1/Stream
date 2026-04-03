# API Reference

[User Guide Home](/Users/eastl/MLObservability/Stream/docs/USER_GUIDE.en.md)

This page collects the public Python API exposed by `Stream`. It focuses on importable surfaces, constructor and method signatures, result models, configuration enums, and the typed exceptions a caller is expected to reason about.

If you need the conceptual explanation for when to use append, scan, replay, rebuild, or repair, use the narrative pages first. If you already know the operation you want and need the exact public surface, this is the page to keep open.

## Public Import Surfaces

The main public package surface is defined by [`src/stream/__init__.py`](/Users/eastl/MLObservability/Stream/src/stream/__init__.py). The public API submodule is defined by [`src/stream/api/__init__.py`](/Users/eastl/MLObservability/Stream/src/stream/api/__init__.py).

Public import paths:

- `stream`
- `stream.api`
- `stream.config`
- `stream.exceptions`
- `stream.models`

In most application code, the primary imports are:

- `StreamStore`
- `StoreConfig`
- `ScanFilter`
- `ReplayMode`

The package root also exports the result models, configuration enums, and typed exceptions documented below.

## Primary Entry Point

### `stream.StreamStore`

`StreamStore` is the main public entry point for the library.

Constructor shape:

```python
from stream import StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))
```

The important point is that callers do not normally assemble lower-level services themselves. They open one `StreamStore` bound to one local store root and perform all canonical write, read, integrity, export, and repair operations through that object.

Public constructor and property:

- `StreamStore.open(config: StoreConfig) -> StreamStore`
- `store.config -> StoreConfig`

Public methods:

- `append(record: object) -> AppendResult`
- `append_many(records: list[object] | tuple[object, ...]) -> AppendResult`
- `scan(scan_filter: ScanFilter | None = None) -> Iterator[StoredRecord]`
- `replay(scan_filter: ScanFilter | None = None, *, mode: ReplayMode = ReplayMode.STRICT) -> ReplayResult`
- `iter_replay(scan_filter: ScanFilter | None = None, *, mode: ReplayMode = ReplayMode.STRICT) -> Iterator[StoredRecord]`
- `check_integrity() -> IntegrityReport`
- `export_jsonl(destination: str | Path, scan_filter: ScanFilter | None = None, *, mode: ReplayMode = ReplayMode.STRICT) -> ReplayResult`
- `rebuild_indexes() -> RepairReport`
- `repair_truncated_tails() -> RepairReport`

### `StreamStore.open(...)`

`StreamStore.open(config)` is the public constructor-style entry point.

Parameters:

- `config`
  - required `StoreConfig`

Returns:

- `StreamStore`

Notes:

- binds the store to one local root path
- initializes the internal service surfaces behind the facade
- is the normal way to create a store instance

### `store.config`

`store.config` returns the resolved `StoreConfig` attached to the store.

Typical use:

```python
print(store.config.root_path)
print(store.config.durability_mode)
```

This is useful when higher-level application code wants to expose store identity or configuration in logs.

## Write Methods

### `store.append(record)`

Append one canonical record to the local store.

Signature:

```python
append(record: object) -> AppendResult
```

Parameters:

- `record`
  - one canonical record-like mapping

Returns:

- `AppendResult`

Raises:

- `RecordValidationError`
  - when the input is not a valid canonical record
- `AppendError`
  - when append execution fails

Operational meaning:

- validates and normalizes one record
- appends it to canonical segment history
- updates helper indexes if indexing is enabled
- returns structured acceptance metadata rather than a bare boolean

Example:

```python
result = store.append(record)
print(result.success)
print(result.accepted_count)
print(result.accepted[0].durability_status)
```

### `store.append_many(records)`

Append multiple canonical records in order.

Signature:

```python
append_many(records: list[object] | tuple[object, ...]) -> AppendResult
```

Parameters:

- `records`
  - ordered batch of canonical record-like mappings

Returns:

- `AppendResult`

Operational meaning:

- preserves append order across accepted records
- returns per-record receipts in `accepted`
- can report rejection details through `rejected`

This matters because `append_many()` should be interpreted as a structured batch append surface, not as a hidden rewrite or transaction abstraction.

Read [Write Path](/Users/eastl/MLObservability/Stream/docs/en/write-path.md) for full write semantics.

## Read Methods

### `store.scan(scan_filter=None)`

Directly scan stored records.

Signature:

```python
scan(scan_filter: ScanFilter | None = None) -> Iterator[StoredRecord]
```

Parameters:

- `scan_filter`
  - optional `ScanFilter`

Returns:

- iterator of `StoredRecord`

Operational meaning:

- direct stored-record inspection path
- preserves append order
- may use helper indexes in simple practical cases
- does not add replay warnings or replay health interpretation

Example:

```python
for stored in store.scan(ScanFilter(run_ref="run/eval-1")):
    print(stored.sequence, stored.record["record_type"])
```

### `store.replay(scan_filter=None, *, mode=ReplayMode.STRICT)`

Replay stored history under explicit replay semantics.

Signature:

```python
replay(
    scan_filter: ScanFilter | None = None,
    *,
    mode: ReplayMode = ReplayMode.STRICT,
) -> ReplayResult
```

Parameters:

- `scan_filter`
  - optional `ScanFilter`
- `mode`
  - `ReplayMode.STRICT` or `ReplayMode.TOLERANT`

Returns:

- `ReplayResult`

Raises:

- `ReplayError`
  - when strict replay is not allowed because the store is corrupted

Operational meaning:

- performs integrity-aware history reading
- returns canonical records plus replay warnings and known gaps when relevant
- is the right surface when read safety matters more than raw retrieval

### `store.iter_replay(scan_filter=None, *, mode=ReplayMode.STRICT)`

Iterator form of replay.

Signature:

```python
iter_replay(
    scan_filter: ScanFilter | None = None,
    *,
    mode: ReplayMode = ReplayMode.STRICT,
) -> Iterator[StoredRecord]
```

Parameters:

- `scan_filter`
  - optional `ScanFilter`
- `mode`
  - `ReplayMode.STRICT` or `ReplayMode.TOLERANT`

Returns:

- iterator of `StoredRecord`

Raises:

- `ReplayError`
  - when strict replay is not allowed

Operational meaning:

- useful when you want replay semantics without materializing the full `ReplayResult.records` tuple first
- still obeys the same integrity gate as `replay()`

### `store.export_jsonl(destination, scan_filter=None, *, mode=ReplayMode.STRICT)`

Export replayed history to JSONL.

Signature:

```python
export_jsonl(
    destination: str | Path,
    scan_filter: ScanFilter | None = None,
    *,
    mode: ReplayMode = ReplayMode.STRICT,
) -> ReplayResult
```

Parameters:

- `destination`
  - output file path
- `scan_filter`
  - optional `ScanFilter`
- `mode`
  - replay mode used for export

Returns:

- `ReplayResult`

Operational meaning:

- exports replayed history rather than bypassing replay
- keeps replay semantics explicit
- is useful for downstream tools that expect JSONL

Read [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md) for the full scan/replay/export relationship.

## Integrity And Maintenance Methods

### `store.check_integrity()`

Run an integrity check on the local store.

Signature:

```python
check_integrity() -> IntegrityReport
```

Returns:

- `IntegrityReport`

Raises:

- `IntegrityError`
  - when integrity processing fails unexpectedly

Operational meaning:

- inspects manifest and segment history
- classifies health as `healthy`, `degraded`, or `corrupted`
- returns issue details and recommendations

### `store.rebuild_indexes()`

Rebuild derivative helper indexes from canonical segments.

Signature:

```python
rebuild_indexes() -> RepairReport
```

Returns:

- `RepairReport`

Operational meaning:

- reconstructs derivative indexes
- reports the integrity state seen during rebuild
- can warn when the underlying store is already damaged

### `store.repair_truncated_tails()`

Repair known truncated-tail corruption and rebuild derivative indexes afterward.

Signature:

```python
repair_truncated_tails() -> RepairReport
```

Returns:

- `RepairReport`

Operational meaning:

- quarantines damaged segment files before modification
- trims damaged tails the store knows how to handle safely
- recomputes manifest frontier
- rebuilds indexes after repair

This is intentionally narrow. It should not be treated as a general-purpose history rewrite API.

Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) before building production repair workflows around it.

## Configuration Models

### `stream.StoreConfig`

`StoreConfig` is the configuration dataclass for one local store.

Signature:

```python
StoreConfig(
    root_path: Path,
    max_segment_bytes: int = 1_048_576,
    durability_mode: DurabilityMode = DurabilityMode.FSYNC,
    layout_mode: LayoutMode = LayoutMode.JSONL_SEGMENTS,
    layout_version: str = "1",
    enable_indexes: bool = True,
)
```

Fields:

- `root_path`
  - required store root path
- `max_segment_bytes`
  - segment rollover threshold
- `durability_mode`
  - append durability behavior
- `layout_mode`
  - currently `jsonl_segments`
- `layout_version`
  - currently `"1"`
- `enable_indexes`
  - whether derivative indexes are maintained

Validation:

- raises `ValueError` if `max_segment_bytes <= 0`

Typical use:

```python
config = StoreConfig(
    root_path=Path(".stream-store"),
    durability_mode=DurabilityMode.FSYNC,
    enable_indexes=True,
)
```

### `stream.DurabilityMode`

Enum controlling append durability behavior.

Values:

- `DurabilityMode.FLUSH`
- `DurabilityMode.FSYNC`

Operational meaning:

- `FLUSH` means buffered file content is flushed from Python to the OS
- `FSYNC` means a stronger durability step is requested

### `stream.LayoutMode`

Enum controlling store layout mode.

Values:

- `LayoutMode.JSONL_SEGMENTS`

At the moment, `Stream` exposes one public layout mode because the library is intentionally narrow around append-oriented JSONL segment storage.

## Result And Filter Models

These models are publicly exported through `stream` and `stream.models`.

### `stream.AppendReceipt`

Dataclass describing one accepted append.

Fields:

- `sequence`
- `segment_id`
- `offset`
- `record_ref`
- `record_type`
- `run_ref`
- `durability_status`

This model is returned inside `AppendResult.accepted`.

### `stream.AppendResult`

Dataclass describing the outcome of one append operation or batch append.

Fields:

- `accepted`
  - tuple of `AppendReceipt`
- `rejected`
  - tuple of rejection messages
- `durability_status`
  - aggregate durability status
- `durable_count`
  - count of records whose durability target was reached

Computed properties:

- `accepted_count`
- `rejected_count`
- `success`

Operational note:

- `success` means nothing was rejected
- `accepted_count` and `rejected_count` are the quickest way to inspect partial batch acceptance

### `stream.DurabilityStatus`

Enum describing the visibility of append durability for accepted records.

Values:

- `DurabilityStatus.ACCEPTED`
- `DurabilityStatus.FLUSHED`
- `DurabilityStatus.FSYNCED`

### `stream.ScanFilter`

Dataclass for common scan and replay filters.

Fields:

- `run_ref`
- `stage_execution_ref`
- `record_type`
- `start_time`
- `end_time`

Typical use:

```python
scan_filter = ScanFilter(
    run_ref="run/eval-1",
    record_type="metric",
)
```

### `stream.StoredRecord`

Dataclass describing one stored record plus placement metadata.

Fields:

- `sequence`
- `segment_id`
- `offset`
- `appended_at`
- `record`

This is the result model returned by `scan()` and `iter_replay()`.

### `stream.ReplayMode`

Enum controlling replay semantics.

Values:

- `ReplayMode.STRICT`
- `ReplayMode.TOLERANT`

Operational meaning:

- `STRICT` refuses corrupted-store replay
- `TOLERANT` allows damaged history to be read with explicit warnings and known gaps

### `stream.ReplayResult`

Dataclass describing replay output.

Fields:

- `records`
  - tuple of `StoredRecord`
- `record_count`
  - number of replayed records
- `mode`
  - replay mode used
- `warnings`
  - replay warnings
- `known_gaps`
  - explicit damaged-history gaps

Typical use:

```python
replay = store.replay(ScanFilter(run_ref="run/eval-1"), mode=ReplayMode.STRICT)
print(replay.record_count)
print(replay.warnings)
```

### `stream.IntegrityState`

Enum describing high-level store health.

Values:

- `IntegrityState.HEALTHY`
- `IntegrityState.DEGRADED`
- `IntegrityState.CORRUPTED`

### `stream.IntegrityIssue`

Dataclass describing one integrity finding.

Fields:

- `severity`
- `code`
- `message`
- `segment_id`
- `line_number`

### `stream.IntegrityReport`

Dataclass describing the result of `check_integrity()`.

Fields:

- `healthy`
- `issues`
- `segment_count`
- `record_count`
- `state`
- `recommendations`

Operational note:

- `healthy` is a top-level summary
- `state` is the higher-signal classification for operator decisions

### `stream.RepairReport`

Dataclass describing the outcome of `rebuild_indexes()` or `repair_truncated_tails()`.

Fields:

- `success`
- `repaired_segments`
- `quarantined_paths`
- `rebuilt_indexes`
- `integrity_state`
- `notes`
- `warnings`

This is intentionally used for both maintenance surfaces so operators can compare maintenance outcomes using one result shape.

## Typed Exceptions

These exceptions are publicly exported through `stream` and `stream.exceptions`.

### `stream.StreamError`

Base exception for `Stream`.

### `stream.LayoutError`

Raised when layout metadata or segment state is invalid.

### `stream.RecordValidationError`

Raised when an input record is not a valid canonical record.

Typical callers should expect this around `append()` and `append_many()`.

### `stream.AppendError`

Raised when append execution fails.

### `stream.ReplayError`

Raised when replay cannot proceed safely.

The most important current case is strict replay against a corrupted store.

### `stream.IntegrityError`

Raised when integrity processing fails unexpectedly.

## Minimal Import Patterns

Most callers only need one of these patterns.

Minimal store usage:

```python
from pathlib import Path

from stream import ScanFilter, StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))

for stored in store.scan(ScanFilter(run_ref="run/eval-1")):
    print(stored.sequence, stored.record["record_type"])
```

Replay-oriented usage:

```python
from stream import ReplayMode, ScanFilter

replay = store.replay(
    ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)
```

Integrity-oriented usage:

```python
from stream import StreamStore

report = store.check_integrity()
print(report.state)
print(report.recommendations)
```

## Which Page To Read Next

- Read [Getting Started](/Users/eastl/MLObservability/Stream/docs/en/getting-started.md) for the smallest end-to-end flow.
- Read [Write Path](/Users/eastl/MLObservability/Stream/docs/en/write-path.md) for append semantics and durability behavior.
- Read [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md) for scan, replay, and export semantics.
- Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) for maintenance and operator interpretation.
