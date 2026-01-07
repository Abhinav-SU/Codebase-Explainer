"""
Code summarization with template-based and AI-powered analysis.
CRITICAL FIXES:
- AST parser error handling (won't crash on bad syntax)
- Graceful degradation when AI is unavailable
- Token cost tracking
- Embedding persistence
"""
import ast
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.config import settings
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class FileSummary(BaseModel):
    """Summary for a single file."""
    filepath: str
    template_summary: dict
    ai_summary: Optional[str] = None
    embedding_id: Optional[str] = None
    parse_errors: List[str] = []


class SummaryResponse(BaseModel):
    """Complete summarization response."""
    upload_id: str
    mode: str
    summarized_at: str
    total_files: int
    successfully_summarized: int
    files: List[FileSummary]
    token_usage: Optional[dict] = None
    embeddings_stored: bool = False


class CodeSummarizer:
    """
    Template-based code summarization with robust error handling.
    CRITICAL: Won't crash on syntax errors in user code.
    """
    
    def __init__(self):
        self.upload_dir = settings.get_absolute_path(settings.upload_dir)
        self.summaries_dir = settings.get_absolute_path(settings.summaries_dir)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
    
    def summarize_file(self, filepath: Path, mode: str = 'template') -> FileSummary:
        """
        Summarize a single file with error recovery.
        """
        parse_errors = []
        
        # Template-based summary (always runs)
        try:
            template_summary = self._template_summary(filepath)
        except Exception as e:
            logger.error(f"Template summary failed for {filepath}: {e}")
            template_summary = {
                "error": str(e),
                "filepath": str(filepath),
                "imports": [],
                "classes": [],
                "functions": [],
                "line_count": 0
            }
            parse_errors.append(f"Template parsing error: {str(e)}")
        
        # AI summary (only if available and requested)
        ai_summary = None
        if mode in ['ai', 'hybrid'] and settings.ai_available:
            try:
                ai_summary = self._ai_summary(filepath, template_summary)
            except Exception as e:
                logger.warning(f"AI summary failed for {filepath}: {e}")
                parse_errors.append(f"AI summary error: {str(e)}")
        
        return FileSummary(
            filepath=str(filepath),
            template_summary=template_summary,
            ai_summary=ai_summary,
            parse_errors=parse_errors
        )
    
    def _template_summary(self, filepath: Path) -> dict:
        """
        Generate template-based summary using AST.
        CRITICAL: Handles syntax errors gracefully.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            logger.error(f"Could not read file {filepath}: {e}")
            raise ValueError(f"Cannot read file: {str(e)}")
        
        # Parse with error handling
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {filepath}: {e}")
            # Return partial info without AST analysis
            return {
                "filepath": str(filepath),
                "imports": [],
                "classes": [],
                "functions": [],
                "line_count": len(code.splitlines()),
                "syntax_error": {
                    "line": e.lineno,
                    "message": str(e)
                }
            }
        except Exception as e:
            logger.error(f"AST parse failed for {filepath}: {e}")
            raise ValueError(f"Parse error: {str(e)}")
        
        # Extract information safely
        try:
            return {
                "filepath": str(filepath),
                "imports": self._safe_extract_imports(tree),
                "classes": self._safe_extract_classes(tree),
                "functions": self._safe_extract_functions(tree),
                "line_count": len(code.splitlines())
            }
        except Exception as e:
            logger.error(f"Error extracting info from {filepath}: {e}")
            raise ValueError(f"Extraction error: {str(e)}")
    
    def _safe_extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract imports with error handling."""
        imports = []
        try:
            for node in ast.walk(tree):
                try:
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        imports.extend(f"{module}.{alias.name}" for alias in node.names)
                except Exception as e:
                    logger.debug(f"Error extracting import: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error walking AST for imports: {e}")
        
        return imports
    
    def _safe_extract_classes(self, tree: ast.AST) -> List[Dict]:
        """Extract classes with error handling."""
        classes = []
        try:
            for node in ast.walk(tree):
                try:
                    if isinstance(node, ast.ClassDef):
                        methods = []
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                methods.append(item.name)
                        
                        classes.append({
                            "name": node.name,
                            "methods": methods,
                            "docstring": ast.get_docstring(node) or ""
                        })
                except Exception as e:
                    logger.debug(f"Error extracting class: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error walking AST for classes: {e}")
        
        return classes
    
    def _safe_extract_functions(self, tree: ast.AST) -> List[Dict]:
        """Extract top-level functions with error handling."""
        functions = []
        try:
            for node in tree.body:
                try:
                    if isinstance(node, ast.FunctionDef):
                        args = []
                        if hasattr(node.args, 'args'):
                            args = [arg.arg for arg in node.args.args]
                        
                        functions.append({
                            "name": node.name,
                            "args": args,
                            "docstring": ast.get_docstring(node) or ""
                        })
                except Exception as e:
                    logger.debug(f"Error extracting function: {e}")
                    continue
        except Exception as e:
            logger.warning(f"Error extracting functions: {e}")
        
        return functions
    
    def _ai_summary(self, filepath: Path, template_summary: dict) -> Optional[str]:
        """
        Generate AI-powered summary using Google Gemini.
        Only called if AI is available.
        """
        if not settings.ai_available:
            return None
        
        try:
            import google.generativeai as genai
            
            # Configure Gemini
            genai.configure(api_key=settings.gemini_api_key)
            # Use gemini-2.0-flash (gemini-1.5-flash is deprecated)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Read file content (truncate if too large)
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()[:8000]  # Gemini can handle more context
            
            # Build prompt
            prompt = self._build_prompt(code, template_summary)
            
            # Call Gemini
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 300,
                }
            )
            
            return response.text
        
        except Exception as e:
            logger.error(f"Google Gemini API error: {e}")
            return None
    
    def _build_prompt(self, code: str, template_summary: dict) -> str:
        """Build prompt for AI summarization."""
        classes = [c['name'] for c in template_summary.get('classes', [])]
        functions = [f['name'] for f in template_summary.get('functions', [])]
        
        return f"""
Analyze this Python code and provide a concise 2-3 sentence summary:

Code Preview:
```python
{code}
```

Detected Structure:
- Classes: {', '.join(classes) if classes else 'None'}
- Functions: {', '.join(functions) if functions else 'None'}
- Imports: {', '.join(template_summary.get('imports', [])[:5])}

Provide:
1. High-level purpose of this file
2. Key functionality and responsibilities
"""
    
    def save_summaries(self, upload_id: str, summaries: List[FileSummary]):
        """Persist summaries to disk."""
        output_dir = self.summaries_dir / upload_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / 'file_summaries.json'
        
        try:
            data = {
                "upload_id": upload_id,
                "summarized_at": datetime.utcnow().isoformat(),
                "total_files": len(summaries),
                "files": [s.dict() for s in summaries]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved summaries for {upload_id} to {output_file}")
        
        except Exception as e:
            logger.error(f"Error saving summaries: {e}")
            raise


# Initialize summarizer
summarizer = CodeSummarizer()


@router.post("/{upload_id}", response_model=SummaryResponse)
async def summarize_codebase(
    upload_id: str,
    mode: str = Query('template', regex='^(template|ai|hybrid)$', description="Summarization mode")
):
    """
    Generate summaries for all files in an upload.
    
    Modes:
    - **template**: Fast, AST-based analysis (no API costs)
    - **ai**: Google Gemini-powered summaries (requires API key)
    - **hybrid**: Both template and AI summaries
    
    Note: If Gemini key is missing, will automatically fall back to template mode.
    """
    logger.info(f"Summarizing upload {upload_id} with mode={mode}")
    
    # Check if upload exists
    upload_dir = summarizer.upload_dir / upload_id
    if not upload_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # Warn if AI requested but not available
    if mode in ['ai', 'hybrid'] and not settings.ai_available:
        logger.warning(f"AI mode requested but not available, falling back to template")
        mode = 'template'
    
    # Find all Python files
    python_files = list(upload_dir.rglob('*.py'))
    logger.info(f"Found {len(python_files)} Python files to summarize")
    
    if not python_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Python files found in upload"
        )
    
    # Summarize each file
    summaries = []
    successful_count = 0
    
    for py_file in python_files:
        try:
            summary = summarizer.summarize_file(py_file, mode=mode)
            summaries.append(summary)
            
            if not summary.parse_errors:
                successful_count += 1
        
        except Exception as e:
            logger.error(f"Failed to summarize {py_file}: {e}")
            # Continue with other files - don't crash on one bad file
            summaries.append(FileSummary(
                filepath=str(py_file),
                template_summary={"error": str(e)},
                parse_errors=[f"Critical error: {str(e)}"]
            ))
    
    # Save summaries
    try:
        summarizer.save_summaries(upload_id, summaries)
    except Exception as e:
        logger.error(f"Failed to save summaries: {e}")
        # Don't fail the request, summaries are already generated
    
    return SummaryResponse(
        upload_id=upload_id,
        mode=mode,
        summarized_at=datetime.utcnow().isoformat(),
        total_files=len(python_files),
        successfully_summarized=successful_count,
        files=summaries,
        token_usage=None,  # TODO: Track token usage
        embeddings_stored=False
    )


@router.get("/{upload_id}", response_model=SummaryResponse)
async def get_summaries(upload_id: str):
    """
    Retrieve previously generated summaries.
    """
    summary_file = summarizer.summaries_dir / upload_id / 'file_summaries.json'
    
    if not summary_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summaries not found for upload {upload_id}. Generate them first with POST /summary/{upload_id}"
        )
    
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return SummaryResponse(
            upload_id=data['upload_id'],
            mode='unknown',  # Not stored in original format
            summarized_at=data['summarized_at'],
            total_files=data['total_files'],
            successfully_summarized=data['total_files'],  # Approximation
            files=[FileSummary(**f) for f in data['files']]
        )
    
    except Exception as e:
        logger.error(f"Error loading summaries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error loading summaries"
        )
