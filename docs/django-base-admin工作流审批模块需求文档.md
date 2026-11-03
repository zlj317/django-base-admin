# django-base-admin 工作流（审批模块）需求文档

| 项目名称 | django-base-admin 工作流（审批）模块 |
| --- | --- |
| 所属系统 | django-base-admin 后台管理基座 |
| 技术栈 | Django 4.2 LTS + DRF + Vue3 + SpiffWorkflow（BPMN2.0）+ bpmn-js |
| 文档版本 | V1.0 |
| 文档状态 | 初稿 |
| 编写日期 | 2026-11-03 |
| 参考原型 | 宇道后台 + 主流BPMN审批引擎（对标Flowable） |

---

## 0. 文档说明

本文档定义 `django-base-admin` 后台基座的**工作流（审批）模块**需求。系统基于 **SpiffWorkflow**（纯 Python BPMN2.0 引擎）实现流程解析与流转，配套前端 **bpmn-js** 可视化流程设计器，提供完整的流程管理、表单管理、审批中心能力，并与系统现有 RBAC 权限体系打通。

> **技术分工说明**：SpiffWorkflow 仅负责加载 BPMN XML、驱动流程实例流转、处理网关/会签/或签；**待办任务、表单渲染、抄送通知、权限控制、审批记录、前端审批页面由本系统自主实现**。

---

## 1. 模块概述

### 1.1 功能定位

内置 BPMN 标准审批引擎，对标 Flowable 使用体验，支持：
- 可视化拖拽设计 BPMN2.0 流程图（bpmn-js）
- 人工审批节点（userTask，暂停等待人工操作）
- 会签、或签、串行审批
- 排他网关、并行网关、条件分支
- 流程监听器、流程表达式、超时策略
- 自定义表单绑定、流程数据持久化
- 待办、已办、抄送、流程轨迹、全局监控

### 1.2 业务价值

免去引入 Java 系 Flowable 的独立引擎成本，在 Django 基座内直接提供符合 BPMN 标准的审批能力，适用于请假、报销、采购、单据、档案归档等审批场景，国产化（飞腾ARM + 银河麒麟）环境友好。

### 1.3 设计原则

1. **标准先行**：遵循 BPMN2.0 标准，流程可被 bpmn-js 可视化设计与解析；
2. **引擎内嵌**：SpiffWorkflow 嵌入 Django 后端，不依赖外部独立流程服务；
3. **能力自主**：待办、表单、抄送、权限、日志由本系统实现，与 RBAC 打通；
4. **流程版本隔离**：流程实例锁定发布版本，修改模型不影响历史实例；
5. **审批可追溯**：全流程审批记录、轨迹、操作日志完整留存。

---

## 2. 菜单与功能需求

> 菜单结构以需求截图为准：【工作流程】一级菜单，下辖【流程管理】【审批中心】【OA示例】三个二级菜单。

### 2.1 一级菜单：工作流程

#### 二级菜单：流程管理（管理员 / 流程配置人员使用）

**1. 流程分类**
- 对流程进行分组归类（如：OA审批、财务审批、采购审批、人事审批）；
- 支持新增、编辑、停用、排序；
- 字段：分类名称、分类编码、排序号、状态（启用/停用）、备注、创建人、创建时间。

**2. 流程模型（核心，bpmn-js 设计入口）**
- 可视化拖拽设计 BPMN2.0 流程图，导出 / 保存 BPMN XML；
- 绑定流程分类、绑定流程表单；
- 支持发布、版本管理、停用、复制模型；
- 支持节点：开始节点、结束节点、用户任务（审批节点）、排他网关、并行网关、子流程、服务任务；
- 节点可配置：审批人策略（指定用户、角色、部门、用户分组、表达式）、会签/或签、超时策略；
- 版本规则：每次发布生成新版本，发起实例锁定当前版本，修改模型不影响运行中的旧实例。

**3. 流程表单**
- 表单设计，为流程绑定自定义业务表单（请假单、报销单、采购单）；
- 支持字段类型：文本、数字、日期、下拉、字典选择、附件；
- 表单数据 JSON 持久化，与流程实例绑定；
- 一个流程模型绑定一个表单，表单在发起、审批时提交与回显。

**4. 用户分组**
- 自定义审批分组，用于 BPMN 节点选人；
- 分组内添加多个系统用户；
- 流程节点配置时直接选择分组，适合固定审批小组（财务组、部门负责人组）。

**5. 流程监听器**
- BPMN 节点事件监听：流程启动、节点进入、节点完成、流程结束、驳回；
- 配置触发动作：回调后端接口、发送消息通知、修改业务数据、写入日志；
- 支持同步回调、异步通知；配置请求地址、请求参数、触发时机。

**6. 流程表达式**
- 自定义表达式，用于网关条件判断、动态审批人计算；
- 支持读取表单变量、用户变量、部门变量；
- 示例：`${form.leaveDays > 3}` 大于 3 天走总监审批。

**7. 流程实例**
- 所有已发起流程实例列表，管理员全局监控；
- 查看流程状态（运行中、已完成、驳回、终止）、流程轨迹、表单数据、审批记录、当前节点；
- 支持强制终止实例。

**8. 流程任务**
- 全局任务监控，所有人工待办任务；
- 查看任务归属、所属实例、当前节点、处理人、任务状态、到期时间；
- 支持管理员转派任务。

#### 二级菜单：审批中心（普通业务用户使用）

**1. 发起流程**
- 展示所有已发布、当前用户有权限发起的流程模型；
- 选择流程，加载绑定表单，填写表单数据，提交启动流程实例。

**2. 我的流程**
- 我发起的所有流程实例；
- 查看流程进度、审批记录、表单、流程图；
- 未被审批时支持撤回。

**3. 待办任务**
- 分配给当前登录用户的审批任务；
- 查看表单、流程图、历史记录；
- 操作：同意、驳回、转审、加签、退回上一步、填写审批意见。

**4. 已办任务**
- 已处理完成的审批任务；
- 查看审批记录、操作日志，仅查看，不可再操作。

**5. 抄送我的**
- 流程设置抄送节点时，抄送用户在此查看流程，只读，无审批权限。

#### 二级菜单：OA示例（演示用）

**1. 请假查询**
- 请假流程业务示例页面，展示请假单数据列表；
- 基于流程表单数据，演示业务表单 + 流程联动效果；
- 可扩展为报销、采购等业务示例。

---

## 3. 核心业务规则

| 规则项 | 说明 |
| --- | --- |
| 流程驱动 | SpiffWorkflow 加载 BPMN XML 驱动流转；`userTask` 人工节点暂停流程，生成待办任务，等待用户操作；用户审批完成后引擎继续流转 |
| 串行审批 | 节点内审批人按顺序逐个审批 |
| 或签 | 节点内任意一人通过，节点完成 |
| 会签 | 节点内全部审批人通过，节点完成 |
| 条件网关 | 通过流程表达式读取表单变量自动分支流转 |
| 超时 | 节点配置超时时间，超时触发监听器（自动提醒、自动驳回、转派） |
| 驳回 | 支持驳回到上一节点 / 驳回至发起人；驳回后流程回退，发起人可重新提交 |
| 权限控制 | 流程模型、发起权限、审批权限复用系统 RBAC，可绑定角色 / 部门 |
| 通知 | 节点到达、待办生成、审批完成、驳回，通过监听器触发站内消息通知 |
| 版本隔离 | 流程实例锁定发布版本，模型改版不影响历史实例 |

---

## 4. 数据表设计（Django Model / MySQL）

> **统一规范**：主键统一 `id bigint` 自增；公共字段：`create_by`（创建人）、`create_time`、`update_by`、`update_time`、`is_deleted`（逻辑删除 0未删/1已删）；除标注外均携带公共字段。

### 4.1 流程分类表 `wf_category`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| name | varchar(100) | 分类名称 |
| code | varchar(64) | 分类编码，唯一 |
| sort | int | 排序 |
| status | tinyint | 0停用，1启用 |
| remark | varchar(255) | 备注 |
| create_by | bigint | 创建用户id |
| create_time | datetime | 创建时间 |
| update_by | bigint | 更新用户id |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint | 逻辑删除 |

### 4.2 流程表单表 `wf_form`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| form_name | varchar(100) | 表单名称 |
| form_key | varchar(64) | 表单唯一标识 |
| form_json | longtext | 表单配置JSON（字段、组件、校验规则） |
| status | tinyint | 启用/停用 |
| remark | varchar(255) | 备注 |
| create_by | bigint | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | bigint | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint | 逻辑删除 |

### 4.3 用户分组表 `wf_group`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| group_name | varchar(100) | 分组名称 |
| group_code | varchar(64) | 分组编码 |
| status | tinyint | 启用/停用 |
| remark | varchar(255) | 备注 |
| create_by | bigint | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | bigint | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint | 逻辑删除 |

### 4.4 用户分组关联表 `wf_group_user`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| group_id | bigint | 分组ID，关联 wf_group |
| user_id | bigint | 用户ID，关联系统用户表 |
| create_time | datetime | 创建时间 |

### 4.5 流程模型表 `wf_model`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| model_name | varchar(100) | 模型名称（请假流程、报销流程） |
| model_key | varchar(64) | 模型唯一Key，引擎识别 |
| category_id | bigint | 所属分类 wf_category.id |
| form_id | bigint | 绑定表单 wf_form.id |
| bpmn_xml | longtext | bpmn-js导出的BPMN2.0 XML，交SpiffWorkflow解析 |
| version | int | 版本号，每次发布+1 |
| status | tinyint | 0草稿，1已发布，2停用 |
| process_status | tinyint | 流程状态：0运行中 1完成 2驳回 3终止 |
| remark | varchar(255) | 备注 |
| create_by | bigint | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | bigint | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint | 逻辑删除 |

### 4.6 流程实例表 `wf_instance`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| instance_key | varchar(64) | 实例唯一标识（引擎 token） |
| model_id | bigint | 关联流程模型 wf_model.id（锁定版本） |
| model_version | int | 模型版本快照 |
| biz_key | varchar(64) | 业务单据号（如请假单号） |
| form_data | longtext | 表单数据JSON |
| start_user_id | bigint | 发起用户id |
| status | tinyint | 流程状态：0运行中 1已完成 2已驳回 3已终止 |
| current_node | varchar(64) | 当前节点ID |
| start_time | datetime | 发起时间 |
| end_time | datetime | 结束时间 |
| create_by | bigint | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | bigint | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint | 逻辑删除 |

### 4.7 流程任务表 `wf_task`（人工待办）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| instance_id | bigint | 关联流程实例 wf_instance.id |
| task_key | varchar(64) | 任务节点ID（BPMN userTask id） |
| task_name | varchar(100) | 任务名称 |
| assignee | bigint | 处理人用户id |
| candidate_group_id | bigint | 候选人分组id（wf_group） |
| status | tinyint | 0待办 1已办 2已转派 3已加签 4已驳回 |
| approve_mode | tinyint | 1串行 2或签 3会签 |
| priority | int | 优先级 |
| due_time | datetime | 到期时间（超时监听用） |
| start_time | datetime | 任务生成时间 |
| end_time | datetime | 任务完成时间 |
| create_by | bigint | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | bigint | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint | 逻辑删除 |

### 4.8 审批记录表 `wf_audit`（历史操作记录）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| instance_id | bigint | 关联流程实例 wf_instance.id |
| task_id | bigint | 关联流程任务 wf_task.id |
| operator_id | bigint | 操作人用户id |
| action | varchar(20) | 操作类型：submit提交 approve同意 reject驳回 transfer转审 addsign加签 back退回 |
| comment | varchar(500) | 审批意见 |
| node_id | varchar(64) | 操作所在节点ID |
| node_name | varchar(100) | 节点名称 |
| create_time | datetime | 操作时间 |

### 4.9 抄送记录表 `wf_cc`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| instance_id | bigint | 关联流程实例 wf_instance.id |
| user_id | bigint | 抄送用户id |
| node_id | varchar(64) | 抄送来源节点 |
| status | tinyint | 0未读 1已读 |
| create_time | datetime | 创建时间 |

### 4.10 流程监听器表 `wf_listener`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| model_id | bigint | 关联流程模型 wf_model.id |
| event_type | varchar(30) | 事件类型：start启动 enter进入 complete完成 end结束 reject驳回 |
| action_type | varchar(30) | 动作：callback回调 notify通知 update_data改数据 log写日志 |
| callback_url | varchar(255) | 回调接口地址 |
| callback_param | text | 回调参数JSON |
| status | tinyint | 启用/停用 |
| create_by | bigint | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | bigint | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint | 逻辑删除 |

### 4.11 流程表达式表 `wf_expression`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| expr_name | varchar(100) | 表达式名称 |
| expr_code | varchar(64) | 表达式编码 |
| expr_content | varchar(500) | 表达式内容，如 `${form.leaveDays > 3}` |
| expr_type | varchar(30) | 类型：condition条件 assignee动态审批人 |
| remark | varchar(255) | 备注 |
| create_by | bigint | 创建人 |
| create_time | datetime | 创建时间 |
| update_by | bigint | 更新人 |
| update_time | datetime | 更新时间 |
| is_deleted | tinyint | 逻辑删除 |

---

## 5. 接口设计规范（DRF）

| 模块 | 接口 | 方法 | 说明 |
| --- | --- | --- | --- |
| 流程分类 | /wf/category/list | GET | 分类分页列表 |
| 流程分类 | /wf/category | POST | 新增分类 |
| 流程分类 | /wf/category/{id} | PUT/DELETE | 修改/删除分类 |
| 流程模型 | /wf/model/list | GET | 模型分页列表 |
| 流程模型 | /wf/model/design/{id} | GET | 获取BPMN XML（加载到bpmn-js） |
| 流程模型 | /wf/model/save | POST | 保存设计后的BPMN XML |
| 流程模型 | /wf/model/publish/{id} | POST | 发布（版本+1） |
| 流程表单 | /wf/form/list | GET | 表单列表 |
| 流程表单 | /wf/form/{id} | GET | 表单配置详情 |
| 用户分组 | /wf/group/list | GET | 分组列表 |
| 用户分组 | /wf/group/{id}/users | GET | 分组内用户 |
| 发起流程 | /wf/instance/start | POST | 提交表单启动流程实例 |
| 我的流程 | /wf/instance/my | GET | 我发起的实例列表 |
| 流程实例 | /wf/instance/list | GET | 全局实例列表（管理员） |
| 流程实例 | /wf/instance/{id}/trace | GET | 流程轨迹 |
| 流程实例 | /wf/instance/{id}/terminate | POST | 强制终止 |
| 待办任务 | /wf/task/todo | GET | 我的待办列表 |
| 已办任务 | /wf/task/done | GET | 我的已办列表 |
| 任务处理 | /wf/task/{id}/approve | POST | 同意 |
| 任务处理 | /wf/task/{id}/reject | POST | 驳回 |
| 任务处理 | /wf/task/{id}/transfer | POST | 转审 |
| 任务处理 | /wf/task/{id}/addsign | POST | 加签 |
| 任务处理 | /wf/task/{id}/back | POST | 退回上一步 |
| 抄送 | /wf/cc/mine | GET | 抄送我的列表 |
| 流程监听器 | /wf/listener | POST/PUT | 监听器配置 |
| 流程表达式 | /wf/expression | POST/PUT | 表达式配置 |

> 统一返回体沿用系统规范 `{code, msg, data}`；接口统一走 RBAC 权限标识校验（如 `wf:model:list`、`wf:task:approve`）。

---

## 6. 非功能需求

| 类别 | 要求 |
| --- | --- |
| 兼容性 | Django 4.2 LTS、SpiffWorkflow、bpmn-js、MySQL 8.0.21、飞腾ARM + 银河麒麟 |
| 性能 | 流程流转为内存计算；待办列表带索引（assignee、status、instance_id） |
| 安全 | 审批接口校验任务归属人，防越权处理他人待办；BPMN XML 解析做安全校验 |
| 可维护 | 流程模型版本隔离，审批记录完整，可审计追踪 |
| 一致性 | 待办任务与流程引擎状态保持一致，事务保证（审批提交 + 引擎流转同事务） |

---

## 7. 风险与备注

1. SpiffWorkflow 不提供可视化设计器、待办、表单，这些由本系统实现，前端开发量较大；
2. 复杂子流程、循环、脚本任务需评估 SpiffWorkflow 版本支持能力；
3. 流程改版只影响新实例，历史实例回查按版本快照展示；
4. 审批提交与流程引擎流转需放在同一数据库事务中，避免待办与流程状态不一致。

---

## 附录：菜单结构总览

```
工作流程
├── 流程管理
│   ├── 流程分类
│   ├── 流程模型
│   ├── 流程表单
│   ├── 用户分组
│   ├── 流程监听器
│   ├── 流程表达式
│   ├── 流程实例
│   └── 流程任务
├── 审批中心
│   ├── 发起流程
│   ├── 我的流程
│   ├── 待办任务
│   ├── 已办任务
│   └── 抄送我的
└── OA示例
    └── 请假查询
```
