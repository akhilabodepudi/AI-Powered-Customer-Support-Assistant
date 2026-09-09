from pathlib import Path

from .database import init_db
from .rag import seed_knowledge_base


if __name__ == "__main__":
    init_db()
    total = seed_knowledge_base(Path(__file__).parent.parent / "knowledge_base")
    print(f"Loaded {total} knowledge-base documents")

