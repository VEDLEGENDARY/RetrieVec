const phases = ["Retrieving", "Generating", "Validating", "Saved"];
export function RunStatus({
  state,
}: {
  state: string;
  errorCode: string | null;
}) {
  const current =
    state === "completed"
      ? 3
      : state === "validating"
        ? 2
        : state === "generating"
          ? 1
          : state === "failed" || state === "cancelled"
            ? -1
            : 0;
  return (
    <ol className="run-status-strip" aria-label="Research progress">
      {phases.map((phase, index) => (
        <li
          key={phase}
          aria-current={index === current ? "step" : undefined}
          data-state={
            index < current
              ? "complete"
              : index === current
                ? state === "failed" || state === "cancelled"
                  ? "stopped"
                  : "current"
                : "pending"
          }
        >
          <span>{phase}</span>
          {index === current && state === "queued" && (
            <small>Waiting for the worker</small>
          )}
          {index === current && state === "failed" && <small>Failed</small>}
          {index === current && state === "cancelled" && (
            <small>Cancelled</small>
          )}
        </li>
      ))}
    </ol>
  );
}
