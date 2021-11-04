[![PyPI version](https://badge.fury.io/py/patchdiff.svg)](https://badge.fury.io/py/patchdiff)
[![CI status](https://github.com/Korijn/patchdiff/workflows/CI/badge.svg)](https://github.com/Korijn/patchdiff/actions)

# Patchdiff 🔍

## Install

`pip install patchdiff`

## Quick-start

```python
from patchdiff import apply, diff, iapply, to_json

input = {"a": [5, 7, 9, {"a", "b", "c"}], "b": 6}
output = {"a": [5, 2, 9, {"b", "c"}], "b": 6, "c": 7}

ops, reverse_ops = diff(input, output)

assert apply(input, ops) == output
assert apply(output, reverse_ops) == input

iapply(input, ops)  # apply in-place
assert input == output

print(to_json(ops, indent=4))
# [
#     {
#         "op": "add",
#         "path": "/c",
#         "value": 7
#     },
#     {
#         "op": "replace",
#         "path": "/a/1",
#         "value": 2
#     },
#     {
#         "op": "remove",
#         "path": "/a/3/a"
#     }
# ]
```
