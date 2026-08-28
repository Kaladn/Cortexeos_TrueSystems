import unittest

import securecore.live_agents as live_agents


class LiveAgentsStagingTests(unittest.TestCase):
    def test_live_agents_package_exists_without_runtime_registration(self):
        self.assertTrue(live_agents.__doc__)


if __name__ == "__main__":
    unittest.main()
