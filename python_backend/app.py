"""
Contract Triage — Python backend

This replaces the direct browser-to-Groq fetch call in the HTML tool with a small
Flask server. The HTML frontend now calls this server instead of calling Groq
directly, which is also closer to how this would actually be deployed in production
(API keys live on a server, never in a browser).

Run with:
    pip install flask flask-cors requests
    export GROQ_API_KEY="your_key_here"
    python app.py

Then open index.html — it will call http://localhost:5000 instead of Groq directly.
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load variables from a local .env file if one exists (see .env.example).
# This file is gitignored / excluded from the submission zip on purpose —
# it should never contain a real key when shared with anyone else.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional — falls back to a key set directly in the terminal

app = Flask(__name__)
CORS(app)  # allow the HTML file (opened directly in a browser) to call this server

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- Standard templates -----------------------------------------------------
# Same baselines as the HTML version, kept here so the Python side is self-contained
# and can be tested or extended independently of the frontend.

TEMPLATES = {
    "nda": """MUTUAL NON-DISCLOSURE AGREEMENT (STANDARD TEMPLATE)

This Agreement is made between PortSwigger Ltd ("Company") and the counterparty ("Recipient").

1. CONFIDENTIAL INFORMATION
"Confidential Information" means any non-public information disclosed by either party, whether oral, written, or electronic, that is designated as confidential or would reasonably be understood to be confidential.

2. TERM
This Agreement shall remain in effect for a period of two (2) years from the Effective Date.

3. OBLIGATIONS
The Recipient shall:
(a) use Confidential Information solely for the purpose of evaluating a potential business relationship;
(b) not disclose Confidential Information to any third party without prior written consent;
(c) protect Confidential Information using the same degree of care it uses for its own confidential information, but no less than reasonable care.

4. EXCLUSIONS
Confidential Information does not include information that:
(a) is or becomes publicly available through no fault of the Recipient;
(b) was rightfully known prior to disclosure;
(c) is independently developed without use of Confidential Information;
(d) is rightfully received from a third party without duty of confidentiality.

5. GOVERNING LAW
This Agreement shall be governed by the laws of England and Wales.

6. LIABILITY
Neither party's liability under this Agreement shall exceed £50,000.

7. RETURN OF MATERIALS
Upon termination, each party shall return or destroy all Confidential Information within 30 days.""",

    "order_form": """CUSTOMER ORDER FORM (STANDARD TEMPLATE)

This Order Form is entered into between PortSwigger Ltd ("Supplier") and the Customer.

1. PRODUCT / LICENCE
Burp Suite Enterprise Edition, annual subscription, as specified in the order summary.

2. TERM
Twelve (12) months from the Order Start Date, auto-renewing annually unless cancelled with 30 days notice.

3. PAYMENT TERMS
Payment due within thirty (30) days of invoice date (Net 30).

4. PRICE
As stated in the order summary. Prices are fixed for the initial term.

5. SEAT COUNT / USAGE LIMITS
As specified in the order summary. Additional seats may be added at the then-current list price, pro-rated for the remainder of the term.

6. SUPPORT LEVEL
Standard support included: business hours email and ticket support, response within 1 business day.

7. DATA PROCESSING
Governed by PortSwigger's standard Data Processing Addendum (DPA), incorporated by reference.

8. LIABILITY CAP
Limited to fees paid in the twelve (12) months preceding the claim.

9. GOVERNING LAW
England and Wales.

10. CANCELLATION
Either party may cancel at the end of the then-current term with 30 days written notice.""",
}


# --- Precedent log -----------------------------------------------------------
# In-memory for this prototype, same as the JS version. A real deployment would
# back this with a database (e.g. Postgres, or even just a shared Google Sheet,
# the same ID-based pattern used in the ActiveFence pipeline) so precedent set by
# one lawyer is visible to the whole team immediately.

precedent_log = []  # list of {doc_type, title, contract_value, flag, logged_at}


def build_precedent_context(doc_type: str) -> str:
    """Turn logged precedents for this doc type into prompt context."""
    relevant = [p for p in precedent_log if p["doc_type"] == doc_type]
    if not relevant:
        return ""
    lines = "\n".join(
        f'- {p["title"]}: "{p["contract_value"]}" was previously approved by a lawyer'
        for p in relevant
    )
    return (
        "\n\nPREVIOUSLY APPROVED PRECEDENTS for this document type "
        "(treat deviations matching these as \"low\" risk and seen_before: true, "
        f"since a human has already signed off on them):\n{lines}"
    )


# --- Prompt construction ------------------------------------------------------

def build_system_prompt(doc_label: str) -> str:
    return f"""You are a contract triage assistant for an in-house legal team at a B2B software company. You compare an incoming {doc_label} against a standard template and identify substantive deviations.

For each deviation, classify it as:
- "low": a deviation the team has clearly seen before, follows an obvious common pattern, safe to approve or respond to with a known standard response.
- "med": a recognisable pattern but worth a quick human glance before approving.
- "high": something genuinely novel, unusually one-sided, or that meaningfully changes risk exposure — needs a lawyer to read closely.

Only flag SUBSTANTIVE differences. Ignore pure formatting or trivial wording changes.

Respond ONLY with valid JSON, no other text:
{{
  "overall_risk": "low" | "med" | "high",
  "overall_summary": "one sentence plain-English summary",
  "clauses": [
    {{
      "title": "short clause name",
      "flag": "low" | "med" | "high",
      "template_value": "brief",
      "contract_value": "brief",
      "reasoning": "one or two plain-English sentences",
      "seen_before": true | false
    }}
  ]
}}"""


# --- Groq call -----------------------------------------------------------------

def call_groq(system_prompt: str, user_content: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at console.groq.com and run: "
            "export GROQ_API_KEY='your_key_here'"
        )

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": GROQ_MODEL,
            "max_tokens": 1500,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(f"Groq API returned {response.status_code}: {response.text[:300]}")

    data = response.json()
    raw_text = data["choices"][0]["message"]["content"].strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    return json.loads(raw_text)


def review_document(doc_type: str, document_text: str) -> dict:
    """Core triage function: compares one document against its template."""
    if doc_type not in TEMPLATES:
        raise ValueError(f"Unknown document type: {doc_type}")

    doc_label = "NDA" if doc_type == "nda" else "customer order form"
    template = TEMPLATES[doc_type]
    system_prompt = build_system_prompt(doc_label)
    precedent_context = build_precedent_context(doc_type)

    user_content = (
        f"STANDARD TEMPLATE:\n{template}\n{precedent_context}\n\n---\n\n"
        f"INCOMING {doc_label.upper()}:\n{document_text}\n\n"
        "Compare and return the JSON triage result."
    )

    return call_groq(system_prompt, user_content)


# --- Routes ----------------------------------------------------------------

@app.route("/api/review", methods=["POST"])
def review_single():
    """Single-document review. Mirrors runSingleReview() in the HTML/JS version."""
    body = request.get_json(force=True)
    doc_type = body.get("doc_type")
    document_text = body.get("document_text", "").strip()

    if not document_text:
        return jsonify({"error": "document_text is required"}), 400
    if doc_type not in TEMPLATES:
        return jsonify({"error": "doc_type must be 'nda' or 'order_form'"}), 400

    try:
        result = review_document(doc_type, document_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/review-batch", methods=["POST"])
def review_batch():
    """
    Batch review. Mirrors runBatchReview() in the HTML/JS version.

    Same ID-based pattern used in the ActiveFence generative media pipeline:
    each document gets an id, gets processed independently, and a failure on
    one item never blocks the rest of the batch — it just gets an 'error'
    status while the others complete normally.
    """
    body = request.get_json(force=True)
    doc_type = body.get("doc_type")
    documents = body.get("documents", [])  # [{"id": "DOC-001", "text": "..."}]

    if doc_type not in TEMPLATES:
        return jsonify({"error": "doc_type must be 'nda' or 'order_form'"}), 400
    if not documents:
        return jsonify({"error": "documents list is required"}), 400

    results = []
    for doc in documents:
        doc_id = doc.get("id")
        text = doc.get("text", "").strip()
        if not text:
            results.append({"id": doc_id, "status": "error", "summary": "Empty document"})
            continue
        try:
            result = review_document(doc_type, text)
            results.append({
                "id": doc_id,
                "status": result["overall_risk"],
                "summary": result["overall_summary"],
                "full": result,
            })
        except Exception as e:
            results.append({"id": doc_id, "status": "error", "summary": str(e)})

    return jsonify({"results": results})


@app.route("/api/precedents", methods=["GET"])
def get_precedents():
    """Return the current precedent log, optionally filtered by doc_type."""
    doc_type = request.args.get("doc_type")
    if doc_type:
        filtered = [p for p in precedent_log if p["doc_type"] == doc_type]
        return jsonify(filtered)
    return jsonify(precedent_log)


@app.route("/api/precedents", methods=["POST"])
def add_precedent():
    """
    Log a lawyer-approved clause as precedent. This is the Python equivalent
    of approveAndLog() / approveAndLogBatch() in the JS version — a human
    explicitly decides what becomes institutional memory, the AI doesn't
    add anything to this log on its own.
    """
    body = request.get_json(force=True)
    required = {"doc_type", "title", "contract_value", "flag"}
    if not required.issubset(body):
        return jsonify({"error": f"Missing fields, need: {required}"}), 400

    import time
    entry = {
        "doc_type": body["doc_type"],
        "title": body["title"],
        "contract_value": body["contract_value"],
        "flag": body["flag"],
        "logged_at": int(time.time() * 1000),
    }
    precedent_log.append(entry)
    return jsonify({"status": "logged", "precedent_count": len(precedent_log)})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "precedent_count": len(precedent_log)})


if __name__ == "__main__":
    print("Contract Triage backend running at http://localhost:5000")
    print(f"Precedent log starts empty. GROQ_API_KEY set: {bool(os.environ.get('GROQ_API_KEY'))}")
    app.run(debug=True, port=5000)
