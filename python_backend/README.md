# Contract Triage — first-pass review tool (v0.2)

This submission includes two versions of the same tool:

- **`index.html`** (this folder) — fully standalone. Open it in a browser, paste in a free Groq API key, done. No installation needed.
- **`python_backend/`** — the same logic rebuilt around a Python Flask server. The browser sends documents to a local Python server, which does all the prompt construction, API calls, and precedent tracking. See `python_backend/README.md` for setup. This is the version that's easiest to read and extend as plain Python, and closer to how this would actually be deployed in production (API keys belong on a server, not in a browser).

Both versions are functionally identical — same templates, same classification logic, same precedent system. Pick whichever is easier to run; the README below applies to both.

## The problem, as I read it
Every contract gets a full manual read, but most of it is the same 80% boilerplate, and most redlines follow patterns the team has already seen. The expensive resource (a lawyer's attention) is being spent reading things that don't need close reading, which is why the queue backs up at end of month/quarter when volume spikes.

## What changed from v0.1
The first version only handled NDAs and assumed one way of working. Talking it through, two things were missing:

1. **Order forms are a different document with different things that matter** — term length, price locks, support SLAs, data residency — not the same checklist as an NDA. So the tool now asks what you're reviewing first, and loads the right baseline.
2. **Not every lawyer wants the same level of AI involvement on every document.** Some days you want a second pair of eyes on one document at a time. Other days — especially end of quarter — you've got a pile and you want it triaged so you only open what actually needs you. So the tool now asks how you want to work, and offers both.

## What changed from v0.2 — precedent memory
Every review used to start from zero, judged only against the static template and the AI's own guess at what counts as "typical." That's a real gap: a new client always brings a new document, but the deviations repeat — Delaware instead of England and Wales, a longer term, a higher liability cap. The legal team already has institutional memory of what they've waved through before; the tool didn't.

Now, in single mode, a lawyer can hit **"Approve & log as precedent"** on any clause. That gets added to a running precedent log for that document type. On every future review, the log is fed back into the prompt, so a deviation that matches something already approved gets flagged "low risk, matches N previously approved precedents" rather than the AI re-guessing from scratch each time. The lawyer decides what becomes precedent, not the AI — this is closer to how a real team actually builds shared judgement.

This is in-memory only in the prototype (clears on page reload). In a real deployment this would be a shared store — likely a Google Sheets or lightweight database, so precedent set by one lawyer benefits the whole team immediately, not just the person who logged it.

## The two modes

**Single mode** — paste one document, get a clause-by-clause comparison against the standard template, each flagged low/medium/high with a plain-English reason. You stay in the loop on every document; AI just cuts the reading time.

**Batch mode** — paste in several documents at once (in a real deployment, this would be wired to a watched folder or a spreadsheet of document IDs and links, a common batch-job pattern: each row gets an ID, a status, and a result written back independently, so one bad document never blocks the rest of the run). You get a queue-style table — ID, risk status, one-line reason — and only open the detail on the ones flagged medium or high. The low-risk ones still have their reasoning logged, which doubles as an audit trail for why something was waved through without a human reading it line by line.

This mirrors how the actual queue works: most days you might want single mode for a one-off; on a heavy sales week you want batch mode to clear the backlog fast.

## Why this shape, not something bigger
I didn't build a full contract management system or a Slack bot. The brief described two fairly narrow, repeatable document types. The highest-leverage thing for a two-week sprint is something that works well on that narrow case and is genuinely usable Monday morning.

If this were a real two-week embed:
- Day 1–2: sit with the legal team, pull 15–20 real past documents of each type to find the actual recurring redline patterns, not ones I'm guessing at
- Day 3–5: build the comparison tool against the real templates, tune the low/med/high boundaries against what the team would actually flag themselves
- Day 6–8: get it in front of whoever currently does this read, watch them use it in both modes, fix what's actually annoying
- Day 9–10: hand it over in a form that keeps running without me — likely wired to wherever contracts actually land (inbox, CLM tool, shared drive) rather than copy-paste

## Honesty about this prototype
- Only NDAs and order forms have templates right now; a DPA template would follow the same pattern
- The risk classification is currently driven by the LLM's judgement against the system prompt. In a real version I'd validate this against actual examples of what the legal team considers "seen before" versus not
- Batch mode processes documents one at a time in sequence rather than in parallel, to keep this prototype simple and avoid rate limit issues — a production version would parallelise with proper concurrency limits, using async job handling
- It needs an API key typed into the browser to run as a static file — in production this sits behind a proper backend; this is just the fastest way to make it genuinely testable as a standalone file rather than something that only works inside a sandboxed environment
- This prototype calls Groq's free API running Llama 3.3 70B, purely so the tool is genuinely free to test end to end with no card or paid account needed. The system prompt and JSON contract are model-agnostic — swapping in Claude, GPT-4, or another model is a one-line change to the API call. For a real legal use case I'd actually want to evaluate a few models specifically on accuracy and consistency of the risk classification before picking one, since getting a "low risk, seen before" call wrong is the one failure mode that actually matters here

## How to run it
Open `index.html` in a browser, get a free API key from console.groq.com (no card required), choose a document type and a mode, and try it. "Load 4 sample documents" in batch mode gives you a mix of clean and redlined NDAs or order forms to triage at once.
