# -*- coding: utf-8 -*-

"""
Message Platform API 客户端
用于从统一消息平台获取消息
"""

import os
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MessagePlatformClient:
    """Message Platform API 客户端"""

    def __init__(self):
        self.base_url = os.getenv('MESSAGE_PLATFORM_API_URL', 'http://8.153.174.176:11528')
        self.timeout = int(os.getenv('MESSAGE_PLATFORM_API_TIMEOUT', '30'))
        self.client_id = os.getenv('MESSAGE_PLATFORM_CLIENT_ID', '')
        self.api_key = os.getenv('MESSAGE_PLATFORM_API_KEY', '')

    def _get_headers(self):
        """获取请求头（包含认证信息）"""
        headers = {'Content-Type': 'application/json'}
        if self.client_id:
            headers['X-Client-ID'] = self.client_id
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def fetch_recent_messages(
        self,
        hours: int = 3,
        limit: int = 1000,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取最近的消息

        Args:
            hours: 时间范围（小时）
            limit: 返回数量限制
            source_type: 消息源类型（可选）
            source_id: 消息源ID（可选）

        Returns:
            消息列表
        """
        try:
            url = f"{self.base_url}/search/messages"
            params = {
                'hours': hours,
                'limit': limit,
                'offset': 0
            }

            if source_type:
                params['source_type'] = source_type
            if source_id:
                params['source_id'] = source_id

            logger.info(f"【API客户端】请求消息: hours={hours}, limit={limit}")

            response = requests.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()

            messages = response.json()
            logger.info(f"【API客户端】获取到 {len(messages)} 条消息")

            return messages

        except requests.exceptions.Timeout:
            logger.error(f"【API客户端】请求超时: {self.base_url}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"【API客户端】请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"【API客户端】未知错误: {e}")
            return []

    def get_sources(self) -> List[Dict[str, Any]]:
        """
        获取消息源列表

        Returns:
            消息源列表
        """
        try:
            url = f"{self.base_url}/mp/v1/sources"
            response = requests.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()

            sources = response.json()
            logger.info(f"【API客户端】获取到 {len(sources)} 个消息源")

            return sources

        except Exception as e:
            logger.error(f"【API客户端】获取消息源失败: {e}")
            return []
