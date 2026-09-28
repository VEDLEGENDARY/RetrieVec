import unittest

from retrievec.contracts import encoded, specification


class ContractTests(unittest.TestCase):
    def test_export_is_deterministic_and_all_schema_references_resolve(self):
        self.assertEqual(encoded(), encoded())
        document = specification()
        ids = []

        def visit(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    self.assertTrue(value["$ref"].startswith("#/"))
                    target = document
                    for part in value["$ref"][2:].split("/"):
                        target = target[part.replace("~1", "/").replace("~0", "~")]
                if "operationId" in value:
                    ids.append(value["operationId"])
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(document)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 10)
        self.assertEqual(
            document["paths"]["/api/v1/me"]["get"]["security"], [{"browserSession": []}]
        )
