# Integrity and Repair

This page explains how `Stream` evaluates store health, how to interpret integrity reports, what different issue types imply operationally, when `strict` replay should fail, when `tolerant` replay is acceptable, how to think about `rebuild-indexes` versus `repair`, and why repair is a cautious canonical operation rather than a casual maintenance shortcut.

If `Layout and Storage` explains what the files are, this page explains what to do when those files no longer agree with the write and replay model.

## What This Page Helps You Decide

After reading this page, you should be able to answer these questions clearly:

- when to run an integrity check
- how to read `healthy`, `state`, `issues`, and `recommendations`
- which problems are corrupted-history problems versus degraded-state problems
- when `strict` replay failure is the correct behavior
- when `tolerant` replay is useful
- when rebuilding indexes is sufficient
- when repairing truncated tails is appropriate
- why repair should not be treated as routine cleanup

## Why Integrity Exists As Its Own Surface

At first glance, it can seem like ordinary reads should be enough to tell you whether a store is in good shape. In practice, that is not safe enough.

`Stream` stores ordered canonical history. That means health is not only about whether some records can still be read. It is also about whether:

- append order is coherent
- segment lines are structurally readable
- manifest state still matches observed history
- helper state can be trusted as derivative convenience rather than misleading noise

That is why integrity is its own explicit surface instead of being folded into one vague notion of "it seems to work."

## The One-Sentence Integrity Model

`Stream` integrity means the local append history still behaves like coherent canonical truth, and repair means making explicit, limited interventions only when the store knows how to do so without pretending damaged history never existed.

Everything in this page follows from that sentence.

## What Integrity Checks Are Looking For

When `Stream` runs an integrity check, it is not merely asking whether the files exist. It inspects manifest and segment history for conditions that break the append-story model.

In practice, it checks for things such as:

- invalid JSON lines
- truncated final lines
- sequence gaps
- manifest sequence mismatch relative to observed history

This matters because integrity in `Stream` is not abstract file hygiene. It is a judgment about whether local history still behaves like trustworthy append-ordered canonical storage.

## The Integrity Report Shape

An integrity check returns an `IntegrityReport`.

That report includes:

- `healthy`
- `issues`
- `segment_count`
- `record_count`
- `state`
- `recommendations`

The important point is that this is not just a pass/fail result. It is an operator-facing summary of what is wrong, how severe it is, and what kind of next step is reasonable.

## What `healthy` Means

`healthy` is the simplest top-level boolean in the report.

If `healthy` is `True`, the store is currently classified as healthy under the integrity rules the library knows how to apply.

If `healthy` is `False`, that does not automatically tell you whether the situation is merely degraded or actively corrupted. That is what `state` is for.

## What `state` Means

`state` is the high-level integrity classification.

The important values are:

- `healthy`
- `degraded`
- `corrupted`

### `healthy`

`healthy` means no known integrity issues were detected.

### `degraded`

`degraded` means issues exist, but they did not rise to the level of error-class corruption.

### `corrupted`

`corrupted` means the store contains error-severity integrity problems and should not be interpreted as fully trustworthy ordered history under `strict` replay.

This distinction matters because not every problem requires the same response.

## What `issues` Means

`issues` is the detailed list of concrete findings.

Each issue contains fields such as:

- `severity`
- `code`
- `message`
- `segment_id`
- `line_number`

This matters because the report is not just meant to trigger alarm. It is meant to help an operator go inspect the exact location and understand the problem in storage terms.

## Severity Is About Operational Risk

The `severity` field is one of the most important parts of an integrity issue.

In practice:

- warning-severity issues indicate something is off and should be interpreted carefully
- error-severity issues mean the canonical history is not safe to treat as fully intact

That means severity is not a cosmetic label. It directly affects how replay semantics should behave.

## The Most Important Issue Codes

Several issue codes are especially important in `Stream`.

### `invalid_json_line`

This means a segment line could not be parsed as JSON.

Operationally, this is serious because a canonical line of history is unreadable.

### `truncated_line`

This means the final line of a segment looks partially written or cut off.

This is important because it is one of the known repairable cases. It often indicates a damaged tail rather than arbitrary interior corruption.

### `sequence_gap`

This means the observed sequence flow no longer matches expected append continuity.

Operationally, this is serious because ordered history is part of the truth model, not incidental metadata.

### `manifest_sequence_mismatch`

This means the manifest's `next_sequence` no longer matches what the observed segment history implies.

This is important because it suggests drift between append frontier tracking and actual canonical history.

## Why `truncated_line` Is Special

`truncated_line` deserves special attention because it is one of the few damage patterns the repair path knows how to address directly.

When the final line of a segment is truncated:

- the earlier prefix of the segment may still be valid
- the damage is localized to the tail
- a quarantine-and-trim repair can make the canonical history coherent again in a limited, explicit way

That makes truncated tails very different from arbitrary corruption deep inside history.

## Why `sequence_gap` Is Serious

A sequence gap is not merely a missing counter. In `Stream`, it is damage to the meaning of ordered history.

Because sequence encodes append order across the store:

- a gap means the accepted-history story has broken
- replay cannot honestly treat that history as complete ordered truth
- rebuild may restore helper indexes, but it does not recreate the missing continuity

This matters because a sequence gap should change how much confidence you place in downstream interpretation.

## What `recommendations` Mean

Recommendations are not arbitrary hints. They are the library's operator-facing suggestions for the kind of action that makes sense given the detected damage.

Examples include advice such as:

- use tolerant replay before strict replay
- repair a damaged segment tail
- inspect segment ordering
- rebuild derivative indexes after repair

The important point is that recommendations are part of the operational model. They tell you which kind of next step aligns with the trust boundary.

## When To Run Integrity Checks

In practice, it is reasonable to run integrity checks:

- when a replay fails unexpectedly
- when the process terminated mid-write or the host crashed
- before choosing between `strict` and `tolerant` interpretation for important reads
- after manual storage inspection
- after a rebuild or repair operation
- when a manifest mismatch or suspicious file state has been observed

This matters because integrity is not only for emergencies. It is part of normal confidence management for a local canonical store.

## What `strict` Replay Is Protecting You From

`strict` replay is one of the clearest operational consequences of integrity state.

If the store is classified as corrupted:

- `strict` replay refuses to proceed

That is not an inconvenience to work around. It is the store refusing to treat damaged history as whole ordered truth.

In practice, `strict` protects you from:

- silently reading through unreadable canonical lines
- interpreting sequence-broken history as coherent
- producing output that looks complete when it is not

## What `tolerant` Replay Is For

`tolerant` replay exists because sometimes partial history is still operationally useful.

Use it when:

- you need to inspect what remains readable
- you want explicit warnings and known gaps
- you understand that the result is useful but incomplete

Do not use it to pretend the store is healthy. Use it to make damage-aware decisions.

That distinction is the whole point of tolerant replay.

## Rebuild Versus Repair

This is the most important maintenance distinction in `Stream`.

### Rebuild

Rebuild means:

- reread canonical segment history
- recreate derivative helper indexes
- restore convenience state from what is still readable

Rebuild does **not** mean:

- restore missing canonical history
- heal unreadable segment lines
- erase the meaning of sequence gaps

### Repair

Repair means:

- operate on known damaged canonical tails
- preserve a quarantine copy first
- trim the damaged tail from canonical storage
- recompute manifest state
- rebuild derivative indexes afterward

Repair is therefore a much more serious action than rebuild.

## When Rebuild Is The Right Tool

Rebuild is appropriate when the problem is primarily with derivative helper state or when helper state should be regenerated after canonical repair.

Typical cases include:

- index files were removed
- index files are stale or suspect
- a repair already changed canonical segments and helper state must be synchronized
- you want to reconstruct practical scan helpers from canonical storage

The important point is that rebuild is a helper-state operation.

## When Rebuild Is Not Enough

Rebuild is not enough when the problem lives in canonical history itself.

Examples include:

- unreadable canonical segment lines
- truncated canonical tails
- sequence gaps in the canonical append order

In these cases, rebuild may still be useful later, but it does not solve the underlying problem by itself.

## When Repair Is The Right Tool

Repair is appropriate only when the damage matches a known repairable pattern, especially truncated segment tails.

In practice, that means:

- the trailing line is damaged
- the valid prefix before it is still readable
- preserving the original damaged segment in quarantine is acceptable
- trimming the damaged suffix is a reasonable canonical intervention

This matters because repair should be narrow and explicit. It is not meant to be a general-purpose "fix the store" button.

## When Repair Is The Wrong Tool

Repair is the wrong tool when:

- the damage is not a known truncated-tail case
- you do not yet understand the canonical problem
- you are trying to recover missing truth that no longer exists
- you only need helper indexes rebuilt
- you are treating repair as casual maintenance instead of a canonical intervention

This matters because unsafe repair can blur the line between recovery and accidental history rewriting.

## What Repair Reports Mean

Repair operations return a `RepairReport`.

That report can include:

- `success`
- `repaired_segments`
- `quarantined_paths`
- `rebuilt_indexes`
- `integrity_state`
- `notes`
- `warnings`

The important point is that repair reporting is trying to preserve auditability. It tells you what happened, what files were touched, what got quarantined, and what integrity state remains afterward.

## What `success` Means In Rebuild And Repair

One subtle but important point is that `success` is contextual.

For rebuild:

- helper indexes may be rebuilt successfully
- but if the canonical store is still corrupted, the report may still mark `success=False`

For repair:

- the repair path may complete
- but the final integrity state still determines whether the result is actually healthy

That matters because "the maintenance action ran" is not the same thing as "the store is now healthy."

## What `integrity_state` In `RepairReport` Means

`integrity_state` tells you the post-operation health classification of the store.

This is especially useful because maintenance actions can have outcomes such as:

- rebuild completed but the store is still corrupted
- repair completed and the store is now healthy
- no repair was necessary and the state remains whatever integrity currently says it is

This field is one of the clearest ways to avoid over-trusting the fact that a command merely ran to completion.

## Why `quarantined_paths` Matter

When repair trims a damaged tail, the original segment is first copied into `quarantine/`.

That means `quarantined_paths` are important because they tell you:

- which original file was preserved
- where to inspect the pre-repair damage
- what canonical file was altered during the repair process

This is not optional decoration. It is part of how `Stream` keeps repair explicit rather than secretive.

## A Typical Integrity Workflow

A practical integrity workflow often looks like this:

1. run `check_integrity()`
2. inspect `state`, `issues`, and `recommendations`
3. decide whether you need direct segment inspection
4. decide whether tolerant replay is acceptable for immediate read needs
5. decide whether rebuild is enough or repair is justified
6. run rebuild or repair
7. run integrity again
8. re-run strict replay if health has been restored

This matters because safe maintenance in `Stream` is iterative and explicit rather than magical.

## CLI Examples

Run an integrity check:

```powershell
stream-cli --store .stream-store integrity
```

Rebuild derivative indexes:

```powershell
stream-cli --store .stream-store rebuild-indexes
```

Repair truncated tails:

```powershell
stream-cli --store .stream-store repair
```

These commands are useful because they expose the same operating model as the Python API without hiding any of the important semantics.

## Python API Examples

Run integrity directly:

```python
report = store.check_integrity()

print(report.healthy)
print(report.state)
print(report.issues)
print(report.recommendations)
```

Rebuild indexes:

```python
repair_report = store.rebuild_indexes()

print(repair_report.success)
print(repair_report.integrity_state)
print(repair_report.warnings)
```

Repair truncated tails:

```python
repair_report = store.repair_truncated_tails()

print(repair_report.success)
print(repair_report.repaired_segments)
print(repair_report.quarantined_paths)
print(repair_report.integrity_state)
```

## Common Mistakes In Integrity Handling

### Treating `strict` Replay Failure As The Problem

The problem is usually the corruption, not the fact that `strict` replay refused to normalize it away.

### Using `tolerant` Replay As A Way To Avoid Diagnosis

Tolerant replay is useful, but it should not replace understanding the integrity report.

### Treating Rebuild As If It Restores Missing Truth

Rebuild restores helper indexes. It does not restore unreadable or missing canonical lines.

### Treating Repair As Routine Maintenance

Repair changes canonical tails in specific known cases. It should feel deliberate.

### Ignoring Post-Operation Integrity State

A command can run successfully while the store remains unhealthy. Always inspect the resulting integrity state.

## Operational Meaning Of A Healthy Result

A healthy integrity result usually means:

- segment lines were readable
- append order was coherent
- manifest frontier matched observed history closely enough
- no error-severity integrity issues were found

That gives you the strongest basis for trusting `strict` replay.

## Operational Meaning Of A Corrupted Result

A corrupted integrity result means the store should not be treated as intact ordered canonical history.

That does not always mean the store is useless. It does mean:

- `strict` replay should not proceed
- any tolerant interpretation should remain explicitly partial
- maintenance decisions should be made carefully and intentionally

That is the whole reason the integrity surface exists.

## A Good Integrity-Side Checklist

Before moving on, it is worth checking that your maintenance mental model now includes all of the following:

1. integrity is an explicit judgment about coherent canonical history
2. warning-severity and error-severity issues do not mean the same thing
3. `strict` replay failure is often the correct protective behavior
4. tolerant replay is useful only when its incompleteness remains explicit
5. rebuild restores derivative helpers, not lost truth
6. repair is a narrow canonical intervention, not a casual refresh
7. post-operation integrity state matters more than the fact that a command returned

## What To Read Next

Read [CLI Reference](/Users/eastl/MLObservability/Stream/docs/en/cli-reference.md) next if you want exact command shapes and JSON payloads for integrity, replay, export, rebuild, and repair workflows.

Read [API Reference](/Users/eastl/MLObservability/Stream/docs/en/api-reference.md) next if you want the public Python surfaces for the same operations.

Read [FAQ](faq.md) next if you want short answers to recurring questions such as why indexes are not authoritative, why `strict` replay fails, and why repair should be treated carefully.
