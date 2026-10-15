import { useEffect, useLayoutEffect, useRef, type RefObject } from "react";

export function useCardReorder(
  list: RefObject<HTMLOListElement | null>,
  identity: string,
  method: string,
  rowIds: string,
) {
  const previous = useRef({
    identity,
    method,
    positions: new Map<string, { x: number; y: number }>(),
  });
  const animations = useRef<Animation[]>([]);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const stop = () => {
      if (media.matches)
        animations.current.forEach((animation) => animation.cancel());
    };
    media.addEventListener("change", stop);
    return () => {
      media.removeEventListener("change", stop);
      animations.current.forEach((animation) => animation.cancel());
    };
  }, []);
  useLayoutEffect(() => {
    animations.current.forEach((animation) => animation.cancel());
    animations.current = [];
    const positions = new Map<string, { x: number; y: number }>();
    const animate =
      previous.current.identity === identity &&
      previous.current.method !== method &&
      !matchMedia("(prefers-reduced-motion: reduce)").matches;
    const duration = parseFloat(
      getComputedStyle(document.documentElement).getPropertyValue(
        "--motion-slow",
      ),
    );
    list.current
      ?.querySelectorAll<HTMLElement>("[data-passage]")
      .forEach((card) => {
        const bounds = card.getBoundingClientRect(),
          id = card.dataset.passage!;
        const position = { x: bounds.left + scrollX, y: bounds.top + scrollY },
          before = previous.current.positions.get(id);
        positions.set(id, position);
        if (
          animate &&
          before &&
          (before.x !== position.x || before.y !== position.y)
        )
          animations.current.push(
            card.animate(
              [
                {
                  transform: `translate(${before.x - position.x}px, ${before.y - position.y}px)`,
                },
                { transform: "none" },
              ],
              { duration, easing: "ease-out" },
            ),
          );
      });
    previous.current = { identity, method, positions };
  }, [identity, method, rowIds, list]);
}
