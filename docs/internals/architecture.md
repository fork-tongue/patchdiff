# Architecture

This page documents how patchdiff works under the hood. Nothing here is part of the public API — it exists so that contributors (and the curious) can find their way around the four core modules: `pointer.py`, `diff.py`, `apply.py` and `produce.py`.

## Pointers

A [`Pointer`][patchdiff.pointer.Pointer] is a tuple of reference tokens behind `__slots__`. Immutability is what makes sharing safe: `append` builds a *new* pointer from `(*tokens, token)`, so the diff recursion can hand the same prefix pointer to many child operations without copies or aliasing bugs. Tokens are kept in their native Python types — integers for list indices, arbitrary hashable values for set members — and only stringified (with RFC 6901 `~0`/`~1` escaping) when a pointer is rendered.

`Pointer.evaluate` resolves a path in two phases with deliberately different strictness:

* the walk **to the parent** is strict — a missing intermediate container raises, because silently landing on a partial parent would let `iapply` write to the wrong place;
* the **leaf** lookup tolerates `KeyError`/`IndexError`/`TypeError` and resolves to `None`, but only when the parent is a container that can be written into — a missing leaf is a legitimate target for an `"add"` (dict inserts, the list `-` append token).

## Diffing

`diff()` dispatches on duck type: both sides having `.append` means list, `.keys` means dict, `.add` means set — which is what lets observ proxies and other container look-alikes flow through unchanged. Everything else (scalars, tuples, frozensets, mismatched container kinds) is one `replace` op. The first check is always `input == output`; equal inputs short-circuit to empty patch lists.

### Lists: DP edit script with prefix/suffix trimming

`diff_lists` computes a minimal edit script in three steps:

1. **Trim.** The common prefix and suffix are stripped first, so the expensive part only covers the changed region — for the common case of a localized edit in a large list, this collapses the problem to a few elements.
2. **DP table.** A classic O(m·n) Levenshtein-style table is built over the trimmed region, where `dp[i][j]` is the cost of transforming the first `i` input elements into the first `j` output elements (add, remove and replace all cost 1).
3. **Traceback and padding.** Walking the table backwards yields the operations in reverse order, indexed in trimmed-sublist coordinates. A second pass re-emits them in application order while tracking a running `padding` offset: every applied `add` shifts subsequent indices up by one, every `remove` shifts them down. Adds that land past the end of the list become the `-` (append) token. When a `replace` pairs two containers, `diff` recurses into them with the element's pointer as the new prefix, so nested changes become deep paths instead of wholesale element replacement.

The reverse operations are built in the same traceback with input/output swapped, then ordered for reverse application.

### Dicts and sets

`diff_dicts` splits keys into three groups — input-only (`remove`), output-only (`add`), and common (recurse). `diff_sets` is the same with elements instead of keys: removals address the element value itself as the final token; additions use the `-` token. In both cases the reverse lists are assembled so that applying them in order undoes the forward list applied in order.

## Applying

`iapply` is a straight interpreter: for each patch it resolves `path.evaluate(obj)` to `(parent, key, _)`, then dispatches on the parent's duck type. Dict writes are direct; list writes convert numeric string keys (from parsed pointers) back to `int` and translate `add` at `-` into `append`; set `add` inserts the value, set `remove` discards the *key* (the addressed element). Patch values are `deepcopy`'d before writing so the patch list and the patched object never share mutable state. `apply` is literally `iapply(deepcopy(obj), patches)`.

## produce(): proxy-based recording

`produce()` wraps the draft in a proxy tree (`DictProxy` / `ListProxy` / `SetProxy`, dispatched by duck type) and lets the recipe mutate it. Three design decisions shape the implementation:

### Paths come from parent links, not stored strings

A proxy stores only its parent proxy and its key within that parent — never an absolute path. Its location is computed on demand by `_location()`, walking up to the root and collecting keys. This is what keeps recorded paths correct when the tree changes under a handed-out reference: when `insert(0, …)` shifts list elements, the list proxy renumbers the keys of its children (`_shift_cache`), and a child that was at index 0 now reports index 1 — no stored path to invalidate.

### Detachment stops recording

Each proxy keeps a registry (`_proxies`) of the child proxies it has handed out. Removing or replacing an element marks the corresponding child proxy *detached*: it still mutates its underlying data (so user code holding it keeps working), but `_location()` returns `None` and nothing gets recorded — its data will be captured by the snapshot of whatever write re-inserts it. Re-inserting a *detached* proxy directly is a move: `_adopt` re-attaches it at the new location, and later mutations through the held reference record at the new path. Adopting a still-attached proxy (or one wrapping duck-typed data) snapshots instead, since a value can only live in one place.

Parent links are **weak references**, so the proxy tree contains no cycles and is reclaimed by plain reference counting the moment `produce` returns. `PatchRecorder.finalize` additionally detaches the root, which severs every remaining proxy's path to the root — a proxy leaked out of the recipe can never append to the already-returned patch lists.

### Values are snapshotted at record time

Every non-scalar value that goes into a patch passes through `_snapshot`: a hand-rolled deep copy for the JSON-like types (dict, list, set, frozenset, tuple), which also replaces nested proxies with copies of their data; unknown types fall back to `copy.deepcopy`, which unwraps third-party proxies (like observ's) through their `__deepcopy__` hooks. Snapshotting at record time — not at finalize — is what makes patches immune to later mutations of the same object.

Forward patches are appended in order; reverse patches are also appended (O(1)) and reversed once in `finalize`, since reverse application order is the mirror of forward order. `record_replace` compares old and new first and skips no-op writes entirely.

### The proxy classes

`DictProxy`, `ListProxy` and `SetProxy` implement the full mutating API of their container (including in-place operators like `|=`, `+=`, `^=`), each method recording the equivalent patch(es) before or after delegating to the underlying data. Read-only methods don't need per-method logic and are generated onto the classes by `_add_reader_methods` as plain pass-throughs. Reads that return containers wrap the result in a child proxy (cached in `_proxies`), which is how deep mutation tracking works without ever copying the draft eagerly.
