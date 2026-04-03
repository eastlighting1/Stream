# Write Path

This page explains how records enter `Stream`, what the library accepts as canonical history, how append execution actually proceeds, and how to interpret append results without making unsafe assumptions. If `Getting Started` showed the first successful write, this page explains the write-side rules that make that success meaningful.

The goal here is not only to say "call `append()`." The goal is to help you decide:

- what should be written at all
- what shape the input must have
- what append success actually means
- how batch behavior differs from transactional all-or-nothing expectations
- how durability modes affect the meaning of a returned result
- when a new segment is created and why that is normal

## What This Page Helps You Decide

After reading this page, you should be able to answer these questions clearly:

- what counts as an acceptable canonical record
- whether you should call `append()` or `append_many()`
- how normalization and validation interact
- what `accepted`, `rejected`, `durability_status`, and `durable_count` really mean
- what happens when only part of a batch is valid
- how `flush` and `fsync` differ operationally
- why append placement metadata such as sequence, segment, and offset matter

## Why The Write Path Deserves Its Own Page

At first glance, `Stream` writing can look trivial: pass a dict in, get a result back. In practice, the write path is where `Stream` decides whether your data is eligible to become canonical history at all.

That means the write path is where several important boundaries are enforced:

- the boundary between arbitrary input and accepted canonical records
- the boundary between accepted writes and rejected writes
- the boundary between a write being accepted and a write being durably committed
- the boundary between canonical segment history and derivative helper state

This matters because most downstream confusion starts with write-side assumptions. If a caller believes "append succeeded" means more than it actually means, or believes "append rejected" implies nothing was salvageable in a batch, later read and repair behavior will feel surprising.

## The One-Sentence Write Model

`Stream` writes canonical records by normalizing input, validating it against the canonical shape, assigning append-order placement, writing a JSONL segment entry, updating manifest state, and then refreshing derivative index pointers.

That sentence is the write path in miniature.

## What The Write Path Owns

The write path in `Stream` owns several concrete responsibilities:

- normalize supported record inputs into a canonical mapping
- validate canonical fields and payload structure
- choose the target segment and next sequence number
- append a single JSONL entry to the canonical segment store
- record append durability status
- advance manifest state
- add pointer entries to derivative indexes

The important point is that writing is not just "serialize this dict." It is "admit this value into canonical local history under append-order rules."

## What Inputs `Stream` Accepts

`Stream` accepts inputs that it can normalize into valid canonical records.

In practice, that includes:

- supported `Spine` record objects
- mapping-like Python records that already carry the canonical fields
- dataclass inputs that normalize into acceptable mappings

The library does not accept arbitrary Python objects or arbitrary JSON-shaped blobs just because they can be serialized.

### A Valid Mapping Example

```python
record = {
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
```

### An Invalid Mapping Example

```python
invalid_record = {
    "record_type": "structured_event",
    "payload": {},
}
```

That second record is not merely incomplete in a cosmetic sense. It cannot become canonical history, because required fields and payload guarantees are missing.

## Normalization Comes Before Validation

One subtle but important part of the write path is that `Stream` normalizes supported inputs before it validates them.

In practice, this means:

- `Spine` objects are converted into canonical payload mappings
- dataclass inputs are converted into mappings first
- mapping inputs are normalized into string-keyed canonical structure

Only after that does `Stream` validate whether the normalized record is acceptable canonical history.

This matters because the write path is intentionally generous about input *formats* but strict about canonical *meaning*.

In other words:

- multiple input shapes may be acceptable
- only one canonical record meaning is acceptable

## What Validation Is Actually Enforcing

Validation in `Stream` is not just type checking. It is enforcing the shape and safety assumptions that make replayable history interpretable later.

That includes checks such as:

- required stable references must be non-blank and well-formed
- timestamps must already be normalized
- `recorded_at` and `observed_at` must make sense in order
- schema version must be supported
- `record_type` must be one of the accepted canonical families
- payload structure must match the chosen `record_type`

This matters because invalid writes are not simply inconvenient. They would contaminate canonical history if they were accepted.

## Record Types Matter On The Write Path

The write path does not treat every record payload as interchangeable.

For example:

- `structured_event` expects event-oriented fields such as `event_key`, `level`, and `message`
- `metric` expects metric-specific fields such as `metric_key`, `value`, and aggregation semantics
- `trace_span` expects span-oriented timing and identity fields
- degradation records follow their own payload expectations

The important point is that `record_type` is not descriptive decoration. It changes how payload validation works and therefore changes what the store will accept.

## The Write Pipeline Step By Step

At a high level, a successful append proceeds through these stages:

1. normalize the input
2. validate the canonical mapping
3. choose the append slot
4. serialize a segment entry
5. write it to the target segment
6. flush or fsync according to durability mode
7. commit manifest progress
8. append derivative index entries
9. return append placement and durability metadata

This sequence explains why append results are so informative. They are not random metadata. They describe the path the write just took through the store.

## Choosing An Append Slot

Before a write lands in a file, `Stream` chooses an append slot. That slot determines:

- the target `segment_id`
- the next `sequence`
- the next line `offset` within that segment

At first glance, this may sound like internal bookkeeping. In practice, it is the beginning of the canonical placement of the record.

This matters because later operations depend on those placement facts:

- scans preserve append order
- replays interpret ordered history
- indexes point back to `(segment_id, offset)` pairs
- integrity checks reason about sequence continuity

## Why Segment Rollover Exists

`Stream` does not write every record into one infinitely growing file. Segments roll over once the current file reaches the configured size threshold.

That means a healthy append path may eventually:

- continue using the current segment while there is room
- switch to a new segment once the configured size limit is reached
- keep sequence numbers increasing across the segment boundary

The important point is that a new segment is not a sign of corruption or fragmentation. It is an ordinary part of the write path.

## What Gets Written To The Segment

The segment file does not store raw caller input. It stores a canonical segment entry:

```json
{
  "sequence": 12,
  "appended_at": "2026-04-03T00:10:00Z",
  "record": {
    "...": "canonical record payload"
  }
}
```

This structure is important because it separates:

- append metadata owned by the store
- canonical record data supplied by the caller

The append metadata tells the story of local acceptance. The canonical record tells the story of the observed event, metric, span, or degradation fact.

## What Gets Written To The Manifest

After a successful segment write, `Stream` advances manifest state.

In practice, this means updating:

- `current_segment_id`
- `next_sequence`
- `last_committed_sequence`
- `current_segment_record_count`

This matters because the manifest tells later appends where the store believes its current write frontier is. If those values drift away from observed segment history, integrity checks can surface that mismatch explicitly.

## What Gets Written To The Indexes

Only after canonical history is written and manifest progress is advanced does `Stream` append helper index entries.

Those derivative entries store pointer information such as:

- `sequence`
- `segment_id`
- `offset`

keyed under practical scan families like:

- `run_ref`
- `stage_execution_ref`
- `record_type`

The important point is that indexes are a write-side convenience artifact, not the thing being canonically written.

## `append()` Versus `append_many()`

Use `append()` when:

- you are writing one logical record
- call-site simplicity matters more than batching
- you want the return shape of a single-record batch without building the list yourself

Use `append_many()` when:

- you already have multiple candidate records
- partial acceptance is acceptable
- you want one append result describing the batch outcome

Operationally, `append()` is just the single-record form of the same write path. It does not create a different storage model.

## Batch Behavior Is Not Transactional

This is one of the most important practical points on the write path.

`append_many()` is not an all-or-nothing transaction. It iterates through the inputs and:

- accepts records that validate
- rejects records that fail validation
- preserves the accepted records in canonical history
- reports rejections back to the caller

That means a batch can succeed partially.

A conceptual result might look like:

```text
success == False
accepted_count == 2
rejected_count == 1
rejected[0] == "record[1] rejected: ..."
```

This matters because callers should not assume that any rejection means "nothing was written." In `Stream`, partial success is normal and explicit.

## How To Read `AppendResult`

The write path is much easier to reason about once you know how to read the result object.

### `accepted`

The `accepted` tuple contains one `AppendReceipt` per successfully appended record.

Each receipt tells you:

- the assigned `sequence`
- the `segment_id`
- the line `offset`
- the `record_ref`
- the `record_type`
- the `run_ref`
- the `durability_status`

### `rejected`

The `rejected` tuple contains human-readable rejection messages for records that failed validation.

These are not just logs. They are the explicit write-side record of what was not admitted into canonical history.

### `durability_status`

At the batch level, `durability_status` summarizes how durable the accepted writes became.

### `durable_count`

`durable_count` reports how many accepted writes reached the store's configured durability threshold.

### `success`

`success` means the batch had no rejections. It does **not** mean more than that.

In particular, it does not by itself mean:

- the store is healthy overall
- the indexes are authoritative
- no earlier corruption exists elsewhere in history

## What `DurabilityStatus` Means

The write path distinguishes between acceptance and durability.

Possible statuses include:

- `accepted`
- `flushed`
- `fsynced`

The practical meaning depends on store configuration.

### `flush`

When the store uses `DurabilityMode.FLUSH`, the append path:

- writes the JSONL entry
- flushes the file handle
- returns a `flushed` durability status for accepted writes

### `fsync`

When the store uses `DurabilityMode.FSYNC`, the append path:

- writes the JSONL entry
- flushes the file handle
- calls `fsync`
- returns an `fsynced` durability status for accepted writes

The important point is that durability is not a vague notion of "probably written." It is an explicit part of the append result.

## Why Durability Is Separate From Acceptance

At first glance, you may want one boolean that says "write succeeded." `Stream` intentionally gives you more than that because acceptance and durability are not the same question.

A caller may care about:

- whether the record became canonical history
- whether the write crossed the stronger `fsync` boundary
- whether the batch was partially accepted

Those are related but distinct operational facts.

## A Simple Single-Record Example

```python
result = store.append(valid_record)

if not result.success:
    raise RuntimeError(result.rejected)

receipt = result.accepted[0]
print(receipt.sequence)
print(receipt.segment_id)
print(receipt.offset)
print(receipt.durability_status)
```

This is a good default pattern because it forces the caller to notice both placement and durability.

## A Simple Batch Example

```python
result = store.append_many([record_a, record_b, record_c])

print("accepted:", result.accepted_count)
print("rejected:", result.rejected_count)

for rejection in result.rejected:
    print("rejection:", rejection)

for receipt in result.accepted:
    print(receipt.sequence, receipt.record_ref, receipt.durability_status)
```

This pattern is useful when you want to preserve valid canonical history without losing visibility into bad inputs.

## Common Mistakes On The Write Path

### Treating Validation As Optional Input Hygiene

Validation is not a soft suggestion. It is the gate that decides whether a value is allowed to become canonical history.

### Assuming `append_many()` Is Transactional

It is not. Valid entries may still be accepted when others fail.

### Ignoring `durability_status`

If your operational model cares about stronger persistence guarantees, you should read the returned durability information rather than collapsing everything into "it wrote."

### Treating Placement Metadata As Incidental

`sequence`, `segment_id`, and `offset` are not cosmetic. They describe where the write entered canonical history and power later read, replay, and repair behavior.

### Assuming Helper Index Writes Are The Important Part

They are not. The canonical act is appending the segment entry. The index updates are derivative.

## Operational Meaning Of A Successful Write

A successful write means:

- the input normalized correctly
- the canonical validation rules passed
- the segment entry was written
- append progress advanced
- placement metadata was assigned
- derivative index pointers were appended

It does **not** mean:

- the overall store has no earlier corruption
- the caller can ignore integrity checks forever
- a later replay cannot fail for unrelated historical reasons

This matters because a write path page should teach precise confidence, not false comfort.

## Operational Meaning Of A Rejected Write

A rejected write means the input was not admitted into canonical history. That is usually the correct outcome.

In practice, rejection protects the store from:

- malformed canonical envelopes
- invalid timestamps
- unsupported schema versions
- payloads that do not match the chosen record type
- malformed correlation or stable reference fields

The important point is that rejection is part of preserving a trustworthy store, not evidence that the library is being unnecessarily strict.

## A Good Write-Side Checklist

Before moving on from the write path, it is worth checking that your mental model now includes all of the following:

1. accepted writes and durable writes are related but distinct concepts
2. `append_many()` can partially succeed
3. validation is what protects canonical history
4. placement metadata matters because ordered history matters
5. helper indexes are refreshed after canonical writes, not instead of them
6. a successful append does not replace the need for later integrity checks

## What To Read Next

Read [Read Path](read-path.md) next if you want to see how the stored write results turn into scan, replay, tolerant read, and export behavior.

Read [Layout and Storage](layout-and-storage.md) next if you want to see how the write-side artifacts map onto `manifest.json`, `segments/`, and `indexes/` on disk.

Read [Integrity and Repair](integrity-and-repair.md) next if you want to understand what later happens when the canonical history written by this path becomes damaged or inconsistent.
