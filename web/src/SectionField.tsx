import { Field, Select } from "./ui";

export function SectionField({
  value,
  onChange,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <Field
      label="Paper section"
      description="Filters the retrieved candidate pool. Sections require opt-in section-aware ingestion; older passages are unclassified."
    >
      <Select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">All sections</option>
        {[
          "abstract",
          "introduction",
          "methods",
          "results",
          "discussion",
          "conclusion",
          "references",
          "unclassified",
        ].map((section) => (
          <option key={section} value={section}>
            {section[0].toUpperCase() + section.slice(1)}
          </option>
        ))}
      </Select>
    </Field>
  );
}
