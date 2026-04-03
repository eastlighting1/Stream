# Mental Model

This page helps you build the right mental model before you read deeper write, read, and repair details. The goal is not to restate every API. The goal is to explain what `Stream` is for, what it is not for, what parts of the on-disk store should be treated as canonical truth versus rebuildable helper state, and how those choices shape the behavior of `scan`, `replay`, integrity checks, rebuilds, and repairs.

If `Getting Started` gives you the first successful flow, this page is meant to explain why that flow behaves the way it does.

## What This Page Helps You Decide

After reading this page, you should be able to answer these questions clearly:

- what belongs in `Stream` and what does not
- what files on disk are authoritative
- why append order matters instead of being incidental metadata
- why `scan` and `replay` both exist
- why helper indexes are useful but not trustworthy as source of truth
- why integrity checks and repair steps are part of ordinary store operation
- what rebuild can restore and what it cannot restore
- what kinds of damage `strict` replay refuses to normalize away

## The One-Sentence Mental Model

`Stream` is a local append-oriented store for canonical observability history where segment files are the source of truth, helper indexes are rebuildable conveniences, and integrity interpretation is explicit rather than hidden.

Almost every design choice in the library follows from that sentence.

## What `Stream` Is

`Stream` is the append-oriented canonical record store of the ML observability stack.

That description is doing a lot of work:

- `append-oriented` means new history is written in order rather than rewritten in place
- `canonical record` means the store expects records that already fit the stack's contract shape
- `store` means `Stream` is responsible for preserving and reading local history, not just forwarding it somewhere else

At first glance, `Stream` can look like a simple local event log. In practice, it is narrower and stricter than that. The important point is that `Stream` is not trying to be a general-purpose analytics database or an arbitrary JSON archive. It is the local persistence layer for canonical observability history.

That has several consequences:

- data acceptance is stricter than plain serialization
- read paths are framed around history interpretation, not just raw lookup
- the on-disk layout is intentionally inspectable
- corruption is surfaced as an operational fact, not hidden behind silent recovery

## What `Stream` Is Not

Understanding what `Stream` does not do is just as important as understanding what it does.

`Stream` is not:

- the metadata anchor store of the stack
- the schema-definition layer
- the analytics or visualization layer
- a free-form bucket for arbitrary runtime blobs
- a system that treats helper indexes as authoritative truth
- a system that silently heals damaged canonical history without telling you

This matters because many operational mistakes start with the wrong assumption about scope. If you expect `Stream` to solve long-term analytics queries, cross-store joins, or schema ownership, you will push it beyond the boundary it is designed to protect.

In practice, the safest way to use `Stream` is to let it stay narrow:

- canonical record history goes in
- practical read and replay operations come out
- helper structures can be rebuilt
- damage is made visible

## The Core Storage Idea

The central idea in `Stream` is simple:

1. canonical records are appended to local segment files
2. append order is preserved explicitly through sequence numbers
3. helper indexes are derived from that canonical history
4. reads may use helper indexes for convenience, but integrity always traces back to segment history

That means the trust boundary is asymmetric:

- `segments/*.jsonl` are canonical
- `manifest.json` tracks append progress and layout state
- `indexes/*/*.jsonl` are helpful but rebuildable

In other words, helper files can accelerate reads, but they do not define reality.

This is not just an implementation detail. It is the store's operating philosophy.

## Why Append Orientation Matters

It is easy to hear "append-oriented" and treat it as a storage optimization. That is too shallow. In `Stream`, append orientation is part of the semantics of the store.

Append orientation means:

- history has an explicit acceptance order
- new facts are added rather than merged into mutable rows
- integrity can reason about sequence continuity
- replay can treat the store as an ordered history rather than a bag of records

The important point is that ordered history is a feature, not accidental baggage. Once you see the store this way, sequence numbers stop looking like internal bookkeeping and start looking like part of the canonical truth.

## Source Of Truth Versus Helper State

This is the single most important mental model in `Stream`.

### Canonical State

Canonical state is the append history you must be able to trust after inspection or repair:

- `segments/segment-*.jsonl`
- the append-order information embedded in segment entries
- the manifest fields that track current append progress

If there is a disagreement between segments and a helper index, the segment history wins.

This matters because any tool or operator decision that treats a helper summary as more real than the stored history is already on the wrong side of the trust boundary.

### Derivative State

Derivative state exists to make common scans practical:

- `indexes/run_ref/*.jsonl`
- `indexes/stage_execution_ref/*.jsonl`
- `indexes/record_type/*.jsonl`

These indexes are useful because they let `Stream` avoid full scans in simple cases. But they are not authoritative because they can be rebuilt from segment history.

This matters because rebuilding an index can restore convenience, but it cannot recreate missing or corrupted canonical history.

### Why This Split Is Healthy

The split between canonical and derivative state can feel inconvenient at first because it asks you to think about trust explicitly. In practice, that explicitness is exactly what keeps local recovery understandable.

Because indexes are derivative:

- you can remove and rebuild them without changing the canonical store
- a damaged index does not automatically imply damaged history
- the store can stay inspectable and repairable without pretending all files are equally important

Because segments are canonical:

- corruption is serious and should be treated seriously
- replay semantics matter
- repair cannot be treated like ordinary cache refresh

## Why `manifest.json` Exists

At first glance, `manifest.json` can look like bookkeeping. In practice, it is part of the store's local operating state.

It tracks things like:

- the current layout mode
- the layout version
- the current segment id
- the next sequence number
- the last committed sequence
- the number of records in the current segment

The important point is that the manifest does not replace the segments. It helps coordinate append progress and detect drift. If the manifest and segment history disagree, that disagreement is itself an operational signal.

In practice, this means:

- a healthy manifest makes appends predictable
- a mismatched manifest is a warning that state needs inspection
- the manifest helps tell you where append progress thinks it is
- the segments tell you what history actually exists

So the manifest is important, but it is important in a supporting role rather than a truth-owning role.

## Why `scan` And `replay` Both Exist

At first glance, these methods look redundant because both read stored records. In practice, they serve different kinds of decisions.

`scan` is for ordinary inspection:

- filter by run, stage, record type, or time
- return stored records directly
- use helper indexes when the query shape allows it

`replay` is for integrity-aware history reading:

- respect `strict` versus `tolerant` semantics
- surface warnings and known gaps when corruption exists
- refuse unsafe strict reads when the store is corrupted

So `scan` answers "what records match this filter?" while `replay` answers "what history can I safely interpret under this replay mode?"

This difference is important because `Stream` is not merely optimizing retrieval. It is helping operators make explicit decisions about how much damage they are willing to tolerate when reading history.

## Why `scan` Can Use Indexes Without Making Indexes Canonical

This design can look contradictory at first.

`scan()` may use helper indexes when the filter is simple enough. That does not make those indexes canonical. It only means the store is willing to consult derivative state for convenience and then still read the real segment lines that those pointers refer to.

In other words:

- the index narrows the search
- the segment line still supplies the truth

That distinction lets the store be practical without weakening the source-of-truth boundary.

## Why Replay Modes Exist At All

Replay modes exist because "reading history" is not a single question once corruption is possible.

### `strict`

`strict` means:

- do not interpret corrupted history as if it were whole
- fail if the store is in a corrupted state
- prioritize safety over convenience

### `tolerant`

`tolerant` means:

- continue reading what can still be interpreted
- skip unreadable lines when necessary
- surface warnings and known gaps explicitly

The important point is that `tolerant` does not mean "healthy enough." It means "usable with acknowledged gaps." That is a very different statement.

## Why Append Order Matters

`Stream` is not only storing records; it is preserving the order in which canonical history was accepted.

That is why sequence numbers exist, and why integrity checks care about sequence gaps. The store is not just a bag of matching records. It is an ordered history that later repair, replay, and export operations depend on.

This matters because corruption is not only about malformed JSON. A sequence gap can also mean the history itself is no longer safe to interpret as complete ordered truth.

It also matters because many downstream questions are sequence-sensitive even when they do not look that way at first. If the accepted order is wrong or incomplete, later reasoning about "what happened next" stops being trustworthy.

## What Integrity Means In `Stream`

Integrity in `Stream` is not an abstract checksum concept. It is an operational judgment about whether the local history still behaves like coherent append truth.

Integrity checks look for things like:

- unreadable JSON lines
- truncated tails
- sequence gaps
- manifest drift relative to observed history

That list tells you something important about the store's design. Integrity is not only about raw file corruption. It is also about whether the append story still makes sense.

## The Healthy Path And The Damaged Path

It helps to think of `Stream` as having two normal operating paths.

### Healthy Path

When the store is healthy:

- append succeeds
- scan returns records normally
- strict replay works
- helper indexes can be used as performance helpers
- export behaves like a straightforward read-side convenience

### Damaged Path

When the store is damaged:

- integrity checks report issues
- strict replay may refuse to proceed
- tolerant replay may continue with warnings and known gaps
- rebuild may restore helper indexes
- repair may trim known damaged tails, but only in specific cases

The important point is that damaged-path behavior is not exceptional design drift. It is part of the intended operating model of a local append store.

## Rebuild Versus Repair

This is one of the most important distinctions in the library.

### Rebuild

Rebuild means:

- reread canonical segment history
- reconstruct derivative indexes
- restore helper state that can be derived again

Rebuild can improve convenience. It cannot recreate truth that no longer exists.

### Repair

Repair means:

- operate on damaged canonical tails in specific known cases
- preserve a quarantine copy before trimming
- recompute manifest state after the canonical change
- rebuild helper indexes afterward

Repair is not a cache refresh. It is an explicit operation on damaged canonical history.

## What `Stream` Optimizes For

`Stream` optimizes for a specific balance:

- inspectable local storage
- predictable append history
- practical filtered reads
- explicit integrity interpretation
- repairability of helper state
- cautious handling of damaged canonical tails

It does not optimize for:

- arbitrary ad hoc analytics
- highly relational query planning
- opaque internal storage
- silent recovery that hides corruption from operators
- pretending every convenience structure is equally authoritative

This matters because the safest `Stream` workflows are explicit. The library prefers surfacing damage over pretending everything is fine.

## What A Good Operator Believes About The Store

A useful shorthand is that a good `Stream` operator believes all of the following:

- the segment history is more important than the index view
- append results are worth reading
- integrity checks are not optional ceremony
- `strict` failure is often the correct outcome
- tolerant replay is useful precisely because it admits incompleteness
- rebuild restores convenience, not lost truth
- repair is a serious but sometimes necessary canonical operation

## Common Mistakes In The Mental Model

### Thinking The Fastest-Readable File Must Be The Truth

A common mistake is to open an index file, see a neat list of pointers, and assume that is the primary persisted reality. It is not. Indexes summarize history. They do not define it.

### Treating Replay Modes As Mere Convenience Flags

`strict` and `tolerant` are not cosmetic options. They represent different safety choices. `strict` protects you from interpreting corrupted history as if it were whole.

### Assuming Rebuild And Repair Mean The Same Thing

They do not. Rebuild restores derivative state. Repair changes damaged canonical segment tails in known recovery cases. Those are very different operations.

### Assuming A Healthy-Looking Scan Guarantees A Healthy Store

A simple scan result can look fine even when the store has underlying corruption elsewhere. This is why integrity checks exist as their own explicit operation.

### Assuming Manifest State Is The Same Thing As History

The manifest is important, but it is not the history itself. It coordinates append progress and can signal drift. It does not replace the segment lines as canonical truth.

## Why This Matters Operationally

This mental model shapes every later decision:

- what you append
- how you interpret reads
- what you trust on disk
- when you choose strict versus tolerant replay
- whether a rebuild is enough
- whether a repair step is acceptable
- whether an apparently convenient shortcut is actually violating the trust boundary

If this page feels clear, the rest of the documentation becomes much easier because the same trust boundary repeats everywhere: canonical history first, helper state second, integrity always explicit.

## A Short Self-Check

Before moving on, it is worth checking whether these statements now feel obvious:

1. The segment files are more authoritative than the helper indexes.
2. `scan` and `replay` are not redundant even when both return records.
3. `strict` replay failing on corruption is a protective behavior.
4. Rebuilding indexes cannot restore missing canonical history.
5. Repair is not the same thing as making an index fresh again.

## What To Read Next

Read [Read Path](read-path.md) next if you want to understand the practical difference between `scan`, `replay`, tolerant reads, and export.

Read [Layout and Storage](layout-and-storage.md) next if you want to see how this mental model maps to the actual on-disk files and manifest fields.

Read [Integrity and Repair](integrity-and-repair.md) next if you want to see how the trust boundary drives rebuild behavior, warnings, and damaged-tail recovery.
