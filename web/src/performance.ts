/** Local, opt-in diagnostics. Never retain queries, URLs, IDs, or source text. */
type Metric = "app.ready" | "retrieval.response" | "ui.event";
type Sample = { metric: Metric; duration_ms: number; outcome: "ok" | "error" };
const enabled = new URLSearchParams(location.search).get("performance") === "1";
const samples: Sample[] = [];
const limit = 200;

export function recordTiming(
  metric: Metric,
  duration: number,
  outcome: Sample["outcome"] = "ok",
) {
  if (!enabled || !Number.isFinite(duration) || duration < 0) return;
  samples.push({
    metric,
    duration_ms: Math.round(duration * 100) / 100,
    outcome,
  });
  if (samples.length > limit) samples.splice(0, samples.length - limit);
}

declare global {
  interface Window {
    retrievecPerformance?: {
      snapshot: () => Sample[];
      clear: () => void;
      eventTimingSupported: boolean;
    };
  }
}

if (enabled) {
  const supported =
    typeof PerformanceObserver !== "undefined" &&
    PerformanceObserver.supportedEntryTypes.includes("event");
  window.retrievecPerformance = {
    snapshot: () => samples.map((sample) => ({ ...sample })),
    clear: () => {
      samples.length = 0;
    },
    eventTimingSupported: supported,
  };
  if (supported) {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        // Event Timing includes input delay, processing, and next presentation.
        // Browser threshold/rounding means this is not a complete INP metric.
        recordTiming("ui.event", entry.duration);
      }
    });
    observer.observe({
      type: "event",
      buffered: true,
      durationThreshold: 16,
    } as PerformanceObserverInit);
  }
}
