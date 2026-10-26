"use client";

import { useEffect, useRef, useState } from "react";
import {
  getMetrics,
  incrementMetric,
  incrementMetricBy,
  checkLlmStatus,
} from "./actions/metrics";
import * as c from "@/lib/constant";
import { STRATEGIES } from "@/lib/templates";

type View = "form" | "loading" | "results" | "capacity";
type LoadingStage = "idle" | "keywords" | "names";

const STRATEGY_ITEMS: { name: string; label: string; desc: string }[] = [
  ...STRATEGIES.map((s) => ({
    name: s.STRATEGY_NAME,
    label:
      s.STRATEGY_NAME === "forge_mint"
        ? "Forge & Mint"
        : s.STRATEGY_NAME.split("_")
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(" "),
    desc:
      s.STRATEGY_NAME === "balanced"
        ? "Mixed naming approaches with batch diversity"
        : s.STRATEGY_NAME === "semantic"
          ? "Core product purpose & benefit driven"
          : s.STRATEGY_NAME === "portmanteau"
            ? "Blended concepts with recognizable roots"
            : s.STRATEGY_NAME === "metaphor"
              ? "Evocative imagery and symbolic identity"
              : s.STRATEGY_NAME === "minimalist"
                ? "Short, clean, high recall names"
                : s.STRATEGY_NAME === "linguistic_twist"
                  ? "Compact spellings and subtle phonetic shifts"
                  : s.STRATEGY_NAME === "developer_syntax"
                    ? "Code, syntax, and engineering culture"
                    : s.STRATEGY_NAME === "abstract_evocative"
                      ? "Invented names with modern startup feel"
                      : s.STRATEGY_NAME === "forge_mint"
                        ? "Compound developer-tool names"
                        : "Legendary figures and ancient folklore",
  })),
  { name: "all", label: "All Strategies", desc: "Run all strategies" },
];

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

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      className={`size-4 text-[#777] transition-transform duration-200 ${open ? "rotate-180 text-white" : ""}`}
      fill="none"
    >
      <path
        d="M4 6l4 4 4-4"
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

function generateNames(input: string, strategy: string, count: number): string[] {
  // shortcut: heuristic generator until API route is plugged in, upgrade when backend tunnel is configured
  const clean = input
    .trim()
    .split(/\s+/)
    .filter((word) => word.length > 2)
    .map((word) => word.replace(/[^a-zA-Z]/g, ""))
    .filter(Boolean);
  const seed = clean[0] || "Forge";
  const short = seed.slice(0, Math.max(3, Math.min(seed.length, 6)));

  const parts = [
    "Flow",
    "Pilot",
    "Layer",
    "Base",
    "Nest",
    "Loop",
    "Stack",
    "Sync",
    "Kit",
    "Node",
    "Core",
    "Ops",
  ];
  const list = parts.map((p, i) => (i % 2 === 0 ? `${short}${p}` : `${p}${short}`));

  if (strategy === "all") {
    return list.slice(0, Math.min(20, Math.max(count, STRATEGIES.length)));
  }
  return list.slice(0, Math.min(20, count));
}

export function NameGenerator() {
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [isOpen, setIsOpen] = useState(false);
  const [count, setCount] = useState(5);
  const [prompt, setPrompt] = useState("");
  const [keywordsInput, setKeywordsInput] = useState("");
  const [loadingStage, setLoadingStage] = useState<LoadingStage>("idle");
  const [view, setView] = useState<View>("form");
  const [names, setNames] = useState<string[]>([]);
  const [copied, setCopied] = useState<string | null>(null);
  const [visitorCount, setVisitorCount] = useState<number>(0);
  const [totalGenerated, setTotalGenerated] = useState<number>(0);
  const [llmStatus, setLlmStatus] = useState<"checking" | "online" | "offline">("checking");
  const [error, setError] = useState("");
  const resultsRef = useRef<HTMLDivElement>(null);
  const selectRef = useRef<HTMLDivElement>(null);

  const verifyLlm = () => {
    setLlmStatus("checking");
    checkLlmStatus().then((res) => {
      setLlmStatus(res.online ? "online" : "offline");
    });
  };

  useEffect(() => {
    // Check engine status once on page load
    verifyLlm();

    // Fetch initial metrics and increment visitors once per session
    getMetrics("wsict").then((data) => {
      setVisitorCount(data.visitors || 0);
      setTotalGenerated(data.total_generated_names || 0);
    });

    const hasVisited =
      typeof window !== "undefined" ? sessionStorage.getItem("wsict_visited") : null;
    if (!hasVisited) {
      if (typeof window !== "undefined") sessionStorage.setItem("wsict_visited", "true");
      incrementMetric("wsict", "visitors").then(() => {
        setVisitorCount((prev) => (prev ? prev + 1 : 1));
      });
    }
  }, []);

  useEffect(() => {
    if (view === "results") resultsRef.current?.focus();
  }, [view]);

  // Keyboard shortcut: 'S' or Alt+S toggles select menu, arrows / digits navigate, Esc closes
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isInput = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA");

      if ((e.key === "s" || e.key === "S") && !e.metaKey && !e.ctrlKey && !isInput) {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.altKey && (e.key === "s" || e.key === "S")) {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (isOpen) {
        if (e.key === "Escape") {
          setIsOpen(false);
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          setSelectedIndex((prev) => (prev + 1) % STRATEGY_ITEMS.length);
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setSelectedIndex((prev) => (prev - 1 + STRATEGY_ITEMS.length) % STRATEGY_ITEMS.length);
        } else if (e.key === "Enter") {
          e.preventDefault();
          setIsOpen(false);
        } else if (/^[0-9]$/.test(e.key)) {
          const num = Number(e.key);
          if (num < STRATEGY_ITEMS.length) {
            e.preventDefault();
            setSelectedIndex(num);
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Click outside to close select menu
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!prompt.trim()) {
      setError("Add a few words about your product first.");
      return;
    }

    let activeKeywords: string[] = [];
    const trimmedKw = keywordsInput.trim();
    if (trimmedKw) {
      const parts = trimmedKw
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean);
      if (parts.length === 0) {
        setError("Please enter valid comma-separated keywords or leave the field blank.");
        return;
      }
      activeKeywords = parts;
    }

    setError("");
    setView("loading");

    try {
      // Step 1: If user didn't enter keywords, generate them via LLM API
      if (activeKeywords.length === 0) {
        setLoadingStage("keywords");
        try {
          const kwRes = await fetch("/api/keywords", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ description: prompt }),
          });

          if (!kwRes.ok) {
            const errData = await kwRes.json().catch(() => ({}));
            throw new Error(errData.error || "Keyword generation failed");
          }

          const kwData = await kwRes.json();
          if (Array.isArray(kwData.keywords) && kwData.keywords.length > 0) {
            activeKeywords = kwData.keywords;
            setKeywordsInput(activeKeywords.join(", "));
          }
        } catch (kwErr) {
          // shortcut: heuristic keyword extraction when local LLM server is unreachable
          console.warn("Auto keyword extraction failed, using heuristic fallback:", kwErr);
          activeKeywords = prompt
            .toLowerCase()
            .replace(/[^a-z0-9\s]/g, "")
            .split(/\s+/)
            .filter((w) => w.length > 3)
            .slice(0, 8);
        }
      }

      setLoadingStage("names");
      const strat = STRATEGY_ITEMS[selectedIndex]?.name || "balanced";
      const safeCount = Math.max(1, Math.min(20, count));

      try {
        const genRes = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            description: prompt,
            keywords: activeKeywords,
            count: safeCount,
            strategy: strat,
          }),
        });

        if (!genRes.ok) {
          const errData = await genRes.json().catch(() => ({}));
          throw new Error(errData.error || "Name generation failed");
        }

        const genData = await genRes.json();
        const generatedList =
          Array.isArray(genData.names) && genData.names.length > 0
            ? genData.names.slice(0, 20)
            : generateNames(prompt, strat, safeCount);

        setNames(generatedList);
        setTotalGenerated((prev) => prev + generatedList.length);
        incrementMetricBy("wsict", "total_generated_names", generatedList.length);
        setView("results");
      } catch (genErr) {
        // shortcut: heuristic name fallback when local LLM server is unreachable
        console.warn("LLM name generation failed, using heuristic fallback:", genErr);
        const fallbackList = generateNames(prompt, strat, safeCount);
        setNames(fallbackList);
        setTotalGenerated((prev) => prev + fallbackList.length);
        incrementMetricBy("wsict", "total_generated_names", fallbackList.length);
        setView("results");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setView("form");
    } finally {
      setLoadingStage("idle");
    }
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
    setLoadingStage("idle");
  };

  return (
    <div className="min-h-screen bg-[#0d0d0d] text-[#ededed]">
      <header className="border-b border-white/[0.07]">
        <div className="mx-auto flex h-16 max-w-280 items-center justify-between px-5 sm:px-8">
          <Logo />
          <button
            type="button"
            onClick={verifyLlm}
            title="Click to recheck engine status"
            className="flex items-center gap-2 font-mono text-[11px] text-[#898989] transition hover:text-[#ddd]"
          >
            {llmStatus === "checking" ? (
              <>
                <span className="size-1.5 rounded-full bg-amber-400 animate-pulse shadow-[0_0_0_3px_rgba(251,191,36,0.15)]" />
                Checking status...
              </>
            ) : llmStatus === "online" ? (
              <>
                <span className="size-1.5 rounded-full bg-[#c6ff3d] shadow-[0_0_0_3px_rgba(198,255,61,0.12)]" />
                Online
              </>
            ) : (
              <>
                <span className="size-1.5 rounded-full bg-[#ff5252] shadow-[0_0_0_3px_rgba(255,82,82,0.18)]" />
                Offline
              </>
            )}
          </button>
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
                Distinctive names generated from your product’s purpose, audience, and point of
                view.{" "}
                <span className="inline-flex items-center gap-1.5 rounded-md border border-[#c6ff3d]/25 bg-[#c6ff3d]/10 px-2.5 py-0.5 font-mono text-[13px] font-bold italic tracking-tight text-[#c6ff3d] shadow-[0_0_14px_rgba(198,255,61,0.12)]">
                  <span className="size-1.5 rounded-full bg-[#c6ff3d] shadow-[0_0_6px_#c6ff3d]" />
                  No sign-up. Just names.
                </span>
              </p>
            </section>

            <section
              aria-label="Tool statistics"
              className="mb-8 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/8 bg-[#121212] px-4 py-3 sm:px-5"
            >
              <div className="flex items-center gap-3">
                <span className="grid size-7 place-items-center rounded-lg bg-[#c6ff3d]/10 text-[#c6ff3d]">
                  <SparkIcon />
                </span>
                <span className="text-[13px] text-[#8e8e8e]">
                  Total names generated by this tool:{" "}
                  <strong className="font-mono text-[14px] font-semibold text-white">
                    {totalGenerated.toLocaleString()}
                  </strong>
                </span>
              </div>
              <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-[#666]">
                <span className="size-1.5 rounded-full bg-[#c6ff3d] shadow-[0_0_6px_#c6ff3d]" />
                Live counter
              </div>
            </section>

            <form
              onSubmit={submit}
              className="rounded-2xl border border-white/9 bg-[#121212] p-4 shadow-[0_24px_80px_rgba(0,0,0,0.28)] sm:p-6"
            >
              <fieldset>
                <div className="mb-2.5 flex items-center justify-between">
                  <label htmlFor="strategy" className="field-label mb-0!">
                    Strategy
                  </label>
                  <span className="font-mono text-[10px] text-[#555]">
                    Shortcut:{" "}
                    <kbd className="rounded border border-white/8 bg-white/4 px-1 py-0.5 text-[#888]">
                      S
                    </kbd>
                  </span>
                </div>
                <div ref={selectRef} className="relative">
                  <button
                    type="button"
                    id="strategy"
                    role="combobox"
                    aria-expanded={isOpen}
                    aria-haspopup="listbox"
                    aria-controls="strategy-list"
                    onClick={() => setIsOpen((prev) => !prev)}
                    className={`flex w-full items-center justify-between rounded-xl border bg-[#0e0e0e] px-4 py-3 text-left transition outline-none ${
                      isOpen
                        ? "border-[#c6ff3d]/60 ring-2 ring-[#c6ff3d]/10"
                        : "border-white/9 hover:border-white/16"
                    }`}
                  >
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] text-[#666]">[{selectedIndex}]</span>
                        <span className="text-[14px] font-medium text-white">
                          {STRATEGY_ITEMS[selectedIndex].label}
                        </span>
                      </div>
                      <span className="font-mono text-[11px] text-[#717171]">
                        {STRATEGY_ITEMS[selectedIndex].desc}
                      </span>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <kbd className="hidden sm:inline-block rounded border border-white/8 bg-white/4 px-1.5 py-0.5 font-mono text-[10px] text-[#666]">
                        S
                      </kbd>
                      <ChevronIcon open={isOpen} />
                    </div>
                  </button>

                  {isOpen && (
                    <ul
                      id="strategy-list"
                      role="listbox"
                      aria-label="Naming strategies"
                      className="absolute z-30 mt-1.5 max-h-72 w-full overflow-y-auto rounded-xl border border-white/10 bg-[#141414] p-1.5 shadow-[0_18px_40px_rgba(0,0,0,0.6)] backdrop-blur-md"
                    >
                      {STRATEGY_ITEMS.map((item, index) => {
                        const selected = selectedIndex === index;
                        return (
                          <li
                            key={item.name}
                            role="option"
                            aria-selected={selected}
                            onClick={() => {
                              setSelectedIndex(index);
                              setIsOpen(false);
                            }}
                            className={`flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 transition ${
                              selected
                                ? "bg-[#c6ff3d]/10 text-white"
                                : "text-[#d1d1d1] hover:bg-white/6"
                            }`}
                          >
                            <div className="flex flex-col gap-0.5">
                              <div className="flex items-center gap-2">
                                <span
                                  className={`font-mono text-[11px] ${selected ? "text-[#c6ff3d]" : "text-[#555]"}`}
                                >
                                  [{index}]
                                </span>
                                <span
                                  className={`text-[13px] font-medium ${selected ? "text-[#c6ff3d]" : "text-white"}`}
                                >
                                  {item.label}
                                </span>
                              </div>
                              <span className="font-mono text-[10px] text-[#6b6b6b]">
                                {item.desc}
                              </span>
                            </div>
                            {selected && (
                              <span className="size-1.5 rounded-full bg-[#c6ff3d] shadow-[0_0_6px_rgba(198,255,61,0.6)]" />
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              </fieldset>

              <div className="mt-6">
                <label htmlFor="brief" className="field-label">
                  Enter your product description
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
                  required
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

              <div className="mt-5">
                <div className="mb-2 flex items-center justify-between">
                  <label htmlFor="keywords" className="field-label mb-0!">
                    Keywords (comma separated)
                  </label>
                  <span className="font-mono text-[10px] text-[#555]">Optional</span>
                </div>
                <input
                  id="keywords"
                  type="text"
                  value={keywordsInput}
                  onChange={(event) => {
                    setKeywordsInput(event.target.value);
                    if (error) setError("");
                  }}
                  placeholder="e.g. ai, code review, ast, developer tool"
                  className="w-full rounded-xl border border-white/9 bg-[#0e0e0e] px-4 py-3 font-mono text-[13px] text-white outline-none transition placeholder:text-[#555] focus:border-[#c6ff3d]/60 focus:ring-2 focus:ring-[#c6ff3d]/10"
                />
              </div>

              <div className="mt-6 flex flex-col gap-5 border-t border-white/[0.07] pt-5 sm:flex-row sm:items-end sm:justify-between">
                <fieldset>
                  <label htmlFor="total-names" className="field-label mb-2 block">
                    Total names (max 20)
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="inline-flex rounded-lg border border-white/8 bg-[#0d0d0d] p-1">
                      {[3, 5, 10, 20].map((number) => (
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
                    <input
                      id="total-names"
                      type="number"
                      min={1}
                      max={20}
                      value={count}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        if (!isNaN(val)) setCount(Math.max(1, Math.min(20, val)));
                      }}
                      className="h-[38px] w-16 rounded-lg border border-white/8 bg-[#0d0d0d] px-2 text-center font-mono text-[13px] text-white outline-none focus:border-[#c6ff3d]/60"
                      aria-label="Custom total names"
                    />
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
                      {loadingStage === "keywords"
                        ? "Generating keywords..."
                        : "Generating names..."}
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
                  <div className="flex items-center gap-2.5">
                    <span className="loading-spinner" />
                    <p className="text-sm font-medium text-[#bdbdbd]">
                      {loadingStage === "keywords"
                        ? "Generating keywords with..."
                        : "Generating names..."}
                    </p>
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-[#c6ff3d]">
                    {loadingStage === "keywords" ? "Step 1/2: Keywords" : "Step 2/2: Names"}
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
        <div className="mx-auto flex max-w-280 flex-col gap-3 px-5 py-6 font-mono text-[11px] text-[#555] sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div className="flex items-center gap-1.5">
            <span>@ wsict by</span>
            <a
              href="https://github.com/r3yc0n1c"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#888] underline decoration-white/20 underline-offset-4 transition hover:text-[#c6ff3d] hover:decoration-[#c6ff3d]"
            >
              r3yc0n1c
            </a>
          </div>
          <span className="text-[10px] uppercase tracking-widest text-[#555]">
            Built for people building things.
          </span>
          <div className="flex items-center gap-2 text-[#777]">
            <span className="size-1.5 rounded-full bg-[#c6ff3d] shadow-[0_0_5px_#c6ff3d]" />
            <span>{visitorCount.toLocaleString()} visitors</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
