"""Deterministic plumbing fixture. Never loaded by production provider configuration."""

import asyncio
import json

from retrievec.app.answers import abstention
from retrievec.app.generation import ProviderError


class FixtureProvider:
    def __init__(self, config):
        self.config = config

    async def count(self, text):
        return len(text.encode("utf-8")) // 3 + 1

    async def generate(self, text, schema):
        data = json.loads(text.split("<|im_start|>user\n", 1)[1].split("<|im_end|>", 1)[0])
        question = data["question"].lower()
        question = question.rsplit("follow-up question: ", 1)[-1]
        if "invalid-answer" in question:
            return json.dumps({"status": "answered", "claims": [{"text": "UNVERIFIED_SENTINEL"}]})
        if "provider-failure" in question:
            raise ProviderError("test-only failure")
        if "cancel" in question:
            await asyncio.sleep(4)
        if "no-evidence" in question:
            return json.dumps(abstention("The retrieved evidence does not answer this question"))
        item = data["evidence"][0]
        quote = item["text"].split(".")[0] + "."
        return json.dumps(
            {
                "status": "answered",
                "claims": [
                    {
                        "id": "claim_1",
                        "text": quote,
                        "evidence_ids": [item["evidence_id"]],
                        "support_status": "structurally_valid",
                        "quotes": [{"evidence_id": item["evidence_id"], "text": quote}],
                    }
                ],
                "comparisons": [],
                "limitations": ["Deterministic fixture; not real-model quality evidence."],
            }
        )
