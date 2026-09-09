import type { Category, Entry, Store, User } from "./api";

export const journeyPhases = [
  {
    name: "Collect",
    place: "The landing",
    subtitle: "Give the everyday a home.",
    description:
      "Bring in a little evidence from each store. Review it as it arrives, and write down what is still unclear.",
    owner: "Moritz collects · technical owner prepares access",
    outcome: "A shared intake routine that works on the team's real phones.",
    gates: [
      "Individual accounts, HTTPS, a phone upload and a tested restore before inviting the team.",
      "One sales source for each store, then receipts, running costs and stock exports. Collect 30 days as a starting batch; mark missing days.",
      "Moritz checks store, date, readability and duplicates. Reviewing a source does not verify its accounting.",
      "One staff practice update, a closing routine and a named person for unanswered questions.",
    ],
    risk: "A folder full of files can still hide gaps.",
    response:
      "Check each store and date separately. Keep originals and link corrections; never fill missing figures with zero.",
  },
  {
    name: "Understand",
    place: "The observatory",
    subtitle: "Make the numbers explainable.",
    description:
      "Match records, resolve differences and build calculations that can be traced back to the original evidence.",
    owner:
      "Technical owner builds · Moritz reconciles · accountant confirms rules",
    outcome:
      "A source-linked view of revenue, costs, cash flow and data gaps for each store.",
    gates: [
      "Verify read-only Loyverse access, receipt/refund imports and ten real product mappings, including kg, packs and pieces.",
      "Record opening stock, transfers, waste and expiry. Include recipes, ingredients and yields for kefir and yogurt production.",
      "Reconcile sales to cash/GCash/cards; separate inventory costs, supplier payments, overhead and investor funding.",
      "The accountant confirms periods, tax treatment and cost allocation. Profit stays unknown until the ledger and coverage support it.",
    ],
    risk: "Sales minus purchases can look like profit while inventory and unpaid bills are missing.",
    response:
      "Use deterministic calculations, opening balances and a reconciled ledger. Show coverage and unresolved differences alongside every total.",
  },
  {
    name: "Improve",
    place: "The market garden",
    subtitle: "Try small changes. Learn what works.",
    description:
      "Use verified information to protect best sellers, reduce waste and test the reasons customers choose us.",
    owner:
      "Moritz executes · technical owner measures · owners approve budgets",
    outcome:
      "Repeatable improvements with a recorded cost, result and decision.",
    gates: [
      "Fresh stock, supplier lead times, pack sizes, order minimums and expiry inform reorder proposals.",
      "Verify the existing procurement app before using its quote and marketplace handoff; a person approves each purchase.",
      "Run one product, merchandising or marketing experiment at a time with a baseline, budget and review date.",
      "Review margin, waste, stockouts and cash weekly. Keep an experiment only when its evidence supports the result.",
    ],
    risk: "A busy competitor or a good sales day can lead to an expensive assumption.",
    response:
      "Record observations, compare like-for-like periods and start with a small reversible trial. Do not treat a hypothesis as customer demand.",
  },
  {
    name: "Grow",
    place: "The harbour",
    subtitle: "Open the next route with confidence.",
    description:
      "Let customers check products and request orders, then expand a store operation that the team can repeat.",
    owner: "Owners approve · Moritz runs fulfilment · technical owner builds",
    outcome:
      "Reliable customer service and a tested playbook for another store.",
    gates: [
      "Publish only approved product information, with stock freshness and a clear handoff when availability is uncertain.",
      "Test reservations, payment confirmation, cancellations, refunds, delivery zones, fees and staff escalation end to end.",
      "Authorize customer channels and any ad spend explicitly. Keep private receipts, costs and customer records out of the public site.",
      "Confirm store economics, staffing, training and operational capacity before expansion. A product for other businesses needs separate tenancy and support design.",
    ],
    risk: "Two customers can request the last pack, or an assistant can promise an unavailable delivery.",
    response:
      "Reserve stock through an authoritative order workflow. Treat chat as a request until stock, payment and delivery are confirmed.",
  },
] as const;

export type StarterTask = {
  store: Exclude<Store, "both">;
  category: Category;
  title: string;
  detail: string;
  state: "missing" | "submitted" | "reviewed";
  entry?: Entry;
};

// Visible evidence only. Shared records cannot stand in for either store's own
// daily report. "Reviewed" means source review, never financial completeness.
export function starterTasks(
  entries: Entry[],
  user: User,
  scope: Store,
): StarterTask[] {
  const stores = user.stores.filter(
    (s): s is Exclude<Store, "both"> =>
      s !== "both" && (scope === "both" || scope === s),
  );
  const visible = entries.filter(
    (e) =>
      (e.store === "both"
        ? user.stores.includes("sausage") && user.stores.includes("health")
        : user.stores.includes(e.store)) &&
      (user.role !== "staff" || e.author_id === user.id),
  );
  const starters: { category: Category; title: string; detail: string }[] = [
    {
      category: "sales",
      title: "Share one day of sales",
      detail:
        "Add a dated report or the message already sent at closing. Say whether cash, GCash, cards and refunds are included.",
    },
    {
      category: "suppliers",
      title: "Add one supplier receipt",
      detail:
        "Capture the full receipt, when stock arrived and any unpaid balance. A clear photo is enough.",
    },
    {
      category: "expenses",
      title: "Capture a running cost",
      detail:
        "Start with rent, electricity or a payroll total. Include the period and whether it is paid.",
    },
    {
      category: "stock",
      title: "Share a product or stock source",
      detail:
        "Bring a Loyverse export or a shelf/freezer photo. Include units; leave unknown counts unknown.",
    },
  ];
  return starters.flatMap((task) =>
    stores.map((store) => {
      const matching = visible.filter(
        (e) => e.store === store && e.category === task.category,
      );
      const entry =
        matching.find((e) => e.status === "reviewed") ?? matching[0];
      return {
        ...task,
        store,
        entry,
        state: entry
          ? entry.status === "reviewed"
            ? "reviewed"
            : "submitted"
          : "missing",
      };
    }),
  );
}
