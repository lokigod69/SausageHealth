import { useState, type FormEvent } from "react";
import { ExternalLink, Link2, Pencil, Trash2 } from "lucide-react";
import { api, type ItemLink } from "./api";

/** Only plain https links are accepted, and the same rule is enforced server side. */
function looksLikeLink(value: string) {
  return value.trim() === "" || /^https:\/\/\S+$/.test(value.trim());
}

/** The recorded link as the shop reads it: a page to open, not a search to run. */
export function LinkCell({
  link,
  canEdit,
  onEdit,
}: {
  link: ItemLink | undefined;
  canEdit: boolean;
  onEdit: () => void;
}) {
  if (!link?.url && !link?.alternative_url)
    return canEdit ? (
      <button className="link-add" onClick={onEdit}>
        <Link2 size={13} /> Add
      </button>
    ) : (
      <span className="unknown-value">—</span>
    );
  return (
    <span className="link-cell">
      {link.url && (
        <a href={link.url} target="_blank" rel="noreferrer noopener">
          <ExternalLink size={13} /> Shop
        </a>
      )}
      {link.alternative_url && (
        <a
          href={link.alternative_url}
          target="_blank"
          rel="noreferrer noopener"
          className="link-alternative"
        >
          <ExternalLink size={13} /> {link.alternative_name ?? "Alternative"}
        </a>
      )}
      {canEdit && (
        <button className="icon-button" onClick={onEdit} title="Edit this link">
          <Pencil size={13} />
          <span className="visually-hidden">Edit this link</span>
        </button>
      )}
    </span>
  );
}

/** The form that records a link, shown as a row under the item it belongs to. */
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
  const [url, setUrl] = useState(link?.url ?? "");
  const [altName, setAltName] = useState(link?.alternative_name ?? "");
  const [altUrl, setAltUrl] = useState(link?.alternative_url ?? "");
  const [note, setNote] = useState(link?.note ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!looksLikeLink(url) || !looksLikeLink(altUrl)) {
      setError("A link has to start with https:// and contain no spaces.");
      return;
    }
    if (altUrl.trim() && !altName.trim()) {
      setError("Name the alternative source, so a reader knows who it is.");
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
            url: url.trim() || null,
            alternative_name: altName.trim() || null,
            alternative_url: altUrl.trim() || null,
            note: note.trim() || null,
            sku,
            item_name: itemName,
          }),
        },
      );
      // Clearing every field removes the record, and the server says so.
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
          Shop link
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://shopee.ph/..."
            autoComplete="off"
            autoFocus
          />
        </label>
        <label className="link-editor-narrow">
          Alternative source
          <input
            value={altName}
            onChange={(event) => setAltName(event.target.value)}
            placeholder="Other seller, Lazada…"
            autoComplete="off"
          />
        </label>
        <label>
          Alternative link
          <input
            value={altUrl}
            onChange={(event) => setAltUrl(event.target.value)}
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
        A short Shopee link works too; it is stored exactly as pasted. Paste the
        page for this exact size and flavour — the link is recorded against this
        one variant, not the whole item.
      </p>
      {error && <div className="error-note">{error}</div>}
      <div className="link-editor-actions">
        <button className="button secondary" disabled={busy}>
          {busy ? "Saving…" : "Save link"}
        </button>
        <button
          className="button ghost"
          type="button"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </button>
        {(link?.url || link?.alternative_url) && (
          <button
            className="button ghost danger"
            type="button"
            onClick={drop}
            disabled={busy}
          >
            <Trash2 size={14} /> Remove
          </button>
        )}
      </div>
    </form>
  );
}
