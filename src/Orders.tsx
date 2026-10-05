import { useEffect, useMemo, useState } from "react";
import {
  Check,
  CircleHelp,
  Clipboard,
  ExternalLink,
  LockKeyhole,
  MessageCircle,
  PackageCheck,
  RefreshCw,
} from "lucide-react";
import {
  api,
  branches,
  type LoyverseCatalogue,
  type LoyverseView,
  type Reorder,
  type Store,
} from "./api";

type Due = {
  key: string;
  name: string;
  sku: string | null;
  inStock: string | null;
  reorder: Reorder;
};
type Group = {
  supplierId: string;
  supplierName: string;
  reorder: Reorder;
  items: Due[];
};

/** The message a person would otherwise type out by hand. */
function orderMessage(group: Group, branch: string) {
  const person = group.reorder.contact?.person;
  const lines = group.items.map((due) => {
    const amount = due.reorder.suggested_order;
    return amount === null
      ? `- ${due.name}`
      : `- ${due.name}: ${amount}${due.sku ? ` (${due.sku})` : ""}`;
  });
  return [
    `Hi${person ? " " + person : ""}, order for The Sausage Guy ${branch}:`,
    "",
    ...lines,
    "",
    "Thank you!",
  ].join("\n");
}

function Channels({ group, message }: { group: Group; message: string }) {
  const [copied, setCopied] = useState(false);
  const contact = group.reorder.contact;
  async function copy() {
    try {
      await navigator.clipboard.writeText(message);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }
  return (
    <div className="order-channels">
      {contact?.whatsapp && (
        <a
          className="button primary"
          href={`https://wa.me/${contact.whatsapp}?text=${encodeURIComponent(message)}`}
          target="_blank"
          rel="noreferrer noopener"
        >
          <MessageCircle size={16} /> WhatsApp
        </a>
      )}
      <button className="button secondary" onClick={copy}>
        {copied ? <Check size={16} /> : <Clipboard size={16} />}
        {copied ? "Copied" : "Copy message"}
      </button>
      {contact?.viber && (
        <a
          className="button ghost"
          href={`viber://chat?number=%2B${contact.viber}`}
          title="Viber cannot carry the text, so copy the message first."
        >
          Viber
        </a>
      )}
      {contact?.messenger && (
        <a
          className="button ghost"
          href={contact.messenger}
          target="_blank"
          rel="noreferrer noopener"
          title="Messenger cannot carry the text, so copy the message first."
        >
          Messenger <ExternalLink size={12} />
        </a>
      )}
    </div>
  );
}

export function Orders({ scope }: { scope: Store }) {
  const [view, setView] = useState<LoyverseView | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let live = true;
    api<LoyverseView>("/loyverse/items")
      .then((result) => live && setView(result))
      .catch((problem) => live && setError((problem as Error).message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, []);

  async function refresh() {
    setRefreshing(true);
    setError("");
    try {
      setView(await api<LoyverseView>("/loyverse/refresh", { method: "POST" }));
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setRefreshing(false);
    }
  }

  const catalogue: LoyverseCatalogue | null = view?.catalogue ?? null;
  const groups = useMemo<Group[]>(() => {
    if (!catalogue) return [];
    const allowed = new Set(
      catalogue.stores
        .filter(
          (row) =>
            scope === "both" ||
            row.workspace_store === scope ||
            row.workspace_store === null,
        )
        .map((row) => row.id),
    );
    const bySupplier = new Map<string, Group>();
    for (const item of catalogue.items)
      for (const variant of item.variants)
        for (const row of variant.stores) {
          if (!allowed.has(row.store_id) || !row.reorder) continue;
          const state = row.reorder.status;
          if (state !== "order_now" && state !== "out_of_stock") continue;
          const options = variant.options.filter(Boolean).join(" · ");
          const group = bySupplier.get(row.reorder.supplier_id) ?? {
            supplierId: row.reorder.supplier_id,
            supplierName: row.reorder.supplier_name,
            reorder: row.reorder,
            items: [],
          };
          group.items.push({
            key: `${variant.variant_id}:${row.store_id}`,
            name: (item.name ?? "Unnamed") + (options ? ` · ${options}` : ""),
            sku: variant.sku,
            inStock: row.stock_state === "tracked" ? row.in_stock : null,
            reorder: row.reorder,
          });
          bySupplier.set(row.reorder.supplier_id, group);
        }
    const out = [...bySupplier.values()];
    for (const group of out)
      group.items.sort(
        (a, b) =>
          (b.reorder.suggested_order ?? 0) - (a.reorder.suggested_order ?? 0),
      );
    out.sort((a, b) => b.items.length - a.items.length);
    return out;
  }, [catalogue, scope]);

  // The branch's own name, not the POS store name: the message already says
  // which shop this is, so using the POS name repeated it.
  const branch =
    branches.find((row) => row.id === scope)?.name ??
    branches[0]?.name ??
    "Panglao";

  if (loading)
    return (
      <div className="items-panel">
        <p className="muted small-text">Loading what is due…</p>
      </div>
    );

  if (!view || view.connection !== "ready")
    return (
      <div className="items-panel">
        <span className="large-icon">
          <LockKeyhole size={25} />
        </span>
        <h2>Loyverse is not connected yet.</h2>
        <p className="small-text muted">
          Orders are worked out from stock and recent sales. Connect Loyverse
          and they appear here.
        </p>
      </div>
    );

  if (!catalogue?.suppliers)
    return (
      <div className="items-panel">
        <span className="large-icon">
          <PackageCheck size={25} />
        </span>
        <h2>No supplier lead times configured.</h2>
        <p className="small-text muted">
          Without a lead time there is no honest deadline, so nothing is
          proposed here. The technical owner sets{" "}
          <code>SH_LOYVERSE_SUPPLIERS</code>.
        </p>
      </div>
    );

  return (
    <>
      <div className="items-bar">
        <p className="small-text">
          {groups.length === 0 ? (
            <span className="muted">
              Nothing is due at the recent sales rate.
            </span>
          ) : (
            <>
              <strong>
                {groups.reduce((total, group) => total + group.items.length, 0)}{" "}
                items
              </strong>{" "}
              <span className="muted">
                across {groups.length} supplier
                {groups.length === 1 ? "" : "s"} · {branch}
              </span>
            </>
          )}
        </p>
        {view.can_refresh && (
          <button
            className="button secondary"
            onClick={refresh}
            disabled={refreshing}
          >
            <RefreshCw size={16} className={refreshing ? "spinning" : ""} />
            {refreshing ? "Checking…" : "Check again"}
          </button>
        )}
      </div>
      {error && (
        <div className="error-note" role="alert">
          {error}
        </div>
      )}

      {groups.length === 0 ? (
        <div className="items-panel">
          <span className="large-icon">
            <Check size={25} />
          </span>
          <h2>Nothing to order right now.</h2>
          <p className="small-text muted">
            A product whose stock or sales rate is unknown is not counted either
            way, so this is not a promise that every shelf is full.
          </p>
        </div>
      ) : (
        <div className="order-board">
          {groups.map((group) => {
            const message = orderMessage(group, branch);
            const settled = done[group.supplierId];
            return (
              <section
                className={`order-card ${settled ? "settled" : ""}`}
                key={group.supplierId}
              >
                <header>
                  <div>
                    <h2>{group.supplierName}</h2>
                    <small>
                      {group.reorder.cycle
                        ? `order ${group.reorder.next_order_day} · arrives ${group.reorder.arrives}`
                        : `${group.reorder.lead_days?.min}–${group.reorder.lead_days?.max} days to arrive`}
                    </small>
                  </div>
                  <span className="order-count">{group.items.length}</span>
                </header>
                <ul>
                  {group.items.map((due) => (
                    <li key={due.key}>
                      <span>
                        {due.name}
                        {due.reorder.status === "out_of_stock" && (
                          <small className="short-by">out of stock</small>
                        )}
                      </span>
                      <strong>
                        {due.reorder.suggested_order === null
                          ? "—"
                          : `${due.reorder.suggested_order}`}
                      </strong>
                    </li>
                  ))}
                </ul>
                <pre className="order-message">{message}</pre>
                <Channels group={group} message={message} />
                {!group.reorder.contact?.whatsapp && (
                  <p className="small-text unknown-value">
                    No number recorded for this supplier, so there is nothing to
                    open. Copy the message instead.
                  </p>
                )}
                <button
                  className="quiet-link"
                  onClick={() =>
                    setDone({ ...done, [group.supplierId]: !settled })
                  }
                >
                  {settled ? "Mark as still open" : "Mark as ordered"}
                  <Check size={15} />
                </button>
              </section>
            );
          })}
        </div>
      )}

      <div className="items-limits">
        <h3>
          <CircleHelp size={15} /> How these quantities are worked out
        </h3>
        <ul className="small-text muted">
          <li>
            Recent weekly sales over the supplier's lead time, minus what is on
            the shelf, rounded up. Nothing is proposed for a product whose stock
            or sales rate is unknown.
          </li>
          <li>
            A weekday-bound supplier is topped up for the whole cycle, because
            missing an order day costs a week rather than a day.
          </li>
          <li>
            WhatsApp can carry the written message. Viber and Messenger cannot,
            so copy it first and paste it into the chat.
          </li>
          <li>
            Marking a supplier as ordered only tidies this screen. It is not
            sent anywhere and does not change stock.
          </li>
        </ul>
      </div>
    </>
  );
}
