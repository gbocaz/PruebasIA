export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export function ConfirmButton({ className, children, message, onConfirm }) {
  return (
    <button
      className={className}
      onClick={() => {
        if (window.confirm(message)) onConfirm();
      }}
    >
      {children}
    </button>
  );
}

export function Bar({ value, max = 100, suffix = "%" }) {
  const pct = max ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="bar">
      <span style={{ width: `${pct}%` }} />
      <div className="label">
        {Number(value).toFixed(0)} {suffix}
      </div>
    </div>
  );
}
