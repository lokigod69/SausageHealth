import { useEffect, useState, type FormEvent } from "react";
import { Check, Copy, Tablet, Trash2 } from "lucide-react";
import { api, timeLabel, type Account, type Device } from "./api";

export function Devices() {
  const [devices, setDevices] = useState<Device[] | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [name, setName] = useState("");
  const [actsAs, setActsAs] = useState("");
  const [issued, setIssued] = useState<{ code: string; name: string } | null>(
    null,
  );
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setDevices(await api<Device[]>("/devices"));
      const people = await api<Account[]>("/users");
      setAccounts(people);
      setActsAs((current) => current || people[0]?.id || "");
    } catch (problem) {
      setError((problem as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const made = await api<{ code: string; name: string }>("/devices", {
        method: "POST",
        body: JSON.stringify({ name, acts_as: actsAs }),
      });
      setIssued({ code: made.code, name: made.name });
      setName("");
      await load();
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function revoke(device: Device) {
    setError("");
    try {
      await api(`/devices/${device.id}/revoke`, { method: "POST" });
      await load();
    } catch (problem) {
      setError((problem as Error).message);
    }
  }

  return (
    <section className="settings-card">
      <h2>
        <Tablet size={17} /> Shop tablets
      </h2>
      <p className="muted small-text">
        A paired tablet stays signed in and is never logged out on its own. That
        is only safe because you can end it here: revoking takes effect on the
        tablet's very next request.
      </p>

      {issued && (
        <div className="pairing-code">
          <span className="eyebrow">CODE FOR {issued.name.toUpperCase()}</span>
          <strong>{issued.code}</strong>
          <p className="small-text muted">
            Type this on the tablet, on the sign-in screen, under "Pair a shop
            tablet". It works once and expires in 15 minutes.
          </p>
          <button
            className="button secondary"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(issued.code);
                setCopied(true);
                setTimeout(() => setCopied(false), 2500);
              } catch {
                setCopied(false);
              }
            }}
          >
            {copied ? <Check size={15} /> : <Copy size={15} />}
            {copied ? "Copied" : "Copy code"}
          </button>
        </div>
      )}

      <form className="pairing-form" onSubmit={create}>
        <label>
          Device name
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Counter tablet"
            required
          />
        </label>
        <label>
          Acts as
          <select
            value={actsAs}
            onChange={(event) => setActsAs(event.target.value)}
          >
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name} · {account.role}
              </option>
            ))}
          </select>
        </label>
        <button
          className="button secondary"
          disabled={busy || !accounts.length}
        >
          {busy ? "Creating…" : "Create pairing code"}
        </button>
      </form>
      {accounts.length === 0 && (
        <p className="small-text unknown-value">
          There is no account for a tablet to act as yet. The owner account is
          deliberately not offered: a tablet on the counter should not be able
          to export the collection or read the audit trail.
        </p>
      )}
      {error && <div className="error-note">{error}</div>}

      {devices && devices.length > 0 && (
        <ul className="device-list">
          {devices.map((device) => (
            <li key={device.id} className={device.revoked ? "revoked" : ""}>
              <span>
                <strong>{device.name}</strong>
                <small>
                  acts as {device.acts_as} ·{" "}
                  {device.revoked
                    ? "ended"
                    : !device.paired
                      ? "waiting for the code"
                      : device.last_seen
                        ? `last used ${timeLabel(device.last_seen)}`
                        : "paired"}
                </small>
              </span>
              {!device.revoked && (
                <button className="icon-button" onClick={() => revoke(device)}>
                  <Trash2 size={16} />
                  <span className="visually-hidden">End this device</span>
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
