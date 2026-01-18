"""
自定义异常

本模块定义GraphRAG工具包的自定义异常类。
"""


class GraphRAGException(Exception):
    """GraphRAG基础异常"""
    pass


class StorageException(GraphRAGException):
    """存储层异常"""
    pass


class EntityExtractionException(GraphRAGException):
    """实体提取异常"""
    pass


class GraphBuildException(GraphRAGException):
    """图谱构建异常"""
    pass


class ConfigException(GraphRAGException):
    """配置异常"""
    pass


class LLMException(GraphRAGException):
    """LLM调用异常"""
    pass
