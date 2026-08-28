import unittest

from securecore.package_api.contracts import (
    SecureCorePackageError,
    SecureCoreRequest,
    SecureCoreResponse,
    validate_request,
    validate_response,
)


class PackageContractsTests(unittest.TestCase):
    def test_anchorworks_read_request_validates(self):
        request = SecureCoreRequest(
            request_id="req-1",
            caller="anchorworks",
            route="status.summary",
            purpose="read status",
        )

        self.assertEqual(validate_request(request).route, "status.summary")

    def test_missing_request_id_rejected(self):
        request = SecureCoreRequest(
            request_id="",
            caller="anchorworks",
            route="status.summary",
            purpose="read status",
        )

        with self.assertRaises(SecureCorePackageError):
            validate_request(request)

    def test_unknown_route_rejected(self):
        request = SecureCoreRequest(
            request_id="req-2",
            caller="anchorworks",
            route="agent.launch",
            purpose="nope",
        )

        with self.assertRaises(SecureCorePackageError):
            validate_request(request)

    def test_response_is_facts_warnings_and_evidence_only(self):
        response = SecureCoreResponse(
            request_id="req-3",
            status="ok",
            facts=["Fusion latest block is intact."],
            evidence_refs=["fusion:block:abc"],
            warnings=[],
        )

        self.assertEqual(validate_response(response).status, "ok")

    def test_response_with_facts_requires_evidence_refs(self):
        response = SecureCoreResponse(
            request_id="req-4",
            status="ok",
            facts=["Some fact"],
            evidence_refs=[],
            warnings=[],
        )

        with self.assertRaises(SecureCorePackageError):
            validate_response(response)


if __name__ == "__main__":
    unittest.main()
