import streamlit as st
import requests
import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd

# Config
SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1"

# Page config
st.set_page_config(page_title="Chat AI", layout="wide", initial_sidebar_state="expanded")

# Initialize session state
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "current_session" not in st.session_state:
    st.session_state.current_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "models" not in st.session_state:
    st.session_state.models = []
if "selected_model" not in st.session_state:
    st.session_state.selected_model = None
if "purpose" not in st.session_state:
    st.session_state.purpose = "General"


def get_available_models(api_key):
    """Fetch available models from OpenRouter"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        response = requests.get(
            f"{OPENROUTER_API_URL}/models",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            # Filter and sort by pricing
            models = sorted(
                models,
                key=lambda x: x.get("pricing", {}).get("prompt", float("inf"))
            )
            return models
    except Exception as e:
        st.error(f"Error fetching models: {str(e)}")
    return []


def filter_models_by_purpose(models, purpose):
    """Filter models based on purpose"""
    if purpose == "General":
        return models
    
    elif purpose == "Academic/Research":
        # Prioritize: Claude, GPT-4, DeepSeek (good reasoning)
        keywords = ["claude", "gpt-4", "deepseek", "mistral"]
        filtered = [m for m in models if any(k in m.get("id", "").lower() for k in keywords)]
        return filtered if filtered else models
    
    elif purpose == "Programming":
        # Prioritize: Code-specific models
        keywords = ["deepseek", "claude", "gpt", "code"]
        filtered = [m for m in models if any(k in m.get("id", "").lower() for k in keywords)]
        return filtered if filtered else models
    
    return models


def get_cheapest_model(models):
    """Get cheapest model from list"""
    if not models:
        return None
    return min(models, key=lambda x: float(x.get("pricing", {}).get("prompt", 999)))


def save_session(session_name, messages, model):
    """Save chat session to JSON file"""
    session_data = {
        "name": session_name,
        "created_at": datetime.now().isoformat(),
        "model": model,
        "messages": messages
    }
    
    # Create filename from session name
    filename = f"{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = SESSIONS_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    
    return str(filepath)


def load_session(filepath):
    """Load chat session from JSON file"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading session: {str(e)}")
    return None


def get_all_sessions():
    """Get list of all saved sessions"""
    sessions = []
    for filepath in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "path": str(filepath),
                    "name": data.get("name", "Unnamed"),
                    "created_at": data.get("created_at", ""),
                    "model": data.get("model", "Unknown"),
                    "message_count": len(data.get("messages", []))
                })
        except:
            continue
    return sessions


def delete_session(filepath):
    """Delete session file"""
    try:
        Path(filepath).unlink()
        return True
    except:
        return False


def search_sessions(query):
    """Search through sessions"""
    all_sessions = get_all_sessions()
    results = []
    
    query_lower = query.lower()
    for session in all_sessions:
        if query_lower in session["name"].lower():
            results.append(session)
        else:
            # Search in messages
            try:
                data = load_session(session["path"])
                if data:
                    for msg in data.get("messages", []):
                        if query_lower in msg.get("content", "").lower():
                            results.append(session)
                            break
            except:
                continue
    
    return results


def chat_with_ai(api_key, model, messages):
    """Send message to OpenRouter API"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        response = requests.post(
            f"{OPENROUTER_API_URL}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": messages,
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


# Sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    
    # API Key
    st.session_state.api_key = st.text_input(
        "OpenRouter API Key",
        value=st.session_state.api_key,
        type="password",
        help="Get from https://openrouter.ai"
    )
    
    if st.session_state.api_key:
        # Load models
        if not st.session_state.models:
            with st.spinner("Loading models..."):
                st.session_state.models = get_available_models(st.session_state.api_key)
        
        if st.session_state.models:
            st.subheader("🤖 Model Selection")
            
            # Purpose selector
            st.session_state.purpose = st.selectbox(
                "Select Purpose:",
                options=["General", "Academic/Research", "Programming"],
                index=["General", "Academic/Research", "Programming"].index(st.session_state.purpose) if st.session_state.purpose in ["General", "Academic/Research", "Programming"] else 0,
                key="purpose_selector"
            )
            
            # Filter models by purpose
            filtered_models = filter_models_by_purpose(st.session_state.models, st.session_state.purpose)
            
            # Display models as a table
            st.write(f"📊 **Available Models for {st.session_state.purpose}** ({len(filtered_models)} found)")
            
            # Create table data
            table_data = []
            for idx, model in enumerate(filtered_models[:15]):  # Show top 15
                price = float(model.get("pricing", {}).get("prompt", 0))
                table_data.append({
                    "Model": model["id"],
                    "Price ($)": f"{price:.6f}",
                    "Select": idx
                })
            
            if table_data:
                # Display models
                for idx, row in enumerate(table_data):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.code(row["Model"], language=None)
                    
                    with col2:
                        st.write(f"**{row['Price ($)']}/1k**")
                    
                    with col3:
                        if st.button("✅ Select", key=f"select_{idx}"):
                            st.session_state.selected_model = filtered_models[idx]["id"]
                            st.success(f"✅ Selected: {filtered_models[idx]['id']}")
                            st.rerun()
                
                # Show currently selected model
                if st.session_state.selected_model:
                    st.divider()
                    selected = next((m for m in filtered_models if m["id"] == st.session_state.selected_model), None)
                    if selected:
                        st.success(f"✅ Currently Selected: **{selected['id']}**")
                        st.info(f"📊 Price: ${float(selected.get('pricing', {}).get('prompt', 0)):.6f} / ${float(selected.get('pricing', {}).get('completion', 0)):.6f}")
                    else:
                        st.warning("Selected model not in current filter. Please select again.")
                else:
                    st.info("👆 Click 'Select' to choose a model")
            else:
                st.warning("No models available for this purpose")
        else:
            st.error("Could not load models. Check your API key.")
    
    st.divider()
    
    # Session Management
    st.subheader("💾 Sessions")
    
    # New session
    new_session_name = st.text_input("New session name:", placeholder="e.g., My Project")
    if st.button("Create New Session") and new_session_name:
        st.session_state.current_session = {
            "name": new_session_name,
            "messages": [],
            "model": st.session_state.selected_model
        }
        st.session_state.messages = []
        st.success(f"Created: {new_session_name}")
        st.rerun()
    
    st.divider()
    
    # Search
    search_query = st.text_input("🔍 Search sessions:", placeholder="Search by name or content")
    
    if search_query:
        search_results = search_sessions(search_query)
        st.write(f"Found {len(search_results)} session(s)")
        for result in search_results:
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"📝 {result['name']} ({result['message_count']} msgs)"):
                    data = load_session(result["path"])
                    if data:
                        st.session_state.current_session = data
                        st.session_state.messages = data.get("messages", [])
                        st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{result['path']}"):
                    if delete_session(result["path"]):
                        st.success("Deleted")
                        st.rerun()
    else:
        # List all sessions
        all_sessions = get_all_sessions()
        if all_sessions:
            st.write(f"📚 {len(all_sessions)} session(s)")
            for session in all_sessions[:10]:  # Show last 10
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(f"📝 {session['name']} ({session['message_count']} msgs)", key=f"load_{session['path']}"):
                        data = load_session(session["path"])
                        if data:
                            st.session_state.current_session = data
                            st.session_state.messages = data.get("messages", [])
                            st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{session['path']}"):
                        if delete_session(session["path"]):
                            st.success("Deleted")
                            st.rerun()
        else:
            st.info("No sessions yet. Create one!")


# Main chat area
st.title("💬 Chat AI")

if st.session_state.current_session:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(f"📌 {st.session_state.current_session['name']}")
    with col2:
        if st.button("📥 Save Session"):
            save_session(
                st.session_state.current_session["name"],
                st.session_state.messages,
                st.session_state.selected_model
            )
            st.success("Session saved!")
    
    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Chat input
    if st.session_state.api_key and st.session_state.selected_model:
        user_input = st.chat_input("Type your message...")
        if user_input:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            with st.chat_message("user"):
                st.write(user_input)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat_with_ai(
                        st.session_state.api_key,
                        st.session_state.selected_model,
                        st.session_state.messages
                    )
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
            
            st.rerun()
    else:
        st.warning("Please set API key and select a model first.")
else:
    st.info("Create a new session or load an existing one from the sidebar.")
