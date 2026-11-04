# django-base-admin 通用标配功能需求文档

| 项目名称 | django-base-admin 通用标配扩展功能 |
| --- | --- |
| 文档版本 | V1.0 |
| 文档状态 | 初稿 |
| 编写日期 | 2026-11-04 |
| 适配主系统 | django-base-admin（Django + Vue3 + MySQL） |
| 配套主文档 | 《后台管理系统需求规格说明书 V1.0》/《附加模块需求说明书 V1.0》 |

---

## 0. 文档说明

本文档整理 **11 条企业后台管理系统高频标配功能**，各模块复用主系统 RBAC 权限体系、统一返回格式、统一菜单层级缩进 UI 规范，并联动附件管理、消息中心、定时任务、报表等既有模块。每条功能均给出：模块概述、菜单归属、功能需求、数据表结构设计。

**包含的 11 条标配功能清单**

| 序号 | 功能模块 | 说明 |
| --- | --- | --- |
| 1 | 编码规则（单号生成器） | 业务单据自动流水号 |
| 2 | 数据导入模板管理 | 导入模板在线维护 |
| 3 | 数据备份与恢复 | MySQL 备份、恢复、策略 |
| 4 | 数据权限管理（行级权限） | 控制数据可见范围 |
| 5 | 脱敏配置管理 | 敏感字段脱敏 |
| 6 | 单据打印模板管理 | 业务单据套打 |
| 7 | 版本管理 | 业务单据历史版本 |
| 8 | 电子签章 | 审批后 PDF 加盖签章 |
| 9 | 接口文档与接口调试 | Swagger 文档 + 在线调试 |
| 10 | 服务健康监控与告警中心 | 服务、库、Redis、任务监控 |
| 11 | 黑名单 / IP 访问限制 | 安全防护 |

---

# 1. 编码规则（单号生成器）

## 1.1 模块概述
为业务单据自动生成唯一流水号，供审批流程、档案、报表、附件等业务调用，支持灵活自定义编号规则。

## 1.2 菜单归属
一级菜单：**系统管理** → 子菜单：**编码规则管理**

## 1.3 功能需求
- 自定义编号规则：前缀、日期格式、流水号位数、分隔符、步长；
- 按周期重置：按日 / 按月 / 按年重置流水号；
- 防重复：锁号机制保证并发下唯一；
- 规则启停、删除、复制；
- 提供通用接口：`POST /sys/no/generate?ruleKey=xxx` 供其他模块调用；
- 规则使用日志、当前序号查看、手动重置序号（需权限）。

## 1.4 数据表设计

### 1.4.1 编码规则表 `sys_no_rule`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| rule_key | varchar(100) | 规则唯一标识 |
| rule_name | varchar(100) | 规则名称 |
| prefix | varchar(50) | 编号前缀，如 BX |
| date_format | varchar(20) | 日期格式，如 YYYYMMDD |
| seq_length | int | 流水号位数 |
| seq_current | int | 当前流水号 |
| step | int | 步长，默认 1 |
| separator | varchar(10) | 分隔符 |
| reset_type | varchar(20) | 重置周期：day/month/year/none |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 1.4.2 编号生成记录表 `sys_no_log`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| rule_id | bigint | 规则 ID |
| no_value | varchar(100) | 生成的编号 |
| biz_type | varchar(50) | 业务类型 |
| biz_id | bigint | 业务 ID |
| gen_user_id | bigint | 生成用户 |
| gen_time | datetime | 生成时间 |
| create_time | datetime | 创建时间 |

---

# 2. 数据导入模板管理

## 2.1 模块概述
为各业务模块提供统一、可维护的 Excel 导入模板，配置表头、字段校验规则，规范数据导入。

## 2.2 菜单归属
一级菜单：**系统管理** → 子菜单：**导入模板管理**

## 2.3 功能需求
- 上传 Excel 导入模板文件、绑定目标数据表；
- 配置模板字段：表头名称、字段名、是否必填、数据类型、长度、正则校验；
- 模板下载（标准表头）、模板预览；
- 导入校验规则管理：非空、长度、格式、枚举值；
- 导入失败时生成错误说明文件（标注行号 + 错误原因）供下载；
- 联动代码生成导入接口、业务单据导入复用模板。

## 2.4 数据表设计

### 2.4.1 导入模板表 `imp_template`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| template_name | varchar(100) | 模板名称 |
| template_key | varchar(100) | 模板唯一标识 |
| table_name | varchar(100) | 目标数据表名 |
| file_type | varchar(20) | 文件类型：xls/xlsx |
| template_file_id | bigint | 模板附件 ID（附件管理） |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 2.4.2 导入模板字段表 `imp_template_column`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| template_id | bigint | 模板 ID |
| column_name | varchar(100) | 数据库字段名 |
| column_header | varchar(100) | Excel 表头名称 |
| is_required | tinyint | 是否必填 |
| data_type | varchar(30) | 数据类型：string/number/date |
| max_length | int | 最大长度 |
| regex | varchar(255) | 正则校验 |
| enum_values | varchar(500) | 枚举值，逗号分隔 |
| sort | int | 排序 |
| is_deleted | tinyint(1) | 逻辑删除 |

---

# 3. 数据备份与恢复

## 3.1 模块概述
提供 MySQL 数据库备份、定时自动备份、恢复与清理能力，保障数据安全。

## 3.2 菜单归属
一级菜单：**系统管理** → 子菜单：**数据备份**

## 3.3 功能需求
- 手动一键备份：导出当前库 SQL，备份文件存入附件管理；
- 定时自动备份：接入 Celery 定时任务，按 cron 策略备份；
- 备份记录：文件、大小、时间、方式、状态；
- 备份文件加密（可选）；
- 在线恢复：仅超级管理员可操作，二次强确认，恢复前自动再备份一次，操作日志留痕；
- 备份策略：保留天数、过期自动清理。

## 3.4 数据表设计

### 3.4.1 备份记录表 `backup_record`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| backup_name | varchar(100) | 备份名称 |
| backup_type | varchar(20) | manual手动 auto自动 |
| db_name | varchar(100) | 数据库名 |
| file_id | bigint | 备份文件附件 ID |
| file_size | bigint | 备份文件大小 |
| encrypt_flag | tinyint | 是否加密 |
| backup_status | tinyint | 0备份中 1成功 2失败 |
| backup_time | datetime | 备份时间 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 3.4.2 备份策略表 `backup_strategy`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| strategy_name | varchar(100) | 策略名称 |
| cron_expr | varchar(100) | cron 表达式 |
| keep_days | int | 保留天数 |
| encrypt_flag | tinyint | 是否加密 |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

---

# 4. 数据权限管理（行级权限）

## 4.1 模块概述
在 RBAC 功能权限基础上，增加**行级数据权限**，控制不同角色可见的数据范围。

## 4.2 菜单归属
一级菜单：**系统管理** → 子菜单：**数据权限配置**

## 4.3 功能需求
- 权限规则类型：全部数据 / 本部门数据 / 本人数据 / 指定角色 / 自定义 SQL 条件；
- 规则绑定角色，一个角色可关联多条数据权限；
- 业务查询自动拼接数据权限过滤条件；
- 数据权限启用/停用、规则优先级配置；
- 联动：所有业务列表、报表查询、审批中心列表按数据权限过滤。

## 4.4 数据表设计

### 4.4.1 数据权限规则表 `sys_data_permission`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| permission_name | varchar(100) | 规则名称 |
| permission_type | varchar(30) | all全部 dept本部门 self本人 role指定角色 custom自定义 |
| scope_value | varchar(500) | 范围值（部门/角色 id 或自定义条件） |
| sql_condition | varchar(1000) | 自定义 SQL 过滤条件 |
| sort | int | 优先级排序 |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 4.4.2 角色数据权限关联表 `sys_role_data_permission`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| role_id | bigint | 角色 ID |
| permission_id | bigint | 数据权限规则 ID |
| create_time | datetime | 创建时间 |

---

# 5. 脱敏配置管理

## 5.1 模块概述
对敏感字段（手机号、身份证、银行卡、邮箱等）按规则脱敏，按角色区分是否查看明文。

## 5.2 菜单归属
一级菜单：**系统管理** → 子菜单：**脱敏规则配置**

## 5.3 功能需求
- 脱敏规则类型：手机号、身份证、银行卡、邮箱、自定义正则；
- 掩码样式：如 `138****8000`；
- 全局开关；
- 按角色配置是否可见明文（管理员明文，普通用户脱敏）；
- 联动代码生成列表、详情、导出 Excel 自动脱敏。

## 5.4 数据表设计

### 5.4.1 脱敏规则表 `desensitize_rule`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| rule_name | varchar(100) | 规则名称 |
| rule_type | varchar(30) | phone/idcard/bank/email/custom |
| mask_style | varchar(20) | 掩码样式 |
| regular | varchar(255) | 自定义正则 |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 5.4.2 脱敏字段配置表 `desensitize_field`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| rule_id | bigint | 规则 ID |
| biz_type | varchar(50) | 业务类型（表名） |
| field_name | varchar(100) | 字段名 |
| status | tinyint | 0停用 1启用 |
| create_time | datetime | 创建时间 |

### 5.4.3 角色明文权限表 `desensitize_role`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| role_id | bigint | 角色 ID |
| rule_id | bigint | 规则 ID（该角色可见明文） |
| create_time | datetime | 创建时间 |

---

# 6. 单据打印模板管理

## 6.1 模块概述
为审批单、业务单据、凭证提供在线设计打印模板，支持套打、批量打印。

## 6.2 菜单归属
一级菜单：**系统管理** → 子菜单：**打印模板管理**

## 6.3 功能需求
- 在线设计打印模板（HTML 模板 + 变量渲染）；
- 绑定业务单据类型；
- 纸张规格配置：A4、自定义、套打；
- 批量打印、打印预览（走附件预览）；
- 模板默认值、版本管理、权限控制。

## 6.4 数据表设计

### 6.4.1 打印模板表 `print_template`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| template_name | varchar(100) | 模板名称 |
| template_key | varchar(100) | 模板唯一标识 |
| biz_type | varchar(50) | 绑定业务类型 |
| html_content | longtext | 模板 HTML 内容 |
| paper_size | varchar(30) | 纸张规格 |
| is_default | tinyint | 是否默认模板 |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

---

# 7. 版本管理（业务单据版本）

## 7.1 模块概述
业务单据每次修改自动保存历史快照，支持版本对比、回滚。

## 7.2 菜单归属
一级菜单：**系统管理** → 子菜单：**版本记录管理**

## 7.3 功能需求
- 单据修改自动生成版本快照；
- 版本列表、版本对比（字段差异高亮）；
- 回滚到历史版本；
- 版本快照数据独立存储，不覆盖当前数据；
- 联动工作流表单、代码生成业务表单。

## 7.4 数据表设计

### 7.4.1 业务版本快照表 `biz_version`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| biz_type | varchar(50) | 业务类型（表名） |
| biz_id | bigint | 业务记录 ID |
| version_no | int | 版本号 |
| version_data | longtext | 版本快照 JSON |
| operator_id | bigint | 操作人 |
| remark | varchar(500) | 备注 |
| create_time | datetime | 创建时间 |

---

# 8. 电子签章

## 8.1 模块概述
在审批完成后的 PDF 文件上加盖电子签章，防篡改、留痕，适配财务、电子档案场景。

## 8.2 菜单归属
一级菜单：**系统管理** → 子菜单：**电子签章**

## 8.3 功能需求
- 上传图片签章、绑定用户/角色；
- 审批通过后自动在 PDF 指定位置加盖签章；
- 签章防篡改校验（哈希校验）；
- 签章日志：时间、用户、文件、结果；
- 签章后 PDF 走 kkFileView 预览。

## 8.4 数据表设计

### 8.4.1 签章表 `sign_stamp`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| stamp_name | varchar(100) | 签章名称 |
| stamp_type | varchar(20) | image图片 word文字 |
| file_id | bigint | 签章图片附件 ID |
| owner_user_id | bigint | 归属用户 |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 8.4.2 签章记录表 `sign_record`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| stamp_id | bigint | 签章 ID |
| biz_type | varchar(50) | 业务类型 |
| biz_id | bigint | 业务 ID |
| file_id | bigint | 加盖签章后的文件附件 ID |
| sign_user_id | bigint | 签章用户 |
| verify_result | varchar(255) | 校验结果 |
| sign_time | datetime | 签章时间 |
| create_time | datetime | 创建时间 |

---

# 9. 接口文档与接口调试

## 9.1 模块概述
基于 drf-spectacular 自动生成 Swagger 接口文档，支持在线查看、调试接口。

## 9.2 菜单归属
一级菜单：**系统管理** → 子菜单：**接口管理**

## 9.3 功能需求
- 自动生成 RESTful 接口文档（Swagger UI / ReDoc）；
- 接口分类、标签管理、权限标注；
- 在线调试接口（需登录、权限校验）；
- 接口调试记录日志；
- 对接【数据同步/外部对接】模块便于外部系统联调。

## 9.4 数据表设计

### 9.4.1 接口调试日志表 `api_debug_log`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| api_path | varchar(255) | 接口路径 |
| method | varchar(10) | 请求方式 |
| request_body | text | 请求参数 |
| response_body | text | 返回结果 |
| http_code | int | 状态码 |
| debug_user_id | bigint | 调试用户 |
| cost_time | bigint | 耗时 |
| debug_time | datetime | 调试时间 |
| create_time | datetime | 创建时间 |

> 说明：接口文档本身由 drf-spectacular 自动生成，无需独立业务表；仅调试记录落库。

---

# 10. 服务健康监控与告警中心

## 10.1 模块概述
监控服务存活、数据库连接、Redis 连接、磁盘使用率、定时任务失败、接口超时，异常推送告警。

## 10.2 菜单归属
一级菜单：**系统管理** → 子菜单：**监控告警**

## 10.3 功能需求
- 监控项：服务存活、数据库、Redis、磁盘、定时任务、接口耗时；
- 阈值告警规则配置、告警级别（提示/警告/严重）；
- 告警记录、处理状态跟踪；
- 告警推送至消息中心（站内）、预留邮件；
- 监控仪表盘展示当前各项状态。

## 10.4 数据表设计

### 10.4.1 告警规则表 `monitor_alarm_rule`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| rule_name | varchar(100) | 规则名称 |
| monitor_type | varchar(30) | service/db/redis/disk/task/api |
| compare_op | varchar(10) | > >= < <= = |
| threshold | varchar(50) | 阈值 |
| alarm_level | tinyint | 1提示 2警告 3严重 |
| channel | varchar(30) | 告警渠道：site/email |
| status | tinyint | 0停用 1启用 |
| remark | varchar(500) | 备注 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 10.4.2 告警记录表 `monitor_alarm_record`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| rule_id | bigint | 告警规则 ID |
| alarm_level | tinyint | 告警级别 |
| alarm_content | varchar(1000) | 告警内容 |
| alarm_time | datetime | 告警时间 |
| handle_status | tinyint | 0未处理 1已处理 |
| handler_id | bigint | 处理人 |
| handle_time | datetime | 处理时间 |
| create_time | datetime | 创建时间 |

---

# 11. 黑名单 / IP 访问限制

## 11.1 模块概述
安全防护：IP 黑白名单、接口限流、登录失败锁定，防暴力破解。

## 11.2 菜单归属
一级菜单：**系统管理** → 子菜单：**安全策略**

## 11.3 功能需求
- IP 黑白名单管理；
- 接口访问限流规则配置；
- 登录失败次数、账号锁定、解锁策略；
- 访问日志、拦截记录查询。

## 11.4 数据表设计

### 11.4.1 IP 黑白名单表 `sys_ip_control`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| ip | varchar(50) | IP 地址/网段 |
| control_type | varchar(10) | black黑名单 white白名单 |
| reason | varchar(255) | 原因 |
| status | tinyint | 0停用 1启用 |
| expire_time | datetime | 过期时间 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

### 11.4.2 登录尝试记录表 `sys_login_attempt`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| username | varchar(64) | 登录账号 |
| ip | varchar(50) | 来源 IP |
| attempt_time | datetime | 尝试时间 |
| success_flag | tinyint | 0失败 1成功 |
| create_time | datetime | 创建时间 |

### 11.4.3 接口限流规则表 `sys_rate_limit`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| rule_name | varchar(100) | 规则名称 |
| limit_url | varchar(255) | 限制接口路径（支持通配） |
| period_sec | int | 统计周期（秒） |
| max_count | int | 周期内最大次数 |
| status | tinyint | 0停用 1启用 |
| create_by | varchar(64) | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | varchar(64) | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint(1) | 逻辑删除 |

---

## 附录：标配功能建表 SQL

> 对应的全部建表 SQL 语句请见独立文件 `common_features_init.sql`，包含本清单全部 11 个功能模块的数据表（sys_no_rule、sys_no_log、imp_template、imp_template_column、backup_record、backup_strategy、sys_data_permission、sys_role_data_permission、desensitize_rule、desensitize_field、desensitize_role、print_template、biz_version、sign_stamp、sign_record、api_debug_log、monitor_alarm_rule、monitor_alarm_record、sys_ip_control、sys_login_attempt、sys_rate_limit）。
