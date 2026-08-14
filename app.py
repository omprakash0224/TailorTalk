import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from src.agent import create_agent, run_agent
import tempfile
import os
import uuid
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# /health endpoint — lightweight background HTTP server
# ---------------------------------------------------------------------------
# Runs on HEALTH_PORT (default 8502) so load balancers / orchestrators can
# probe liveness without touching the Streamlit websocket.
# The daemon thread is started once per process (guarded by a module-level
# flag) and shuts down automatically when Streamlit exits.

_HEALTH_PORT = int(os.environ.get("HEALTH_PORT", "8502"))
_HEALTH_SERVER_STARTED = False


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler: GET /health -> 200 JSON, everything else -> 404."""

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            body = json.dumps({"status": "ok", "service": "TailorTalk"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    # Suppress the default request log lines from cluttering Streamlit output
    def log_message(self, format, *args):  # noqa: A002
        pass


def _start_health_server() -> None:
    """Start the health-check HTTP server in a background daemon thread."""
    global _HEALTH_SERVER_STARTED
    if _HEALTH_SERVER_STARTED:
        return
    _HEALTH_SERVER_STARTED = True

    server = HTTPServer(("0.0.0.0", _HEALTH_PORT), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, name="health-server", daemon=True)
    thread.start()


_start_health_server()
# ---------------------------------------------------------------------------

# Page config
st.set_page_config(page_title="TailorTalk Saree Search", page_icon="🥻", layout="wide")
st.title("🥻 TailorTalk Visual Saree Search")

# Initialize agent (cached via session_state so it's created only once)
if "agent" not in st.session_state:
    st.session_state.agent = create_agent()

# Initialize chat history (LangChain message objects) and display messages list
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past chat messages on rerun
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "results" in msg:
            cols = st.columns(3)
            for idx, r in enumerate(msg["results"]):
                with cols[idx % 3]:
                    st.image(r["image_url"], use_container_width=True)
                    st.markdown(f"**{r['name']}**")
                    st.markdown(f"Match: {r['score']:.1f}%")
                    st.markdown(f"Price: ₹{r['price']}")
                    st.markdown(f"[View product]({r['product_url']})")

# Sidebar: image upload / URL input
with st.sidebar:
    st.header("🔍 Search with an Image")
    uploaded_file = st.file_uploader("Upload a saree image", type=["jpg", "jpeg", "png", "webp"])
    image_url_input = st.text_input("Or paste an image URL")
    if uploaded_file:
        st.image(uploaded_file, caption="Your query image", use_container_width=True)

# Chat input
if prompt := st.chat_input("Ask about sarees or find similar ones..."):
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build agent input, appending image context if provided
    agent_input = prompt

    if uploaded_file is not None:
        temp_path = os.path.join(tempfile.gettempdir(), f"upload_{uuid.uuid4().hex}.jpg")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        agent_input += (
            f"\n[User uploaded an image. Local path: {temp_path}. "
            "Use this path for the image_path argument of search_similar_sarees.]"
        )
    elif image_url_input:
        agent_input += (
            f"\n[User provided an image URL: {image_url_input}. "
            "Use this for the image_url argument of search_similar_sarees.]"
        )

    # Persist user message in display history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Run agent and display response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                output = run_agent(
                    st.session_state.agent,
                    agent_input,
                    st.session_state.chat_history,
                )
                st.markdown(output)

                # Update LangChain chat history for multi-turn context
                st.session_state.chat_history.append(HumanMessage(content=agent_input))
                st.session_state.chat_history.append(AIMessage(content=output))

                # Persist assistant message
                assistant_msg = {"role": "assistant", "content": output}

                # Render image grid if the tool stored results
                if st.session_state.get("last_results"):
                    results = st.session_state.pop("last_results")
                    assistant_msg["results"] = results

                    cols = st.columns(3)
                    for idx, r in enumerate(results):
                        with cols[idx % 3]:
                            st.image(r["image_url"], use_container_width=True)
                            st.markdown(f"**{r['name']}**")
                            st.markdown(f"Match: {r['score']:.1f}%")
                            retail = r.get("retail_price", r["price"])
                            disc = r["price"]
                            if retail and retail != disc:
                                st.markdown(f"~~₹{retail}~~ **₹{disc}**")
                            else:
                                st.markdown(f"**₹{disc}**")
                            st.markdown(f"[🛍️ View product]({r['product_url']})")

                st.session_state.messages.append(assistant_msg)

            except Exception as e:
                st.error(f"Something went wrong: {e}")
