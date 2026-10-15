import type { Collection, Session } from "./api";
import { SearchPage } from "./features/search/SearchPage";

export function Search(props: {
  collection: Collection;
  session: Session;
  fail: (error: unknown) => void;
}) {
  return (
    <SearchPage
      key={`${props.session.principal_id}:${props.collection.collection_id}`}
      {...props}
    />
  );
}
