from typing import List, Mapping

from ._types import T


def list_from_indexed_dict(dct: Mapping[int, T]) -> List[T]:
    """
    Given `{0: 'v_0', ..., n: 'v_N'}`, return `['v_0', ... 'v_n']`.
    """
    return [dct[index] for index in range(max(dct) + 1)]