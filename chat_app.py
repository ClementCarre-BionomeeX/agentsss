import streamlit as st
import requests
import json
import urllib.parse
from html.parser import HTMLParser
import re


BRAVE_API_KEY = "BSAsSbus0w3hVnrBYSxt_aZZjZLGvIg"  # 🔁 Replace this


def html_to_markdown(text):
    # Convert <strong> and <b> to bold
    text = re.sub(r"</?(strong|b)>", "**", text)
    # Convert <em> and <i> to italic
    text = re.sub(r"</?(em|i)>", "*", text)
    # Remove all other tags (simplified)
    text = re.sub(r"<[^>]+>", "", text)
    return text


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)


def strip_html(html):
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


def fetch_images(query):
    try:
        image_response = requests.get(
            "https://api.search.brave.com/res/v1/images/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            params={"q": query, "count": 3},
            timeout=10,
        )
        images = image_response.json().get("results", [])
        return [img.get("thumbnail") for img in images if "thumbnail" in img]
    except Exception as e:
        print(f"❌ Image fetch failed: {e}")
        return []


def perform_image_search(query: str) -> list:
    print(f"🖼️ Performing Brave image search: {query}")
    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/images/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            params={"q": query, "count": 6},  # 6 is divisible by 3 for nice grid
            timeout=10,
        )
        images = response.json().get("results", [])
        print("🧪 Raw image results:", images)

        results = []
        for img in images:
            thumb = img.get("thumbnail", {}).get("src")
            full_img = img.get("properties", {}).get("url") or img.get("url")
            title = img.get("title", "Image")
            source = img.get("source", "")
            if isinstance(thumb, str) and thumb.startswith("http"):
                results.append(
                    {
                        "thumbnail": thumb,
                        "full_url": full_img,
                        "title": title,
                        "source": source,
                    }
                )
            else:
                print(f"⚠️ Skipped: {thumb}")
        return results
    except Exception as e:
        print(f"❌ Image search failed: {e}")
        return []


def perform_web_search(query: str) -> str:
    print(f"🌐 Performing Brave search: {query}")
    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            params={"q": query, "count": 5},
            timeout=10,
        )

        results = response.json().get("web", {}).get("results", [])
        if not results:
            return "🔍 No search results found."

        output = "🔍 **Top Search Results:**\n\n"
        for r in results:
            title = html_to_markdown(r["title"])
            desc = html_to_markdown(r["description"])
            url = r["url"]
            output += f"- [{title}]({url})\n  \n  {desc}\n\n"

        # Fetch images
        image_urls = fetch_images(query)
        if image_urls:
            output += "\n🖼️ **Top Image Previews:**\n\n"
            for url in image_urls:
                output += f"![Image]({url})\n\n"

        return output.strip()
    except Exception as e:
        print(f"❌ Brave search failed: {e}")
        return "**[Error]** Web search failed."


OLLAMA_MODEL = "gpt-oss:20b"
OLLAMA_HOST = "http://localhost:11434"

st.set_page_config(page_title="Agentic Chat", layout="centered")
st.title("🤖 Agentic Chat (v0)")
st.caption("Chatting with an Ollama-backed agent")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Display chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Say something to the agent...")

if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 🌐 Check for /search tool command
    if user_input.startswith("/search "):
        query = user_input[len("/search ") :].strip()
        result = perform_web_search(query)

        with st.chat_message("assistant"):
            st.markdown(result)

        st.session_state.messages.append({"role": "assistant", "content": result})
        st.stop()  # prevent going to Ollama for this message
    # 🖼️ /image command
    elif user_input.startswith("/image "):
        query = user_input[len("/image ") :].strip()
        image_data = perform_image_search(query)

        with st.chat_message("assistant"):
            if image_data:
                st.markdown("🖼️ **Top Image Results:**")
                cols = st.columns(3)  # 3 per row

                for i, img in enumerate(image_data):
                    with cols[i % 3]:
                        st.image(img["thumbnail"], use_container_width=True)
                        st.markdown(
                            f"""<div style='font-size: 0.85em'>
                            <b>{img['title']}</b><br>
                            <i>{img['source']}</i><br>
                            <a href="{img['full_url']}" target="_blank">View full image</a>
                            </div>""",
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown("⚠️ No images could be rendered.")

        st.session_state.messages.append(
            {"role": "assistant", "content": f"[Images returned for: {query}]"}
        )
        st.stop()

    # Assistant message container
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": st.session_state.messages,
                    "stream": True,
                },
                stream=True,
                timeout=60,
            )

            for line in response.iter_lines():
                if line:
                    raw = line.decode("utf-8")
                    print(f"🧩 [RAW LINE] {raw}")  # Server-side log

                    if raw.startswith("data: "):
                        raw = raw[6:]

                    try:
                        data = json.loads(raw)
                        delta = data.get("message", {}).get("content", "")
                        full_response += delta
                        response_placeholder.markdown(full_response)
                    except Exception as e:
                        print(f"⚠️ JSON decode error: {e}")
                        print(f"⚠️ Line that caused error: {raw}")

        except Exception as e:
            print(f"❌ Request failed: {e}")
            full_response = "**[Error]** Unable to contact Ollama."

        # Save assistant message
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response}
        )
