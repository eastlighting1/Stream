# Getting Started

This page helps you answer one practical question first: how do you get one local `StreamStore` working end-to-end in a real Python session? The goal is not to explain every storage detail yet. The goal is to make one append-read flow succeed, show what gets written on disk, explain what the results mean, and establish the first few habits that make later repair and replay work feel natural instead of mysterious.

If you only read one page before trying the library, this should be that page.

## What This Page Helps You Do

After reading this page, you should be able to:

- create a local `StreamStore`
- append one canonical record successfully
- append multiple records and interpret partial acceptance
- scan the stored history back out
- replay that history in a way that matches store integrity
- export replayed history when another tool needs JSONL
- run the equivalent CLI commands
- recognize which on-disk files are canonical and which are only helpers

## Why Start Here

At first glance, `Stream` can look like a generic event log with a few convenience methods. In practice, that mental model is too loose. `Stream` is specifically the append-oriented canonical record store of the stack. The important point is that the segment history is the source of truth, while helper indexes are derivative and rebuildable.

This matters because the first successful workflow should teach the right habits immediately:

- append canonical records, not arbitrary debug blobs
- pay attention to append results instead of assuming writes are all-or-nothing
- read through `scan` or `replay` depending on what question you are asking
- treat `segments/` as authoritative
- treat `indexes/` as helpers
- treat integrity checks as ordinary store operations, not just emergency procedures

If that mental model lands early, later pages about damaged stores, tolerant replay, and repair become much easier to reason about.

## Before You Start

This page assumes you have a Python environment where the `stream` package is importable.

The examples use:

- a local store rooted at `.stream-store`
- one `structured_event` record family
- `run_ref="run/eval-1"` as the practical scan key

You do not need a running service, database, or remote backend. `Stream` is local-first by design.

## The Smallest Successful Flow

The smallest useful flow is:

1. Create a store rooted at a local directory.
2. Append one valid canonical record.
3. Scan the store using a practical filter.
4. Replay the same history through the replay path.

```python
from pathlib import Path

from stream import ReplayMode, ScanFilter, StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))

append_result = store.append(
    {
        "record_ref": "record/eval-start",
        "record_type": "structured_event",
        "recorded_at": "2026-04-03T00:10:00Z",
        "observed_at": "2026-04-03T00:10:00Z",
        "producer_ref": "scribe.python.local",
        "run_ref": "run/eval-1",
        "stage_execution_ref": "stage/evaluate",
        "operation_context_ref": "op/evaluate-open",
        "correlation_refs": {"trace_id": "trace/eval-1"},
        "completeness_marker": "complete",
        "degradation_marker": "none",
        "schema_version": "1.0.0",
        "payload": {
            "event_key": "evaluation.started",
            "level": "info",
            "message": "Evaluation started.",
        },
    }
)

print(append_result.success)
print(append_result.accepted_count)
print(append_result.accepted[0].durability_status)

records = list(store.scan(ScanFilter(run_ref="run/eval-1")))
print(records[0].sequence, records[0].record["record_type"])

replay = store.replay(ScanFilter(run_ref="run/eval-1"), mode=ReplayMode.STRICT)
print(replay.record_count, replay.mode)
```

One successful run already teaches most of the runtime shape:

- `append()` returns structured append metadata, not just `True` or `False`
- `scan()` returns stored records in append order
- `replay()` returns a replay result that can surface warnings and known gaps later
- the store can be inspected directly on disk after the write

## Step 1: Open A Store

Creating a `StreamStore` is intentionally simple:

```python
from pathlib import Path

from stream import StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))
```

That one line sets the local root of the store and initializes the inspectable layout if it does not exist yet.

In practice, this means:

- the root directory will be created
- a `segments/` directory will be created
- `manifest.json` will be initialized if missing
- helper indexes will be enabled unless you configure otherwise

The important point is that opening the store is not just creating an object in memory. It is also declaring where canonical history will live on disk.

## Step 2: Append A Canonical Record

The first write should be a valid canonical record. This is worth being explicit about because `Stream` is not a free-form JSON bucket.

```python
append_result = store.append(
    {
        "record_ref": "record/eval-start",
        "record_type": "structured_event",
        "recorded_at": "2026-04-03T00:10:00Z",
        "observed_at": "2026-04-03T00:10:00Z",
        "producer_ref": "scribe.python.local",
        "run_ref": "run/eval-1",
        "stage_execution_ref": "stage/evaluate",
        "operation_context_ref": "op/evaluate-open",
        "correlation_refs": {"trace_id": "trace/eval-1"},
        "completeness_marker": "complete",
        "degradation_marker": "none",
        "schema_version": "1.0.0",
        "payload": {
            "event_key": "evaluation.started",
            "level": "info",
            "message": "Evaluation started.",
        },
    }
)
```

This succeeds only if the record satisfies the expected canonical shape. That includes:

- required envelope fields
- normalized timestamps
- a supported schema version
- a payload structure that matches the record type

In other words, `Stream` is not deciding whether your data is merely serializable. It is deciding whether the record is acceptable canonical history.

## Step 3: Read The Append Result Carefully

A common first mistake is to call `append()` and then ignore the return value. Do not do that.

For a healthy one-record store, the result usually looks conceptually like this:

```text
append_result.success == True
append_result.accepted_count == 1
append_result.rejected_count == 0
append_result.accepted[0].durability_status == "flushed" or "fsynced"
append_result.accepted[0].sequence == 1
append_result.accepted[0].segment_id == 1
append_result.accepted[0].offset == 1
```

The important point is that append tells you more than "the write worked":

- `success` tells you whether the batch had any rejections
- `accepted_count` and `rejected_count` tell you whether the result was partial
- `durability_status` tells you how far the write reached on disk before the method returned
- `sequence`, `segment_id`, and `offset` tell you where the record landed in canonical history

That metadata becomes much more useful once your store holds more than one line of history.

## Step 4: Scan The Stored History

Once the record exists, you can inspect it with `scan()`:

```python
records = list(store.scan(ScanFilter(run_ref="run/eval-1")))

for stored in records:
    print(stored.sequence, stored.record["record_type"], stored.record["payload"])
```

`scan()` is the straightforward read path. It is usually the right default when you want:

- ordinary local inspection
- filtering by run, stage, record type, or time window
- stored records directly, without replay semantics layered on top

The key idea is that `scan()` answers a practical retrieval question: what stored records match this filter?

## Step 5: Replay The Same History

Now read the same history through `replay()`:

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

For a healthy store, the replay result usually looks conceptually like this:

```text
replay.record_count == 1
replay.mode == "strict"
replay.warnings == ()
replay.known_gaps == ()
```

At first glance, `scan()` and `replay()` can look redundant because both return stored records. In practice, they answer slightly different questions:

- `scan()` asks what is stored
- `replay()` asks what history can be safely interpreted under a chosen replay mode

That difference does not matter much in a healthy one-record example. It matters a great deal once corruption enters the picture.

## Step 6: Try A Small Batch Append

`Stream` is append-oriented, so it is useful to see a small batch early instead of assuming every write will be single-record.

```python
batch_result = store.append_many(
    [
        {
            "record_ref": "record/eval-metric-1",
            "record_type": "metric",
            "recorded_at": "2026-04-03T00:10:01Z",
            "observed_at": "2026-04-03T00:10:01Z",
            "producer_ref": "scribe.python.local",
            "run_ref": "run/eval-1",
            "stage_execution_ref": "stage/evaluate",
            "operation_context_ref": "op/evaluate-metric-1",
            "correlation_refs": {"trace_id": "trace/eval-1"},
            "completeness_marker": "complete",
            "degradation_marker": "none",
            "schema_version": "1.0.0",
            "payload": {
                "metric_key": "evaluation.loss",
                "value": 0.42,
                "value_type": "scalar",
                "aggregation_scope": "step",
                "tags": {"split": "validation"},
            },
        },
        {
            "record_type": "metric",
            "payload": {},
        },
    ]
)

print(batch_result.accepted_count)
print(batch_result.rejected_count)
print(batch_result.rejected)
```

This matters because `append_many()` is not all-or-nothing. A batch can accept valid records and reject invalid ones in the same call.

## What You Should Expect Back Overall

After a healthy first run, you should expect three different kinds of information from the library:

- append results tell you acceptance, durability, and placement
- stored records tell you what canonical lines exist
- replay results tell you how history was interpreted

The important point is that append, scan, and replay are deliberately different surfaces because they support different operational decisions.

## What Gets Written On Disk

After the first append, the store directory will look roughly like this:

```text
.stream-store/
  manifest.json
  segments/
    segment-000001.jsonl
  indexes/
    run_ref/
      run__eval-1.jsonl
    stage_execution_ref/
      stage__evaluate.jsonl
    record_type/
      structured_event.jsonl
```

The first canonical segment entry will look roughly like this:

```json
{
  "sequence": 1,
  "appended_at": "2026-04-03T00:10:00Z",
  "record": {
    "record_ref": "record/eval-start",
    "record_type": "structured_event",
    "recorded_at": "2026-04-03T00:10:00Z",
    "observed_at": "2026-04-03T00:10:00Z",
    "producer_ref": "scribe.python.local",
    "run_ref": "run/eval-1",
    "stage_execution_ref": "stage/evaluate",
    "operation_context_ref": "op/evaluate-open",
    "correlation_refs": {
      "trace_id": "trace/eval-1"
    },
    "completeness_marker": "complete",
    "degradation_marker": "none",
    "schema_version": "1.0.0",
    "payload": {
      "event_key": "evaluation.started",
      "level": "info",
      "message": "Evaluation started."
    }
  }
}
```

And `manifest.json` will start tracking append progress:

```json
{
  "layout_mode": "jsonl_segments",
  "layout_version": "1",
  "current_segment_id": 1,
  "next_sequence": 2,
  "last_committed_sequence": 1,
  "current_segment_record_count": 1
}
```

This matters because it shows the trust boundary clearly:

- `segments/` hold canonical append history
- `manifest.json` tracks append progress and current layout state
- `indexes/` help practical scans but are not authoritative

## The Equivalent CLI Flow

The same first workflow should also feel simple from the CLI.

Scan the local store:

```powershell
stream-cli --store .stream-store scan --run-ref run/eval-1
```

Replay the same history:

```powershell
stream-cli --store .stream-store replay --run-ref run/eval-1 --mode strict
```

Run a quick integrity check:

```powershell
stream-cli --store .stream-store integrity
```

Export replayed history to JSONL:

```powershell
stream-cli --store .stream-store export --run-ref run/eval-1 --output exports/eval.jsonl
```

In a healthy store, the integrity output will look conceptually like this:

```json
{
  "healthy": true,
  "state": "healthy",
  "segment_count": 1,
  "record_count": 1,
  "issues": [],
  "recommendations": []
}
```

## How To Think About `scan` Versus `replay`

At first glance, `scan` and `replay` look very similar because both return stored records. In practice, they answer slightly different questions.

Use `scan` when:

- you want stored records directly
- you are filtering by run, stage, record type, or time
- you are doing ordinary local inspection
- you want the simplest possible read path

Use `replay` when:

- you want an integrity-aware read path
- you need `strict` versus `tolerant` semantics
- you want warnings and known-gap reporting when the store is damaged
- you want to make an explicit statement about how much damage you are willing to tolerate

## How To Think About `strict` Versus `tolerant`

Even in a getting-started page, it helps to establish this difference early.

- `strict` prioritizes safety over convenience
- `tolerant` prioritizes usable partial history with explicit warnings

The important point is that `tolerant` is not "better because it returns more." It is simply a different tradeoff.

## Common Mistakes In A First Setup

### Treating `Stream` Like A Generic JSON Bucket

A common mistake is to assume any JSON payload can be appended as long as it looks event-like. `Stream` expects canonical records that satisfy the contract shape used by the stack.

### Treating Indexes As Source Of Truth

It is tempting to inspect `indexes/` first and assume they are authoritative because they are easy to read. They are not. Indexes are rebuildable helper files. The canonical history lives in `segments/*.jsonl`.

### Assuming `strict` Replay Is Just A More Picky Read

`strict` replay is not a cosmetic mode. It is a safety boundary. If the store is corrupted, `strict` replay refuses to continue.

### Ignoring Partial Batch Results

Another common mistake is to treat `append_many()` like a transactional all-or-nothing call. It is not. You need to read the result object and see whether the batch accepted only part of the input.

## Why This Matters Operationally

Even this first walkthrough establishes the key operational habits:

- append results should be interpreted, not ignored
- replay mode should be chosen deliberately
- on-disk helper files should not be mistaken for canonical truth
- integrity checks are part of ordinary store usage, not only emergency recovery
- export should be thought of as a read-side convenience, not a new truth source

## A Good First Session Checklist

If you want a practical self-check after finishing this page, confirm that you can do all of the following in one short session:

1. open a fresh local store
2. append one valid canonical record
3. inspect the append result fields
4. scan the record back by `run_ref`
5. replay the same record in `strict` mode
6. open `manifest.json` and the first segment on disk
7. run `stream-cli integrity`
8. export replayed history to a JSONL file

## What To Read Next

Read [Mental Model](mental-model.md) next if you want the storage boundary, trust model, and role of `Stream` to feel precise.

Read [Read Path](read-path.md) next if you want a deeper explanation of `scan`, `replay`, tolerant reads, and export behavior.

Read [Write Path](write-path.md) next if you want to understand record acceptance, batching, durability, and append behavior in more detail.
