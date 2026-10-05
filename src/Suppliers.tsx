import { useEffect, useState, type FormEvent } from "react";
import { ChevronDown, Pencil, Store, Trash2 } from "lucide-react";
import { api, type ShopSupplier } from "./api";

const WEEKDAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

const EMPTY = {
  id: "",
  name: "",
  lead_min: "",
  lead_max: "",
  order_weekday: "",
  delivery_weekday: "",
  whatsapp: "",
  viber: "",
  person: "",
  note: "",
  match_names: "",
  match_categories: "",
};

function describe(supplier: ShopSupplier) {
  if (supplier.order_weekday && supplier.delivery_weekday)
    return `orders ${supplier.order_weekday}, delivers ${supplier.delivery_weekday}`;
  if (supplier.lead_min === null) return "no lead time recorded";
  return supplier.lead_min === supplier.lead_max
    ? `${supplier.lead_min} days to arrive`
    : `${supplier.lead_min}–${supplier.lead_max} days to arrive`;
}

/** Suppliers the shop adds itself, on top of the ones set up with the deployment.
 *
 *  The configured ones are not shown or editable here: they are commercially
 *  sensitive and live in the host's encrypted configuration on purpose.
 */
export function Suppliers({ canEdit }: { canEdit: boolean }) {
  const [rows, setRows] = useState<ShopSupplier[] | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<typeof EMPTY | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [paste, setPaste] = useState<string | null>(null);
  const [imported, setImported] = useState("");

  async function load() {
    try {
      setRows(await api<ShopSupplier[]>("/shop-suppliers"));
    } catch (problem) {
      setError((problem as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, []);

  function set(key: keyof typeof EMPTY, value: string) {
    setForm((current) => (current ? { ...current, [key]: value } : current));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!form) return;
    setError("");
    setBusy(true);
    try {
      await api("/shop-suppliers", {
        method: "PUT",
        body: JSON.stringify({
          name: form.name,
          id: form.id || null,
          lead_min: form.lead_min === "" ? null : Number(form.lead_min),
          lead_max: form.lead_max === "" ? null : Number(form.lead_max),
          order_weekday: form.order_weekday || null,
          delivery_weekday: form.delivery_weekday || null,
          whatsapp: form.whatsapp || null,
          viber: form.viber || null,
          person: form.person || null,
          note: form.note || null,
          match_names: form.match_names || null,
          match_categories: form.match_categories || null,
        }),
      });
      setForm(null);
      await load();
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }

  /** One paste for a whole list, so nobody types suppliers in one at a time. */
  async function importAll(event: FormEvent) {
    event.preventDefault();
    if (!paste) return;
    setError("");
    setImported("");
    setBusy(true);
    try {
      const rows = await api<ShopSupplier[]>("/shop-suppliers/import", {
        method: "POST",
        body: JSON.stringify({ text: paste }),
      });
      setRows(rows);
      setPaste(null);
      setImported(`${rows.length} suppliers are now recorded here.`);
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function drop(supplier: ShopSupplier) {
    setError("");
    try {
      await api(`/shop-suppliers/${encodeURIComponent(supplier.id)}`, {
        method: "DELETE",
      });
      await load();
    } catch (problem) {
      setError((problem as Error).message);
    }
  }

  return (
    <section className="supplier-panel">
      <button className="supplier-toggle" onClick={() => setOpen(!open)}>
        <Store size={16} /> Suppliers you added here
        <span className="order-count">{rows?.length ?? "—"}</span>
        <ChevronDown size={15} className={open ? "turned" : undefined} />
      </button>
      {open && (
        <>
          <p className="muted small-text">
            These are added on top of the suppliers set up with the deployment,
            which are not listed here. Give a supplier its number and the
            products it brings, and its orders get a message button of their
            own. A product listed here goes to this supplier even if the
            deployment's configuration says otherwise.
          </p>
          {rows && rows.length > 0 && (
            <ul className="supplier-list">
              {rows.map((supplier) => (
                <li key={supplier.id}>
                  <span>
                    <strong>{supplier.name}</strong>
                    <small>
                      {describe(supplier)}
                      {supplier.whatsapp
                        ? " · WhatsApp recorded"
                        : " · no number"}
                      {supplier.match_names
                        ? ` · ${supplier.match_names.split("\n").length} products`
                        : ""}
                    </small>
                  </span>
                  {canEdit && (
                    <span className="supplier-actions">
                      <button
                        className="icon-button"
                        onClick={() =>
                          setForm({
                            ...EMPTY,
                            ...supplier,
                            lead_min: supplier.lead_min?.toString() ?? "",
                            lead_max: supplier.lead_max?.toString() ?? "",
                            order_weekday: supplier.order_weekday ?? "",
                            delivery_weekday: supplier.delivery_weekday ?? "",
                            whatsapp: supplier.whatsapp ?? "",
                            viber: supplier.viber ?? "",
                            person: supplier.person ?? "",
                            note: supplier.note ?? "",
                            match_names: supplier.match_names ?? "",
                            match_categories: supplier.match_categories ?? "",
                          })
                        }
                      >
                        <Pencil size={15} />
                        <span className="visually-hidden">Edit</span>
                      </button>
                      <button
                        className="icon-button"
                        onClick={() => drop(supplier)}
                      >
                        <Trash2 size={15} />
                        <span className="visually-hidden">Remove</span>
                      </button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
          {error && <div className="error-note">{error}</div>}
          {imported && <p className="small-text">{imported}</p>}
          {canEdit && !form && paste === null && (
            <div className="link-editor-actions">
              <button
                className="button secondary"
                onClick={() => setForm({ ...EMPTY })}
              >
                Add a supplier
              </button>
              <button className="button ghost" onClick={() => setPaste("")}>
                Import a list
              </button>
            </div>
          )}
          {paste !== null && (
            <form className="link-editor" onSubmit={importAll}>
              <label>
                Paste a supplier list
                <textarea
                  value={paste}
                  onChange={(event) => setPaste(event.target.value)}
                  rows={8}
                  placeholder={'{"suppliers": [...], "rules": [...]}'}
                  autoFocus
                />
              </label>
              <p className="small-text muted">
                The same shape the deployment's configuration uses, so a list
                can be prepared once and pasted here. Nothing is written unless
                every supplier in it is accepted, and anything this cannot store
                is refused by name rather than quietly dropped.
              </p>
              {error && <div className="error-note">{error}</div>}
              <div className="link-editor-actions">
                <button className="button secondary" disabled={busy}>
                  {busy ? "Importing…" : "Import"}
                </button>
                <button
                  className="button ghost"
                  type="button"
                  onClick={() => {
                    setPaste(null);
                    setError("");
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
          {form && (
            <form className="link-editor" onSubmit={save}>
              <div className="link-editor-fields">
                <label>
                  Name
                  <input
                    value={form.name}
                    onChange={(event) => set("name", event.target.value)}
                    placeholder="Who brings the goods"
                    required
                    autoFocus
                  />
                </label>
                <label className="link-editor-narrow">
                  Contact person
                  <input
                    value={form.person}
                    onChange={(event) => set("person", event.target.value)}
                    placeholder="Who to greet"
                  />
                </label>
                <label className="link-editor-narrow">
                  WhatsApp
                  <input
                    value={form.whatsapp}
                    onChange={(event) => set("whatsapp", event.target.value)}
                    placeholder="+63 9xx xxx xxxx"
                  />
                </label>
                <label className="link-editor-narrow">
                  Viber
                  <input
                    value={form.viber}
                    onChange={(event) => set("viber", event.target.value)}
                    placeholder="+63 9xx xxx xxxx"
                  />
                </label>
              </div>
              <div className="link-editor-fields">
                <label className="link-editor-narrow">
                  Days to arrive · fastest
                  <input
                    value={form.lead_min}
                    onChange={(event) => set("lead_min", event.target.value)}
                    inputMode="numeric"
                    placeholder="2"
                  />
                </label>
                <label className="link-editor-narrow">
                  Days to arrive · slowest
                  <input
                    value={form.lead_max}
                    onChange={(event) => set("lead_max", event.target.value)}
                    inputMode="numeric"
                    placeholder="3"
                  />
                </label>
                <label className="link-editor-narrow">
                  Or · order day
                  <select
                    value={form.order_weekday}
                    onChange={(event) =>
                      set("order_weekday", event.target.value)
                    }
                  >
                    <option value="">—</option>
                    {WEEKDAYS.map((day) => (
                      <option key={day} value={day}>
                        {day}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="link-editor-narrow">
                  Or · delivery day
                  <select
                    value={form.delivery_weekday}
                    onChange={(event) =>
                      set("delivery_weekday", event.target.value)
                    }
                  >
                    <option value="">—</option>
                    {WEEKDAYS.map((day) => (
                      <option key={day} value={day}>
                        {day}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="link-editor-fields">
                <label>
                  Products · one per line
                  <textarea
                    value={form.match_names}
                    onChange={(event) => set("match_names", event.target.value)}
                    rows={5}
                    placeholder={"Greek Yogurt\nKefir\nCoffee Beans"}
                  />
                </label>
                <label className="link-editor-narrow">
                  Whole categories · one per line
                  <textarea
                    value={form.match_categories}
                    onChange={(event) =>
                      set("match_categories", event.target.value)
                    }
                    rows={5}
                    placeholder="Dairy"
                  />
                </label>
              </div>
              <p className="small-text muted">
                A product line matches any item whose name contains it, so
                "Coffee Beans" covers both the 1 kg and the 100 g pack. Either
                give days to arrive, or an order day and a delivery day for a
                supplier who only takes orders once a week.
              </p>
              <div className="link-editor-actions">
                <button className="button secondary" disabled={busy}>
                  {busy ? "Saving…" : "Save supplier"}
                </button>
                <button
                  className="button ghost"
                  type="button"
                  onClick={() => {
                    setForm(null);
                    setError("");
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </>
      )}
    </section>
  );
}
