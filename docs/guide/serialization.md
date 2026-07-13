# Serialization

Operation lists are plain data (dicts with `"op"`, `"path"` and `"value"` keys) except for the paths, which are [`Pointer`][patchdiff.pointer.Pointer] objects. [`to_json`][patchdiff.serialize.to_json] renders the paths to their JSON pointer string form and serializes the whole list to an RFC 6902 JSON patch document:

```python
from patchdiff import diff, to_json

ops, _ = diff({"a": [5, 7]}, {"a": [5, 2], "c": 7})

assert to_json(ops) == (
    '[{"op": "add", "path": "/c", "value": 7},'
    ' {"op": "replace", "path": "/a/1", "value": 2}]'
)
```

Keyword arguments are forwarded to `json.dumps`, so `indent`, `sort_keys`, `default`, etc. all work:

```python
from patchdiff import diff, to_json

ops, _ = diff({"a": 1}, {"a": 2})

print(to_json(ops, indent=4))
```

```json
[
    {
        "op": "replace",
        "path": "/a",
        "value": 2
    }
]
```

If you only want the paths stringified but not the JSON encoding, for example to hand patches to another JSON patch library or a different serializer, use [`to_str_paths`][patchdiff.serialize.to_str_paths]:

```python
from patchdiff import diff
from patchdiff.serialize import to_str_paths

ops, _ = diff({"a": 1}, {"a": 2})

assert to_str_paths(ops) == [{"op": "replace", "path": "/a", "value": 2}]
assert ops[0]["path"] != "/a"  # the original ops are not mutated
```

## Non-JSON values

Serialization is only lossless for JSON-representable structures. Two things to watch out for:

* **Values**: patches on structures containing sets, frozensets or tuples carry those objects in their `"value"` fields, and `json.dumps` can't encode them. Pass a `default=` to convert them (accepting that the type is lost), or keep such patches in memory instead.
* **Paths**: non-string pointer tokens (integer list indices, set members) are stringified. For lists that's exactly RFC 6901; for sets it means the *member itself* becomes a string token, which cannot be parsed back into the original value.

```python
from patchdiff import diff, to_json

ops, _ = diff({"tags": {"a"}}, {"tags": {"a", "b"}})

assert to_json(ops) == '[{"op": "add", "path": "/tags/-", "value": "b"}]'
```

See [gotchas](gotchas.md) for the full list of RFC 6902 divergences.
