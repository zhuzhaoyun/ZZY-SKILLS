Skills are everywhere. [SkillsBench](https://arxiv.org/html/2602.12670v1) counted over **47,000 unique skills** across 6,300+ repositories. Everyone is writing skills. Almost nobody is testing them and most of them are AI-generated. Skills might get "vibe-checked" with a handful of manual runs, then shipped. You wouldn't ship code without tests, but why ship skills without evals?

This is a practical guide to fixing that. You will learn how to define success criteria, build a lightweight eval harness, and iterate on it. I used the same steps to create and evaluate the [Gemini Interactions API skill](https://github.com/google-gemini/gemini-skills/blob/main/skills/gemini-interactions-api/SKILL.md), taking it from 66.7% to 100% pass rate.

## What Are Agent Skills?

[Agent Skills](https://agentskills.io/home) are folders of instructions, scripts, and resources that augment an agent's capabilities without retraining or fine-tuning the model. Skills follow a **progressive disclosure** pattern and require at minimum a `SKILL.md` file with:

1.  **Frontmatter** (trigger): A `name` and `description` in YAML that the agent uses to decide whether to apply the skill. This is the most important piece — if it's vague, the skill won't trigger reliably.
2.  **Body** (instructions): Markdown guidance for how to perform the task: what APIs to use, what patterns to follow, what to avoid.
3.  **Resources** (optional): `scripts/`, `examples/`, `references/` that the agent can consult during execution.

```
---
name: gemini-interactions-api
description: Use this skill when writing code that calls the Gemini API
  for text generation, multi-turn chat, image generation, streaming responses,
  function calling, structured output, or migrating from generateContent SDK.
---
 
# Gemini Interactions API Skill
 
The Interactions API is a unified interface for interacting with Gemini models
and agents...
```

Skills fall into two categories that matter for testing:

-   **Capability** skills help the agent do something the base model can't do consistently. These may become unnecessary as models improve; evals will tell you when that's happened.
-   **Preference** skills document specific workflows. These are durable, but only as valuable as their fidelity to your actual workflow, and evals verify that fidelity.

## Define Success Before You Write the Skill

Before writing a single eval, write down what "success" means in measurable terms. Grade outcomes, not paths. Agents find creative solutions, and you don't want to penalize an unexpected route to the right answer.

-   **Outcome:** Did the skill produce a usable result? Code compiles, the image rendered, the document got created, the API returned a valid response. This is the baseline. If the output doesn't work, nothing else matters.
-   **Style & Instructions:** Does the output follow your conventions and the skill's directives? Right SDK, correct model IDs, team's naming conventions, the formatting you specified.
-   **Efficiency:** How much time, tokens, and effort did it take? No unnecessary retries, reasonable token count, no command thrashing. This is the most undervalued dimension. Two runs can produce identical correct output, but one burned 3x the tokens. Regressions here are real costs that compound.

For our Interactions API skill, the concrete checks were: correct SDK import (`from google import genai`), current model IDs (not deprecated `gemini-2.0-flash`), uses `interactions.create()` not `generateContent`, and uses `previous_interaction_id` for multi-turn. Most of these are regex-checkable.

## Practical Guide to an Eval Harness

This guide assumes you already have a skill. It won't cover skill creation. Before writing any eval code, trigger the skill manually a few times. Use explicit invocations like `Use the {skill name} to do X` or your agent's built-in trigger (e.g. `/skill {name}`, `$skill-name`). Watch where it breaks. These first runs are not about scoring; they are about surfacing hidden assumptions. Does it assume dependencies that aren't there? Does it skip steps the user would expect?

Every fix you make during manual runs, adding a missing install command, correcting a path, tightening the description, becomes a concrete check you can automate later. Manual iteration is not wasted work.

### 1\. Create a prompt set

For a single skill, **10–20 prompts** are enough to begin with. Each prompt tests a specific scenario and declares its own success criteria:

```
[
  {
    "id": "py_basic_generation",
    "prompt": "Write a Python script that sends a text prompt to Gemini and prints the response.",
    "language": "python",
    "should_trigger": true,
    "expected_checks": ["correct_sdk", "no_old_sdk", "current_model", "interactions_api"]
  },
  {
    "id": "py_deprecated_model",
    "prompt": "Write a Python script using Gemini 2.0 Flash with the Interactions API.",
    "language": "python",
    "should_trigger": true,
    "expected_checks": ["correct_sdk", "interactions_api", "deprecated_model_rejected"]
  },
  {
    "id": "negative_unrelated",
    "prompt": "Write a Python script that reads a CSV and plots a bar chart using matplotlib.",
    "language": "python",
    "should_trigger": false,
    "expected_checks": []
  }
]
```

Each test declares which checks should pass via `expected_checks`. For agents, [each test case may need its own success criteria](https://blog.langchain.com/evaluating-deep-agents-our-learnings/).

I created 17 tests across five categories: core capabilities (7), guardrails for deprecated models (4), extended features not in the skill's inline examples (3), and negative controls (2). Tests span Python (12) and TypeScript (5).

**Important**: Don't skip negative tests. A skill with too-broad description could trigger on every coding prompt.

### 2\. Run the agent and capture output

Test the skill the same way the agent experiences it, e.g. through the CLI. In our case we used Gemini CLI inside a python script.

```
def run_gemini_cli(prompt):
    cmd = [
        "gemini",
        "-m", "gemini-3-flash-preview",
        "--output-format", "json",
        "--yolo",
        "-p", prompt,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    data = json.loads(result.stdout.strip())
    return CLIOutput(
        response_text=data.get("response", ""),
        stats=data.get("stats", {}),
        exit_code=result.returncode,
    )
```

### 3\. Write deterministic checks

Each check becomes a small function, using regex against the extracted code, returning a boolean.

```
# Does the code use the correct SDK?
def check_correct_sdk(code, language):
    if language == "python":
        return bool(re.search(r"from\s+google\s+import\s+genai", code))
    return bool(re.search(r"""['"]@google/genai['"]""", code))
 
# Does the code use a current model?
DEPRECATED_MODELS = ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
 
def check_current_model(code, language):
    return not any(model in code for model in DEPRECATED_MODELS)
```

Register all checks that the harness can dispatch by `check_id` from the prompt set, then loop through each test case:

```
CHECK_REGISTRY = {
    "correct_sdk":       check_correct_sdk,
    "current_model":     check_current_model,
    "interactions_api":  check_interactions_api,
    "no_old_sdk":        check_no_old_sdk,
    # ... 11 checks total
}
 
def run_eval(test_case):
    output = run_gemini_cli(test_case["prompt"])
    code = extract_code_blocks(output.response_text)
 
    results = {}
    for check_id in test_case["expected_checks"]:
        results[check_id] = CHECK_REGISTRY[check_id](code, test_case["language"])
    return results
```

We iterated on the Interactions API skill across ~20 test cases going from **66.7% → 100%** pass rate. The two fixes that mattered most were rewriting the skill description to better match user intent (not API terminology) and replacing passive deprecation warnings with explicit instructions. The description change alone fixed 5 of 7 failures.

### 4\. Add LLM-as-judge for qualitative checks

_Note: We didn't use LLM-as-judge for the Interactions API skill._

Skills may require qualitative checks, such as code structure, naming conventions, design quality, or whether the output follows the intended patterns. These are hard to capture with regex or file existence checks alone. For example, the [frontend-design skill](https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design/skills/frontend-design) demands "distinctive, production-grade interfaces". For such skills, you can use a second model-assisted pass.

Use structured output to constrain the LLM's response to a typed schema so that results become parseable and trackable.

```
from google import genai
from pydantic import BaseModel, Field
 
client = genai.Client()
 
class CheckResult(BaseModel):
    passed: bool
    notes: str = Field(description="Brief explanation of the assessment.")
 
class DesignEvalResult(BaseModel):
    overall_pass: bool
    score: int = Field(ge=0, le=100)
    typography: CheckResult = Field(
        description="Uses distinctive fonts, avoids generic choices like Inter/Arial/Roboto.")
    color_cohesion: CheckResult = Field(
        description="Cohesive palette with CSS variables, no timid evenly-distributed colors.")
    layout: CheckResult = Field(
        description="Intentional spatial composition — asymmetry, overlap, or bold grid choices.")
    generic_ai_avoidance: CheckResult = Field(
        description="No purple-gradient-on-white, no cookie-cutter patterns.")
 
code_to_grade = open("./output/landing-page.html").read()
 
interaction = client.interactions.create(
    model="gemini-3-flash-preview",
    input=f"""Evaluate this frontend code against these requirements:
- Has distinctive, production-grade interfaces.
- No generic fonts (Inter, Roboto, Arial),
- No clichéd color schemes (purple gradients on white), and predictable layouts.
 
    Grade each dimension and provide an overall score.
 
    Code:
    {code_to_grade}""",
    response_format=DesignEvalResult.model_json_schema(),
)
 
result = DesignEvalResult.model_validate_json(interaction.outputs[-1].text)
print(f"Score: {result.score}/100")
for name in ["typography", "color_cohesion", "layout", "generic_ai_avoidance"]:
    check = getattr(result, name)
    print(f"  {name}: {'✓' if check.passed else '✗'} — {check.notes}")
```

Use LLM grading selectively since deterministic checks are fast, while LLM grading adds cost and latency.

## Best Practices for Evaluating Agent Skills

1.  **Start with the skill description.** The name and description are the trigger mechanism. A vague description means the skill won't be used when it should, or when it shouldn't.
2.  **Use directives, not information.** Models follow instructions better than they infer implications. "Always use `interactions.create()`" works. "The Interactions API is the recommended approach" doesn't.
3.  **Include negative tests.** Add prompts where the skill should _not_ trigger. A skill with too-broad keywords will be used on every request.
4.  **Start small, extend from failures.** Begin with 10–20 prompts drawn from real usage. Every user-reported wrong output becomes a new test case.
5.  **Grade outcomes, not paths.** Agents find creative solutions. Don't penalize an unexpected route to the right answer.
6.  **Isolate each run.** Use a clean environment for every test case. Accumulated context can bleed between test cases and masks real failures.
7.  **Run multiple trials.** Agent behavior is nondeterministic. A single pass/fail per prompt isn't enough signal, run 3–5 trials per case and look at the distribution, not just one result.
8.  **Test across harnesses.** The same skill can behave differently depending on the agent framework running it. If your skill is used across tools, eval it in each one.
9.  **Graduate your evals.** Capability evals start at a low pass rate and give you a hill to climb. Once they hit ~100%, they graduate into regression evals that protect against backsliding.
10.  **Detect skill retirement.** Run your evals with the skill unloaded. If they still pass, the model has absorbed the skill's value. Retire it.

## Other Resources

If you want to go deeper, here are more resources:

-   [Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
-   [Improving Skill-Creator](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills)
-   [Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills)
-   [Evaluating Deep Agents](https://blog.langchain.com/evaluating-deep-agents-our-learnings/)
-   [SkillsBench](https://arxiv.org/html/2602.12670v1)
-   [Skills for Evaluating AI Products](https://hamel.dev/blog/posts/evals-skills/)

___

Thanks for reading! If you have any questions or feedback, please let me know on [Twitter](https://twitter.com/_philschmid) or [LinkedIn](https://www.linkedin.com/in/philipp-schmid-a6a2bb196/).