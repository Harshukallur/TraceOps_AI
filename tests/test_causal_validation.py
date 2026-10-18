import unittest

from app.mcp_agent import validate_report


class TestCausalValidation(unittest.TestCase):
    def test_explicit_non_causation_claim_does_not_warn(self):
        report = (
            "The graph records a relationship between the deployment "
            "and incident. This relationship does not prove that the "
            "deployment caused the incident."
        )

        warnings = validate_report(
            report=report,
            evidence=[],
            service_name="Payment API",
        )

        causal_warnings = [
            warning
            for warning in warnings
            if "causal or root-cause claim" in warning.lower()
        ]

        self.assertEqual(
            causal_warnings,
            [],
            f"Unexpected causal warning: {causal_warnings}",
        )

    def test_unsupported_positive_causal_claim_warns(self):
        report = (
            "The deployment caused the incident."
        )

        warnings = validate_report(
            report=report,
            evidence=[],
            service_name="Payment API",
        )

        causal_warnings = [
            warning
            for warning in warnings
            if "causal or root-cause claim" in warning.lower()
        ]

        self.assertTrue(
            causal_warnings,
            "Expected a warning for an unsupported causal claim.",
        )


if __name__ == "__main__":
    unittest.main()
