
import unittest

from app.mcp_agent import (
    _natural_language_reversal_warnings,
    build_deterministic_dependency_section,
)


class TestDependencyDirection(unittest.TestCase):

    def setUp(self):
        self.evidence = [
            {
                "tool": "find_dependencies",
                "arguments": {"service_name": "Payment API"},
                "is_error": False,
                "result": [
                    {
                        "service": "Checkout",
                        "hops": 1,
                        "dependency_path": [
                            "Checkout",
                            "Payment API",
                        ],
                    },
                    {
                        "service": "Order Management",
                        "hops": 2,
                        "dependency_path": [
                            "Order Management",
                            "Checkout",
                            "Payment API",
                        ],
                    },
                ],
            }
        ]

        # The reversal checker expects paths, not complete evidence records.
        self.dependency_paths = [
            ["Checkout", "Payment API"],
            ["Order Management", "Checkout", "Payment API"],
        ]

    def test_correct_dependency_direction_is_preserved(self):
        section = build_deterministic_dependency_section(
            self.evidence
        )

        self.assertIn("Checkout -> Payment API", section)
        self.assertIn(
            "Order Management -> Checkout -> Payment API",
            section,
        )
        self.assertIn(
            "Checkout depends on Payment API",
            section,
        )
        self.assertNotIn(
            "Payment API depends on Checkout",
            section,
        )

    def test_reversed_dependency_claim_is_detected(self):
        incorrect_report = (
            "Payment API depends on Checkout. "
            "Checkout depends on Payment API."
        )

        warnings = _natural_language_reversal_warnings(
            incorrect_report,
            self.dependency_paths,
        )

        self.assertTrue(
            warnings,
            "A reversed dependency claim should produce a warning.",
        )

    def test_correct_dependency_claim_has_no_reversal_warning(self):
        correct_report = (
            "Checkout depends on Payment API. "
            "Order Management depends on Checkout."
        )

        warnings = _natural_language_reversal_warnings(
            correct_report,
            self.dependency_paths,
        )

        self.assertFalse(
            warnings,
            "Correct dependency claims should not produce warnings.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
