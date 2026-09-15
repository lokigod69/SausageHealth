import { useEffect, useMemo, useState } from "react";
import {
  Boxes,
  CircleAlert,
  CircleHelp,
  LockKeyhole,
  Package,
  RefreshCw,
  Search,
  TriangleAlert,
} from "lucide-react";
import {
  api,
  ApiError,
  money,
  quantity,
  stockStateNames,
  storeNames,
  timeLabel,
  type LoyverseCatalogue,
  type LoyverseCurrency,
  type LoyverseItem,
  type LoyverseStoreRow,
  type LoyverseVariant,
  type LoyverseView,
  type Store,
  type User,
} from "./api";

type Row = {
  item: LoyverseItem;
  variant: LoyverseVariant;
  store: LoyverseStoreRow;
  key: string;
};
const PAGE = 250;
const statusFilters = {
  all: "All rows",
  below_optimal: "Below optimal stock",
  low_stock: "At or below low stock",
  unknown: "Stock unknown",
  not_tracked: "Stock not tracked",
  unavailable: "Not available for sale",
} as const;
type StatusFilter = keyof typeof statusFilters;
const sorters = {
  name: "Item name",
  shortfall: "Largest shortfall first",
  stock: "Lowest known stock first",
} as const;
type Sorter = keyof typeof sorters;

/** A ready-to-edit mapping for the stores this account returned but nobody has claimed. */
function unmappedSample(catalogue: LoyverseCatalogue) {
  const unmapped = catalogue.stores.filter((row) => !row.workspace_store);
  return JSON.stringify(
    Object.fromEntries(unmapped.map((row) => [row.id, "sausage"])),
  );
}

/** Sorting only. Displayed figures always come from the exact source string. */
function sortable(value: string | null) {
  const parsed = value === null ? Number.NaN : Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function priceLabel(
  variant: LoyverseVariant,
  store: LoyverseStoreRow,
  currency: LoyverseCurrency | null,
) {
  if (store.price !== null)
    return { text: money(store.price, currency), hint: "" };
  if (
    store.pricing_type === "VARIABLE" ||
    variant.default_pricing_type === "VARIABLE"
  )
    return {
      text: "At sale",
      hint: "Price is entered on the POS at the time of sale.",
    };
  if (store.settings_present) return { text: "Not set", hint: "" };
  if (variant.default_price !== null)
    return {
      text: money(variant.default_price, currency),
      hint: "Loyverse returned no settings for this store; this is the item default price.",
    };
  return { text: "Not set", hint: "" };
}

function StockCell({ store }: { store: LoyverseStoreRow }) {
  if (store.stock_state !== "tracked")
    return (
      <span
        className="unknown-value"
        title={
          store.stock_state === "not_tracked"
            ? "Stock tracking is switched off for this item in Loyverse. It has no count, which is not the same as zero."
            : store.stock_state === "components_only"
              ? "A composite item without production. Loyverse holds the stock of its components instead."
              : "Loyverse returned no inventory level for this variant in this store."
        }
      >
        {stockStateNames[store.stock_state]}
      </span>
    );
  return (
    <span className="stock-value">
      <strong>{quantity(store.in_stock)}</strong>
      {store.below_optimal !== null && (
        <small className="short-by">
          short {quantity(store.below_optimal)}
        </small>
      )}
    </span>
  );
}

function RowStatus({ store }: { store: LoyverseStoreRow }) {
  if (store.available_for_sale === false)
    return <span className="tag">Not for sale</span>;
  if (store.low_stock_alert)
    return (
      <span className="tag amber">
        <TriangleAlert size={11} /> Low stock
      </span>
    );
  if (store.below_optimal !== null)
    return <span className="tag amber">Below optimal</span>;
  if (store.stock_state === "tracked")
    return <span className="tag green">Stocked</span>;
  return <span className="tag">No count</span>;
}

function Summary({ catalogue }: { catalogue: LoyverseCatalogue }) {
  const c = catalogue.counts;
  const tiles = [
    { label: "Items", value: c.items, note: `${c.variants} variants` },
    { label: "Counted", value: c.tracked, note: "stock figures held" },
    {
      label: "Below optimal",
      value: c.below_optimal,
      note: `${c.optimal_stock_set} targets set`,
    },
    {
      label: "Low stock",
      value: c.low_stock_alerts,
      note: "at or under threshold",
    },
    { label: "Not tracked", value: c.not_tracked, note: "no count kept" },
    { label: "Unknown", value: c.unknown_stock, note: "no level returned" },
  ];
  return (
    <div className="items-summary">
      {tiles.map((tile) => (
        <div key={tile.label}>
          <span className="eyebrow">{tile.label}</span>
          <strong>{tile.value}</strong>
          <small>{tile.note}</small>
        </div>
      ))}
    </div>
  );
}

export function Items({ user, scope }: { user: User; scope: Store }) {
  const [view, setView] = useState<LoyverseView | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");
  const [store, setStore] = useState("all");
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [sorter, setSorter] = useState<Sorter>("name");
  const [shown, setShown] = useState(PAGE);

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
    setNotice("");
    try {
      const result = await api<LoyverseView>("/loyverse/refresh", {
        method: "POST",
      });
      setView(result);
      setNotice(
        `Read from Loyverse. ${result.catalogue?.counts.items ?? 0} items and ${result.catalogue?.counts.variants ?? 0} variants saved.`,
      );
    } catch (problem) {
      setError((problem as Error).message);
      if (problem instanceof ApiError && problem.status !== 403)
        api<LoyverseView>("/loyverse/items")
          .then(setView)
          .catch(() => {});
    } finally {
      setRefreshing(false);
    }
  }

  const catalogue = view?.catalogue ?? null;
  const visibleStores = useMemo(() => {
    if (!catalogue) return [];
    return catalogue.stores.filter(
      (row) =>
        scope === "both" ||
        row.workspace_store === scope ||
        row.workspace_store === null,
    );
  }, [catalogue, scope]);

  const rows = useMemo<Row[]>(() => {
    if (!catalogue) return [];
    const allowed = new Set(visibleStores.map((row) => row.id));
    const collected: Row[] = [];
    for (const item of catalogue.items)
      for (const variant of item.variants)
        for (const storeRow of variant.stores)
          if (allowed.has(storeRow.store_id))
            collected.push({
              item,
              variant,
              store: storeRow,
              key: `${variant.variant_id}:${storeRow.store_id}`,
            });
    return collected;
  }, [catalogue, visibleStores]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matched = rows.filter((row) => {
      if (store !== "all" && row.store.store_id !== store) return false;
      if (category !== "all" && (row.item.category_id ?? "none") !== category)
        return false;
      if (status === "below_optimal" && row.store.below_optimal === null)
        return false;
      if (status === "low_stock" && !row.store.low_stock_alert) return false;
      if (status === "unknown" && row.store.stock_state !== "unknown")
        return false;
      if (status === "not_tracked" && row.store.stock_state !== "not_tracked")
        return false;
      if (status === "unavailable" && row.store.available_for_sale !== false)
        return false;
      if (!needle) return true;
      return [
        row.item.name,
        row.item.category_name,
        row.variant.sku,
        row.variant.barcode,
        ...row.variant.options,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
    const ordered = [...matched];
    if (sorter === "shortfall")
      ordered.sort(
        (a, b) =>
          (sortable(b.store.below_optimal) || 0) -
          (sortable(a.store.below_optimal) || 0),
      );
    if (sorter === "stock")
      ordered.sort((a, b) => {
        const left = sortable(a.store.in_stock);
        const right = sortable(b.store.in_stock);
        if (Number.isNaN(left) && Number.isNaN(right)) return 0;
        if (Number.isNaN(left)) return 1; // Unknown counts never pose as the lowest stock.
        if (Number.isNaN(right)) return -1;
        return left - right;
      });
    return ordered;
  }, [rows, query, store, category, status, sorter]);

  useEffect(
    () => setShown(PAGE),
    [query, store, category, status, sorter, scope],
  );

  if (loading)
    return (
      <div className="items-panel">
        <p className="muted small-text">Loading the saved item list…</p>
      </div>
    );

  if (error && !view)
    return (
      <div className="items-panel">
        <h2>The item list could not be opened.</h2>
        <p className="small-text muted">{error}</p>
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
          {view?.connection === "credential_missing"
            ? "The connection is switched on, but this server holds no Loyverse access credential."
            : "This workspace reads the Loyverse catalogue only when the technical owner switches the connection on."}
        </p>
        {user.role === "owner" && (
          <div className="items-setup">
            <p className="small-text">
              To connect, set on the API server and restart it:
            </p>
            <ul className="small-text muted">
              <li>
                <code>SH_LOYVERSE_ENABLED=1</code>
              </li>
              <li>
                <code>SH_LOYVERSE_TOKEN</code> — or leave the token in the
                private
                <code> .data/loyverse-access.json</code> file this server
                already expects.
              </li>
              <li>
                <code>SH_LOYVERSE_STORE_MAP</code> — for example{" "}
                <code>{'{"<loyverse-store-id>":"sausage"}'}</code>. Until a
                store is mapped, its rows stay unattributed rather than being
                assigned to a shop.
              </li>
            </ul>
            <p className="small-text muted">
              The credential stays on the server. It is never sent to this page,
              put in a URL, or committed. Reading is GET-only: nothing here
              writes to the POS.
            </p>
          </div>
        )}
      </div>
    );

  const currency = catalogue?.currency ?? null;
  const page = filtered.slice(0, shown);
  const showStore = visibleStores.length > 1;

  return (
    <>
      <div className="items-bar">
        <div>
          <p className="small-text">
            {catalogue ? (
              <>
                Read from Loyverse {timeLabel(catalogue.captured_at)} ·{" "}
                <span className="muted">
                  {catalogue.counts.items} items across{" "}
                  {visibleStores.length === 1
                    ? (visibleStores[0].name ?? "one store")
                    : `${visibleStores.length} stores`}
                </span>
              </>
            ) : (
              <span className="muted">
                Nothing has been read from Loyverse yet.
              </span>
            )}
          </p>
          {view.last_attempt?.status === "failed" && (
            <p className="small-text amber-text">
              <CircleAlert size={13} /> Last attempt failed:{" "}
              {view.last_attempt.error}
            </p>
          )}
        </div>
        {view.can_refresh && (
          <button
            className="button secondary"
            onClick={refresh}
            disabled={refreshing}
          >
            <RefreshCw size={16} className={refreshing ? "spinning" : ""} />
            {refreshing
              ? "Reading…"
              : catalogue
                ? "Refresh from Loyverse"
                : "Read from Loyverse"}
          </button>
        )}
      </div>
      {notice && <div className="items-notice small-text">{notice}</div>}
      {error && view && (
        <div className="error-note" role="alert">
          {error}
        </div>
      )}
      {catalogue &&
        catalogue.counts.mapped_stores < catalogue.counts.stores &&
        user.role === "owner" && (
          <div className="items-warning small-text">
            <CircleAlert size={14} />
            <div>
              <p>
                {catalogue.counts.stores - catalogue.counts.mapped_stores}{" "}
                Loyverse store
                {catalogue.counts.stores - catalogue.counts.mapped_stores === 1
                  ? " is"
                  : "s are"}{" "}
                not mapped to {storeNames.sausage} or {storeNames.health}. Their
                rows are shown to you unattributed. Confirm which shop each one
                is, then set <code>SH_LOYVERSE_STORE_MAP</code> on the API
                server and restart it.
              </p>
              <ul className="store-id-list">
                {catalogue.stores
                  .filter((row) => !row.workspace_store)
                  .map((row) => (
                    <li key={row.id}>
                      {row.name ?? "Unnamed store"} <code>{row.id}</code>
                    </li>
                  ))}
              </ul>
              <p className="muted">
                Replace each value with <code>"sausage"</code> or{" "}
                <code>"health"</code>, and drop any store that is neither:
              </p>
              <code className="map-sample">{unmappedSample(catalogue)}</code>
            </div>
          </div>
        )}
      {catalogue?.unmatched_store_mapping?.length ? (
        <p className="items-warning small-text">
          <CircleAlert size={14} />
          The store mapping names {
            catalogue.unmatched_store_mapping.length
          }{" "}
          store id
          {catalogue.unmatched_store_mapping.length === 1 ? "" : "s"} this
          account does not return. That mapping has no effect.
        </p>
      ) : null}

      {!catalogue ? (
        <div className="items-panel">
          <span className="large-icon">
            <Boxes size={25} />
          </span>
          <h2>No item list saved yet.</h2>
          <p className="small-text muted">
            {view.can_refresh
              ? "Read the catalogue once to store a dated snapshot of items, variants, stock and optimal stock."
              : "Ask the technical owner or a store operator to read the catalogue once."}
          </p>
        </div>
      ) : visibleStores.length === 0 ? (
        <div className="items-panel">
          <span className="large-icon">
            <Package size={25} />
          </span>
          <h2>No Loyverse store is mapped to this view.</h2>
          <p className="small-text muted">
            The saved catalogue holds {catalogue.counts.stores} store
            {catalogue.counts.stores === 1 ? "" : "s"}, none of which is mapped
            to your selection. Nothing here is attributed to a shop without that
            mapping.
          </p>
        </div>
      ) : (
        <>
          <Summary catalogue={catalogue} />
          <div className="collection-tools items-tools">
            <label className="search">
              <Search size={15} />
              <span className="visually-hidden">Search items</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search name, SKU, barcode or category"
              />
            </label>
            {showStore && (
              <select
                value={store}
                onChange={(event) => setStore(event.target.value)}
              >
                <option value="all">All stores</option>
                {visibleStores.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name ?? "Unnamed store"}
                    {row.workspace_store ? "" : " (unmapped)"}
                  </option>
                ))}
              </select>
            )}
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="all">All categories</option>
              {catalogue.categories.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name ?? "Unnamed category"}
                </option>
              ))}
              <option value="none">No category</option>
            </select>
            <select
              value={status}
              onChange={(event) =>
                setStatus(event.target.value as StatusFilter)
              }
            >
              {Object.entries(statusFilters).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <select
              value={sorter}
              onChange={(event) => setSorter(event.target.value as Sorter)}
            >
              {Object.entries(sorters).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <p className="items-count small-text muted">
            {filtered.length} of {rows.length} variant rows
            {showStore ? " across the selected stores" : ""}.
          </p>
          {filtered.length === 0 ? (
            <div className="items-panel">
              <p className="muted small-text">Nothing matches these filters.</p>
            </div>
          ) : (
            <div className="items-table-wrap">
              <table className="items-table">
                <thead>
                  <tr>
                    <th scope="col">Item</th>
                    <th scope="col">SKU</th>
                    <th scope="col">Category</th>
                    {showStore && <th scope="col">Store</th>}
                    <th scope="col" className="numeric">
                      Price
                    </th>
                    <th scope="col" className="numeric">
                      Cost
                    </th>
                    <th scope="col" className="numeric">
                      In stock
                    </th>
                    <th scope="col" className="numeric">
                      Optimal
                    </th>
                    <th scope="col" className="numeric">
                      Low at
                    </th>
                    <th scope="col">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {page.map(({ item, variant, store: storeRow, key }) => {
                    const price = priceLabel(variant, storeRow, currency);
                    const options = variant.options.filter(Boolean).join(" · ");
                    return (
                      <tr key={key}>
                        <td data-label="Item">
                          <span className="item-name">
                            <strong>{item.name ?? "Unnamed item"}</strong>
                            {options && <small>{options}</small>}
                            <span className="item-flags">
                              {item.sold_by_weight && (
                                <span className="tag">By weight</span>
                              )}
                              {item.is_composite && (
                                <span className="tag">Composite</span>
                              )}
                              {!storeRow.settings_present && (
                                <span
                                  className="tag"
                                  title="Loyverse returned no settings for this variant in this store."
                                >
                                  No store settings
                                </span>
                              )}
                            </span>
                          </span>
                        </td>
                        <td data-label="SKU">
                          <span className="mono">{variant.sku ?? "—"}</span>
                          {variant.barcode && (
                            <small className="mono muted">
                              {variant.barcode}
                            </small>
                          )}
                        </td>
                        <td data-label="Category">
                          {item.category_name ?? (
                            <span className="unknown-value">No category</span>
                          )}
                        </td>
                        {showStore && (
                          <td data-label="Store">
                            {storeRow.store_name ?? "Unnamed store"}
                            {!storeRow.workspace_store && (
                              <small className="unknown-value">Unmapped</small>
                            )}
                          </td>
                        )}
                        <td
                          data-label="Price"
                          className="numeric"
                          title={price.hint}
                        >
                          {price.text}
                        </td>
                        <td data-label="Cost" className="numeric">
                          {variant.cost === null ? (
                            <span className="unknown-value">Not recorded</span>
                          ) : (
                            money(variant.cost, currency)
                          )}
                        </td>
                        <td data-label="In stock" className="numeric">
                          <StockCell store={storeRow} />
                        </td>
                        <td data-label="Optimal" className="numeric">
                          {storeRow.optimal_stock === null ? (
                            <span className="unknown-value">Not set</span>
                          ) : (
                            quantity(storeRow.optimal_stock)
                          )}
                        </td>
                        <td data-label="Low at" className="numeric">
                          {storeRow.low_stock === null ? (
                            <span className="unknown-value">Not set</span>
                          ) : (
                            quantity(storeRow.low_stock)
                          )}
                        </td>
                        <td data-label="Status">
                          <RowStatus store={storeRow} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {filtered.length > page.length && (
            <button
              className="button ghost items-more"
              onClick={() => setShown(shown + PAGE)}
            >
              Show {Math.min(PAGE, filtered.length - page.length)} more
            </button>
          )}
          <div className="items-limits">
            <h3>
              <CircleHelp size={15} /> What this list is, and is not
            </h3>
            <ul className="small-text muted">
              {catalogue.limitations.map((line) => (
                <li key={line}>{line}</li>
              ))}
              <li>
                Loyverse starts a variant cost at 0.00, so a zero cost can mean
                it was never entered. Treat it as unconfirmed until a supplier
                document says otherwise.
              </li>
            </ul>
          </div>
        </>
      )}
    </>
  );
}
