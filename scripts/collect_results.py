import json
import os
import subprocess
import urllib.request

WORK_DIR = "work"

JOB_ID = os.environ["JOB_ID"]
SUBMIT_LOGS_URL = os.environ["SUBMIT_LOGS_URL"]
WORKER_TOKEN = os.environ["WORKER_TOKEN"]


def read_text(path, default=""):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return default


def read_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception:
        return default


def cmd_version(command):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=20,
        )
        return result.stdout.strip()
    except Exception as exc:
        return f"version unavailable: {exc}"


slither_json = read_json(f"{WORK_DIR}/slither-report.json", {})
slither_stdout = read_text(f"{WORK_DIR}/slither.stdout.txt")
slither_stderr = read_text(f"{WORK_DIR}/slither.stderr.txt")
slither_exit = read_text(f"{WORK_DIR}/slither.exitcode", "1").strip()

solhint_json = read_json(f"{WORK_DIR}/solhint-report.json", {})
solhint_text = read_text(f"{WORK_DIR}/solhint-report.txt")
solhint_stderr = read_text(f"{WORK_DIR}/solhint.stderr.txt")
solhint_exit = read_text(f"{WORK_DIR}/solhint.exitcode", "1").strip()

slither_status = "completed" if slither_json else "failed"
solhint_status = "completed" if solhint_json or solhint_text else "failed"

worker_metadata = {
    "worker": "github_actions",
    "job_id": JOB_ID,
    "slither_exit_code": slither_exit,
    "solhint_exit_code": solhint_exit,
    "slither_stderr": slither_stderr[-10000:],
    "solhint_stderr": solhint_stderr[-10000:],
    "slither_version": cmd_version(["slither", "--version"]),
    "solhint_version": cmd_version(["solhint", "--version"]),
    "python_version": cmd_version(["python", "--version"]),
    "node_version": cmd_version(["node", "--version"]),
}

payload = {
    "job_id": JOB_ID,
    "slither_status": slither_status,
    "slither_log_json": json.dumps(slither_json, ensure_ascii=False),
    "slither_log_text": slither_stdout[-100000:],
    "slither_tool_version": worker_metadata["slither_version"],
    "solhint_status": solhint_status,
    "solhint_log_json": json.dumps(solhint_json, ensure_ascii=False),
    "solhint_log_text": solhint_text[-100000:] if solhint_text else solhint_stderr[-100000:],
    "solhint_tool_version": worker_metadata["solhint_version"],
    "worker_metadata_json": json.dumps(worker_metadata, ensure_ascii=False),
    "error": "",
}

data = json.dumps(payload).encode("utf-8")

req = urllib.request.Request(
    SUBMIT_LOGS_URL,
    data=data,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "X-NovaNet-Worker-Token": WORKER_TOKEN,
    },
)

try:
    with urllib.request.urlopen(req, timeout=90) as response:
        print(response.status)
        print(response.read().decode("utf-8", errors="replace"))
except Exception as exc:
    print(f"Failed to submit logs: {exc}")
    raise
