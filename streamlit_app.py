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
DEEPSEEK_API_URL = "https://api.deepseek.com/v1"

# Page config
st.set_page_config(page_title="Chat AI", layout="wide", initial_sidebar_state="expanded")

# Load persisted data from file
PERSIST_FILE = Path("user_preferences.json")

def load_preferences():
    """Load user preferences from file"""
    if PERSIST_FILE.exists():
        try:
            with open(PERSIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "api_key_openrouter": "",
        "api_key_deepseek": "",
        "purpose": "General",
        "selected_models": {
            "General": None,
            "Academic/Research": None,
            "Programming": None
        },
        "current_session_id": None
    }

def save_preferences(prefs):
    """Save user preferences to file"""
    try:
        with open(PERSIST_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except:
        pass

def generate_session_id():
    """Generate a unique session ID"""
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def get_session_file(session_id):
    """Get session file path"""
    return SESSIONS_DIR / f"{session_id}.json"

def load_current_session(session_id):
    """Load current session data"""
    if not session_id:
        return None
    
    filepath = get_session_file(session_id)
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

def save_current_session(session_id, session_data):
    """Save current session data (auto-save)"""
    if not session_id:
        return False
    
    try:
        filepath = get_session_file(session_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def archive_current_session(session_id, session_name, messages, model):
    """Archive current session to named file"""
    if not session_id or not session_name or not messages:
        return False
    
    try:
        session_data = {
            "name": session_name,
            "created_at": datetime.now().isoformat(),
            "model": model,
            "messages": messages
        }
        
        # Create filename from session name
        filename = f"archive_{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = SESSIONS_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        # Delete the active session file
        active_file = get_session_file(session_id)
        if active_file.exists():
            active_file.unlink()
        
        return True
    except:
        return False

def save_session(session_name, messages, model):
    """Save chat session to JSON file"""
    session_data = {
        "name": session_name,
        "created_at": datetime.now().isoformat(),
        "model": model,
        "messages": messages
    }
    
    # Create filename from session name
    filename = f"archive_{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    """Get list of all saved sessions (archived only)"""
    sessions = []
    for filepath in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            # Only show archived sessions (start with archive_)
            if filepath.name.startswith("archive_"):
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

# Load preferences at startup
persisted_prefs = load_preferences()

# Initialize session state with persisted values
if "api_key_openrouter" not in st.session_state:
    st.session_state.api_key_openrouter = persisted_prefs.get("api_key_openrouter", "")
if "api_key_deepseek" not in st.session_state:
    st.session_state.api_key_deepseek = persisted_prefs.get("api_key_deepseek", "")
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = persisted_prefs.get("current_session_id")
if "messages" not in st.session_state:
    # Load messages from current session if exists
    if st.session_state.current_session_id:
        session_data = load_current_session(st.session_state.current_session_id)
        if session_data:
            st.session_state.messages = session_data.get("messages", [])
        else:
            st.session_state.messages = []
    else:
        st.session_state.messages = []
if "models_openrouter" not in st.session_state:
    st.session_state.models_openrouter = []
if "models_deepseek" not in st.session_state:
    st.session_state.models_deepseek = []
if "selected_models" not in st.session_state:
    st.session_state.selected_models = persisted_prefs.get("selected_models", {
        "General": None,
        "Academic/Research": None,
        "Programming": None
    })
if "purpose" not in st.session_state:
    st.session_state.purpose = persisted_prefs.get("purpose", "General")
if "model_search" not in st.session_state:
    st.session_state.model_search = ""
if "show_model_modal" not in st.session_state:
    st.session_state.show_model_modal = False
if "current_session_name" not in st.session_state:
    if st.session_state.current_session_id:
        session_data = load_current_session(st.session_state.current_session_id)
        if session_data:
            st.session_state.current_session_name = session_data.get("name", "Unnamed")
        else:
            st.session_state.current_session_name = None
    else:
        st.session_state.current_session_name = None

def get_available_models_openrouter(api_key):
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
            # Add provider tag and sort by pricing
            for model in models:
                model["provider"] = "OpenRouter"
            models = sorted(
                models,
                key=lambda x: float(x.get("pricing", {}).get("prompt", 999999))
            )
            return models
    except Exception as e:
        st.error(f"Error fetching OpenRouter models: {str(e)}")
    return []

def get_available_models_deepseek(api_key):
    """Fetch available models from DeepSeek"""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        response = requests.get(
            f"{DEEPSEEK_API_URL}/models",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            # Add provider tag
            for model in models:
                model["provider"] = "DeepSeek"
                # DeepSeek models typically have pricing structure
                if "pricing" not in model:
                    model["pricing"] = {"prompt": 0, "completion": 0}
            return models
    except Exception as e:
        st.warning(f"Error fetching DeepSeek models: {str(e)}")
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

def search_models(models, query):
    """Search models by name"""
    if not query:
        return models
    query_lower = query.lower()
    return [m for m in models if query_lower in m.get("id", "").lower()]

def format_price(price):
    """Format price with full decimal notation"""
    if price is None:
        return "Free"
    
    price = float(price) if price else 0
    
    if price == 0:
        return "Free"
    else:
        # Use Decimal for precise formatting
        from decimal import Decimal
        try:
            d = Decimal(str(price))
            # Get the number of decimal places needed
            if price >= 0.1:
                return f"${price:.6f}"
            elif price >= 0.0001:
                return f"${price:.10f}"
            else:
                # For very small numbers, show up to 15 decimals
                return f"${price:.15f}".rstrip('0').rstrip('.')
        except:
            return f"${price:.15f}".rstrip('0').rstrip('.')

def get_model_price(model):
    """Safely get model price"""
    try:
        price = model.get("pricing", {}).get("prompt", None)
        if price is not None:
            return float(price)
    except:
        pass
    return None

def chat_with_ai(api_key, model_id, messages, provider):
    """Send message to AI API"""
    try:
        if provider == "DeepSeek":
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            url = f"{DEEPSEEK_API_URL}/chat/completions"
        else:  # OpenRouter
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            url = f"{OPENROUTER_API_URL}/chat/completions"
        
        response = requests.post(
            url,
            headers=headers,
            json={
                "model": model_id,
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

def save_all_preferences():
    """Save all preferences to file"""
    prefs = {
        "api_key_openrouter": st.session_state.api_key_openrouter,
        "api_key_deepseek": st.session_state.api_key_deepseek,
        "purpose": st.session_state.purpose,
        "selected_models": st.session_state.selected_models,
        "current_session_id": st.session_state.current_session_id
    }
    save_preferences(prefs)

def auto_save_session():
    """Auto-save current session"""
    if st.session_state.current_session_id:
        session_data = {
            "name": st.session_state.current_session_name,
            "created_at": datetime.now().isoformat(),
            "model": st.session_state.selected_models.get(st.session_state.purpose),
            "messages": st.session_state.messages
        }
        save_current_session(st.session_state.current_session_id, session_data)

# Sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    
    # API Keys
    st.subheader("🔑 API Keys")
    
    api_key_or = st.text_input(
        "OpenRouter API Key",
        value=st.session_state.api_key_openrouter,
        type="password",
        help="Get from https://openrouter.ai"
    )
    
    if api_key_or != st.session_state.api_key_openrouter:
        st.session_state.api_key_openrouter = api_key_or
        save_all_preferences()
    
    api_key_ds = st.text_input(
        "DeepSeek API Key",
        value=st.session_state.api_key_deepseek,
        type="password",
        help="Get from https://platform.deepseek.com"
    )
    
    if api_key_ds != st.session_state.api_key_deepseek:
        st.session_state.api_key_deepseek = api_key_ds
        save_all_preferences()
    
    if st.session_state.api_key_openrouter or st.session_state.api_key_deepseek:
        # Load models
        if not st.session_state.models_openrouter and st.session_state.api_key_openrouter:
            with st.spinner("Loading OpenRouter models..."):
                st.session_state.models_openrouter = get_available_models_openrouter(st.session_state.api_key_openrouter)
        
        if not st.session_state.models_deepseek and st.session_state.api_key_deepseek:
            with st.spinner("Loading DeepSeek models..."):
                st.session_state.models_deepseek = get_available_models_deepseek(st.session_state.api_key_deepseek)
        
        # Combine all models
        all_models = st.session_state.models_openrouter + st.session_state.models_deepseek
        
        if all_models:
            st.subheader("🤖 Model Selection")
            
            # Purpose selector
            old_purpose = st.session_state.purpose
            st.session_state.purpose = st.selectbox(
                "Select Purpose:",
                options=["General", "Academic/Research", "Programming"],
                index=["General", "Academic/Research", "Programming"].index(st.session_state.purpose) if st.session_state.purpose in ["General", "Academic/Research", "Programming"] else 0,
                key="purpose_selector"
            )
            
            if old_purpose != st.session_state.purpose:
                save_all_preferences()
            
            # Filter models by purpose
            filtered_models = filter_models_by_purpose(all_models, st.session_state.purpose)
            
            # Open modal button
            if st.button("📋 Browse Models", key="open_modal_button", use_container_width=True):
                st.session_state.show_model_modal = True
            
            # Show currently selected model for this purpose
            current_selected = st.session_state.selected_models.get(st.session_state.purpose)
            if current_selected:
                st.markdown("---")
                # Parse model info (format: "provider:model_id")
                if isinstance(current_selected, str) and ":" in current_selected:
                    provider, model_id = current_selected.split(":", 1)
                    selected = next((m for m in all_models if m["id"] == model_id and m.get("provider") == provider), None)
                else:
                    selected = next((m for m in all_models if m["id"] == current_selected), None)
                
                if selected:
                    price = get_model_price(selected)
                    price_str = format_price(price)
                    provider_tag = f"🔷 {selected.get('provider', 'Unknown')}"
                    st.success(f"✅ Currently Selected:\n\n**{selected['id']}**\n\n{provider_tag}\n\n{price_str}/1k tokens")
                else:
                    st.warning("Selected model not found.")
        else:
            st.error("Could not load models. Check your API keys.")
    else:
        st.warning("Please add at least one API key (OpenRouter or DeepSeek)")
    
    st.divider()
    
    # Session Management
    st.subheader("💾 Sessions")
    
    # New session
    new_session_name = st.text_input("New session name:", placeholder="e.g., My Project")
    if st.button("Create New Session") and new_session_name:
        # Archive current session before creating new one
        if st.session_state.current_session_id and st.session_state.current_session_name and st.session_state.messages:
            archive_current_session(
                st.session_state.current_session_id,
                st.session_state.current_session_name,
                st.session_state.messages,
                st.session_state.selected_models.get(st.session_state.purpose)
            )
        
        # Create new session
        session_id = generate_session_id()
        st.session_state.current_session_id = session_id
        st.session_state.current_session_name = new_session_name
        st.session_state.messages = []
        auto_save_session()
        save_all_preferences()
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
                    # Archive current session
                    if st.session_state.current_session_id and st.session_state.current_session_name and st.session_state.messages:
                        archive_current_session(
                            st.session_state.current_session_id,
                            st.session_state.current_session_name,
                            st.session_state.messages,
                            st.session_state.selected_models.get(st.session_state.purpose)
                        )
                    
                    data = load_session(result["path"])
                    if data:
                        st.session_state.current_session_name = data.get("name", "Unnamed")
                        st.session_state.messages = data.get("messages", [])
                        st.session_state.current_session_id = None  # Archived session
                        st.session_state.show_model_modal = False
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
                        # Archive current session
                        if st.session_state.current_session_id and st.session_state.current_session_name and st.session_state.messages:
                            archive_current_session(
                                st.session_state.current_session_id,
                                st.session_state.current_session_name,
                                st.session_state.messages,
                                st.session_state.selected_models.get(st.session_state.purpose)
                            )
                        
                        data = load_session(session["path"])
                        if data:
                            st.session_state.current_session_name = data.get("name", "Unnamed")
                            st.session_state.messages = data.get("messages", [])
                            st.session_state.current_session_id = None  # Archived session
                            st.session_state.show_model_modal = False
                            st.rerun()
                with col2:
                    if st.button("🗑️", key=f"del_{session['path']}"):
                        if delete_session(session["path"]):
                            st.success("Deleted")
                            st.rerun()
        else:
            st.info("No sessions yet. Create one!")


# Modal for model selection
if st.session_state.show_model_modal:
    col_close, col_title = st.columns([1, 5])
    with col_close:
        if st.button("✖️ Close", key="close_modal"):
            st.session_state.show_model_modal = False
            st.rerun()
    
    st.title("🤖 Select Model")
    
    # Combine all models
    all_models = st.session_state.models_openrouter + st.session_state.models_deepseek
    
    # Purpose selector in modal
    modal_purpose = st.selectbox(
        "Filter by Purpose:",
        options=["General", "Academic/Research", "Programming"],
        index=["General", "Academic/Research", "Programming"].index(st.session_state.purpose),
        key="modal_purpose_selector"
    )
    
    if modal_purpose != st.session_state.purpose:
        st.session_state.purpose = modal_purpose
        save_all_preferences()
    
    # Filter models by purpose
    filtered_models = filter_models_by_purpose(all_models, st.session_state.purpose)
    
    # Search box
    modal_search = st.text_input(
        "🔍 Search models:",
        placeholder="Type model name...",
        key="modal_search_box"
    )
    
    # Search models
    searched_models = search_models(filtered_models, modal_search)
    
    # Display count and table
    st.write(f"📊 **Available Models** ({len(searched_models)} found)")
    st.markdown("---")
    
    if searched_models:
        # Display as table with columns
        for idx, model in enumerate(searched_models):
            price = get_model_price(model)
            price_str = format_price(price)
            provider = model.get("provider", "Unknown")
            provider_badge = "🔶 OpenRouter" if provider == "OpenRouter" else "🔷 DeepSeek"
            
            col1, col2, col3, col4 = st.columns([2, 0.8, 1.2, 0.8])
            
            with col1:
                st.code(model["id"], language=None)
            
            with col2:
                st.write(f"**{provider_badge}**")
            
            with col3:
                st.write(price_str)
            
            with col4:
                if st.button("✅ Select", key=f"modal_select_{idx}_{model['id']}_{provider}"):
                    # Store as "provider:model_id"
                    st.session_state.selected_models[st.session_state.purpose] = f"{provider}:{model['id']}"
                    save_all_preferences()
                    st.session_state.show_model_modal = False
                    auto_save_session()
                    st.success(f"✅ Selected: {model['id']}")
                    st.rerun()
    else:
        st.warning("No models found for this search")


# Main chat area
if not st.session_state.show_model_modal:
    st.title("💬 Chat AI")
    
    if st.session_state.current_session_name:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader(f"📌 {st.session_state.current_session_name}")
        with col2:
            if st.button("📥 Save as Archive"):
                save_session(
                    st.session_state.current_session_name,
                    st.session_state.messages,
                    st.session_state.selected_models.get(st.session_state.purpose)
                )
                st.success("Session saved to archive!")
        
        # Display messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Chat input
        current_selected = st.session_state.selected_models.get(st.session_state.purpose)
        if current_selected:
            # Parse provider and model_id
            if ":" in current_selected:
                provider, model_id = current_selected.split(":", 1)
            else:
                provider, model_id = "OpenRouter", current_selected
            
            # Check if API key exists for the provider
            api_key = None
            if provider == "DeepSeek" and st.session_state.api_key_deepseek:
                api_key = st.session_state.api_key_deepseek
            elif provider == "OpenRouter" and st.session_state.api_key_openrouter:
                api_key = st.session_state.api_key_openrouter
            
            if api_key:
                user_input = st.chat_input("Type your message...")
                if user_input:
                    # Add user message
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                    with st.chat_message("user"):
                        st.write(user_input)
                    
                    # Auto-save after user message
                    auto_save_session()
                    
                    # Get AI response
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            response = chat_with_ai(
                                api_key,
                                model_id,
                                st.session_state.messages,
                                provider
                            )
                            st.write(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # Auto-save after assistant response
                    auto_save_session()
                    st.rerun()
            else:
                st.warning(f"Please add API key for {provider}")
        else:
            st.warning("Please select a model first.")
    else:
        st.info("Create a new session or load an existing one from the sidebar.")
