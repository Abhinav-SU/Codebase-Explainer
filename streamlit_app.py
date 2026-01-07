"""
Streamlit Frontend with Error Boundaries and Session Management.
CRITICAL FIXES:
- Error boundaries to prevent crashes
- Session state management
- Progress indicators
- Graceful handling of backend errors
"""
import streamlit as st
import requests
from pathlib import Path
import json
import time
from typing import Optional, Dict, Any

# Import UI components
from utils.ui_components import (
    show_error, show_success, show_warning, show_info,
    ProgressTracker, loading_spinner
)

# Configuration
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Codebase Explainer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Error boundary decorator with enhanced error display
def with_error_boundary(func):
    """Decorator to add error handling to Streamlit functions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError:
            show_error(
                "Backend Connection Failed",
                "Cannot connect to the backend API",
                "Make sure the server is running: `uvicorn app.main:app --reload` on http://localhost:8000"
            )
            return None
        except requests.exceptions.Timeout:
            show_error(
                "Request Timeout",
                "The server took too long to respond",
                "The server might be overloaded or processing a large file. Try again in a moment."
            )
            return None
        except requests.exceptions.RequestException as e:
            show_error(
                "Network Error",
                "A network problem occurred",
                str(e)
            )
            return None
        except Exception as e:
            show_error(
                "Unexpected Error",
                "Something went wrong",
                str(e)
            )
            st.exception(e)  # Show full traceback in debug mode
            return None
    return wrapper


def initialize_session_state():
    """Initialize session state variables."""
    # Check for upload_id in URL query parameters
    query_params = st.query_params
    url_upload_id = query_params.get('upload_id', None)
    
    if 'upload_id' not in st.session_state:
        # Load from URL if available
        st.session_state['upload_id'] = url_upload_id
    elif url_upload_id and st.session_state['upload_id'] != url_upload_id:
        # Update if URL has different upload_id
        st.session_state['upload_id'] = url_upload_id
        # Clear related session state when upload_id changes
        st.session_state['summary_data'] = None
        st.session_state['selected_file'] = None
    if 'filename' not in st.session_state:
        st.session_state['filename'] = None
    if 'summary_data' not in st.session_state:
        st.session_state['summary_data'] = None
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    if 'backend_available' not in st.session_state:
        st.session_state['backend_available'] = None
    if 'ai_enabled' not in st.session_state:
        st.session_state['ai_enabled'] = None
    if 'selected_file' not in st.session_state:
        st.session_state['selected_file'] = None


@with_error_boundary
def check_backend_health() -> Optional[Dict[str, Any]]:
    """Check if backend is available and get configuration."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def display_backend_status():
    """Show backend connection status in sidebar."""
    health = check_backend_health()
    
    if health:
        st.session_state['backend_available'] = True
        st.session_state['ai_enabled'] = health.get('ai_available', False)
        
        with st.sidebar:
            st.success("✅ Backend Connected")
            
            if health.get('ai_available'):
                st.info("🤖 AI Features Enabled")
            else:
                st.warning("⚠️ AI Disabled (Template mode only)")
            
            if health.get('demo_mode'):
                st.info("🎬 Demo Mode Active")
    else:
        st.session_state['backend_available'] = False
        st.session_state['ai_enabled'] = False
        
        with st.sidebar:
            show_error(
                "Backend Offline",
                "Cannot reach the API server",
                "Start backend: `uvicorn app.main:app --reload`"
            )


def main():
    """Main application entry point."""
    initialize_session_state()
    
    st.title("🔍 AI-Powered Codebase Explainer")
    st.markdown("Upload a zipped codebase to analyze, summarize, and query it.")
    
    # Check backend status
    display_backend_status()
    
    # Sidebar for upload
    with st.sidebar:
        st.header("📤 Upload Codebase")
        
        if not st.session_state['backend_available']:
            st.error("Backend must be running to upload files")
        else:
            uploaded_file = st.file_uploader(
                "Choose a ZIP file",
                type=['zip'],
                help="Upload a zipped Python codebase (max 100MB)"
            )
            
            if uploaded_file:
                if st.button("Process Upload", type="primary"):
                    process_upload(uploaded_file)
        
        # Clear button
        if st.session_state['upload_id']:
            st.divider()
            if st.button("🗑️ Clear Current Project"):
                st.session_state['upload_id'] = None
                st.session_state['filename'] = None
                st.session_state['summary_data'] = None
                st.session_state['chat_history'] = []
                st.rerun()
    
    # Main content area
    if st.session_state['upload_id']:
        display_codebase_view()
    else:
        display_welcome_message()


@with_error_boundary
def process_upload(uploaded_file):
    """Handle file upload to backend with enhanced progress tracking."""
    
    # Create progress tracker with stages
    tracker = ProgressTracker(
        stages=['upload', 'extract', 'parse', 'summarize'],
        stage_names={
            'upload': '📤 Uploading File',
            'extract': '📦 Extracting Contents',
            'parse': '🔍 Parsing Code',
            'summarize': '📊 Generating Summaries'
        }
    )
    
    try:
        # Stage 1: Upload file (0-30%)
        tracker.update('upload', 0, "Preparing upload...")
        
        files = {'file': uploaded_file}
        response = requests.post(
            f"{API_BASE_URL}/upload",
            files=files,
            timeout=60
        )
        
        if response.status_code != 201:
            error_data = response.json()
            tracker.error(f"Upload failed: {error_data.get('detail', 'Unknown error')}")
            return
        
        data = response.json()
        st.session_state['upload_id'] = data['upload_id']
        st.session_state['filename'] = data['filename']
        
        tracker.complete('upload')
        
        # Stage 2: Extract (30-50%)
        tracker.update('extract', 50, "Extracting files from archive...")
        time.sleep(0.5)  # Let backend process
        tracker.complete('extract')
        
        # Stage 3: Parse (50-70%)
        tracker.update('parse', 70, "Analyzing code structure...")
        time.sleep(0.5)
        tracker.complete('parse')
        
        # Stage 4: Summarize (70-100%)
        tracker.update('summarize', 75, "Generating AI summaries...")
        
        # Use hybrid mode to get both template and AI summaries if available
        summarize_response = requests.post(
            f"{API_BASE_URL}/summary/{data['upload_id']}?mode=hybrid",
            timeout=120
        )
        
        if summarize_response.status_code != 200:
            error_data = summarize_response.json()
            tracker.error(f"Summarization failed: {error_data.get('detail', 'Unknown error')}")
            return
        
        st.session_state['summary_data'] = summarize_response.json()
        tracker.complete('summarize')
        
        # Success!
        show_success(
            "Upload and analysis complete!",
            "Browse your files in the 'Files & Summaries' tab"
        )
        time.sleep(1.5)
        st.rerun()
    
    except requests.exceptions.Timeout:
        tracker.error("Upload timed out. Try a smaller file or check your connection.")
    except requests.exceptions.ConnectionError:
        tracker.error("Cannot connect to backend. Make sure it's running on port 8000.")
    except Exception as e:
        tracker.error(f"Unexpected error: {str(e)}")
    finally:
        time.sleep(2)
        tracker.clear()


def display_welcome_message():
    """Show welcome screen when no codebase is loaded."""
    st.markdown("""
    ### Welcome to Codebase Explainer! 👋
    
    This tool helps you quickly understand unfamiliar codebases using AI.
    
    **Features:**
    - 📦 Upload zipped Python projects
    - 📊 Automatic code analysis and summarization
    - 🔍 Browse files and view detailed summaries
    - 🗺️ Identify classes, functions, and imports
    
    **Get Started:**
    1. Make sure the backend is running (check sidebar)
    2. Upload a ZIP file using the sidebar
    3. Wait for analysis to complete
    4. Browse summaries and explore your code
    
    ---
    
    ### Quick Setup Checklist:
    
    ✅ **Step 1**: Install dependencies
    ```bash
    pip install -r requirements.txt
    ```
    
    ✅ **Step 2**: Create `.env` file (copy from `.env.example`)
    ```bash
    GEMINI_API_KEY=your_key_here  # Optional for demo
    ENABLE_AI_FEATURES=false      # Set to false for demo without API costs
    ```
    
    ✅ **Step 3**: Start backend
    ```bash
    uvicorn app.main:app --reload
    ```
    
    ✅ **Step 4**: Start frontend (this page)
    ```bash
    streamlit run streamlit_app.py
    ```
    """)
    
    # Health check display
    with st.expander("🏥 System Health Check"):
        if st.button("Check Backend Status"):
            health = check_backend_health()
            if health:
                st.success("✅ Backend is running")
                st.json(health)
            else:
                st.error("❌ Backend is not responding")


@with_error_boundary
def display_codebase_view():
    """Main view showing uploaded codebase."""
    upload_id = st.session_state['upload_id']
    filename = st.session_state['filename']
    
    st.subheader(f"📁 {filename}")
    st.caption(f"Upload ID: `{upload_id}`")
    
    # Tabs for different views - NOW WITH 5 TABS!
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "� Files & Summaries", 
        "📊 Overview", 
        "💬 Ask AI",
        "⚖️ Compare",
        "⚙️ Settings"
    ])
    
    with tab1:
        display_file_explorer(upload_id)
    
    with tab2:
        display_overview(upload_id)
    
    with tab3:
        display_qa_section(upload_id)
    
    with tab4:
        display_comparison_view()
    
    with tab5:
        display_settings(upload_id)


@with_error_boundary
def display_file_explorer(upload_id):
    """Show file tree and summaries with better layout."""
    st.markdown("### 📂 File Explorer & Summaries")
    
    # Fetch files from backend
    response = requests.get(f"{API_BASE_URL}/files/{upload_id}", timeout=10)
    
    if response.status_code != 200:
        st.error(f"Failed to load files: {response.json().get('detail', 'Unknown error')}")
        return
    
    data = response.json()
    files = data['files']
    
    if not files:
        st.warning("No files found in this upload")
        return
    
    st.success(f"✅ Found {data['total_files']} files")
    
    # Create two columns: file list (left) and details (right)
    col_files, col_details = st.columns([1, 2])
    
    with col_files:
        st.markdown("#### 📋 File List")
        
        # Build tree structure
        tree = build_tree_structure(files)
        
        # Display tree with expandable sections
        for folder, items in tree.items():
            with st.expander(f"📁 {folder} ({len(items)} files)", expanded=(folder == "root")):
                for file_info in items:
                    # Show file name and size
                    size_kb = file_info['size_bytes'] / 1024
                    
                    if st.button(
                        f"📄 {file_info['filename']} ({size_kb:.1f} KB)",
                        key=f"view_{file_info['relative_path']}",
                        use_container_width=True
                    ):
                        st.session_state['selected_file'] = file_info
    
    with col_details:
        st.markdown("#### 📊 File Details & Summary")
        
        # Show selected file details
        if 'selected_file' in st.session_state and st.session_state['selected_file']:
            display_file_details(upload_id, st.session_state['selected_file'])
        else:
            st.info("👈 Select a file from the list to view its details and summary")


def build_tree_structure(files):
    """Organize files into folder hierarchy."""
    tree = {}
    
    for file_info in files:
        parts = Path(file_info['relative_path']).parts
        
        if len(parts) > 1:
            folder = parts[0]
        else:
            folder = "root"
        
        if folder not in tree:
            tree[folder] = []
        
        tree[folder].append(file_info)
    
    return tree


@with_error_boundary
def display_file_details(upload_id, file_info):
    """Show detailed summary and content for a file in a cleaner layout."""
    st.markdown(f"### 📄 {file_info['filename']}")
    st.caption(f"📍 Path: `{file_info['relative_path']}`")
    
    # Fetch summary - handle None case
    summary_data = st.session_state.get('summary_data') or {}
    
    # If summary_data is empty but upload_id exists, try to fetch it
    if not summary_data.get('files') and upload_id:
        try:
            with st.spinner("Loading summaries..."):
                response = requests.get(f"{API_BASE_URL}/summary/{upload_id}?mode=hybrid", timeout=30)
                if response.status_code == 200:
                    summary_data = response.json()
                    st.session_state['summary_data'] = summary_data
        except:
            pass  # If fetch fails, continue with empty data
    
    file_summaries = summary_data.get('files', [])
    
    file_summary = next(
        (s for s in file_summaries if s['filepath'].endswith(file_info['relative_path'])),
        None
    )
    
    if not file_summary:
        st.warning("⚠️ No summary available for this file yet.")
        st.info("💡 Generate summaries by clicking 'Generate Summaries' in the Overview tab")
        return
    
    template = file_summary.get('template_summary', {})
    
    # Check for parsing errors
    if file_summary.get('parse_errors'):
        with st.expander("⚠️ Parsing Errors", expanded=False):
            for error in file_summary['parse_errors']:
                st.code(error, language="text")
    
    # AI Summary (if available)
    if file_summary.get('ai_summary'):
        st.markdown("#### 🤖 AI-Powered Summary")
        st.success(file_summary['ai_summary'])
        st.markdown("---")
    
    # Quick Stats
    st.markdown("#### � Quick Stats")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Classes", len(template.get('classes', [])))
    with col2:
        st.metric("⚡ Functions", len(template.get('functions', [])))
    with col3:
        st.metric("📥 Imports", len(template.get('imports', [])))
    with col4:
        st.metric("📝 Lines", template.get('line_count', 0))
    
    st.markdown("---")
    
    # Detailed Structure
    st.markdown("#### 🔍 Code Structure")
    
    # Imports
    if template.get('imports'):
        with st.expander(f"📥 Imports ({len(template['imports'])})", expanded=True):
            for imp in template['imports'][:20]:  # Limit display
                st.code(imp, language="python")
            if len(template['imports']) > 20:
                st.caption(f"... and {len(template['imports']) - 20} more")
    
    # Classes
    if template.get('classes'):
        with st.expander(f"📦 Classes ({len(template['classes'])})", expanded=True):
            for cls in template['classes']:
                st.markdown(f"**`class {cls['name']}`**")
                if cls.get('docstring'):
                    st.info(f"📝 {cls['docstring']}")
                if cls.get('methods'):
                    st.caption(f"🔧 Methods: `{', '.join(cls['methods'])}`")
                st.markdown("---")
    
    # Functions
    if template.get('functions'):
        with st.expander(f"⚡ Functions ({len(template['functions'])})", expanded=True):
            for func in template['functions']:
                args_str = ', '.join(func['args']) if func['args'] else ''
                st.markdown(f"**`def {func['name']}({args_str})`**")
                if func.get('docstring'):
                    st.info(f"📝 {func['docstring']}")
                st.markdown("---")
    
    # View raw content option
    with st.expander("📜 View File Content", expanded=False):
        try:
            content_response = requests.get(
                f"{API_BASE_URL}/files/{upload_id}/{file_info['relative_path']}",
                timeout=10
            )
            if content_response.status_code == 200:
                content = content_response.json()['content']
                st.code(content, language="python")
            else:
                st.error("Failed to load file content")
        except Exception as e:
            st.error(f"Error loading content: {str(e)}")


@with_error_boundary
def display_overview(upload_id):
    """Show high-level codebase statistics and dependency graph."""
    st.markdown("### 📊 Codebase Overview")
    
    # Fetch summary data - handle None case
    summary_data = st.session_state.get('summary_data') or {}
    
    # If summary_data is empty but upload_id exists, try to fetch it
    if not summary_data.get('files') and upload_id:
        try:
            with st.spinner("Loading summaries..."):
                response = requests.get(f"{API_BASE_URL}/summary/{upload_id}?mode=hybrid", timeout=30)
                if response.status_code == 200:
                    summary_data = response.json()
                    st.session_state['summary_data'] = summary_data
        except:
            pass  # If fetch fails, continue with empty data
    
    if not summary_data:
        st.warning("Summary data not available. Generate summaries first.")
        return
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    files = summary_data.get('files', [])
    
    with col1:
        st.metric("Total Files", len(files))
    
    with col2:
        total_lines = sum(
            f.get('template_summary', {}).get('line_count', 0) 
            for f in files
        )
        st.metric("Total Lines", f"{total_lines:,}")
    
    with col3:
        successful = summary_data.get('successfully_summarized', 0)
        st.metric("Summarized", successful)
    
    with col4:
        failed = len(files) - successful
        st.metric("Parse Errors", failed)
    
    st.markdown("---")
    
    # Dependency Graph Visualization
    st.markdown("### 🕸️ Dependency Graph")
    st.caption("Visualize how files in your codebase import from each other")
    
    if st.button("🔄 Generate Dependency Graph", use_container_width=True):
        with st.spinner("Analyzing dependencies..."):
            try:
                response = requests.get(
                    f"{API_BASE_URL}/api/graph/{upload_id}",
                    timeout=30
                )
                response.raise_for_status()
                graph_data = response.json()
                
                # Store in session state
                st.session_state['graph_data'] = graph_data
                show_success("Dependency graph generated successfully!")
                
            except requests.exceptions.Timeout:
                show_error(
                    "Request Timeout",
                    "The graph generation is taking longer than expected. Try with a smaller codebase.",
                    "Timeout after 30 seconds"
                )
            except Exception as e:
                show_error("Graph Generation Failed", str(e))
    
    # Display graph if available
    if 'graph_data' in st.session_state:
        graph_data = st.session_state['graph_data']
        display_dependency_graph(graph_data)
    
    st.markdown("---")
    
    # Show files with errors
    if failed > 0:
        st.warning(f"⚠️ {failed} files had parsing errors")
        with st.expander("View files with errors"):
            for file_summary in files:
                if file_summary.get('parse_errors'):
                    st.text(f"❌ {file_summary['filepath']}")
                    for error in file_summary['parse_errors']:
                        st.caption(f"   {error}")


@with_error_boundary
def display_qa_section(upload_id):
    """Dedicated Q&A interface with chat history."""
    st.markdown("### 💬 Ask AI About Your Codebase")
    
    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Quick start tips
    if not st.session_state.chat_history:
        st.info("💡 **Get Started:** Ask questions about your code! Try:\n"
                "- What does this codebase do?\n"
                "- Explain the main classes and their relationships\n"
                "- How does the authentication work?\n"
                "- Show me the database models")
    
    # Display chat history
    for i, qa in enumerate(st.session_state.chat_history):
        with st.container():
            # Question
            st.markdown(f"**🤔 Question {i+1}:**")
            st.markdown(f"> {qa['question']}")
            
            # Answer
            st.markdown("**🤖 Answer:**")
            
            # Format answer with markdown support
            answer_text = qa['answer']
            if '```' in answer_text:
                # Already has code blocks
                st.markdown(answer_text)
            else:
                # Plain text answer
                st.write(answer_text)
            
            # Show sources if available
            if qa.get('sources'):
                with st.expander(f"📚 Sources ({len(qa['sources'])} files)", expanded=False):
                    for source in qa['sources']:
                        st.markdown(f"- `{source['file']}`")
                        if source.get('snippet'):
                            st.code(source['snippet'], language='python')
            
            st.markdown("---")
    
    # Question input area
    st.markdown("#### Ask a New Question")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        question = st.text_area(
            "Your Question",
            placeholder="Type your question about the codebase...",
            height=100,
            key=f"question_input_{len(st.session_state.chat_history)}"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        ask_button = st.button("🚀 Ask", type="primary", use_container_width=True)
        
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    # Handle question submission
    if ask_button and question.strip():
        with loading_spinner("🤔 Thinking..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/query/{upload_id}",
                    json={"question": question},
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        'question': question,
                        'answer': result.get('answer', 'No answer provided'),
                        'sources': result.get('sources', []),
                        'timestamp': time.time()
                    })
                    
                    show_success("Answer generated!", "Check the response above")
                    time.sleep(1)
                    st.rerun()
                else:
                    error_detail = response.json().get('detail', 'Unknown error')
                    show_error(
                        "Query Failed",
                        f"Status code: {response.status_code}",
                        error_detail
                    )
            
            except requests.exceptions.Timeout:
                show_error(
                    "Request Timeout",
                    "The AI is taking too long to respond",
                    "Try asking a simpler question or check your API configuration"
                )
            except requests.exceptions.ConnectionError:
                show_error(
                    "Connection Error",
                    "Cannot reach the backend server",
                    "Make sure the backend is running on http://localhost:8000"
                )
            except Exception as e:
                show_error(
                    "Unexpected Error",
                    "Something went wrong while processing your question",
                    str(e)
                )
    
    elif ask_button:
        show_warning("Empty Question", "Please type a question before clicking Ask")
    
    # Export chat history option
    if st.session_state.chat_history:
        st.markdown("#### 📥 Export Chat History")
        
        # Prepare export data
        export_data = {
            'upload_id': upload_id,
            'total_questions': len(st.session_state.chat_history),
            'conversations': [
                {
                    'question': qa['question'],
                    'answer': qa['answer'],
                    'sources': [s['file'] for s in qa.get('sources', [])]
                }
                for qa in st.session_state.chat_history
            ]
        }
        
        st.download_button(
            label="📄 Download as JSON",
            data=json.dumps(export_data, indent=2),
            file_name=f"qa_history_{upload_id}.json",
            mime="application/json",
            use_container_width=True
        )


@with_error_boundary
def display_comparison_view():
    """Display codebase comparison interface."""
    st.markdown("### ⚖️ Compare Codebases")
    st.caption("Compare two uploaded codebases to see differences in structure, metrics, and dependencies")
    
    # Fetch available codebases
    try:
        response = requests.get(f"{API_BASE_URL}/api/comparison/list", timeout=10)
        if response.status_code != 200:
            st.error("Failed to load available codebases")
            return
        
        codebases = response.json()
        
        if len(codebases) < 2:
            st.warning("⚠️ You need at least 2 uploaded codebases to compare.")
            st.info("💡 Upload more codebases using the sidebar to enable comparison.")
            return
        
        # Create upload selector
        st.markdown("#### Select Codebases to Compare")
        
        col1, col2 = st.columns(2)
        
        with col1:
            base_options = {f"{cb['name']} ({cb['upload_id'][:8]}...)": cb['upload_id'] for cb in codebases}
            base_selected = st.selectbox(
                "📌 Base Codebase",
                options=list(base_options.keys()),
                help="Select the base codebase to compare against"
            )
            base_upload_id = base_options[base_selected]
        
        with col2:
            # Filter out the base from compare options
            compare_options = {
                f"{cb['name']} ({cb['upload_id'][:8]}...)": cb['upload_id'] 
                for cb in codebases 
                if cb['upload_id'] != base_upload_id
            }
            
            if not compare_options:
                st.error("No other codebases available to compare")
                return
            
            compare_selected = st.selectbox(
                "🔄 Compare With",
                options=list(compare_options.keys()),
                help="Select the codebase to compare against the base"
            )
            compare_upload_id = compare_options[compare_selected]
        
        # Compare button
        if st.button("🚀 Compare Codebases", type="primary", use_container_width=True):
            perform_comparison(base_upload_id, compare_upload_id)
        
        # Show cached comparison if available
        comparison_key = f"comparison_{base_upload_id}_{compare_upload_id}"
        if comparison_key in st.session_state:
            display_comparison_results(st.session_state[comparison_key])
    
    except requests.exceptions.ConnectionError:
        show_error(
            "Connection Error",
            "Cannot connect to backend",
            "Make sure the backend is running on http://localhost:8000"
        )
    except Exception as e:
        show_error("Error", "Failed to load codebases", str(e))


@with_error_boundary
def perform_comparison(base_upload_id: str, compare_upload_id: str):
    """Perform comparison between two codebases."""
    with st.spinner("🔄 Comparing codebases... This may take a moment."):
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/comparison/compare",
                params={
                    "base_upload_id": base_upload_id,
                    "compare_upload_id": compare_upload_id
                },
                timeout=60
            )
            
            if response.status_code != 200:
                error_data = response.json()
                show_error(
                    "Comparison Failed",
                    f"Status: {response.status_code}",
                    error_data.get('detail', 'Unknown error')
                )
                return
            
            comparison_data = response.json()
            
            # Store in session state
            comparison_key = f"comparison_{base_upload_id}_{compare_upload_id}"
            st.session_state[comparison_key] = comparison_data
            
            show_success("Comparison complete!", "Results displayed below")
            st.rerun()
        
        except requests.exceptions.Timeout:
            show_error(
                "Request Timeout",
                "Comparison is taking longer than expected",
                "Try with smaller codebases or check server performance"
            )
        except Exception as e:
            show_error("Comparison Error", "Failed to compare codebases", str(e))


@with_error_boundary
def display_comparison_results(comparison: Dict):
    """Display detailed comparison results."""
    st.markdown("---")
    st.markdown("### 📊 Comparison Results")
    
    # Summary header
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"**Base:** `{comparison.get('base_name', 'Unknown')}`")
        st.caption(f"ID: `{comparison.get('base_upload_id', '')[:8]}...`")
    
    with col2:
        similarity = comparison.get('similarity_score', 0.0)
        st.metric("Similarity", f"{similarity:.1%}")
    
    with col3:
        compared_at = comparison.get('compared_at', '')
        if compared_at:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(compared_at.replace('Z', '+00:00'))
                st.caption(f"Compared: {dt.strftime('%Y-%m-%d %H:%M')}")
            except:
                pass
    
    # Comparison summary
    summary = comparison.get('comparison_summary', '')
    if summary:
        st.info(f"📝 **Summary:** {summary}")
    
    st.markdown("---")
    
    # Metrics comparison
    st.markdown("#### 📈 Code Metrics Comparison")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        size_change = comparison.get('size_change_bytes', 0)
        size_percent = comparison.get('size_change_percent', 0.0)
        if abs(size_change) >= 1024:
            size_display = f"{size_change / 1024:.1f} KB"
        else:
            size_display = f"{size_change} B"
        st.metric(
            "Size Change",
            size_display,
            delta=f"{size_percent:+.1f}%" if size_percent != 0.0 else None
        )
    
    with col2:
        lines_change = comparison.get('lines_change', 0)
        lines_percent = comparison.get('lines_change_percent', 0.0)
        st.metric(
            "Lines Change",
            f"{lines_change:,}",
            delta=f"{lines_percent:+.1f}%"
        )
    
    with col3:
        classes_change = comparison.get('classes_change', 0)
        st.metric(
            "Classes Change",
            f"{classes_change:+d}"
        )
    
    with col4:
        functions_change = comparison.get('functions_change', 0)
        st.metric(
            "Functions Change",
            f"{functions_change:+d}"
        )
    
    st.markdown("---")
    
    # File changes
    st.markdown("#### 📁 File Changes")
    
    files_added = comparison.get('files_added', [])
    files_removed = comparison.get('files_removed', [])
    files_modified = comparison.get('files_modified', [])
    files_unchanged = comparison.get('files_unchanged', [])
    
    # Create tabs for different file change types
    change_tab1, change_tab2, change_tab3, change_tab4 = st.tabs([
        f"➕ Added ({len(files_added)})",
        f"➖ Removed ({len(files_removed)})",
        f"✏️ Modified ({len(files_modified)})",
        f"✅ Unchanged ({len(files_unchanged)})"
    ])
    
    with change_tab1:
        if files_added:
            for file_path in files_added[:50]:  # Limit display
                st.success(f"➕ `{file_path}`")
            if len(files_added) > 50:
                st.caption(f"... and {len(files_added) - 50} more files")
        else:
            st.info("No files were added")
    
    with change_tab2:
        if files_removed:
            for file_path in files_removed[:50]:
                st.error(f"➖ `{file_path}`")
            if len(files_removed) > 50:
                st.caption(f"... and {len(files_removed) - 50} more files")
        else:
            st.info("No files were removed")
    
    with change_tab3:
        if files_modified:
            for file_path in files_modified[:50]:
                st.warning(f"✏️ `{file_path}`")
            if len(files_modified) > 50:
                st.caption(f"... and {len(files_modified) - 50} more files")
        else:
            st.info("No files were modified")
    
    with change_tab4:
        if files_unchanged:
            st.caption(f"Showing first 20 of {len(files_unchanged)} unchanged files:")
            for file_path in files_unchanged[:20]:
                st.text(f"✅ `{file_path}`")
            if len(files_unchanged) > 20:
                st.caption(f"... and {len(files_unchanged) - 20} more files")
        else:
            st.info("No files remained unchanged")
    
    st.markdown("---")
    
    # Dependency changes
    deps_added = comparison.get('dependencies_added', [])
    deps_removed = comparison.get('dependencies_removed', [])
    new_circular = comparison.get('new_circular_dependencies', [])
    resolved_circular = comparison.get('resolved_circular_dependencies', [])
    
    if deps_added or deps_removed or new_circular or resolved_circular:
        st.markdown("#### 🔗 Dependency Changes")
        
        dep_col1, dep_col2 = st.columns(2)
        
        with dep_col1:
            if deps_added:
                st.markdown("**➕ Added Dependencies:**")
                for dep in deps_added[:10]:
                    st.success(f"`{dep}`")
                if len(deps_added) > 10:
                    st.caption(f"... and {len(deps_added) - 10} more")
            
            if new_circular:
                st.markdown("**⚠️ New Circular Dependencies:**")
                for cycle in new_circular[:5]:
                    st.warning(f"`{' → '.join(cycle)}`")
                if len(new_circular) > 5:
                    st.caption(f"... and {len(new_circular) - 5} more")
        
        with dep_col2:
            if deps_removed:
                st.markdown("**➖ Removed Dependencies:**")
                for dep in deps_removed[:10]:
                    st.error(f"`{dep}`")
                if len(deps_removed) > 10:
                    st.caption(f"... and {len(deps_removed) - 10} more")
            
            if resolved_circular:
                st.markdown("**✅ Resolved Circular Dependencies:**")
                for cycle in resolved_circular[:5]:
                    st.success(f"`{' → '.join(cycle)}`")
                if len(resolved_circular) > 5:
                    st.caption(f"... and {len(resolved_circular) - 5} more")
    
    # Export comparison
    st.markdown("---")
    st.markdown("#### 📥 Export Comparison")
    
    comparison_json = json.dumps(comparison, indent=2, default=str)
    st.download_button(
        label="💾 Download Comparison as JSON",
        data=comparison_json,
        file_name=f"comparison_{comparison.get('base_upload_id', 'base')}_{comparison.get('compare_upload_id', 'compare')}.json",
        mime="application/json",
        use_container_width=True
    )


def display_settings(upload_id):
    """Settings and management options."""
    st.markdown("### ⚙️ Settings")
    
    st.info(f"Current Upload ID: `{upload_id}`")
    
    # Delete upload option
    st.markdown("#### 🗑️ Delete Upload")
    st.warning("This will permanently delete this upload and all associated data.")
    
    if st.button("Delete This Upload", type="secondary"):
        with st.spinner("Deleting..."):
            response = requests.delete(f"{API_BASE_URL}/upload/{upload_id}")
            if response.status_code == 200:
                st.success("✅ Upload deleted successfully")
                st.session_state['upload_id'] = None
                st.session_state['filename'] = None
                st.session_state['summary_data'] = None
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to delete upload")
    
    # Export summaries
    st.markdown("#### 📥 Export Summaries")
    if st.button("Download as JSON"):
        summary_data = st.session_state.get('summary_data') or {}
        if summary_data and summary_data.get('files'):
            json_str = json.dumps(summary_data, indent=2)
            st.download_button(
                label="💾 Download JSON",
                data=json_str,
                file_name=f"summaries_{upload_id}.json",
                mime="application/json"
            )


@with_error_boundary
def display_dependency_graph(graph_data):
    """Display interactive dependency graph using pyvis."""
    from pyvis.network import Network
    import tempfile
    import streamlit.components.v1 as components
    
    stats = graph_data.get('statistics', {})
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    circular_deps = graph_data.get('circular_dependencies', [])
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Dependencies", stats.get('total_dependencies', 0))
    
    with col2:
        st.metric("Isolated Files", stats.get('isolated_files', 0))
    
    with col3:
        st.metric("Circular Deps", stats.get('circular_dependencies', 0))
    
    with col4:
        st.metric("Missing Imports", stats.get('missing_imports', 0))
    
    # Show circular dependencies warning
    if circular_deps:
        with st.expander("⚠️ Circular Dependencies Detected", expanded=True):
            st.warning(f"Found {len(circular_deps)} circular import chain(s)")
            for i, cycle in enumerate(circular_deps[:5]):  # Show first 5
                st.text(f"{i+1}. {' → '.join(cycle)}")
            if len(circular_deps) > 5:
                st.caption(f"... and {len(circular_deps) - 5} more")
    
    # Most imported files
    most_imported = stats.get('most_imported', [])
    if most_imported:
        with st.expander("📌 Most Imported Files"):
            for item in most_imported:
                st.text(f"• {item['file']} ({item['count']} imports)")
    
    # Create network graph
    if nodes and len(nodes) <= 100:  # Limit for performance
        st.markdown("#### Interactive Graph")
        st.caption("Click and drag to explore • Zoom with scroll • Click nodes for details")
        
        net = Network(
            height="600px",
            width="100%",
            bgcolor="#ffffff",
            font_color="#000000",
            directed=True
        )
        
        # Configure physics for better layout
        net.set_options("""
        {
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 100,
                    "springConstant": 0.08
                },
                "maxVelocity": 50,
                "solver": "forceAtlas2Based",
                "timestep": 0.35,
                "stabilization": {"iterations": 150}
            }
        }
        """)
        
        # Add nodes
        for node in nodes:
            net.add_node(
                node['id'],
                label=node['label'],
                title=f"{node['full_path']}\nImports: {node['imports_count']}\nImported by: {node['imported_by_count']}",
                size=node['size']
            )
        
        # Add edges
        for edge in edges:
            net.add_edge(edge['from'], edge['to'])
        
        # Generate HTML
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
                net.save_graph(f.name)
                with open(f.name, 'r', encoding='utf-8') as html_file:
                    html_content = html_file.read()
            
            # Display in Streamlit
            components.html(html_content, height=600, scrolling=True)
            
        except Exception as e:
            show_error("Graph Rendering Error", str(e))
    
    elif len(nodes) > 100:
        st.warning(f"⚠️ Graph has {len(nodes)} nodes. Visualization is disabled for performance reasons (limit: 100 nodes).")
        st.info("💡 Consider filtering by folder or analyzing smaller modules separately.")
    
    else:
        st.info("No dependencies found to visualize.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("💥 Critical Error in Application")
        st.exception(e)
        st.info("Try refreshing the page or restarting the application.")
