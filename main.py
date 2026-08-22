"""
项目1：AI智能知识库问答系统 — FastAPI 后端
=============================================
启动：
  source venv/Scripts/activate
  export HF_HUB_OFFLINE=1
  export DEEPSEEK_API_KEY="sk-你的Key"
  uvicorn main:app --reload --port 8012

测试：浏览器打开 http://127.0.0.1:8012/docs
"""

import os, shutil
import chromadb
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ============================================================
# 第 1 块：全局初始化
# ============================================================

app = FastAPI(title="AI知识库问答系统")
API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_BASE = "https://api.deepseek.com"
KNOWLEDGE_DIR = "./knowledge"

os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# ---- 加载 Embedding 模型（启动时一次）----
print("加载 Embedding 模型...")
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

# ---- 文本切分器 ----
splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
)

# ---- 向量库（初始为空，上传文件后才填充）----
vector_store = None       # None 表示还没有创建向量库，启动时不构建，等上传文件后再构建，这叫懒加载


# ============================================================
# 第 2 块：文档处理函数
# ============================================================

def parse_file(file_path: str) -> str:
    """
    解析文件，返回纯文本内容。
    支持 .txt / .md / .pdf
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        import fitz  # PyMuPDF — 只在用到时才 import
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    elif ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    else:
        raise ValueError(f"不支持的文件格式：{ext}。只支持 PDF、TXT、Markdown。")


def _clear_vector_store():
    """清空内存中的旧向量库 + 删除磁盘上的旧 collection"""
    global vector_store
    vector_store = None          # 先让内存里的引用作废
    try:
        _client = chromadb.PersistentClient(path="./chroma_db")
        for _coll in _client.list_collections():
            _client.delete_collection(_coll.name)
    except Exception as e:
        print(f"清理旧向量库警告（可忽略）：{e}")


def rebuild_vector_store():
    """
    重新扫描 knowledge/ 目录下所有文件 → 解析 → 切分 → 向量化 → 存入 ChromaDB。
    每次上传/删除文件后调用此函数。
    """
    global vector_store

    all_chunks = []
    files = [f for f in os.listdir(KNOWLEDGE_DIR) if os.path.isfile(os.path.join(KNOWLEDGE_DIR, f))]

    if not files:
        # 目录空了，也要清空旧向量库！否则会回答已删除文件的内容
        _clear_vector_store()
        return None, "knowledge 目录为空，请先上传文件。"

    for filename in files:
        file_path = os.path.join(KNOWLEDGE_DIR, filename)
        try:
            text = parse_file(file_path)
            chunks = splitter.split_text(text)
            # 给每个 chunk 标记来源文件名
            for c in chunks:
                all_chunks.append(f"[来源：{filename}] {c}")
        except Exception as e:
            print(f"解析 {filename} 失败：{e}")

    if not all_chunks:
        _clear_vector_store()
        return None, "未能从文件中提取到任何文本内容。"

    # 有文件：先清空旧的，再重建新的（避免新旧数据混在一起）
    _clear_vector_store()

    vector_store = Chroma.from_texts(
        texts=all_chunks,
        embedding=embeddings,
        persist_directory="./chroma_db",
        collection_name="knowledge",    # 固定 collection 名，每次重建前删除旧的
    )

    return len(all_chunks), None     # 成功：返回 (片段数, 无错误)


# ============================================================
# 第 3 块：Pydantic 模型
# ============================================================

class AskRequest(BaseModel):
    question: str
    temperature: float = 0.3


# ============================================================
# 第 4 块：API 接口
# ============================================================

@app.get("/")
def root():
    return {
        "message": "AI知识库问答系统已就绪",
        "endpoints": {
            "POST /upload": "上传文件（PDF/TXT/MD）",
            "POST /ask": "向知识库提问",
            "GET /status": "查看知识库状态",
        }
    }


@app.get("/status")
def status():
    """查看知识库当前状态"""
    files = [f for f in os.listdir(KNOWLEDGE_DIR) if os.path.isfile(os.path.join(KNOWLEDGE_DIR, f))]
    return {
        "files": files,
        "file_count": len(files),
        "has_index": vector_store is not None,
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传一个文档到知识库。
    支持 PDF、TXT、Markdown。
    上传后自动重建向量索引。
    """
    # 检查文件类型
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".txt", ".md"]:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式：{ext}。只支持 PDF、TXT、Markdown。"
        )

    # 保存文件到 knowledge/ 目录
    save_path = os.path.join(KNOWLEDGE_DIR, file.filename)
    content = await file.read()  # UploadFile 是 FastAPI 专门处理文件的类型，必须用 await file.read() 拿内容。

    # 先验证：文件内容不能为空（先判断，再写盘，避免留下空文件垃圾）
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空，请检查后重新上传")

    with open(save_path, "wb") as f:
        f.write(content)
    # 重建向量库
    chunk_count, error = rebuild_vector_store()
    if error:
        return {"message": "文件已保存，但索引构建失败", "error": error}

    return {
        "message": f"文件 {file.filename} 上传成功！",
        "chunks_created": chunk_count,
    }



SYSTEM_PROMPT = (
    "你是一个知识库助手。根据以下【参考资料】回答用户问题。\n"
    "规则：\n"
    "1. 如果资料中有答案，基于资料回答，末尾注明[来源：文件名]。\n"
    "2. 如果资料中没有答案，说'知识库中暂无相关信息'，不要编造。\n"
    "3. 用中文回答，简洁清晰。\n\n"
    "【参考资料】\n"
    "{context}"
)

@app.delete("/files/{filename}")
def delete_file(filename: str):
    file_path = os.path.join(KNOWLEDGE_DIR, filename)

    # 先验证：文件存在才删除（先判断，再动手）
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"文件 {filename} 不存在")

    os.remove(file_path)
    rebuild_vector_store()
    return {"message": f"文件 {filename} 已删除"}


@app.post("/ask")
def ask(req: AskRequest):
    """向知识库提问"""
    if vector_store is None:
        # 尝试自动构建
        chunk_count, error = rebuild_vector_store()
        if error:
            raise HTTPException(status_code=400, detail="知识库为空，请先上传文件。")

    # 步骤 1：检索
    related_docs = vector_store.similarity_search(req.question, k=3)

    context_parts = []
    sources = []
    for i, doc in enumerate(related_docs):
        context_parts.append(f"[片段{i+1}] {doc.page_content}")
        # 提取来源信息
        content = doc.page_content
        if content.startswith("[来源："):
            source_name = content.split("]")[0].replace("[来源：", "")
            sources.append(source_name)

    context = "\n\n".join(context_parts)

    # 步骤 2：调用 LLM
    client = OpenAI(api_key=API_KEY, base_url=API_BASE)
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
            {"role": "user", "content": req.question},
        ],
        temperature=req.temperature,
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": list(set(sources)),       # 去重
        "tokens_used": response.usage.total_tokens,
    }
