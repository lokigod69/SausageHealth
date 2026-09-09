import {
  ArrowRight,
  Check,
  Compass,
  Flag,
  Leaf,
  LockKeyhole,
  MapPin,
  Receipt,
  ShieldCheck,
} from "lucide-react";
import {
  storeNames,
  type Category,
  type Entry,
  type Store,
  type User,
} from "./api";
import { journeyPhases, starterTasks } from "./readiness";

type IntakeProps = {
  user: User;
  entries: Entry[];
  scope: Store;
  loaded: boolean;
  onCapture: (category: Category, store: Store) => void;
  onReview: (entry: Entry) => void;
};

export function NextStep({
  user,
  entries,
  scope,
  loaded,
  onCapture,
  onReview,
}: IntakeProps) {
  const tasks = starterTasks(entries, user, scope);
  const pending = tasks.find((t) => t.state === "submitted");
  const next = tasks.find((t) => t.state === "missing");
  const reviewNext =
    user.role !== "staff" &&
    pending &&
    !tasks.some((t) => t.category === "sales" && t.state === "missing");
  const action = reviewNext ? pending : next;
  return (
    <section className="next-compass" aria-labelledby="next-step-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">INITIAL RECORDS</span>
          <h2 id="next-step-title">Next update</h2>
        </div>
        <Compass size={26} aria-hidden="true" />
      </div>
      {!loaded ? (
        <p className="muted small-text">Waiting for the collection to load.</p>
      ) : (
        <>
          <div className="next-action">
            <span className="eyebrow">
              {action ? storeNames[action.store] : "COLLECTION"}
            </span>
            <h3>
              {reviewNext
                ? "Review a submitted record"
                : (next?.title ?? "Initial records submitted")}
            </h3>
            <p>
              {reviewNext
                ? "Check the store, date and original file. Note any missing or unclear information."
                : (next?.detail ??
                  (user.role === "staff"
                    ? "Your operator reviews the sources. Keep adding closing reports and receipts as they arrive."
                    : "Collect the last 30 days of records. Check missing dates and duplicates."))}
            </p>
            <button
              className="button primary"
              onClick={() =>
                reviewNext
                  ? onReview(pending.entry!)
                  : onCapture(
                      next?.category ?? "sales",
                      next?.store ?? tasks[0]?.store ?? user.stores[0],
                    )
              }
            >
              {reviewNext
                ? "Review this source"
                : next
                  ? "Add this source"
                  : "Add another update"}
              <ArrowRight size={16} />
            </button>
          </div>
          <div className="store-signals" aria-label="First daily sales sources">
            {tasks
              .filter((t) => t.category === "sales")
              .map((t) => (
                <div key={t.store}>
                  {t.store === "health" ? (
                    <Leaf size={17} />
                  ) : (
                    <Receipt size={17} />
                  )}
                  <span>
                    {storeNames[t.store]}
                    <small>
                      {t.state === "missing"
                        ? "First sales source needed"
                        : t.state === "submitted"
                          ? "First source awaits review"
                          : "First source reviewed"}
                    </small>
                  </span>
                  {t.state === "reviewed" && <Check size={16} />}
                </div>
              ))}
          </div>
          <p className="fine-print">
            {user.role === "staff"
              ? "Based on your own submissions only."
              : "Based on records you can access."}{" "}
            Shows first records only, not complete sales coverage.
          </p>
        </>
      )}
    </section>
  );
}

export function Journey({
  user,
  entries,
  scope,
  loaded,
  onCapture,
  onReview,
  phase,
  onPhase,
  environment,
}: IntakeProps & {
  phase: number;
  onPhase: (phase: number) => void;
  environment?: string;
}) {
  const selected = journeyPhases[phase];
  return (
    <div className="journey-world">
      <section className="journey-intro">
        <div>
          <span className="eyebrow">
            <Compass size={15} /> CURRENT PHASE / COLLECT
          </span>
          <h2>
            From records
            <br />
            <em>to decisions.</em>
          </h2>
          <p>
            Collect records, reconcile the numbers, test improvements, then
            expand.
          </p>
          {user.role === "owner" && (
            <span className="tag amber">
              {environment
                ? environment === "production"
                  ? "Production mode · verification required"
                  : "Local preview"
                : "Checking workspace mode…"}
            </span>
          )}
        </div>
        <div className="journey-island" aria-hidden="true">
          <img src="/art/island.png" alt="" />
        </div>
      </section>
      <nav className="route-stops" aria-label="Explore the roadmap phases">
        {journeyPhases.map((p, i) => (
          <button
            key={p.name}
            className={phase === i ? "selected" : ""}
            aria-pressed={phase === i}
            onClick={() => onPhase(i)}
          >
            <span className="route-marker">
              {i === 0 ? <Flag size={19} /> : `0${i + 1}`}
            </span>
            <span className="route-label">
              <strong>{p.name}</strong>
              <small>{i === 0 ? "CURRENT PHASE" : "PLANNED"}</small>
            </span>
          </button>
        ))}
      </nav>
      <section className="route-detail" aria-labelledby="phase-title">
        <div className="route-story">
          <span className="eyebrow">
            <MapPin size={14} /> {selected.place.toUpperCase()}
          </span>
          <h2 id="phase-title">{selected.subtitle}</h2>
          <p>{selected.description}</p>
          <dl>
            <dt>Responsibility</dt>
            <dd>{selected.owner}</dd>
            <dt>Outcome</dt>
            <dd>{selected.outcome}</dd>
          </dl>
          <div className="route-caution">
            <ShieldCheck size={20} />
            <div>
              <strong>{selected.risk}</strong>
              <p>{selected.response}</p>
            </div>
          </div>
        </div>
        <div className="route-gates">
          <span className="eyebrow">REQUIREMENTS</span>
          <ol>
            {selected.gates.map((gate, i) => (
              <li key={gate}>
                <span>{String(i + 1).padStart(2, "0")}</span>
                <p>{gate}</p>
              </li>
            ))}
          </ol>
          <p className="fine-print">
            Planned requirements. Phase completion needs owner review.
          </p>
        </div>
      </section>
      {phase === 0 && (
        <div className="journey-practical">
          <NextStep
            {...{ user, entries, scope, loaded, onCapture, onReview }}
          />
        </div>
      )}
      {user.role === "owner" && (
        <details className="launch-checklist">
          <summary>
            <LockKeyhole size={18} />
            <span>
              Deployment checks
              <small>Verify on the selected server</small>
            </span>
          </summary>
          <div>
            <p>
              Configure the server and individual accounts for
              ops.thesausageguy.shop.
            </p>
            <ul>
              <li>
                Build the container and verify HTTPS, login and account/store
                isolation.
              </li>
              <li>
                Save a photo from Moritz's real phone; find and review it on
                another device, including after a server restart.
              </li>
              <li>
                Restore a backup with its originals in a separate location. Set
                off-host backup, disk monitoring and a person to respond to
                failures.
              </li>
              <li>
                Test a failed upload, an expired login and a large file. Explain
                what “saved” means before real data arrives.
              </li>
            </ul>
            <p>
              AI can follow manual intake. It needs a model, API key, provider
              budget and representative evaluation; photo reading and audio
              transcription remain planned.
            </p>
          </div>
        </details>
      )}
    </div>
  );
}
