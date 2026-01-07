"""
Embedding cache optimization for multi-codebase scenarios.
Reduces redundant computation by sharing common chunks across uploads.
"""
import hashlib
import json
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from utils.logger import setup_logger

logger = setup_logger(__name__)


class EmbeddingCacheManager:
    """
    Manages cached embeddings to avoid redundant computation.
    Uses content-based hashing to identify identical code chunks.
    """
    
    def __init__(self, cache_dir: Path = Path("embeddings_cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
        # In-memory index: hash -> embedding_id
        self.hash_to_embedding: Dict[str, str] = {}
        
        # Track which uploads use which embeddings
        self.upload_embeddings: Dict[str, Set[str]] = defaultdict(set)
        
        # Statistics
        self.cache_hits = 0
        self.cache_misses = 0
        
        self._load_index()
    
    def _load_index(self):
        """Load existing embedding index from disk."""
        index_file = self.cache_dir / "embedding_index.json"
        
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                    self.hash_to_embedding = data.get('hash_to_embedding', {})
                    
                    # Convert upload embeddings back to sets
                    upload_emb = data.get('upload_embeddings', {})
                    self.upload_embeddings = {
                        k: set(v) for k, v in upload_emb.items()
                    }
                    
                logger.info(f"Loaded embedding index: {len(self.hash_to_embedding)} cached embeddings")
            except Exception as e:
                logger.warning(f"Failed to load embedding index: {e}")
    
    def _save_index(self):
        """Save embedding index to disk."""
        index_file = self.cache_dir / "embedding_index.json"
        
        try:
            data = {
                'hash_to_embedding': self.hash_to_embedding,
                'upload_embeddings': {
                    k: list(v) for k, v in self.upload_embeddings.items()
                },
                'updated_at': datetime.utcnow().isoformat()
            }
            
            with open(index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save embedding index: {e}")
    
    def compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_cached_embedding(self, content: str) -> Optional[str]:
        """
        Check if embedding exists for this content.
        
        Args:
            content: Code content to check
            
        Returns:
            embedding_id if cached, None otherwise
        """
        content_hash = self.compute_content_hash(content)
        
        if content_hash in self.hash_to_embedding:
            self.cache_hits += 1
            embedding_id = self.hash_to_embedding[content_hash]
            logger.debug(f"Cache HIT for hash {content_hash[:8]}... -> {embedding_id}")
            return embedding_id
        else:
            self.cache_misses += 1
            logger.debug(f"Cache MISS for hash {content_hash[:8]}...")
            return None
    
    def store_embedding(
        self,
        content: str,
        embedding_id: str,
        upload_id: str
    ):
        """
        Store embedding ID for content.
        
        Args:
            content: Code content
            embedding_id: ID of stored embedding
            upload_id: Upload that generated this embedding
        """
        content_hash = self.compute_content_hash(content)
        
        # Store hash -> embedding mapping
        self.hash_to_embedding[content_hash] = embedding_id
        
        # Track which upload uses this embedding
        self.upload_embeddings[upload_id].add(embedding_id)
        
        # Save index
        self._save_index()
        
        logger.debug(f"Stored embedding {embedding_id} for hash {content_hash[:8]}...")
    
    def get_upload_embeddings(self, upload_id: str) -> Set[str]:
        """Get all embedding IDs used by an upload."""
        return self.upload_embeddings.get(upload_id, set())
    
    def find_shared_embeddings(
        self,
        upload_id1: str,
        upload_id2: str
    ) -> Set[str]:
        """
        Find embeddings shared between two uploads.
        Indicates identical code chunks.
        """
        emb1 = self.upload_embeddings.get(upload_id1, set())
        emb2 = self.upload_embeddings.get(upload_id2, set())
        
        shared = emb1 & emb2
        logger.info(f"Shared embeddings between {upload_id1} and {upload_id2}: {len(shared)}")
        
        return shared
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_cached_embeddings': len(self.hash_to_embedding),
            'total_uploads_tracked': len(self.upload_embeddings),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size_bytes': self._estimate_cache_size()
        }
    
    def _estimate_cache_size(self) -> int:
        """Estimate total cache size in bytes."""
        total_size = 0
        
        for embedding_file in self.cache_dir.glob("*.json"):
            try:
                total_size += embedding_file.stat().st_size
            except:
                pass
        
        return total_size
    
    def cleanup_upload(self, upload_id: str):
        """
        Remove embeddings for a deleted upload.
        Only removes if no other uploads share them.
        """
        if upload_id not in self.upload_embeddings:
            return
        
        embeddings = self.upload_embeddings[upload_id]
        
        # Check if other uploads use these embeddings
        for embedding_id in embeddings:
            # Count how many uploads use this embedding
            usage_count = sum(
                1 for emb_set in self.upload_embeddings.values()
                if embedding_id in emb_set
            )
            
            # If only this upload uses it, we could delete the embedding file
            # But for safety, we'll keep it (orphaned embeddings cleaned up separately)
            if usage_count == 1:
                logger.debug(f"Embedding {embedding_id} now orphaned (was only used by {upload_id})")
        
        # Remove from tracking
        del self.upload_embeddings[upload_id]
        self._save_index()
        
        logger.info(f"Cleaned up embedding tracking for {upload_id}")
    
    def find_duplicate_chunks(
        self,
        upload_id1: str,
        upload_id2: str
    ) -> List[Dict]:
        """
        Find duplicate code chunks between uploads.
        
        Returns:
            List of {content_hash, embedding_id, locations} for duplicates
        """
        shared_embeddings = self.find_shared_embeddings(upload_id1, upload_id2)
        
        duplicates = []
        for embedding_id in shared_embeddings:
            # Find content hash for this embedding
            content_hash = None
            for hash_val, emb_id in self.hash_to_embedding.items():
                if emb_id == embedding_id:
                    content_hash = hash_val
                    break
            
            if content_hash:
                duplicates.append({
                    'content_hash': content_hash,
                    'embedding_id': embedding_id,
                    'uploads': [upload_id1, upload_id2]
                })
        
        logger.info(f"Found {len(duplicates)} duplicate chunks between uploads")
        return duplicates


# Global cache manager instance
_cache_manager: Optional[EmbeddingCacheManager] = None


def get_embedding_cache() -> EmbeddingCacheManager:
    """Get or create global embedding cache manager."""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = EmbeddingCacheManager()
    
    return _cache_manager
