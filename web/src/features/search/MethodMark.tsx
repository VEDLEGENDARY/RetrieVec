import type { Method } from "./types";
export function MethodMark({ method }: { method: Method }) {
  return (
    <span
      className="retrieval-mark"
      data-retrieval={method}
      aria-hidden="true"
    />
  );
}
