"use client";

import { type SubmitEvent, useEffect, useRef, useState } from "react";
import * as c from "./constant"
  
type Template = "SaaS" | "Developer tool" | "AI product";
type View = "form" | "loading" | "results" | "capacity";

const templates: { name: Template; description: string }[] = [
  { name: "SaaS", description: "Clear & ownable" },
  { name: "Developer tool", description: "Technical & sharp" },
  { name: "AI product", description: "Modern & intelligent" },
];

const nameParts: Record<Template, string[]> = {
  SaaS: ["Flow", "Pilot", "Layer", "Base", "Nest", "Loop", "Stack", "Path"],
  "Developer tool": ["Kit", "Forge", "Stack", "Node", "Ops", "Core", "Shell", "Sync"],
  "AI product": ["Mind", "Neural", "Spark", "Sage", "Nova", "Sense", "Lume", "Aura"],
};

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4" fill="none">
      <path
        d="M3.5 8h9M9 4.5 12.5 8 9 11.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CopyIcon({ done }: { done: boolean }) {
  return done ? (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4" fill="none">
      <path
        d="m3.5 8.5 3 3 6-7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  ) : (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4" fill="none">
      <rect x="5.5" y="5.5" width="7" height="7" rx="1.5" stroke="currentColor" />
      <path
        d="M10.5 5.5V5A1.5 1.5 0 0 0 9 3.5H5A1.5 1.5 0 0 0 3.5 5v4A1.5 1.5 0 0 0 5 10.5h.5"
        stroke="currentColor"
      />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 18 18" className="size-4.5" fill="none">
      <path
        d="M9 1.75c.45 3.86 3.39 6.8 7.25 7.25C12.39 9.45 9.45 12.39 9 16.25 8.55 12.39 5.61 9.45 1.75 9 5.61 8.55 8.55 5.61 9 1.75Z"
        fill="currentColor"
      />
    </svg>
  );
}

function Logo() {
  return (
    <div className="flex items-center gap-2.5 text-sm font-semibold tracking-[-0.02em] text-white">
      <span className="grid size-6 place-items-center rounded-md bg-[#c6ff3d] text-[#0d0d0d]">
        <span className="font-mono text-[11px] font-bold">W/</span>
      </span>
      {c.APP_NAME}
    </div>
  );
}

function generateNames(input: string, template: Template, count: number) {
  const clean = input
    .trim()
    .split(/\s+/)
    .filter((word) => word.length > 2)
    .map((word) => word.replace(/[^a-zA-Z]/g, ""))
    .filter(Boolean);
  const seed = clean[0] || "Bright";
  const short = seed.slice(0, Math.max(3, Math.min(seed.length, 6)));
  const parts = nameParts[template];
  const variants = [
    `${short}${parts[0]}`,
    `${short.slice(0, 4)}${parts[1]}`,
    `${parts[2]}${short}`,
    `${short.slice(0, 3)}${parts[3].toLowerCase()}`,
    `${short}${parts[4]}`,
    `${parts[5]}${short.slice(0, 4)}`,
    `${short.slice(0, 5)}${parts[6]}`,
    `${parts[7]}${short}`,
  ];
  return variants
    .slice(0, count)
    .map((name) => name.charAt(0).toUpperCase() + name.slice(1).toLowerCase());
}

export function NameGenerator() {
  const [template, setTemplate] = useState<Template>("SaaS");
  const [count, setCount] = useState(5);
  const [prompt, setPrompt] = useState("");
  const [view, setView] = useState<View>("form");
  const [names, setNames] = useState<string[]>([]);
  const [copied, setCopied] = useState<string | null>(null);
  const [error, setError] = useState("");
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (view === "results") resultsRef.current?.focus();
  }, [view]);

  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    if (!prompt.trim()) {
      setError("Add a few words about your product first.");
      return;
    }
    setError("");
    setView("loading");
    window.setTimeout(() => {
      if (/\b(capacity|unavailable)\b/i.test(prompt)) {
        setView("capacity");
      } else {
        setNames(generateNames(prompt, template, count));
        setView("results");
      }
    }, 1250);
  };

  const copyName = async (name: string) => {
    try {
      await navigator.clipboard.writeText(name);
      setCopied(name);
      window.setTimeout(() => setCopied(null), 1600);
    } catch {
      setCopied(null);
    }
  };

  const reset = () => {
    setView("form");
    setNames([]);
  };

  return (
    <div className="min-h-screen bg-[#0d0d0d] text-[#ededed]">
      <header className="border-b border-white/[0.07]">
        <div className="mx-auto flex h-16 max-w-280 items-center justify-between px-5 sm:px-8">
          <Logo />
          <div className="flex items-center gap-2 font-mono text-[11px] text-[#898989]">
            <span className="size-1.5 rounded-full bg-[#c6ff3d] shadow-[0_0_0_3px_rgba(198,255,61,0.08)]" />
            All systems operational
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-195 px-5 pb-20 pt-16 sm:px-8 sm:pt-24">
        {view === "capacity" ? (
          <section
            className="mx-auto flex max-w-140 flex-col items-center py-12 text-center"
            aria-labelledby="capacity-title"
          >
            <div className="mb-7 grid size-12 place-items-center rounded-xl border border-white/8 bg-[#151515] text-[#c6ff3d]">
              <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5" fill="none">
                <path
                  d="M12 8v4m0 4h.01M10.29 3.86 2.82 17a2 2 0 0 0 1.74 3h14.88a2 2 0 0 0 1.74-3L13.71 3.86a2 2 0 0 0-3.42 0Z"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <p className="mb-4 font-mono text-[11px] uppercase tracking-[0.18em] text-[#c6ff3d]">
              At capacity
            </p>
            <h1
              id="capacity-title"
              className="text-balance text-3xl font-semibold tracking-[-0.045em] text-white sm:text-4xl"
            >
              Too many great ideas at once.
            </h1>
            <p className="mt-4 max-w-110 text-pretty text-[15px] leading-7 text-[#8f8f8f]">
              Our naming engine is taking a quick breather. Your brief is safe—try again in a
              moment.
            </p>
            <button onClick={reset} className="primary-button mt-8">
              Try again <ArrowIcon />
            </button>
            <span className="mt-5 font-mono text-[10px] uppercase tracking-[0.12em] text-[#595959]">
              Error / capacity_reached
            </span>
          </section>
        ) : (
          <>
            <section className="mb-12 sm:mb-14">
              <div className="mb-6 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-[#c6ff3d]">
                <span className="h-px w-5 bg-[#c6ff3d]" />
                AI naming engine
              </div>
              <h1 className="max-w-170 text-balance text-[42px] font-semibold leading-[1.04] tracking-[-0.055em] text-white sm:text-[62px]">
                A better name is the beginning.
              </h1>
              <p className="mt-5 max-w-137.5 text-pretty text-[15px] leading-7 text-[#929292] sm:text-base">
                Distinctive software names generated from your product’s purpose, audience, and
                point of view.
              </p>
            </section>

            <form
              onSubmit={submit}
              className="rounded-2xl border border-white/9 bg-[#121212] p-4 shadow-[0_24px_80px_rgba(0,0,0,0.28)] sm:p-6"
            >
              <fieldset>
                <legend className="field-label">Choose a direction</legend>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {templates.map((item) => {
                    const selected = template === item.name;
                    return (
                      <button
                        type="button"
                        key={item.name}
                        aria-pressed={selected}
                        onClick={() => setTemplate(item.name)}
                        className={`template-button ${selected ? "template-button--selected" : ""}`}
                      >
                        <span className="text-[13px] font-medium text-[#e8e8e8]">{item.name}</span>
                        <span className="mt-1 font-mono text-[10px] text-[#6f6f6f]">
                          {item.description}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </fieldset>

              <div className="mt-6">
                <label htmlFor="brief" className="field-label">
                  Describe your product
                </label>
                <textarea
                  id="brief"
                  rows={4}
                  value={prompt}
                  aria-describedby={error ? "brief-error" : "brief-hint"}
                  aria-invalid={Boolean(error)}
                  onChange={(event) => {
                    setPrompt(event.target.value);
                    if (error) setError("");
                  }}
                  placeholder="e.g. An AI code review tool for fast-moving engineering teams..."
                  className="w-full resize-none rounded-xl border border-white/9 bg-[#0e0e0e] px-4 py-3.5 text-[14px] leading-6 text-white outline-none transition placeholder:text-[#555] focus:border-[#c6ff3d]/60 focus:ring-2 focus:ring-[#c6ff3d]/10"
                />
                <div className="mt-2 min-h-4">
                  {error ? (
                    <p id="brief-error" role="alert" className="text-xs text-[#ff8e7f]">
                      {error}
                    </p>
                  ) : (
                    <p id="brief-hint" className="font-mono text-[10px] text-[#5f5f5f]">
                      Be specific for more distinctive results.
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-4 flex flex-col gap-5 border-t border-white/[0.07] pt-5 sm:flex-row sm:items-end sm:justify-between">
                <fieldset>
                  <legend className="field-label mb-2!">Number of names</legend>
                  <div className="inline-flex rounded-lg border border-white/8 bg-[#0d0d0d] p-1">
                    {[3, 5, 8].map((number) => (
                      <button
                        type="button"
                        key={number}
                        aria-pressed={count === number}
                        onClick={() => setCount(number)}
                        className={`count-button ${
                          count === number ? "count-button--selected" : ""
                        }`}
                      >
                        {number}
                      </button>
                    ))}
                  </div>
                </fieldset>
                <button
                  type="submit"
                  disabled={view === "loading"}
                  className="primary-button w-full sm:w-auto"
                >
                  {view === "loading" ? (
                    <>
                      <span className="loading-spinner" />
                      Generating
                    </>
                  ) : (
                    <>
                      <SparkIcon />
                      Generate names
                      <ArrowIcon />
                    </>
                  )}
                </button>
              </div>
            </form>

            {view === "loading" && (
              <section className="mt-10" aria-live="polite" aria-label="Generating names">
                <div className="mb-4 flex items-center justify-between">
                  <p className="text-sm font-medium text-[#bdbdbd]">Exploring possibilities</p>
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[#666]">
                    Thinking
                  </span>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  {["first", "second", "third", "fourth"]
                    .slice(0, Math.min(count, 4))
                    .map((skeleton) => (
                      <div
                        key={skeleton}
                        className="h-18 animate-pulse rounded-xl border border-white/6 bg-[#121212]"
                      />
                    ))}
                </div>
              </section>
            )}

            {view === "results" && (
              <section
                ref={resultsRef}
                tabIndex={-1}
                className="mt-10 outline-none"
                aria-labelledby="results-title"
              >
                <div className="mb-4 flex items-end justify-between">
                  <div>
                    <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.15em] text-[#c6ff3d]">
                      Freshly generated
                    </p>
                    <h2
                      id="results-title"
                      className="text-lg font-semibold tracking-tight text-white"
                    >
                      Names worth building on
                    </h2>
                  </div>
                  <button
                    type="button"
                    onClick={reset}
                    className="text-xs text-[#7e7e7e] transition hover:text-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#c6ff3d]"
                  >
                    Start over
                  </button>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  {names.map((name, index) => (
                    <article
                      key={name}
                      className="group flex min-h-19 items-center justify-between rounded-xl border border-white/8 bg-[#121212] px-4 transition hover:border-white/16 hover:bg-[#151515]"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-[10px] text-[#515151]">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <h3 className="text-[17px] font-medium tracking-tight text-[#f0f0f0]">
                          {name}
                        </h3>
                      </div>
                      <button
                        type="button"
                        onClick={() => copyName(name)}
                        aria-label={`Copy ${name}`}
                        className={`copy-button ${copied === name ? "copy-button--done" : ""}`}
                      >
                        <CopyIcon done={copied === name} />
                        <span className="hidden text-[11px] sm:inline">
                          {copied === name ? "Copied" : "Copy"}
                        </span>
                      </button>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>

      <footer className="border-t border-white/6">
        <div className="mx-auto flex max-w-280 flex-col gap-2 px-5 py-6 font-mono text-[10px] uppercase tracking-widest text-[#555] sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>No sign-up. Just names.</span>
          <span>Built for people building things.</span>
        </div>
      </footer>
    </div>
  );
}
