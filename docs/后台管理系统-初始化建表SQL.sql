-- =====================================================================
-- 后台管理系统 初始化建表 SQL（V1.0）
-- 数据库：MySQL 8.0.21（utf8mb4）
-- 实例：192.168.0.76:3306  账号 root / 密码 root
-- 说明：本脚本创建全部 sys_ 开头系统基础表（含代码生成器配置表）
-- 执行前请先自行创建业务数据库（示例：gen_admin），然后在此库中执行本脚本
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. 创建业务数据库（示例库名，如已存在可跳过）
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `gen_admin`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE `gen_admin`;

-- =====================================================================
-- 1. 用户表 sys_user
-- =====================================================================
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `username`    VARCHAR(50)  NOT NULL COMMENT '用户名（登录账号）',
  `password`    VARCHAR(100) NOT NULL COMMENT '密码（bcrypt加密）',
  `nickname`    VARCHAR(50)  DEFAULT NULL COMMENT '昵称',
  `phone`       VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
  `email`       VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  `avatar`      VARCHAR(255) DEFAULT NULL COMMENT '头像地址',
  `dept_id`     BIGINT       DEFAULT NULL COMMENT '所属部门ID',
  `status`      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0启用 1禁用',
  `create_by`   VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_dept_id` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统用户表';

-- =====================================================================
-- 2. 角色表 sys_role
-- =====================================================================
DROP TABLE IF EXISTS `sys_role`;
CREATE TABLE `sys_role` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `role_name`   VARCHAR(50) NOT NULL COMMENT '角色名称',
  `role_key`    VARCHAR(50) NOT NULL COMMENT '角色编码（唯一）',
  `role_sort`   INT         DEFAULT 0 COMMENT '角色排序',
  `status`      TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '状态：0启用 1禁用',
  `data_scope`  TINYINT(1)  NOT NULL DEFAULT 1 COMMENT '数据权限：1全部 2本部门 3自定义',
  `remark`      VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`   VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME    DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME    DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_key` (`role_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统角色表';

-- 用户-角色关联表（多对多）
DROP TABLE IF EXISTS `sys_user_role`;
CREATE TABLE `sys_user_role` (
  `user_id` BIGINT NOT NULL COMMENT '用户ID',
  `role_id` BIGINT NOT NULL COMMENT '角色ID',
  PRIMARY KEY (`user_id`, `role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户角色关联表';

-- =====================================================================
-- 3. 菜单权限表 sys_menu
-- =====================================================================
DROP TABLE IF EXISTS `sys_menu`;
CREATE TABLE `sys_menu` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `parent_id`   BIGINT      NOT NULL DEFAULT 0 COMMENT '父级菜单ID（0为顶级）',
  `menu_name`   VARCHAR(50) NOT NULL COMMENT '菜单名称',
  `path`        VARCHAR(200) DEFAULT NULL COMMENT '路由地址',
  `component`   VARCHAR(255) DEFAULT NULL COMMENT '前端组件路径',
  `perms`       VARCHAR(100) DEFAULT NULL COMMENT '权限标识，如 system:user:list',
  `menu_type`   CHAR(1)     NOT NULL DEFAULT 'M' COMMENT '菜单类型：M目录 C菜单 F按钮',
  `icon`        VARCHAR(100) DEFAULT NULL COMMENT '菜单图标',
  `order_num`   INT         DEFAULT 0 COMMENT '排序',
  `visible`     CHAR(1)     NOT NULL DEFAULT '0' COMMENT '是否可见：0显示 1隐藏',
  `status`      CHAR(1)     NOT NULL DEFAULT '0' COMMENT '状态：0正常 1停用',
  `create_by`   VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME    DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME    DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统菜单权限表';

-- 角色-菜单关联表（多对多）
DROP TABLE IF EXISTS `sys_role_menu`;
CREATE TABLE `sys_role_menu` (
  `role_id` BIGINT NOT NULL COMMENT '角色ID',
  `menu_id` BIGINT NOT NULL COMMENT '菜单ID',
  PRIMARY KEY (`role_id`, `menu_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色菜单关联表';

-- =====================================================================
-- 4. 部门表 sys_dept
-- =====================================================================
DROP TABLE IF EXISTS `sys_dept`;
CREATE TABLE `sys_dept` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `parent_id`   BIGINT      NOT NULL DEFAULT 0 COMMENT '父部门ID（0为顶级）',
  `dept_name`   VARCHAR(50) NOT NULL COMMENT '部门名称',
  `order_num`   INT         DEFAULT 0 COMMENT '排序',
  `leader`      VARCHAR(50) DEFAULT NULL COMMENT '负责人',
  `phone`       VARCHAR(20) DEFAULT NULL COMMENT '联系电话',
  `status`      CHAR(1)     NOT NULL DEFAULT '0' COMMENT '状态：0正常 1停用',
  `create_by`   VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME    DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME    DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统部门表';

-- =====================================================================
-- 5. 字典类型表 sys_dict_type
-- =====================================================================
DROP TABLE IF EXISTS `sys_dict_type`;
CREATE TABLE `sys_dict_type` (
  `id`          BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `dict_name`   VARCHAR(100) NOT NULL COMMENT '字典名称',
  `dict_type`   VARCHAR(100) NOT NULL COMMENT '字典类型编码（唯一）',
  `status`      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '状态：0启用 1停用',
  `remark`      VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`   VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME    DEFAULT NULL COMMENT '创建时间',
  `update_by`   VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
  `update_time` DATETIME    DEFAULT NULL COMMENT '更新时间',
  `is_deleted`  TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dict_type` (`dict_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='字典类型表';

-- =====================================================================
-- 6. 字典数据表 sys_dict_data
-- =====================================================================
DROP TABLE IF EXISTS `sys_dict_data`;
CREATE TABLE `sys_dict_data` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `dict_type_id`  BIGINT NOT NULL COMMENT '所属字典类型ID',
  `dict_label`    VARCHAR(100) NOT NULL COMMENT '字典标签（展示文本）',
  `dict_value`    VARCHAR(100) NOT NULL COMMENT '字典键值',
  `dict_sort`     INT DEFAULT 0 COMMENT '排序',
  `status`        TINYINT(1) NOT NULL DEFAULT 0 COMMENT '状态：0启用 1停用',
  `remark`        VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`     VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME    DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME    DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)  NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_dict_type_id` (`dict_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='字典数据表';

-- =====================================================================
-- 7. 操作日志表 sys_oper_log
-- =====================================================================
DROP TABLE IF EXISTS `sys_oper_log`;
CREATE TABLE `sys_oper_log` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `oper_user`     VARCHAR(64)  DEFAULT NULL COMMENT '操作人账号',
  `module_name`   VARCHAR(50)  DEFAULT NULL COMMENT '操作模块',
  `oper_type`     VARCHAR(20)  DEFAULT NULL COMMENT '操作类型：新增/编辑/删除/导出/导入',
  `request_url`   VARCHAR(255) DEFAULT NULL COMMENT '请求地址',
  `request_param` TEXT         COMMENT '请求参数',
  `response_result` TEXT       COMMENT '响应结果',
  `cost_time`     BIGINT       DEFAULT NULL COMMENT '耗时（毫秒）',
  `oper_time`     DATETIME     DEFAULT NULL COMMENT '操作时间',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_oper_time` (`oper_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统操作日志表';

-- =====================================================================
-- 8. 登录日志表 sys_login_log
-- =====================================================================
DROP TABLE IF EXISTS `sys_login_log`;
CREATE TABLE `sys_login_log` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `username`     VARCHAR(50)  DEFAULT NULL COMMENT '登录账号',
  `ip`           VARCHAR(50)  DEFAULT NULL COMMENT '登录IP',
  `login_time`   DATETIME     DEFAULT NULL COMMENT '登录时间',
  `status`       TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '登录状态：0成功 1失败',
  `browser`      VARCHAR(100) DEFAULT NULL COMMENT '浏览器信息',
  `msg`          VARCHAR(255) DEFAULT NULL COMMENT '提示消息',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  `is_deleted`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_login_time` (`login_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统登录日志表';

-- =====================================================================
-- 9. 系统配置表 sys_config
-- =====================================================================
DROP TABLE IF EXISTS `sys_config`;
CREATE TABLE `sys_config` (
  `id`           BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `config_key`   VARCHAR(100) NOT NULL COMMENT '配置键（唯一）',
  `config_value` VARCHAR(500) DEFAULT NULL COMMENT '配置值',
  `config_name`  VARCHAR(100) DEFAULT NULL COMMENT '配置名称',
  `remark`       VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `create_by`    VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`  DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`    VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`  DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统配置表';

-- =====================================================================
-- 10. 代码生成配置表 sys_gen_table（生成任务主表）
-- =====================================================================
DROP TABLE IF EXISTS `sys_gen_table`;
CREATE TABLE `sys_gen_table` (
  `id`              BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `table_name`      VARCHAR(100) NOT NULL COMMENT '数据库表名',
  `table_comment`   VARCHAR(200) DEFAULT NULL COMMENT '表注释',
  `class_name`      VARCHAR(100) DEFAULT NULL COMMENT '生成的实体类名（Django model名）',
  `module_name`     VARCHAR(50)  DEFAULT NULL COMMENT '模块英文标识，如 student',
  `module_comment`  VARCHAR(100) DEFAULT NULL COMMENT '模块中文名称',
  `url_prefix`      VARCHAR(100) DEFAULT NULL COMMENT '接口路由前缀，如 /api/student/',
  `gen_path`        VARCHAR(255) DEFAULT NULL COMMENT '前端页面存放路径',
  `parent_menu_id`  BIGINT       DEFAULT NULL COMMENT '父级菜单ID（生成菜单用）',
  `is_delete_logic` TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否开启逻辑删除：1开 0关',
  `import_enable`   TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否开启导入：1开 0关',
  `export_enable`   TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否开启导出：1开 0关',
  `create_by`       VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`     DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`       VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`     DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_table_name` (`table_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代码生成配置表';

-- =====================================================================
-- 11. 代码生成字段配置表 sys_gen_table_column（核心配置表）
-- =====================================================================
DROP TABLE IF EXISTS `sys_gen_table_column`;
CREATE TABLE `sys_gen_table_column` (
  `id`            BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `gen_table_id`  BIGINT      NOT NULL COMMENT '关联生成任务ID（sys_gen_table.id）',
  `column_name`   VARCHAR(100) NOT NULL COMMENT '数据库字段名',
  `column_comment` VARCHAR(200) DEFAULT NULL COMMENT '字段注释',
  `column_type`   VARCHAR(50)  DEFAULT NULL COMMENT '字段类型，如 int/varchar/datetime/decimal',
  `is_pk`         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否主键：1是 0否',
  `dict_type`     VARCHAR(100) DEFAULT NULL COMMENT '绑定字典类型编码',
  `form_type`     VARCHAR(50)  DEFAULT NULL COMMENT '表单控件：input/number/date/select/radio/textarea/image/file',
  `is_list`       TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否列表展示：1是 0否',
  `is_query`      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否查询条件：1是 0否',
  `query_type`    VARCHAR(20)  DEFAULT NULL COMMENT '查询方式：eq/like/gt/lt/between',
  `is_required`   TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否必填：1是 0否',
  `is_export`     TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否导出字段：1是 0否',
  `is_import`     TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '是否导入字段：1是 0否',
  `sort`          INT          DEFAULT 0 COMMENT '排序号',
  `create_by`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人账号',
  `create_time`   DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_by`     VARCHAR(64)  DEFAULT NULL COMMENT '更新人账号',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  `is_deleted`    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删 1已删',
  PRIMARY KEY (`id`),
  KEY `idx_gen_table_id` (`gen_table_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代码生成字段配置表';

-- =====================================================================
-- 12. 初始化基础数据（可选，管理员账号 admin / 123456，密码占位，请按需调整）
-- =====================================================================
INSERT INTO `sys_user` (`id`, `username`, `password`, `nickname`, `status`, `create_time`, `is_deleted`)
VALUES (1, 'admin', 'admin_placeholder_use_bcrypt', '系统管理员', 0, NOW(), 0);

INSERT INTO `sys_role` (`id`, `role_name`, `role_key`, `role_sort`, `status`, `create_time`, `is_deleted`)
VALUES (1, '超级管理员', 'admin', 1, 0, NOW(), 0);

INSERT INTO `sys_user_role` (`user_id`, `role_id`) VALUES (1, 1);

INSERT INTO `sys_config` (`id`, `config_key`, `config_value`, `config_name`, `create_time`, `is_deleted`)
VALUES
  (1, 'sys.upload.max_size', '10', '上传文件大小上限(MB)', NOW(), 0),
  (2, 'sys.export.max_rows', '50000', '导出最大行数', NOW(), 0),
  (3, 'sys.page.default_size', '10', '默认分页条数', NOW(), 0);

-- =====================================================================
-- 完成。请按顺序执行，并在 Django 中配置对应连接信息。
-- =====================================================================
-- （注：内容由AI生成）
