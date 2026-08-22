# 项目1：AI智能知识库问答系统

> 简历项目编号 #1 

## 功能

1. 用户上传 PDF/TXT/Markdown 文件
2. 系统自动解析文档、向量化存储
3. 用户自然语言提问，AI 基于文档回答
4. 回答带原文引用来源
5. Web 界面（Streamlit）

## 技术栈

FastAPI + LangChain + ChromaDB + PyMuPDF + Streamlit + DeepSeek API

## 目录结构

```
项目1-知识库问答系统/
├── main.py          # FastAPI 后端
├── app.py           # Streamlit 前端
├── requirements.txt # 依赖清单
├── knowledge/       # 上传的文件存这里
└── chroma_db/       # 向量库
```
