"""
项目1：AI智能知识库问答系统 -- Streamlit 前端
=============================================
启动：streamlit run app.py
前提：FastAPI 后端必须已经在运行（uvicorn main:app --port 8012）
运行方式（需要开两个终端）

  终端 1：FastAPI 后端

  cd /d/Software/CC_EG/1/学习和求职相关/项目1-知识库问答系统
  source venv/Scripts/activate
  export HF_HUB_OFFLINE=1
  export DEEPSEEK_API_KEY="sk-你的Key"
  uvicorn main:app --port 8012

  终端 2：Streamlit 前端

  cd /d/Software/CC_EG/1/学习和求职相关/项目1-知识库问答系统
  source venv/Scripts/activate
  streamlit run app.py

  会自动打开浏览器 → http://localhost:8501
"""
import streamlit as st
import requests

st.set_page_config(page_title="AI知识库问答", page_icon=":books:")
st.title("AI 智能知识库问答系统")

API_URL = "http://127.0.0.1:8012"

# ============================================================
# 左侧边栏：文件上传
# ============================================================

with st.sidebar:
    st.header("[上传] 知识库文件")
    st.caption("支持 PDF / TXT / Markdown")

    uploaded_file = st.file_uploader(
        "选择一个文件",
        type=["pdf", "txt", "md"],
        help="上传后系统自动解析并构建索引",
    )

    if uploaded_file is not None:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        try:
            resp = requests.post(f"{API_URL}/upload", files=files)
            if resp.status_code == 200:
                data = resp.json()
                st.success(f"上传成功! 共 {data['chunks_created']} 个片段")
            else:
                st.error(f"上传失败：{resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("无法连接后端，请先启动 FastAPI 服务。")

    st.divider()

    st.subheader("删除文件")
    try:
        #先拿文件列表
        resp = requests.get(f"{API_URL}/status")
        files = resp.json()['files']
        if files:
            file_to_delete = st.selectbox("选择要删除的文件",files)
            if st.button(f"删除{file_to_delete}"):
                del_resp = requests.delete(f"{API_URL}/files/{file_to_delete}")
                if del_resp.status_code == 200:
                    st.success(del_resp.json()["message"])
                    st.rerun()
                else:
                    st.error(del_resp.text)
        else:
            st.caption("知识库暂无文件")
    except requests.exceptions.ConnectionError:
        st.error("无法连接后端.")


    if st.button("查看知识库状态"):
        try:
            resp = requests.get(f"{API_URL}/status")
            data = resp.json()
            st.info(f"已上传 {data['file_count']} 个文件")
            for f in data["files"]:
                st.text(f"  - {f}")
        except requests.exceptions.ConnectionError:
            st.error("无法连接后端。")


# ============================================================
# 主区域：问答界面
# ============================================================

st.subheader("向知识库提问")

question = st.text_input(
    "输入你的问题",
    placeholder="例如：什么是RAG？它的优势是什么？",
)

col1, col2 = st.columns([1, 4])
with col1:
    ask_button = st.button("提问", type="primary")
with col2:
    temperature = st.slider(
        "创造性",
        0.0, 1.5, 0.3, 0.1,
        help="0=严谨标准  0.7=自然流畅  1.5=天马行空"
    )

if ask_button and question:
    with st.spinner("AI 正在思考..."):
        try:
            resp = requests.post(
                f"{API_URL}/ask",
                json={"question": question, "temperature": temperature},
            )
            if resp.status_code == 200:
                data = resp.json()
                st.markdown("### 回答")
                st.write(data["answer"])

                if data.get("sources"):
                    st.divider()
                    st.caption("参考来源：")
                    for s in data["sources"]:
                        st.caption(f"  - {s}")

                st.caption(f"Token 消耗：{data['tokens_used']}")
            else:
                st.error(f"请求失败：{resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("无法连接后端。请先运行：uvicorn main:app --port 8012")

if not question:
    st.divider()
    st.markdown("""
    **使用方法：**
    1. 先在左侧边栏上传文件（PDF / TXT / Markdown）
    2. 在输入框中输入你的问题
    3. 点击"提问"按钮，AI 会基于你上传的资料回答
    """)
