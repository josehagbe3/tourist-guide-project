def validate_results(results: dict):
    # simple validation for now
    if not results["data"]:
        return {"error": "No valid data collected", "status": "error"}

    return {"status": "success", "results": results}