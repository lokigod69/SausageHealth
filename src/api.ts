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
  if (system.upload_mode !== "direct") return api<Entry>("/entries", { method: "POST", body: form });
  const files = form.getAll("files").filter((file): file is File => file instanceof File);
  const manifest = [];
  for (const file of files) {
    const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
    manifest.push({ name: file.name, size: file.size,
      sha256: Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("") });
  }
  const fields = Object.fromEntries(["store", "category", "title", "notes", "occurred_on", "request_key"]
    .map(key => [key, String(form.get(key) ?? "")]));
  const intent = await api<{ entry?: Entry; id: string; files: { grant: string }[] }>("/upload-intents", {
    method: "POST", body: JSON.stringify({ ...fields, files: manifest }),
  });
  if (intent.entry) return intent.entry;
  for (let index = 0; index < files.length; index++) {
    const { url } = await api<{ url: string }>("/storage", {
      method: "POST", body: JSON.stringify({ grant: intent.files[index].grant }),
    });
    let response: Response;
    try {
      response = await fetch(url, { method: "PUT", credentials: "omit",
        headers: { "Content-Type": "application/octet-stream" }, body: files[index] });
    } catch {
      throw new ApiError("The file upload was interrupted. Keep this page open and retry.");
    }
    // A lost response may mean the immutable original is already there. Finalization verifies its bytes.
    // Blob currently reports an existing no-overwrite path as 400/bad_request.
    // Neither 400 nor 409 proves success: the finalizer must verify every size/hash.
    if (!response.ok && response.status !== 400 && response.status !== 409)
      throw new ApiError("The file upload could not be confirmed. Keep this page open and retry.");
  }
  return api<Entry>(`/upload-intents/${intent.id}/finalize`, { method: "POST" });
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
