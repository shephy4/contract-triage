"""
Simple command-line test of the contract triage logic, no Flask, no browser.

This is the best place to actually read and understand what's happening —
it's the same review_document() function the Flask server uses, just called
directly from a script so you can see input -> output with nothing else
in the way.

Run with:
    pip install requests
    export GROQ_API_KEY="your_key_here"
    python test_cli.py
"""

import os
import sys

# Reuse the exact same logic as the Flask app, no duplication
sys.path.insert(0, os.path.dirname(__file__))
from app import review_document, TEMPLATES, precedent_log


REDLINED_NDA_EXAMPLE = """MUTUAL NON-DISCLOSURE AGREEMENT

This Agreement is made between PortSwigger Ltd ("Company") and Acme Security Solutions Ltd ("Recipient").

1. CONFIDENTIAL INFORMATION
"Confidential Information" means any non-public information disclosed by either party, whether oral, written, or electronic, that is designated as confidential or would reasonably be understood to be confidential.

2. TERM
This Agreement shall remain in effect for a period of five (5) years from the Effective Date.

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
This Agreement shall be governed by the laws of Delaware, United States.

6. LIABILITY
Neither party's liability under this Agreement shall exceed £500,000.

7. RETURN OF MATERIALS
Upon termination, each party shall return or destroy all Confidential Information within 90 days.

8. INDEMNIFICATION
The Recipient shall indemnify and hold harmless the Company against any and all claims, damages, losses, and expenses arising from the Recipient's breach of this Agreement, including reasonable attorneys' fees, without limitation."""


def print_result(result: dict):
    risk_labels = {"low": "LOW RISK", "med": "NEEDS A GLANCE", "high": "NEEDS A LAWYER"}
    print(f"\n  Overall: {risk_labels.get(result['overall_risk'], result['overall_risk'])}")
    print(f"  Summary: {result['overall_summary']}\n")
    for clause in result["clauses"]:
        flag = risk_labels.get(clause["flag"], clause["flag"])
        print(f"  [{flag}] {clause['title']}")
        print(f"      Template: {clause['template_value']}")
        print(f"      Document: {clause['contract_value']}")
        print(f"      Why: {clause['reasoning']}")
        if clause.get("seen_before"):
            print(f"      -> AI judges this a common pattern")
        print()


if __name__ == "__main__":
    print("=" * 70)
    print("CONTRACT TRIAGE — CLI test")
    print("=" * 70)

    print("\nReviewing a redlined NDA against the standard template...")
    result = review_document("nda", REDLINED_NDA_EXAMPLE)
    print_result(result)

    print("=" * 70)
    print("Now simulating a lawyer approving the 'Liability' clause as precedent,")
    print("then re-running the SAME review to show the precedent gets picked up.")
    print("=" * 70)

    liability_clause = next(c for c in result["clauses"] if c["title"].lower() == "liability")
    precedent_log.append({
        "doc_type": "nda",
        "title": liability_clause["title"],
        "contract_value": liability_clause["contract_value"],
        "flag": liability_clause["flag"],
        "logged_at": 0,
    })
    print(f"\nLogged precedent: {liability_clause['title']} -> {liability_clause['contract_value']}\n")

    print("Re-running the review with that precedent now in memory...")
    result2 = review_document("nda", REDLINED_NDA_EXAMPLE)
    print_result(result2)
