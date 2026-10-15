import {
  cloneElement,
  useId,
  type ComponentProps,
  type ReactElement,
  type ReactNode,
} from "react";

export function Button({
  variant,
  loading,
  className = "",
  disabled,
  children,
  ...props
}: ComponentProps<"button"> & {
  variant?: "primary" | "secondary" | "quiet";
  loading?: boolean;
}) {
  return (
    <button
      {...props}
      className={`${variant ?? ""} ${className}`.trim()}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      {children}
    </button>
  );
}
export function Input(props: ComponentProps<"input">) {
  return <input {...props} />;
}
export function Select(props: ComponentProps<"select">) {
  return <select {...props} />;
}
export function Textarea(props: ComponentProps<"textarea">) {
  return <textarea {...props} />;
}

export function ActionLink({
  className = "",
  variant,
  ...props
}: ComponentProps<"a"> & { variant?: "primary" | "quiet" }) {
  return (
    <a {...props} className={`button ${variant ?? ""} ${className}`.trim()} />
  );
}
export function IconButton(
  props: ComponentProps<typeof Button> & { "aria-label": string },
) {
  return (
    <Button {...props} className={`icon-button ${props.className ?? ""}`} />
  );
}
type Control = {
  id?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: ComponentProps<"input">["aria-invalid"];
};
export function Field({
  label,
  description,
  error,
  children,
  className = "",
}: {
  label: ReactNode;
  description?: ReactNode;
  error?: ReactNode;
  children: ReactElement<Control>;
  className?: string;
}) {
  const generated = useId();
  const id = children.props.id ?? generated;
  const describedBy =
    [
      children.props["aria-describedby"],
      description ? `${id}-description` : null,
      error ? `${id}-error` : null,
    ]
      .filter(Boolean)
      .join(" ") || undefined;
  return (
    <div className={`field ${className}`.trim()}>
      <label htmlFor={id}>{label}</label>
      {cloneElement(children, {
        id,
        "aria-invalid": error ? true : children.props["aria-invalid"],
        "aria-describedby": describedBy,
      })}
      {description && (
        <p id={`${id}-description`} className="field-description">
          {description}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="file-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
export function Surface({
  as: Tag = "section",
  className = "",
  ...props
}: Omit<ComponentProps<"div">, "ref"> & {
  as?: "section" | "article" | "div" | "header";
}) {
  return (
    <Tag
      {...props}
      data-material="solid"
      className={`surface ${className}`.trim()}
    />
  );
}
/** Keeps native summary keyboard behavior and each caller's open state. */
export function Disclosure({
  className = "",
  ...props
}: ComponentProps<"details">) {
  return <details {...props} className={`disclosure ${className}`.trim()} />;
}
/** Callers retain modal lifetime, focus return, shortcuts, and cancellation. */
export function NativeDialog({
  className = "",
  ...props
}: ComponentProps<"dialog">) {
  return <dialog {...props} className={`native-dialog ${className}`.trim()} />;
}
export function StatusBadge({
  children,
  tone = "info",
  className = "",
  ...props
}: ComponentProps<"span"> & { tone?: "info" | "error" | "success" }) {
  return (
    <span {...props} className={`status-badge ${tone} ${className}`.trim()}>
      {children}
    </span>
  );
}
export function More({
  children,
  label = "More options",
  ...props
}: ComponentProps<"details"> & { label?: string }) {
  return (
    <Disclosure {...props} className={`more-options ${props.className ?? ""}`}>
      <summary>{label}</summary>
      <div className="more-body">{children}</div>
    </Disclosure>
  );
}
export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="loading-state" role="status" aria-busy="true">
      <p>{label}</p>
      <div aria-hidden="true" className="skeleton" />
      <div aria-hidden="true" className="skeleton short" />
    </div>
  );
}
export function Notice({
  children,
  error = false,
  action,
}: {
  children: ReactNode;
  error?: boolean;
  action?: ReactNode;
}) {
  return (
    <div
      className={error ? "error" : "interaction-notice"}
      role={error ? "alert" : "status"}
    >
      {children}
      {action}
    </div>
  );
}
export function EmptyState({
  title,
  children,
  action,
  icon,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <Surface className="empty">
      {icon && <span className="empty-symbol">{icon}</span>}
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </Surface>
  );
}
