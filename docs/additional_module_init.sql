-- =====================================================================
-- django-base-admin 附加模块 初始化建表 SQL（V1.0）
-- 数据库：MySQL 8.0.21（utf8mb4）
-- 说明：创建本次新增的全部扩展模块数据表
--  附件管理 / 消息中心 / 公告通知 / 定时任务 / 报表管理 / 报表大屏 / 数据同步外部对接
-- 执行前请确认已连接业务数据库（示例：gen_admin）
-- =====================================================================

USE `gen_admin`;

-- =====================================================================
-- 一、附件管理模块
-- =====================================================================

-- 1.1 附件主表 wf_file
DROP TABLE IF EXISTS `wf_file`;
CREATE TABLE `wf_file` (
  `id`             BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `file_name`      VARCHAR(255) NOT NULL COMMENT '存储文件名',
  `original_name`  VARCHAR(255) NOT NULL COMMENT '原始文件名',
  `file_ext`       VARCHAR(32)  DEFAULT NULL COMMENT '文件后缀',
  `mime_type`      VARCHAR(100) DEFAULT NULL COMMENT 'MIME类型',
  `file_size`      BIGINT       DEFAULT 0 COMMENT '文件大小（字节）',
  `file_md5`       VARCHAR(64)  DEFAULT NULL COMMENT '文件MD5（去重用）',
  `storage_type`   VARCHAR(20)  NOT NULL DEFAULT 'local' COMMENT '存储方式：local本地 minio对象存储',
  `storage_path`   VARCHAR(500) DEFAULT NULL COMMENT '存储路径/对象key',
  `bucket`         VARCHAR(100) DEFAULT NULL COMMENT '存储桶（MinIO）',
  `biz_type`       VARCHAR(50)  DEFAULT NULL COMMENT '关联业务类型（如审批单、报表、公告）',
  `biz_id`         BIGINT       DEFAULT NULL COMMENT '关联业务ID',
  `is_private`     TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否私有：0公共 1私有',
  `is_locked`      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否归档锁定：0否 1是（锁定禁止删除）',
  `is_watermark`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否预览水印：0否 1是',
  `expire_time`    DATETIME     DEFAULT NULL COMMENT '有效期（临时附件过期清理）',
  `upload_user_id` BIGINT       DEFAULT NULL COMMENT '上传用户id',
  `create_by`      VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`    DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`      VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`    DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`     TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_md5` (`file_md5`),
  KEY `idx_biz` (`biz_type`, `biz_id`),
  KEY `idx_upload_user` (`upload_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='附件主表';

-- 1.2 上传/预览配置表 wf_file_config
DROP TABLE IF EXISTS `wf_file_config`;
CREATE TABLE `wf_file_config` (
  `id`                BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `config_key`        VARCHAR(100) NOT NULL COMMENT '配置键',
  `config_value`      VARCHAR(500) DEFAULT NULL COMMENT '配置值',
  `config_name`       VARCHAR(100) DEFAULT NULL COMMENT '配置名称',
  `config_type`       VARCHAR(30)  DEFAULT NULL COMMENT '配置分组：upload上传 preview预览 storage存储',
  `remark`            VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`         VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`       DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`         VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`       DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='附件上传/预览配置表';

-- 1.3 附件回收站表 wf_file_recycle
DROP TABLE IF EXISTS `wf_file_recycle`;
CREATE TABLE `wf_file_recycle` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `file_id`     BIGINT       NOT NULL COMMENT '原附件ID wf_file.id',
  `file_name`   VARCHAR(255) DEFAULT NULL COMMENT '文件名快照',
  `delete_user_id` BIGINT    DEFAULT NULL COMMENT '删除用户id',
  `delete_time` DATETIME     DEFAULT NULL COMMENT '删除时间',
  `create_time` DATETIME     DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_file_id` (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='附件回收站表';

-- =====================================================================
-- 二、消息中心模块
-- =====================================================================

-- 2.1 消息模板表 msg_template
DROP TABLE IF EXISTS `msg_template`;
CREATE TABLE `msg_template` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `template_code` VARCHAR(100) NOT NULL COMMENT '模板编码',
  `template_name` VARCHAR(100) NOT NULL COMMENT '模板名称',
  `msg_type`      VARCHAR(30)  NOT NULL COMMENT '消息类型：todo待办 done已办 cc抄送 system系统 report报表 alarm告警 notice公告',
  `template_content` VARCHAR(1000) DEFAULT NULL COMMENT '模板内容（含变量占位符）',
  `channel`       VARCHAR(30)  DEFAULT 'site' COMMENT '推送渠道：site站内 sms短信 email邮件',
  `status`        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `remark`        VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_code` (`template_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='消息模板表';

-- 2.2 站内消息表 msg_record
DROP TABLE IF EXISTS `msg_record`;
CREATE TABLE `msg_record` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `msg_type`     VARCHAR(30)  NOT NULL COMMENT '消息类型',
  `title`        VARCHAR(200) DEFAULT NULL COMMENT '消息标题',
  `content`      VARCHAR(1000) DEFAULT NULL COMMENT '消息内容',
  `receiver_id`  BIGINT       DEFAULT NULL COMMENT '接收用户id',
  `link_url`     VARCHAR(255) DEFAULT NULL COMMENT '跳转链接',
  `biz_type`     VARCHAR(50)  DEFAULT NULL COMMENT '关联业务类型',
  `biz_id`       BIGINT       DEFAULT NULL COMMENT '关联业务ID',
  `is_read`      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否已读：0未读 1已读',
  `read_time`    DATETIME     DEFAULT NULL COMMENT '已读时间',
  `create_by`    VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`    VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`  DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_receiver` (`receiver_id`, `is_read`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='站内消息表';

-- 2.3 消息推送记录表 msg_push_log
DROP TABLE IF EXISTS `msg_push_log`;
CREATE TABLE `msg_push_log` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `record_id`    BIGINT       DEFAULT NULL COMMENT '关联站内消息ID msg_record.id',
  `receiver_id`  BIGINT       DEFAULT NULL COMMENT '接收用户id',
  `channel`      VARCHAR(30)  DEFAULT NULL COMMENT '推送渠道：site短信 email',
  `push_status`  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '推送状态：0待推送 1成功 2失败',
  `error_msg`    VARCHAR(500) DEFAULT NULL COMMENT '失败原因',
  `retry_count`  INT          DEFAULT 0 COMMENT '重试次数',
  `push_time`    DATETIME     DEFAULT NULL COMMENT '推送时间',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_record_id` (`record_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='消息推送记录表';

-- 2.4 消息推送配置表 msg_push_config
DROP TABLE IF EXISTS `msg_push_config`;
CREATE TABLE `msg_push_config` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `channel`      VARCHAR(30)  NOT NULL COMMENT '渠道：site短信 email',
  `channel_name` VARCHAR(100) DEFAULT NULL COMMENT '渠道名称',
  `enabled`      TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否启用：0停用 1启用',
  `config_json`  TEXT         COMMENT '渠道配置JSON（短信服务商、邮件smtp等）',
  `remark`       VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`    VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`    VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`  DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_channel` (`channel`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='消息推送配置表';

-- =====================================================================
-- 三、公告通知模块
-- =====================================================================

-- 3.1 公告分类表 notice_category
DROP TABLE IF EXISTS `notice_category`;
CREATE TABLE `notice_category` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `category_name` VARCHAR(100) NOT NULL COMMENT '分类名称',
  `category_code` VARCHAR(64)  DEFAULT NULL COMMENT '分类编码',
  `sort`        INT          DEFAULT 0 COMMENT '排序',
  `status`      TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `remark`      VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`   VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='公告分类表';

-- 3.2 公告信息表 notice_info
DROP TABLE IF EXISTS `notice_info`;
CREATE TABLE `notice_info` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `category_id`   BIGINT       DEFAULT NULL COMMENT '公告分类ID',
  `title`         VARCHAR(200) NOT NULL COMMENT '公告标题',
  `content`       TEXT         COMMENT '公告内容',
  `attachment_ids` VARCHAR(500) DEFAULT NULL COMMENT '关联附件ID，逗号分隔',
  `is_top`        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否置顶：0否 1是',
  `status`        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0草稿 1发布 2下线',
  `role_scope`    VARCHAR(255) DEFAULT NULL COMMENT '可见角色范围（逗号分隔角色id，空为全部）',
  `start_time`    DATETIME     DEFAULT NULL COMMENT '生效开始时间',
  `end_time`      DATETIME     DEFAULT NULL COMMENT '生效结束时间',
  `publish_user_id` BIGINT     DEFAULT NULL COMMENT '发布用户id',
  `publish_time`  DATETIME     DEFAULT NULL COMMENT '发布时间',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_publish_time` (`publish_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='公告信息表';

-- 3.3 公告已读记录表 notice_read
DROP TABLE IF EXISTS `notice_read`;
CREATE TABLE `notice_read` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `notice_id`   BIGINT       NOT NULL COMMENT '公告ID',
  `user_id`     BIGINT       NOT NULL COMMENT '用户ID',
  `read_time`   DATETIME     DEFAULT NULL COMMENT '阅读时间',
  `create_time` DATETIME     DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_notice_user` (`notice_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='公告已读记录表';

-- =====================================================================
-- 四、定时任务管理模块（Celery）
-- =====================================================================

-- 4.1 任务信息表 task_info
DROP TABLE IF EXISTS `task_info`;
CREATE TABLE `task_info` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `task_name`     VARCHAR(100) NOT NULL COMMENT '任务名称',
  `task_key`      VARCHAR(100) NOT NULL COMMENT '任务唯一标识（Celery任务名）',
  `task_type`     VARCHAR(20)  NOT NULL COMMENT '调度类型：cron间隔 interval间隔',
  `cron_expr`     VARCHAR(100) DEFAULT NULL COMMENT 'cron表达式',
  `interval_sec`  INT          DEFAULT NULL COMMENT '间隔秒数',
  `params`        TEXT         COMMENT '任务参数JSON',
  `status`        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `retry_on_fail` TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '失败是否重试：0否 1是',
  `retry_count`   INT          DEFAULT 0 COMMENT '重试次数',
  `remark`        VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_key` (`task_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='定时任务信息表';

-- 4.2 任务日志表 task_log
DROP TABLE IF EXISTS `task_log`;
CREATE TABLE `task_log` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `task_id`      BIGINT       DEFAULT NULL COMMENT '任务ID task_info.id',
  `task_name`    VARCHAR(100) DEFAULT NULL COMMENT '任务名称快照',
  `run_status`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '执行状态：0运行中 1成功 2失败',
  `return_info`  TEXT         COMMENT '返回信息',
  `error_msg`    TEXT         COMMENT '异常报错信息',
  `cost_time`    BIGINT       DEFAULT 0 COMMENT '耗时（毫秒）',
  `run_time`     DATETIME     DEFAULT NULL COMMENT '执行时间',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_id` (`task_id`),
  KEY `idx_run_time` (`run_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='定时任务日志表';

-- =====================================================================
-- 五、报表管理模块
-- =====================================================================

-- 5.1 报表分类表 rp_category
DROP TABLE IF EXISTS `rp_category`;
CREATE TABLE `rp_category` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `category_name` VARCHAR(100) NOT NULL COMMENT '分类名称',
  `sort`          INT          DEFAULT 0 COMMENT '排序',
  `status`        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `remark`        VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='报表分类表';

-- 5.2 报表数据源配置表 rp_datasource
DROP TABLE IF EXISTS `rp_datasource`;
CREATE TABLE `rp_datasource` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `ds_name`       VARCHAR(100) NOT NULL COMMENT '数据源名称',
  `ds_type`       VARCHAR(20)  NOT NULL COMMENT '数据源类型：mysql本地库 api外部接口',
  `ds_config`     TEXT         COMMENT '数据源配置JSON（库连接或接口配置）',
  `status`        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `remark`        VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='报表数据源配置表';

-- 5.3 报表模板表 rp_template
DROP TABLE IF EXISTS `rp_template`;
CREATE TABLE `rp_template` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `template_name` VARCHAR(100) NOT NULL COMMENT '模板名称',
  `template_key`  VARCHAR(100) DEFAULT NULL COMMENT '模板唯一标识',
  `category_id`   BIGINT       DEFAULT NULL COMMENT '报表分类ID rp_category.id',
  `ds_id`         BIGINT       DEFAULT NULL COMMENT '数据源ID rp_datasource.id',
  `template_json` LONGTEXT     COMMENT 'lowcode-report报表设计JSON',
  `version`       INT          DEFAULT 1 COMMENT '模板版本',
  `status`        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `permission_json` TEXT       COMMENT '模板权限配置（角色可见/可编辑）',
  `remark`        VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='报表模板表';

-- 5.4 报表生成记录表 rp_generate_record
DROP TABLE IF EXISTS `rp_generate_record`;
CREATE TABLE `rp_generate_record` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `template_id`   BIGINT       DEFAULT NULL COMMENT '报表模板ID rp_template.id',
  `template_name` VARCHAR(100) DEFAULT NULL COMMENT '模板名称快照',
  `param_json`    TEXT         COMMENT '生成参数JSON',
  `gen_status`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '生成状态：0生成中 1成功 2失败',
  `file_id`       BIGINT       DEFAULT NULL COMMENT '生成文件附件ID wf_file.id',
  `error_msg`     TEXT         COMMENT '失败信息',
  `gen_type`      VARCHAR(20)  DEFAULT 'manual' COMMENT '生成方式：manual手动 schedule定时',
  `cost_time`     BIGINT       DEFAULT 0 COMMENT '耗时（毫秒）',
  `gen_user_id`   BIGINT       DEFAULT NULL COMMENT '执行用户id',
  `gen_time`      DATETIME     DEFAULT NULL COMMENT '生成时间',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_template_id` (`template_id`),
  KEY `idx_gen_time` (`gen_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='报表生成记录表';

-- =====================================================================
-- 六、报表大屏模块（datart）
-- =====================================================================

-- 6.1 大屏信息表 bi_screen
DROP TABLE IF EXISTS `bi_screen`;
CREATE TABLE `bi_screen` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `screen_name`   VARCHAR(100) NOT NULL COMMENT '大屏名称',
  `screen_config` LONGTEXT     COMMENT '大屏设计JSON（组件、布局、数据绑定）',
  `status`        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0草稿 1已发布 2停用',
  `share_url`     VARCHAR(255) DEFAULT NULL COMMENT '分享链接',
  `share_password` VARCHAR(64) DEFAULT NULL COMMENT '分享访问密码',
  `refresh_sec`   INT          DEFAULT 60 COMMENT '自动刷新间隔秒数',
  `snapshot_file_id` BIGINT    DEFAULT NULL COMMENT '大屏快照附件ID wf_file.id',
  `remark`        VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='报表大屏信息表';

-- 6.2 大屏数据集表 bi_dataset
DROP TABLE IF EXISTS `bi_dataset`;
CREATE TABLE `bi_dataset` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `dataset_name`  VARCHAR(100) NOT NULL COMMENT '数据集名称',
  `ds_type`       VARCHAR(20)  NOT NULL COMMENT '数据源类型：mysql api',
  `ds_config`     TEXT         COMMENT '数据集配置JSON',
  `screen_id`     BIGINT       DEFAULT NULL COMMENT '所属大屏ID bi_screen.id',
  `status`        TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `remark`        VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='大屏数据集表';

-- 6.3 大屏访问记录表 bi_visit_log
DROP TABLE IF EXISTS `bi_visit_log`;
CREATE TABLE `bi_visit_log` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `screen_id`    BIGINT       DEFAULT NULL COMMENT '大屏ID bi_screen.id',
  `visitor_user_id` BIGINT    DEFAULT NULL COMMENT '访问用户id',
  `visit_ip`     VARCHAR(50)  DEFAULT NULL COMMENT '访问IP',
  `visit_time`   DATETIME     DEFAULT NULL COMMENT '访问时间',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_screen_id` (`screen_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='大屏访问记录表';

-- =====================================================================
-- 七、数据同步 / 外部对接模块
-- =====================================================================

-- 7.1 外部接口配置表 outer_api_config
DROP TABLE IF EXISTS `outer_api_config`;
CREATE TABLE `outer_api_config` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `api_name`     VARCHAR(100) NOT NULL COMMENT '接口名称',
  `api_url`      VARCHAR(500) NOT NULL COMMENT '接口地址',
  `method`       VARCHAR(10)  NOT NULL DEFAULT 'GET' COMMENT '请求方式：GET/POST/PUT/DELETE',
  `headers_json` TEXT         COMMENT '请求头JSON',
  `params_json`  TEXT         COMMENT '请求参数JSON',
  `auth_type`    VARCHAR(20)  DEFAULT 'none' COMMENT '认证方式：none token basic',
  `auth_config`  TEXT         COMMENT '认证配置JSON（token值、basic账号密码）',
  `status`       TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `remark`       VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`    VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`    VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`  DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='外部接口配置表';

-- 7.2 外部接口请求日志表 outer_api_request_log
DROP TABLE IF EXISTS `outer_api_request_log`;
CREATE TABLE `outer_api_request_log` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `api_id`       BIGINT       DEFAULT NULL COMMENT '接口ID outer_api_config.id',
  `api_name`     VARCHAR(100) DEFAULT NULL COMMENT '接口名称快照',
  `request_url`  VARCHAR(500) DEFAULT NULL COMMENT '请求地址',
  `request_param` TEXT        COMMENT '请求参数',
  `response_body` TEXT        COMMENT '返回结果',
  `http_code`    INT          DEFAULT NULL COMMENT 'HTTP状态码',
  `cost_time`    BIGINT       DEFAULT 0 COMMENT '耗时（毫秒）',
  `error_msg`    TEXT         COMMENT '异常信息',
  `request_time` DATETIME     DEFAULT NULL COMMENT '请求时间',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_api_id` (`api_id`),
  KEY `idx_request_time` (`request_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='外部接口请求日志表';

-- 7.3 数据同步任务表 outer_sync_task
DROP TABLE IF EXISTS `outer_sync_task`;
CREATE TABLE `outer_sync_task` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `sync_name`    VARCHAR(100) NOT NULL COMMENT '同步任务名称',
  `api_id`       BIGINT       DEFAULT NULL COMMENT '来源接口ID outer_api_config.id',
  `target_table` VARCHAR(100) DEFAULT NULL COMMENT '目标本地表名',
  `sync_field_json` TEXT      COMMENT '字段映射JSON（接口字段->本地字段）',
  `sync_type`    VARCHAR(20)  DEFAULT 'manual' COMMENT '同步方式：manual手动 schedule定时',
  `task_id`      BIGINT       DEFAULT NULL COMMENT '关联定时任务ID task_info.id',
  `status`       TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '状态：0停用 1启用',
  `remark`       VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`    VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`    VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`  DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='数据同步任务表';

-- =====================================================================
-- 初始化基础配置数据（可选）
-- =====================================================================
-- 附件上传/预览默认配置
INSERT INTO `wf_file_config` (`id`, `config_key`, `config_value`, `config_name`, `config_type`, `create_time`, `is_deleted`) VALUES
  (1, 'file.upload.max_size', '10', '单文件大小上限(MB)', 'upload', NOW(), 0),
  (2, 'file.upload.chunk_size', '5', '分片大小(MB)', 'upload', NOW(), 0),
  (3, 'file.upload.whitelist', 'jpg,png,gif,pdf,doc,docx,xls,xlsx,ppt,pptx,txt,zip,mp4,mp3', '文件后缀白名单', 'upload', NOW(), 0),
  (4, 'file.storage.type', 'local', '存储方式(local/minio)', 'storage', NOW(), 0),
  (5, 'file.preview.kkfileview_url', 'http://127.0.0.1:8012', 'kkFileView服务地址', 'preview', NOW(), 0),
  (6, 'file.preview.onlyoffice_url', 'http://127.0.0.1:8080', 'OnlyOffice服务地址', 'preview', NOW(), 0),
  (7, 'file.watermark.enable', '0', '预览水印开关(0关1开)', 'preview', NOW(), 0),
  (8, 'file.expire.clean_days', '30', '过期附件清理周期(天)', 'storage', NOW(), 0);

-- =====================================================================
-- 完成。请按顺序执行。
-- =====================================================================
-- （注：内容由AI生成）
