"""
api/index.py — Vercel Serverless Function Entry Point for CyberSynthetic.
Exports top-level WSGI `app` handler compatible with Vercel Python Serverless Builder (@vercel/python).
"""
import sys
import pathlib
from flask import Flask, jsonify, request

# Ensure root workspace is in sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from engine.plan import Plan
from engine.generate import run_scenario

app = Flask(__name__)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return jsonify({
        "name": "CyberSynthetic Platform API",
        "status": "online",
        "description": "Enterprise Synthetic Data Engine",
        "endpoints": {
            "health": "/api/health",
            "generate": "/api/generate (POST)"
        },
        "message": "For full interactive Streamlit UI, run 'streamlit run app.py' or deploy to Streamlit Community Cloud."
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "platform": "CyberSynthetic",
        "version": "1.0.0"
    })

@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json(force=True) if request.is_json else {}
        seed = int(data.get("seed", 42))
        users = int(data.get("users", 20))
        duration_days = int(data.get("duration_days", 3))
        language = data.get("language", "en")
        difficulty = data.get("difficulty", "medium")

        plan = Plan(
            seed=seed,
            users=users,
            devices=max(1, int(users * 0.7)),
            duration_days=duration_days,
            difficulty=difficulty,
            domains=["auth", "email", "endpoint"],
            language=language,
            use_llm=False,
            generate_documents=False,
        )

        result = run_scenario(plan)
        
        # Format table shapes and scores for JSON response
        table_summary = {
            name: {"rows": len(df), "columns": list(df.columns)}
            for name, df in result["tables"].items()
        }

        return jsonify({
            "status": "success",
            "run_id": result["run_id"],
            "dataset_hash": result["dataset_hash"],
            "tables": table_summary,
            "scores": {k: float(v) for k, v in result.get("scores", {}).items() if isinstance(v, (int, float))}
        })
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500

if __name__ == "__main__":
    app.run(port=5000)
