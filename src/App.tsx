import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  AudioLines,
  BookOpen,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  Compass,
  File,
  FileText,
  Home,
  Leaf,
  LockKeyhole,
  LogOut,
  Map,
  MapPin,
  Menu,
  Moon,
  Package,
  Plus,
  Receipt,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Sprout,
  Store as StoreIcon,
  Sun,
  Upload,
  Users,
  Wallet,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  categoryNames,
  dateLabel,
  fileSize,
  manilaDate,
  prompts,
  storeNames,
  type Category,
  type Entry,
  type Store,
  type User,
} from "./api";

import { Journey, NextStep } from "./Journey";

type Page =
  "overview" | "collection" | "stores" | "roadmap" | "team" | "settings";
const navItems = [
  { id: "overview", label: "Overview", icon: Home },
  { id: "collection", label: "Collection", icon: BookOpen },
  { id: "stores", label: "Our stores", icon: StoreIcon },
  { id: "roadmap", label: "The journey", icon: Map },
  { id: "team", label: "Agent team", icon: Sparkles },
] as const;
const catIcons = {
  sales: Receipt,
  stock: Package,
  suppliers: ClipboardList,
  expenses: Wallet,
  team: Users,
  walkthrough: MapPin,
  other: FileText,
};

function PixelMark({ small = false }: { small?: boolean }) {
  return (
    <span className={`pixel-mark ${small ? "small" : ""}`} aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
      <i />
      <i />
      <i />
      <i />
      <i />
    </span>
  );
}
function ErrorNote({ message }: { message: string }) {
  return message ? (
    <div className="error-note" role="alert">
      {message}
    </div>
  ) : null;
}
function Tag({ children, tone = "" }: { children: ReactNode; tone?: string }) {
  return <span className={`tag ${tone}`}>{children}</span>;
}
function Modal({
  title,
  children,
  onClose,
  wide = false,
  busy = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = ref.current!;
    element.showModal();
    return () => element.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "wide" : ""}`}
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="modal-top">
        <span className="eyebrow">SAUSAGE HEALTH / {title}</span>
        <button
          type="button"
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
          disabled={busy}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      onLogin(
        await api<User>("/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-world">
        <div className="brand">
          <PixelMark />
          <span>
            sausage<span className="brand-light">health</span>
          </span>
        </div>
        <div className="login-heading">
          <span className="eyebrow">TWO STORES. ONE SHARED VISION.</span>
          <h1>
            A little island.
            <br />A bigger picture.
          </h1>
          <p>A home for everything that helps our stores grow.</p>
        </div>
        <img
          src="/art/island.png"
          alt="Illustrated tropical island with two glowing shops and a small observatory"
        />
        <div className="login-foot">
          <MapPin size={14} /> Panglao Island, Philippines{" "}
          <span>Made for the way we work.</span>
        </div>
      </div>
      <section className="login-form">
        <span className="eyebrow">
          <LockKeyhole size={14} /> YOUR PRIVATE WORKSPACE
        </span>
        <h2>Welcome back.</h2>
        <p>Let’s bring the everyday into focus.</p>
        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
            />
          </label>
          <ErrorNote message={error} />
          <button className="button primary" disabled={busy}>
            {busy ? "Signing in…" : "Enter your workspace"}
            <ArrowRight size={17} />
          </button>
        </form>
        <p className="fine-print">
          Access is by invitation. Ask the technical owner for your account or a
          password reset.
        </p>
        <div className="login-stores">
          <span>
            <StoreIcon size={16} /> The Sausage Guy
          </span>
          <span>
            <Leaf size={16} /> Natural Mind Health
          </span>
        </div>
      </section>
    </main>
  );
}

function Capture({
  user,
  initial,
  initialStore,
  onClose,
  onSaved,
}: {
  user: User;
  initial: Category;
  initialStore: Store;
  onClose: () => void;
  onSaved: (entry: Entry) => void;
}) {
  const [step, setStep] = useState(1);
  const [store, setStore] = useState<Store>(
    initialStore !== "both" && user.stores.includes(initialStore)
      ? initialStore
      : user.stores[0],
  );
  const [category, setCategory] = useState<Category>(initial);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [date, setDate] = useState(manilaDate());
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [reauth, setReauth] = useState(false);
  const [rePassword, setRePassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const pendingForm = useRef<FormData | null>(null);
  const requestKey = useRef(crypto.randomUUID());
  const fileInput = useRef<HTMLInputElement>(null);
  const locked = busy || uncertain;
  useEffect(() => {
    if (!(notes || title || files.length)) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [notes, title, files.length]);
  async function signInAgain() {
    setAuthBusy(true);
    setError("");
    try {
      const account = await api<User>("/login", {
        method: "POST",
        body: JSON.stringify({ email: user.email, password: rePassword }),
      });
      if (account.id !== user.id)
        throw new Error(
          "This update belongs to a different account. Contact the technical owner.",
        );
      setReauth(false);
      setRePassword("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAuthBusy(false);
    }
  }
  function close() {
    if (
      !busy &&
      !authBusy &&
      (!(notes || title || files.length) ||
        window.confirm(
          uncertain
            ? "The save has not been confirmed. Leave without checking? Your draft will be lost; check Collection before submitting a new copy."
            : "Leave this update? It has not been saved yet.",
        ))
    )
      onClose();
  }
  function addFiles(incoming: FileList | File[]) {
    if (locked) return;
    const all = [...files, ...Array.from(incoming)];
    if (
      all.length > 5 ||
      all.some((f) => f.size > 50 * 1024 * 1024) ||
      all.reduce((n, f) => n + f.size, 0) > 100 * 1024 * 1024
    ) {
      setError("Use up to 5 files, 50 MB per file and 100 MB in total.");
      return;
    }
    setFiles(all);
    setError("");
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy || reauth) return;
    setBusy(true);
    setError("");
    const form = pendingForm.current ?? new FormData();
    if (!pendingForm.current) {
      Object.entries({
        store,
        category,
        title: title.trim() || `${categoryNames[category]} · ${date}`,
        notes,
        occurred_on: date,
        request_key: requestKey.current,
      }).forEach(([k, v]) => form.append(k, v));
      files.forEach((file) => form.append("files", file));
    }
    pendingForm.current = form;
    try {
      onSaved(await api<Entry>("/entries", { method: "POST", body: form }));
    } catch (e) {
      setError((e as Error).message);
      if (e instanceof ApiError && e.status === 401) setReauth(true);
      if (e instanceof ApiError && e.status && e.status < 500 && !uncertain) {
        pendingForm.current = null;
        setUncertain(false);
      } else {
        setUncertain(true);
      }
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="ADD AN UPDATE" onClose={close} wide busy={busy || authBusy}>
      <div className="capture-heading">
        <div className="step-count">
          <span className={step === 1 ? "active" : "complete"}>
            {step === 1 ? "1" : <Check size={14} />}
          </span>
          <i />
          <span className={step === 2 ? "active" : ""}>2</span>
        </div>
        <p className="eyebrow">
          {step === 1 ? "A LITTLE CONTEXT" : "THE EVERYDAY DETAILS"}
        </p>
        <h2>
          {step === 1 ? "What are we collecting?" : prompts[category].title}
        </h2>
        <p>
          {step === 1
            ? "Start small. One report, receipt, or thought is enough."
            : prompts[category].hint}
        </p>
      </div>
      {step === 1 ? (
        <div className="capture-body">
          <label>
            Which store?
            <select
              value={store}
              onChange={(e) => setStore(e.target.value as Store)}
            >
              {user.stores.map((s) => (
                <option key={s} value={s}>
                  {storeNames[s]}
                </option>
              ))}
              {user.stores.length === 2 && (
                <option value="both">Both stores</option>
              )}
            </select>
          </label>
          <fieldset>
            <legend>What would you like to add?</legend>
            <div className="category-grid">
              {(Object.keys(categoryNames) as Category[]).map((c) => {
                const Icon = catIcons[c];
                return (
                  <button
                    type="button"
                    key={c}
                    className={`category-option ${category === c ? "selected" : ""}`}
                    aria-pressed={category === c}
                    onClick={() => setCategory(c)}
                  >
                    <Icon size={21} />
                    <span>{categoryNames[c]}</span>
                    {category === c && <Check size={15} />}
                  </button>
                );
              })}
            </div>
          </fieldset>
          <div className="modal-actions">
            <span className="muted small-text">
              Rough notes are welcome here.
            </span>
            <button className="button primary" onClick={() => setStep(2)}>
              Continue
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="capture-body">
          <div className="capture-context">
            <Tag>{storeNames[store]}</Tag>
            <Tag>{categoryNames[category]}</Tag>
          </div>
          <div className="form-row">
            <label>
              A short title <span className="optional">optional</span>
              <input
                maxLength={160}
                disabled={locked}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={`${categoryNames[category]} · ${date}`}
              />
            </label>
            <label>
              Date of the information
              <input
                type="date"
                disabled={locked}
                required
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
          </div>
          <label>
            Add a note
            <textarea
              rows={4}
              disabled={locked}
              maxLength={30000}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={prompts[category].placeholder}
            />
          </label>
          <input
            ref={fileInput}
            className="visually-hidden"
            type="file"
            disabled={locked}
            multiple
            tabIndex={-1}
            aria-label="Choose files"
            accept=".txt,.csv,.tsv,.xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp,.heic,.mp4,.mov,.m4a,.mp3,.wav,.ogg,.webm"
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            className={`dropzone ${dragging ? "dragging" : ""}`}
            disabled={locked}
            onClick={() => fileInput.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              addFiles(e.dataTransfer.files);
            }}
          >
            <Upload size={23} />
            <strong>Add files or drop them here</strong>
            <span>
              Photos, receipts, spreadsheets, WhatsApp text exports, audio &
              short videos
            </span>
            <small>Up to 5 files · 50 MB each · 100 MB total</small>
          </button>
          {files.length > 0 && (
            <div className="file-list">
              {files.map((f, i) => (
                <div key={`${f.name}-${i}`}>
                  <File size={17} />
                  <span>
                    {f.name}
                    <small>{fileSize(f.size)}</small>
                  </span>
                  <button
                    className="icon-button"
                    type="button"
                    aria-label={`Remove ${f.name}`}
                    onClick={() => setFiles(files.filter((_, n) => n !== i))}
                    disabled={locked}
                  >
                    <X size={17} />
                  </button>
                </div>
              ))}
            </div>
          )}
          <ErrorNote message={error} />
          {reauth && (
            <div
              className="reauth-panel"
              role="group"
              aria-label="Sign in again without losing your update"
            >
              <strong>Your session ended. Your draft is still here.</strong>
              <p>Sign in again as {user.email}, then save this update.</p>
              <label>
                Password
                <input
                  type="password"
                  autoComplete="current-password"
                  value={rePassword}
                  onChange={(e) => setRePassword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      if (!authBusy && rePassword) void signInAgain();
                    }
                  }}
                />
              </label>
              <button
                type="button"
                className="button secondary"
                disabled={authBusy || !rePassword}
                onClick={signInAgain}
              >
                {authBusy ? "Signing in…" : "Sign in and keep my draft"}
              </button>
            </div>
          )}
          {uncertain && (
            <p className="retry-note" role="status">
              The save may have reached the server. Retry the same update to
              check safely. Its details are held unchanged until we have
              confirmation.
            </p>
          )}
          <p className="capture-note">
            <ShieldCheck size={15} /> Originals are saved privately. This update
            will wait for review.
          </p>
          <div className="modal-actions">
            <button
              type="button"
              className="button ghost"
              onClick={() => setStep(1)}
              disabled={locked}
            >
              <ArrowLeft size={16} />
              Back
            </button>
            <button
              className="button primary"
              disabled={busy || reauth || (!notes.trim() && !files.length)}
            >
              {busy
                ? "Saving your update…"
                : uncertain
                  ? "Retry the same update"
                  : "Save update"}
              {busy ? <span className="spinner" /> : <ArrowRight size={16} />}
            </button>
          </div>
          <span className="fine-print">
            Wait for the saved confirmation before closing. Your draft stays on
            this screen if the connection fails.
          </span>
        </form>
      )}
    </Modal>
  );
}

type Draft = {
  id: string;
  status: string;
  model: string;
  error?: string;
  result: null | {
    summary: string;
    facts: { label: string; value: string; source_id: string; quote: string }[];
    questions: string[];
  };
};
function EntryDetail({
  entry,
  user,
  aiConnected,
  onClose,
  onReviewed,
}: {
  entry: Entry;
  user: User;
  aiConnected: boolean;
  onClose: () => void;
  onReviewed: (entry: Entry) => void;
}) {
  const [note, setNote] = useState(entry.review_note);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  useEffect(() => {
    if (user.role !== "staff")
      api<Draft | null>(`/entries/${entry.id}/draft`)
        .then(setDraft)
        .catch(() => {});
  }, [entry.id, user.role]);
  async function extract() {
    setBusy(true);
    setError("");
    try {
      setDraft(
        await api<Draft>(`/entries/${entry.id}/extract`, { method: "POST" }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function review() {
    setBusy(true);
    setError("");
    try {
      onReviewed(
        await api<Entry>(`/entries/${entry.id}/review`, {
          method: "POST",
          body: JSON.stringify({
            status: entry.status === "reviewed" ? "needs_review" : "reviewed",
            note,
            version: entry.version,
          }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="COLLECTED UPDATE" onClose={onClose} wide busy={busy}>
      <div className="detail-content">
        <div className="capture-context">
          <Tag>{storeNames[entry.store]}</Tag>
          <Tag tone={entry.status === "reviewed" ? "green" : "amber"}>
            {entry.status === "reviewed" ? "Reviewed" : "Needs review"}
          </Tag>
        </div>
        <h2>{entry.title}</h2>
        <p className="muted small-text">
          {categoryNames[entry.category]} · {dateLabel(entry.occurred_on)}
          <br />
          Added by {entry.author_name} on {dateLabel(entry.created_at)}
        </p>
        <div className="source-note">
          {entry.notes || "The original attachment contains this update."}
        </div>
        <h3>
          Original files{" "}
          <span className="muted">({entry.attachments.length})</span>
        </h3>
        {entry.attachments.length ? (
          <div className="file-list">
            {entry.attachments.map((f) => (
              <a href={`/api/files/${f.id}`} key={f.id} download>
                <File size={18} />
                <span>
                  {f.name}
                  <small>{fileSize(f.size)} · Original preserved</small>
                </span>
                <ArrowDownToLine size={18} />
              </a>
            ))}
          </div>
        ) : (
          <p className="muted small-text">This update was saved as a note.</p>
        )}
        {entry.reviewed_at && (
          <div className="review-record">
            <CheckCheck size={17} />
            <p>
              {entry.status === "reviewed" ? "Reviewed" : "Returned for review"}{" "}
              by {entry.reviewer_name} · {dateLabel(entry.reviewed_at)}
              {entry.review_note && <span>{entry.review_note}</span>}
            </p>
          </div>
        )}
        {user.role !== "staff" && (
          <section className="ai-section">
            <div className="section-heading">
              <h3>
                <Sparkles size={17} /> A second pair of eyes
              </h3>
              <Tag tone={aiConnected ? "green" : ""}>
                {aiConnected ? "Text assistant ready" : "AI not connected"}
              </Tag>
            </div>
            <p className="muted small-text">
              {aiConnected
                ? "Prepare a draft from this note and readable text exports. Their text will be sent through OpenRouter to the configured model. Photos, PDFs, and audio still need manual review."
                : "The intake assistant is built and waiting for a model connection. You can review the saved original here."}
            </p>
            {aiConnected && (
              <button
                className="button secondary"
                disabled={busy}
                onClick={extract}
              >
                {busy
                  ? "Preparing…"
                  : draft?.status === "complete"
                    ? "Retrieve saved AI draft"
                    : "Prepare AI draft"}
                <Sparkles size={16} />
              </button>
            )}
            {draft?.result && (
              <div className="ai-draft">
                <Tag tone="amber">AI draft · check every claim</Tag>
                <p>{draft.result.summary}</p>
                {draft.result.facts.map((f, i) => (
                  <div className="proposed-fact" key={i}>
                    <strong>{f.label}</strong>
                    <span>{f.value}</span>
                    <blockquote>“{f.quote}”</blockquote>
                    <small>
                      Source:{" "}
                      {f.source_id === "note"
                        ? "Original note"
                        : f.source_id === "context"
                          ? "Submitted store, date & title"
                          : entry.attachments.find((a) => a.id === f.source_id)
                              ?.name || "Original text export"}
                    </small>
                  </div>
                ))}
                {draft.result.questions.length > 0 && (
                  <div className="draft-questions">
                    <h3>Still worth checking</h3>
                    <ul>
                      {draft.result.questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="fine-print">
                  Prepared with {draft.model}. Source quotes were checked
                  automatically; their meaning and accuracy still need your
                  review. No figures have been posted to a ledger.
                </p>
              </div>
            )}
            {draft?.status === "running" && (
              <p className="fine-print">
                A request was started. Check again in a moment. An interrupted
                request can be retried after two minutes.
              </p>
            )}
            {draft?.status === "failed" && (
              <p className="fine-print">
                The last draft could not be completed. Your source is unchanged.
              </p>
            )}
          </section>
        )}
        {user.role !== "staff" && (
          <div className="review-section">
            <h3>Review the source</h3>
            <p className="muted small-text">
              Confirm it is understandable and belongs to the right store and
              date. Reviewing a source does not verify profit or post it to an
              accounting ledger.
            </p>
            <label>
              Review note <span className="optional">optional</span>
              <textarea
                rows={2}
                maxLength={2000}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Anything the team should know about this record?"
              />
            </label>
            <ErrorNote message={error} />
            <button className="button primary" disabled={busy} onClick={review}>
              {busy
                ? "Saving…"
                : entry.status === "reviewed"
                  ? "Return for review"
                  : "Mark as reviewed"}
              <Check size={17} />
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}

function Guide({
  onClose,
  onStart,
}: {
  onClose: () => void;
  onStart: () => void;
}) {
  return (
    <Modal title="YOUR FIRST FIVE MINUTES" onClose={onClose}>
      <div className="guide-content">
        <span className="large-icon">
          <Sprout />
        </span>
        <h2>
          A small start.
          <br />A clearer tomorrow.
        </h2>
        <p>
          You don’t need to organize everything first. Bring one useful thing
          from today.
        </p>
        <ol className="guide-steps">
          <li>
            <span>1</span>
            <div>
              <h3>Choose the store</h3>
              <p>
                Keep each store’s sales and stock separate. Use “Both stores”
                for shared costs or routines.
              </p>
            </div>
          </li>
          <li>
            <span>2</span>
            <div>
              <h3>Add what you already have</h3>
              <p>
                Take a receipt photo, attach a report, or write a note. Say when
                it happened and what it means.
              </p>
            </div>
          </li>
          <li>
            <span>3</span>
            <div>
              <h3>Save, then check</h3>
              <p>
                Wait for “Update saved.” Find it in Collection. Moritz or the
                owner can review it there.
              </p>
            </div>
          </li>
        </ol>
        <div className="gentle-note">
          <AudioLines size={18} />
          <p>
            Prefer talking? Record a short voice note on your phone and attach
            it. Automatic transcription comes after AI is connected.
          </p>
        </div>
        <button className="button primary" onClick={onStart}>
          Let’s add the first update
          <ArrowRight size={17} />
        </button>
      </div>
    </Modal>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [page, setPage] = useState<Page>("overview");
  const [scope, setScope] = useState<Store>("both");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [capture, setCapture] = useState<Category | null>(null);
  const [captureStore, setCaptureStore] = useState<Store | undefined>();
  const [detail, setDetail] = useState<Entry | null>(null);
  const [guide, setGuide] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [collectionLoaded, setCollectionLoaded] = useState(false);
  const [phaseOpen, setPhaseOpen] = useState(0);
  const [light, setLight] = useState(
    () => localStorage.getItem("sh-theme") === "light",
  );
  const [system, setSystem] = useState<{
    ai: string;
    loyverse: string;
    environment: string;
  } | null>(null);
  const [audit, setAudit] = useState<
    | { id: number; actor_name: string; action: string; created_at: string }[]
    | null
  >(null);
  useEffect(() => {
    document.documentElement.dataset.theme = light ? "light" : "dark";
    localStorage.setItem("sh-theme", light ? "light" : "dark");
  }, [light]);
  useEffect(() => {
    api<User>("/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  async function refresh() {
    setError("");
    setCollectionLoaded(false);
    try {
      setEntries(await api<Entry[]>("/entries"));
      setCollectionLoaded(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    if (user) {
      setScope(user.stores.length === 2 ? "both" : user.stores[0]);
      void refresh();
      api<typeof system>("/system")
        .then(setSystem)
        .catch(() => {});
    }
  }, [user]);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(""), 6500);
    return () => clearTimeout(t);
  }, [notice]);
  function navigate(next: Page) {
    setPage(next);
    setMobileNav(false);
    window.scrollTo({ top: 0 });
  }
  function startIntake(category: Category, store: Store) {
    setCaptureStore(store);
    setCapture(category);
  }
  function closeCapture() {
    setCapture(null);
    setCaptureStore(undefined);
  }
  function saved(entry: Entry) {
    setEntries((old) => [entry, ...old.filter((e) => e.id !== entry.id)]);
    closeCapture();
    setNotice("Update saved. The original is safely in your collection.");
  }
  function reviewed(entry: Entry) {
    setEntries((old) => old.map((e) => (e.id === entry.id ? entry : e)));
    setDetail(entry);
    setNotice(
      entry.status === "reviewed" ? "Review saved." : "Returned for review.",
    );
  }
  async function logout() {
    try {
      await api("/logout", { method: "POST" });
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 401)) {
        setError((e as Error).message);
        return;
      }
    }
    setUser(null);
    setEntries([]);
    setCollectionLoaded(false);
    setSystem(null);
    setAudit(null);
    setDetail(null);
    setPage("overview");
    setError("");
  }
  if (loading)
    return (
      <div className="loading-screen">
        <PixelMark />
        <p>Bringing your island into focus…</p>
      </div>
    );
  if (!user) return <Login onLogin={setUser} />;
  const scoped = entries.filter(
    (e) => scope === "both" || e.store === scope || e.store === "both",
  );
  const reviewedCount = scoped.filter((e) => e.status === "reviewed").length;
  const coverage = (Object.keys(categoryNames) as Category[]).filter(
    (c) => c !== "other",
  );
  const ready = coverage.filter((c) =>
    scoped.some((e) => e.category === c),
  ).length;
  const filtered = scoped.filter(
    (e) =>
      (status === "all" || e.status === status) &&
      `${e.title} ${e.notes} ${e.author_name} ${categoryNames[e.category]}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const title =
    page === "overview"
      ? "Your island, in focus."
      : {
          collection: "A home for the everyday.",
          stores: "Two stores. One shared vision.",
          roadmap: "From a small start to something bigger.",
          team: "A thoughtful team, built around you.",
          settings: "Your workspace, your way.",
        }[page];
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {mobileNav && (
        <button
          className="nav-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
        <button
          className="brand"
          onClick={() => navigate("overview")}
          aria-label="Sausage Health home"
        >
          <PixelMark />
          <span>
            sausage<span className="brand-light">health</span>
            <small>THE SHARED PICTURE</small>
          </span>
        </button>
        <div className="workspace-label">
          WORKSPACE <span>01</span>
        </div>
        <nav aria-label="Main navigation">
          {navItems.map((n) => (
            <button
              key={n.id}
              className={`nav-item ${page === n.id ? "active" : ""}`}
              onClick={() => navigate(n.id)}
              aria-current={page === n.id ? "page" : undefined}
            >
              <n.icon size={19} />
              <span>{n.label}</span>
              {n.id === "collection" && entries.length > 0 && (
                <small>{entries.length}</small>
              )}
              {page === n.id && <i />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="phase-mini">
            <div>
              <span className="status-dot" />
              THE BEGINNING<span>01 / 04</span>
            </div>
            <p>Good things take root.</p>
            <div className="phase-track">
              <b />
              <i />
              <i />
              <i />
            </div>
            <button onClick={() => navigate("roadmap")}>
              See our journey
              <ArrowRight size={14} />
            </button>
          </div>
          <button
            className={`nav-item ${page === "settings" ? "active" : ""}`}
            onClick={() => navigate("settings")}
          >
            <Settings2 size={18} />
            Workspace settings
          </button>
          <button className="nav-item" onClick={() => setGuide(true)}>
            <CircleHelp size={18} />A little guidance
          </button>
          <div className="user-row">
            <span className="avatar">{user.name.slice(0, 1)}</span>
            <span>
              {user.name}
              <small>
                {user.role === "owner"
                  ? "Technical owner"
                  : user.role === "manager"
                    ? "Store operator"
                    : "Store team"}
              </small>
            </span>
            <button
              className="icon-button"
              aria-label="Sign out"
              onClick={logout}
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMobileNav(true)}
          >
            <Menu size={23} />
          </button>
          <div className="breadcrumb">
            <Compass size={17} />
            <span>
              {page === "overview"
                ? "Overview"
                : page === "settings"
                  ? "Workspace settings"
                  : navItems.find((n) => n.id === page)?.label}
            </span>
            <span className="breadcrumb-slash">/</span>
            <span className="muted">Panglao, Philippines</span>
          </div>
          <div className="topbar-actions">
            <span className="date-top">{dateLabel(manilaDate())}</span>
            <button
              className="icon-button"
              aria-label={
                light ? "Switch to night theme" : "Switch to day theme"
              }
              onClick={() => setLight(!light)}
            >
              {light ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <span className="avatar small-avatar">{user.name.slice(0, 1)}</span>
          </div>
        </header>
        <main id="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                {page === "overview"
                  ? `A FRESH START, ${user.name.split(" ")[0].toUpperCase()}`
                  : "SAUSAGE HEALTH / WORKSPACE"}
              </p>
              <h1>{title}</h1>
            </div>
            <label className="scope-select">
              <span className="visually-hidden">Filter by store</span>
              <span className="store-symbols">
                <StoreIcon size={14} />
                <Leaf size={14} />
              </span>
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value as Store)}
              >
                {user.stores.length === 2 && (
                  <option value="both">Both stores</option>
                )}
                {user.stores.map((s) => (
                  <option key={s} value={s}>
                    {storeNames[s]}
                  </option>
                ))}
              </select>
              <ChevronDown size={14} />
            </label>
          </div>
          {error && (
            <div className="page-error">
              <ErrorNote message={error} />
              <button className="button ghost" onClick={refresh}>
                Try again
              </button>
            </div>
          )}
          {page === "overview" && (
            <>
              <section className="hero">
                <div className="hero-text">
                  <span className="phase-tag">
                    <span className="status-dot" />
                    PHASE 01 <i /> COLLECT & CONNECT
                  </span>
                  <h2>
                    Good things start
                    <br />
                    with a <em>clear picture.</em>
                  </h2>
                  <p>
                    Collect the everyday. Understand the business.
                    <br className="desktop-br" /> Grow something good, together.
                  </p>
                  <button
                    className="button primary"
                    onClick={() => setCapture("sales")}
                  >
                    <Plus size={18} />
                    {entries.length ? "Add an update" : "Add your first update"}
                    <ArrowRight size={17} />
                  </button>
                  <button
                    className="quiet-link hero-guide"
                    onClick={() => setGuide(true)}
                  >
                    <CircleHelp size={14} />
                    New here? Start with a little guidance
                  </button>
                </div>
                <div className="hero-art">
                  <div className="orbit orbit-one" />
                  <div className="orbit orbit-two" />
                  <img
                    src="/art/island.png"
                    alt="Pixel-art island with our two stores, palms, and an observatory connected by warm paths"
                  />
                  <span className="art-coordinate">
                    9°35′ N &nbsp; 123°45′ E
                    <span>PANGLAO ISLAND · AN ILLUSTRATED VISION</span>
                  </span>
                  <span className="pixel-spark one">✦</span>
                  <span className="pixel-spark two">✦</span>
                </div>
              </section>
              <section className="metrics" aria-label="Collection progress">
                <div>
                  <span className="metric-icon">
                    <BookOpen size={21} />
                  </span>
                  <span>
                    <strong>
                      {collectionLoaded
                        ? scoped.length.toString().padStart(2, "0")
                        : "—"}
                    </strong>
                    <small>Updates collected</small>
                  </span>
                  <span className="metric-detail">
                    Every little piece helps
                  </span>
                </div>
                <div>
                  <span className="metric-icon">
                    <CheckCheck size={22} />
                  </span>
                  <span>
                    <strong>
                      {collectionLoaded
                        ? reviewedCount.toString().padStart(2, "0")
                        : "—"}
                    </strong>
                    <small>Sources reviewed</small>
                  </span>
                  <span className="metric-detail">
                    Building a reliable foundation
                  </span>
                </div>
                <button
                  onClick={() => {
                    navigate("roadmap");
                    setPhaseOpen(1);
                  }}
                >
                  <span className="metric-icon amber-icon">
                    <Wallet size={21} />
                  </span>
                  <span>
                    <strong className="awaiting">Awaiting records</strong>
                    <small>Our profitability picture</small>
                  </span>
                  <ChevronRight size={17} />
                </button>
              </section>
              <div className="dashboard-lower">
                <NextStep
                  user={user}
                  entries={entries}
                  scope={scope}
                  loaded={collectionLoaded}
                  onCapture={startIntake}
                  onReview={setDetail}
                />
                <section className="foundation-card">
                  <div className="foundation-top">
                    <span className="eyebrow">THE BIGGER PICTURE</span>
                    <Sprout size={23} />
                  </div>
                  <h2>
                    First, we put
                    <br />
                    down roots.
                  </h2>
                  <p>
                    Six kinds of information help us understand what’s really
                    happening in our stores.
                  </p>
                  <div className="coverage-grid">
                    {coverage.map((c) => (
                      <span
                        key={c}
                        className={
                          scoped.some((e) => e.category === c) ? "filled" : ""
                        }
                        title={categoryNames[c]}
                      />
                    ))}
                  </div>
                  <div className="coverage-label">
                    <strong>{collectionLoaded ? ready : "—"} of 6</strong>
                    <span>areas started</span>
                  </div>
                  <button
                    className="quiet-link"
                    onClick={() => navigate("collection")}
                  >
                    Explore the collection
                    <ArrowRight size={15} />
                  </button>
                  <PixelMark small />
                </section>
              </div>
              <section className="recent-section">
                <div className="section-heading">
                  <h2>From the stores</h2>
                  <button
                    className="quiet-link"
                    onClick={() => navigate("collection")}
                  >
                    View collection
                    <ArrowRight size={15} />
                  </button>
                </div>
                {scoped.length ? (
                  <div className="recent-list">
                    {scoped.slice(0, 3).map((e) => (
                      <button key={e.id} onClick={() => setDetail(e)}>
                        <span className={`store-dot ${e.store}`} />
                        <span>
                          <strong>{e.title}</strong>
                          <small>
                            {storeNames[e.store]} · {dateLabel(e.occurred_on)}
                          </small>
                        </span>
                        <Tag tone={e.status === "reviewed" ? "green" : ""}>
                          {e.status === "reviewed"
                            ? "Reviewed"
                            : "Needs review"}
                        </Tag>
                        <ChevronRight size={16} />
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="empty-strip">
                    <Leaf size={22} />
                    <p>
                      {collectionLoaded
                        ? "A fresh page for both stores."
                        : "Loading your collection…"}
                      <span>
                        {collectionLoaded
                          ? "Your first update will start the story here."
                          : "Checking what has been saved."}
                      </span>
                    </p>
                    <button
                      className="quiet-link"
                      onClick={() => setCapture("other")}
                    >
                      Add an update
                      <Plus size={16} />
                    </button>
                  </div>
                )}
              </section>
            </>
          )}

          {page === "collection" && (
            <>
              <div className="intro-row">
                <p>
                  A receipt, a report, a rough idea. Keep the original and the
                  context together.
                  <br />
                  <span className="muted">
                    {user.role === "staff"
                      ? "You can see your own updates for your assigned stores."
                      : "Review sources here before they become part of the business picture."}
                  </span>
                </p>
                <button
                  className="button primary"
                  onClick={() => setCapture("sales")}
                >
                  <Plus size={18} />
                  Add an update
                </button>
              </div>
              <div className="collection-areas">
                {coverage.map((c) => {
                  const Icon = catIcons[c];
                  const count = scoped.filter((e) => e.category === c).length;
                  return (
                    <button key={c} onClick={() => setCapture(c)}>
                      <Icon size={23} />
                      <strong>{categoryNames[c]}</strong>
                      <span>
                        {count
                          ? `${count} update${count === 1 ? "" : "s"} collected`
                          : "Ready for a first update"}
                        <Plus size={14} />
                      </span>
                    </button>
                  );
                })}
              </div>
              <div className="collection-tools">
                <label className="search">
                  <Search size={18} />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Find a report, note, or receipt…"
                    aria-label="Search collection"
                  />
                </label>
                <label>
                  <span className="visually-hidden">Review status</span>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                  >
                    <option value="all">All updates</option>
                    <option value="needs_review">Needs review</option>
                    <option value="reviewed">Reviewed</option>
                  </select>
                </label>
                <button
                  className="icon-button"
                  onClick={refresh}
                  aria-label="Refresh collection"
                >
                  <Compass size={18} />
                </button>
              </div>
              <div className="collection-list">
                {filtered.length ? (
                  filtered.map((e) => {
                    const Icon = catIcons[e.category];
                    return (
                      <button
                        className="entry-row"
                        key={e.id}
                        onClick={() => setDetail(e)}
                      >
                        <span className="entry-icon">
                          <Icon size={22} />
                        </span>
                        <span className="entry-title">
                          <strong>{e.title}</strong>
                          <small>
                            <span className={`store-dot ${e.store}`} />
                            {storeNames[e.store]} · {categoryNames[e.category]}{" "}
                            · {e.attachments.length}{" "}
                            {e.attachments.length === 1 ? "file" : "files"}
                          </small>
                        </span>
                        <span className="entry-date">
                          {dateLabel(e.occurred_on)}
                          <small>{e.author_name}</small>
                        </span>
                        <Tag tone={e.status === "reviewed" ? "green" : "amber"}>
                          {e.status === "reviewed"
                            ? "Reviewed"
                            : "Needs review"}
                        </Tag>
                        <ChevronRight size={17} />
                      </button>
                    );
                  })
                ) : (
                  <div className="empty-state">
                    <BookOpen size={32} />
                    <h2>
                      {query || status !== "all"
                        ? "No matching updates."
                        : collectionLoaded
                          ? "Every picture starts somewhere."
                          : "Opening the collection…"}
                    </h2>
                    <p>
                      {query || status !== "all"
                        ? "Try a different search or review status."
                        : "Add a sales report, a receipt, or a short note. We’ll keep it all together."}
                    </p>
                    <button
                      className="button secondary"
                      onClick={() => setCapture("sales")}
                    >
                      <Plus size={16} />
                      Add an update
                    </button>
                  </div>
                )}
              </div>
            </>
          )}

          {page === "stores" && (
            <>
              <p className="page-intro">
                Different strengths. A shared foundation. Store details below
                come from the founder’s brief and still need Moritz’s
                confirmation.
              </p>
              <div className="stores-grid">
                {(["sausage", "health"] as const)
                  .filter(
                    (s) =>
                      user.stores.includes(s) &&
                      (scope === "both" || scope === s),
                  )
                  .map((s) => (
                    <article className={`store-card ${s}`} key={s}>
                      <div className="store-card-top">
                        <span className="large-icon">
                          {s === "sausage" ? (
                            <StoreIcon size={29} />
                          ) : (
                            <Leaf size={29} />
                          )}
                        </span>
                        <Tag>Details to confirm</Tag>
                      </div>
                      <span className="eyebrow">
                        {s === "sausage"
                          ? "THE FREEZER & DELI"
                          : "THE EVERYDAY GOOD"}
                      </span>
                      <h2>{storeNames[s]}</h2>
                      <p>
                        {s === "sausage"
                          ? "Sausages, steaks, bacon, cold cuts, fish, frozen vegetables, and a few good extras."
                          : "Cacao, house-made kefir and yogurt, honey, nuts, supplements, goat milk, eggs, and more."}
                      </p>
                      <div className="store-facts">
                        <span>
                          <MapPin size={15} />
                          {s === "sausage"
                            ? "Panglao, Bohol"
                            : "Bil-isan area, Panglao · address to confirm"}
                        </span>
                        <span>
                          <BookOpen size={15} />
                          {
                            entries.filter(
                              (e) => e.store === s || e.store === "both",
                            ).length
                          }{" "}
                          updates collected
                        </span>
                        <span>
                          <LockKeyhole size={15} />
                          Loyverse connection pending
                        </span>
                      </div>
                      <button
                        className="button secondary"
                        onClick={() => {
                          setScope(s);
                          navigate("collection");
                        }}
                      >
                        Open store collection
                        <ArrowRight size={16} />
                      </button>
                      {s === "sausage" && (
                        <a
                          className="quiet-link"
                          href="https://www.thesausageguy.shop/panglao"
                          target="_blank"
                          rel="noreferrer"
                        >
                          Visit the customer website ↗
                        </a>
                      )}
                    </article>
                  ))}
              </div>
              <div className="future-store">
                <span className="large-icon">
                  <Sprout size={25} />
                </span>
                <div>
                  <h3>Room for what comes next.</h3>
                  <p>
                    A third store can join the same system. First, let’s
                    understand the two we have. Azure Sky and future locations
                    are awaiting details.
                  </p>
                </div>
                <button
                  className="quiet-link"
                  onClick={() => setCapture("other")}
                >
                  Add expansion notes
                  <Plus size={16} />
                </button>
              </div>
            </>
          )}

          {page === "roadmap" && (
            <Journey
              user={user}
              entries={entries}
              scope={scope}
              loaded={collectionLoaded}
              onCapture={startIntake}
              onReview={setDetail}
              phase={phaseOpen}
              onPhase={setPhaseOpen}
              onGuide={() => setGuide(true)}
              environment={system?.environment}
            />
          )}

          {page === "team" && (
            <>
              <div className="intro-row">
                <p>
                  Specialist roles with one shared source of truth.
                  <br />
                  <span className="muted">
                    {system?.ai === "ready"
                      ? "Text intake can run when you request it. The other departments are planned."
                      : "These are the planned departments. The text intake assistant is built; a model connection is still needed."}
                  </span>
                </p>
                <Tag tone="amber">
                  {system?.ai === "ready"
                    ? "Intake available on request"
                    : "Awaiting data & AI connection"}
                </Tag>
              </div>
              <div className="agent-grid">
                {[
                  {
                    icon: Compass,
                    name: "The coordinator",
                    label: "THE SHARED MEMORY",
                    desc: "Keeps the plan, open questions, and next actions together. Gives both owners the same context.",
                    needs: "Reviewed records + operating priorities",
                  },
                  {
                    icon: BookOpen,
                    name: "The intake assistant",
                    label: "MAKING SENSE OF INPUTS",
                    desc: "Prepares draft facts from notes and readable text exports when connected. Photo reading and audio transcription are still planned.",
                    needs: "Text samples + model, API key and provider budget",
                  },
                  {
                    icon: Wallet,
                    name: "The finance analyst",
                    label: "THE TRUE COST OF THINGS",
                    desc: "Will explain reconciled sales, costs, and margin. Calculations stay deterministic and traceable.",
                    needs: "Sales + costs + accountant-confirmed rules",
                  },
                  {
                    icon: Package,
                    name: "The stock keeper",
                    label: "THE RIGHT THINGS ON HAND",
                    desc: "Will flag low stock, expiry risk, and replenishment needs. Buying decisions stay with a person.",
                    needs: "Live inventory + product and supplier mappings",
                  },
                  {
                    icon: Users,
                    name: "The customer host",
                    label: "A HELPFUL FIRST HELLO",
                    desc: "Will answer from fresh, approved product data and collect order requests for staff to confirm.",
                    needs: "Verified availability + delivery workflow",
                  },
                  {
                    icon: Sprout,
                    name: "The growth partner",
                    label: "GOOD IDEAS, MEASURED",
                    desc: "Will suggest product and marketing experiments, with a clear hypothesis, budget, and result.",
                    needs: "Sales history + customer and competitor evidence",
                  },
                ].map((a) => (
                  <article className="agent-card" key={a.name}>
                    <div className="agent-top">
                      <span className="large-icon">
                        <a.icon size={24} />
                      </span>
                      <span className="planned-label">
                        <span />
                        {a.name === "The intake assistant"
                          ? system?.ai === "ready"
                            ? "TEXT READY"
                            : "TEXT BUILT"
                          : "PLANNED"}
                      </span>
                    </div>
                    <p className="eyebrow">{a.label}</p>
                    <h2>{a.name}</h2>
                    <p>{a.desc}</p>
                    <div className="agent-needs">
                      <span>STARTS WITH</span>
                      {a.needs}
                    </div>
                  </article>
                ))}
              </div>
              <div className="gentle-note">
                <ShieldCheck size={21} />
                <p>
                  Every recommendation will show its sources. Stock changes,
                  customer messages, ads, and purchases require the right human
                  authority.
                </p>
              </div>
            </>
          )}

          {page === "settings" && (
            <>
              <div className="settings-grid">
                <section className="settings-card">
                  <h2>Your workspace</h2>
                  <div className="setting-row">
                    <span>
                      Signed in as<small>{user.email}</small>
                    </span>
                    <Tag>{user.role}</Tag>
                  </div>
                  <div className="setting-row">
                    <span>
                      Appearance
                      <small>A little daylight, or the evening glow.</small>
                    </span>
                    <button
                      className="button secondary"
                      onClick={() => setLight(!light)}
                    >
                      {light ? <Moon size={17} /> : <Sun size={17} />}
                      {light ? "Night" : "Day"}
                    </button>
                  </div>
                  <div className="setting-row">
                    <span>
                      Time & currency
                      <small>Dates follow the stores’ local time.</small>
                    </span>
                    <span>Manila · PHP</span>
                  </div>
                  <div className="setting-row">
                    <span>
                      Getting started
                      <small>A short walkthrough for the team.</small>
                    </span>
                    <button
                      className="quiet-link"
                      onClick={() => setGuide(true)}
                    >
                      Open guide
                      <ArrowRight size={15} />
                    </button>
                  </div>
                </section>
                <section className="settings-card">
                  <h2>Connections</h2>
                  <div className="setting-row">
                    <span>
                      Private collection
                      <small>Records and originals saved on the server.</small>
                    </span>
                    <Tag tone={system ? "green" : ""}>
                      {system ? "Available" : "Checking"}
                    </Tag>
                  </div>
                  <div className="setting-row">
                    <span>
                      Loyverse
                      <small>Read-only sales and inventory connection.</small>
                    </span>
                    <Tag>Not connected</Tag>
                  </div>
                  <div className="setting-row">
                    <span>
                      AI providers
                      <small>Extraction and specialist workers.</small>
                    </span>
                    <Tag>
                      {system?.ai === "ready"
                        ? "Text assistant ready"
                        : "Not connected"}
                    </Tag>
                  </div>
                  <div className="setting-row">
                    <span>
                      Customer orders
                      <small>Availability, reservations, and delivery.</small>
                    </span>
                    <Tag>Planned</Tag>
                  </div>
                </section>
              </div>
              {user.role === "owner" && (
                <section className="settings-card owner-settings">
                  <h2>For the technical owner</h2>
                  <p className="muted">
                    Account administration, deployment, and provider credentials
                    are managed on the server. This keeps those controls out of
                    everyday store work.
                  </p>
                  <div className="owner-actions">
                    <a className="button secondary" href="/api/export" download>
                      <ArrowDownToLine size={17} />
                      Export collection index
                    </a>
                    <button
                      className="button secondary"
                      onClick={async () => {
                        try {
                          setAudit(await api("/audit"));
                        } catch (e) {
                          setError((e as Error).message);
                        }
                      }}
                    >
                      <ShieldCheck size={17} />
                      View recent activity
                    </button>
                  </div>
                  <p className="fine-print">
                    The JSON index includes source metadata and notes. Original
                    attachments are downloaded separately; full backups include
                    both.
                  </p>
                  {audit && (
                    <div className="audit-list">
                      {audit.map((a) => (
                        <div key={a.id}>
                          <span>{a.action}</span>
                          <span>{a.actor_name}</span>
                          <small>{dateLabel(a.created_at)}</small>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              )}
            </>
          )}
          <footer className="page-footer">
            <span>
              <PixelMark small />A little more clarity. Every day.
            </span>
            <span>
              SAUSAGE HEALTH <i /> FOUNDATION 0.1
            </span>
          </footer>
        </main>
      </div>
      {capture && (
        <Capture
          user={user}
          initial={capture}
          initialStore={captureStore ?? scope}
          onClose={closeCapture}
          onSaved={saved}
        />
      )}
      {detail && (
        <EntryDetail
          entry={detail}
          user={user}
          aiConnected={system?.ai === "ready"}
          onClose={() => setDetail(null)}
          onReviewed={reviewed}
        />
      )}
      {guide && (
        <Guide
          onClose={() => setGuide(false)}
          onStart={() => {
            setGuide(false);
            setCapture("sales");
          }}
        />
      )}
      {notice && (
        <div className="toast" role="status">
          <Check size={19} />
          {notice}
          <button
            className="icon-button"
            aria-label="Dismiss confirmation"
            onClick={() => setNotice("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
