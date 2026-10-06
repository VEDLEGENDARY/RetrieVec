import { Disclosure } from "./ui";

export type PaperMetadata = {
  authors?: string[];
  year?: number | null;
  doi?: string | null;
  metadata_provenance?: Record<string, unknown>;
};

export function PaperDetails({ paper }: { paper: PaperMetadata }) {
  if (
    !paper.metadata_provenance &&
    !paper.authors?.length &&
    !paper.year &&
    !paper.doi
  )
    return null;
  return (
    <Disclosure>
      <summary>Source metadata</summary>
      <dl>
        <dt>Authors</dt>
        <dd>
          {paper.authors?.length ? paper.authors.join(", ") : "Not reported"}
        </dd>
        <dt>Year</dt>
        <dd>{paper.year ?? "Not reported"}</dd>
        <dt>DOI</dt>
        <dd>{paper.doi ?? "Not reported"}</dd>
      </dl>
      {paper.metadata_provenance && (
        <Disclosure>
          <summary>Metadata provenance</summary>
          <p>
            External bibliographic metadata may be associated with a
            user-provided source without independent verification.
          </p>
          <pre>{JSON.stringify(paper.metadata_provenance, null, 2)}</pre>
        </Disclosure>
      )}
    </Disclosure>
  );
}
