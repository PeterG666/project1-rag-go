# 项目1 Day 1：后端 API 搭建

> 📅 2026-08-09 | 🎯 完成文件上传 + 检索问答 API

## 启动命令

```bash
cd /d/Software/CC_EG/1/学习和求职相关/项目1-知识库问答系统
source venv/Scripts/activate
export HF_HUB_OFFLINE=1
export DEEPSEEK_API_KEY="sk-你的Key"
uvicorn main:app --reload --port 8012
```

## 接口一览

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/` | 服务状态 |
| GET | `/status` | 查看已上传文件 |
| POST | `/upload` | 上传文件（PDF/TXT/MD） |
| POST | `/ask` | 向知识库提问 |

## 测试步骤

1. 启动服务 → 打开 http://127.0.0.1:8012/docs
2. GET /status → 确认 knowledge/ 目录下有 knowledge.txt
3. POST /upload → 上传一个新文件（可以先上传一个 TXT）
4. POST /ask → 提一个问题，确认回答带来源引用
5. POST /upload → 再上传一个 PDF 文件（如没有，跳过）
6. POST /ask → 再提问，确认能检索到多个文件的内容

## 本项目新增知识点

- `UploadFile`：FastAPI 的文件上传类型，`await file.read()` 读内容
- `fitz.open()`：PyMuPDF 打开 PDF，`page.get_text()` 提取文字
- `rebuild_vector_store()`：每次上传文件后重建整个向量库（简单直接）
