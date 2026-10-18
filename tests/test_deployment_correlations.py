
import json
import unittest

from app.mcp_agent import build_evidence_summary


class TestDeploymentCorrelations(unittest.TestCase):
    def test_deployment_incident_link_is_extracted(self):
        evidence = [
            {
                "tool": "get_incident_deployment_correlations",
                "is_error": False,
                "result": [
                    json.dumps({
                        "deployment_id": "DEP-208",
                        "deployment_version": "v2.4.1",
                        "deployment_status": "completed",
                        "deployment_description": "Payment API release",
                        "incident_id": "INC-1045",
                        "incident_title": "Payment errors after deployment",
                        "incident_severity": "high",
                        "incident_status": "investigating",
                        "service_name": "Payment API",
                        "service_status": "degraded",
                        "relationship": "Deployment FOLLOWED_BY Incident",
                        "causation_confirmed": False,
                    })
                ],
            }
        ]

        summary = build_evidence_summary(evidence)

        self.assertIn("deployment_correlations", summary)
        correlations = summary["deployment_correlations"]

        self.assertEqual(len(correlations), 1)
        self.assertEqual(correlations[0]["deployment_id"], "DEP-208")
        self.assertEqual(correlations[0]["incident_id"], "INC-1045")
        self.assertFalse(correlations[0]["causation_confirmed"])


if __name__ == "__main__":
    unittest.main()
