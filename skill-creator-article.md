# Why Does Your Skill Always Underperform? How to Iteratively Optimize Your Skill?

**Have you ever encountered these situations?**
- You spent a whole day writing a Skill, but it underperformed after launching?
- The functionality was implemented, but the AI couldn't consistently output the desired results?
- After tweaking for hours, the effect actually got worse?

**The root cause isn't that your Skill is written incorrectly—it's that you lack a systematic evaluation and iteration method.**

Today, we'll build an **automated Skill evaluation system** from scratch, step by step.

---

## 1. Starting from a Problem

Let's say you wrote a "Construction Design Specification Generation" Skill. You wanted it to:
- Automatically generate complete design specification documents based on user input
- Output in standardized format with complete content
- Avoid missing key sections

You confidently tested a few cases, only to find:
- Case A: Generated document missing the "Structural Design" section
- Case B: Format was correct, but key data was wrong
- Case C: Completely correct

**You're confused—is this Skill actually working or not?**

---

## 2. What Is Your Evaluation Method?

Most people's evaluation method is:

```
Write Skill → Test a few cases → Judge by feeling → Tweak → Test more → Feels about right → Launch
```

This approach has several critical problems:

| Problem | Description |
|---------|-------------|
| **Sample size too small** | 3-5 cases can't possibly cover various edge cases |
| **Subjective judgment** | "Feels about right" is not an objective standard |
| **No regression testing** | Fixing A might introduce B |
| **Can't quantify progress** | How much better is this version than the last? |

---

## 3. Step 1: Define "Success Criteria"

Before starting evaluation, we need to define **what good Skill output looks like**.

For the "Construction Design Specification Generation" Skill, success criteria might be:

```
1. Document contains all necessary sections (structural, electrical, plumbing, etc.)
2. Each section has substantive content (not just empty framework)
3. Data is consistent with user input
4. Format meets standards (heading hierarchy, numbering rules, etc.)
5. Total word count is within reasonable range (2000-5000 words)
```

These standards are called **Assertions** in the Skill Creator system.

### How to Write Assertions

```json
{
  "assertions": [
    {
      "text": "Output document contains 'Structural Design' section",
      "type": "content"
    },
    {
      "text": "Output document contains 'Electrical Design' section",
      "type": "content"
    },
    {
      "text": "Structural Design section exceeds 200 words",
      "type": "quality"
    },
    {
      "text": "Project name matches user input",
      "type": "accuracy"
    }
  ]
}
```

---

## 4. Step 2: Design Test Cases

**The quality of your test cases directly determines the quality of your Skill.**

Good test cases look like this:

```
❌ Bad example:
"Generate a design specification"

✅ Good example:
"I need a design specification for an office building project located in Chaoyang District, Beijing, with a total floor area of 12,000 square meters, 8 floors above ground, 2 floors underground, primarily for office and conference use."
```

Good test cases should:
- **Be specific**: Include specific values, locations, functional requirements
- **Be diverse**: Cover different types (residential/office/commercial), different scales
- **Be challenging**: Include edge cases (large scale, special requirements, etc.)

### Number of Test Cases

Ideally, each Skill should have **8-20 test cases** prepared.

```
eval-0: Beijing Chaoyang office building, 8 floors, 12000㎡
eval-1: Shanghai residential project, 6 floors above ground, 8000㎡
eval-2: Guangzhou shopping mall, 4 floors above ground, 2 underground, 25000㎡
eval-3: Shenzhen factory building, steel structure, 30000㎡
... (continue adding based on actual situation)
```

---

## 5. Step 3: Establish Control Experiments

**Question: How do you know the Skill is actually useful, rather than the AI just being good at it?**

The answer: **Control experiments**.

For each test case, we run two versions simultaneously:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Test Case: "Beijing Chaoyang Office Building Spec"        │
│                                                             │
│   ┌─────────────────────┐    ┌─────────────────────┐      │
│   │   with_skill        │    │   without_skill     │      │
│   │   (using Skill)     │    │   (without Skill)   │      │
│   └─────────────────────┘    └─────────────────────┘      │
│                                                             │
│   Compare the quality difference between outputs             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

If the with_skill version is significantly better, the Skill is truly effective.

---

## 6. Step 4: Let the Machine "Grade Papers"

Now the question:

> **You have 16 test cases, each with 2 versions (with/without), totaling 32 outputs.**
> **Are you going to check them all manually?**

This is where **Grader (Grading Agent)** comes in.

### What Is Grader?

Grader is a specialized evaluation Agent that:

1. Reads test outputs
2. Checks against preset Assertions one by one
3. Gives PASS/FAIL judgment with evidence

```
Test Runner Output
       │
       ▼
┌─────────────────────────────┐
│         Grader              │
│                             │
│  Assertion Checks:          │
│  ✓ Has structural section → PASS
│  ✓ Has electrical section → PASS
│  ✓ Word count > 200 → PASS │
│  ✗ Data consistency → FAIL  │
│                             │
│  → grading.json            │
└─────────────────────────────┘
```

### Grader's Evaluation Criteria

| Result | Condition |
|--------|----------|
| **PASS** | Clear evidence exists, AND it's genuine task completion, not superficial compliance |
| **FAIL** | No evidence, evidence contradicts, or superficial compliance with wrong content |

**Note: Grader does not give "partial pass"—each Assertion is either 0 or 1.**

### How to Build Grader?

Grader is essentially an **Agent Definition File**—a `.md` file describing what the Grader Agent should do.

#### 1. Create Grader Definition File

Create `agents/grader.md` in your Skill directory:

```markdown
# Grader Agent

Evaluate expectations against an execution transcript and outputs.

## Role

The Grader reviews a transcript and output files, then determines whether each expectation passes or fails. Provide clear evidence for each judgment.

You have two jobs: grade the outputs, and critique the evals themselves.

## Inputs

You receive these parameters in your prompt:

- **expectations**: List of expectations to evaluate (strings)
- **transcript_path**: Path to the execution transcript (markdown file)
- **outputs_dir**: Directory containing output files from execution

## Process

### Step 1: Read the Transcript

1. Read the transcript file completely
2. Note the eval prompt, execution steps, and final result
3. Identify any issues or errors documented

### Step 2: Examine Output Files

1. List files in outputs_dir
2. Read/examine each file relevant to the expectations
3. Note contents, structure, and quality

### Step 3: Evaluate Each Assertion

For each expectation:

1. **Search for evidence** in the transcript and outputs
2. **Determine verdict**:
   - **PASS**: Clear evidence the expectation is true AND reflects genuine task completion
   - **FAIL**: No evidence, or evidence contradicts, or superficial compliance
3. **Cite the evidence**: Quote the specific text or describe what you found

### Step 4: Write Grading Results

Save results to `{outputs_dir}/../grading.json`.

## Output Format

```json
{
  "expectations": [
    {
      "text": "The output includes the name 'John Smith'",
      "passed": true,
      "evidence": "Found in transcript: 'Extracted names: John Smith...'"
    }
  ],
  "summary": {
    "passed": 2,
    "failed": 1,
    "pass_rate": 0.67
  }
}
```
```

#### 2. Launch Grader Agent

Use the **Agent tool** in your main flow to launch Grader:

```python
# Pseudocode, actually executed in Claude Code
Agent(
    subagent_type="general-purpose",
    prompt=f"""Read agents/grader.md and evaluate the outputs.

    Parameters:
    - expectations: {assertions_list}
    - transcript_path: {workspace}/iteration-1/eval-0/with_skill/transcript.md
    - outputs_dir: {workspace}/iteration-1/eval-0/with_skill/outputs/

    Save grading.json to {workspace}/iteration-1/eval-0/with_skill/grading.json
    """
)
```

#### 3. Grader's Core Logic

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Inputs:                                                    │
│  - expectations: ["Has structural section", "Has electrical", ...]
│  - transcript: Complete record of Test Runner execution     │
│  - outputs: Generated document files                       │
│                                                             │
│  Flow:                                                      │
│  1. Read transcript, understand task and execution steps   │
│  2. Read outputs, check actual content                     │
│  3. Find evidence for each assertion                       │
│  4. Judge PASS/FAIL, cite evidence                         │
│                                                             │
│  Output: grading.json                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Step 5: Aggregate Data, Discover Patterns

Single test case results aren't enough—we need **overall analysis**.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   eval-0/grading.json  ─┐                                   │
│   eval-1/grading.json  ─┼─→ Aggregation ─→ benchmark.json  │
│   eval-2/grading.json  ─┤              │                    │
│   ...                   ─┘              │                    │
│                                         ▼                    │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  Benchmark Summary Report                            │  │
│   │                                                       │  │
│   │  with_skill pass rate:     87.5% ± 8.2%             │  │
│   │  without_skill pass rate:  35.0% ± 12.1%           │  │
│   │                                                       │  │
│   │  Delta: +52.5%                                        │  │
│   │                                                       │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

That's not enough—we also need **Analyzer (Analysis Agent)** to discover hidden issues.

### What Can Analyzer Discover?

```
┌─────────────────────────────────────────────────────────────┐
│  Analyzer Analysis Results:                                  │
│                                                             │
│  1. "Has structural section" passes in both configs →       │
│     Cannot differentiate Skill value, may need stricter      │
│     assertions                                              │
│                                                             │
│  2. "Data consistency" without_skill pass rate only 20% → │
│     Skill genuinely adds value here                         │
│                                                             │
│  3. eval-3 (Beijing factory) has high variance (60%±30%) →│
│     May be unstable, needs more testing                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### How to Build Analyzer?

#### 1. Create Analyzer Definition File

Create `agents/analyzer.md` in your Skill directory:

```markdown
# Post-hoc Analyzer Agent

Analyze benchmark results to understand patterns and anomalies.

## Role

Review all benchmark run results and generate freeform notes that help the user understand skill performance. Focus on patterns that wouldn't be visible from aggregate metrics alone.

## Inputs

You receive these parameters in your prompt:

- **benchmark_data_path**: Path to benchmark.json with all run results
- **skill_path**: Path to the skill being benchmarked
- **output_path**: Where to save the notes

## Process

### Step 1: Read Benchmark Data

1. Read the benchmark.json containing all run results
2. Note the configurations tested (with_skill, without_skill)
3. Understand the run_summary aggregates already calculated

### Step 2: Analyze Per-Assertion Patterns

For each expectation across all runs:
- Does it **always pass** in both configurations?
- Does it **always fail** in both configurations?
- Does it **pass with skill but fail without**?
- Is it **highly variable**?

### Step 3: Analyze Cross-Eval Patterns

- Are certain eval types consistently harder/easier?
- Do some evals show high variance while others are stable?
- Are there surprising results that contradict expectations?

### Step 4: Analyze Metrics Patterns

- Does the skill significantly increase execution time?
- Is there high variance in resource usage?
- Are there outlier runs?

### Step 5: Generate Notes

Write freeform observations as a list of strings.

### Step 6: Write Notes

Save notes to `{output_path}` as a JSON array:

```json
[
  "Assertion 'X' passes 100% in both - may not differentiate skill",
  "Eval 3 shows high variance (50% ± 40%)",
  "Without-skill fails consistently on table extraction"
]
```

## Guidelines

- **DO**: Report what you observe in the data
- **DO NOT**: Suggest improvements to the skill
- **DO NOT**: Make subjective quality judgments
```

#### 2. Launch Analyzer Agent

```python
# Pseudocode
Agent(
    subagent_type="general-purpose",
    prompt=f"""Read agents/analyzer.md and analyze the benchmark results.

    Parameters:
    - benchmark_data_path: {workspace}/iteration-1/benchmark.json
    - skill_path: /path/to/construction-design-spec/
    - output_path: {workspace}/iteration-1/analyst_notes.json

    Read benchmark.json, analyze patterns, and save notes.
    """
)
```

#### 3. Analyzer's Core Logic

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Inputs:                                                    │
│  - benchmark.json (aggregated all test results)             │
│  - skill_path (path to the skill under test)               │
│                                                             │
│  Analysis Dimensions:                                       │
│  1. Per-Assertion: Each assertion's performance with/without│
│  2. Cross-Eval: Pattern differences between test cases      │
│  3. Metrics: Time, token consumption anomalies             │
│                                                             │
│  Output:                                                    │
│  - analyst_notes.json (list of insights)                    │
│                                                             │
│  Example Insights:                                          │
│  - "'Output is PDF' passes in both configs, can't          │
│     differentiate value"                                    │
│  - "eval-3 has high variance (60%±30%), may be unstable"  │
│  - "Skill adds clear value on data accuracy (+52%)"        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Step 6: Human Review, Prevent Machine Errors

Even the most accurate machine grading can have omissions.

This is why we need **HTML Viewer**—letting humans do the final check.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  Test Case: eval-0 Beijing Chaoyang Office          │  │
│   │                                                     │  │
│   │  Prompt: Generate an office building spec...        │  │
│   │                                                     │  │
│   │  with_skill output: [rendered document preview]    │  │
│   │                                                     │  │
│   │  without_skill output: [rendered document preview] │  │
│   │                                                     │  │
│   │  Machine grade: PASS (4/5 assertions)               │  │
│   │                                                     │  │
│   │  Your feedback: ____________________________       │  │
│   │                                                     │  │
│   │                          [Prev] [Next]              │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Users can:
- Visually compare with/without output differences
- Leave specific feedback: "The data in paragraph 3 is wrong"
- Decide whether the Skill meets launch standards

### Generating HTML Viewer

```python
# Run generation script
bash generate_review.py \
    /path/to/workspace/iteration-1 \
    --skill-name "construction-design-spec" \
    --benchmark /path/to/benchmark.json \
    --static /tmp/review.html

# Then open browser
open /tmp/review.html
```

---

## 9. Step 7: Closed-Loop Iteration

Based on user feedback, we know where the Skill needs improvement.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   User Feedback:                                            │
│   "Missing 'Green Building Design' section, it's trending" │
│   "Basement waterproofing description is too brief"         │
│                                                             │
│        ↓                                                   │
│                                                             │
│   Modify SKILL.md:                                          │
│   - Add 'Green Building Design' to section checklist        │
│   - Expand basement waterproofing content requirements      │
│                                                             │
│        ↓                                                   │
│                                                             │
│   Rerun all tests (regression testing)                     │
│                                                             │
│        ↓                                                   │
│                                                             │
│   Benchmark comparison:                                      │
│   Old version pass rate: 87.5%                              │
│   New version pass rate: 91.2%  (+3.7%)                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Iteration Loop:**
```
Test → Grade → Aggregate → Analyze → User Feedback → Improve → Retest → ...
```

Continue until:
- All user feedback is empty (everything looks OK)
- Pass rate reaches target (e.g., 90%+)
- No significant improvement for 2-3 consecutive rounds

---

## 10. Complete Agent Collaboration Flow

With all that said, how does our evaluation system run automatically?

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Main Agent                         │   │
│  │              (Main Flow Coordinator)                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                               │
│        ┌───────────────────┼───────────────────┐           │
│        │                   │                   │           │
│        ▼                   ▼                   ▼           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │ Test Runner │    │ Test Runner │    │ Test Runner │   │
│  │ (with)      │    │ (with)      │    │ (with)      │   │
│  └─────────────┘    └─────────────┘    └─────────────┘   │
│        │                   │                   │           │
│        ▼                   ▼                   ▼           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │ Test Runner │    │ Test Runner │    │ Test Runner │   │
│  │(without)    │    │(without)    │    │(without)    │   │
│  └─────────────┘    └─────────────┘    └─────────────┘   │
│        │                   │                   │           │
│        └───────────────────┼───────────────────┘           │
│                            │  Complete                    │
│                            ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Grader Agents (Grading)                  │   │
│  │   Defined by agents/grader.md                         │   │
│  │   Each output → grading.json                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                               │
│                            ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         aggregate_benchmark.py (Aggregation Script)   │   │
│  │   All grading.json → benchmark.json                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                               │
│                            ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Analyzer Agent (Analysis)                   │   │
│  │   Defined by agents/analyzer.md                       │   │
│  │   benchmark → pattern insights                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                               │
│                            ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          generate_review.py → HTML Viewer             │   │
│  │   Display to user for review                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                               │
│                            ▼                               │
│                     User Feedback                          │
│                            │                               │
│                            ▼                               │
│                   Improve SKILL.md                         │
│                            │                               │
│                            └─────────────────────────────  │
│                                         Loop               │
└─────────────────────────────────────────────────────────────┘
```

### How Many Agents Are Involved?

Using 8 test cases as an example:

| Stage | Agent/Tool | Count |
|-------|-----------|-------|
| Test Execution | Test Runner | 16 |
| Grading | Grader | 16 |
| Analysis | Analyzer | 1 |
| **Total** | | **33+** |

Plus Main Agent coordination at various stages, **one evaluation involves nearly 40 Agent collaborations**.

---

## 11. Why Do We Need So Many Agents?

| Design | Reason |
|--------|--------|
| **Test Runner Parallel** | 16 tests run simultaneously, saving time |
| **Grader Independent** | Avoid Main Agent bias when grading |
| **Scripts for Aggregation** | Simple calculations don't need LLM, saving tokens |
| **Analyzer Optional** | Can skip for simple scenarios |
| **Human Final Review** | Machine grading may have omissions, humans check |

---

## 12. Skill File Structure Summary

At this point, we can summarize a **complete Skill evaluation system file structure**:

```
my-skill/
├── SKILL.md                    # Main flow definition
├── agents/
│   ├── grader.md              # ⭐ Grader Agent definition
│   └── analyzer.md            # ⭐ Analyzer Agent definition
├── scripts/
│   ├── aggregate_benchmark.py  # Aggregation script
│   └── generate_review.py     # HTML generation script
├── evals/
│   └── evals.json             # Test cases + assertions
└── references/
    └── schemas.md             # Data structure definitions
```

---

## 13. Congratulations!

**You have now mastered a complete Skill iterative optimization method.**

This method helps you:
- ✅ Systematically evaluate Skill effectiveness, no more guessing
- ✅ Speak with data, quantify improvement results
- ✅ Automate most evaluation work, save time and effort
- ✅ Discover hidden issues, regression testing prevents degradation
- ✅ Make Skills output stably across various edge cases

**More importantly, you learned how to build:**
- ✅ **Grader Agent** - Grade outputs against assertions
- ✅ **Analyzer Agent** - Analyze benchmark data patterns
- ✅ **Complete Agent Collaboration Flow** - How Main Agent coordinates dozens of Agents

---

## Next Steps

If you want to practice hands-on:

1. **Create your first Skill directory structure**
2. **Write agents/grader.md** - Define your Grader logic
3. **Write agents/analyzer.md** - Define your Analyzer logic
4. **Prepare evals/evals.json** - Prepare test cases and assertions
5. **Run in Claude Code** - Start the testing loop

---

**Remember: A good Skill is not written out—it's tested out, and iteratively refined.**

---

*If you found this article useful, feel free to share it with your friends.*
