# LLM集成目录说明

## 目录作用

llm目录提供LLM集成接口，支持多种LLM提供商（OpenAI、Anthropic、自定义LLM）。通过统一的接口设计，可以轻松切换不同的LLM提供商。

## 文件列表

- `__init__.py` - 模块初始化文件
- `base.py` - LLM基类接口定义，所有LLM客户端必须继承此类
- `openai_client.py` - OpenAI客户端实现，支持GPT-4、GPT-3.5等模型
- `anthropic_client.py` - Anthropic客户端实现，支持Claude系列模型

## 技术说明

### LLM基类接口（base.py）

**设计原则**：
- 定义统一的接口规范
- 支持同步和异步两种调用方式
- 使用抽象基类（ABC）强制实现

**核心方法**：
- `generate_async(messages, temperature, max_tokens, **kwargs)` - 异步生成文本
- `generate(messages, temperature, max_tokens, **kwargs)` - 同步生成文本

**消息格式**：
```python
messages = [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "用户输入"}
]
```

### OpenAI客户端（openai_client.py）

**支持的模型**：
- GPT-4（gpt-4）
- GPT-3.5 Turbo（gpt-3.5-turbo）
- 其他OpenAI兼容模型

**核心功能**：
- 异步和同步调用
- 自动重试机制
- 错误处理和日志记录
- 支持自定义base_url（兼容第三方API）

**初始化参数**：
- `api_key` - OpenAI API密钥
- `model` - 模型名称（默认gpt-4）
- `base_url` - API基础URL（可选）

### Anthropic客户端（anthropic_client.py）

**支持的模型**：
- Claude 3.5 Sonnet（claude-3-5-sonnet-20241022）
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku

**核心功能**：
- 异步和同步调用
- System消息提取（Anthropic API要求）
- 错误处理和日志记录

**初始化参数**：
- `api_key` - Anthropic API密钥
- `model` - 模型名称（默认claude-3-5-sonnet-20241022）

## 使用示例

### 使用OpenAI客户端

```python
from graphrag.llm.openai_client import OpenAIClient

# 初始化
client = OpenAIClient(
    api_key="your_openai_api_key",
    model="gpt-4"
)

# 异步调用
messages = [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"}
]
response = await client.generate_async(messages)
print(response)

# 同步调用
response = client.generate(messages)
print(response)
```

### 使用Anthropic客户端

```python
from graphrag.llm.anthropic_client import AnthropicClient

# 初始化
client = AnthropicClient(
    api_key="your_anthropic_api_key",
    model="claude-3-5-sonnet-20241022"
)

# 异步调用
messages = [
    {"role": "system", "content": "你是一个助手"},
    {"role": "user", "content": "你好"}
]
response = await client.generate_async(messages)
print(response)
```

### 实现自定义LLM客户端

```python
from graphrag.llm.base import BaseLLMClient
from typing import List, Dict

class MyCustomLLM(BaseLLMClient):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        # 实现你的LLM API调用逻辑
        response = await self._call_my_api(messages)
        return response

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        # 同步版本
        import asyncio
        return asyncio.run(self.generate_async(messages, temperature, max_tokens, **kwargs))
```

### 与message_platform集成

```python
from graphrag.core.entity_extractor import EntityExtractor
from message_platform.llm import global_llm_manager

# 使用message_platform的LLM客户端
llm_client = global_llm_manager.fast_client

# 初始化实体提取器
extractor = EntityExtractor(llm_client)

# 提取实体
result = await extractor.extract_entities(text)
```

## 扩展方式

### 添加新的LLM提供商

1. 在`llm/`目录创建新文件（如`your_llm_client.py`）
2. 继承`BaseLLMClient`基类
3. 实现`generate_async`和`generate`方法
4. 在`__init__.py`中导出新客户端

示例：

```python
# your_llm_client.py
from .base import BaseLLMClient
from typing import List, Dict

class YourLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "your-model"):
        self.api_key = api_key
        self.model = model

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        # 实现API调用
        pass

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        import asyncio
        return asyncio.run(self.generate_async(messages, temperature, max_tokens, **kwargs))
```

## 注意事项

### API密钥管理

- 使用环境变量存储API密钥
- 不要在代码中硬编码密钥
- 使用`.env`文件管理本地开发环境

### 速率限制

- OpenAI和Anthropic都有速率限制
- 实现重试机制处理429错误
- 使用指数退避策略

### 成本控制

- 监控Token使用量
- 设置合理的`max_tokens`
- 使用较小的模型处理简单任务

### 幻觉检测

- LLM可能产生幻觉输出
- 实体提取器内置幻觉检测机制
- 验证输出格式和内容

### 错误处理

- 捕获API调用异常
- 记录详细的错误日志
- 提供降级策略

### 异步调用

- 优先使用异步方法提高性能
- 避免在同步上下文中调用异步方法
- 使用`asyncio.run()`包装异步调用

### 消息格式

- OpenAI和Anthropic的消息格式略有不同
- Anthropic需要单独提取system消息
- 确保消息格式符合API要求

### 模型选择

- GPT-4：最强大，成本最高
- GPT-3.5 Turbo：性价比高
- Claude 3.5 Sonnet：平衡性能和成本
- 根据任务复杂度选择合适的模型
