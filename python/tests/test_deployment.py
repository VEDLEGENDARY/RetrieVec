import unittest

from retrievec.deployment import render


class DeploymentTests(unittest.TestCase):
    def test_storage_scope_and_singleton_invariants(self):
        bundle = render(
            image="registry.example/retrievec@sha256:" + "a" * 64,
            origin="https://research.example",
            issuer="https://identity.example",
        )
        items = bundle["items"]
        self.assertFalse(
            any(item["kind"] in ("Secret", "HorizontalPodAutoscaler") for item in items)
        )
        workspace = next(
            item
            for item in items
            if item["kind"] == "Deployment" and item["metadata"]["name"] == "workspace"
        )
        self.assertEqual(workspace["spec"]["replicas"], 1)
        self.assertEqual(workspace["spec"]["strategy"]["type"], "Recreate")
        pod = workspace["spec"]["template"]["spec"]
        self.assertFalse(pod["automountServiceAccountToken"])
        container = pod["containers"][0]
        self.assertNotEqual(
            container["livenessProbe"]["httpGet"]["path"],
            container["readinessProbe"]["httpGet"]["path"],
        )
        self.assertEqual(len([v for v in pod["volumes"] if "persistentVolumeClaim" in v]), 2)

    def test_unpinned_image_and_insecure_origin_rejected(self):
        for image, origin in (
            ("retrievec:latest", "https://research.example"),
            ("retrievec@sha256:" + "a" * 64, "http://research.example"),
        ):
            with self.assertRaises(ValueError):
                render(image=image, origin=origin, issuer="https://identity.example")
