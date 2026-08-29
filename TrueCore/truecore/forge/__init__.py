"""TrueCore Forge.

Forge is the pre-cutover binary storage foundation for TrueCore.
It is introduced beside the current JSONL truth stores, not as an
immediate replacement for them.

Current doctrine:
- substrates append
- forge stores
- loggers log
- agents infer
"""

from truecore.forge.reader import ForgeReader
from truecore.forge.pulse_writer import ForgePulseWriter, PulseConfig
from truecore.forge.record import ForgeRecord
from truecore.forge.sharded import ShardedForgeReader, ShardedForgeWriter
from truecore.forge.writer import ForgeWriter

__all__ = [
    "ForgePulseWriter",
    "ForgeReader",
    "ForgeRecord",
    "ForgeWriter",
    "PulseConfig",
    "ShardedForgeReader",
    "ShardedForgeWriter",
]
