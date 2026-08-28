"""SecureCore creator/security harness.

The harness is a deterministic map over SecureCore's own registries. It can
describe components, draft creation guidance, and choose candidate capabilities.
It cannot execute tools or grant policy authority.
"""

from securecore.harness.knowledge import SecureCoreHarness

__all__ = ["SecureCoreHarness"]

