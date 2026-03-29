from dotenv import load_dotenv
from agent.planner import create_plan
from agent.executor import execute_plan
from agent.validator import validate_results
from agent.responder import build_response

load_dotenv()


def plan_trip(data: dict):

    # Step 1: Plan
    plan = create_plan(data)
    if plan.get("status") == "error":
        return plan

    # Clarification needed — missing required fields
    if plan.get("needs_clarification"):
        return {
            "status": "needs_clarification",
            "message": plan["clarification_message"],
            "missing_fields": plan.get("missing_fields", [])
        }

    # Step 2: Execute
    results = execute_plan(plan, data)

    # Step 3: Validate — on full failure, still build a graceful response
    validated = validate_results(results)
    if validated.get("status") == "error":
        results["errors"].append({"tool": "all", "error": validated["error"]})

    # Step 4: Respond
    response = build_response(plan["city"], results, from_city=plan.get("from_city"))

    return response
