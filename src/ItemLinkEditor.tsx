import { useState, type FormEvent } from "react";
import { ExternalLink, Link2, Pencil, Trash2 } from "lucide-react";
import { api, type ItemLink } from "./api";

/** Only plain https links are accepted, and the same rule is enforced server side. */
function looksLikeLink(value: string) {
  return value.trim() === "" || /^https:\/\/\S+$/.test(value.trim());
}

/** The two named slots are checked here as well, so a mistake is caught before saving. */
const SHOPEE = /^https:\/\/([a-z0-9-]+\.)*(shopee\.ph|shp\.ee)(\/|$)/i;
const LAZADA =
  /^https:\/\/([a-z0-9-]+\.)*(lazada\.com\.ph|lazada\.sg|lzd\.co)(\/|$)/i;

/** Every recorded link for one variant, in the order a person should try them. */
function filled(link: ItemLink | undefined) {
  if (!link) return [];
  return [
    { name: "Shopee", url: link.url },
    { name: "Lazada", url: link.lazada_url },
    { name: link.alternative_name ?? "Other", url: link.alternative_url },
  ].filter((slot): slot is { name: string; url: string } => Boolean(slot.url));
}

/** The recorded links as the shop reads them: pages to open, not searches to run. */
export function LinkCell({
  link,
  canEdit,
  onEdit,
}: {
  link: ItemLink | undefined;
  canEdit: boolean;
  onEdit: () => void;
}) {
  const slots = filled(link);
  if (!slots.length)
    return canEdit ? (
      <button className="link-add" onClick={onEdit}>
        <Link2 size={13} /> Add
      </button>
    ) : (
      <span className="unknown-value">—</span>
    );
  return (
    <span className="link-cell">
      {slots.map((slot, index) => (
        <a
          key={slot.url}
          href={slot.url}
          target="_blank"
          rel="noreferrer noopener"
          className={index ? "link-alternative" : undefined}
        >
          <ExternalLink size={13} /> {slot.name}
        </a>
      ))}
      {canEdit && (
        <button
          className="icon-button"
          onClick={onEdit}
          title="Edit these links"
        >
          <Pencil size={13} />
          <span className="visually-hidden">Edit these links</span>
        </button>
      )}
    </span>
  );
}

/** The form that records the links, shown as a row under the item they belong to. */
export function LinkEditor({
  variantId,
  sku,
  itemName,
  link,
  onSaved,
  onCancel,
}: {
  variantId: string;
  sku: string | null;
  itemName: string | null;
  link: ItemLink | undefined;
  onSaved: (link: ItemLink | null) => void;
  onCancel: () => void;
}) {
  const [shopee, setShopee] = useState(link?.url ?? "");
  const [lazada, setLazada] = useState(link?.lazada_url ?? "");
  const [otherName, setOtherName] = useState(link?.alternative_name ?? "");
  const [otherUrl, setOtherUrl] = useState(link?.alternative_url ?? "");
  const [note, setNote] = useState(link?.note ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function wrongField() {
    for (const value of [shopee, lazada, otherUrl])
      if (!looksLikeLink(value))
        return "A link has to start with https:// and contain no spaces.";
    if (shopee.trim() && !SHOPEE.test(shopee.trim()))
      return "That is not a shopee.ph link. Put it in the third slot and name it.";
    if (lazada.trim() && !LAZADA.test(lazada.trim()))
      return "That is not a lazada.com.ph link. Put it in the third slot and name it.";
    if (otherUrl.trim() && !otherName.trim())
      return "Name the third source, so a reader knows who it is.";
    return "";
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const wrong = wrongField();
    if (wrong) {
      setError(wrong);
      return;
    }
    setError("");
    setBusy(true);
    try {
      const saved = await api<ItemLink | { ok: boolean }>(
        `/item-links/${encodeURIComponent(variantId)}`,
        {
          method: "PUT",
          body: JSON.stringify({
            url: shopee.trim() || null,
            lazada_url: lazada.trim() || null,
            alternative_name: otherName.trim() || null,
            alternative_url: otherUrl.trim() || null,
            note: note.trim() || null,
            sku,
            item_name: itemName,
          }),
        },
      );
      // Clearing every link removes the record, and the server says so.
      onSaved("variant_id" in saved ? (saved as ItemLink) : null);
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function drop() {
    setError("");
    setBusy(true);
    try {
      await api(`/item-links/${encodeURIComponent(variantId)}`, {
        method: "DELETE",
      });
      onSaved(null);
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="link-editor" onSubmit={save}>
      <div className="link-editor-fields">
        <label>
          Shopee
          <input
            value={shopee}
            onChange={(event) => setShopee(event.target.value)}
            placeholder="https://shopee.ph/..."
            autoComplete="off"
            autoFocus
          />
        </label>
        <label>
          Lazada
          <input
            value={lazada}
            onChange={(event) => setLazada(event.target.value)}
            placeholder="https://www.lazada.com.ph/..."
            autoComplete="off"
          />
        </label>
      </div>
      <div className="link-editor-fields">
        <label className="link-editor-narrow">
          Third source · name
          <input
            value={otherName}
            onChange={(event) => setOtherName(event.target.value)}
            placeholder="Other seller, a shop, a website…"
            autoComplete="off"
          />
        </label>
        <label>
          Third source · link
          <input
            value={otherUrl}
            onChange={(event) => setOtherUrl(event.target.value)}
            placeholder="https://..."
            autoComplete="off"
          />
        </label>
        <label className="link-editor-narrow">
          Note
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Pack size, variant…"
            autoComplete="off"
          />
        </label>
      </div>
      <p className="small-text muted">
        Fill in whichever you have; none is required. A short Shopee link works
        too, and is stored exactly as pasted. Paste the page for this exact size
        and flavour — the links are recorded against this one variant, not the
        whole item. Only the Shopee page gets a buying ceiling, because that is
        where a price is picked off a listing.
      </p>
      {error && <div className="error-note">{error}</div>}
      <div className="link-editor-actions">
        <button className="button secondary" disabled={busy}>
          {busy ? "Saving…" : "Save links"}
        </button>
        <button
          className="button ghost"
          type="button"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </button>
        {filled(link).length > 0 && (
          <button
            className="button ghost danger"
            type="button"
            onClick={drop}
            disabled={busy}
          >
            <Trash2 size={14} /> Remove all
          </button>
        )}
      </div>
    </form>
  );
}
