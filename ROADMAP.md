# Roadmap to patchdiff 1.0.0

This roadmap takes patchdiff from 0.3.x to its first stable release, following the same
program that took [observ](https://github.com/fork-tongue/observ) to 1.0.0 (observ
PRs #175–#197): a documentation site, full modern typing, hardened test and benchmark
suites, modern CI, and several rounds of foundational and micro optimization — each item
delivered as its own PR.

## Where patchdiff stands today (0.3.12)

- **Code**: `pointer.py`, `diff.py` (O(m·n) DP list diff with prefix/suffix trim),
  `apply.py` (per-patch `hasattr` dispatch, unconditional `deepcopy` of values),
  `produce.py` (Immer-style proxies with parent-link path tracking), `serialize.py`,
  `types.py`.
- **Typing**: old-style (`List`, `Dict`, bare `List` for op lists), no TypedDicts for
  operations, no `py.typed` marker, no type checker in CI.
- **Tests**: ~6,400 lines with 100% coverage enforced in CI — already strong, but
  missing property-based round-trip fuzzing and an RFC 6902 compliance corpus.
- **Benchmarks**: solid suite (list/dict/set diff, apply, pointer, produce-vs-diff), but
  the CI guard is the design observ replaced in #181/#187: a single master run vs a
  single PR run at `--benchmark-compare-fail=mean:5%`, which sits below the noise floor
  of GitHub-hosted runners.
- **CI**: one generation behind observ #182 (checkout v6, setup-uv v8.1.0, no uv
  caching, redundant steps).
- **Docs**: README only; no docs site.

## The PR series

Five tracks, roughly in order: infrastructure first (the rest relies on it), then
docs / typing / test hardening in any order, then the optimization iterations (measured
by the new benchmark guard and locked in by typing and property tests), capped by the
release PR.

### Track A — CI & benchmark infrastructure

**PR 1 — Modernize CI workflows** *(port of observ #182)*

- Bump all actions in `ci.yml` and `benchmark.yml`: checkout v7, setup-uv v8.3.2
  (SHA-pinned), upload-artifact v7 / download-artifact v8, action-gh-release v3
  (SHA-pinned).
- Enable uv caching (`enable-cache: true`, keyed on `pyproject.toml`, with a
  per-Python-version suffix in the test matrix).
- Trim steps: drop `uv sync` in the build job (`uv build` uses an isolated build env),
  drop checkout in the publish job (it only needs the dist artifact), drop the
  benchmark artifact upload.

**PR 2 — Noise-robust benchmark guard** *(port of observ #181 + #187)*

- Replace the single-run `--benchmark-compare-fail=mean:5%` gate with:
  - interleaved master/PR benchmark runs (A/B/A/B/A/B, 3 runs each),
  - `--benchmark-disable-gc` and `PYTHONHASHSEED=0` to remove the two dominant noise
    sources,
  - a `benchmarks/compare_runs.py` that fails a benchmark only when the *fastest* PR
    run is more than 25% slower than the *slowest* master run (per-benchmark medians).
- Document the threshold for what it is: a tripwire for gross accidental regressions,
  not a precision instrument. Deltas below it are measured deliberately with repeated
  local runs.

### Track B — Documentation

**PR 3 — MkDocs docs site + GitHub Pages deployment** *(port of observ #176)*

- MkDocs + Material theme + mkdocstrings (`mkdocs.yml` in the same shape as observ's),
  a `docs` dependency group, and a `docs.yml` workflow that builds with
  `uv sync --only-group docs` and deploys via `upload-pages-artifact`/`deploy-pages`.
- Content:
  - *Getting Started*: installation, quick start.
  - *Guide*: diffing, applying patches (`apply` vs `iapply`), JSON pointers,
    `produce()` and drafts (including `in_place`), serialization (`to_json`),
    observ integration, gotchas & best practices (set/tuple extensions vs strict
    RFC 6902, patch value snapshotting).
  - *Reference*: API reference generated from docstrings; add docstrings to `diff`,
    `apply`, `iapply`, `produce`, `to_json` and `Pointer` where missing (no behavior
    changes).
- Every code example executed and verified; the site builds warning-free with the exact
  CI recipe. Before the first deploy, GitHub Pages must be set to "GitHub Actions" as
  the source in the repository settings.

**PR 4 — Internals docs section** *(analog of observ #179)*

- Architecture documentation: the DP list diff with prefix/suffix trimming, traceback
  and index padding; reverse-op construction; `Pointer.evaluate` semantics (strict
  parent walk, tolerant leaf); and `produce`'s proxy design (parent links, on-demand
  path computation, detach semantics, `_snapshot`/`_unwrap`, the `PatchRecorder`).

**PR 5 — README rewrite** *(analog of observ #180)*

- Links up front (docs site, PyPI, CI), a sharper pitch, slimmed to pitch + quick
  example pointing at the docs site, and a referral to sibling project observ.

### Track C — Typing

**PR 6 — Runtime cleanups split out from the typing work** *(analog of observ #184)*

- Only the behavioral changes the typing PR needs, reviewable in isolation: introduce
  `Operation` TypedDict shapes in `types.py` (add/remove/replace ops carrying
  `path: Pointer`), use them in `serialize.py`, and normalize any signatures that
  type-check poorly. No public API changes.

**PR 7 — Full modern type hinting, checked with `ty` in CI** *(analog of observ #185, stacked on PR 6)*

- PEP 604 unions and builtin generics everywhere via `from __future__ import
  annotations` (the runtime floor stays Python 3.9); precise signatures —
  `diff(...) -> tuple[list[Operation], list[Operation]]`,
  `produce(...) -> tuple[Diffable, list[Operation], list[Operation]]`; a `py.typed`
  marker in the package.
- A `ty` dependency group, `[tool.ty]` config in `pyproject.toml` scoped to
  `patchdiff/` with `python-version = "3.9"`, and a dedicated Typecheck job in CI added
  to `publish`'s `needs`.
- Fix whatever genuine annotation bugs `ty` surfaces (observ found several).

### Track D — Test hardening

**PR 8 — Property-based round-trip tests + RFC 6902 compliance corpus**

- Hypothesis-based property tests (new dev dependency): for randomly generated nested
  structures of dicts, lists, sets, tuples and scalars, assert
  `apply(input, ops) == output`, `apply(output, rops) == input`, `iapply` equivalence,
  `to_json` round-trips through `Pointer.from_str`, and pointer escape/unescape
  round-trips.
- Vendor the applicable cases of the
  [json-patch-tests](https://github.com/json-patch/json-patch-tests) corpus; patchdiff
  deliberately extends RFC 6902 (sets, tuples), so divergent cases are skipped with
  documented reasons.
- The analog, in spirit, of observ #189: test the library's core promise directly.

### Track E — Optimization iterations

Each PR carries benchmark numbers in its body and is guarded by PR 2's tripwire. Two
foundational-design passes, then micro passes over each hot path.

**PR 9 — Foundational: replace the O(m·n) DP list diff with Myers O(ND)**

- `diff_lists` currently builds a full DP table over the changed region. With
  prefix/suffix trimming already in place, switch the changed-region diff to Myers'
  greedy algorithm (linear-space refinement if warranted). Patch semantics stay
  identical — the existing tests plus PR 8's properties pin behavior. Expected large
  wins on the `list-diff-similar` benchmark groups.

**PR 10 — Foundational: `produce()` hot-path design pass**

- Design-level wins in the proxy layer: avoid per-write `Pointer` allocation (record
  token paths as tuples until finalize), skip `_snapshot` for scalar values at the
  call site, cache `_location` walks where safe. Measured with the produce benchmark
  groups.

**PR 11 — Micro: diff + pointer pass** *(analog of observ's #190/#191/#194–#196 cluster)*

- Inner-loop trims in `diff_dicts`/`diff_sets` and the `diff_lists` traceback: op dict
  construction, bound methods, positional calls; `Pointer.append`/`evaluate`/`__str__`
  micro-costs.

**PR 12 — Micro: apply/iapply pass**

- Dispatch on the parent type once per patch instead of up to three `hasattr` checks,
  skip `deepcopy` for immutable scalar values, hoist the int-key conversion.

**PR 13 — Micro: produce trap-level pass** *(analog of observ #192/#193)*

- Cut per-call overhead in the `DictProxy`/`ListProxy`/`SetProxy` methods: no
  `**kwargs` where the wrapped method doesn't accept keywords, bind hot attributes to
  locals/closures, hoist repeated lookups out of loops; pin the call conventions with
  signature tests as observ did.

### Release

**PR 14 — Bump version to 1.0.0** *(analog of observ #197)*

- Version bump with a release-notes body covering features, correctness, docs and
  tooling, and headline before/after benchmark tables (median times, both versions run
  interleaved locally).

## Ground rules throughout

- Every change lands as its own reviewable PR; stacking only where required (PR 7 on
  PR 6).
- Optimization PRs land after PR 2 (trustworthy guard), PR 7 (typecheck holds the
  annotations) and PR 8 (property tests as the safety net).
- 100% test coverage stays enforced (`--cov-fail-under=100`) for the entire series.
