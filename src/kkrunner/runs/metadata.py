"""JSON-only immutable application metadata, opaque to the execution layer."""

import json


class FrozenMetadata(dict):
    """JSON-encodable mapping whose descendants cannot be mutated in place."""

    def _immutable(self, *args, **kwargs):
        raise TypeError("Run metadata is immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _immutable


def freeze_metadata(value):
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise TypeError("Application metadata must be a mapping with string keys")

    # Reject objects, non-finite numbers, and non-JSON key types before freezing.
    def validate(item):
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise TypeError("Metadata keys must be strings")
            for v in item.values():
                validate(v)
        elif isinstance(item, (list, tuple)):
            for v in item:
                validate(v)

    validate(value)
    json.dumps(value, allow_nan=False)

    def freeze(item):
        if isinstance(item, dict):
            return FrozenMetadata((k, freeze(v)) for k, v in item.items())
        if isinstance(item, (list, tuple)):
            return tuple(freeze(v) for v in item)
        return item

    return freeze(value)
