from pathlib import Path
import chromadb
from openai import OpenAI
from . import config
KB_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"
DB_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma"

_client: OpenAI | None = None

def _embedding(texts:list[str])->list[list[float]]:
    global _client
    if _client is None:
        _client=OpenAI(
            api_key=config.EMBEDDING_API_KEY,
            base_url=config.EMBEDDING_BASE_URL,
        )
    resp=_client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in resp.data]

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """按空行分段，段落到 size 左右合成一块，块之间留 overlap 字重叠。"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""

    for para in paragraphs:
        # 单段就超长：先存掉手上的，再把这段硬切
        if len(para) > size:
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(para), size - overlap):
                chunks.append(para[i : i + size])
            continue

        if len(buf) + len(para) <= size:
            buf = f"{buf}\n\n{para}" if buf else para
            continue

        chunks.append(buf)
        tail = chunks[-1][-overlap:]
        buf = f"{tail}\n\n{para}"

    if buf:
        chunks.append(buf)
    return chunks

def build_index() -> int:
    """读取知识库目录下所有 md，切片、向量化、写入 Chroma。返回块数。"""
    client = chromadb.PersistentClient(path=str(DB_DIR))
    col = client.get_or_create_collection("psychology")

    old = col.get()
    if old["ids"]:
        col.delete(ids=old["ids"])

    total = 0
    for md in sorted(KB_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        chunks = split_text(text)
        col.add(
            ids=[f"{md.stem}-{i}" for i in range(len(chunks))],
            documents=chunks,
            embeddings=_embedding(chunks),
            metadatas=[{"source": md.name} for _ in chunks],
        )
        total += len(chunks)
        print(f"{md.name}: {len(chunks)} 块")

    print(f"入库完成，共 {total} 块")
    return total

def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """检索与 query 最相关的 top_k 个片段。"""
    client = chromadb.PersistentClient(path=str(DB_DIR))
    col = client.get_or_create_collection("psychology")

    result = col.query(
        query_embeddings=_embedding([query]),
        n_results=top_k,
    )

    hits = []
    for doc, meta, dist in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        hits.append({"text": doc, "source": meta["source"], "distance": dist})
    return hits

if __name__ == "__main__":
    build_index()