import { Check, Hand } from "lucide-react";
import { type Reorder } from "./api";

export type KnownSupplier = { id: string; name: string; note: string | null };

/** The supplier a product comes from, and whether that was a rule or a decision.
 *
 *  A choice made by hand is marked, because the difference matters when the
 *  assignment looks wrong: a rule can be corrected for every product it sweeps
 *  up, while a decision was made about this one product only.
 */
export function SupplierCell({
  reorder,
  chosen,
  known,
  canEdit,
  pending,
  onChoose,
}: {
  reorder: Reorder | null;
  chosen: string | undefined;
  known: KnownSupplier[];
  canEdit: boolean;
  pending: boolean;
  onChoose: (supplierId: string) => void;
}) {
  // A choice saved in this session is shown at once; the stored catalogue only
  // catches up on the next sync, and waiting for that would look broken.
  const effective = chosen ?? reorder?.supplier_id ?? "";
  const byHand = chosen !== undefined || reorder?.by_hand;
  const name =
    known.find((row) => row.id === effective)?.name ??
    reorder?.supplier_name ??
    null;

  if (!canEdit)
    return name ? (
      <span className="supplier-cell">{name}</span>
    ) : (
      <span className="unknown-value">No rule</span>
    );

  return (
    <span className="supplier-cell">
      <select
        value={effective}
        disabled={pending}
        onChange={(event) => onChoose(event.target.value)}
        aria-label="Supplier for this product"
      >
        <option value="">{name && !effective ? name : "No supplier"}</option>
        {known.map((row) => (
          <option key={row.id} value={row.id}>
            {row.name}
          </option>
        ))}
      </select>
      {pending ? (
        <Check size={12} className="supplier-saving" />
      ) : byHand ? (
        <span
          title="Chosen by hand, not by a rule"
          className="supplier-by-hand"
        >
          <Hand size={12} />
        </span>
      ) : null}
    </span>
  );
}
