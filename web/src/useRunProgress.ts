import { useEffect, useState } from "react";

type Preview = {
  title: string;
  text: string;
  page_range: number[] | null;
  evidence_id: string;
};
/** Native SSE reconnection resumes event IDs; final run polling reauthorizes publication. */
export function useRunProgress(
  runId: string | null,
  active: boolean,
  refresh: () => void,
) {
  const [sources, setSources] = useState<Preview[]>([]);
  useEffect(() => {
    setSources([]);
    if (!runId || !active) return;
    const events = new EventSource(
      `/api/v1/runs/${encodeURIComponent(runId)}/events`,
    );
    let last = 0;
    const listen = (
      type: string,
      apply: (data: Record<string, unknown>) => void,
    ) => {
      events.addEventListener(type, (event) => {
        const message = event as MessageEvent;
        const sequence = Number(message.lastEventId);
        if (!Number.isSafeInteger(sequence) || sequence <= last) return;
        try {
          const data = JSON.parse(message.data);
          if (data.run_id !== runId) return;
          apply(data);
          last = sequence;
        } catch {
          events.close();
          setSources([]);
        }
      });
    };
    listen("evidence_ready", (data) => {
      if (
        !Array.isArray(data.evidence) ||
        data.evidence.length > 100 ||
        data.evidence.some(
          (item) =>
            !item ||
            typeof item.title !== "string" ||
            typeof item.text !== "string" ||
            typeof item.evidence_id !== "string",
        )
      )
        throw Error("Invalid evidence event");
      setSources(data.evidence as Preview[]);
    });
    for (const stage of [
      "queued",
      "retrieving",
      "generating",
      "validating",
      "completed",
      "failed",
      "cancelled",
    ]) {
      listen(stage, () => {
        if (["completed", "failed", "cancelled"].includes(stage))
          setSources([]);
        refresh();
      });
    }
    return () => events.close();
  }, [runId, active, refresh]);
  return { sources };
}
