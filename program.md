# prompt-optimizer

Autonomous prompt engineering optimizer, inspired by Karpathy's autoresearch pattern.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar13`). The branch `prompt-opt/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b prompt-opt/<tag>` from current main/master.
3. **Read the in-scope files**: Read these files for full context:
   - `program.md` — this file, your instructions.
   - `prompt.txt` — the system prompt you will modify. This is the only file you optimize.
   - `eval_set.jsonl` — the evaluation examples with ground truth. Read-only.
   - `evaluate.py` — the evaluation script. Read-only.
   - `resources.md` — accumulated learnings from past experiments. You will update this.
   - `.env` — check that API key is configured for the chosen provider.
4. **Verify setup**: Run `python evaluate.py` to confirm it works and establish the baseline.
5. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
6. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs a full evaluation of the system prompt against 30 test examples. You launch it simply as: `python evaluate.py > run.log 2>&1`.

**What you CAN do:**
- Modify `prompt.txt` — this is the only file you edit. Everything is fair game: instructions, few-shot examples, formatting rules, field definitions, edge case handling, output structure, chain-of-thought, anything.
- Update `resources.md` — append what you learned after each experiment.

**What you CANNOT do:**
- Modify `evaluate.py`. It is read-only.
- Modify `eval_set.jsonl`. It is read-only.
- Install new packages or add dependencies.

**The goal is simple: get the highest accuracy.** Since the eval set is fixed, you need to craft the best possible system prompt. Everything about the prompt is fair game: add examples, add rules, restructure, simplify, or try radically different approaches.

**Simplicity criterion**: All else being equal, simpler prompts are better. A small improvement that adds massive prompt complexity is not worth it. Conversely, removing text and getting equal or better results is a great outcome — that's a simplification win. When evaluating whether to keep a change, weigh the complexity cost against the improvement magnitude. A 0.5% accuracy improvement that adds 500 words of instructions? Probably not worth it. A 0.5% improvement from deleting text? Definitely keep. An improvement of ~0 but much simpler prompt? Keep.

**The first run**: Your very first run should always be to establish the baseline, so you will run the evaluation with the prompt as-is.

## Output format

Once the script finishes it prints a summary like this:

```
---
accuracy:      72.50
exact_matches: 135/180
null_correct:  53/60
parse_errors:  1
avg_latency_s: 1.23
total_tokens:  15234
est_cost_usd:  0.00
examples:      30
```

You can extract the key metric from the log file:

```
grep "^accuracy:" run.log
```

The script also writes `last_run.json` with per-example details (which examples failed, what the model returned vs expected). **Read this file** to understand failure patterns and guide your next experiment.

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated).

The TSV has a header row and 5 columns:

```
commit	accuracy	parse_errors	status	description
```

1. git commit hash (short, 7 chars)
2. accuracy achieved (e.g. 72.50)
3. parse_errors count
4. status: `keep`, `discard`, or `crash`
5. short text description of what this experiment tried

Example:

```
commit	accuracy	parse_errors	status	description
a1b2c3d	52.50	2	keep	baseline
b2c3d4e	68.33	0	keep	added 2 few-shot examples
c3d4e5f	67.50	0	discard	added chain-of-thought reasoning
d4e5f6g	0.00	30	crash	broke JSON output format
```

## The experiment loop

The experiment runs on a dedicated branch (e.g. `prompt-opt/mar13`).

LOOP UNTIL STOPPED:

1. Look at the git state: the current branch/commit we're on.
2. Read `results.tsv` and `resources.md` for context on what's been tried.
3. Read `last_run.json` to understand which specific examples are failing and why. Focus your next change on fixing the most common failure patterns.
4. Hypothesize a change to `prompt.txt`. Write down your hypothesis before making the change.
5. Edit `prompt.txt` with your experimental idea.
6. git commit the change with a descriptive message.
7. Run the experiment: `python evaluate.py > run.log 2>&1` (redirect everything — do NOT use tee or let output flood your context)
8. Read out the results: `grep "^accuracy:\|^parse_errors:" run.log`
9. If the grep output is empty, something crashed. Run `tail -n 50 run.log` to read the error and attempt a fix.
10. Record the results in the TSV (NOTE: do not commit the results.tsv file, leave it untracked by git).
11. If accuracy improved (higher), you "advance" the branch, keeping the git commit. Update `resources.md` with what worked and why.
12. If accuracy is equal or worse, you `git reset --hard HEAD~1` to discard. Update `resources.md` with what didn't work.
13. **Check stop conditions** from `.env`:
    - If `MAX_ITERATIONS` > 0 and you've completed that many experiments → stop.
    - If `MAX_COST_USD` > 0 and cumulative `est_cost_usd` exceeds it → stop.
    - If `PLATEAU_WINDOW` > 0 and the last N experiments all failed to improve → stop.
    - If any stop condition triggers, print a final summary (best accuracy, total experiments, total cost) and exit gracefully.
14. If no stop condition triggered, continue the loop.

The idea is that you are a completely autonomous researcher trying things out. If they work, keep. If they don't, discard. And you're advancing the branch so that you can iterate.

**Timeout**: Each evaluation should take ~30-60 seconds. If a run exceeds 5 minutes, kill it and treat it as a failure.

**Crashes**: If a run crashes, use your judgment: If it's something dumb and easy to fix (e.g. the prompt caused JSON parse errors), fix it and re-run. If the approach itself is fundamentally broken, just skip it, log "crash" as the status, and move on.

**Strategies to try** (in rough order of expected impact):
1. Add 2-3 few-shot examples covering different difficulty levels
2. Add explicit rules for null handling
3. Add date/time normalization instructions
4. Handle edge cases (relative dates, price ranges, canceled events)
5. Add format examples showing exact expected JSON structure
6. Try different prompt structures (detailed vs concise)
7. Handle non-English text
8. Handle non-event text (should return all nulls)
9. Simplification passes — remove text that doesn't help

**NEVER STOP** unless a stop condition from `.env` triggers. Once the experiment loop has begun, do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep, or away from the computer and expects you to continue working autonomously. If you run out of ideas, think harder — re-read `last_run.json` for new failure patterns, try combining previous near-misses, try more radical prompt restructuring. The loop runs until a stop condition triggers or the human interrupts you, period.
