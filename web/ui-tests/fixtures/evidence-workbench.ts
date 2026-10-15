import type { Page } from "@playwright/test";
export async function evidenceWorkbench(
  target: Pick<Page, "route">,
  options: { onlyRequested?: boolean; gate?: Promise<void> } = {},
) {
  const requests: { query: string; retrieval: string }[] = [];
  const failures = new Set<string>();
  let failAll = false;
  await target.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/me"))
      return route.fulfill({
        json: { principal_id: "workbench-fixture", csrf_token: "fixture" },
      });
    if (path === "/api/v1/collections")
      return route.fulfill({
        json: ["one", "two"].map((id) => ({
          collection_id: id,
          title: `Evidence collection ${id}`,
          visibility: "private",
          can_manage: true,
          active_snapshot: `snapshot-${id}`,
        })),
      });
    if (path.endsWith("/papers") || path.endsWith("/runs"))
      return route.fulfill({ json: { items: [], next_cursor: null } });
    if (path === "/api/v1/search") {
      const body = route.request().postDataJSON();
      requests.push(body);
      if (options.gate) await options.gate;
      if (failAll || failures.has(body.retrieval))
        return route.fulfill({
          status: 503,
          json: {
            code: "retrieval_unavailable",
            message:
              "The requested retrieval method is unavailable. Retry the search.",
          },
        });
      const methods =
        body.retrieval === "compare" || !options.onlyRequested
          ? ["sparse", "dense", "hybrid"]
          : [body.retrieval];
      return route.fulfill({
        json: {
          collection_id: body.collection_id,
          snapshot_id: `snapshot-${body.collection_id}`,
          query: body.query,
          mode: body.mode,
          results: Object.fromEntries(
            methods.map((method) => {
              const ids =
                method === "dense"
                  ? ["c", "a", "b", "d", "e", "f", "g"]
                  : method === "hybrid"
                    ? ["b", "a", "c", "d", "e", "f", "g"]
                    : ["a", "b", "c", "d", "e", "f", "g"];
              return [
                method,
                {
                  hits: ids.map((id, index) => ({
                    chunk_id: `passage-${id}`,
                    title: `Synthetic paper ${id}`,
                    rank: index + 1,
                    text:
                      id === "g"
                        ? '<img src=x onerror="window.injected=true"><script>window.injected=true</script> Retrieval text stays literal.'
                        : `Sparse retrieval uses exact terms. Dense retrieval finds semantic neighbors. This retained passage ${id} is synthetic interface verification text.`,
                    page_range: [index + 1, index + 1],
                    source_id: "fixture-source",
                    source_sha256: "e".repeat(64),
                    bm25_score: 4 - index / 10,
                    cosine_score: 0.9 - index / 100,
                    rrf_score: 0.04 - index / 1000,
                  })),
                  total_matches: 7,
                  configuration: { fixture: true },
                },
              ];
            }),
          ),
        },
      });
    }
    if (path.includes("/sources/"))
      return route.fulfill({
        contentType: "text/html",
        body: "<!doctype html><html lang='en'><title>Synthetic source</title><body><p>Original source fixture.</p></body></html>",
      });
    return route.fulfill({ json: [] });
  });
  return {
    requests,
    failures,
    setFailAll: (value: boolean) => {
      failAll = value;
    },
  };
}
