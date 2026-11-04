-- =====================================================================
-- 后台管理系统 工作流（审批）模块建表 SQL（V1.0）
-- 数据库：MySQL 8.0.21（utf8mb4）
-- 说明：本脚本创建全部 wf_ 开头的工作流表
-- 公共字段：create_by/create_time/update_by/update_time/is_deleted
-- =====================================================================

USE `gen_admin`;

-- =====================================================================
-- 1. 流程分类表 wf_category
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_category` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `name`        VARCHAR(100) NOT NULL COMMENT '分类名称',
  `code`        VARCHAR(64)  NOT NULL COMMENT '分类编码（唯一）',
  `sort`        INT          NOT NULL DEFAULT 0 COMMENT '排序号，越小越靠前',
  `status`      TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `remark`      VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `create_by`   VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wf_category_code` (`code`),
  KEY `idx_wf_category_sort` (`sort`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程分类表';

-- =====================================================================
-- 2. 流程表单表 wf_form
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_form` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `form_name`   VARCHAR(100) NOT NULL COMMENT '表单名称',
  `form_key`    VARCHAR(64)  NOT NULL COMMENT '表单唯一标识',
  `form_json`   LONGTEXT     COMMENT '表单配置JSON（字段、组件、校验规则）',
  `status`      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0启用 1停用',
  `remark`      VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `create_by`   VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wf_form_key` (`form_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程表单表';

-- =====================================================================
-- 3. 用户分组表 wf_group
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_group` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `group_name`  VARCHAR(100) NOT NULL COMMENT '分组名称',
  `group_code`  VARCHAR(64)  NOT NULL COMMENT '分组编码（唯一）',
  `status`      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0启用 1停用',
  `remark`      VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `create_by`   VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wf_group_code` (`group_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户分组表';

-- =====================================================================
-- 4. 用户分组关联表 wf_group_user
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_group_user` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `group_id`    BIGINT NOT NULL COMMENT '分组ID（wf_group.id）',
  `user_id`     BIGINT NOT NULL COMMENT '用户ID（sys_user.id）',
  `create_time` DATETIME DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wf_group_user` (`group_id`, `user_id`),
  KEY `idx_wf_group_user_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户分组关联表';

-- =====================================================================
-- 5. 流程模型表 wf_model
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_model` (
  `id`             BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `model_name`     VARCHAR(100) NOT NULL COMMENT '模型名称（请假流程、报销流程）',
  `model_key`      VARCHAR(64)  NOT NULL COMMENT '模型唯一Key（引擎识别）',
  `category_id`    BIGINT       DEFAULT NULL COMMENT '所属分类 wf_category.id',
  `form_id`        BIGINT       DEFAULT NULL COMMENT '绑定表单 wf_form.id',
  `bpmn_xml`       LONGTEXT     COMMENT 'bpmn-js导出的BPMN2.0 XML',
  `node_config`    LONGTEXT     COMMENT '节点审批人配置JSON（设计器维护）',
  `version`        INT          NOT NULL DEFAULT 0 COMMENT '版本号，每次发布+1',
  `status`         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0草稿 1已发布 2停用',
  `process_status` TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '流程状态：0运行中 1完成 2驳回 3终止',
  `remark`         VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `create_by`      VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`    DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`      VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`    DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`     TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wf_model_key` (`model_key`),
  KEY `idx_wf_model_category` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程模型表';

-- =====================================================================
-- 6. 流程实例表 wf_instance
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_instance` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `instance_key`  VARCHAR(64)  NOT NULL COMMENT '实例唯一标识（引擎token）',
  `model_id`      BIGINT       NOT NULL COMMENT '关联流程模型 wf_model.id（锁定版本）',
  `model_version` INT          NOT NULL DEFAULT 1 COMMENT '模型版本快照',
  `biz_key`       VARCHAR(64)  DEFAULT NULL COMMENT '业务单据号（如请假单号）',
  `form_data`     LONGTEXT     COMMENT '表单数据JSON',
  `start_user_id` BIGINT       NOT NULL COMMENT '发起用户ID',
  `status`        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0运行中 1已完成 2已驳回 3已终止',
  `current_node`  VARCHAR(200) DEFAULT NULL COMMENT '当前节点ID（并行时逗号分隔）',
  `start_time`    DATETIME     DEFAULT NULL COMMENT '发起时间',
  `end_time`      DATETIME     DEFAULT NULL COMMENT '结束时间',
  `engine_state`  LONGTEXT     COMMENT '引擎运行状态JSON（网关到达记录、串行队列）',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wf_instance_key` (`instance_key`),
  KEY `idx_wf_instance_model` (`model_id`),
  KEY `idx_wf_instance_start_user` (`start_user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程实例表';

-- =====================================================================
-- 7. 流程任务表 wf_task（人工待办）
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_task` (
  `id`                 BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `instance_id`        BIGINT       NOT NULL COMMENT '关联流程实例 wf_instance.id',
  `task_key`           VARCHAR(64)  NOT NULL COMMENT '任务节点ID（BPMN userTask id）',
  `task_name`          VARCHAR(100) DEFAULT NULL COMMENT '任务名称',
  `assignee`           BIGINT       DEFAULT NULL COMMENT '处理人用户ID',
  `candidate_group_id` BIGINT       DEFAULT NULL COMMENT '候选人分组ID（wf_group）',
  `status`             TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0待办 1已办 2已转派 3已加签 4已驳回',
  `approve_mode`       TINYINT(1)   NOT NULL DEFAULT 2 COMMENT '审批方式：1串行 2或签 3会签',
  `priority`           INT          NOT NULL DEFAULT 0 COMMENT '优先级',
  `due_time`           DATETIME     DEFAULT NULL COMMENT '到期时间（超时监听用）',
  `start_time`         DATETIME     DEFAULT NULL COMMENT '任务生成时间',
  `end_time`           DATETIME     DEFAULT NULL COMMENT '任务完成时间',
  `create_by`          VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`        DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`          VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`        DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_wf_task_assignee_status` (`assignee`, `status`),
  KEY `idx_wf_task_instance` (`instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程任务表';

-- =====================================================================
-- 8. 审批记录表 wf_audit（历史操作记录）
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_audit` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `instance_id` BIGINT       NOT NULL COMMENT '关联流程实例 wf_instance.id',
  `task_id`     BIGINT       DEFAULT NULL COMMENT '关联流程任务 wf_task.id',
  `operator_id` BIGINT       DEFAULT NULL COMMENT '操作人用户ID',
  `action`      VARCHAR(20)  DEFAULT NULL COMMENT '操作类型：submit提交 approve同意 reject驳回 transfer转审 addsign加签 back退回',
  `comment`     VARCHAR(500) DEFAULT NULL COMMENT '审批意见',
  `node_id`     VARCHAR(64)  DEFAULT NULL COMMENT '操作所在节点ID',
  `node_name`   VARCHAR(100) DEFAULT NULL COMMENT '节点名称',
  `create_time` DATETIME     DEFAULT NULL COMMENT '操作时间',
  PRIMARY KEY (`id`),
  KEY `idx_wf_audit_instance` (`instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='审批记录表';

-- =====================================================================
-- 9. 抄送记录表 wf_cc
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_cc` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `instance_id` BIGINT      NOT NULL COMMENT '关联流程实例 wf_instance.id',
  `user_id`     BIGINT      NOT NULL COMMENT '抄送用户ID',
  `node_id`     VARCHAR(64) DEFAULT NULL COMMENT '抄送来源节点',
  `status`      TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '状态：0未读 1已读',
  `create_time` DATETIME    DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_wf_cc_user` (`user_id`, `status`),
  KEY `idx_wf_cc_instance` (`instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='抄送记录表';

-- =====================================================================
-- 10. 流程监听器表 wf_listener
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_listener` (
  `id`             BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `model_id`       BIGINT       NOT NULL COMMENT '关联流程模型 wf_model.id',
  `event_type`     VARCHAR(30)  NOT NULL COMMENT '事件类型：start启动 enter进入 complete完成 end结束 reject驳回',
  `action_type`    VARCHAR(30)  NOT NULL COMMENT '动作：callback回调 notify通知 update_data改数据 log写日志',
  `callback_url`   VARCHAR(255) DEFAULT NULL COMMENT '回调接口地址',
  `callback_param` TEXT         COMMENT '回调参数JSON',
  `status`         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0启用 1停用',
  `create_by`      VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`    DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`      VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`    DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`     TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_wf_listener_model` (`model_id`, `event_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程监听器表';

-- =====================================================================
-- 11. 流程表达式表 wf_expression
-- =====================================================================
CREATE TABLE IF NOT EXISTS `wf_expression` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `expr_name`    VARCHAR(100) NOT NULL COMMENT '表达式名称',
  `expr_code`    VARCHAR(64)  NOT NULL COMMENT '表达式编码（唯一）',
  `expr_content` VARCHAR(500) DEFAULT NULL COMMENT '表达式内容，如 ${form.leaveDays > 3}',
  `expr_type`    VARCHAR(30)  NOT NULL DEFAULT 'condition' COMMENT '类型：condition条件 assignee动态审批人',
  `remark`       VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `create_by`    VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`    VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`  DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_wf_expr_code` (`expr_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程表达式表';
