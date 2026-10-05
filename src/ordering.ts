/** The order view's text and figures, kept out of the component so they can be tested.
 *
 *  The one rule that matters here: `orderMessage` is sent to a supplier over
 *  WhatsApp. Our buying ceiling is our margin, so nothing derived from it may
 *  appear in that text -- it belongs on the shop's own screen only.
 */
import type { Reorder } from "./api";

export type Due = {
  key: string;
  name: string;
  sku: string | null;
  inStock: string | null;
  reorder: Reorder;
};

export type Group = {
  supplierId: string;
  supplierName: string;
  reorder: Reorder;
  items: Due[];
};

/** The message a person would otherwise type out by hand. */
export function orderMessage(group: Group, branch: string) {
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

/** `0.30` shown as `30%`.
 *
 *  Fixed to two places first: in binary floating point `0.3 * 100` is
 *  30.000000000000004, which would reach the screen verbatim.
 */
export function percentLabel(share: string | null) {
  if (!share) return null;
  return `${(Number(share) * 100).toFixed(2).replace(/\.?0+$/, "")}%`;
}

/** The margin the ceilings on one supplier's card hold, or null if none do. */
export function groupMargin(group: Group) {
  return (
    group.items.find((due) => due.reorder.target_margin)?.reorder
      .target_margin ?? null
  );
}

/** Whether anything on this card has a ceiling worth explaining.
 *
 *  A missing state is not a ceiling: a catalogue stored before the ceiling
 *  shipped has no such field, and explaining one that is not shown would be
 *  describing something the reader cannot see.
 */
export function hasCeiling(group: Group) {
  return group.items.some(
    (due) =>
      Boolean(due.reorder.target_state) &&
      due.reorder.target_state !== "not_shopee",
  );
}
