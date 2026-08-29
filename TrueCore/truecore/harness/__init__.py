"""TrueCore creator/security harness.

The harness is a deterministic map over TrueCore's own registries. It can
describe components, draft creation guidance, and choose candidate capabilities.
It cannot execute tools or grant policy authority.
"""

from truecore.harness.knowledge import TrueCoreHarness

__all__ = ["TrueCoreHarness"]

