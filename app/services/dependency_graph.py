"""
Dependency Graph Builder for Python Projects
Analyzes import statements and constructs dependency relationships
"""
import ast
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class DependencyGraphBuilder:
    """Build and analyze dependency graphs from Python codebases."""
    
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.files_data = {}  # filepath -> imports list
        self.graph = defaultdict(set)  # file -> set of files it imports from
        self.reverse_graph = defaultdict(set)  # file -> set of files that import it
        self.circular_deps = []
        self.missing_imports = []
        
    def build_graph(self, upload_id: str) -> Dict:
        """
        Build complete dependency graph for the uploaded codebase.
        
        Returns:
            Dict containing nodes, edges, circular dependencies, and statistics
        """
        logger.info(f"Building dependency graph for upload_id: {upload_id}")
        
        # Find all Python files
        python_files = list(self.upload_dir.glob("**/*.py"))
        logger.info(f"Found {len(python_files)} Python files")
        
        # Extract imports from each file
        for py_file in python_files:
            rel_path = str(py_file.relative_to(self.upload_dir))
            imports = self._extract_imports(py_file)
            self.files_data[rel_path] = imports
            
        # Build graph relationships
        self._build_relationships()
        
        # Detect circular dependencies
        self._detect_circular_dependencies()
        
        # Generate graph data structure
        graph_data = self._generate_graph_data()
        
        logger.info(f"Graph built: {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")
        
        return graph_data
    
    def _extract_imports(self, filepath: Path) -> List[str]:
        """Extract all import statements from a Python file."""
        imports = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
                
            tree = ast.parse(code, filename=str(filepath))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        
        except SyntaxError as e:
            logger.warning(f"Syntax error in {filepath}: {e}")
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}")
            
        return imports
    
    def _build_relationships(self):
        """Build graph relationships between files based on imports."""
        # Create mapping of module names to file paths
        module_to_file = self._build_module_mapping()
        
        # Build dependency edges
        for file_path, imports in self.files_data.items():
            for import_name in imports:
                # Check if this import refers to a file in our codebase
                target_file = self._resolve_import(import_name, file_path, module_to_file)
                
                if target_file:
                    # Add edge: file_path imports from target_file
                    self.graph[file_path].add(target_file)
                    self.reverse_graph[target_file].add(file_path)
                elif self._is_local_import(import_name):
                    # Track missing local imports
                    self.missing_imports.append({
                        'file': file_path,
                        'import': import_name
                    })
    
    def _build_module_mapping(self) -> Dict[str, str]:
        """Create mapping from module names to file paths."""
        module_map = {}
        
        for file_path in self.files_data.keys():
            # Convert file path to module name
            # e.g., "app/services/parser.py" -> "app.services.parser"
            module_name = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
            module_map[module_name] = file_path
            
            # Also map shorter versions
            parts = module_name.split('.')
            for i in range(len(parts)):
                partial = '.'.join(parts[i:])
                if partial not in module_map:
                    module_map[partial] = file_path
        
        return module_map
    
    def _resolve_import(self, import_name: str, source_file: str, module_map: Dict[str, str]) -> Optional[str]:
        """Resolve an import name to a file path in the codebase."""
        # Direct match
        if import_name in module_map:
            return module_map[import_name]
        
        # Check if it's a submodule of something in our codebase
        parts = import_name.split('.')
        for i in range(len(parts), 0, -1):
            partial = '.'.join(parts[:i])
            if partial in module_map:
                return module_map[partial]
        
        return None
    
    def _is_local_import(self, import_name: str) -> bool:
        """Check if import appears to be from local codebase (not external package)."""
        # Simple heuristic: if it starts with common local patterns
        local_patterns = ['app', 'src', 'lib', 'utils', 'services', 'models', 'routes']
        first_part = import_name.split('.')[0]
        return first_part in local_patterns
    
    def _detect_circular_dependencies(self):
        """Detect circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> bool:
            """DFS to detect cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    self.circular_deps.append(cycle)
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.graph.keys():
            if node not in visited:
                dfs(node, [])
    
    def _generate_graph_data(self) -> Dict:
        """Generate graph data structure for visualization."""
        nodes = []
        edges = []
        
        # Get all unique files (nodes)
        all_files = set(self.files_data.keys())
        
        for file_path in all_files:
            # Calculate node metrics
            imports_count = len(self.graph.get(file_path, set()))
            imported_by_count = len(self.reverse_graph.get(file_path, set()))
            
            nodes.append({
                'id': file_path,
                'label': Path(file_path).name,
                'full_path': file_path,
                'imports_count': imports_count,
                'imported_by_count': imported_by_count,
                'size': max(10, imported_by_count * 5)  # Visual size based on importance
            })
        
        # Build edges
        edge_id = 0
        for source, targets in self.graph.items():
            for target in targets:
                edges.append({
                    'id': edge_id,
                    'from': source,
                    'to': target,
                    'arrows': 'to'
                })
                edge_id += 1
        
        # Calculate statistics
        stats = {
            'total_files': len(all_files),
            'total_dependencies': len(edges),
            'circular_dependencies': len(self.circular_deps),
            'missing_imports': len(self.missing_imports),
            'isolated_files': len([f for f in all_files if not self.graph.get(f) and not self.reverse_graph.get(f)]),
            'most_imported': self._get_most_imported(3),
            'most_imports': self._get_most_imports(3)
        }
        
        return {
            'nodes': nodes,
            'edges': edges,
            'circular_dependencies': self.circular_deps,
            'missing_imports': self.missing_imports,
            'statistics': stats
        }
    
    def _get_most_imported(self, limit: int) -> List[Dict]:
        """Get files that are imported the most."""
        file_counts = [
            {'file': file, 'count': len(importers)}
            for file, importers in self.reverse_graph.items()
        ]
        file_counts.sort(key=lambda x: x['count'], reverse=True)
        return file_counts[:limit]
    
    def _get_most_imports(self, limit: int) -> List[Dict]:
        """Get files that import the most."""
        file_counts = [
            {'file': file, 'count': len(imports)}
            for file, imports in self.graph.items()
        ]
        file_counts.sort(key=lambda x: x['count'], reverse=True)
        return file_counts[:limit]
    
    def get_file_dependencies(self, file_path: str) -> Dict:
        """Get direct dependencies for a specific file."""
        return {
            'file': file_path,
            'imports_from': list(self.graph.get(file_path, set())),
            'imported_by': list(self.reverse_graph.get(file_path, set())),
            'imports_count': len(self.graph.get(file_path, set())),
            'imported_by_count': len(self.reverse_graph.get(file_path, set()))
        }
