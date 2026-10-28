import os

import requests
import streamlit as st

API_URL = os.getenv("DATA_AGENT_API_URL", "http://localhost:8000")

st.set_page_config(page_title="Data Agent", page_icon="📊", layout="wide")
st.title("📊 Data Agent")
st.caption("Ask for data extraction, CSV transformations, or SQL analysis.")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Gemini API Key", type="password", help="Used for this session's requests and not stored by the app.")
    st.caption("Your key is sent to the local API server only when you submit a message.")

if "chat" not in st.session_state:
    st.session_state.chat = []

for item in st.session_state.chat:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        if item.get("steps"):
            with st.expander("Agent activity"):
                for step in item["steps"]:
                    st.write(f"• {step}")
        for filename in item.get("files", []):
            try:
                response = requests.get(f"{API_URL}/download/{filename}", timeout=30)
                response.raise_for_status()
                st.download_button(
                    "⬇️ Download CSV", response.content, file_name=filename,
                    mime="text/csv", key=f"download-{item.get('id', '')}-{filename}",
                    use_container_width=True,
                )
            except requests.RequestException:
                st.error(f"Could not retrieve {filename} from the API server.")

query = st.chat_input("What would you like to do with your data?")
if query:
    st.session_state.chat.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        if not api_key.strip():
            answer = "Add your Gemini API key in Settings before sending a request."
            st.error(answer)
            st.session_state.chat.append({"role": "assistant", "content": answer})
        else:
            with st.spinner("The agent is working…"):
                try:
                    response = requests.post(
                        f"{API_URL}/chat",
                        json={"user_query": query, "gemini_api_key": api_key},
                        # ETL can take several minutes while the graph retries
                        # a transient Gemini/API error or processes a dataset.
                        timeout=(10, 900),
                    )
                    response.raise_for_status()
                    payload = response.json()
                    answer = payload.get("answer", "No response returned.")
                    st.markdown(answer)
                    if payload.get("steps"):
                        with st.expander("Agent activity", expanded=True):
                            for step in payload["steps"]:
                                st.write(f"• {step}")
                    files = payload.get("files", [])
                    for filename in files:
                        file_response = requests.get(f"{API_URL}/download/{filename}", timeout=30)
                        file_response.raise_for_status()
                        st.download_button("⬇️ Download CSV", file_response.content,
                                           file_name=filename, mime="text/csv",
                                           key=f"new-download-{len(st.session_state.chat)}-{filename}",
                                           use_container_width=True)
                    st.session_state.chat.append({
                        "role": "assistant", "content": answer,
                        "steps": payload.get("steps", []), "files": files,
                        "id": str(len(st.session_state.chat)),
                    })
                except requests.HTTPError as exc:
                    try:
                        detail = exc.response.json().get("detail", "The agent request failed.")
                    except (ValueError, AttributeError):
                        detail = "The agent request failed."
                    st.error(detail)
                    st.session_state.chat.append({"role": "assistant", "content": detail})
                except requests.Timeout:
                    detail = (
                        "The agent is taking longer than 15 minutes to respond. "
                        "The backend may still be processing this request; check its terminal before retrying."
                    )
                    st.error(detail)
                    st.session_state.chat.append({"role": "assistant", "content": detail})
                except requests.RequestException:
                    detail = "Could not reach the API server. Make sure FastAPI is running on port 8000."
                    st.error(detail)
                    st.session_state.chat.append({"role": "assistant", "content": detail})
