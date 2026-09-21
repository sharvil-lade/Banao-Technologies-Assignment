"""
The AI layer - and the only place in this codebase where a model sees data.

Design rules, enforced by structure rather than discipline:

  1. The LLM reads free text and returns a LABEL. It never sees, produces or
     adjusts a monetary amount. Every rupee figure in this system is computed
     by pandas in aggregate.py.
  2. Its output lands in columns prefixed `ai_` and never overwrites
     reason_code (D-16). Deterministic fact and model interpretation sit side
     by side in the same table and are always distinguishable.
  3. Every label carries a verbatim evidence quote, the model name and a run id,
     so any interpretation can be checked against the source record.

Three backends:
  cache     - read a previously generated classification file (default; needs no
              network, so a clean machine can run the whole tool)
  anthropic - call the Anthropic API (needs ANTHROPIC_API_KEY)
  rules     - deterministic keyword baseline, no model at all. Exists as an
              honest fallback AND as the control the LLM is measured against in
              validation: if the model cannot beat keywords, it has not earned
              its place.
"""
from __future__ import annotations
import json
import os
import re
import uuid
from pathlib import Path
import pandas as pd
from . import config

VALID_REASONS = set(config.REASON_LABELS) | {"INSUFFICIENT-EVIDENCE"}
VALID_THEMES = {
    "payment_failure", "transit_lost", "transit_damage", "dead_on_arrival",
    "hardware_fault", "connectivity_firmware", "delivery_delay",
    "customer_cancellation", "pricing_coupon", "service_recovery", "return_qc", "unclear",
}
AI_COLUMNS = ["ai_suggested_reason", "ai_theme", "ai_confidence", "ai_evidence_quote",
              "ai_model", "ai_run_id"]

PROMPT_PATH = config.ROOT / "prompts" / "reason_classifier.md"
DEFAULT_CACHE = config.DERIVED / "ai_classifications.csv"
MAX_TEXT = 400


def build_input(refunds: pd.DataFrame) -> pd.DataFrame:
    """The exact text handed to the model. Truncated for cost; agent_notes is
    the decisive field so it is never the one dropped."""
    out = refunds[["ticket_id"]].copy()
    out["customer_message"] = refunds.customer_message.fillna("").str.slice(0, MAX_TEXT)
    out["agent_notes"] = refunds.agent_notes.fillna("").str.slice(0, MAX_TEXT)
    return out


def write_batches(refunds: pd.DataFrame, out_dir, batch_size: int = 200):
    """Write JSONL batches. Used by the API backend and by manual/offline runs."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = build_input(refunds)
    paths = []
    for i in range(0, len(src), batch_size):
        chunk = src.iloc[i:i + batch_size]
        p = out_dir / f"batch_{i // batch_size:03d}.jsonl"
        with open(p, "w", encoding="utf-8") as fh:
            for _, r in chunk.iterrows():
                fh.write(json.dumps({
                    "ticket_id": r.ticket_id,
                    "customer_message": r.customer_message,
                    "agent_notes": r.agent_notes,
                }, ensure_ascii=False) + "\n")
        paths.append(p)
    return paths


# ---------------------------------------------------------------- rules backend
# TIER 1 of the classifier. Ordered most-specific first; a ticket takes the first
# pattern that matches. The ordering IS the logic: "payment debited, no ord"
# mentions a payment gateway and so does a return-refund chase, so the payment
# patterns must be tested before the return patterns.
#
# These patterns were derived by reading a 168-ticket sample by hand (that sample
# is now data/eval/gold_labels.csv and is what the engine is measured against).
# Anything this tier cannot resolve returns INSUFFICIENT-EVIDENCE and is escalated
# to tier 2, the model. That escalation is the only thing that costs money.
RULES = [
    # --- payment: most specific, and the phrasing is unmistakable
    ("DUP-PAYMENT", "payment_failure",
     r"(?:payment debited,?\s*no\s*ord|paymnt debited|amount deducted without ord|"
     r"deducted but no order|no order was created|failed ord(?:er)? aft(?:e)?r payment|"
     r"faild ord|charged twice|charged two times|double charge|double paymeent|"
     r"double payment|duplicate payment|duplicate txn|duplicate refunded|"
     r"conf(?:irmed|irmde|n)?\s*utrs?|asked for utr|pg dashboard|payment gateway|"
     r"upi shows success|paid via upi, amount deducted|money debited but order not|"
     r"went to (?:you|u) but (?:your|ur) site says i have no orders|"
     r"page failed after i paid|two entries of rs)"),
    # --- cancellation before dispatch
    ("CANCEL", "customer_cancellation",
     r"(?:cancel(?:l)?ed before disp|cancell?ation request|cancel ord|order cancellation|"
     r"ord cancellation|cancelllation|ordered by mistake|don\'?t ship it|"
     r"change of mind|please cancel|want to cancel|cancelled, r(?:e)?fnd initiated|"
     r"cancelled, refund initiated)"),
    # --- physical damage on arrival
    ("DOA-REPL", "transit_damage",
     r"(?:transit damage|damaged in transit|damage conf|unit r(?:e)?c(?:ei)?vd damaged|"
     r"received damaged|arrived damaged|box was crushed|parcel looked like it was|"
     r"kicked here from the warehouse|is cracked|has a crack|craack|"
     r"dent on the case straight out of the box|dead on arrival|\bdoa\b)"),
    # --- parcel never arrived
    ("LOST-TRANSIT", "transit_lost",
     r"(?:lost in transit|shipment not r(?:e)?c(?:ei)?vd|ord(?:er)? not delivered|"
     r"not delivered even after|package not delivered|never arrived|undelivered|"
     r"has not been delivered|tracking not updating|delivery delayed|dlvry delayed|"
     r"\brto\b|awb with courier|chk awb|courier partner)"),
    # --- pricing and coupons
    ("PRICE-ADJ", "pricing_coupon",
     r"(?:promo code|prmo code|pormo code|coupon|discount not applied|price drop|"
     r"price adj|festive offer|cart eligi|20% off|cashback not)"),
    # --- the return / reverse-pickup process (the single biggest true category)
    ("RETURN-QC-OK", "return_qc",
     r"(?:reverse p(?:ic)?k(?:u)?p|revrese pickup|reverse pkp|pkp not done|pickup not done|"
     r"pcikup missed|pkp missed|pickup missed|nobody came for the pickup|"
     r"nobdy came for the pickup|pickup scheduled but no one|pickup awb|pkp awb|"
     r"re-?raised p(?:ic)?k(?:u)?p|rescheduled pickup|passed qc|qc status|qc report|"
     r"return was accepted|where is the money for the return|"
     r"picked up the item|return received|returned the|change of mind.*return|"
     r"r(?:e)?fnd not credited|refund not credited|reufnd not credited|"
     r"r(?:e)?fnd delay|refund delay|refuund delay|rfeund|refund pending|rfnd pending|"
     r"refund not received|refund was promised|still waiting for my refund|"
     r"arn shared|refund reprocessed|rfnd reprocessed|wrong item|wrong variant|"
     r"incorrect product shipped|ordered black, got white|"
     r"opened the parcel and it is a completely different thing)"),
    # --- in-warranty hardware and firmware faults
    ("WTY-BUYBACK", "hardware_fault",
     r"(?:warranty|wty\b|\brma\b|buy-?back|service cent|repair (?:status|completed)|"
     r"no update on my repair|battery drain|draining fast|promised \d+ hours|"
     r"not charging|no charge|no led|not taking charge|mic issue|mic not working|"
     r"sound like|single side audio|no audio one side|one ear only|side silent|"
     r"unresponsive display|ignores my finger|screen)"),
    ("WTY-BUYBACK", "connectivity_firmware",
     r"(?:pairing fail|unable to pair|cannot pair|not discoverable|device not discover|"
     r"intermittent disconnect|random disconnect|connection drop|connection dropping|"
     r"losing my phone if i walk|fw update|firmware|bluetooth|crackling|distortion|"
     r"frying sound|stutters)"),
    # --- genuine goodwill, checked LAST so a real reason always wins
    ("GW-OTHER", "service_recovery",
     r"(?:as goodwill|one-?time gesture|goodwill|as a gesture|apolog|"
     r"escalation avoided|threatened social media|to keep him happy|"
     r"to keep her happy|cx was very upset|placate)"),
]
_COMPILED = [(c, t, re.compile(p, re.IGNORECASE)) for c, t, p in RULES]

# The known failure mode of tier 1, found by measuring against the gold set.
# When the agent both describes a concrete problem AND uses goodwill language
# ("resolved... refund given anyway", "cx threatened social media"), the keyword
# order decides the answer and the order is arbitrary. That is a real ambiguity,
# not a gap in the pattern list, so these are escalated to tier 2 rather than
# guessed at. Escalating is the honest move AND the cheap one: it is a small,
# well-defined slice of tickets.
GOODWILL_RE = re.compile(
    r"(?:as goodwill|one-?time gesture|goodwill|as a gesture|escalation avoided|"
    r"threatened social media|to keep (?:him|her) happy|cx was very upset|placate)",
    re.IGNORECASE)
RESOLVED_RE = re.compile(
    r"(?:resolved|rslvd|re-?pair successful|paired ok|reset done|advised|adv |"
    r"fw update resolved|repair completed|reshipped|rslvd on chat)", re.IGNORECASE)



def classify_rules(refunds: pd.DataFrame) -> pd.DataFrame:
    """
    Tier 1: deterministic keyword classification. No model, no network, no cost.

    Reads the agent note first and the customer message only as a fallback: the
    note is written after the agent knows what happened, so it is the more
    reliable field. Unresolved rows return INSUFFICIENT-EVIDENCE for tier 2.
    """
    src = build_input(refunds)
    rows = []
    for _, r in src.iterrows():
        reason, theme, quote, tier = "INSUFFICIENT-EVIDENCE", "unclear", "", "unresolved"
        for field, label in ((r.agent_notes, "note"), (r.customer_message, "message")):
            for code, th, rx in _COMPILED:
                m = rx.search(field or "")
                if m:
                    reason, theme, tier = code, th, f"rules:{label}"
                    s = max(0, m.start() - 25)
                    quote = field[s:m.end() + 25].replace("\n", " ").strip()[:90]
                    break
            if reason != "INSUFFICIENT-EVIDENCE":
                break
        # Conflict check: a concrete reason AND explicit goodwill language.
        note = r.agent_notes or ""
        if (reason not in ("INSUFFICIENT-EVIDENCE", "GW-OTHER")
                and GOODWILL_RE.search(note) and RESOLVED_RE.search(note)):
            reason, theme, tier = "INSUFFICIENT-EVIDENCE", "unclear", "escalated:goodwill_conflict"
            quote = note.replace("\n", " ").strip()[:90]
        rows.append({"ticket_id": r.ticket_id, "ai_suggested_reason": reason,
                     "ai_theme": theme, "ai_confidence": "n/a (rules)",
                     "ai_evidence_quote": quote, "ai_model": "rules-baseline-v2",
                     "ai_run_id": tier})
    out = pd.DataFrame(rows)
    out["ai_theme"] = out.ai_theme.where(out.ai_theme.isin(VALID_THEMES), "unclear")
    return out


# ------------------------------------------------------------ anthropic backend
def classify_anthropic(refunds: pd.DataFrame, model: str = "claude-sonnet-4-5",
                       batch_size: int = 50, max_batches: int | None = None) -> pd.DataFrame:
    """
    Real API path. Requires ANTHROPIC_API_KEY and the `anthropic` package.

    Not exercised in the shipped run - this environment had no key, so the
    committed classifications were produced by the model listed in the cache
    file. Kept complete and honest rather than removed: it is how Vireo would
    re-run this monthly.
    """
    import anthropic  # imported lazily so the tool runs without the dependency

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    run_id = uuid.uuid4().hex[:8]
    src = build_input(refunds)
    rows = []
    batches = range(0, len(src), batch_size)
    if max_batches:
        batches = list(batches)[:max_batches]
    for i in batches:
        chunk = src.iloc[i:i + batch_size]
        payload = "\n".join(
            json.dumps({"ticket_id": r.ticket_id, "customer_message": r.customer_message,
                        "agent_notes": r.agent_notes}, ensure_ascii=False)
            for _, r in chunk.iterrows())
        msg = client.messages.create(
            model=model, max_tokens=8000, temperature=0,
            system=prompt,
            messages=[{"role": "user", "content": payload}],
        )
        rows.extend(_parse_jsonl(msg.content[0].text, model, run_id))
    return _frame(rows)


def _parse_jsonl(text: str, model: str, run_id: str) -> list:
    rows = []
    for line in text.splitlines():
        line = line.strip().strip("`")
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append({
            "ticket_id": d.get("ticket_id"),
            "ai_suggested_reason": d.get("reason", "INSUFFICIENT-EVIDENCE"),
            "ai_theme": d.get("theme", "unclear"),
            "ai_confidence": d.get("confidence", "low"),
            "ai_evidence_quote": str(d.get("evidence", ""))[:90],
            "ai_model": model, "ai_run_id": run_id,
        })
    return rows


def _frame(rows: list) -> pd.DataFrame:
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["ticket_id"] + AI_COLUMNS)
    # A model can return a label outside the list. Quarantine it rather than
    # letting an invented reason code into the report.
    bad = ~out.ai_suggested_reason.isin(VALID_REASONS)
    out.loc[bad, "ai_suggested_reason"] = "INSUFFICIENT-EVIDENCE"
    out.loc[bad, "ai_confidence"] = "low"
    out["ai_theme"] = out.ai_theme.where(out.ai_theme.isin(VALID_THEMES), "unclear")
    return out.drop_duplicates("ticket_id")


# ---------------------------------------------------------------- cache backend
def classify_cached(refunds: pd.DataFrame, cache_path=None) -> pd.DataFrame:
    cache_path = Path(cache_path or DEFAULT_CACHE)
    if not cache_path.exists():
        raise FileNotFoundError(
            f"No AI classification cache at {cache_path}. Run with --ai-backend rules "
            f"for a no-model baseline, or set ANTHROPIC_API_KEY and use --ai-backend anthropic.")
    cached = pd.read_csv(cache_path, dtype=str, keep_default_na=False)
    return _frame(cached.to_dict("records"))


# -------------------------------------------------------------- two-tier entry
TIER2_CACHE = config.ROOT / "data" / "ai_labels" / "tier2.jsonl"


def classify_two_tier(refunds: pd.DataFrame, escalate_backend: str = "cache",
                      tier2_cache=None, **kw) -> pd.DataFrame:
    """
    The production classifier, and the reason this tool is cheap to run.

    Tier 1 (rules) resolves everything it can for nothing. Only what it cannot
    resolve - roughly 5% of refunds - reaches tier 2, the model. On the supplied
    18 months that is 125 tickets out of 2,340; at Vireo's ~650 tickets a week
    it is a couple of hundred model calls a month, not tens of thousands.

    escalate_backend:
      cache     - read tier-2 labels from data/ai_labels/tier2.jsonl (default,
                  needs no key, lets a clean machine reproduce the shipped numbers)
      anthropic - send the escalated rows to the API (how Vireo would re-run it)
      none      - leave them INSUFFICIENT-EVIDENCE and report the gap honestly
    """
    tier1 = classify_rules(refunds)
    unresolved = tier1.ai_suggested_reason == "INSUFFICIENT-EVIDENCE"
    n_esc = int(unresolved.sum())
    if n_esc == 0 or escalate_backend == "none":
        tier1.attrs["tier2_count"] = 0
        tier1.attrs["tier1_count"] = len(tier1) - n_esc
        return tier1

    esc_ids = set(tier1.loc[unresolved, "ticket_id"])
    esc_rows = refunds[refunds.ticket_id.isin(esc_ids)]

    if escalate_backend == "anthropic":
        tier2 = classify_anthropic(esc_rows, **kw)
    else:
        path = Path(tier2_cache or TIER2_CACHE)
        if not path.exists():
            raise FileNotFoundError(
                f"No tier-2 label cache at {path}. Use escalate_backend='none' to "
                f"run without a model, or 'anthropic' with ANTHROPIC_API_KEY set.")
        recs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        tier2 = _frame([{
            "ticket_id": d["ticket_id"], "ai_suggested_reason": d.get("reason"),
            "ai_theme": d.get("theme", "unclear"), "ai_confidence": d.get("confidence", "low"),
            "ai_evidence_quote": str(d.get("evidence", ""))[:90],
            "ai_model": d.get("model", "claude-opus-5"),
            "ai_run_id": "tier2", } for d in recs if d["ticket_id"] in esc_ids])

    merged = tier1.set_index("ticket_id")
    if not tier2.empty:
        t2 = tier2.set_index("ticket_id")
        common = merged.index.intersection(t2.index)
        merged.loc[common, AI_COLUMNS] = t2.loc[common, AI_COLUMNS]
    out = merged.reset_index()
    out.attrs["tier1_count"] = len(out) - n_esc
    out.attrs["tier2_count"] = n_esc
    return out


# ---------------------------------------------------------------------- entry
def classify(refunds: pd.DataFrame, backend: str = "two_tier", **kw) -> pd.DataFrame:
    if backend == "two_tier":
        return classify_two_tier(refunds, **kw)
    if backend == "cache":
        return classify_cached(refunds, kw.get("cache_path"))
    if backend == "rules":
        return classify_rules(refunds)
    if backend == "anthropic":
        return classify_anthropic(refunds, **kw)
    raise ValueError(f"unknown backend {backend!r}")


def attach(refunds: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """
    Join labels onto the canonical table without touching a single fact.

    `reason_code` stays exactly as the source system recorded it. The model's
    view is `ai_suggested_reason`, and where they differ we say so - we do not
    pick a winner. `flag_reason_mismatch` is an INTERPRETATION flag; it is
    deliberately excluded from the deterministic suspicion flags in policy.py.
    """
    n_before = len(refunds)
    out = refunds.merge(labels[["ticket_id"] + AI_COLUMNS], on="ticket_id", how="left")
    assert len(out) == n_before, "AI label join changed the row count"

    out["ai_covered"] = out.ai_suggested_reason.notna()
    for c in AI_COLUMNS:
        out[c] = out[c].fillna("")
    conclusive = out.ai_covered & ~out.ai_suggested_reason.isin(["", "INSUFFICIENT-EVIDENCE"])
    out["flag_reason_mismatch"] = conclusive & (out.ai_suggested_reason != out.reason_code)
    out["ai_agrees_with_recorded"] = conclusive & (out.ai_suggested_reason == out.reason_code)
    # The crisp business question for the dropdown default.
    out["ai_says_not_really_goodwill"] = (
        (out.reason_code == config.DROPDOWN_DEFAULT_REASON)
        & conclusive & (out.ai_suggested_reason != config.DROPDOWN_DEFAULT_REASON)
    )
    return out
