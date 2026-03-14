"""
Prompt Optimizer Evaluator — runs eval set against target model, scores results.
Supports Gemini (free tier), OpenRouter, and Anthropic as providers.
"""

import json
import os
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
PROVIDER = os.getenv("PROVIDER", "gemini").lower()
MODEL = os.getenv("MODEL", "")
PROMPT_FILE = Path(__file__).parent / "prompt.txt"
EVAL_FILE = Path(__file__).parent / "eval_set.jsonl"
LAST_RUN_FILE = Path(__file__).parent / "last_run.json"

FIELDS = ["name", "date", "time", "location", "price", "organizer"]

# Cost per 1K tokens (input, output) — approximate
COST_TABLE = {
    "gemini": (0.0, 0.0),  # free tier
    "openrouter": (0.0, 0.0),  # varies; default free model
    "anthropic": (0.001, 0.005),  # haiku approximate
}

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openrouter": "google/gemini-2.5-flash",
    "anthropic": "claude-haiku-4-5-20251001",
}


def get_model():
    return MODEL or DEFAULT_MODELS.get(PROVIDER, "gemini-2.0-flash")


def call_gemini(system_prompt: str, user_text: str) -> tuple[str, int, int]:
    from google import genai

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    response = client.models.generate_content(
        model=get_model(),
        contents=user_text,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0,
        ),
    )
    text = response.text or ""
    # Approximate token counts from usage metadata
    usage = getattr(response, "usage_metadata", None)
    input_tokens = getattr(usage, "prompt_token_count", 0) or 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0
    return text, input_tokens, output_tokens


def call_openrouter(system_prompt: str, user_text: str) -> tuple[str, int, int]:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
    response = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0,
    )
    text = response.choices[0].message.content or ""
    usage = response.usage
    input_tokens = usage.prompt_tokens if usage else 0
    output_tokens = usage.completion_tokens if usage else 0
    return text, input_tokens, output_tokens


def call_anthropic(system_prompt: str, user_text: str) -> tuple[str, int, int]:
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=get_model(),
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_text}],
        temperature=0,
    )
    text = response.content[0].text if response.content else ""
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    return text, input_tokens, output_tokens


CALLERS = {
    "gemini": call_gemini,
    "openrouter": call_openrouter,
    "anthropic": call_anthropic,
}


def normalize(value):
    """Normalize a value for comparison."""
    if value is None:
        return None
    s = str(value).strip().lower()
    # Remove leading "the " for location comparisons
    for prefix in ["the "]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s


def score_field(expected, actual) -> float:
    """Score a single field: 1.0 exact, 0.5 fuzzy, 0.0 miss."""
    e = normalize(expected)
    a = normalize(actual)

    # Both null
    if e is None and a is None:
        return 1.0
    # One null, other not
    if e is None or a is None:
        return 0.0
    # Exact match
    if e == a:
        return 1.0
    # Fuzzy match
    ratio = SequenceMatcher(None, e, a).ratio()
    if ratio > 0.8:
        return 0.5
    return 0.0


def parse_json_response(text: str) -> dict | None:
    """Try to extract JSON from model response."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
        return None


def main():
    if PROVIDER not in CALLERS:
        print(f"ERROR: Unknown provider '{PROVIDER}'. Use: gemini, openrouter, anthropic", file=sys.stderr)
        sys.exit(1)

    caller = CALLERS[PROVIDER]

    # Load system prompt
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()

    # Load eval set
    examples = []
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    total_fields = len(examples) * len(FIELDS)
    total_score = 0.0
    exact_matches = 0
    null_correct = 0
    null_total = 0
    parse_errors = 0
    total_input_tokens = 0
    total_output_tokens = 0
    latencies = []
    details = []

    for i, ex in enumerate(examples):
        input_text = ex["input"]
        expected = ex["expected"]

        start_time = time.time()
        try:
            raw_response, in_tok, out_tok = caller(system_prompt, input_text)
            latency = time.time() - start_time
        except Exception as e:
            latency = time.time() - start_time
            raw_response = ""
            in_tok, out_tok = 0, 0
            print(f"  [{i+1}/{len(examples)}] API error: {e}", file=sys.stderr)

        latencies.append(latency)
        total_input_tokens += in_tok
        total_output_tokens += out_tok

        actual = parse_json_response(raw_response)
        # If model returned a list, take the first dict element
        if isinstance(actual, list):
            actual = actual[0] if actual and isinstance(actual[0], dict) else None
        if not isinstance(actual, dict):
            actual = None
        if actual is None:
            parse_errors += 1
            field_scores = {f: 0.0 for f in FIELDS}
            details.append({
                "index": i,
                "input": input_text[:100],
                "expected": expected,
                "actual": None,
                "raw_response": raw_response[:500],
                "field_scores": field_scores,
                "parse_error": True,
            })
            continue

        field_scores = {}
        for field in FIELDS:
            exp_val = expected.get(field)
            act_val = actual.get(field)
            s = score_field(exp_val, act_val)
            field_scores[field] = s
            total_score += s
            if s == 1.0:
                exact_matches += 1
            if exp_val is None:
                null_total += 1
                if act_val is None:
                    null_correct += 1

        details.append({
            "index": i,
            "input": input_text[:100],
            "expected": expected,
            "actual": actual,
            "field_scores": field_scores,
            "parse_error": False,
        })

        # Rate limit courtesy
        if PROVIDER == "gemini":
            time.sleep(0.5)
        else:
            time.sleep(0.1)

    # Calculate metrics
    accuracy = (total_score / total_fields * 100) if total_fields > 0 else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    # Estimate cost
    cost_in, cost_out = COST_TABLE.get(PROVIDER, (0.0, 0.0))
    est_cost = (total_input_tokens / 1000 * cost_in) + (total_output_tokens / 1000 * cost_out)

    # Print greppable summary (matching Karpathy's output style)
    print("---")
    print(f"accuracy:      {accuracy:.2f}")
    print(f"exact_matches: {exact_matches}/{total_fields}")
    print(f"null_correct:  {null_correct}/{null_total}")
    print(f"parse_errors:  {parse_errors}")
    print(f"avg_latency_s: {avg_latency:.2f}")
    print(f"total_tokens:  {total_input_tokens + total_output_tokens}")
    print(f"est_cost_usd:  {est_cost:.4f}")
    print(f"examples:      {len(examples)}")

    # Write detailed results for the optimizer agent to inspect
    with open(LAST_RUN_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "accuracy": round(accuracy, 2),
            "provider": PROVIDER,
            "model": get_model(),
            "details": details,
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed results written to {LAST_RUN_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
