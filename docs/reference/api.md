# API Reference

The public API is small: two ways to obtain patches ([`diff`][patchdiff.diff.diff] and [`produce`][patchdiff.produce.produce]), two ways to apply them ([`apply`][patchdiff.apply.apply] and [`iapply`][patchdiff.apply.iapply]), and serialization helpers. All of these can be imported directly from `patchdiff`. The [`Pointer`][patchdiff.pointer.Pointer] class lives in `patchdiff.pointer`.

## Diffing

::: patchdiff.diff.diff

## Applying patches

::: patchdiff.apply.apply

::: patchdiff.apply.iapply

## Proxy-based patch generation

::: patchdiff.produce.produce

## Serialization

::: patchdiff.serialize.to_json

::: patchdiff.serialize.to_str_paths

## Pointers

::: patchdiff.pointer.Pointer

::: patchdiff.pointer.escape

::: patchdiff.pointer.unescape
