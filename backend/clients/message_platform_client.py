# -*- coding: utf-8 -*-
"""
消息平台API客户端
用于从消息平台获取消息数据
"""

import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MessagePlatformClient:
    """消息平台API客户端"""

    def __init__(self, base_url: str = None, timeout: int = 30):
        import os
        if base_url is None:
            base_url = os.getenv("MESSAGE_PLATFORM_API_URL", "http://8.153.174.176:11528")
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client_id = os.getenv('MESSAGE_PLATFORM_CLIENT_ID', '')
        self.api_key = os.getenv('MESSAGE_PLATFORM_API_KEY', '')

    def _get_headers(self):
        """获取请求头（包含认证信息）"""
        headers = {}
        if self.client_id:
            headers['X-Client-ID'] = self.client_id
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def get_messages(
        self,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        hours: int = 0
    ) -> Dict[str, Any]:
        """获取消息列表"""
        try:
            url = f"{self.base_url}/search/messages"
            params = {"limit": limit, "offset": offset}

            if source_type:
                params["source_type"] = source_type
            if source_id:
                params["source_id"] = source_id
            if hours > 0:
                params["hours"] = hours

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params, headers=self._get_headers())
                response.raise_for_status()
                messages = response.json()
                total = int(response.headers.get("X-Total-Count", len(messages)))
                return {"messages": messages, "total": total}

        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            raise

    def search_messages(
        self,
        query: str,
        source_type: Optional[str] = None,
        time_range: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """搜索消息"""
        try:
            url = f"{self.base_url}/search/messages"
            payload = {"query": query, "limit": limit}

            if source_type:
                payload["source_type"] = source_type
            if time_range:
                payload["time_range"] = time_range

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=self._get_headers())
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"搜索消息失败: {e}")
            raise


def get_message_platform_client() -> MessagePlatformClient:
    """获取消息平台客户端实例"""
    import os
    base_url = os.getenv("MESSAGE_PLATFORM_API_URL", "http://localhost:11528")
    return MessagePlatformClient(base_url)
