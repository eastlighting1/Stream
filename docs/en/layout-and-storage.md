# Layout and Storage

This page explains how `Stream` is laid out on disk, what each file family means, which parts of the layout are canonical versus derivative, and how operators should interpret manifest state, segment files, helper indexes, sequence numbers, offsets, segment rollover, rebuild behavior, and repair behavior.

If `Mental Model` defines the trust boundary conceptually, this page shows exactly where that boundary lives in the filesystem.

## What This Page Helps You Decide

After reading this page, you should be able to answer these questions clearly:

- what the default store layout looks like on disk
- what `manifest.json` is responsible for and what it is not responsible for
- what `segments/` contain and why they are canonical
- what `indexes/` contain and why they are derivative
- what `sequence`, `segment_id`, and `offset` mean in storage terms
- how segment rollover works
- what changes during rebuild and repair operations
- which files you should trust first when debugging a local store

## Why Layout Deserves Its Own Page

At first glance, `Stream` storage can look simple: a few JSON files under one local root. In practice, the layout is where the store's philosophy becomes visible:

- canonical history should be inspectable
- append progress should be explicit
- helper state should be rebuildable
- corruption should be diagnosable from local files

That means the on-disk shape is not incidental packaging. It is part of how the library stays understandable during both healthy operation and damage recovery.

## The One-Sentence Storage Model

`Stream` stores canonical append history in JSONL segment files, tracks write-frontier state in a manifest, and keeps practical scan pointers in derivative JSONL indexes that can be rebuilt from the canonical segments.

Everything on disk makes more sense once that sentence feels natural.

## The Default Store Layout

A healthy local store rooted at `.stream-store` will look roughly like this:

```text
.stream-store/
  manifest.json
  segments/
    segment-000001.jsonl
    segment-000002.jsonl
  indexes/
    run_ref/
      run__eval-1.jsonl
    stage_execution_ref/
      stage__evaluate.jsonl
    record_type/
      structured_event.jsonl
      metric.jsonl
```

In some cases you may also see:

```text
.stream-store/
  quarantine/
    segment-000003.jsonl
```

The `quarantine/` directory appears when repair needs to preserve a pre-trim copy of a damaged segment before rewriting the canonical file.

## The Top-Level Structure

At the top level, the store is intentionally split into a few clearly different responsibilities.

### `manifest.json`

The manifest tracks append frontier and layout state.

### `segments/`

Segments hold canonical append history.

### `indexes/`

Indexes hold derivative pointers used to accelerate common scans.

### `quarantine/`

Quarantine holds preserved copies of damaged segments before specific repair operations.

That split is important because it mirrors the trust split:

- segments are truth
- manifest coordinates current write progress
- indexes are helpers
- quarantine is a repair-side safety artifact

## Why The Layout Is Inspectable

`Stream` intentionally uses a layout that can be read with ordinary local tools.

That means:

- you can open a segment with a text editor
- you can inspect manifest drift without a custom debugger
- you can tell whether indexes exist or not just by looking at the directory tree
- you can explain repair decisions in terms of concrete files

This matters because local observability storage is hardest to trust when it becomes opaque. `Stream` chooses inspectability as part of its safety model.

## What `manifest.json` Is

`manifest.json` is the store's local operating-state file.

A healthy manifest may look like this:

```json
{
  "layout_mode": "jsonl_segments",
  "layout_version": "1",
  "current_segment_id": 2,
  "next_sequence": 48,
  "last_committed_sequence": 47,
  "current_segment_record_count": 19
}
```

The manifest answers questions such as:

- what layout mode is this store using
- what layout version is this store using
- which segment is currently active for append
- which sequence should be assigned next
- which sequence was most recently committed
- how many records the current segment currently holds

The important point is that `manifest.json` helps the store continue appending predictably. It does not replace canonical history.

## What `manifest.json` Is Not

The manifest is not:

- the primary record store
- a substitute for segment inspection
- a complete representation of canonical history
- a guarantee that the underlying segments are healthy

This matters because one of the easiest mistakes in local storage debugging is to treat the manifest as if it were the whole truth. It is not. It is a compact description of append frontier state.

## Manifest Fields And What They Mean

### `layout_mode`

This tells you the layout strategy being used. Right now the important expected value is `jsonl_segments`.

### `layout_version`

This tells you the current layout version. It matters when reasoning about compatibility and future layout evolution.

### `current_segment_id`

This tells you which segment the store believes is the active append target.

### `next_sequence`

This tells you which sequence number the next accepted record should receive.

### `last_committed_sequence`

This tells you the most recent sequence that the store recorded as committed.

### `current_segment_record_count`

This tells you how many records the current segment currently contains according to manifest state.

Together these values tell the append path where it thinks it is. They do not define what history actually exists. The segments do that.

## When Manifest Mismatch Matters

One of the useful things about `manifest.json` is that it can disagree with observed segment history.

That disagreement is not just bookkeeping noise. It is an operational signal.

For example, a mismatch may suggest:

- an interrupted write path
- a damaged manifest
- repaired or trimmed canonical history that required recomputation
- drift between append frontier tracking and observed segment contents

This matters because a manifest mismatch is one of the clearest examples of why manifest and segment history must be interpreted together rather than independently.

## What Lives In `segments/`

The `segments/` directory is the canonical append store.

Each segment file is line-oriented JSONL, and each non-blank line represents one accepted append entry. A segment entry contains:

- a canonical `sequence`
- the store-generated `appended_at` timestamp
- the canonical `record` payload

A conceptual example looks like this:

```json
{
  "sequence": 47,
  "appended_at": "2026-04-03T00:10:15Z",
  "record": {
    "record_ref": "record/eval-metric-2",
    "record_type": "metric",
    "recorded_at": "2026-04-03T00:10:15Z",
    "observed_at": "2026-04-03T00:10:15Z",
    "producer_ref": "scribe.python.local",
    "run_ref": "run/eval-1",
    "stage_execution_ref": "stage/evaluate",
    "operation_context_ref": "op/evaluate-metric-2",
    "correlation_refs": {
      "trace_id": "trace/eval-1"
    },
    "completeness_marker": "complete",
    "degradation_marker": "none",
    "schema_version": "1.0.0",
    "payload": {
      "metric_key": "evaluation.loss",
      "value": 0.39,
      "value_type": "scalar",
      "aggregation_scope": "step",
      "tags": {
        "split": "validation"
      }
    }
  }
}
```

The important point is that this line is the canonical fact of local acceptance. Everything else in the store is downstream of it.

## Why Segments Are Canonical

Segments are canonical because they preserve:

- the accepted record payload
- the accepted append order
- the durable local history that later reads and replays interpret

If an index says one thing and a segment line says another, the segment line wins.

If a manifest says the next sequence should be `48` but the segment history shows otherwise, the segment history is still the closer representation of truth.

That asymmetry is intentional.

## Segment Naming And Ordering

Segments use names like:

- `segment-000001.jsonl`
- `segment-000002.jsonl`

The padded numeric suffix is useful because:

- it sorts naturally
- it makes append progression easy to inspect visually
- it keeps layout interpretation simple for both code and humans

The `segment_id` in read and write metadata corresponds to this numeric identity.

## Why Segment Files Roll Over

`Stream` does not keep writing forever into a single file. Segment rollover happens when the active segment reaches the configured `max_segment_bytes` threshold.

In practice, that means:

- the current segment remains the append target while it is under the size limit
- once the size threshold is reached, the next append moves to a new segment id
- append sequence numbers continue increasing across the new file boundary

This matters because multiple segments are a sign of ordinary healthy growth, not of trouble.

## What `sequence` Means

`sequence` is the global append-order identity of an accepted record.

It is not:

- local only to one segment
- a convenience counter with no semantic meaning
- replaceable by line order alone

It is:

- monotonic across the whole store
- central to replay interpretation
- central to integrity checks

This matters because sequence continuity is one of the clearest expressions of coherent canonical history.

## What `offset` Means

`offset` is the line position of a record within its segment file.

In practice, it tells the store:

- which specific line inside the segment corresponds to a helper index pointer
- where a stored record lives within its segment context

This matters because helper indexes do not copy record payloads. They point back to canonical segment locations using `(segment_id, offset)`.

## Why `sequence` And `offset` Both Exist

At first glance, it may seem redundant to have both `sequence` and `offset`.

They are serving different purposes:

- `sequence` expresses global append order across the store
- `offset` expresses local placement inside a specific segment

You need both because:

- replay and integrity care about global order
- indexed lookups need precise local file positions

Once you see that split, the storage layout becomes much easier to reason about.

## What Lives In `indexes/`

The `indexes/` directory contains derivative JSONL helper files.

These are grouped by family:

- `indexes/run_ref/`
- `indexes/stage_execution_ref/`
- `indexes/record_type/`

Each file contains pointer entries such as:

```json
{"offset":1,"segment_id":1,"sequence":1}
```

That pointer says, in effect:

- this matching record lives in segment `1`
- on line `1`
- with global sequence `1`

The index is useful because it narrows scan work. It is not useful because it replaces the canonical segment entry.

## Why Index File Names Look Sanitized

Values such as `run/eval-1` become filenames like:

- `run__eval-1.jsonl`

This sanitization exists so practical keys can become filesystem-safe filenames. It is a storage convenience detail, not a semantic transformation of the canonical record.

The important point is that the canonical value still lives in the segment payload. The filename is just a helper representation.

## Why Indexes Are Derivative

Indexes are derivative because they can be rebuilt from canonical history.

That means:

- deleting an index file does not delete canonical history
- rebuilding indexes reconstructs helper pointers from segments
- a damaged index should not be interpreted as damaged truth by default

This matters because operators should treat index damage and segment damage very differently.

## What Happens During Index Rebuild

When indexes are rebuilt, `Stream`:

1. scans canonical history
2. derives pointer records from stored segment entries
3. recreates index files under `indexes/`

The important point is that rebuild restores convenience, not truth.

If canonical segments are already damaged, rebuild cannot magically recreate what is unreadable or missing. It can only rebuild helper pointers from what remains interpretable.

## What Happens During Repair

Repair is different from rebuild because it can operate on canonical segment tails.

In the known truncated-tail repair path, `Stream`:

1. detects a damaged trailing segment line
2. copies the original segment into `quarantine/`
3. trims the damaged tail from the canonical segment
4. recomputes manifest state
5. rebuilds derivative indexes

This matters because repair changes canonical storage, while rebuild only changes derivative helper state.

## What `quarantine/` Means

The `quarantine/` directory is a safety artifact of repair.

If a damaged segment is going to be trimmed, `Stream` first preserves a copy under `quarantine/`.

That means:

- repair is not silent destruction
- operators can still inspect the original damaged bytes afterward
- the system preserves an explicit audit trail of what was altered during repair

This is one of the clearest examples of the library preferring explicit, inspectable operations over hidden cleanup.

## How To Inspect A Store Manually

When debugging a local store, a good inspection order is:

1. open `manifest.json`
2. list and inspect `segments/`
3. inspect the specific segment lines around the affected sequence
4. inspect `indexes/` only after understanding the segment reality
5. inspect `quarantine/` if a repair already happened

This order matters because it keeps you aligned with the trust boundary:

- canonical history first
- helper state second
- recovery artifacts last

## Common Mistakes In Layout Interpretation

### Treating The Manifest As The Whole Store

The manifest is useful, but it is not the canonical record history.

### Treating Indexes As Authoritative Because They Are Easier To Read

Indexes are compact and readable, but they are still derivative helper state.

### Treating Multiple Segments As A Problem

Multiple segment files are usually just healthy growth under append and rollover rules.

### Assuming Rebuild And Repair Touch The Same Kinds Of Files

They do not. Rebuild operates on derivative indexes. Repair may alter canonical segments and then rebuild helper state afterward.

### Ignoring `quarantine/`

If repair ran, the quarantine copy is part of the operational story. It tells you what canonical file was changed and preserves the pre-trim evidence.

## Operational Meaning Of A Healthy Layout

A healthy layout usually means:

- segments are readable
- sequence order is coherent
- manifest frontier matches observed segment history
- indexes exist when enabled and point back to real segment lines

This does not mean every file must be perfect in the same way. It means the storage layers agree in the roles they are supposed to play.

## Operational Meaning Of A Damaged Layout

A damaged layout may show up as:

- malformed segment lines
- truncated tails
- sequence gaps
- manifest drift
- missing or stale derivative indexes

The important point is that not all damage has the same severity:

- damaged indexes may be inconvenient
- damaged segments are serious
- damaged manifest state is important but still secondary to canonical segment reality

That distinction is exactly why `Stream` splits these files the way it does.

## A Good Storage-Side Checklist

Before moving on, it is worth checking that your storage mental model now includes all of the following:

1. `segments/` are canonical
2. `manifest.json` tracks append frontier rather than replacing history
3. `indexes/` are derivative pointer files
4. `sequence` is global while `offset` is local to a segment
5. segment rollover is normal
6. rebuild restores helper state
7. repair can alter canonical tails and preserve originals in `quarantine/`

## What To Read Next

Read [Integrity and Repair](integrity-and-repair.md) next if you want to see how damaged layouts are interpreted, reported, rebuilt, and repaired.

Read [CLI Reference](/Users/eastl/MLObservability/Stream/docs/en/cli-reference.md) next if you want exact commands for inspecting layout, running integrity checks, replaying history, exporting JSONL, rebuilding indexes, and repairing truncated tails.

Read [API Reference](/Users/eastl/MLObservability/Stream/docs/en/api-reference.md) next if you want the public library surfaces that sit on top of this storage model.
