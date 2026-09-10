#!/usr/bin/env python3
"""Start a Skill Run on the compose stack and follow it, the way the agent will.

    python skill_run.py clinical-data-integration drug_name=Lutathera
    python skill_run.py rare-disease-diagnosis 'symptoms=["hepatosplenomegaly","coarse facies"]'

Polls `status` and prints a line per step boundary. When the run asks a question
(a repair or a judgement), it is printed and answered from stdin as JSON — or,
with --auto, with a placeholder, which is enough to prove the plumbing. The bundle
is printed at the end. Reads the process from the packaged YAML until DSR-709
lands the GraphDB loader.
"""
import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from temporalio.client import Client  # noqa: E402

from tooluniverse.skill_graph import load_graph  # noqa: E402
from tooluniverse.skill_workflow import TASK_QUEUE, SkillRunInput, SkillWorkflow  # noqa: E402


def _value(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill")
    ap.add_argument("inputs", nargs="*", help="name=value (value may be JSON)")
    ap.add_argument("--address", default="127.0.0.1:7233")
    ap.add_argument("--namespace", default="skills")
    ap.add_argument("--auto", action="store_true", help="answer questions with placeholders")
    args = ap.parse_args()

    process = load_graph(args.skill)
    inputs = {k: _value(v) for k, v in (kv.split("=", 1) for kv in args.inputs)}
    client = await Client.connect(args.address, namespace=args.namespace)
    run_id = f"skill-{args.skill}-{uuid.uuid4().hex[:8]}"
    handle = await client.start_workflow(
        SkillWorkflow.run,
        SkillRunInput(skill=args.skill, process=process, inputs=inputs),
        id=run_id, task_queue=TASK_QUEUE)
    print(f"started {run_id}  (UI: http://127.0.0.1:8233/namespaces/{args.namespace}/workflows/{run_id})")

    seen = None
    while True:
        state = await handle.query(SkillWorkflow.status)
        if state["finished"]:
            break
        tick = (state["step_id"], len(state["done"]))
        if tick != seen:
            seen = tick
            print(f"  step {state['step_id']}: {state['step_label']}  "
                  f"({len(state['done'])} done, {state['remaining']} remaining)")
        question = state["waiting_for"]
        if question:
            print(f"  ? {question['kind']} at {question['step']} wants {question['wants']}")
            if args.auto:
                answer = {n: ["placeholder"] for n in question["wants"]}
            else:
                answer = json.loads(input("  answer (JSON): "))
            await handle.signal(SkillWorkflow.answer, answer)
        await asyncio.sleep(1)

    bundle = await handle.result()
    print(json.dumps({k: bundle[k] for k in ("steps_done", "failures", "blocked", "unresolved")},
                     indent=1))
    print(f"facts: {json.dumps(bundle['facts'], default=str)[:600]}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
