# Read Path

This page explains how `Stream` reads stored history back out, why `scan` and `replay` are not the same thing, when helper indexes can speed up reads, and how to interpret `strict`, `tolerant`, warnings, known gaps, and export behavior without crossing the store's trust boundary.

If the write path explains how canonical history gets in, the read path explains how that history should be interpreted once it is on disk.

## What This Page Helps You Decide

After reading this page, you should be able to answer these questions clearly:

- when to use `scan()` and when to use `replay()`
- when a scan can use helper indexes and when it cannot
- what `strict` and `tolerant` replay actually mean
- what `warnings` and `known_gaps` are telling you
- how `export_jsonl()` relates to replay rather than redefining truth
- why a successful read is not always the same thing as a safe interpretation

## Why The Read Path Deserves Its Own Page

At first glance, reading from `Stream` can look straightforward: you ask for records, and the store returns records. In practice, the read path is where `Stream` turns stored canonical history into operator decisions.

That is why the read path needs more than one surface:

- `scan()` for direct inspection
- `replay()` for integrity-aware history interpretation
- `export_jsonl()` for downstream JSONL output built on replay semantics

The important point is that reading is not only retrieval. It is also interpretation.

## The One-Sentence Read Model

`Stream` reads canonical history either by scanning stored records directly or by replaying them under explicit integrity semantics, optionally using derivative indexes to narrow practical scans without changing the canonical source of truth.

That sentence contains the whole read-side philosophy:

- canonical history still lives in segments
- helper indexes can help locate relevant lines
- replay adds safety semantics on top of retrieval

## The Three Main Read Surfaces

`Stream` exposes three closely related but distinct read-side surfaces:

1. `scan()`
2. `replay()`
3. `export_jsonl()`

These are related, but they do not mean the same thing.

### `scan()`

Use `scan()` when you want stored records directly.

### `replay()`

Use `replay()` when you want a read that explicitly accounts for store integrity and replay mode.

### `export_jsonl()`

Use `export_jsonl()` when another tool needs replayed history in line-oriented JSON output.

The important point is that export is built on replay rather than bypassing it.

## What `scan()` Does

`scan()` is the direct stored-record inspection path.

In practice, it:

- walks segment history in append order
- applies the requested `ScanFilter`
- returns `StoredRecord` values
- may use helper indexes in some simple cases

A simple example looks like this:

```python
from stream import ScanFilter

records = list(store.scan(ScanFilter(run_ref="run/eval-1")))

for stored in records:
    print(
        stored.sequence,
        stored.segment_id,
        stored.offset,
        stored.record["record_type"],
    )
```

This matters because `scan()` is intentionally boring in the best way. It is the read path you use when you want to ask, "what stored records match this filter?"

## What A `StoredRecord` Represents

A `StoredRecord` is not just the original record mapping. It contains both:

- canonical record data
- append-side placement metadata

That means each `StoredRecord` includes:

- `sequence`
- `segment_id`
- `offset`
- `appended_at`
- `record`

This is important because reads in `Stream` preserve the distinction between:

- what the record says
- where and when it entered local canonical history

That distinction becomes crucial for replay interpretation and later operational debugging.

## What `ScanFilter` Is Really Doing

`ScanFilter` is the practical read-side filter object for common inspection patterns.

It can filter by:

- `run_ref`
- `stage_execution_ref`
- `record_type`
- `start_time`
- `end_time`

At first glance, this can look like a small convenience wrapper. In practice, it captures the library's opinionated read shape: `Stream` is optimized for practical local history inspection, not for arbitrary relational querying.

## What `scan()` Does Not Do

It is just as important to understand what `scan()` does not promise.

`scan()` does not:

- automatically certify that the store is healthy
- attach replay warnings and known gaps
- reinterpret corruption as partial history in the way replay does
- elevate helper indexes into source-of-truth status

This matters because a clean-looking `scan()` result should never be read as proof that the store is globally healthy.

## When `scan()` Can Use Helper Indexes

One of the most useful read-path details is that `scan()` can consult helper indexes when the filter is simple enough.

In practice, index-assisted scan is available when:

- there is no time window filter
- exactly one indexed family is populated

That means a filter like this can use an index:

```python
ScanFilter(record_type="metric")
```

and a filter like this can use an index:

```python
ScanFilter(run_ref="run/eval-1")
```

but a filter like this cannot:

```python
ScanFilter(run_ref="run/eval-1", record_type="metric")
```

and a filter with time boundaries cannot either:

```python
ScanFilter(run_ref="run/eval-1", start_time="2026-04-03T00:00:00Z")
```

The important point is that helper indexes are used for practical narrowing, not for redefining the truth source.

## Why Indexed Scan Does Not Break The Trust Boundary

At first glance, using an index in the read path may look like treating the index as authoritative. That is not what happens.

The index contributes:

- candidate `(segment_id, offset)` pointers

The segment still contributes:

- the actual canonical line content

So the read path remains grounded in canonical segments even when a derivative index makes the lookup more efficient.

That distinction is one of the healthiest parts of the design.

## What `replay()` Does

`replay()` reads stored history under an explicit replay mode.

A simple example looks like this:

```python
from stream import ReplayMode, ScanFilter

replay = store.replay(
    ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)

print(replay.record_count)
print(replay.mode)
print(replay.warnings)
print(replay.known_gaps)
```

Unlike `scan()`, `replay()` is not merely returning matching stored records. It is also making a statement about how integrity should affect your ability to interpret that history.

## Why `replay()` Exists When `scan()` Already Exists

This is one of the biggest conceptual points in the read path.

At first glance, `scan()` and `replay()` can look redundant because both return records. In practice, they answer different questions:

- `scan()` asks, "what stored records match this filter?"
- `replay()` asks, "what history can be safely interpreted under this replay mode?"

That means replay is where safety semantics become explicit.

If you keep this distinction in mind, later damaged-store behavior feels coherent rather than surprising.

## `strict` Replay

`strict` replay is the conservative read path.

In practice, `strict` replay means:

- check store integrity first
- if the store is corrupted, stop instead of proceeding
- do not interpret damaged history as if it were whole

This matters because `strict` is not a "more picky convenience setting." It is a safety boundary.

When `strict` replay fails, that failure is often the right operational outcome.

## `tolerant` Replay

`tolerant` replay is the damage-aware read path.

In practice, `tolerant` replay means:

- check store integrity first
- keep reading what can still be interpreted
- skip unreadable lines when necessary
- return warnings and known gaps so the caller knows the history is incomplete

This matters because `tolerant` is not pretending the store is healthy. It is acknowledging damage explicitly while still extracting usable partial history.

## What `ReplayResult` Tells You

`ReplayResult` is a richer object than a plain list of stored records.

It includes:

- `records`
- `record_count`
- `mode`
- `warnings`
- `known_gaps`

The important point is that `ReplayResult` combines retrieval with integrity interpretation.

### `records`

These are the replayed `StoredRecord` values.

### `record_count`

This tells you how many records were replayed under the chosen mode.

### `mode`

This tells you whether the read was performed under `strict` or `tolerant` semantics.

### `warnings`

In tolerant replay, `warnings` summarize integrity issues that should affect how you interpret the returned history.

### `known_gaps`

In tolerant replay, `known_gaps` give machine-readable-ish descriptions of integrity errors that left holes in the readable history.

## What `warnings` Mean

Warnings are not generic advisory strings. They are telling you that the returned history should be interpreted with caution.

In practice, warnings may reflect:

- invalid JSON lines
- truncated tails
- sequence gaps
- manifest drift

The important point is that warnings belong to interpretation, not just logging.

If your caller ignores replay warnings, it is choosing convenience over explicit safety.

## What `known_gaps` Mean

Known gaps are one of the most important outputs of tolerant replay.

They exist because `tolerant` mode is not trying to hide the fact that some history became unsafe or unreadable. Instead, it says:

- these records were replayed
- these damaged locations were not

That means a tolerant replay result is useful precisely because it admits incompleteness.

This matters operationally because downstream tools may still be able to inspect partial history usefully as long as they do not confuse it with complete truth.

## Why Replay Checks Integrity First

The replay path intentionally runs integrity checks before deciding how to continue.

That is important because replay is not just "read whatever lines you can." It is "read history in a way that matches the store's integrity state."

In practice:

- `strict` replay refuses to proceed on a corrupted store
- `tolerant` replay continues, but only with explicit warnings and known gaps

This is one of the clearest examples of `Stream` choosing explicit safety over silent convenience.

## What Happens On Corruption

It helps to think through the damaged-store read path explicitly.

### If You Call `scan()`

`scan()` may still return matching records, but it is not the primary safety surface.

If corruption appears in the path being read:

- ordinary scan may encounter unreadable lines
- if corruption tolerance is not enabled in that context, the read may raise
- the result does not include replay semantics

### If You Call `replay(mode="strict")`

The replay fails early if the store is classified as corrupted.

### If You Call `replay(mode="tolerant")`

The replay attempts to continue and returns:

- the records that can still be interpreted
- warnings describing the integrity concerns
- known gaps describing where the damage was observed

This matters because the read path is intentionally explicit about damage instead of trying to hide it behind a best-effort read that looks healthy.

## What `iter_replay()` Is For

`iter_replay()` exists for the same conceptual read path as `replay()`, but it yields records as an iterator instead of building the final tuple first.

Use it when:

- you want replay semantics
- you want incremental consumption
- you do not need the fully materialized replay result immediately

The mental model is still the same: replay semantics first, iteration style second.

## What `export_jsonl()` Does

`export_jsonl()` is a read-side convenience built on replay.

A simple example looks like this:

```python
from pathlib import Path

from stream import ReplayMode, ScanFilter

result = store.export_jsonl(
    Path("exports/eval.jsonl"),
    ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)

print(result.record_count)
```

The important point is that export does not invent a new interpretation layer. It:

1. performs replay under the chosen mode
2. writes the replayed record payloads as JSONL
3. returns the same replay result so the caller can still inspect interpretation metadata

This matters because exported JSONL is a convenience output, not a new canonical truth source.

## Why Export Lives On The Read Side

It may be tempting to think of export as its own storage concern. In `Stream`, it is better to see it as a read-path extension.

That is because export:

- depends on replay semantics
- does not create authoritative new history
- exists to hand already interpreted history to another tool

Once you see export this way, it becomes clear why replay warnings still matter before export.

## A Healthy Read Example

A healthy read session usually looks like this:

```python
records = list(store.scan(ScanFilter(record_type="metric")))
replay = store.replay(ScanFilter(record_type="metric"), mode=ReplayMode.STRICT)

print(len(records))
print(replay.record_count)
print(replay.warnings)
```

In a healthy store:

- the scan count and replay count may match
- warnings are empty
- known gaps are empty
- strict replay succeeds

This does not mean `scan()` and `replay()` are interchangeable. It means they happen to agree under healthy conditions.

## A Tolerant Read Example

A tolerant read session conceptually looks like this:

```python
replay = store.replay(mode=ReplayMode.TOLERANT)

print(replay.record_count)
print(replay.warnings)
print(replay.known_gaps)
```

In a damaged store, this may produce:

```text
record_count == 17
warnings == ("last segment line looks truncated or partially written", ...)
known_gaps == ("truncated_line@segment=3:line=42", ...)
```

The important point is that the result is still useful, but only if you keep the warnings attached to your interpretation.

## Common Mistakes On The Read Path

### Treating `scan()` And `replay()` As Interchangeable

They can return the same records in healthy cases, but they exist for different decisions.

### Ignoring Replay Warnings

Warnings are not noise. They are a statement that the returned history should not be read as fully healthy.

### Treating `tolerant` As A Better Default

`tolerant` is not a more capable `strict`. It is a different tradeoff that accepts explicit incompleteness.

### Assuming Indexed Scan Means The Index Is Canonical

Indexed scan uses the index to narrow the search, then still reads segment lines as truth.

### Treating Exported JSONL As New Truth

Exported files are downstream convenience artifacts. They are not a replacement for the canonical segment history.

## Operational Meaning Of A Successful Read

A successful read can mean different things depending on the surface.

### Successful `scan()`

This means matching records were read successfully. It does not certify global integrity.

### Successful `strict` Replay

This means the store's integrity state allowed strict interpretation for that replay.

### Successful `tolerant` Replay

This means usable partial history was returned, not that the store was healthy.

That distinction matters because the same word, "success," can hide very different operational meanings if you collapse these surfaces together.

## A Good Read-Side Checklist

Before moving on, it is worth checking that your read-side mental model now includes all of the following:

1. `scan()` is the direct inspection path
2. `replay()` is the integrity-aware interpretation path
3. indexed scan improves convenience without changing truth ownership
4. `strict` failure on corruption is often the right outcome
5. `tolerant` replay is useful because it keeps warnings and known gaps explicit
6. export is built on replay rather than bypassing it

## What To Read Next

Read [Layout and Storage](layout-and-storage.md) next if you want to see how these read paths map onto `manifest.json`, segment files, and derivative indexes on disk.

Read [Integrity and Repair](integrity-and-repair.md) next if you want to understand how corruption, rebuilds, and repair decisions affect later replay behavior.

Read [CLI Reference](/Users/eastl/MLObservability/Stream/docs/en/cli-reference.md) next if you want exact command-line shapes for scan, replay, export, and integrity inspection.
