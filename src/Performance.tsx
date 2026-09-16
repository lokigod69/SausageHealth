import { useEffect, useMemo, useState } from "react";
import {
  CircleAlert,
  CircleHelp,
  Clock,
  LockKeyhole,
  PackageCheck,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import {
  api,
  dayLabel,
  grouped,
  money,
  quantity,
  timeLabel,
  type LoyverseCurrency,
  type LoyverseView,
  type Performance as Trading,
  type Store,
  type User,
  type Reorder,
  type VariantHistory,
} from "./api";

type Line = {
  variantId: string;
  name: string;
  sku: string | null;
  category: string | null;
  history: VariantHistory;
  inStock: string | null;
  perWeek: string | null;
  lowStock: string | null;
  trackStock: boolean;
  reorder: Reorder | null;
};

/** Days of stock left at the recent rate. Only when both numbers are known. */
function coverDays(line: Line) {
  if (line.inStock === null || line.perWeek === null) return null;
  const rate = Number(line.perWeek) / 7;
  if (!Number.isFinite(rate) || rate <= 0) return null;
  const days = Number(line.inStock) / rate;
  return Number.isFinite(days) ? days : null;
}

function Bars({
  trading,
  currency,
}: {
  trading: Trading;
  currency: LoyverseCurrency | null;
}) {
  const rows = trading.daily;
  const peak = Math.max(
    1,
    ...rows.map((row) => Math.abs(Number(row.collected) || 0)),
  );
  const width = Math.max(320, rows.length * 9);
  return (
    <div className="chart-scroll">
      <svg
        className="daily-chart"
        viewBox={`0 0 ${width} 132`}
        role="img"
        aria-label={`Reported takings per day from ${trading.from} to ${trading.to}`}
      >
        {rows.map((row, index) => {
          const value = Math.abs(Number(row.collected) || 0);
          const height = Math.max(1, (value / peak) * 108);
          return (
            <rect
              key={row.date}
              x={index * 9}
              y={118 - height}
              width={7}
              height={height}
              rx={1}
              className={
                row.excluded
                  ? "bar excluded"
                  : row.receipts === 0
                    ? "bar quiet"
                    : "bar"
              }
            >
              <title>
                {`${row.date} · ${money(row.collected, currency)} · ${row.receipts} receipts${
                  row.excluded ? " · marked as not representative" : ""
                }`}
              </title>
            </rect>
          );
        })}
      </svg>
    </div>
  );
}

function Heatmap({ trading }: { trading: Trading }) {
  const hours = [...new Set(trading.hourly.map((row) => row.hour))].sort(
    (a, b) => a - b,
  );
  const bySlot = new Map(
    trading.hourly.map((row) => [`${row.weekday}:${row.hour}`, row]),
  );
  const peak = Math.max(1, ...trading.hourly.map((row) => row.receipts));
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  return (
    <div className="chart-scroll">
      <table className="heatmap">
        <thead>
          <tr>
            <th scope="col" className="corner">
              <span className="visually-hidden">Weekday</span>
            </th>
            {hours.map((hour) => (
              <th key={hour} scope="col">
                {String(hour).padStart(2, "0")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {days.map((day, index) => (
            <tr key={day}>
              <th scope="row">{day}</th>
              {hours.map((hour) => {
                const row = bySlot.get(`${index}:${hour}`);
                const count = row?.receipts ?? 0;
                return (
                  <td key={hour}>
                    <span
                      className="heat"
                      style={{
                        opacity: count ? 0.15 + (count / peak) * 0.85 : 0,
                      }}
                      title={`${day} ${String(hour).padStart(2, "0")}:00 · ${count} receipts`}
                    />
                    {count === 0 && (
                      <i
                        className="heat-empty"
                        title={`${day} ${hour}:00 · none`}
                      />
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Ranking({
  title,
  hint,
  lines,
  render,
  empty,
}: {
  title: string;
  hint: string;
  lines: Line[];
  render: (line: Line) => { value: string | null; note: string };
  empty: string;
}) {
  return (
    <section className="rank-card">
      <h3>{title}</h3>
      <p className="small-text muted">{hint}</p>
      {lines.length === 0 ? (
        <p className="small-text unknown-value">{empty}</p>
      ) : (
        <ol className="rank-list">
          {lines.map((line) => {
            const shown = render(line);
            return (
              <li key={line.variantId}>
                <span className="rank-name">
                  <strong>{line.name}</strong>
                  <small>{line.category ?? "No category"}</small>
                </span>
                <span className="rank-value">
                  <strong>{shown.value}</strong>
                  <small>{shown.note}</small>
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

export function PerformancePage({ user, scope }: { user: User; scope: Store }) {
  const [view, setView] = useState<LoyverseView | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [storeId, setStoreId] = useState<string | null>(null);
  const [rankBy, setRankBy] = useState<"collected" | "units">("collected");

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

  const catalogue = view?.catalogue ?? null;
  const visible = useMemo(() => {
    if (!catalogue?.performance) return [];
    return catalogue.stores.filter(
      (row) =>
        (scope === "both" ||
          row.workspace_store === scope ||
          row.workspace_store === null) &&
        catalogue.performance?.[row.id],
    );
  }, [catalogue, scope]);

  const selected =
    storeId && visible.some((row) => row.id === storeId)
      ? storeId
      : visible[0]?.id;
  const trading = selected
    ? (catalogue?.performance?.[selected] ?? null)
    : null;

  const lines = useMemo<Line[]>(() => {
    if (!catalogue || !trading || !selected) return [];
    const out: Line[] = [];
    for (const item of catalogue.items)
      for (const variant of item.variants) {
        const storeRow = variant.stores.find(
          (row) => row.store_id === selected,
        );
        if (!storeRow) continue;
        const history = trading.variants[variant.variant_id];
        const options = variant.options.filter(Boolean).join(" · ");
        out.push({
          variantId: variant.variant_id,
          name:
            (item.name ?? "Unnamed item") + (options ? ` · ${options}` : ""),
          sku: variant.sku,
          category: item.category_name,
          history: history ?? {
            units: "0",
            collected: "0",
            receipts: 0,
            first_sold: null,
            last_sold: null,
          },
          inStock:
            storeRow.stock_state === "tracked" ? storeRow.in_stock : null,
          perWeek: storeRow.sold_per_week,
          lowStock: storeRow.low_stock,
          trackStock: item.track_stock,
          reorder: storeRow.reorder,
        });
      }
    return out;
  }, [catalogue, trading, selected]);

  if (loading)
    return (
      <div className="items-panel">
        <p className="muted small-text">Loading the saved figures…</p>
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
          Trading figures come from the same read as the item list. Connect
          Loyverse and they appear here.
        </p>
      </div>
    );

  if (!trading || !catalogue)
    return (
      <div className="items-panel">
        <span className="large-icon">
          <TrendingUp size={25} />
        </span>
        <h2>No trading figures saved yet.</h2>
        <p className="small-text muted">
          {catalogue
            ? "This snapshot was taken before receipts were read. Refresh to add them."
            : "Read the catalogue once and the figures follow."}
        </p>
        {view.can_refresh && (
          <button
            className="button secondary"
            onClick={refresh}
            disabled={refreshing}
          >
            <RefreshCw size={16} className={refreshing ? "spinning" : ""} />
            {refreshing ? "Reading…" : "Refresh from Loyverse"}
          </button>
        )}
      </div>
    );

  const currency = catalogue.currency;
  const sold = lines.filter((line) => Number(line.history.units) > 0);
  const byCollected = [...sold].sort(
    (a, b) => Number(b.history.collected) - Number(a.history.collected),
  );
  const byUnits = [...sold].sort(
    (a, b) => Number(b.history.units) - Number(a.history.units),
  );
  const best = (rankBy === "collected" ? byCollected : byUnits).slice(0, 10);
  const weakest = [...sold]
    .sort((a, b) => Number(a.history.collected) - Number(b.history.collected))
    .slice(0, 10);
  const deadStock = lines
    .filter(
      (line) =>
        Number(line.history.units) <= 0 &&
        line.inStock !== null &&
        Number(line.inStock) > 0,
    )
    .sort((a, b) => Number(b.inStock) - Number(a.inStock))
    .slice(0, 10);
  // Zero stock with a sales rate is not "nearly out". It is already out, and
  // every day it stays that way is a sale that cannot happen.
  const stockedOut = lines
    .filter(
      (line) =>
        line.inStock !== null &&
        Number(line.inStock) <= 0 &&
        Number(line.perWeek ?? 0) > 0,
    )
    .sort((a, b) => Number(b.perWeek ?? 0) - Number(a.perWeek ?? 0))
    .slice(0, 10);
  const running = lines
    .map((line) => ({ line, days: coverDays(line) }))
    .filter((entry) => entry.days !== null && entry.days > 0 && entry.days < 14)
    .sort((a, b) => (a.days ?? 0) - (b.days ?? 0))
    .slice(0, 10);
  const unguarded = sold
    .filter(
      (line) =>
        line.trackStock &&
        line.lowStock === null &&
        Number(line.perWeek ?? 0) >= 1,
    )
    .sort((a, b) => Number(b.perWeek ?? 0) - Number(a.perWeek ?? 0))
    .slice(0, 10);

  const tiles = [
    {
      label: "Taken",
      value: money(trading.collected, currency),
      note: "reported, not reconciled",
    },
    {
      label: "Receipts",
      value: String(trading.receipts),
      note: `${trading.trading_days} trading days`,
    },
    {
      label: "Units",
      value: grouped(trading.units),
      note: `${trading.lines} lines`,
    },
    {
      label: "Average basket",
      value: money(trading.basket.average_collected, currency),
      note: `${trading.basket.average_units} units per receipt`,
    },
    {
      label: "Top ten share",
      value: trading.concentration.top_ten_share
        ? `${trading.concentration.top_ten_share}%`
        : "—",
      note: "of everything taken",
    },
    {
      label: "Refunds",
      value: String(trading.refund_receipts),
      note: "already subtracted above",
    },
  ];

  return (
    <>
      <div className="items-bar">
        <div>
          <p className="small-text">
            {trading.from && trading.to ? (
              <>
                {dayLabel(trading.from)} – {dayLabel(trading.to)}{" "}
                <span className="muted">
                  · {trading.trading_days} of {trading.calendar_days} days had
                  sales · read {timeLabel(catalogue.captured_at)}
                </span>
              </>
            ) : (
              <span className="muted">No receipts in this account yet.</span>
            )}
          </p>
        </div>
        <div className="bar-actions">
          {visible.length > 1 && (
            <select
              value={selected}
              onChange={(event) => setStoreId(event.target.value)}
            >
              {visible.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name ?? "Unnamed store"}
                </option>
              ))}
            </select>
          )}
          {view.can_refresh && (
            <button
              className="button secondary"
              onClick={refresh}
              disabled={refreshing}
            >
              <RefreshCw size={16} className={refreshing ? "spinning" : ""} />
              {refreshing ? "Reading…" : "Refresh"}
            </button>
          )}
        </div>
      </div>
      {error && (
        <div className="error-note" role="alert">
          {error}
        </div>
      )}
      {Object.keys(trading.money_flags).length > 0 && (
        <p className="items-warning small-text">
          <CircleAlert size={14} />
          Some receipts carry tax, tip or surcharge (
          {Object.entries(trading.money_flags)
            .map(([field, count]) => `${field}: ${count}`)
            .join(", ")}
          ). The money mapping this project validated covers receipts without
          them, so treat these totals as needing a separate check.
        </p>
      )}
      {trading.excluded_periods.length === 0 && user.role === "owner" && (
        <p className="items-warning small-text">
          <CircleAlert size={14} />
          No period is marked as unrepresentative. If trading was disrupted — a
          renovation, a closure — set <code>
            SH_LOYVERSE_EXCLUDED_PERIODS
          </code>{" "}
          so those days are flagged in the chart instead of quietly dragging
          every comparison down.
        </p>
      )}

      <div className="items-summary perf-summary">
        {tiles.map((tile) => (
          <div key={tile.label}>
            <span className="eyebrow">{tile.label}</span>
            <strong>{tile.value}</strong>
            <small>{tile.note}</small>
          </div>
        ))}
      </div>

      {catalogue.suppliers &&
        (() => {
          const due = lines.filter(
            (line) =>
              line.reorder?.status === "order_now" ||
              line.reorder?.status === "out_of_stock",
          );
          const bySupplier = new Map<string, Line[]>();
          for (const line of due) {
            const key = line.reorder!.supplier_name;
            bySupplier.set(key, [...(bySupplier.get(key) ?? []), line]);
          }
          const groups = [...bySupplier.entries()].sort(
            (a, b) => b[1].length - a[1].length,
          );
          return (
            <section className="panel-block">
              <div className="section-heading">
                <h2>
                  <PackageCheck size={17} /> Needs ordering
                </h2>
                <span className="eyebrow">
                  {due.length} OF {lines.length} LINES
                </span>
              </div>
              {groups.length === 0 ? (
                <p className="small-text unknown-value">
                  Nothing is due at the recent sales rate. A product whose stock
                  or rate is unknown gives no advice either way.
                </p>
              ) : (
                <div className="order-groups">
                  {groups.map(([supplier, rows]) => {
                    const first = rows[0].reorder!;
                    return (
                      <div className="order-group" key={supplier}>
                        <div className="order-head">
                          <strong>{supplier}</strong>
                          <small>
                            {first.cycle
                              ? `order ${first.next_order_day} \u00b7 arrives ${first.arrives}`
                              : `${first.lead_days?.min}\u2013${first.lead_days?.max} days${
                                  first.buffer_days
                                    ? ` + ${first.buffer_days} buffer`
                                    : ""
                                }`}
                          </small>
                        </div>
                        <ul className="order-list">
                          {rows.slice(0, 12).map((line) => (
                            <li key={line.variantId}>
                              <span>{line.name}</span>
                              <small
                                className={
                                  line.reorder!.status === "out_of_stock"
                                    ? "short-by"
                                    : ""
                                }
                              >
                                {line.reorder!.status === "out_of_stock"
                                  ? "out of stock"
                                  : `${line.reorder!.days_of_cover} days left`}
                              </small>
                            </li>
                          ))}
                          {rows.length > 12 && (
                            <li className="unknown-value">
                              <span>and {rows.length - 12} more</span>
                            </li>
                          )}
                        </ul>
                      </div>
                    );
                  })}
                </div>
              )}
              {catalogue.suppliers.unassigned_count > 0 &&
                user.role === "owner" && (
                  <p className="small-text muted">
                    {catalogue.suppliers.unassigned_count} item
                    {catalogue.suppliers.unassigned_count === 1 ? "" : "s"}{" "}
                    match no supplier rule and deliberately get no advice:{" "}
                    {catalogue.suppliers.unassigned
                      .slice(0, 6)
                      .map((row) => row.item)
                      .join(", ")}
                    .
                  </p>
                )}
            </section>
          );
        })()}

      <section className="panel-block">
        <div className="section-heading">
          <h2>Taken per day</h2>
          <span className="eyebrow">
            {trading.from} → {trading.to}
          </span>
        </div>
        <Bars trading={trading} currency={currency} />
        {trading.excluded_periods.length > 0 && (
          <p className="small-text muted">
            Amber bars fall inside a period marked as not representative:{" "}
            {trading.excluded_periods
              .map(
                (period) => `${period.from} to ${period.to} (${period.reason})`,
              )
              .join("; ")}
            .
          </p>
        )}
      </section>

      <section className="panel-block">
        <div className="section-heading">
          <h2>
            <Clock size={17} /> When people actually come in
          </h2>
          <span className="eyebrow">
            RECEIPTS · UTC+{trading.local_utc_offset_hours}
          </span>
        </div>
        <Heatmap trading={trading} />
        <p className="small-text muted">
          Local hours assume UTC+{trading.local_utc_offset_hours}, which earlier
          receipt reconciliation matched. The store's configured timezone is
          still unconfirmed upstream, so treat the edges of the day with a
          little care.
        </p>
      </section>

      <div className="rank-grid">
        <Ranking
          title={
            rankBy === "collected"
              ? "Bestsellers by takings"
              : "Bestsellers by units"
          }
          hint="Over the whole saved history. These two lists are not the same."
          lines={best}
          empty="Nothing sold in this period."
          render={(line) =>
            rankBy === "collected"
              ? {
                  value: money(line.history.collected, currency),
                  note: `${quantity(line.history.units)} units`,
                }
              : {
                  value: `${quantity(line.history.units)} units`,
                  note: money(line.history.collected, currency) ?? "",
                }
          }
        />
        <Ranking
          title="Weakest sellers"
          hint="Sold at least once, but least of all. Last sale shown so you can see how stale it is."
          lines={weakest}
          empty="Nothing sold in this period."
          render={(line) => ({
            value: money(line.history.collected, currency),
            note: line.history.last_sold
              ? `last ${dayLabel(line.history.last_sold)}`
              : "—",
          })}
        />
        <Ranking
          title="Stock with no sales"
          hint="On the shelf for the whole period without selling once. This is money standing still."
          lines={deadStock}
          empty="Everything in stock has sold at least once."
          render={(line) => ({
            value: `${quantity(line.inStock)} in stock`,
            note: "no sale in this period",
          })}
        />
        <Ranking
          title="Out of stock, still selling"
          hint="Nothing left on the shelf but it was moving. Every day like this is a sale that cannot happen."
          lines={stockedOut}
          empty="Nothing that sells is out of stock."
          render={(line) => ({
            value: `${quantity(line.perWeek)}/week`,
            note: "none in stock",
          })}
        />
        <Ranking
          title="Running low"
          hint="Stock divided by the recent weekly rate. Under two weeks of cover left."
          lines={running.map((entry) => entry.line)}
          empty="Nothing is close to running low at the recent rate."
          render={(line) => {
            const days = coverDays(line);
            return {
              value:
                days === null ? "—" : `${days.toFixed(days < 10 ? 1 : 0)} days`,
              note: `${quantity(line.inStock)} left · ${quantity(line.perWeek)}/week`,
            };
          }}
        />
        <Ranking
          title="Selling, but unguarded"
          hint="Moves at least one a week and has no low-stock threshold set in Loyverse, so nothing will warn you."
          lines={unguarded}
          empty="Every regular seller has a threshold set."
          render={(line) => ({
            value: `${quantity(line.perWeek)}/week`,
            note: "no low-stock alert set",
          })}
        />
      </div>

      <div className="items-limits">
        <h3>
          <CircleHelp size={15} /> What these figures are
        </h3>
        <ul className="small-text muted">
          <li>
            Everything here is what the POS recorded, counted by business date.
            It is a reported observation, not reconciled against cash, bank or
            settlement.
          </li>
          <li>
            Takings are the amounts receipts say were collected, with refunds
            subtracted once. No cost, margin or profit is derived anywhere on
            this page.
          </li>
          <li>
            The history is only as deep as the account: {trading.calendar_days}{" "}
            days from {trading.from}. Nothing earlier exists to read.
          </li>
          <li>
            A day with no receipts is shown as having none. That is not a claim
            that the shop was closed.
          </li>
          <li>
            Cover and weekly rates use the recent sales window, so a disrupted
            period distorts them until it is marked.
          </li>
        </ul>
      </div>
      <div className="rank-toggle">
        <button
          className="button ghost"
          onClick={() =>
            setRankBy(rankBy === "collected" ? "units" : "collected")
          }
        >
          Rank bestsellers by {rankBy === "collected" ? "units" : "takings"}
        </button>
      </div>
    </>
  );
}
