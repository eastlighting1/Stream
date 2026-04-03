# Stream User Guide (EN)

`Stream` documentation should help a new user answer a practical question first: "how should I use
this library as the append-oriented canonical record store in a local Python workflow?" Before
reading every storage detail, it is more useful to understand what `Stream` owns, what it does not
own, and how a normal write-read-repair flow should feel in day-to-day use.

## Start Here

- [Getting Started](en/getting-started.md)
- [Mental Model](en/mental-model.md)
- [Write Path](en/write-path.md)
- [Read Path](en/read-path.md)
- [Layout and Storage](en/layout-and-storage.md)
- [Integrity and Repair](en/integrity-and-repair.md)
- [CLI Reference](en/cli-reference.md)
- [API Reference](en/api-reference.md)
- [Examples](en/examples.md)
- [FAQ](en/faq.md)

## Recommended Reading Order

1. Start with [English Docs Home](USER_GUIDE.en.md) if you want the documentation map before
   jumping into individual tasks.
2. Read [Getting Started](en/getting-started.md) for the smallest successful `StreamStore` flow.
3. Read [Mental Model](en/mental-model.md) to understand what `Stream` owns, what is canonical
   truth, and what remains derivative.
4. Read [Write Path](en/write-path.md) to understand accepted records, append semantics, batching,
   and validation boundaries.
5. Read [Read Path](en/read-path.md) to understand the difference between `scan`, `replay`,
   tolerant reads, and JSONL export.
6. Read [Layout and Storage](en/layout-and-storage.md) to understand `manifest.json`,
   `segments/*.jsonl`, derivative indexes, and what should be trusted on disk.
7. Read [Integrity and Repair](en/integrity-and-repair.md) when you need to interpret corruption,
   rebuild indexes, or repair truncated tails safely.
8. Use [CLI Reference](en/cli-reference.md) when you want exact command-line shapes and output payloads.
9. Use [API Reference](en/api-reference.md) when you want exact public Python imports, methods, result models, and exceptions.
10. Use [Examples](en/examples.md) and [FAQ](en/faq.md) as quick follow-up references once the
    main concepts are familiar.

If you are new to `Stream`, reading `Getting Started`, `Mental Model`, and `Write Path` first is
usually enough to begin using the library correctly. The storage and repair pages become more
important once the store starts serving as operational history instead of a toy example.

## What This Documentation Optimizes For

`Stream` is not the metadata anchor store, the analytics layer, or the visualization surface of the
stack. It is the append-oriented local store for canonical observability records. Because of that,
the most important documentation questions are usually:

- where should a `StreamStore` live in an application or experiment workflow
- what should be appended as canonical history, and what should stay outside the store
- when should callers prefer `scan` versus `replay`
- how should tolerant replay warnings and known gaps be interpreted
- what on-disk state is canonical, and what is only rebuildable helper state
- when is it safe to rebuild indexes, and when is a real repair step required

So the docs are organized around storage behavior and operational interpretation, not around module
names alone.

## What Stream Does

At a high level, `Stream` helps code do six things:

- append canonical records one-by-one or in batches
- preserve append order as local JSONL segment history
- scan stored records by practical filters such as run, stage, record type, and time
- replay canonical history in `strict` or `tolerant` mode
- export replayed history to JSONL for downstream inspection
- diagnose corruption and repair known damaged-tail cases while keeping canonical truth explicit

The normal usage pattern looks like this:

```text
create StreamStore
  -> append canonical records during execution
    -> scan or replay local history for inspection
      -> export replayed history when another tool needs JSONL output
        -> run integrity checks if corruption or drift is suspected
          -> rebuild indexes or repair truncated tails only when needed
```

This is intentionally narrower than a general-purpose event database. `Stream` is optimized for an
inspectable local record history that stays understandable even when the surrounding stack changes.

## How The Pages Are Split

The current pages are grouped by user task rather than by internal package layout.

- `Getting Started`
  - first successful append, scan, replay, and CLI flow
- `Mental Model`
  - role, boundaries, source-of-truth rules, and storage ownership
- `Write Path`
  - accepted records, append behavior, batching, durability, and validation
- `Read Path`
  - scan, replay, tolerant reads, and export behavior
- `Layout and Storage`
  - manifest, segments, derivative indexes, sequence flow, and storage trust boundaries
- `Integrity and Repair`
  - integrity interpretation, rebuild behavior, and truncated-tail recovery
- `CLI Reference`
  - exact command shapes, options, and output payloads
- `API Reference`
  - exact public imports, methods, models, and exceptions
- `Examples`
  - scenario-based reading paths into example code
- `FAQ`
  - short answers to recurring operational and conceptual questions

This is intentional. Most confusion in `Stream` comes from questions like "what is canonical
truth?", "what should I trust on disk?", and "what should I do after corruption?" rather than from
questions like "what file contains which class?"

## What To Read If You Are In A Hurry

If you only have a few minutes, read these three pages first:

1. [Getting Started](en/getting-started.md)
2. [Mental Model](en/mental-model.md)
3. [Read Path](en/read-path.md)

Those pages are enough to understand:

- the basic runtime shape of `Stream`
- what the canonical on-disk boundary looks like
- how to choose between append, scan, replay, and export

## Relationship To Spine And The Rest Of The Stack

`Stream` sits alongside the rest of the ML observability stack, but its responsibility is specific.

- `Spine` defines canonical record contracts and validation vocabulary
- capture-side libraries produce the runtime facts that become canonical records
- `Stream` stores those canonical records locally in append order and helps operators read or
  recover that history safely

If you need deep schema meaning or record-shape semantics, the relevant place is usually `Spine`.
If you need to understand local canonical history, replay behavior, corruption handling, and
repair-oriented store operations, the relevant place is `Stream`.

## Related Files

- Project README: [README.md](../README.md)
- English docs home: [docs/USER_GUIDE.en.md](USER_GUIDE.en.md)
- Package entrypoint: [src/stream/__init__.py](../src/stream/__init__.py)
- Public store API: [src/stream/api/store.py](../src/stream/api/store.py)
- CLI entrypoint: [src/stream/cli.py](../src/stream/cli.py)
- Basic example: [examples/basic_usage.py](../examples/basic_usage.py)
