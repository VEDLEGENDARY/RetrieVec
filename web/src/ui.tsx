import { type ComponentProps, type ReactNode } from "react";

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

export function More({
  children,
  label = "More options",
  ...props
}: ComponentProps<"details"> & { label?: string }) {
  return (
    <details {...props} className={`more-options ${props.className ?? ""}`}>
      <summary>{label}</summary>
      <div className="more-body">{children}</div>
    </details>
  );
}
export function Skeleton({ label = "Loading…" }: { label?: string }) {
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
