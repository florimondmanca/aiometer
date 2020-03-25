import itertools
from typing import Iterable, Iterator, Tuple, TypeVar

T = TypeVar("T")


def pairwise(iterable: Iterable[T]) -> Iterator[Tuple[T, T]]:
    """s -> (s0, s1), (s1, s2), (s2, s3), ..."""
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)
