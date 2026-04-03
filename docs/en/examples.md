# Examples

This page collects practical `Stream` examples and, just as importantly, explains which example to reach for first. The goal is not to replace the deeper write, read, and repair pages. The goal is to help you move from "I understand the concepts" to "I know which concrete flow matches the problem in front of me."

If the rest of the docs explain how `Stream` works, this page explains how to assemble those pieces into recognizable everyday scenarios.

## What This Page Helps You Choose

After reading this page, you should be able to decide:

- which example matches a new local store setup
- how to choose between append, scan, replay, and export in a real workflow
- when a small inline example is enough and when you should switch back to a concept page
- how to read example output without confusing helper state with canonical truth
- which examples are ordinary inspection flows and which ones are operational recovery flows

## Why `Stream` Needs Scenario Examples

At first glance, `Stream` can seem small enough that one basic example should be enough. In practice, the hard part is not usually "how do I call one method?" The hard part is "which method sequence matches the decision I need to make right now?"

That is why this page is organized by scenario rather than by API symbol.

The important point is that `Stream` usage tends to cluster into a few recurring patterns:

- start a local store and append canonical records
- inspect a subset of stored history during normal development
- replay canonical history with integrity-aware behavior
- export replayed history when another tool expects JSONL
- diagnose a damaged store without pretending the damage does not matter

Those are the patterns this page focuses on.

## How To Use This Page

Use this page in one of two ways:

- read from top to bottom if you are new to `Stream`
- jump to the scenario that matches the question you have right now

When an example starts to raise deeper questions such as "what exactly is canonical?" or "why did `strict` fail here?", follow the linked concept page rather than trying to learn everything from the example itself.

## Example Map

If you are not sure where to start, use this quick map:

- "I need the smallest end-to-end success path."
  - Start with `Example 1: One Record In, One Record Back Out`
- "I want to write a few records and inspect a run."
  - Go to `Example 2: Append A Small Run And Scan It`
- "I want an integrity-aware read instead of a plain scan."
  - Go to `Example 3: Replay A Run In Strict Mode`
- "Another tool needs JSONL output."
  - Go to `Example 4: Export Replayed History`
- "I suspect the store is damaged and I need to read carefully."
  - Go to `Example 5: Inspect Integrity Before Acting`
- "I need a repair-oriented operator flow."
  - Go to `Example 6: Rebuild First, Repair Only When Justified`

## Example 1: One Record In, One Record Back Out

This is the smallest example that still feels like real `Stream` usage.

Use it when:

- you are opening a local store for the first time
- you want to confirm the package imports correctly
- you want to see what one accepted append looks like on disk

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

stored = list(store.scan(ScanFilter(run_ref="run/eval-1")))
replay = store.replay(ScanFilter(run_ref="run/eval-1"), mode=ReplayMode.STRICT)

print(append_result.success)
print(append_result.accepted_count)
print(stored[0].sequence, stored[0].record["record_type"])
print(replay.record_count, replay.mode)
```

What to notice:

- `append()` returns structured acceptance information
- `scan()` returns stored records with placement metadata
- `replay()` adds an integrity-aware interpretation layer on top of reading

A typical mental model after this example should be:

- one canonical record was appended to a segment
- scan returned the stored record directly
- replay confirmed that strict interpretation was acceptable for that history

The corresponding on-disk shape usually starts to look like this:

```text
.stream-store/
  manifest.json
  segments/
    segment-000001.jsonl
  indexes/
    run_ref/
      run__eval-1.jsonl
```

This matters because the first successful example should already teach the trust split:

- `segments/` are canonical history
- `indexes/` are helpers
- `manifest.json` tracks store operating state

If this is the only example you run today, read [Getting Started](/Users/eastl/MLObservability/Stream/docs/en/getting-started.md) next.

## Example 2: Append A Small Run And Scan It

Once the first write succeeds, the next common question is usually: what does a slightly more realistic run look like?

Use this example when:

- you want to append more than one record
- you want to inspect a run through `scan()`
- you want to see how append order shows up during reads

```python
from pathlib import Path

from stream import ScanFilter, StoreConfig, StreamStore

store = StreamStore.open(StoreConfig(root_path=Path(".stream-store")))

records = [
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
    },
    {
        "record_ref": "record/eval-metric-1",
        "record_type": "metric",
        "recorded_at": "2026-04-03T00:10:05Z",
        "observed_at": "2026-04-03T00:10:05Z",
        "producer_ref": "scribe.python.local",
        "run_ref": "run/eval-1",
        "stage_execution_ref": "stage/evaluate",
        "operation_context_ref": "op/evaluate-open",
        "correlation_refs": {"trace_id": "trace/eval-1"},
        "completeness_marker": "complete",
        "degradation_marker": "none",
        "schema_version": "1.0.0",
        "payload": {
            "metric_key": "accuracy",
            "metric_value": 0.94,
        },
    },
]

append_result = store.append_many(records)

for stored in store.scan(ScanFilter(run_ref="run/eval-1")):
    print(stored.sequence, stored.offset, stored.record["record_type"])
```

What to notice:

- `append_many()` is still append-oriented, not a hidden rewrite operation
- accepted records still become individually ordered segment entries
- `scan()` preserves append order when returning matching records

In practice, this example is useful for checking whether your application is emitting canonical records with the run and stage references you expect.

A common mistake is to treat `scan()` like a semantic replay layer. It is not. `scan()` is for direct inspection of stored records that match a practical filter. If you need integrity-aware interpretation, switch to replay.

Read [Write Path](/Users/eastl/MLObservability/Stream/docs/en/write-path.md) if you want to understand append acceptance, batching, and durability in more detail.

## Example 3: Replay A Run In Strict Mode

This example is the next step once you no longer just want matching stored records. You want an interpretation of local history under replay rules.

Use it when:

- you want the store to apply integrity-aware replay semantics
- you want a default read mode for trustworthy local history
- you want a result that can later surface warnings or gaps explicitly

```python
from stream import ReplayMode, ScanFilter

replay = store.replay(
    ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)

print(replay.mode)
print(replay.record_count)
print(replay.warnings)
print(replay.known_gaps)
```

What to notice:

- strict replay is not just "scan with a different name"
- a successful strict replay means the requested history passed the store's integrity interpretation for that read
- replay returns a result model, not just raw stored records

In practice, `strict` should be the default operator mindset when you believe the store should be healthy.

This matters because strict replay is allowed to fail when the underlying history is not safe to normalize away. That is a protection mechanism, not an inconvenience.

If you find yourself asking why replay exists separately from scan, go back to [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md).

## Example 4: Export Replayed History

Sometimes the question is not "how do I inspect this in Python?" but "how do I hand coherent history to another tool?"

Use this example when:

- another tool expects line-oriented JSON
- you want to preserve replay semantics while exporting
- you want a convenient operational handoff format

```python
from pathlib import Path

from stream import ReplayMode, ScanFilter

output_path = Path("exports/run-eval-1.jsonl")

report = store.export_jsonl(
    output_path=output_path,
    scan_filter=ScanFilter(run_ref="run/eval-1"),
    mode=ReplayMode.STRICT,
)

print(report.record_count)
print(report.output_path)
```

What to notice:

- export builds on replay semantics rather than bypassing them
- the output is a convenience format, not a new source of truth
- if strict replay is not justified, export should not pretend otherwise

A common mistake is to think exported JSONL becomes the canonical history. It does not. The canonical history is still the ordered segment record history in the store.

Read [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md) if you need the exact relationship between replay and export.

## Example 5: Inspect Integrity Before Acting

This is the example to reach for when something feels off.

Use it when:

- replay begins failing unexpectedly
- you suspect truncation or other on-disk damage
- you want a diagnosis before choosing rebuild or repair

```python
integrity = store.check_integrity()

print(integrity.healthy)
print(integrity.state)

for issue in integrity.issues:
    print(issue.severity, issue.code, issue.segment_id, issue.line_number)

for recommendation in integrity.recommendations:
    print(recommendation)
```

What to notice:

- integrity is its own explicit operator surface
- `healthy` alone is not enough; `state`, `issues`, and `recommendations` matter
- this is the right place to learn what kind of problem you have before touching the store

In practice, the first useful question is rarely "how do I fix this?" The first useful question is "what kind of damage am I actually looking at?"

That is why integrity inspection comes before rebuild and repair.

Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) after this example.

## Example 6: Rebuild First, Repair Only When Justified

This is the most operational example on the page.

Use it when:

- an integrity report suggests helper-state drift
- you want to rebuild derivative indexes safely
- you are considering repair and need to be deliberate about it

```python
rebuild_report = store.rebuild_indexes()
print(rebuild_report.success)
print(rebuild_report.integrity_state)
print(rebuild_report.warnings)

repair_report = store.repair()
print(repair_report.success)
print(repair_report.actions_taken)
print(repair_report.quarantined_paths)
```

What to notice:

- rebuild and repair are not interchangeable
- rebuild is about derivative helper state
- repair is a canonical operation that should only happen when the store knows how to make a limited, explicit correction

The important point is that rebuild is the ordinary first maintenance step when indexes drift, while repair should feel more serious because it touches the operator's interpretation of canonical history.

A common mistake is to treat repair as harmless cleanup. In `Stream`, that is the wrong mindset.

Read [Layout and Storage](/Users/eastl/MLObservability/Stream/docs/en/layout-and-storage.md) and [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) before relying on this flow in production.

## Example 7: Start From The Bundled Basic Example

If you prefer to begin with a checked-in file instead of copying snippets out of the docs, start here.

The bundled example lives at [examples/basic_usage.py](/Users/eastl/MLObservability/Stream/examples/basic_usage.py).

It shows a deliberately small workflow:

- open a local store
- append one canonical record
- scan by `run_ref`
- print the stored results

That makes it a good fit for:

- verifying that your environment imports `stream`
- seeing one small canonical record shape in code
- confirming what a basic scan flow feels like

After running it, move to:

- [Getting Started](/Users/eastl/MLObservability/Stream/docs/en/getting-started.md) if you want the fuller walkthrough
- [Write Path](/Users/eastl/MLObservability/Stream/docs/en/write-path.md) if you want append semantics
- [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md) if you want replay and export semantics

## Common Example Mistakes

Several mistakes show up repeatedly when people first adapt these snippets:

- treating arbitrary JSON as appendable canonical records
- assuming `append_many()` is automatically all-or-nothing
- using `scan()` when the real question is replay safety
- treating exported JSONL as canonical storage
- jumping to `repair()` before reading the integrity report
- treating `indexes/` as source of truth during debugging

If one of the examples feels surprising, the most likely cause is not that the method is strange. The more likely cause is that `Stream` is being approached with a looser event-log mental model than the library actually supports.

## Which Page To Read Next

Use this quick guide after the examples:

- if append acceptance or batching feels unclear, read [Write Path](/Users/eastl/MLObservability/Stream/docs/en/write-path.md)
- if `scan`, `replay`, or `export_jsonl()` boundaries feel unclear, read [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md)
- if you want to understand what is canonical on disk, read [Layout and Storage](/Users/eastl/MLObservability/Stream/docs/en/layout-and-storage.md)
- if you are diagnosing damage, read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md)
- if you want the smallest full walkthrough again, read [Getting Started](/Users/eastl/MLObservability/Stream/docs/en/getting-started.md)

The important point is that examples should speed up recognition, not replace the deeper mental model. In `Stream`, correct operational interpretation still matters more than memorizing one happy-path snippet.
