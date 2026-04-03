# FAQ

[User Guide Home](/Users/eastl/MLObservability/Stream/docs/USER_GUIDE.en.md)

This page answers recurring `Stream` questions in a compact form. It is not a substitute for the main concept pages. It is the place to go when you already have a concrete question and need the shortest correct answer.

If a short answer here raises a deeper question about trust boundaries, replay semantics, or repair safety, follow the linked concept page rather than treating the FAQ as the whole story.

## What Is `Stream` For?

`Stream` is the local append-oriented canonical record store of the ML observability stack.

That means it is for:

- storing canonical observability records locally
- preserving append order explicitly
- scanning and replaying that local history
- exporting replayed history when another tool needs JSONL
- checking integrity and performing narrow repair operations

It is not a general analytics database, a schema-definition layer, or an arbitrary JSON bucket.

Read [Mental Model](/Users/eastl/MLObservability/Stream/docs/en/mental-model.md) for the longer explanation.

## What Counts As Canonical Truth On Disk?

The canonical truth is the segment history in `segments/*.jsonl`, together with the append-order meaning expressed by sequence numbers and the manifest fields that track append frontier state.

The short version is:

- `segments/` are canonical history
- `manifest.json` is store operating state
- `indexes/` are derivative helpers

If a helper index disagrees with segment history, the segment history wins.

Read [Layout and Storage](/Users/eastl/MLObservability/Stream/docs/en/layout-and-storage.md) next if this boundary is still fuzzy.

## Why Are Indexes Not The Source Of Truth?

Because `indexes/` can be rebuilt from canonical segment history.

An index is useful because it narrows practical scans. It is not authoritative because it does not own the history. If an index is stale, missing, or partially rebuilt, that affects convenience and performance. It does not redefine what was canonically appended.

This matters because many debugging mistakes start when someone treats a helper file as more real than the segments it points to.

## Why Do `scan()` And `replay()` Both Exist?

Because they answer different questions.

- `scan()` asks: which stored records match this practical filter?
- `replay()` asks: what history can I safely interpret under this replay mode?

`scan()` is the direct inspection path. `replay()` adds integrity-aware semantics on top of reading.

Use `scan()` when you want stored records. Use `replay()` when replay safety matters.

Read [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md) for the full distinction.

## When Should I Use `scan()`?

Use `scan()` when:

- you want to inspect matching stored records directly
- you want placement metadata such as `sequence`, `segment_id`, or `offset`
- you are doing normal development-time or operator-time inspection
- you do not need replay warnings or known gaps packaged into a result model

`scan()` is intentionally practical and straightforward. It is not meant to hide the store behind interpretation logic.

## When Should I Use `replay()`?

Use `replay()` when:

- you want integrity-aware history reading
- you want explicit `strict` or `tolerant` semantics
- you want warnings and known gaps surfaced as part of the result
- you want the same semantics that power JSONL export

If the question is "can I safely treat this as coherent ordered history?", `replay()` is usually the right surface.

## Why Can `strict` Replay Fail?

Because `strict` is supposed to fail when the store is corrupted.

That is not a usability defect. It is the store refusing to normalize damaged history into something that looks complete and trustworthy.

In practice, strict replay protects you from:

- reading through unreadable canonical lines as if nothing happened
- treating sequence-broken history as coherent
- exporting or consuming output that looks complete when it is not

Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) for the operator meaning of strict failure.

## When Is `tolerant` Replay Acceptable?

`tolerant` replay is acceptable when partial history is still useful and the consumer is willing to treat that history as explicitly incomplete.

That usually means:

- warnings are surfaced and not ignored
- known gaps are carried forward into interpretation
- the result is used for triage, debugging, or partial recovery

It does not mean the store is healthy enough. It means the caller is intentionally choosing a degraded read mode.

## Is `tolerant` Replay The Same As "Good Enough"?

No.

`tolerant` means "read what can still be interpreted, and say out loud where the gaps are." It does not mean the damage is minor, harmless, or safe to forget.

That distinction is one of the most important habits to keep in `Stream`.

## What Do `warnings` And `known_gaps` Mean?

In `ReplayResult`:

- `warnings` describe integrity issues that matter for interpretation
- `known_gaps` point to explicit damaged-history gaps, especially for error-severity issues

They are not decorative metadata. They are part of the meaning of the replay result.

If you ignore them, you are effectively pretending the store said less than it actually did.

## What Is The Difference Between `rebuild_indexes()` And `repair_truncated_tails()`?

`rebuild_indexes()` repairs derivative helper state.

`repair_truncated_tails()` performs a narrow canonical repair for a known damaged-tail case and then rebuilds derivative indexes afterward.

The short version is:

- rebuild is for helper-state recovery
- repair is for limited canonical-history intervention

If you remember only one thing, remember this: rebuild is ordinary maintenance; repair is more serious.

Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) before using repair in production workflows.

## Why Doesn't Rebuilding Indexes Make A Corrupted Store Healthy?

Because rebuilding indexes only reconstructs derivative helper state.

If the real problem is unreadable segment lines, sequence gaps, or damaged canonical history, rebuilding indexes does not recreate the missing truth. It only restores convenience structures derived from whatever canonical history is still readable.

This is why rebuild can warn even when it succeeds as a helper-state operation.

## When Should I Reach For `repair_truncated_tails()`?

Reach for `repair_truncated_tails()` when:

- integrity reporting points to truncated final lines
- the damage is localized to segment tails
- you want the store to quarantine damaged files before trimming
- you understand that this is a canonical intervention, not casual cleanup

Do not reach for it as a generic "fix my store" button.

## Why Does Repair Create Quarantine Copies?

Because canonical repair should preserve evidence of what changed.

Before trimming a damaged tail, the repair path copies the original segment into `quarantine/`. That gives operators a preserved artifact of the damaged file for later inspection.

This matters because repair should be explicit and auditable, not silent.

## Can I Treat Exported JSONL As The Canonical Store?

No.

`export_jsonl()` is a convenience output surface built on replay semantics. The canonical store remains the local segment history inside the `Stream` root.

Export files are useful for:

- downstream tooling
- debugging handoff
- reviewable snapshots

They do not replace the store's canonical history.

## Why Does `scan` CLI Output Only The Record Body?

Because the CLI `scan` command is intentionally a lightweight stored-record inspection surface.

It prints the canonical record mapping rather than the full `StoredRecord` envelope. If you need placement metadata such as `sequence`, `segment_id`, or `offset`, use the Python API.

Read [CLI Reference](/Users/eastl/MLObservability/Stream/docs/en/cli-reference.md) and [API Reference](/Users/eastl/MLObservability/Stream/docs/en/api-reference.md) for the exact shapes.

## What Does `AppendResult.success` Actually Mean?

`AppendResult.success` means there were no rejected records in that append operation.

It does not mean:

- every future read will be healthy forever
- the store is globally healthy
- the result replaces an integrity check

It is an append outcome signal, not a store-wide health classification.

## Can `append_many()` Partially Accept A Batch?

Yes. You should read the result model rather than assuming all-or-nothing behavior.

That is why `AppendResult` exposes:

- `accepted`
- `rejected`
- `accepted_count`
- `rejected_count`
- `durable_count`

The important point is that `append_many()` is a structured append surface, not a hidden database transaction abstraction.

## What Does `durability_status` Mean?

`durability_status` tells you how far the append reached in durability terms.

The public enum values are:

- `accepted`
- `flushed`
- `fsynced`

This matters because "accepted by the store" and "reached the configured durability target" are related but not identical ideas.

Read [Write Path](/Users/eastl/MLObservability/Stream/docs/en/write-path.md) for the full write-side explanation.

## Why Does `Stream` Care So Much About Sequence?

Because sequence is part of the meaning of ordered canonical history.

In `Stream`, sequence is not ornamental metadata. It is how the store expresses append continuity across the local history. If sequence continuity breaks, the history story breaks with it.

That is why sequence gaps are integrity issues rather than small cosmetic problems.

## Is `manifest.json` More Important Than The Segments?

No.

`manifest.json` is important, but it is important in a supporting role. It tracks append frontier and layout state. It does not replace segment history as the source of truth.

If the manifest disagrees with observed history, that disagreement is itself a signal that the store needs inspection.

## Should I Run Integrity Checks Only In Emergencies?

No.

Integrity checks are especially useful when something looks wrong, but they are also part of ordinary confidence management for a local canonical store.

In practice, it is reasonable to run them:

- after suspicious process termination
- before relying on an important replay
- after manual file inspection
- after rebuild or repair operations

## What Should I Read First If I Am New?

If you are just starting, read these in order:

1. [Getting Started](/Users/eastl/MLObservability/Stream/docs/en/getting-started.md)
2. [Mental Model](/Users/eastl/MLObservability/Stream/docs/en/mental-model.md)
3. [Write Path](/Users/eastl/MLObservability/Stream/docs/en/write-path.md)
4. [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md)

That sequence is enough to build the right core habits before you go deeper into storage layout or repair.

## Where Should I Go Next?

- Read [Mental Model](/Users/eastl/MLObservability/Stream/docs/en/mental-model.md) if the trust boundary still feels abstract.
- Read [Write Path](/Users/eastl/MLObservability/Stream/docs/en/write-path.md) if append acceptance, batching, or durability feels unclear.
- Read [Read Path](/Users/eastl/MLObservability/Stream/docs/en/read-path.md) if `scan`, `replay`, and export still blur together.
- Read [Layout and Storage](/Users/eastl/MLObservability/Stream/docs/en/layout-and-storage.md) if you need to inspect the on-disk store directly.
- Read [Integrity and Repair](/Users/eastl/MLObservability/Stream/docs/en/integrity-and-repair.md) if you are diagnosing damage or planning maintenance.
- Read [CLI Reference](/Users/eastl/MLObservability/Stream/docs/en/cli-reference.md) for exact command shapes.
- Read [API Reference](/Users/eastl/MLObservability/Stream/docs/en/api-reference.md) for exact Python surfaces.
