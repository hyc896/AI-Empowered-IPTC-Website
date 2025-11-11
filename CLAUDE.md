当创建新文件或完成新功能时，必须遵循以下顺序：
1. 阅读"项目架构.md"文件，确保理解项目结构和目标。
2. 针对涉及的每一个包，你都需要运用context7进行查询，获取其最新版本和主要内容。
3. 基于你的理解，进行plan，计划需要新增的后端模块结构，所有SQLAlchemy实体表结构，所有新增文件和函数的意义及出入参。
4. 开始撰写。撰写过程中不要做非必要的回退和补丁。
5. 撰写完成后，修改"项目架构.md"，毫无缺漏的更新项目的文件夹架构图，新增功能的全链路中涉及的所有函数、变量、SQLAlchemy实体结构。每个模块都要有详细的中文说明。不准写其余无关内容，不准加入任何emoji符号。

注意：所有代码放在/backend文件夹中。

代码遵循KISS（keep it simple and stupid）原则，保证代码简洁且无编译错误。

# 文档质量控制规范（Documentation Review Checklist）

## 文档审查检查清单

在修改CLAUDE.md、项目架构.md或任何agent文档（.claude/agents/*.md）后，必须执行以下检查清单：

### 1. 架构一致性验证
- [ ] **代码实际 vs 文档描述**：文档描述的架构是否与backend/代码实现完全一致？
  - 检查方法：Read backend/database/entities.py，对照文档中的表结构描述
  - 反例：文档说"新消息源使用统一表"，但代码中每个源都是独立表
- [ ] **实体类引用准确性**：文档中提到的ORM类名是否都在entities.py中存在？
  - 检查方法：Grep "class.*Message.*Base" backend/database/entities.py
  - 反例：文档提到InternationalMessage，但entities.py中已删除该类
- [ ] **表名一致性**：文档中的mysql_table名称与entities.py的__tablename__完全匹配？
  - 检查方法：对比文档中的表名与代码中的__tablename__定义
  - 反例：文档说mp_international_messages，代码是mp_partnership_ai_messages

### 2. 技术栈与框架准确性
- [ ] **ORM框架引用正确**：message_platform项目使用SQLAlchemy，personal_agent项目使用TypeORM
  - message_platform文档必须写"SQLAlchemy ORM"
  - personal_agent文档必须写"TypeORM"
  - 检查方法：Grep "TypeORM\|SQLAlchemy" 文档路径
- [ ] **编程语言一致**：message_platform是Python项目，personal_agent是Node.js/TypeScript项目
- [ ] **数据库配置准确**：文档中的数据库名、端口、路径是否与实际环境一致？
  - message_platform数据库：message_platform（非personal_agent）
  - 检查方法：Read backend/config/__init__.py确认实际配置

### 3. 路径与文件位置验证
- [ ] **文件路径准确性**：文档中的文件路径是否实际存在？
  - 检查方法：Glob "backend/sources/*/collector.py"验证采集器路径
  - 反例：文档写backend/services/message/sources/，实际是backend/sources/
- [ ] **API路径参数格式**：文档中的API路径使用单花括号{source_id}，不是双花括号
  - 检查方法：Grep "{{[a-z_]+}}" 文档路径（应该为0结果）
  - 正确示例：/api/v1/sources/{source_id}
  - 错误示例：/api/v1/sources/{{source_id}}

### 4. 格式规则范围明确性
- [ ] **双花括号规则适用范围**：是否明确说明双花括号{{}}仅用于Python f-string中的提示词字面量？
  - 必须包含的说明：
    - "仅适用于提示词字面量"
    - "不适用于Python字典定义"
    - "不适用于文档中的API路径参数"
  - 检查方法：搜索文档中关于花括号的规则描述
- [ ] **规则示例完整性**：格式规则是否提供了正确和错误的对比示例？

### 5. 概念解释完整性
- [ ] **"为什么"的解释**：重要架构决策是否包含"为什么这样设计"的说明？
  - 必须解释的决策：
    - 为什么每个消息源一张独立表？
    - 为什么旧表保持现状不改？
    - 为什么使用@hybrid_property而非直接改表结构？
  - 检查方法：搜索"为什么"、"设计理由"、"架构决策"等关键词
- [ ] **术语定义清晰**：专业术语是否有明确定义或上下文说明？
  - 示例：ORM Registry、external_id、@hybrid_property、双轨制ORM架构

### 6. 字段映射与命名规范
- [ ] **统一字段标准文档化**：2025统一字段标准是否完整列出所有核心字段？
  - 必须包含：id, source_id, external_id, title, content, summary, provider, published_at, crawled_at, url
- [ ] **禁止字段明确列出**：是否明确禁止image_url, source_url, author, seq等字段？
- [ ] **字段映射规则清晰**：网页字段→数据库字段的映射规则是否有表格说明？
  - 示例：post_id/article_id → external_id

### 7. 代码示例准确性
- [ ] **代码片段可运行**：文档中的代码示例是否语法正确、可直接运行？
  - 检查Python字典：应该是{"key": "value"}不是{{"key": "value"}}
  - 检查SQL语句：是否有语法错误
- [ ] **示例与实际代码一致**：示例代码的风格、命名是否与项目实际代码一致？
  - 检查方法：Read类似功能的实际代码文件进行对比

### 8. 交叉引用验证
- [ ] **多文档一致性**：CLAUDE.md、项目架构.md、agent文档之间的描述是否一致？
  - 检查点：ORM框架名称、数据库名称、表结构描述、文件路径
  - 检查方法：在所有文档中Grep同一概念，对比描述是否一致
- [ ] **文档与代码同步**：代码更新后是否同步更新了所有相关文档？
  - 示例：新增PartnershipAIMessage后，项目架构.md是否更新了实体列表？

### 9. 配置与环境准确性
- [ ] **环境变量正确**：文档中的环境变量名、默认值是否与config代码一致？
- [ ] **端口号准确**：文档中的端口号是否与实际运行端口一致？
  - message_platform: 11528
  - personal_agent: 11527
- [ ] **数据库连接信息**：MySQL、ChromaDB的host、port、database名称是否正确？

### 10. 实战验证
- [ ] **实际运行测试**：文档中的操作步骤是否经过实际运行验证？
  - SQL注册脚本是否能成功执行？
  - 采集器是否能成功运行？
  - API调用示例是否返回正确结果？
- [ ] **错误场景覆盖**：常见问题排查章节是否覆盖实际遇到的错误？

## 文档修复工作流

当发现文档错误时，按以下步骤修复：

1. **定位所有相关文档**：
   - Grep错误描述关键词，找出所有包含该错误的文档
   - 示例：Grep "InternationalMessage" **/*.md

2. **追溯根本原因**：
   - 为什么会出现这个错误？是架构理解错误？还是代码更新后文档未同步？
   - 是否有其他地方也可能存在类似错误？

3. **制定修复计划**：
   - 列出所有需要修改的文档和位置
   - 按优先级排序（P0: 致命错误, P1: 准确性问题, P2: 改进建议）

4. **系统性修复**：
   - 一次性修复所有相关文档，避免遗漏
   - 修复后执行本检查清单，确保质量

5. **验证修复效果**：
   - Grep验证错误描述已完全删除
   - Read验证修改后的描述准确无误
   - 对比代码确认文档与实现一致

## 使用本检查清单的时机

**强制执行**：
- 修改CLAUDE.md、项目架构.md后
- 创建或修改.claude/agents/*.md文档后
- 新增数据库表、ORM实体后
- 重大架构调整后

**建议执行**：
- 发现代码与文档不一致时
- 用户反馈文档理解困难时
- 新成员加入项目前（确保文档准确）

# 架构设计原则（必须遵守）

## Fail Fast原则（快速失败）
- 错误应在启动时发现，而非运行时暴露给用户
- 配置错误应阻止服务启动，并提供详细的错误信息
- 启动验证机制检查配置与代码的一致性
- 提供具体的修复建议，而非模糊的错误提示

## 配置与代码一致性
- 动态配置必须与代码定义完全一致
- 启动时自动验证配置完整性
- 使用ORM Registry自动注册机制，避免手动维护映射表
- 配置表名必须与entities.py中的__tablename__完全匹配

## 自动化优于手动
- 优先使用自动注册机制（ORM Registry）
- 避免手动维护映射表（容易遗漏）
- 新增功能时减少手动同步点
- 工具脚本自动化常见任务（如fix_table_names.py）

## 防御式编程
- 启动时验证配置，运行时仍要检查有效性
- 单个模块错误不应影响整体服务
- 详细日志记录异常路径和中间状态
- 使用白名单机制防止配置注入

## LLM交互的隐藏陷阱与防护（message_platform特有）

本项目大量使用LLM进行翻译、摘要生成等任务。以下经验教训来自真实生产问题，必须严格遵守。

### LLM提示词格式的反模式

**问题案例**：2025年11月arXiv翻译任务中，415条记录显示100%成功，实际有8条幻觉输出，LLM回复"请提供您需要翻译的英文摘要内容"而非执行翻译。

**根本原因**：
1. 使用标签式格式触发LLM的"模板填充"心理模型
2. 提示词末尾留空白行，LLM认为在等待用户输入
3. 格式示例：
```
原文：
{text}

中文翻译：
```
最后的"中文翻译："后面是空的，LLM误认为这是待填充的模板框架

**正确做法**：
- 使用system/user消息结构明确分离角色和任务
- System消息定义角色和规则
- User消息直接提供待处理文本
- 避免任何"待填充"的视觉暗示
- 示例参考：backend/llm/translator.py的_build_messages方法

**为什么重要**：
- 标签式格式会让LLM进入"引导模式"而非"执行模式"
- 此类幻觉不包含明显错误标记，难以通过简单检查发现
- 需要输出验证机制才能检测

### LLM输出验证的必要性

**问题案例**：翻译脚本统计显示100%成功率，实际包含多种幻觉输出。

**幻觉演化历史**：
- 第一阶段（2025年初）：353条记录包含模板占位符`{{abstract}}`、`{{translation}}`
- 第二阶段（2025年11月）：8条记录包含引导式回复"请提供您需要翻译的内容"
- 预期未来：幻觉形式会继续演化

**教训**：
1. 永远不要信任LLM的输出，必须验证
2. 表面成功率可能掩盖深层问题
3. 单一检测条件有盲区（只检查降级标记会遗漏幻觉）
4. 需要多种幻觉模式检测：
   - 模板占位符：`{{variable}}`
   - 引导式回复："请提供"、"我将为您"
   - 元描述："以下是翻译结果"、"翻译如下"
   - LaTeX公式误判：需要精确正则排除合法大括号

**防护机制**（已在translator中实现）：
- _is_hallucination()方法检测多种幻觉模式
- 检测到幻觉自动触发降级策略
- 返回截断原文而非幻觉内容
- 参考：backend/llm/translator.py第92-132行

### SQL查询的细节陷阱

**问题案例**：查询失败记录时，`LIKE '%[AI翻译%'`无法匹配包含`[AI翻译暂不可用]`的记录。

**SQL特殊字符转义规则**：
- 方括号在SQL LIKE中有特殊含义，必须转义
- 正确写法：`LIKE '%\\[AI翻译%'`
- 错误写法：`LIKE '%[AI翻译%'`（匹配失败）

**过度匹配的代价**：
- `LIKE '%{{%'`会误判LaTeX数学公式中的合法大括号
- LaTeX示例：`O(d^{\beta - \frac{1}{2}})`包含合法的`}}`
- 解决方案：使用精确正则匹配`{{variable}}`模式

**查询条件权衡**：
- 宽松条件：覆盖率高但误判多（如匹配所有`{{`）
- 严格条件：精确但可能遗漏（如只匹配特定模板）
- 建议策略：先用精确条件查询，验证后再考虑放宽

### 数据质量监控原则

**核心原则**：统计数字不可信，必须抽样验证实际内容。

**监控频率**：
- 大规模操作后：抽查10-20条实际内容
- 定期检查：每周抽查异常模式
- 新功能上线：小批量测试（5-10条）→验证→大批量执行

**异常模式演化追踪**：
- 记录每次发现的新幻觉形式
- 更新检测规则覆盖新模式
- 定期回顾历史问题，防止回归

**验证清单**：
- 输出内容是否符合预期格式
- 是否包含已知幻觉模式
- 长度是否合理（过长/过短都异常）
- 语言是否正确（中文/外文）

### 小批量测试的重要性

**问题案例**：初次测试5条翻译成功，全量执行415条时出现8条失败。

**测试策略**：
1. 初次验证：5-10条样本
2. 扩大范围：50-100条验证
3. 全量执行：确认无问题后
4. 持续监控：执行后抽查结果

**为什么小样本不够**：
- LLM输出有随机性
- 边缘情况出现概率低
- 5条成功≠1000条都成功

配置文档撰写策略：
1. 在任何配置文档（如requirements.txt，config.yaml等）中，禁止撰写任何的版本号。如果一定要写，就写latest。
2. 在任何readme中，启动方式必须写完整，且必须用分号分隔并直接写在一行内，便于直接复制粘贴到终端运行。

# 代码修改修复策略
## 请你遵循以下代码修改/修复策略的工作流：
## 1. 首先，定位目前用户需要你解决的问题——它到底在哪里，是什么？用Grep搜索错误信息/关键字快速定位，用Read读取相关代码文件了解上下文，用Glob找到相关模块的所有文件
## 2. 纵向分析：链路追踪——从该问题的表象出发，对代码进行请求响应生命周期的全链路追踪，即通过代码搜索，完整的遍历PersonalAgent调用 → message_platform API → 服务层 → 数据库的全链路中的所有涉及函数，变量和字段，重点检查DTO和实体映射，观察每两个函数间的出入参是否完全对齐？函数间是否有不一致的逻辑存在？与数据库字段的对应调用关系是否准确？
## 3. 横向分析：相似功能对比——在纵向分析的基础上，对代码进行横向分析，即观察与每个函数相类似的，临近的功能代码中是否存在被重复定义的变量、字段与不一致的实现逻辑，如果有，请指出。
## 4. 联网搜索：查看项目内类似功能的实现模式，使用context7 MCP搜索相关库文档找到标准示范。如果context7可以解决，就不要使用Web Search。
## 5. 深度思考：将上述结果进行深度思考，得出最终的修改方案，制定具体的修改步骤而不是抽象描述。
## 代码遵循KISS（keep it simple and stupid）原则，保证代码简洁且无编译错误。
## 请务必保证你确定了问题的根本成因，且确定了问题的绝对正确解决方案再停止思考分析，而不是鲁莽的进入调试阶段。Ultrathink。

## 代码修复实战经验（必须遵守）

### 数据结构与类型检查
- 在使用任何数据结构前，必须先用Read工具查看其定义和返回格式，不能凭猜测
- 遍历字典时明确使用 .items() 返回(key, value) 或 .values() 返回值列表
- 应使用公开方法而非直接访问私有属性（如用 get_all_sources() 而非 ._sources）
- 使用字段前必须用 hasattr() 或 .get() 检查是否存在
- 类型转换要防护：str(record_id) 防止ID是整数类型

### 唯一标识与去重策略
- ChromaDB的 upsert(ids=[...]) 中，ID必须是稳定的唯一标识，绝不能用 uuid.uuid4() 动态生成
- 应使用业务唯一字段：seq、item_id、url 等，回退策略：seq or item_id or url or uuid.uuid4()
- 去重逻辑需要多级降级策略，优先级：url > id > title > 内容哈希
- 不能因为某个字段为空就跳过记录，空值时应使用备用字段或哈希值

### 参数与配置一致性
- 工具参数定义的 "default" 只是文档说明，实际代码中的 kwargs.get("limit", 10) 才是真正的默认值，两处必须一致
- 同一个概念在不同地方的字段名必须统一（如enabled不能在代码中写成active）
- 对于不同数据源的字段差异，代码中必须做适配映射（如 seq vs item_id, url vs source_url）
- 能够动态加载的配置，坚决不用硬编码。始终避免硬编码。

### 日志与调试
- 日志要记录关键中间状态：检索到多少条、去重前后数量、相似度、批次进度等
- 错误日志必须包含完整上下文：哪个消息源、哪个步骤、什么参数
- 从日志分析问题的步骤：看数量→检查参数传递→看重复→检查去重逻辑→看失败→检查链路
- 启动日志必须分类：【启动】【数据库初始化】【ChromaDB初始化】【采集器】等

### 批量操作与容错
- 向量化API调用必须分批处理（每批50条），避免超时或内存溢出
- 数据库差集检查应限制范围（默认最近1000条），不要全表扫描
- 单条记录失败不应中断整体流程：try-except-continue
- 启动时的后台任务失败不应导致服务无法启动

### 防御式编程
- 使用 .get() 而不是直接访问字典键：source.get('name', 'unknown')
- 检查集合是否为空再操作：if not records: return []
- 时间格式转换要处理None：published_at.isoformat() if published_at else ''
- 异步函数必须用 await 调用，Windows环境需要设置 WindowsProactorEventLoopPolicy()

### API设计标准（本项目强制要求）

**原则：全系统统一为RESTful标准格式**

- 后端直接返回数据对象，不包装成{{success, data}}格式
- 使用HTTP状态码表示成功/失败：200 OK, 201 Created, 204 No Content, 404 Not Found, 500 Internal Server Error
- DELETE端点返回HTTP 204 No Content，无响应体
- 所有端点必须明确定义response_model
- 与PersonalAgent的API调用格式必须完全一致

#### HTTP状态码使用规范
- 200 OK：GET/PUT成功，返回数据
- 201 Created：POST成功创建，返回新对象
- 204 No Content：DELETE成功，无返回内容
- 400 Bad Request：参数错误
- 404 Not Found：资源不存在
- 500 Internal Server Error：服务器错误

#### 为什么选择RESTful而非包装格式？
1. 符合HTTP协议语义（状态码已表示成功/失败）
2. 与主流框架一致（FastAPI、Stripe API、GitHub API）
3. FastAPI的 response_model 自动文档和类型校验
4. 减少数据嵌套层级，降低出错概率
5. 与PersonalAgent集成时保持一致性

#### 检查清单（新增API时必须遵守）
- [ ] 后端直接返回数据对象，不包装 `{success, data}`
- [ ] DELETE端点返回 `status_code=204`
- [ ] 所有response_model明确定义
- [ ] 与PersonalAgent的message_platform_client调用方式一致
- [ ] 测试通过

### 消息源配置驱动原则（message_platform特有）

- 所有消息源必须在mp_message_sources表注册
- 消息源的category字段决定API中的source_type参数
- 消息源的config字段（JSON）存储采集器配置和chroma_collection名称
- 新增消息源会自动同步到PersonalAgent的工具描述，无需修改代码

### ORM使用规范（message_platform特有）

**ORM双轨制架构（本项目实践）**：

本项目采用双轨制ORM架构，根据使用场景选择不同的绑定方式：

1. **静态绑定**：直接使用ORM类（采集器、统计服务）
   - 优点：编译时检查、类型安全、性能最优
   - 适用：固定逻辑、不需要动态扩展的场景
   - 示例：`db.query(TongHuaShunMessage).filter(...)`

2. **动态绑定**：通过Registry动态获取ORM类（搜索服务）
   - 优点：易扩展、配置驱动、支持动态启用禁用
   - 适用：需要根据配置动态处理多个数据源的场景
   - 示例：`model = registry.get_model(table_name)`

**历史债务统一方案（@hybrid_property映射）**：

旧表（同花顺、Kr36、arXiv）的唯一ID字段不统一（seq/item_id/arxiv_id），通过ORM层属性映射实现代码统一：

```python
class TongHuaShunMessage(Base):
    seq = Column(String(50))

    @hybrid_property
    def external_id(self):
        """统一的外部ID访问接口（映射到seq）"""
        return self.seq

# 统一访问方式
record.external_id  # 自动返回seq/item_id/arxiv_id
db.query(model).filter(model.external_id.in_(ids))  # 查询自动转换
```

优点：
- ✅ 零数据库改动，零数据冗余
- ✅ 代码层面完全统一（新旧表都用external_id）
- ✅ SQLAlchemy自动转换查询条件
- ✅ 新表直接定义external_id字段，无需映射

**ORM类注册规范**：
- 消息表（*_messages）：自动注册到ORM Registry，支持动态查询
- 配置表（MessageSource等）：不注册到Registry，使用静态绑定
- 表名命名规范：`mp_{source_name}_messages`
- 启动时自动扫描entities.py，仅注册以_messages结尾的表
- 配置中的mysql_table必须与__tablename__完全一致（包括mp_前缀）

**配置表名验证清单**：
1. 数据库config.mysql_table → 必须在ORM Registry中注册
2. ORM类__tablename__ → 必须被至少一个消息源配置引用
3. 表名格式统一：统一使用带mp_前缀的格式
4. 启动验证自动检查上述三项

**SQL注入防护**：
- SQLAlchemy ORM自动使用参数化查询
- 即使使用f-string格式化，ORM也会将用户输入作为参数绑定
- 表名映射使用白名单机制（ORM Registry）
- 禁止直接拼接SQL字符串

### 启动验证机制（message_platform特有）

**启动时自动检查项**：

1. ORM类自动注册验证
   - 扫描entities模块中的所有ORM类
   - 验证每个类的__tablename__定义
   - 构建全局ORM Registry映射表

2. 消息源配置完整性
   - 检查config.mysql_table字段存在性
   - 验证表名是否有对应的ORM类
   - 检查ChromaDB collection配置
   - 验证消息源的is_active状态

3. 配置与代码一致性
   - 配置的表名 → ORM类必须存在
   - ORM类 → 配置中必须有引用（检测孤立的ORM类）
   - 表名格式统一性检查

**验证失败处理**：
- 打印详细的验证报告（错误/警告/信息分类）
- 提供具体的修复建议（SQL语句或脚本命令）
- 阻止服务启动（fail_on_error=True）
- 调试模式：设置环境变量SKIP_VALIDATION=1可跳过验证

**验证报告示例**：
```
❌ 错误: 消息源 '同花顺7x24快讯' 配置的表名 'tonghuashun_messages' 未找到对应的ORM类
💡 修复建议:
  1. 运行修复脚本: python backend/scripts/fix_table_names.py
  2. 或手动修改: UPDATE mp_message_sources SET config = JSON_SET(config, '$.mysql_table', 'mp_tonghuashun_messages') WHERE name = '同花顺快讯';
```

**环境变量配置**：
- SKIP_VALIDATION=1：跳过启动验证（仅调试用，生产环境禁止）

### 数据库设计规范（message_platform特有）

**统一字段标准（强制执行）**：

所有新建消息表必须遵循统一字段标准。旧表（同花顺、Kr36、arXiv）保持现状不动。

**核心必备字段（所有新表必须包含，不准增删改）**：

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | varchar(36) | PRIMARY KEY | UUID主键 |
| source_id | varchar(36) | FOREIGN KEY, NOT NULL | 外键→mp_message_sources，ondelete=CASCADE |
| external_id | varchar(100) | INDEX | 外部唯一标识（post_id/article_id/event_id等） |
| title | varchar(500) | NOT NULL | 标题 |
| content | text | NOT NULL | 正文内容 |
| summary | text | NULL | 摘要（优先从网页提取summary字段，无则用content，content>1000字时取前1000字） |
| provider | varchar(500) | NULL | 作者或信息提供方（多个用逗号分隔） |
| published_at | datetime | INDEX | 发布时间 |
| crawled_at | datetime | NOT NULL, INDEX | 抓取时间，默认datetime.now() |
| url | varchar(500) | UNIQUE, NOT NULL | 原文链接（用于去重） |

**严格禁止的字段**：
- 禁止添加 image_url 字段（我们不需要图片）
- 禁止使用 source_url 命名（统一用url）
- 禁止使用 author 命名（统一用provider）
- 禁止使用 seq、item_id、arxiv_id 等作为字段名（统一用external_id）

**字段映射铁律**：
无论网页HTML或API返回的字段名是什么，都必须按照统一标准映射到数据库字段：

| 网页字段示例 | 必须映射为 | 说明 |
|-------------|-----------|------|
| post_id, article_id, event_id | external_id | 外部ID统一字段 |
| authors, author, by | provider | 作者统一字段 |
| permalink, link, href | url | 链接统一字段 |
| excerpt, abstract, description | summary 或 content | 根据长度判断 |

**扩展字段规范**：
- 在核心字段基础上，可根据业务需求添加特殊字段
- 扩展字段命名必须语义明确，采用snake_case
- 常见扩展字段：
  - region（地区：US/EU/UK/GLOBAL等）
  - category（分类）
  - language（语言：en/zh/fr等）
  - tags（JSON数组）
  - metadata（JSON对象，存储其他非标准字段）

**外键与级联删除**：
- 所有消息表必须通过source_id外键关联mp_message_sources
- 外键定义必须包含ondelete="CASCADE"，确保删除消息源时级联删除消息

**去重策略**：
- 新表统一使用url字段去重（UNIQUE约束）
- 旧表保持不变：同花顺url、Kr36 item_id、arXiv arxiv_id
- 插入前务必检查url是否已存在（使用数据库查询或try-except IntegrityError）

**索引设计（强制要求）**：
- idx_source_id：source_id字段
- idx_published_at：published_at字段
- idx_crawled_at：crawled_at字段
- idx_source_published：联合索引(source_id, published_at)
- idx_url：url字段（UNIQUE INDEX）
- idx_external_id：external_id字段（如果该字段有值）

### 数据库表设计决策：为什么每个消息源一张独立表？

**核心原则**：本项目采用"一源一表"架构，每个消息源对应一张独立的MySQL表。

**设计理由**：

1. **字段差异化**：
   - 同花顺有seq、image_url字段
   - Kr36有item_id、kr_route字段
   - arXiv有arxiv_id、doi、journal_ref等学术字段
   - 强行统一到一张表会导致大量NULL字段浪费存储

2. **查询性能优化**：
   - 每个消息源索引策略不同（arXiv需doi索引，同花顺需provider索引）
   - 独立表避免大表扫描，查询效率更高
   - 分区存储降低锁竞争

3. **运维灵活性**：
   - 可独立备份、迁移、优化单个消息源数据
   - 删除消息源时通过CASCADE直接清理，无需复杂WHERE条件
   - 独立表结构变更不影响其他消息源

4. **代码可维护性**：
   - ORM类定义清晰，每个类对应明确的业务实体
   - 类型检查更严格，减少运行时错误
   - 新增消息源无需修改现有表结构

**统一字段标准的作用**：

虽然采用独立表，但2025年起所有新建消息表必须遵循统一字段标准：
- 核心字段名称统一：external_id、provider、url等
- 索引命名统一：idx_source_id、idx_published_at等
- 代码层通过@hybrid_property统一访问接口（旧表兼容）

**新建表的决策流程**：

新增消息源时，默认创建独立表。考虑因素：
- 是否有特殊字段需求？→ 独立表
- 预期数据量是否大（>1万条）？→ 独立表
- 是否需要定制索引策略？→ 独立表
- 字段结构与现有表完全一致且数据量小？→ 可考虑复用（罕见）

**架构演进记录**：

- 早期曾规划mp_external_messages作为通用外部消息表（已弃用）
- 后续规划mp_international_messages作为国际消息源统一表
- 实践发现：Partnership on AI的category、region等扩展字段需求差异大
- 最终决策：改为独立表mp_partnership_ai_messages
- 迁移记录：backend/scripts/migrate_partnership_ai_to_new_table.sql

### 采集器实现规范（message_platform特有）

**标准采集器流程**：
1. 网页抓取（使用Playwright）
2. 数据解析
3. 去重检查（查询数据库）
4. 数据入库
5. 更新source.last_crawled_at

**去重检查必做**：
- 查询数据库检查唯一字段是否已存在
- 使用try-except-continue模式，单条失败不影响批次

**错误处理**：
- 网络请求必须设置timeout
- 捕获Playwright的TimeoutError
- 单个消息解析失败不应中断整体采集
- 日志记录：新增数量、重复数量、失败数量

### 生产环境失败案例教训（必须遵守）

本节来自2025年11月针对5个消息源（RAND、OECD、GovAI、CSIS、CSET）的summary翻译失败大规模问题的深度反思。这些教训适用于整个项目，必须严格遵守。

#### 异步编程的生命周期管理原则

**核心问题**：数据库会话与异步HTTP请求混用导致连接池阻塞。

**铁律**：
- 异步IO操作（HTTP请求、文件读写、外部API调用）绝不在数据库事务上下文中执行
- 数据库会话的生命周期应当尽可能短，完成CRUD后立即关闭
- 预处理模式：先异步处理所有外部依赖，收集结果后再批量写入数据库

**真实后果**：
- RAND、CSIS、CNAS的采集器在`with create_session() as db:`块内调用`translator.translate()`
- 翻译每条消息耗时2-5秒，期间数据库连接被占用
- 多采集器并发运行时快速耗尽连接池，导致全局性能下降和连接超时

**防护检查清单**：
- 代码审查时搜索`with create_session()`块，检查块内是否有`await`关键字
- 所有外部服务调用必须在数据库会话之外完成
- 使用静态分析工具检测会话内的async操作

#### "临时"禁用必定变成永久债务

**核心问题**：OECD采集器中translator被注释禁用长达4个月，原因标注"临时调试"。

**铁律**：
- 禁止在生产代码中使用"临时"、"TODO"、"暂时"等标记
- 任何功能的禁用必须有明确的恢复时间表和责任人
- 注释掉的代码必须在同一个开发周期内删除或恢复

**真实后果**：
- 4个月时间内OECD采集了数千条记录，所有summary为空
- 问题被发现时已无法追溯当初禁用的原因
- 需要大规模数据修复和ChromaDB重建

**防护机制**：
- 代码审查时拒绝包含注释代码的Pull Request
- 使用Git blame追踪注释代码的提交记录，超过72小时自动告警
- 功能开关（Feature Flag）优于代码注释

#### 关注点分离的架构强制执行

**核心问题**：GovAI和CSET在scraping阶段混入了translation逻辑。

**铁律**：
- 采集（scraping）、处理（processing）、存储（storing）三阶段严格分离
- 每个函数只做一件事，函数名必须准确反映其职责
- 数据流单向传递：raw data → processed data → persisted data

**真实后果**：
- 翻译逻辑散落在`_collect_once()`循环中，与DOM解析混合
- 错误难以定位：翻译失败时无法判断是网页结构变化还是LLM问题
- 代码复用困难：无法在其他场景重用scraping逻辑

**架构模式**：
- Scraper负责：从网页提取原始数据，返回字典列表
- Processor负责：数据转换、翻译、验证，返回处理后的字典
- Storer负责：去重检查、数据库插入、向量化

#### 禁止替下游工具做决策

**核心问题**：所有6个采集器都对content进行`[:1000]`截断后再调用translator。

**铁律**：
- 不要假设下游工具的能力边界，把完整输入交给它们处理
- 优化应该由最了解性能瓶颈的模块负责
- 数据截断必须有明确的业务理由，而非"可能会更好"的猜测

**真实后果**：
- Translator内部已实现智能截断和分块翻译，但从未被使用
- 1000字截断导致大量长文档信息丢失
- 下游工具升级后上游截断成为瓶颈

**判断标准**：
- 如果某个操作可以在上游做也可以在下游做，优先让下游做
- 上游仅在明确的性能或业务需求时才做预处理
- 每个截断/过滤操作必须在文档中解释"为什么"

#### 参照标准的建立与强制对照

**核心问题**：6个采集器实现各异，没有统一的"正确示范"。

**铁律**：
- 每类功能必须有一个Golden Example作为参照标准
- 新实现必须与Golden Example进行逐项对照
- Golden Example必须文档化其设计决策

**真实后果**：
- CIGI采集器是唯一正确实现，但未标记为参照标准
- 开发新采集器时重复犯同样的错误
- Code Review缺乏客观评判依据

**操作流程**：
1. 确定Golden Example：backend/sources/cigi/collector.py
2. 新采集器开发时：逐函数对照Golden Example
3. 文档化Golden Example的关键决策：
   - 为什么pre-translation？→ 避免会话阻塞
   - 为什么全文传给translator？→ 信任下游工具
   - 为什么三阶段分离？→ 职责单一原则

#### 隐式假设必须显式验证

**核心问题**：所有6个采集器隐式假设"1000字够用了"，从未验证。

**铁律**：
- 任何数值阈值（长度限制、超时时间、批次大小）必须有数据支撑
- 假设必须写入文档并定期验证
- 设计决策必须可追溯：为什么是1000而不是500或2000？

**验证机制**：
- 在项目文档中维护"关键假设清单"
- 每个假设标注：提出时间、验证方法、上次验证日期
- 定期review假设是否仍然成立

**示例假设清单**：
- 假设：单个summary不超过2000字 → 验证方法：每月统计summary长度分布
- 假设：翻译响应时间<5秒 → 验证方法：监控P95延迟
- 假设：重复消息率<5% → 验证方法：每日统计去重命中率

#### 数据质量的主动监控而非被动发现

**核心问题**：数千条错误数据累积数月才被发现。

**铁律**：
- 关键数据字段必须有自动化质量检查
- 异常模式应触发告警，而非等待用户反馈
- 定期抽样验证统计数字的真实性

**监控维度**：
- Summary为空率：单日超过10%触发告警
- 翻译降级率：包含"[AI翻译暂不可用]"的比例
- Content长度分布：P50/P95是否正常
- 新消息到达率：突然下降可能是采集器失败

**验证频率**：
- 实时监控：错误率、响应时间
- 每日报告：数据质量指标、异常模式
- 每周抽查：随机选取10-20条记录人工检查
- 每月review：假设清单、Golden Example有效性

#### 失败的分级响应机制

**核心问题**：单个采集器的翻译失败不应该导致该消息被丢弃。

**铁律**：
- P0错误（数据库连接失败）：中断流程，人工介入
- P1错误（翻译失败）：降级处理，使用截断原文，记录日志
- P2错误（单条消息解析失败）：跳过该条，继续处理后续

**降级策略实施**：
- 翻译失败 → 返回content前1000字+标记
- 向量化失败 → 跳过ChromaDB，MySQL正常保存
- 单条插入失败 → 记录失败ID，不影响批次

**告警升级路径**：
- 个别失败：记录日志
- 失败率>10%：发送告警
- 失败率>50%：暂停采集器，人工介入

这些教训的根本目标：将隐性的脆弱性转化为显性的防护机制，从被动修复转向主动预防。

### ChromaDB向量存储规范（message_platform特有）

**集合管理**：
- 集合名称从消息源config.chroma_collection字段读取，不使用前缀
- 每个消息源对应一个独立集合

**向量化标准**：
- ID使用业务唯一标识（seq、item_id、arxiv_id），不用uuid.uuid4()
- 元数据必须包含：id, source_id, title, summary, published_at, url
- 批量插入使用upsert操作，防止重复

**向量同步去重逻辑**：
- 多级降级策略：url > id > title > 内容哈希
- 不能因为某个字段为空就跳过记录

**分批处理**：
- 每批50条，防止超时
- 使用BATCH_SIZE常量

**ChromaDB初始化三铁律（必须遵守）**：

**铁律1：配置路径** - `config.get('database', {}).get('chromadb', {})`（不是storage！）

**铁律2：使用前检查** - `if not chroma_storage.is_initialized(): return`

**铁律3：脚本显式初始化** - 使用ConfigManager加载配置（会解析环境变量），然后调用`chroma_storage.initialize(chroma_config)`

**历史教训**：
- 配置路径写成storage.chromadb → 找不到配置
- 直接访问_client私有属性 → AttributeError
- 未检查is_initialized()直接upsert → 'client' attribute错误

### 消息源扩展指南（message_platform特有）

**新增消息源标准流程**：
1. 在backend/sources/new_source/目录创建采集器模块
2. 实现采集器类（包含collect方法）
3. 在CollectorService的COLLECTOR_REGISTRY注册
4. 在数据库mp_message_sources表注册消息源配置
5. 测试验证：采集、去重、入库、向量化
6. PersonalAgent自动同步，无需修改代码

**采集器必须实现**：
- __init__方法接收source_id和config参数
- collect方法返回List[Dict]格式的消息列表
- 实现去重检查逻辑
- 更新last_crawled_at时间戳

## 禁止事项（必须严格遵守）

不准在代码中加入任何TODO，MOCK代码或数据！
不准在代码中加入任何TODO，MOCK代码或数据！
不准在代码中加入任何TODO，MOCK代码或数据！
不准在代码中加入任何TODO，MOCK代码或数据！

- VARCHAR()括号内的数字不要大于500，防止SQL索引过长
- 能够动态加载的配置，坚决不用硬编码。始终避免硬编码。
- 不要在代码中加入任何TODO
- 所有 datetime.utcnow() 替换为 datetime.now()
- 使用ls显示目录，而不是dir。牢记你在bash环境中。
- 在Python代码的f-string或模板引擎中编写大模型提示词时，将花括号{和}用{{和}}转义，避免被解析为变量占位符。**此规则仅适用于提示词字面量**，不适用于：(1)Python字典定义 (2)文档中的API路径参数（应使用单花括号如{source_id}）
- 不要在代码中加入emoji符号

## 常见问题排查（message_platform特有）

**采集器不工作**：
1. 检查mp_message_sources表中is_active是否为1
2. 检查CollectorService是否注册了对应的Collector类
3. 检查日志中是否有异常信息
4. 验证配置中的interval和schedule是否正确

**向量检索无结果**：
1. 检查ChromaDB集合是否存在（查看启动日志）
2. 检查向量同步是否成功（查看统计信息）
3. 检查相似度阈值是否过高（config.yaml中的similarity_threshold）
4. 使用scripts/中的诊断脚本检查数据质量

**API返回404**：
1. 检查路由是否正确注册（main.py中的include_router）
2. 检查端点路径是否正确（/api/v1前缀）
3. 检查FastAPI文档（http://localhost:11528/docs）
4. 查看日志中的路由加载信息

**PersonalAgent无法调用**：
1. 检查message_platform是否启动（/health端点）
2. 检查personal_agent中的MESSAGE_PLATFORM_URL环境变量
3. 检查网络连接（防火墙、端口占用）
4. 查看message_platform_client的健康检查日志
