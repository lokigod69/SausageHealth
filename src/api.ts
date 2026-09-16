export type Store = "sausage" | "health" | "both";
export type Category =
  | "sales"
  | "stock"
  | "suppliers"
  | "expenses"
  | "team"
  | "walkthrough"
  | "other";
export type User = {
  id: string;
  name: string;
  email: string;
  role: "owner" | "manager" | "staff";
  stores: Store[];
};
export type Attachment = {
  id: string;
  name: string;
  size: number;
  sha256: string;
};
export type Entry = {
  id: string;
  store: Store;
  category: Category;
  title: string;
  notes: string;
  occurred_on: string;
  created_at: string;
  author_name: string;
  author_id: string;
  status: "needs_review" | "reviewed";
  attachments: Attachment[];
  reviewed_at: string | null;
  reviewer_name: string | null;
  review_note: string;
  version: number;
};

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch("/api" + path, {
      credentials: "same-origin",
      ...init,
      headers: {
        "X-SH-Request": "1",
        ...(init.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(
      "The connection was interrupted. Keep this page open and try again; we could not confirm the result.",
    );
  }
  if (!response.ok) {
    let message =
      "We could not confirm the result. Keep this page open and try again.";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* Keep a useful connection message. */
    }
    throw new ApiError(message, response.status);
  }
  try {
    return await response.json();
  } catch {
    throw new ApiError(
      "The server response was interrupted. Keep this page open and try again; we could not confirm the result.",
    );
  }
}

export async function submitEntry(form: FormData): Promise<Entry> {
  const system = await api<{ upload_mode?: string }>("/system");
  if (system.upload_mode !== "direct")
    return api<Entry>("/entries", { method: "POST", body: form });
  const files = form
    .getAll("files")
    .filter((file): file is File => file instanceof File);
  const manifest = [];
  for (const file of files) {
    const digest = await crypto.subtle.digest(
      "SHA-256",
      await file.arrayBuffer(),
    );
    manifest.push({
      name: file.name,
      size: file.size,
      sha256: Array.from(new Uint8Array(digest), (byte) =>
        byte.toString(16).padStart(2, "0"),
      ).join(""),
    });
  }
  const fields = Object.fromEntries(
    ["store", "category", "title", "notes", "occurred_on", "request_key"].map(
      (key) => [key, String(form.get(key) ?? "")],
    ),
  );
  const intent = await api<{
    entry?: Entry;
    id: string;
    files: { grant: string }[];
  }>("/upload-intents", {
    method: "POST",
    body: JSON.stringify({ ...fields, files: manifest }),
  });
  if (intent.entry) return intent.entry;
  for (let index = 0; index < files.length; index++) {
    const { url } = await api<{ url: string }>("/storage", {
      method: "POST",
      body: JSON.stringify({ grant: intent.files[index].grant }),
    });
    let response: Response;
    try {
      response = await fetch(url, {
        method: "PUT",
        credentials: "omit",
        headers: { "Content-Type": "application/octet-stream" },
        body: files[index],
      });
    } catch {
      throw new ApiError(
        "The file upload was interrupted. Keep this page open and retry.",
      );
    }
    // A lost response may mean the immutable original is already there. Finalization verifies its bytes.
    // Blob currently reports an existing no-overwrite path as 400/bad_request.
    // Neither 400 nor 409 proves success: the finalizer must verify every size/hash.
    if (!response.ok && response.status !== 400 && response.status !== 409)
      throw new ApiError(
        "The file upload could not be confirmed. Keep this page open and retry.",
      );
  }
  return api<Entry>(`/upload-intents/${intent.id}/finalize`, {
    method: "POST",
  });
}

export const storeNames: Record<Store, string> = {
  sausage: "The Sausage Guy",
  health: "Natural Mind Health",
  both: "Both stores",
};
export const categoryNames: Record<Category, string> = {
  sales: "Daily sales",
  stock: "Stock & products",
  suppliers: "Suppliers & purchases",
  expenses: "Running costs",
  team: "Team & routines",
  walkthrough: "Store walkthrough",
  other: "Other",
};
export const prompts: Record<
  Category,
  { hint: string; placeholder: string; title: string }
> = {
  sales: {
    title: "Share a day of sales",
    hint: "Add a Loyverse report, a photo of the daily total, or a WhatsApp text export. Include the date and store.",
    placeholder:
      "What did the report say? Include cash, GCash, card sales, refunds, and anything that needs explaining.",
  },
  stock: {
    title: "Add stock records",
    hint: "Start with a Loyverse product export or clear shelf/freezer photos. Exact counts can come later.",
    placeholder:
      "Which products are these? Include units (pack, piece, kg), quantities if known, and anything that expires soon.",
  },
  suppliers: {
    title: "Add a supplier receipt",
    hint: "Photograph the full receipt so quantities, prices, delivery fees, and supplier details are readable.",
    placeholder:
      "Who did we buy from? When did it arrive? Were there delivery fees, missing items, or a balance still owed?",
  },
  expenses: {
    title: "Capture a running cost",
    hint: "Rent, payroll, electricity, transport, repairs, or permits. Include the period the cost covers.",
    placeholder:
      "What is this cost? How much in PHP? Is it monthly or one-off? Is it paid or still owed?",
  },
  team: {
    title: "Capture how things work",
    hint: "Explain one routine in your own words. A short voice recording or note is enough to start.",
    placeholder:
      "Who does this task? What are the steps? What tends to go wrong? Avoid personal IDs and private employee details.",
  },
  walkthrough: {
    title: "Introduce your store",
    hint: "Take a few photos or a short video of the entrance, shelves, freezers, and preparation area.",
    placeholder:
      "Tell us where things are, what sells well, what’s difficult, opening hours, and what you’d like to improve.",
  },
  other: {
    title: "Add a note",
    hint: "Ideas, customer requests, competitor observations or questions.",
    placeholder:
      "Describe the observation or question. Mark assumptions separately.",
  },
};
export function manilaDate() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Manila",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}
export function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Manila",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value.length === 10 ? value + "T12:00:00+08:00" : value));
}
export function fileSize(size: number) {
  return size < 1024 * 1024
    ? `${Math.max(1, Math.round(size / 1024))} KB`
    : `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export type WorkspaceStore = "sausage" | "health";
export type StockState =
  "tracked" | "not_tracked" | "unknown" | "components_only";
export type LoyverseCurrency = {
  code: string | null;
  decimal_places: number | null;
};
export type LoyverseStoreRow = {
  store_id: string;
  store_name: string | null;
  workspace_store: WorkspaceStore | null;
  settings_present: boolean;
  available_for_sale: boolean | null;
  pricing_type: string | null;
  price: string | null;
  optimal_stock: string | null;
  low_stock: string | null;
  stock_state: StockState;
  in_stock: string | null;
  stock_updated_at: string | null;
  below_optimal: string | null;
  low_stock_alert: boolean;
  sold_units: string | null;
  sold_per_week: string | null;
  weekly_units: string[] | null;
};
export type LoyverseVariant = {
  variant_id: string;
  sku: string | null;
  barcode: string | null;
  options: (string | null)[];
  cost: string | null;
  default_price: string | null;
  default_pricing_type: string | null;
  updated_at: string | null;
  stores: LoyverseStoreRow[];
};
export type LoyverseItem = {
  id: string;
  name: string | null;
  category_id: string | null;
  category_name: string | null;
  track_stock: boolean;
  sold_by_weight: boolean;
  is_composite: boolean;
  use_production: boolean;
  option_names: (string | null)[];
  updated_at: string | null;
  variants: LoyverseVariant[];
};
export type LoyverseCounts = {
  stores: number;
  mapped_stores: number;
  items: number;
  variants: number;
  variant_store_rows: number;
  tracked: number;
  not_tracked: number;
  components_only: number;
  unknown_stock: number;
  below_optimal: number;
  low_stock_alerts: number;
  optimal_stock_set: number;
  unavailable: number;
  with_sales: number;
  no_sales: number;
};
export type LoyverseSales = {
  window_days: number;
  weeks: number;
  from: string;
  to: string;
  counted_receipts: number;
  refund_receipts: number;
  cancelled_skipped: number;
  other_types_skipped: number;
  outside_window_skipped: number;
  basis: string;
};
export type LoyverseCatalogue = {
  schema_version: number;
  captured_at: string;
  currency: LoyverseCurrency | null;
  sales: LoyverseSales | null;
  performance: Record<string, Performance> | null;
  stores: {
    id: string;
    name: string | null;
    workspace_store: WorkspaceStore | null;
  }[];
  unmatched_store_mapping?: string[];
  categories: { id: string; name: string | null }[];
  items: LoyverseItem[];
  counts: LoyverseCounts;
  limitations: string[];
};
export type LoyverseView = {
  connection: "ready" | "not_connected" | "credential_missing";
  can_refresh: boolean;
  last_attempt: {
    status: string;
    started_at: string;
    finished_at: string | null;
    error: string | null;
  } | null;
  catalogue: LoyverseCatalogue | null;
  captured_at: string | null;
};

/** Thousands separators for readability. The value itself is never rounded. */
export function grouped(value: string | null) {
  if (value === null) return null;
  const [whole, fraction] = value.split(".");
  const sign = whole.startsWith("-") ? "-" : "";
  const body = (sign ? whole.slice(1) : whole).replace(
    /\B(?=(\d{3})+(?!\d))/g,
    ",",
  );
  return sign + body + (fraction ? "." + fraction : "");
}

/** Trim trailing zeros for display only. The exact source value is never rounded. */
export function quantity(value: string | null) {
  if (value === null) return null;
  if (!value.includes(".")) return value;
  const trimmed = value.replace(/0+$/, "").replace(/\.$/, "");
  return trimmed === "" || trimmed === "-" ? "0" : trimmed;
}

/** Pad to the account's decimal places. Never shortens, so no value is altered. */
export function money(value: string | null, currency: LoyverseCurrency | null) {
  if (value === null) return null;
  const places = currency?.decimal_places ?? null;
  let shown = value;
  if (places !== null && places > 0) {
    const [whole, fraction = ""] = value.split(".");
    shown = `${whole}.${fraction.length >= places ? fraction : fraction.padEnd(places, "0")}`;
  }
  // Separators are readability only; no digit is added, removed or rounded.
  shown = grouped(shown) ?? shown;
  return currency?.code ? `${currency.code} ${shown}` : shown;
}

export const stockStateNames: Record<StockState, string> = {
  tracked: "In stock",
  not_tracked: "Not tracked",
  unknown: "Unknown",
  components_only: "Components only",
};
export function timeLabel(value: string) {
  return new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Manila",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export type DailyRow = {
  date: string;
  receipts: number;
  units: string;
  collected: string;
  excluded: boolean;
};
export type HourlyRow = {
  weekday: number;
  weekday_name: string;
  hour: number;
  receipts: number;
  units: string;
  collected: string;
};
export type VariantHistory = {
  units: string;
  collected: string;
  receipts: number;
  first_sold: string | null;
  last_sold: string | null;
};
export type Performance = {
  from: string | null;
  to: string | null;
  calendar_days: number;
  trading_days: number;
  receipts: number;
  refund_receipts: number;
  units: string;
  collected: string;
  lines: number;
  basket: {
    average_collected: string;
    average_lines: string;
    average_units: string;
  };
  concentration: { top_ten_collected: string; top_ten_share: string | null };
  daily: DailyRow[];
  hourly: HourlyRow[];
  variants: Record<string, VariantHistory>;
  excluded_periods: { from: string; to: string; reason: string }[];
  local_utc_offset_hours: number;
  money_flags: Record<string, number>;
  skipped: Record<string, number>;
};

export function dayLabel(value: string) {
  return new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Manila",
    day: "numeric",
    month: "short",
  }).format(new Date(value + "T12:00:00+08:00"));
}
