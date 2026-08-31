"""Compatibility imports for the historical HotpotQA benchmark.

The implementation is native TrueMem machinery and contains no benchmark
identity, expected answer, gold-document rule, or dataset-specific constant.
"""

from truemem.engine.xpu_relationship_index import (
    XpuAnswerWalker,
    XpuRelationshipIndex,
    _assert_xpu,
    _lexicographic_order,
)

__all__ = ["XpuAnswerWalker", "XpuRelationshipIndex", "_assert_xpu", "_lexicographic_order"]
