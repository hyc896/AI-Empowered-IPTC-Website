-- 为 mp_nikkei_asia_ai_messages 表添加字段增强服务需要的字段

USE message_platform;

-- 先清空表数据
TRUNCATE TABLE mp_nikkei_asia_ai_messages;

-- 1. 添加 industry_tags 字段（行业标签，逗号分隔）
ALTER TABLE mp_nikkei_asia_ai_messages 
ADD COLUMN industry_tags VARCHAR(200) DEFAULT NULL COMMENT '行业标签（逗号分隔，最多3个）';

-- 2. 添加 ai_tag 字段（AI分类标签）
ALTER TABLE mp_nikkei_asia_ai_messages 
ADD COLUMN ai_tag VARCHAR(50) DEFAULT NULL COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）';

-- 3. 修改 region 字段类型，允许存储更详细的地区信息
ALTER TABLE mp_nikkei_asia_ai_messages 
MODIFY COLUMN region VARCHAR(200) DEFAULT NULL COMMENT '地区（如：中国/广东省/深圳市）';

-- 显示表结构
DESCRIBE mp_nikkei_asia_ai_messages;
