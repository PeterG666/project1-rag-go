# AI 智能知识库问答系统

上传自己的资料，再像聊天一样提问。系统会先从文档里找到相关内容，再交给大模型组织答案，并展示参考文件，方便核对。

这是一个面向 AI 应用开发的个人实践项目，重点是把文档处理、检索、模型调用和 Docker 部署串成一个能实际使用的应用。

## 能做什么

- 上传 PDF、TXT、Markdown 文件，自动解析、切分并建立向量索引。
- 用自然语言提问，回答附带参考文件来源。
- 查看、删除知识库文件，删除后更新索引。
- 通过提示词约束模型：资料里没有答案时，说明未找到相关信息。

## 怎么实现

**技术栈：** Python、FastAPI、Streamlit、LangChain、ChromaDB、PyMuPDF、DeepSeek API、Docker Compose。

```text
上传文档 → 提取文字 → 文本切分 → 向量化并保存
用户提问 → 检索相关片段 → DeepSeek 生成回答 → 展示答案和来源
```

- **检索与生成分开处理**：使用 `BAAI/bge-small-zh-v1.5` 在 CPU 上计算文本向量，ChromaDB 保存和检索向量，DeepSeek 负责回答。
- **前后端分开部署**：Streamlit 提供页面，FastAPI 处理上传和问答，容器之间通过服务名通信。
- **数据不绑在容器里**：文档、向量库文件和模型缓存使用命名数据卷保存；API Key 通过环境变量传入，不写进镜像。

## Docker 运行

需要先启动 Docker，并准备可用的 DeepSeek API Key。以下命令以 **Git Bash** 为例。

### 1. 获取代码并配置 Key

```bash
git clone https://github.com/PeterG666/project1-rag-go.git
cd project1-rag-go
cp -n .env.example .env
```

用编辑器打开 `.env`，填写自己的 Key，不要提交真实 Key：

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 2. 构建两个镜像

当前 Compose 引用本地镜像，需要先完成构建。下面只打包必要文件，也适用于本地中文项目目录：

```bash
tar -cf - .dockerignore Dockerfile.backend requirements.txt main.py | docker build -t rag-backend:v1 -f Dockerfile.backend -
tar -cf - .dockerignore Dockerfile.frontend requirements.frontend.txt app.py | docker build -t rag-frontend:v1 -f Dockerfile.frontend -
```

### 3. 启动服务

两个镜像都构建成功后，先启动后端并查看日志：

```bash
docker compose config --quiet
docker compose up -d --no-build backend
docker compose logs -f --tail 40 backend
```

首次启动需要联网下载 Embedding 模型，之后会保留缓存。看到 `Application startup complete` 后，按 `Ctrl+C` 退出日志跟踪，再启动前端：

```bash
docker compose up -d --no-build frontend
```

- 页面：[http://localhost:18512](http://localhost:18512)
- 接口文档：[http://localhost:18012/docs](http://localhost:18012/docs)

在页面上传一份资料，等待索引建立完成，就可以提问。问答会调用自己的 DeepSeek API 额度。

## 验证与说明

已完成本地手工验证：文档上传、带来源问答、资料外问题提示，以及重新创建容器后不重新上传仍能继续问答。

重启后，首次提问会根据保留的文档重建索引。文档、向量库和模型缓存保存在 Docker 数据卷中，不随 GitHub 代码上传；使用 `docker compose down -v` 会删除这些卷。

目前适合个人本地使用和项目演示，暂未加入登录、用户隔离和自动化评测。
