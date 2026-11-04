# django-base-admin 高级可选功能需求文档

| 项目名称 | django-base-admin 高级可选扩展功能 |
| --- | --- |
| 文档版本 | V1.0 |
| 文档状态 | 初稿 |
| 编写日期 | 2026-11-04 |
| 适配主系统 | django-base-admin（Django + Vue3 + MySQL） |
| 配套主文档 | 《后台管理系统需求规格说明书 V1.0》/《附加模块需求说明书 V1.0》 |

---

## 0. 文档说明

本文档整理 **4 项偏高级、按需选用的扩展功能**，各模块复用主系统 RBAC 权限体系、统一返回格式、统一菜单层级缩进 UI 规范，并联动附件管理、消息中心、定时任务等既有模块。每条功能均给出：模块概述、菜单归属、功能需求、数据表结构设计。

**包含的 4 项高级功能清单**

| 序号 | 功能模块 | 说明 |
| --- | --- | --- |
| 1 | 多租户（SaaS） | 多单位数据隔离 |
| 2 | 工单模块 | IT 运维 / 报修 / 需求工单 |
| 3 | 日历日程 | 日程、提醒、排班 |
| 4 | 知识库 | 文档库管理 |

---

# 1. 多租户（SaaS）

## 1.1 模块概述
支持多单位 / 多租户数据隔离，每个租户拥有独立数据空间，适合未来多单位部署或 SaaS 化运营。租户间数据物理隔离（按租户 ID 字段过滤 + 可选独立库）。

> 建议默认**共享库 + 租户字段隔离**方案（成本低、易维护）；若租户数据安全要求高，可扩展为独立库模式。

## 1.2 菜单归属
一级菜单：**系统管理** → 子菜单：**租户管理**

## 1.3 功能需求
- 租户新增、编辑、启停、过期管理；
- 租户套餐 / 配额配置（用户数、存储空间上限，可选）；
- 租户初始化：创建租户管理员、默认角色、部门、字典；
- 数据隔离：所有业务表携带 tenant_id，查询自动追加租户过滤；
- 租户切换：超管可全局切换查看；
- 租户到期冻结、续期。

## 1.4 数据表设计

### 1.4.1 租户表 `sys_tenant`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| tenant_name | varchar(100) | 租户名称 |
| tenant_code | varchar(100) | 租户编码（唯一） |
| status | tinyint | 0停用 1启用 |
| expire_time | datetime | 到期时间 |
| max_user_count | int | 最大用户数 |
| max_storage_mb | bigint | 存储配额（MB） |
| config_json | text | 租户配置 JSON |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 1.4.2 租户用户关联表 `sys_tenant_user`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| tenant_id | bigint | 租户 ID |
| user_id | bigint | 用户 ID |
| is_tenant_admin | tinyint | 是否租户管理员 |
| join_time | datetime | 加入时间 |
| create_time | datetime | 创建时间 |

### 1.4.3 租户套餐表 `sys_tenant_package`（可选）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| package_name | varchar(100) | 套餐名称 |
| max_user_count | int | 用户数上限 |
| max_storage_mb | bigint | 存储配额 |
| price | decimal(10,2) | 价格 |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

> **改造说明**：启用多租户后，全系统业务表需追加 `tenant_id` 字段并在查询层统一过滤（可通过 Django 中间件 / queryset 基类实现）。

---

# 2. 工单模块

## 2.1 模块概述
提供 IT 运维、报修、需求类工单管理，支持工单提交、分派、处理、关闭、催办，可联动工作流审批。

## 2.2 菜单归属
一级菜单：**工单管理** → 子菜单：**工单列表、工单类型、我提交的工单、待处理工单**

## 2.3 功能需求
- 工单类型管理（硬件故障、软件问题、需求申请、其他）；
- 工单提交：标题、内容、优先级、附件（复用附件管理）；
- 工单分派、认领、转派；
- 处理流程：待处理 → 处理中 → 已解决 → 已关闭；
- 催办、超时提醒；
- 工单日志：状态变更、操作记录全程留痕；
- 工单统计（按类型、状态、处理人）。

## 2.4 数据表设计

### 2.4.1 工单类型表 `work_order_type`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| type_name | varchar(100) | 类型名称 |
| sort | int | 排序 |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 2.4.2 工单主表 `work_order`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| order_no | varchar(64) | 工单编号（编码规则生成） |
| order_type_id | bigint | 工单类型 ID |
| title | varchar(200) | 工单标题 |
| content | text | 工单内容 |
| attachment_ids | varchar(500) | 附件 ID，逗号分隔 |
| priority | tinyint | 优先级：1低 2中 3高 |
| status | tinyint | 0待处理 1处理中 2已解决 3已关闭 |
| creator_id | bigint | 提交人 |
| assignee_id | bigint | 处理人 |
| expect_time | datetime | 期望完成时间 |
| close_time | datetime | 关闭时间 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 2.4.3 工单日志表 `work_order_log`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| order_id | bigint | 工单 ID |
| operator_id | bigint | 操作人 |
| action | varchar(50) | 操作类型：create提交 assign分派 accept认领 transfer转派 solve解决 close关闭 remind催办 |
| comment | varchar(1000) | 处理说明 |
| create_time | datetime | 操作时间 |

---

# 3. 日历日程

## 3.1 模块概述
提供日程管理、日历视图、提醒功能，适配 OA 场景的日程安排、会议、提醒。

## 3.2 菜单归属
一级菜单：**日历日程** → 子菜单：**我的日程、日程提醒**

## 3.3 功能需求
- 日程新增、编辑、删除；
- 日 / 周 / 月日历视图展示；
- 全天日程、时间段日程；
- 日程提醒：提前提醒（接入消息中心/定时任务）；
- 共享日程：指定人员可见；
- 日程到期、逾期标记。

## 3.4 数据表设计

### 3.4.1 日程表 `cal_schedule`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| title | varchar(200) | 日程标题 |
| content | text | 日程内容 |
| start_time | datetime | 开始时间 |
| end_time | datetime | 结束时间 |
| all_day | tinyint | 是否全天 |
| owner_id | bigint | 所属用户 |
| reminder_minutes | int | 提前提醒分钟数 |
| remind_status | tinyint | 0未提醒 1已提醒 |
| shared_json | varchar(500) | 共享人员 ID，逗号分隔 |
| status | tinyint | 0正常 1取消 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 3.4.2 日程提醒记录表 `cal_reminder`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| schedule_id | bigint | 日程 ID |
| remind_user_id | bigint | 提醒用户 |
| remind_time | datetime | 提醒时间 |
| remind_status | tinyint | 0待发送 1已发送 2失败 |
| create_time | datetime | 创建时间 |

---

# 4. 知识库

## 4.1 模块概述
提供文档知识库管理，支持分类、多格式文档存储、检索，复用附件管理存储文件。

## 4.2 菜单归属
一级菜单：**知识库** → 子菜单：**文档分类、文档列表、我的文档**

## 4.3 功能需求
- 文档分类（多级树形）；
- 文档上传（复用附件管理）、标题、正文、标签；
- 文档预览（kkFileView）、下载；
- 全文/标题检索；
- 文档权限：私有、公开、指定角色可见；
- 版本记录（复用版本管理）；
- 收藏、阅读统计。

## 4.4 数据表设计

### 4.4.1 知识库分类表 `kb_category`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| category_name | varchar(100) | 分类名称 |
| parent_id | bigint | 父分类 ID |
| sort | int | 排序 |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 4.4.2 知识库文档表 `kb_document`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| category_id | bigint | 分类 ID |
| doc_title | varchar(200) | 文档标题 |
| doc_content | longtext | 文档正文 |
| file_id | bigint | 附件文件 ID |
| tags | varchar(255) | 标签，逗号分隔 |
| author_id | bigint | 作者 |
| permission_type | varchar(20) | private私有 public公开 role角色 |
| role_json | varchar(500) | 可见角色 ID |
| read_count | int | 阅读次数 |
| version | int | 当前版本 |
| status | tinyint | 0草稿 1发布 2下线 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 4.4.3 知识库收藏表 `kb_favorite`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| doc_id | bigint | 文档 ID |
| user_id | bigint | 收藏用户 |
| create_time | datetime | 收藏时间 |

---

## 附录：高级功能建表 SQL

> 对应的全部建表 SQL 语句请见独立文件 `advanced_features_init.sql`，包含本清单全部 4 个功能模块的数据表（sys_tenant、sys_tenant_user、sys_tenant_package、work_order_type、work_order、work_order_log、cal_schedule、cal_reminder、kb_category、kb_document、kb_favorite）。
