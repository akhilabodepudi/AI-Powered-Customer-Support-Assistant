import io
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from .config import get_settings
from .database import connect, get_recent_messages, init_db, save_message
from .models import ChatRequest, ChatResponse, DocumentSummary, EscalationRequest, FeedbackRequest, utc_now
from .rag import answer_question, ingest_text, seed_knowledge_base


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with connect() as db:
        empty = db.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"] == 0
    if empty:
        seed_knowledge_base(Path(__file__).parent.parent / "knowledge_base")
    yield


app = FastAPI(
    title="AI Customer Support Assistant API",
    version="1.0.0",
    description="A grounded RAG support assistant with citations, confidence scoring, and human escalation.",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)


def require_admin(x_admin_key: str = Header(default="")) -> None:
    if not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "provider": settings.ai_provider}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    user_message_id = str(uuid.uuid4())
    save_message(user_message_id, conversation_id, "user", payload.message)
    history = get_recent_messages(conversation_id)
    answer, confidence, citations, escalated = answer_question(payload.message, history[:-1])
    assistant_message_id = str(uuid.uuid4())
    save_message(
        assistant_message_id,
        conversation_id,
        "assistant",
        answer,
        {"confidence": confidence, "citations": [c.model_dump() for c in citations], "escalated": escalated},
    )
    return ChatResponse(
        conversation_id=conversation_id,
        message_id=assistant_message_id,
        answer=answer,
        confidence=confidence,
        citations=citations,
        escalated=escalated,
    )


@app.post("/api/feedback", status_code=201)
def feedback(payload: FeedbackRequest) -> dict:
    with connect() as db:
        exists = db.execute("SELECT 1 FROM messages WHERE id = ?", (payload.message_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Message not found")
        db.execute(
            "INSERT OR REPLACE INTO feedback VALUES (?, ?, ?, ?)",
            (payload.message_id, int(payload.helpful), payload.comment, utc_now()),
        )
    return {"status": "recorded"}


@app.post("/api/escalations", status_code=201)
def escalate(payload: EscalationRequest) -> dict:
    escalation_id = str(uuid.uuid4())
    with connect() as db:
        exists = db.execute("SELECT 1 FROM conversations WHERE id = ?", (payload.conversation_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Conversation not found")
        db.execute(
            "INSERT INTO escalations VALUES (?, ?, ?, ?, ?, ?)",
            (escalation_id, payload.conversation_id, payload.email, payload.summary, "open", utc_now()),
        )
    return {"id": escalation_id, "status": "open"}


@app.get("/api/admin/documents", response_model=list[DocumentSummary], dependencies=[Depends(require_admin)])
def list_documents() -> list[dict]:
    with connect() as db:
        rows = db.execute(
            "SELECT d.id, d.title, d.source, d.created_at, COUNT(c.id) AS chunk_count "
            "FROM documents d LEFT JOIN chunks c ON c.document_id = d.id GROUP BY d.id ORDER BY d.created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/admin/documents", status_code=201, dependencies=[Depends(require_admin)])
async def upload_document(file: UploadFile = File(...)) -> dict:
    filename = Path(file.filename or "document.txt").name
    extension = Path(filename).suffix.lower()
    if extension not in {".txt", ".md", ".pdf"}:
        raise HTTPException(status_code=415, detail="Upload a .txt, .md, or .pdf file")
    raw = await file.read(5_000_001)
    if len(raw) > 5_000_000:
        raise HTTPException(status_code=413, detail="File exceeds 5 MB")
    try:
        if extension == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
        else:
            text = raw.decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Could not extract readable text") from exc
    if len(text.strip()) < 20:
        raise HTTPException(status_code=422, detail="Document does not contain enough readable text")
    document_id, chunk_count = ingest_text(Path(filename).stem, filename, text)
    return {"id": document_id, "filename": filename, "chunks": chunk_count}


@app.delete("/api/admin/documents/{document_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_document(document_id: str) -> None:
    with connect() as db:
        cursor = db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Document not found")


@app.get("/api/admin/analytics", dependencies=[Depends(require_admin)])
def analytics() -> dict:
    with connect() as db:
        conversations = db.execute("SELECT COUNT(*) AS n FROM conversations").fetchone()["n"]
        answers = db.execute("SELECT COUNT(*) AS n FROM messages WHERE role = 'assistant'").fetchone()["n"]
        escalations = db.execute("SELECT COUNT(*) AS n FROM escalations").fetchone()["n"]
        feedback_rows = db.execute("SELECT helpful FROM feedback").fetchall()
    helpful = sum(row["helpful"] for row in feedback_rows)
    return {
        "conversations": conversations,
        "answers": answers,
        "escalations": escalations,
        "helpfulness_rate": round(helpful / len(feedback_rows), 3) if feedback_rows else None,
    }

