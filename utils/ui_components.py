"""
UI Components for consistent styling and user feedback.
"""
import streamlit as st
from contextlib import contextmanager
from typing import Optional


@contextmanager
def loading_spinner(message: str = "Processing..."):
    """
    Context manager for consistent loading states with spinner.
    
    Usage:
        with loading_spinner("Uploading file..."):
            # do work
            response = requests.post(...)
    """
    placeholder = st.empty()
    
    with placeholder.container():
        col1, col2 = st.columns([1, 10])
        with col1:
            st.spinner()
        with col2:
            st.info(f"⏳ {message}")
    
    try:
        yield placeholder
    finally:
        placeholder.empty()


def show_error(title: str, message: str, details: Optional[str] = None):
    """
    Display error message with consistent formatting.
    
    Args:
        title: Error title/heading
        message: User-friendly error description
        details: Optional technical details (shown in expander)
    """
    st.error(f"❌ **{title}**")
    st.markdown(message)
    
    if details:
        with st.expander("🔍 Technical Details"):
            st.code(details, language="text")


def show_success(message: str, next_action: Optional[str] = None):
    """
    Display success message with optional next step.
    
    Args:
        message: Success message
        next_action: Optional hint for what to do next
    """
    st.success(f"✅ {message}")
    
    if next_action:
        st.caption(f"💡 Next: {next_action}")


def show_warning(message: str, suggestion: Optional[str] = None):
    """
    Display warning message with optional suggestion.
    
    Args:
        message: Warning message
        suggestion: Optional suggestion to fix the issue
    """
    st.warning(f"⚠️ {message}")
    
    if suggestion:
        st.caption(f"💡 Suggestion: {suggestion}")


def show_progress(current: int, total: int, message: str = "", stage: str = ""):
    """
    Show progress bar with status message.
    
    Args:
        current: Current step number
        total: Total number of steps
        message: Status message
        stage: Current stage name
    """
    progress = current / total if total > 0 else 0
    
    if stage:
        full_message = f"{stage}: {message} ({current}/{total})"
    else:
        full_message = f"{message} ({current}/{total})"
    
    st.progress(progress, text=full_message)


def show_info(message: str, icon: str = "ℹ️"):
    """Display informational message with custom icon."""
    st.info(f"{icon} {message}")


def show_metric_card(label: str, value: str, delta: Optional[str] = None, help_text: Optional[str] = None):
    """
    Display a metric in a card format.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional change indicator
        help_text: Optional help tooltip
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        help=help_text
    )


class ProgressTracker:
    """Track multi-stage progress with automatic updates."""
    
    def __init__(self, stages: list, stage_names: dict = None):
        """
        Initialize progress tracker.
        
        Args:
            stages: List of stage identifiers (e.g., ['upload', 'extract'])
            stage_names: Optional dict mapping stage IDs to display names
        """
        self.stages = stages
        self.stage_names = stage_names or {s: s for s in stages}
        self.total_stages = len(stages)
        self.current_stage_index = 0
        self.progress_bar = st.empty()
        self.status_text = st.empty()
    
    def update(self, stage: str, progress_pct: int = None, message: str = ""):
        """
        Update progress to specific stage.
        
        Args:
            stage: Stage identifier
            progress_pct: Overall progress percentage (0-100), auto-calculated if None
            message: Status message to display
        """
        if stage in self.stages:
            self.current_stage_index = self.stages.index(stage)
        
        # Calculate progress
        if progress_pct is None:
            progress_pct = int((self.current_stage_index / self.total_stages) * 100)
        
        stage_display_name = self.stage_names.get(stage, stage)
        
        # Update progress bar
        self.progress_bar.progress(progress_pct / 100.0)
        
        # Update status text
        status_msg = f"{stage_display_name}"
        if message:
            status_msg += f" - {message}"
        self.status_text.text(status_msg)
    
    def complete(self, stage: str):
        """Mark a stage as complete."""
        if stage in self.stages:
            idx = self.stages.index(stage)
            progress_pct = int(((idx + 1) / self.total_stages) * 100)
            self.progress_bar.progress(progress_pct / 100.0)
            stage_display_name = self.stage_names.get(stage, stage)
            self.status_text.text(f"✅ {stage_display_name} - Complete")
    
    def error(self, message: str):
        """Show error state."""
        self.progress_bar.empty()
        self.status_text.error(f"❌ {message}")
    
    def clear(self):
        """Clear the progress display."""
        self.progress_bar.empty()
        self.status_text.empty()


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_code_snippet(code: str, language: str = "python", max_lines: int = 10):
    """
    Format and display code snippet with line limit.
    
    Args:
        code: Code to display
        language: Programming language
        max_lines: Maximum lines to show
    """
    lines = code.split('\n')
    
    if len(lines) > max_lines:
        truncated = '\n'.join(lines[:max_lines])
        st.code(truncated, language=language)
        st.caption(f"... {len(lines) - max_lines} more lines (truncated)")
    else:
        st.code(code, language=language)
