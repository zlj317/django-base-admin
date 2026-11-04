-- ==========================================================================
-- django-base-admin 新增功能建表 SQL（需求4 标配 + 需求5 高级 + 需求6 首页）
-- 全部 IF NOT EXISTS，幂等可重复执行
-- ==========================================================================

-- ==========================================================================
-- 需求4：通用标配功能（21 张表）
-- ==========================================================================

-- 1.1 编码规则表
CREATE TABLE IF NOT EXISTS `sys_no_rule` (
  `id` bigint(20) NOT NULL,
  `rule_key` varchar(100) NOT NULL COMMENT '规则唯一标识',
  `rule_name` varchar(100) NOT NULL COMMENT '规则名称',
  `prefix` varchar(50) DEFAULT '' COMMENT '编号前缀，如 BX',
  `date_format` varchar(20) DEFAULT 'YYYYMMDD' COMMENT '日期格式',
  `seq_length` int(11) DEFAULT 4 COMMENT '流水号位数',
  `seq_current` int(11) DEFAULT 0 COMMENT '当前流水号',
  `step` int(11) DEFAULT 1 COMMENT '步长',
  `separator` varchar(10) DEFAULT '' COMMENT '分隔符',
  `reset_type` varchar(20) DEFAULT 'none' COMMENT '重置周期：day/month/year/none',
  `reset_time` date DEFAULT NULL COMMENT '上次重置日期',
  `status` tinyint(1) DEFAULT 1 COMMENT '0停用 1启用',
  `remark` varchar(500) DEFAULT NULL COMMENT '备注',
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rule_key` (`rule_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='编码规则表';

CREATE TABLE IF NOT EXISTS `sys_no_log` (
  `id` bigint(20) NOT NULL,
  `rule_id` bigint(20) NOT NULL COMMENT '规则ID',
  `no_value` varchar(100) NOT NULL COMMENT '生成的编号',
  `biz_type` varchar(50) DEFAULT NULL COMMENT '业务类型',
  `biz_id` bigint(20) DEFAULT NULL COMMENT '业务ID',
  `gen_user_id` bigint(20) DEFAULT NULL COMMENT '生成用户',
  `gen_time` datetime DEFAULT NULL COMMENT '生成时间',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_rule` (`rule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='编号生成记录表';

-- 2.1 导入模板表
CREATE TABLE IF NOT EXISTS `imp_template` (
  `id` bigint(20) NOT NULL,
  `template_name` varchar(100) NOT NULL,
  `template_key` varchar(100) NOT NULL,
  `table_name` varchar(100) DEFAULT NULL COMMENT '目标数据表名',
  `file_type` varchar(20) DEFAULT 'xlsx',
  `template_file_id` bigint(20) DEFAULT NULL,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_key` (`template_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='导入模板表';

CREATE TABLE IF NOT EXISTS `imp_template_column` (
  `id` bigint(20) NOT NULL,
  `template_id` bigint(20) NOT NULL,
  `column_name` varchar(100) NOT NULL COMMENT '数据库字段名',
  `column_header` varchar(100) NOT NULL COMMENT 'Excel表头名称',
  `is_required` tinyint(1) DEFAULT 0,
  `data_type` varchar(30) DEFAULT 'string',
  `max_length` int(11) DEFAULT NULL,
  `regex` varchar(255) DEFAULT NULL,
  `enum_values` varchar(500) DEFAULT NULL,
  `sort` int(11) DEFAULT 0,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_template` (`template_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='导入模板字段表';

-- 3.1 备份记录表
CREATE TABLE IF NOT EXISTS `backup_record` (
  `id` bigint(20) NOT NULL,
  `backup_name` varchar(100) NOT NULL,
  `backup_type` varchar(20) DEFAULT 'manual' COMMENT 'manual手动 auto自动',
  `db_name` varchar(100) DEFAULT NULL,
  `file_id` bigint(20) DEFAULT NULL,
  `file_size` bigint(20) DEFAULT NULL,
  `encrypt_flag` tinyint(1) DEFAULT 0,
  `backup_status` tinyint(1) DEFAULT 0 COMMENT '0备份中 1成功 2失败',
  `backup_time` datetime DEFAULT NULL,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='备份记录表';

CREATE TABLE IF NOT EXISTS `backup_strategy` (
  `id` bigint(20) NOT NULL,
  `strategy_name` varchar(100) NOT NULL,
  `cron_expr` varchar(100) DEFAULT NULL,
  `keep_days` int(11) DEFAULT 7,
  `encrypt_flag` tinyint(1) DEFAULT 0,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='备份策略表';

-- 4.1 数据权限规则表
CREATE TABLE IF NOT EXISTS `sys_data_permission` (
  `id` bigint(20) NOT NULL,
  `permission_name` varchar(100) NOT NULL,
  `permission_type` varchar(30) DEFAULT 'all' COMMENT 'all全部 dept本部门 self本人 role指定角色 custom自定义',
  `scope_value` varchar(500) DEFAULT NULL,
  `sql_condition` varchar(1000) DEFAULT NULL,
  `sort` int(11) DEFAULT 0,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据权限规则表';

CREATE TABLE IF NOT EXISTS `sys_role_data_permission` (
  `id` bigint(20) NOT NULL,
  `role_id` bigint(20) NOT NULL,
  `permission_id` bigint(20) NOT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_perm` (`role_id`, `permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色数据权限关联表';

-- 5.1 脱敏规则表
CREATE TABLE IF NOT EXISTS `desensitize_rule` (
  `id` bigint(20) NOT NULL,
  `rule_name` varchar(100) NOT NULL,
  `rule_type` varchar(30) DEFAULT 'phone' COMMENT 'phone/idcard/bank/email/custom',
  `mask_style` varchar(20) DEFAULT '****',
  `regular` varchar(255) DEFAULT NULL,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脱敏规则表';

CREATE TABLE IF NOT EXISTS `desensitize_field` (
  `id` bigint(20) NOT NULL,
  `rule_id` bigint(20) NOT NULL,
  `biz_type` varchar(50) DEFAULT NULL,
  `field_name` varchar(100) DEFAULT NULL,
  `status` tinyint(1) DEFAULT 1,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_rule` (`rule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脱敏字段配置表';

CREATE TABLE IF NOT EXISTS `desensitize_role` (
  `id` bigint(20) NOT NULL,
  `role_id` bigint(20) NOT NULL,
  `rule_id` bigint(20) NOT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_rule` (`role_id`, `rule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色明文权限表';

-- 6.1 打印模板表
CREATE TABLE IF NOT EXISTS `print_template` (
  `id` bigint(20) NOT NULL,
  `template_name` varchar(100) NOT NULL,
  `template_key` varchar(100) NOT NULL,
  `biz_type` varchar(50) DEFAULT NULL,
  `html_content` longtext COMMENT '模板HTML内容',
  `paper_size` varchar(30) DEFAULT 'A4',
  `is_default` tinyint(1) DEFAULT 0,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_key` (`template_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='打印模板表';

-- 7.1 业务版本快照表
CREATE TABLE IF NOT EXISTS `biz_version` (
  `id` bigint(20) NOT NULL,
  `biz_type` varchar(50) NOT NULL,
  `biz_id` bigint(20) NOT NULL,
  `version_no` int(11) DEFAULT 1,
  `version_data` longtext COMMENT '版本快照JSON',
  `operator_id` bigint(20) DEFAULT NULL,
  `remark` varchar(500) DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_biz` (`biz_type`, `biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='业务版本快照表';

-- 8.1 签章表
CREATE TABLE IF NOT EXISTS `sign_stamp` (
  `id` bigint(20) NOT NULL,
  `stamp_name` varchar(100) NOT NULL,
  `stamp_type` varchar(20) DEFAULT 'image' COMMENT 'image图片 word文字',
  `file_id` bigint(20) DEFAULT NULL,
  `owner_user_id` bigint(20) DEFAULT NULL,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='签章表';

CREATE TABLE IF NOT EXISTS `sign_record` (
  `id` bigint(20) NOT NULL,
  `stamp_id` bigint(20) NOT NULL,
  `biz_type` varchar(50) DEFAULT NULL,
  `biz_id` bigint(20) DEFAULT NULL,
  `file_id` bigint(20) DEFAULT NULL,
  `sign_user_id` bigint(20) DEFAULT NULL,
  `verify_result` varchar(255) DEFAULT NULL,
  `sign_time` datetime DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_stamp` (`stamp_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='签章记录表';

-- 9.1 接口调试日志表
CREATE TABLE IF NOT EXISTS `api_debug_log` (
  `id` bigint(20) NOT NULL,
  `api_path` varchar(255) DEFAULT NULL,
  `method` varchar(10) DEFAULT NULL,
  `request_body` text,
  `response_body` text,
  `http_code` int(11) DEFAULT NULL,
  `debug_user_id` bigint(20) DEFAULT NULL,
  `cost_time` bigint(20) DEFAULT NULL,
  `debug_time` datetime DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='接口调试日志表';

-- 10.1 告警规则表
CREATE TABLE IF NOT EXISTS `monitor_alarm_rule` (
  `id` bigint(20) NOT NULL,
  `rule_name` varchar(100) NOT NULL,
  `monitor_type` varchar(30) DEFAULT 'service' COMMENT 'service/db/redis/disk/task/api',
  `compare_op` varchar(10) DEFAULT '>',
  `threshold` varchar(50) DEFAULT NULL,
  `alarm_level` tinyint(1) DEFAULT 1 COMMENT '1提示 2警告 3严重',
  `channel` varchar(30) DEFAULT 'site',
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警规则表';

CREATE TABLE IF NOT EXISTS `monitor_alarm_record` (
  `id` bigint(20) NOT NULL,
  `rule_id` bigint(20) DEFAULT NULL,
  `alarm_level` tinyint(1) DEFAULT 1,
  `alarm_content` varchar(1000) DEFAULT NULL,
  `alarm_time` datetime DEFAULT NULL,
  `handle_status` tinyint(1) DEFAULT 0 COMMENT '0未处理 1已处理',
  `handler_id` bigint(20) DEFAULT NULL,
  `handle_time` datetime DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_rule` (`rule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='告警记录表';

-- 11.1 IP黑白名单表
CREATE TABLE IF NOT EXISTS `sys_ip_control` (
  `id` bigint(20) NOT NULL,
  `ip` varchar(50) NOT NULL,
  `control_type` varchar(10) DEFAULT 'black' COMMENT 'black黑名单 white白名单',
  `reason` varchar(255) DEFAULT NULL,
  `status` tinyint(1) DEFAULT 1,
  `expire_time` datetime DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='IP黑白名单表';

CREATE TABLE IF NOT EXISTS `sys_login_attempt` (
  `id` bigint(20) NOT NULL,
  `username` varchar(64) DEFAULT NULL,
  `ip` varchar(50) DEFAULT NULL,
  `attempt_time` datetime DEFAULT NULL,
  `success_flag` tinyint(1) DEFAULT 0,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='登录尝试记录表';

CREATE TABLE IF NOT EXISTS `sys_rate_limit` (
  `id` bigint(20) NOT NULL,
  `rule_name` varchar(100) NOT NULL,
  `limit_url` varchar(255) DEFAULT NULL,
  `period_sec` int(11) DEFAULT 60,
  `max_count` int(11) DEFAULT 100,
  `status` tinyint(1) DEFAULT 1,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='接口限流规则表';

-- ==========================================================================
-- 需求5：高级可选功能（11 张表）
-- ==========================================================================

-- 1.1 租户表
CREATE TABLE IF NOT EXISTS `sys_tenant` (
  `id` bigint(20) NOT NULL,
  `tenant_name` varchar(100) NOT NULL,
  `tenant_code` varchar(100) NOT NULL,
  `status` tinyint(1) DEFAULT 1,
  `expire_time` datetime DEFAULT NULL,
  `max_user_count` int(11) DEFAULT 100,
  `max_storage_mb` bigint(20) DEFAULT 2048,
  `config_json` text,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_code` (`tenant_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='租户表';

CREATE TABLE IF NOT EXISTS `sys_tenant_user` (
  `id` bigint(20) NOT NULL,
  `tenant_id` bigint(20) NOT NULL,
  `user_id` bigint(20) NOT NULL,
  `is_tenant_admin` tinyint(1) DEFAULT 0,
  `join_time` datetime DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tenant_user` (`tenant_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='租户用户关联表';

CREATE TABLE IF NOT EXISTS `sys_tenant_package` (
  `id` bigint(20) NOT NULL,
  `package_name` varchar(100) NOT NULL,
  `max_user_count` int(11) DEFAULT 100,
  `max_storage_mb` bigint(20) DEFAULT 2048,
  `price` decimal(10,2) DEFAULT 0.00,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='租户套餐表';

-- 2.1 工单类型表
CREATE TABLE IF NOT EXISTS `work_order_type` (
  `id` bigint(20) NOT NULL,
  `type_name` varchar(100) NOT NULL,
  `sort` int(11) DEFAULT 0,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单类型表';

CREATE TABLE IF NOT EXISTS `work_order` (
  `id` bigint(20) NOT NULL,
  `order_no` varchar(64) DEFAULT NULL,
  `order_type_id` bigint(20) DEFAULT NULL,
  `title` varchar(200) NOT NULL,
  `content` text,
  `attachment_ids` varchar(500) DEFAULT NULL,
  `priority` tinyint(1) DEFAULT 2 COMMENT '1低 2中 3高',
  `status` tinyint(1) DEFAULT 0 COMMENT '0待处理 1处理中 2已解决 3已关闭',
  `creator_id` bigint(20) DEFAULT NULL,
  `assignee_id` bigint(20) DEFAULT NULL,
  `expect_time` datetime DEFAULT NULL,
  `close_time` datetime DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_creator` (`creator_id`),
  KEY `idx_assignee` (`assignee_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单主表';

CREATE TABLE IF NOT EXISTS `work_order_log` (
  `id` bigint(20) NOT NULL,
  `order_id` bigint(20) NOT NULL,
  `operator_id` bigint(20) DEFAULT NULL,
  `action` varchar(50) DEFAULT NULL COMMENT 'create/assign/accept/transfer/solve/close/remind',
  `comment` varchar(1000) DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_order` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工单日志表';

-- 3.1 日程表
CREATE TABLE IF NOT EXISTS `cal_schedule` (
  `id` bigint(20) NOT NULL,
  `title` varchar(200) NOT NULL,
  `content` text,
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `all_day` tinyint(1) DEFAULT 0,
  `owner_id` bigint(20) DEFAULT NULL,
  `reminder_minutes` int(11) DEFAULT 0,
  `remind_status` tinyint(1) DEFAULT 0 COMMENT '0未提醒 1已提醒',
  `shared_json` varchar(500) DEFAULT NULL,
  `status` tinyint(1) DEFAULT 0 COMMENT '0正常 1取消',
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_owner` (`owner_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日程表';

CREATE TABLE IF NOT EXISTS `cal_reminder` (
  `id` bigint(20) NOT NULL,
  `schedule_id` bigint(20) NOT NULL,
  `remind_user_id` bigint(20) DEFAULT NULL,
  `remind_time` datetime DEFAULT NULL,
  `remind_status` tinyint(1) DEFAULT 0 COMMENT '0待发送 1已发送 2失败',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_schedule` (`schedule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日程提醒记录表';

-- 4.1 知识库分类表
CREATE TABLE IF NOT EXISTS `kb_category` (
  `id` bigint(20) NOT NULL,
  `category_name` varchar(100) NOT NULL,
  `parent_id` bigint(20) DEFAULT 0,
  `sort` int(11) DEFAULT 0,
  `status` tinyint(1) DEFAULT 1,
  `remark` varchar(500) DEFAULT NULL,
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_parent` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库分类表';

CREATE TABLE IF NOT EXISTS `kb_document` (
  `id` bigint(20) NOT NULL,
  `category_id` bigint(20) DEFAULT NULL,
  `doc_title` varchar(200) NOT NULL,
  `doc_content` longtext,
  `file_id` bigint(20) DEFAULT NULL,
  `tags` varchar(255) DEFAULT NULL,
  `author_id` bigint(20) DEFAULT NULL,
  `permission_type` varchar(20) DEFAULT 'public' COMMENT 'private私有 public公开 role角色',
  `role_json` varchar(500) DEFAULT NULL,
  `read_count` int(11) DEFAULT 0,
  `version` int(11) DEFAULT 1,
  `status` tinyint(1) DEFAULT 1 COMMENT '0草稿 1发布 2下线',
  `create_by` varchar(64) DEFAULT '',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_by` varchar(64) DEFAULT '',
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_category` (`category_id`),
  KEY `idx_author` (`author_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库文档表';

CREATE TABLE IF NOT EXISTS `kb_favorite` (
  `id` bigint(20) NOT NULL,
  `doc_id` bigint(20) NOT NULL,
  `user_id` bigint(20) NOT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_doc_user` (`doc_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库收藏表';

-- ==========================================================================
-- 需求6：系统首页（1 张可选表）
-- ==========================================================================

CREATE TABLE IF NOT EXISTS `home_user_config` (
  `id` bigint(20) NOT NULL,
  `user_id` bigint(20) NOT NULL,
  `favorite_menus` varchar(1000) DEFAULT NULL,
  `home_layout` varchar(500) DEFAULT NULL,
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='首页个性化配置表';
