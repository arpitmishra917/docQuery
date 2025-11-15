import streamlit as st
import requests

st.set_page_config(page_title="Chat with your PDF", layout="centered")
st.title("📄 Chat with your PDF")

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
    st.session_state.chat_history = []

# Upload PDF
uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
if uploaded_file and not st.session_state.session_id:
    with st.spinner("Uploading and indexing your PDF..."):
        response = requests.post(
            "http://localhost:8000/upload",
            files={"file": (uploaded_file.name, uploaded_file, "application/pdf")}
        )
        if response.status_code == 200:
            st.session_state.session_id = response.json()["session_id"]
            st.success("PDF uploaded and indexed successfully!")
        else:
            st.error(response.json().get("error", "Upload failed."))

# Ask a question
if st.session_state.session_id:
    query = st.text_input("Ask a question about your PDF")
    if query:
        with st.spinner("Thinking..."):
            response = requests.post(
                "http://localhost:8000/chat",
                data={"session_id": st.session_state.session_id, "query": query}
            )
            if response.status_code == 200:
                answer = response.json()["answer"]
                st.session_state.chat_history.append((query, answer))
            else:
                st.error(response.json().get("error", "Chat failed."))

# Display chat history
if st.session_state.chat_history:
    st.markdown("### Chat History")
    for q, a in reversed(st.session_state.chat_history):
        st.markdown(f"**You:** {q}")
        st.markdown(f"**Bot:** {a}")
        st.markdown("---")