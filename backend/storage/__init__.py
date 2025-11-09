# -*- coding: utf-8 -*-

"""
PersonalAgent Storage module
Vector and document storage backends
"""

from .chromadb_storage import ChromaDBStorage
from typing import Optional

# 全局实例
_chromadb_storage: Optional[ChromaDBStorage] = None

def get_chromadb_storage() -> Optional[ChromaDBStorage]:
    """获取全局ChromaDB存储实例"""
    global _chromadb_storage
    if _chromadb_storage is None:
        _chromadb_storage = ChromaDBStorage()
    return _chromadb_storage

def initialize_chromadb(config: dict) -> bool:
    """初始化全局ChromaDB存储"""
    storage = get_chromadb_storage()
    return storage.initialize(config)

__all__ = ['ChromaDBStorage', 'get_chromadb_storage', 'initialize_chromadb']
