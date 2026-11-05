-- =============================================
-- 数据库：django_base_admin
-- 3D可视化模块初始化脚本 scene3d_init.sql
-- 更新说明：所有主键使用雪花算法 BIGINT，无自增
-- 连接信息：192.168.0.76:3306 root / root
-- =============================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 1. 3D场景分类表 scene3d_category
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_category`;
CREATE TABLE `scene3d_category` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `category_name` VARCHAR(100) NOT NULL COMMENT '分类名称',
  `category_code` VARCHAR(50) NOT NULL COMMENT '分类编码',
  `sort` INT DEFAULT 0 COMMENT '排序号',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1启用 0禁用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_category_code` (`category_code`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='3D场景分类表';

-- ----------------------------
-- 2. 场景模板表 scene3d_template
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_template`;
CREATE TABLE `scene3d_template` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `template_name` VARCHAR(100) NOT NULL COMMENT '模板名称',
  `template_code` VARCHAR(50) NOT NULL COMMENT '模板编码',
  `category_id` BIGINT DEFAULT NULL COMMENT '所属分类ID，关联scene3d_category.id',
  `template_config` JSON DEFAULT NULL COMMENT '模板默认配置JSON（光照、天空盒、默认材质等）',
  `thumbnail_file_id` BIGINT DEFAULT NULL COMMENT '缩略图附件ID，关联附件管理表',
  `sort` INT DEFAULT 0 COMMENT '排序',
  `status` TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_template_code` (`template_code`),
  KEY `idx_category_id` (`category_id`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='3D场景模板表';

-- ----------------------------
-- 3. 3D场景主表 scene3d_scene
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_scene`;
CREATE TABLE `scene3d_scene` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_name` VARCHAR(100) NOT NULL COMMENT '场景名称',
  `scene_code` VARCHAR(50) NOT NULL COMMENT '场景业务编码',
  `category_id` BIGINT NOT NULL COMMENT '分类ID，scene3d_category.id',
  `template_id` BIGINT DEFAULT NULL COMMENT '来源模板ID，scene3d_template.id',
  `scene_status` TINYINT NOT NULL COMMENT '状态：0草稿 1已发布 2已下线',
  `thumbnail_file_id` BIGINT DEFAULT NULL COMMENT '场景缩略图附件ID',
  `scene_config` JSON DEFAULT NULL COMMENT '场景全局配置：相机默认视角、光照、背景、全局参数',
  `remark` VARCHAR(1000) DEFAULT '' COMMENT '场景描述备注',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_scene_code` (`scene_code`),
  KEY `idx_category_id` (`category_id`),
  KEY `idx_scene_status` (`scene_status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='3D场景主表';

-- ----------------------------
-- 4. 模型资源表 scene3d_model_resource
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_model_resource`;
CREATE TABLE `scene3d_model_resource` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `model_name` VARCHAR(100) NOT NULL COMMENT '模型名称',
  `model_code` VARCHAR(50) NOT NULL COMMENT '模型编码',
  `model_type` VARCHAR(30) NOT NULL COMMENT '模型类型 glb/gltf',
  `file_id` BIGINT NOT NULL COMMENT '附件ID，关联附件管理模块',
  `triangle_count` INT DEFAULT 0 COMMENT '三角面数量',
  `file_size` BIGINT DEFAULT 0 COMMENT '文件大小 单位byte',
  `thumbnail_file_id` BIGINT DEFAULT NULL COMMENT '模型缩略图附件ID',
  `sort` INT DEFAULT 0 COMMENT '排序',
  `status` TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_code` (`model_code`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='3D模型资源表';

-- ----------------------------
-- 5. 场景对象表 scene3d_scene_object
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_scene_object`;
CREATE TABLE `scene3d_scene_object` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '所属场景ID scene3d_scene.id',
  `resource_id` BIGINT NOT NULL COMMENT '模型资源ID scene3d_model_resource.id',
  `object_name` VARCHAR(100) NOT NULL COMMENT '对象名称，如A01机柜',
  `object_code` VARCHAR(50) NOT NULL COMMENT '对象业务编码',
  `parent_id` BIGINT DEFAULT NULL COMMENT '父对象ID，用于场景层级树',
  `position` JSON NOT NULL COMMENT '坐标 {x,y,z}',
  `rotation` JSON NOT NULL COMMENT '旋转 {x,y,z}',
  `scale` JSON NOT NULL COMMENT '缩放 {x,y,z}',
  `label_text` VARCHAR(200) DEFAULT '' COMMENT '漂浮标签文字',
  `is_show_label` TINYINT DEFAULT 1 COMMENT '是否显示标签 1是0否',
  `sort` INT DEFAULT 0 COMMENT '层级排序',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_resource_id` (`resource_id`),
  KEY `idx_parent_id` (`parent_id`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='场景内模型对象实例表';

-- ----------------------------
-- 6. 数据绑定配置表 scene3d_data_bind
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_data_bind`;
CREATE TABLE `scene3d_data_bind` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID scene3d_scene.id',
  `object_id` BIGINT NOT NULL COMMENT '场景对象ID scene3d_scene_object.id',
  `bind_name` VARCHAR(100) NOT NULL COMMENT '绑定名称',
  `data_source_type` VARCHAR(20) NOT NULL COMMENT '数据源类型：db数据库 / api接口 / ws websocket',
  `source_config` JSON NOT NULL COMMENT '数据源配置、字段映射配置',
  `refresh_interval` INT DEFAULT 30 COMMENT '轮询刷新间隔，单位秒，ws为0',
  `mapping_rule` JSON NOT NULL COMMENT '数值映射规则：区间、颜色、状态、动画',
  `status` TINYINT DEFAULT 1 COMMENT '1启用 0停用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_object_id` (`object_id`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='模型数据绑定配置表';

-- ----------------------------
-- 7. 告警规则表 scene3d_alarm_rule
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_alarm_rule`;
CREATE TABLE `scene3d_alarm_rule` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `bind_id` BIGINT NOT NULL COMMENT '绑定配置ID scene3d_data_bind.id',
  `rule_name` VARCHAR(100) NOT NULL COMMENT '规则名称',
  `compare_operator` VARCHAR(20) NOT NULL COMMENT '比较符 > >= < <= = between',
  `threshold_value` VARCHAR(100) NOT NULL COMMENT '阈值',
  `alarm_level` TINYINT NOT NULL COMMENT '告警级别 1提示 2警告 3严重',
  `alarm_effect` JSON NOT NULL COMMENT '前端效果：闪烁、光晕、颜色、图标',
  `is_auto_notice` TINYINT DEFAULT 1 COMMENT '是否自动推送消息',
  `is_auto_workflow` TINYINT DEFAULT 0 COMMENT '是否自动发起审批工单',
  `workflow_def_id` BIGINT DEFAULT NULL COMMENT '关联工作流定义ID（SpiffWorkflow）',
  `status` TINYINT DEFAULT 1 COMMENT '1启用 0停用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_bind_id` (`bind_id`),
  KEY `idx_alarm_level` (`alarm_level`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='3D可视化告警规则表';

-- ----------------------------
-- 8. 告警记录表 scene3d_alarm_record
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_alarm_record`;
CREATE TABLE `scene3d_alarm_record` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID',
  `object_id` BIGINT NOT NULL COMMENT '对象ID',
  `rule_id` BIGINT NOT NULL COMMENT '告警规则ID',
  `alarm_value` VARCHAR(100) NOT NULL COMMENT '触发时采集数值',
  `alarm_level` TINYINT NOT NULL COMMENT '告警级别',
  `alarm_status` TINYINT NOT NULL COMMENT '0未确认 1已确认 2已闭环 3已忽略',
  `confirm_user_id` BIGINT DEFAULT NULL COMMENT '确认人ID',
  `confirm_time` DATETIME DEFAULT NULL COMMENT '确认时间',
  `close_time` DATETIME DEFAULT NULL COMMENT '闭环时间',
  `work_order_id` BIGINT DEFAULT NULL COMMENT '关联工单ID',
  `workflow_instance_id` BIGINT DEFAULT NULL COMMENT '关联审批实例ID',
  `remark` VARCHAR(1000) DEFAULT '' COMMENT '处置备注',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '告警发生时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_object_id` (`object_id`),
  KEY `idx_rule_id` (`rule_id`),
  KEY `idx_alarm_status` (`alarm_status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='3D告警历史记录表';

-- ----------------------------
-- 9. 巡检路线表 scene3d_patrol_route
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_patrol_route`;
CREATE TABLE `scene3d_patrol_route` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID',
  `route_name` VARCHAR(100) NOT NULL COMMENT '巡检路线名称',
  `route_code` VARCHAR(50) NOT NULL COMMENT '路线编码',
  `way_points` JSON NOT NULL COMMENT '路径点位集合：相机坐标、视角、停留时长',
  `speed` DECIMAL(10,2) DEFAULT 1.0 COMMENT '漫游速度',
  `cycle_flag` TINYINT DEFAULT 0 COMMENT '是否循环 1是0否',
  `status` TINYINT DEFAULT 1 COMMENT '1启用0禁用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_status` (`status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='3D巡检路线配置表';

-- ----------------------------
-- 10. 巡检执行记录表 scene3d_patrol_record
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_patrol_record`;
CREATE TABLE `scene3d_patrol_record` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID',
  `route_id` BIGINT NOT NULL COMMENT '巡检路线ID',
  `patrol_code` VARCHAR(50) NOT NULL COMMENT '巡检单号',
  `patrol_user_id` BIGINT NOT NULL COMMENT '巡检人ID',
  `start_time` DATETIME NOT NULL COMMENT '巡检开始时间',
  `end_time` DATETIME DEFAULT NULL COMMENT '巡检结束时间',
  `patrol_status` TINYINT NOT NULL COMMENT '0进行中 1正常完成 2异常终止',
  `abnormal_count` INT DEFAULT 0 COMMENT '本次巡检发现异常数量',
  `report_file_id` BIGINT DEFAULT NULL COMMENT '巡检报告附件ID',
  `remark` VARCHAR(1000) DEFAULT '' COMMENT '巡检备注',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_route_id` (`route_id`),
  KEY `idx_patrol_user_id` (`patrol_user_id`),
  KEY `idx_patrol_status` (`patrol_status`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='巡检执行记录表';

-- ----------------------------
-- 11. 场景版本表 scene3d_scene_version
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_scene_version`;
CREATE TABLE `scene3d_scene_version` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID',
  `version_no` VARCHAR(30) NOT NULL COMMENT '版本号 v1/v2/v3',
  `version_desc` VARCHAR(500) DEFAULT '' COMMENT '版本描述',
  `snapshot_config` JSON NOT NULL COMMENT '场景全量快照配置',
  `thumbnail_file_id` BIGINT DEFAULT NULL COMMENT '快照缩略图',
  `is_publish` TINYINT DEFAULT 0 COMMENT '是否发布版本 1是0否',
  `create_by` BIGINT DEFAULT NULL COMMENT '版本创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '版本生成时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='场景版本快照表';

-- ----------------------------
-- 12. 场景访问权限表 scene3d_scene_permission
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_scene_permission`;
CREATE TABLE `scene3d_scene_permission` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID',
  `target_type` VARCHAR(20) NOT NULL COMMENT '授权对象：role角色 / user用户 / dept部门',
  `target_id` BIGINT NOT NULL COMMENT '角色/用户/部门ID',
  `permission_type` TINYINT NOT NULL COMMENT '权限类型：1只读 2可交互 3可编辑',
  `expire_time` DATETIME DEFAULT NULL COMMENT '授权过期时间，为空永久有效',
  `create_by` BIGINT DEFAULT NULL COMMENT '创建人ID',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` BIGINT DEFAULT NULL COMMENT '更新人ID',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_target_id` (`target_id`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='场景访问权限表';

-- ----------------------------
-- 13. 场景访问日志表 scene3d_access_log
-- ----------------------------
DROP TABLE IF EXISTS `scene3d_access_log`;
CREATE TABLE `scene3d_access_log` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '访问场景ID',
  `user_id` BIGINT DEFAULT NULL COMMENT '访问用户ID，匿名访问为空',
  `access_ip` VARCHAR(50) NOT NULL COMMENT '访问IP地址',
  `access_ua` VARCHAR(1000) DEFAULT '' COMMENT '浏览器UA',
  `access_type` VARCHAR(20) NOT NULL COMMENT '访问方式：系统登录 / 分享链接',
  `stay_seconds` INT DEFAULT 0 COMMENT '停留时长(秒)',
  `access_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '访问时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_access_time` (`access_time`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='场景访问日志表';


-- ===================== 初始化样例数据（雪花ID示例）=====================
INSERT INTO `scene3d_category` (`id`, `category_name`, `category_code`, `sort`, `status`, `remark`) VALUES
(1760000000000000001, '机房', 'ROOM_SERVER', 1, 1, '服务器机房场景'),
(1760000000000000002, '档案库房', 'ROOM_ARCHIVE', 2, 1, '档案库房场景'),
(1760000000000000003, '园区', 'PARK', 3, 1, '办公园区场景');

INSERT INTO `scene3d_template` (`id`, `template_name`, `template_code`, `category_id`, `template_config`, `sort`, `status`) VALUES
(1760000000000000011, '空白模板', 'TEMPLATE_EMPTY', NULL, '{}', 0, 1),
(1760000000000000012, '标准机房模板', 'TEMPLATE_SERVER_ROOM', 1760000000000000001, '{"sky":"#eeeeee","ambient":0.6}', 1, 1),
(1760000000000000013, '档案库房模板', 'TEMPLATE_ARCHIVE_ROOM', 1760000000000000002, '{"sky":"#f5f5f5","ambient":0.7}', 2, 1);

INSERT INTO `scene3d_scene` (`id`, `scene_name`, `scene_code`, `category_id`, `template_id`, `scene_status`, `scene_config`, `remark`) VALUES
(1760000000000000021, '数据中心机房 DC-ROOM-01', 'SC-2026-0001', 1760000000000000001, 1760000000000000012, 1, '{}', '机关信息机房，6台机柜、空调、UPS、温湿度传感器'),
(1760000000000000022, '档案库房 ARCH-ROOM-01', 'SC-2026-0002', 1760000000000000002, 1760000000000000013, 1, '{}', '档案库房，密集架、环境监测'),
(1760000000000000023, '办公园区', 'SC-2026-0003', 1760000000000000003, 1760000000000000011, 0, '{}', '办公园区草稿场景');

SET FOREIGN_KEY_CHECKS = 1;
