"""FastAPI bridge for the LangGraph data agent."""

import os
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
OUTPUT_DIRS = (ROOT / "data" / "extract", ROOT / "data" / "transform")
_agent_lock = threading.Lock()


class ActivityHandler(BaseCallbackHandler):
    """Collect event labels without recording prompts, arguments, or model output."""

    def __init__(self) -> None:
        self.steps: list[str] = []

    def on_chain_start(self, serialized: dict[str, Any] | None, inputs: dict[str, Any], **kwargs: Any) -> None:
        name = (serialized or {}).get("name") or kwargs.get("name")
        if name:
            self.steps.append(f"Started {name}")

    def on_tool_start(self, serialized: dict[str, Any] | None, input_str: str, **kwargs: Any) -> None:
        name = (serialized or {}).get("name") or "tool"
        self.steps.append(f"Running {name}")

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        self.steps.append("Tool finished")

app = FastAPI(title="Data Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    user_query: str = Field(min_length=1, max_length=10000)
    gemini_api_key: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    answer: str
    steps: list[str]
    files: list[str]


def _message_text(content: Any) -> str:
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


def _csv_snapshot() -> dict[Path, tuple[int, int]]:
    return {
        path.resolve(): (path.stat().st_mtime_ns, path.stat().st_size)
        for folder in OUTPUT_DIRS
        if folder.exists()
        for path in folder.rglob("*.csv")
        if path.is_file()
    }


def _safe_files(candidates: set[Path]) -> list[str]:
    approved: list[str] = []
    for path in sorted(candidates):
        if path.suffix.lower() != ".csv":
            continue
        if any(path.is_relative_to(folder.resolve()) for folder in OUTPUT_DIRS):
            approved.append(path.name)
    return approved


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.gemini_api_key.strip():
        raise HTTPException(status_code=400, detail="Enter a Gemini API key to continue.")

    # The existing graph constructs its Gemini clients during module import and
    # those clients capture the key. Serialize requests while swapping keys.
    with _agent_lock:
        old_gemini_key = os.environ.get("GEMINI_API_KEY")
        old_google_key = os.environ.get("GOOGLE_API_KEY")
        supplied_key = request.gemini_api_key.strip()
        # The Google GenAI client prefers GOOGLE_API_KEY if both variables
        # exist (for example, after loading a project .env file).
        os.environ["GEMINI_API_KEY"] = supplied_key
        os.environ["GOOGLE_API_KEY"] = supplied_key
        try:
            import importlib
            import agents.router_agent as router_agent

            router_agent = importlib.reload(router_agent)
            before = _csv_snapshot()
            activity = ActivityHandler()
            result = router_agent.data_agent.invoke(
                {"messages": [HumanMessage(content=request.user_query)], "route_response": ""},
                config={"callbacks": [activity]},
            )
            messages = result.get("messages", []) if isinstance(result, dict) else getattr(result, "messages", [])
            route = result.get("route_response", "") if isinstance(result, dict) else getattr(result, "route_response", "")
            if route == "error":
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "The router could not classify this request, so no SQL or ETL task ran. "
                        "Check the FastAPI terminal for the Gemini error. Verify that your API key "
                        "is valid and enabled for the configured Gemini model, then retry."
                    ),
                )
            answer = _message_text(messages[-1].content) if messages else "The agent finished without a response."
            after = _csv_snapshot()
            changed = {path for path, signature in after.items() if before.get(path) != signature}
            files = _safe_files(changed)
            steps = ["Classified request" + (f" as {route.upper()}" if route else ""), *activity.steps]
            if not activity.steps:
                steps.append("Executed agent workflow")
            if files:
                steps.append("Found generated CSV output")
            return ChatResponse(answer=answer, steps=steps, files=files)
        except HTTPException:
            raise
        except Exception as exc:
            message = str(exc)
            if any(token in message.lower() for token in ("api key", "api_key", "unauthorized", "permission_denied", "401")):
                raise HTTPException(status_code=401, detail="Gemini rejected the API key. Check the key and try again.") from exc
            raise HTTPException(status_code=502, detail=f"The agent could not complete this request: {message}") from exc
        finally:
            # Restore the server's prior environment instead of retaining the
            # submitted credential or disrupting existing .env configuration.
            if old_gemini_key is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = old_gemini_key
            if old_google_key is None:
                os.environ.pop("GOOGLE_API_KEY", None)
            else:
                os.environ["GOOGLE_API_KEY"] = old_google_key


@app.get("/download/{filename}")
def download(filename: str) -> FileResponse:
    # Accept a basename only; never allow a client supplied path to escape.
    if Path(filename).name != filename or not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files from the data output folders can be downloaded.")
    for folder in OUTPUT_DIRS:
        candidate = (folder / filename).resolve()
        if candidate.is_relative_to(folder.resolve()) and candidate.is_file():
            return FileResponse(candidate, media_type="text/csv", filename=candidate.name)
    raise HTTPException(status_code=404, detail="CSV file not found.")
