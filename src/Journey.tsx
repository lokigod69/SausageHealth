import {
  ArrowRight,
  BookOpen,
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
          <span className="eyebrow">YOUR NEXT SMALL STEP</span>
          <h2 id="next-step-title">A little clarity, today.</h2>
        </div>
        <Compass size={26} aria-hidden="true" />
      </div>
      {!loaded ? (
        <p className="muted small-text">
          Load the collection to find your next step. No progress is assumed.
        </p>
      ) : (
        <>
          <div className="next-action">
            <span className="eyebrow">
              {action ? storeNames[action.store] : "KEEP THE ROUTINE GOING"}
            </span>
            <h3>
              {reviewNext
                ? "Check a source that came in"
                : (next?.title ?? "Your first sources are in.")}
            </h3>
            <p>
              {reviewNext
                ? "Check the store, date and original. Add a note for anything unclear. This is source review, not a financial sign-off."
                : (next?.detail ??
                  (user.role === "staff"
                    ? "Your operator reviews the sources. Keep adding closing reports and receipts as they arrive."
                    : "Keep collecting the recent 30-day picture. Check missing dates and duplicates before calculating anything."))}
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
            A first source is a starting point, not a complete sales history.
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
  onGuide,
  environment,
}: IntakeProps & {
  phase: number;
  onPhase: (phase: number) => void;
  onGuide: () => void;
  environment?: string;
}) {
  const selected = journeyPhases[phase];
  return (
    <div className="journey-world">
      <section className="journey-intro">
        <div>
          <span className="eyebrow">
            <Compass size={15} /> THE FIELD GUIDE / CHAPTER 01
          </span>
          <h2>
            A clear route.
            <br />
            <em>One useful step at a time.</em>
          </h2>
          <p>
            Collect. Review. Learn. We can improve a routine today while
            building the evidence for bigger decisions.
          </p>
          <span className="tag amber">
            {environment
              ? environment === "production"
                ? "Server mode · launch checks required"
                : "Local preview · shared access comes next"
              : "Checking workspace mode…"}
          </span>
        </div>
        <div className="journey-island" aria-hidden="true">
          <img src="/art/island.png" alt="" />
          <span>THE ISLAND IS OUR VISION. THE RECORDS SHOW OUR PROGRESS.</span>
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
              <small>{i === 0 ? "CURRENT CHAPTER" : "PLANNED"}</small>
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
            <dt>Who carries this forward</dt>
            <dd>{selected.owner}</dd>
            <dt>What we're working toward</dt>
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
          <span className="eyebrow">BEFORE WE MOVE FORWARD</span>
          <ol>
            {selected.gates.map((gate, i) => (
              <li key={gate}>
                <span>{String(i + 1).padStart(2, "0")}</span>
                <p>{gate}</p>
              </li>
            ))}
          </ol>
          <p className="fine-print">
            These are acceptance requirements, not completed tasks. The owners
            confirm each phase with evidence; uploads do not unlock phases
            automatically.
          </p>
        </div>
      </section>
      {phase === 0 && (
        <div className="journey-practical">
          <NextStep
            {...{ user, entries, scope, loaded, onCapture, onReview }}
          />
          <section className="moritz-note">
            <span className="eyebrow">
              <BookOpen size={16} /> THE FIRST FIVE MINUTES
            </span>
            <h2>Start where you are, Moritz.</h2>
            <p>
              No big preparation needed. When your account is ready, bring
              yesterday's sales message from each store and one receipt.
            </p>
            <ol>
              <li>Choose the store and the kind of information.</li>
              <li>Add a note or file and the date it covers.</li>
              <li>Save, wait for confirmation, then find it in Collection.</li>
            </ol>
            <button className="button secondary" onClick={onGuide}>
              Open the quick guide
              <ArrowRight size={16} />
            </button>
            <p className="fine-print">
              Staff see only their own submissions in assigned stores. Moritz
              reviews the operational picture.
            </p>
          </section>
        </div>
      )}
      <details className="launch-checklist">
        <summary>
          <LockKeyhole size={18} />
          <span>
            Before sharing the workspace with the team
            <small>Technical owner · confirm on the selected host</small>
          </span>
        </summary>
        <div>
          <p>
            Choose the domain and server, then create separate accounts. A
            domain suggestion or a production setting does not certify a launch.
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
    </div>
  );
}
