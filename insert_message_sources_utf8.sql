-- ============================================================================
-- 消息平台消息源配置数据（UTF-8编码）
-- Message Platform Message Sources Configuration Data (UTF-8)
-- ============================================================================

USE message_platform;

-- 临时禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 清空现有数据
DELETE FROM mp_message_sources;

-- 重新启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 插入消息源配置
INSERT INTO mp_message_sources (id, name, adapter_name, category, display_name, config, schedule, is_active, created_at, updated_at) VALUES

-- 1. The Guardian (UK)
('1f15e34e-c3d7-11f0-b75e-08bfb82ee112', 'guardian', 'guardian', 'news', 'The Guardian (UK)', 
'{"region": "UK", "interval": 3600, "language": "en", "mysql_table": "mp_guardian_messages", "collector_module": "backend.sources.guardian.collector", "chroma_collection": "guardian_news"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 2. Tech in Asia
('1f857861-c3d8-11f0-b75e-08bfb82ee112', 'techinasia', 'techinasia', 'news', 'Tech in Asia', 
'{"region": "Southeast Asia", "interval": 3600, "language": "en", "mysql_table": "mp_techinasia_messages", "collector_module": "backend.sources.techinasia.collector", "chroma_collection": "techinasia"}', 
NULL, 1, NOW(), NOW()),

-- 3. Global Center on AI Governance
('2783bc7c-bf1f-11f0-8cb6-00ff40160484', 'gcg_ai', 'gcg_ai', 'research', 'Global Center on AI Governance (GCG)', 
'{"url": "https://www.globalcenter.ai/research", "region": "ZA", "interval": 604800, "language": "en", "mysql_table": "mp_gcg_ai_messages", "collector_module": "backend.sources.gcg_ai.collector", "chroma_collection": "gcg_ai_research"}', 
'0 0 * * 0', 1, NOW(), NOW()),

-- 4. arXiv学术论文
('282ce629-ab29-495c-9e1f-f59478f3e7ef', 'arxiv', 'ArxivAdapter', 'paper', 'arXiv学术论文', 
'{"interval": 86400, "categories": ["cs.AI", "cs.LG"], "mysql_table": "mp_arxiv_messages", "collector_module": "backend.sources.arxiv.collector", "chroma_collection": "arxiv"}', 
'0 21 * * *', 1, NOW(), NOW()),

-- 5. Wired
('2a3b2567-c4a2-11f0-b75e-08bfb82ee112', 'wired', 'wired', 'news', 'Wired科技新闻', 
'{"region": "美国", "language": "en", "mysql_table": "mp_wired_messages", "collector_module": "backend.sources.wired.collector", "chroma_collection": "wired_tech"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 6. La Nación (阿根廷)
('361b2433-c780-11f0-b359-08bfb82ee112', 'lanacion', 'lanacion', 'news', 'La Nación (阿根廷)', 
'{"region": "阿根廷", "interval": 3600, "language": "es", "mysql_table": "mp_lanacion_messages", "collector_module": "backend.sources.lanacion.collector", "chroma_collection": "lanacion"}', 
'0 */2 * * *', 1, NOW(), NOW()),

-- 7. Axios新闻
('600c78e9-c4a0-11f0-b75e-08bfb82ee112', 'axios', 'axios', 'news', 'Axios新闻', 
'{"region": "美国", "language": "en", "mysql_table": "mp_axios_messages", "collector_module": "backend.sources.axios.collector", "chroma_collection": "axios_news"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 8. VentureBeat
('798eafc5-c040-11f0-8cb6-00ff40160484', 'venturebeat', 'venturebeat', 'news', 'VentureBeat科技媒体', 
'{"region": "US", "interval": 86400, "language": "en", "mysql_table": "mp_venturebeat_messages", "collector_module": "backend.sources.venturebeat.collector", "chroma_collection": "venturebeat"}', 
'0 0 * * *', 0, NOW(), NOW()),

-- 9. Investing.com
('82016605-c316-11f0-bcbb-00ff40160484', 'investing_com_news', 'investing_com', 'news', 'Investing.com General News', 
'{"interval": 30, "mysql_table": "mp_investing_com_messages", "collector_module": "backend.sources.investing_com.collector", "chroma_collection": "investing_com_news"}', 
'*/1 * * * *', 1, NOW(), NOW()),

-- 10. Inteligencia Argentina
('89060cc1-c76d-11f0-b359-08bfb82ee112', 'inteligencia_argentina', 'inteligencia_argentina', 'news', 'Inteligencia Argentina AI', 
'{"region": "阿根廷", "interval": 3600, "language": "es", "mysql_table": "mp_inteligencia_argentina_messages", "collector_module": "backend.sources.inteligencia_argentina.collector", "chroma_collection": "inteligencia_argentina_ai"}', 
'0 */2 * * *', 1, NOW(), NOW()),

-- 11. CNBC Technology
('8c31f770-c4a2-11f0-b75e-08bfb82ee112', 'cnbc', 'cnbc', 'news', 'CNBC Technology', 
'{"region": "美国", "language": "en", "mysql_table": "mp_cnbc_messages", "collector_module": "backend.sources.cnbc.collector", "chroma_collection": "cnbc_tech"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 12. Financial Times Technology
('8d4bdf4e-c4a2-11f0-b75e-08bfb82ee112', 'financial_times', 'financial_times', 'news', 'Financial Times Technology', 
'{"region": "英国", "language": "en", "mysql_table": "mp_financial_times_messages", "collector_module": "backend.sources.financial_times.collector", "chroma_collection": "financial_times_tech"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 13. Ars Technica
('8e6cdcd2-c4a2-11f0-b75e-08bfb82ee112', 'ars_technica', 'ars_technica', 'news', 'Ars Technica', 
'{"region": "美国", "language": "en", "mysql_table": "mp_ars_technica_messages", "collector_module": "backend.sources.ars_technica.collector", "chroma_collection": "ars_technica_tech"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 14. Der Spiegel Netzwelt
('8f951d03-c4a2-11f0-b75e-08bfb82ee112', 'der_spiegel', 'der_spiegel', 'news', 'Der Spiegel Netzwelt', 
'{"region": "德国", "language": "de", "mysql_table": "mp_der_spiegel_messages", "collector_module": "backend.sources.der_spiegel.collector", "chroma_collection": "der_spiegel_tech"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 15. Le Monde Pixels
('90bc559d-c4a2-11f0-b75e-08bfb82ee112', 'le_monde', 'le_monde', 'news', 'Le Monde Pixels', 
'{"region": "法国", "language": "fr", "mysql_table": "mp_le_monde_messages", "collector_module": "backend.sources.le_monde.collector", "chroma_collection": "le_monde_tech"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 16. Times of India Tech
('91e80f16-c4a2-11f0-b75e-08bfb82ee112', 'times_of_india', 'times_of_india', 'news', 'Times of India Tech', 
'{"region": "印度", "language": "en", "mysql_table": "mp_times_of_india_messages", "collector_module": "backend.sources.times_of_india.collector", "chroma_collection": "times_of_india_tech"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 17. TechCrunch
('928ce803-c37a-11f0-88d0-08bfb82ee112', 'techcrunch', 'techcrunch', 'news', 'TechCrunch Tech News', 
'{"region": "GLOBAL", "interval": 7200, "language": "en", "mysql_table": "mp_techcrunch_messages", "collector_module": "backend.sources.techcrunch.collector", "chroma_collection": "techcrunch_messages"}', 
'0 * * * *', 1, NOW(), NOW()),

-- 18. The Hindu Business
('930a3863-c4a2-11f0-b75e-08bfb82ee112', 'the_hindu', 'the_hindu', 'news', 'The Hindu Business', 
'{"region": "印度", "language": "en", "mysql_table": "mp_the_hindu_messages", "collector_module": "backend.sources.the_hindu.collector", "chroma_collection": "the_hindu_tech"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 19. Partnership on AI
('961d6c98-be21-11f0-8cb6-00ff40160484', 'partnership_ai', 'partnership_ai_collector', 'ai_governance', 'Partnership on AI', 
'{"url": "https://partnershiponai.org/blog/", "region": "US", "interval": 86400, "language": "en", "mysql_table": "mp_partnership_ai_messages", "collector_module": "backend.sources.partnership_ai.collector", "chroma_collection": "mp_partnership_ai"}', 
'0 0 0 * * *', 1, NOW(), NOW()),

-- 20. 36氪快讯
('a153c829-a3fd-11f0-b59f-08bfb82ee112', 'kr36', 'kr36_collector', 'news', '36氪快讯', 
'{"url": "https://www.36kr.com/newsflashes", "interval": 180, "mysql_table": "mp_kr36_messages", "collector_module": "backend.sources.kr36.collector", "chroma_collection": "kr36"}', 
'0 */3 * * * *', 1, NOW(), NOW()),

-- 21. BetaKit
('a1f5d25f-c3d8-11f0-b75e-08bfb82ee112', 'betakit', 'betakit', 'news', 'BetaKit加拿大科技新闻', 
'{"region": "加拿大", "interval": 86400, "language": "en", "mysql_table": "mp_betakit_messages", "collector_module": "backend.sources.betakit.collector", "chroma_collection": "betakit_tech_news"}', 
NULL, 1, NOW(), NOW()),

-- 22. Centre for the Governance of AI
('ba2b9387-beea-11f0-8cb6-00ff40160484', 'govai', 'govai', 'news', 'Centre for the Governance of AI', 
'{"url": "https://www.governance.ai/research", "region": "GLOBAL", "interval": 86400, "language": "en", "mysql_table": "mp_govai_messages", "collector_module": "backend.sources.govai.collector", "chroma_collection": "govai_research"}', 
'0 2 * * *', 1, NOW(), NOW()),

-- 23. 证券时报
('cd1acf31-c48b-11f0-b75e-08bfb82ee112', 'securities_times', 'securities_times', 'news', '证券时报', 
'{"region": "CN", "interval": 86400, "language": "zh", "mysql_table": "mp_securities_times_messages", "collector_module": "backend.sources.securities_times.collector", "chroma_collection": "securities_times"}', 
'0 0 */6 * * ?', 1, NOW(), NOW()),

-- 24. Nikkei Asia AI
('d679025d-c304-11f0-bcbb-00ff40160484', 'nikkei_asia_ai', 'nikkei_asia', 'news', 'Nikkei Asia AI', 
'{"url": "https://asia.nikkei.com/Business/Technology/Artificial-intelligence", "interval": 3600, "mysql_table": "mp_nikkei_asia_ai_messages", "collector_module": "backend.sources.nikkei_asia.collector", "chroma_collection": "nikkei_asia_ai"}', 
'0 */1 * * *', 1, NOW(), NOW()),

-- 25. Bloomberg Technology
('dce23340-c495-11f0-b75e-08bfb82ee112', 'bloomberg', 'bloomberg', 'news', 'Bloomberg Technology', 
'{"region": "全球", "language": "en", "mysql_table": "mp_bloomberg_messages", "collector_module": "backend.sources.bloomberg.collector", "chroma_collection": "bloomberg_tech"}', 
'0 */2 * * *', 1, NOW(), NOW()),

-- 26. 同花顺快讯
('e13de063-80a2-4c4b-94ad-90854706106a', 'tonghuashun', 'TongHuaShunAdapter', 'news', '同花顺7x24快讯', 
'{"url": "https://news.10jqka.com.cn/realtimenews.html", "interval": 15, "mysql_table": "mp_tonghuashun_messages", "collector_module": "backend.sources.tonghuashun.collector", "chroma_collection": "tonghuashun"}', 
'*/15 * * * * *', 1, NOW(), NOW()),

-- 27. 华尔街日报科技版
('f158aafb-c49d-11f0-b75e-08bfb82ee112', 'wsj_tech', 'wsj', 'news', '华尔街日报科技版', 
'{"region": "美国", "interval": 3600, "language": "en", "mysql_table": "mp_wsj_messages", "collector_module": "backend.sources.wsj.collector", "chroma_collection": "wsj_tech"}', 
'0 */1 * * *', 1, NOW(), NOW());

-- 验证插入结果
SELECT COUNT(*) as total_sources FROM mp_message_sources;
SELECT name, display_name FROM mp_message_sources ORDER BY name;

