from typing import NamedTuple, Optional

from .._concurrency import MemorySendChannel


class Config(NamedTuple):
    include_index: bool
    send_to: Optional[MemorySendChannel]
