const kes = new Intl.NumberFormat("en-KE", {
  style: "currency",
  currency: "KES",
  maximumFractionDigits: 0,
});

export function formatKES(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "KES 0";
  const number = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(number)) return "KES 0";
  return kes.format(number);
}

export function formatNumber(value: string | number | null | undefined): string {
  const number = typeof value === "number" ? value : Number(value ?? 0);
  if (Number.isNaN(number)) return "0";
  return new Intl.NumberFormat("en-KE").format(number);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return `${formatDate(value)} · ${date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
}

export function initials(name: string | null | undefined): string {
  if (!name) return "?";
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function statusTone(status: string | null | undefined): "success" | "warning" | "danger" | "info" {
  switch ((status ?? "").toUpperCase()) {
    case "PAID":
    case "CONFIRMED":
    case "SENT":
    case "SUCCESS":
      return "success";
    case "PARTIAL":
    case "PENDING":
    case "UNMATCHED":
      return "warning";
    case "OVERDUE":
    case "FAILED":
    case "REVERSED":
      return "danger";
    default:
      return "info";
  }
}

export function monthLabel(value: string): string {
  const [year, month] = value.split("-").map(Number);
  if (!year || !month) return value;
  return new Date(year, month - 1, 1).toLocaleDateString("en-GB", {
    month: "short",
    year: "numeric",
  });
}
