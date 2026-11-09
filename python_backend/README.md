# Contract Triage — Python backend version

This is a second version of the tool, built around a Python Flask server instead
of calling Groq directly from the browser. Same logic, same prompts, same
precedent system — just with the "thinking" part in Python instead of JavaScript,
so it can be read, run, and extended as a Python project.

## Why this version exists alongside the pure-HTML one

The original `index.html` (in the parent folder) is fully standalone — open it,
paste in a free Groq API key, done. That's the simplest possible thing to hand
someone to test.

This version moves the API key and all the prompt-building logic server-side,
which is closer to how a real production tool would actually be built (API
keys should never live in a browser long-term) — and it means the core logic
exists as plain, readable Python that's easy to study, test, and extend without
touching any JavaScript at all.

## Setup

```bash
cd python_backend
pip install -r requirements.txt
```

Get a free API key at console.groq.com (no card required), then choose **one** of these two ways to provide it:

**Option A — a local `.env` file (recommended, less typing each time)**

Copy `.env.example` to a new file called `.env` in this folder, and put your real key in it:

```
GROQ_API_KEY=gsk_your_actual_key_here
```

`app.py` loads this automatically. **Never put a real key in `.env.example` or in any file you intend to share** — `.env` is meant to stay local to your machine only.

**Option B — set it in your terminal each session**

```bash
export GROQ_API_KEY="your_key_here"      # Mac/Linux
set GROQ_API_KEY=your_key_here           # Windows (cmd)
$env:GROQ_API_KEY="your_key_here"        # Windows (PowerShell)
```

This only lasts for that terminal session — close the window and you'll need to set it again.

## Run it two ways

**1. As a CLI script, no web server, no browser** — the fastest way to actually
read and understand the logic:

```bash
python test_cli.py
```

This calls `review_document()` directly, prints the result, then logs a
precedent and re-runs the same review to show the precedent being picked up
in the second pass.

**2. As a full web app**, same as before but Python-backed:

```bash
python app.py
```

This starts a server at `http://localhost:5000`. Then open `index.html`
(in this folder) in a browser — it now talks to your local Python server
instead of calling Groq directly.

## How the pieces fit together

- **`app.py`** — the whole backend. Templates, prompt construction, the precedent
  log, and three routes: `/api/review` (single document), `/api/review-batch`
  (multiple documents, same ID-tracked pattern as the JS version), and
  `/api/precedents` (view and add precedents).
- **`test_cli.py`** — imports straight from `app.py` and calls the same
  `review_document()` function a script would, no Flask involved. Good place
  to start reading if you want to understand the logic with nothing else
  in the way.
- **`index.html`** — same UI as the original, but the JavaScript now just
  sends documents to your Python server and renders whatever comes back,
  instead of building prompts and calling Groq itself.

## What's genuinely the same vs what changed

Same: the templates, the low/med/high classification logic, the precedent
concept, the batch ID-tracking pattern, the overall UI and flow.

Changed: where the "thinking" happens. In the original, the browser builds
the prompt and calls Groq directly. Here, the browser just sends the raw
document and document type to Python, and Python does everything — building
the prompt, calling Groq, tracking precedents — and sends back a finished
result.
