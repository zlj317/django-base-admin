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
CREATE TABLE IF NOT EXISTS `scene3d_category` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `category_name` VARCHAR(100) NOT NULL COMMENT '分类名称',
  `category_code` VARCHAR(50) NOT NULL COMMENT '分类编码',
  `sort` INT DEFAULT 0 COMMENT '排序号',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1启用 0禁用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_template` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `template_name` VARCHAR(100) NOT NULL COMMENT '模板名称',
  `template_code` VARCHAR(50) NOT NULL COMMENT '模板编码',
  `category_id` BIGINT DEFAULT NULL COMMENT '所属分类ID，关联scene3d_category.id',
  `template_config` JSON DEFAULT NULL COMMENT '模板默认配置JSON（光照、天空盒、默认材质等）',
  `thumbnail_file_id` BIGINT DEFAULT NULL COMMENT '缩略图附件ID，关联附件管理表',
  `sort` INT DEFAULT 0 COMMENT '排序',
  `status` TINYINT DEFAULT 1 COMMENT '1启用 0禁用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_scene` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_name` VARCHAR(100) NOT NULL COMMENT '场景名称',
  `scene_code` VARCHAR(50) NOT NULL COMMENT '场景业务编码',
  `category_id` BIGINT NOT NULL COMMENT '分类ID，scene3d_category.id',
  `template_id` BIGINT DEFAULT NULL COMMENT '来源模板ID，scene3d_template.id',
  `scene_status` TINYINT NOT NULL COMMENT '状态：0草稿 1已发布 2已下线',
  `thumbnail_file_id` BIGINT DEFAULT NULL COMMENT '场景缩略图附件ID',
  `scene_config` JSON DEFAULT NULL COMMENT '场景全局配置：相机默认视角、光照、背景、全局参数',
  `remark` VARCHAR(1000) DEFAULT '' COMMENT '场景描述备注',
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_model_resource` (
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
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_scene_object` (
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
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_data_bind` (
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
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_alarm_rule` (
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
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_alarm_record` (
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
CREATE TABLE IF NOT EXISTS `scene3d_patrol_route` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID',
  `route_name` VARCHAR(100) NOT NULL COMMENT '巡检路线名称',
  `route_code` VARCHAR(50) NOT NULL COMMENT '路线编码',
  `way_points` JSON NOT NULL COMMENT '路径点位集合：相机坐标、视角、停留时长',
  `speed` DECIMAL(10,2) DEFAULT 1.0 COMMENT '漫游速度',
  `cycle_flag` TINYINT DEFAULT 0 COMMENT '是否循环 1是0否',
  `status` TINYINT DEFAULT 1 COMMENT '1启用0禁用',
  `remark` VARCHAR(500) DEFAULT '' COMMENT '备注',
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_patrol_record` (
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
CREATE TABLE IF NOT EXISTS `scene3d_scene_version` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID',
  `version_no` VARCHAR(30) NOT NULL COMMENT '版本号 v1/v2/v3',
  `version_desc` VARCHAR(500) DEFAULT '' COMMENT '版本描述',
  `snapshot_config` JSON NOT NULL COMMENT '场景全量快照配置',
  `thumbnail_file_id` BIGINT DEFAULT NULL COMMENT '快照缩略图',
  `is_publish` TINYINT DEFAULT 0 COMMENT '是否发布版本 1是0否',
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '版本创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '版本生成时间',
  `is_deleted` TINYINT DEFAULT 0 COMMENT '是否删除 0否 1是',
  PRIMARY KEY (`id`),
  KEY `idx_scene_id` (`scene_id`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='场景版本快照表';

-- ----------------------------
-- 12. 场景访问权限表 scene3d_scene_permission
-- ----------------------------
CREATE TABLE IF NOT EXISTS `scene3d_scene_permission` (
  `id` BIGINT NOT NULL COMMENT '雪花主键ID',
  `scene_id` BIGINT NOT NULL COMMENT '场景ID',
  `target_type` VARCHAR(20) NOT NULL COMMENT '授权对象：role角色 / user用户 / dept部门',
  `target_id` BIGINT NOT NULL COMMENT '角色/用户/部门ID',
  `permission_type` TINYINT NOT NULL COMMENT '权限类型：1只读 2可交互 3可编辑',
  `expire_time` DATETIME DEFAULT NULL COMMENT '授权过期时间，为空永久有效',
  `create_by` VARCHAR(64) DEFAULT NULL COMMENT '创建人账号',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_by` VARCHAR(64) DEFAULT NULL COMMENT '更新人账号',
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
CREATE TABLE IF NOT EXISTS `scene3d_access_log` (
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


-- ===================== 初始化样例数据（雪花ID示例，INSERT IGNORE 幂等）=====================
-- 说明：全部使用 INSERT IGNORE，重复执行 init_db 不会产生重复数据，也不会覆盖用户改动。
INSERT IGNORE INTO `scene3d_category` (`id`, `category_name`, `category_code`, `sort`, `status`, `remark`) VALUES
(1760000000000000001, '机房', 'ROOM_SERVER', 1, 1, '服务器机房场景'),
(1760000000000000002, '档案库房', 'ROOM_ARCHIVE', 2, 1, '档案库房场景'),
(1760000000000000003, '园区', 'PARK', 3, 1, '办公园区场景');

INSERT IGNORE INTO `scene3d_template` (`id`, `template_name`, `template_code`, `category_id`, `template_config`, `sort`, `status`) VALUES
(1760000000000000011, '空白模板', 'TEMPLATE_EMPTY', NULL, '{}', 0, 1),
(1760000000000000012, '标准机房模板', 'TEMPLATE_SERVER_ROOM', 1760000000000000001, '{"sky":"#eeeeee","ambient":0.6}', 1, 1),
(1760000000000000013, '档案库房模板', 'TEMPLATE_ARCHIVE_ROOM', 1760000000000000002, '{"sky":"#f5f5f5","ambient":0.7}', 2, 1);

INSERT IGNORE INTO `scene3d_scene` (`id`, `scene_name`, `scene_code`, `category_id`, `template_id`, `scene_status`, `scene_config`, `remark`) VALUES
(1760000000000000021, '数据中心机房 DC-ROOM-01', 'SC-2026-0001', 1760000000000000001, 1760000000000000012, 1, '{}', '机关信息机房，6台机柜、空调、UPS、温湿度传感器'),
(1760000000000000022, '档案库房 ARCH-ROOM-01', 'SC-2026-0002', 1760000000000000002, 1760000000000000013, 1, '{}', '档案库房，密集架、环境监测'),
(1760000000000000023, '办公园区', 'SC-2026-0003', 1760000000000000003, 1760000000000000011, 0, '{}', '办公园区草稿场景');

-- 模型资源：仅登记元信息，file_id=0 表示尚未上传真实 glb 文件；前端用程序化几何体占位渲染
INSERT IGNORE INTO `scene3d_model_resource` (`id`, `model_name`, `model_code`, `model_type`, `file_id`, `triangle_count`, `file_size`, `sort`, `status`, `remark`) VALUES
(1760000000000000031, '机柜_42U标准柜', 'MD-0001', 'model', 0, 118400, 6501171, 1, 1, 'A系列机柜通用，程序化占位'),
(1760000000000000032, '服务器_2U机架式', 'MD-0002', 'model', 0, 42600, 3250585, 2, 1, '机柜内服务器实例'),
(1760000000000000033, '精密空调_风冷机组', 'MD-0003', 'model', 0, 156200, 9122611, 3, 1, '机房精密空调'),
(1760000000000000034, 'UPS_模块化主机', 'MD-0004', 'model', 0, 88300, 5662310, 4, 1, '模块化UPS机柜'),
(1760000000000000035, '档案密集架_六联', 'MD-0005', 'model', 0, 210500, 12373196, 5, 1, '档案库房密集架'),
(1760000000000000036, '温湿度传感器_吸顶', 'MD-0006', 'model', 0, 8600, 629145, 6, 1, '吊顶传感器');

-- 场景对象：数据中心机房 2 排 × 3 列机柜 + 服务器/空调/UPS/温湿度传感器
INSERT IGNORE INTO `scene3d_scene_object` (`id`, `scene_id`, `resource_id`, `object_name`, `object_code`, `parent_id`, `position`, `rotation`, `scale`, `label_text`, `is_show_label`, `sort`, `remark`) VALUES
(1760000000000000041, 1760000000000000021, 1760000000000000031, '机柜A01', 'cabinet_A01', NULL, '{"x":-3,"y":0,"z":0}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '机柜A01', 1, 1, '第1排左'),
(1760000000000000042, 1760000000000000021, 1760000000000000031, '机柜A02', 'cabinet_A02', NULL, '{"x":0,"y":0,"z":0}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '机柜A02', 1, 2, '第1排中'),
(1760000000000000043, 1760000000000000021, 1760000000000000031, '机柜A03', 'cabinet_A03', NULL, '{"x":3,"y":0,"z":0}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '机柜A03', 1, 3, '第1排右'),
(1760000000000000044, 1760000000000000021, 1760000000000000031, '机柜A04', 'cabinet_A04', NULL, '{"x":-3,"y":0,"z":-2.2}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '机柜A04', 1, 4, '第2排左'),
(1760000000000000045, 1760000000000000021, 1760000000000000031, '机柜A05', 'cabinet_A05', NULL, '{"x":0,"y":0,"z":-2.2}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '机柜A05', 1, 5, '第2排中'),
(1760000000000000046, 1760000000000000021, 1760000000000000031, '机柜A06', 'cabinet_A06', NULL, '{"x":3,"y":0,"z":-2.2}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '机柜A06', 1, 6, '第2排右'),
(1760000000000000047, 1760000000000000021, 1760000000000000032, '服务器A01-01', 'server_A01_01', 1760000000000000041, '{"x":-3,"y":1.2,"z":0.1}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '服务器A01-01', 1, 7, 'A01柜U12位'),
(1760000000000000048, 1760000000000000021, 1760000000000000033, '精密空调01', 'ac_01', NULL, '{"x":5.5,"y":0,"z":-1}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '精密空调01', 1, 8, '机房东侧'),
(1760000000000000049, 1760000000000000021, 1760000000000000034, 'UPS主机', 'ups_01', NULL, '{"x":-5.5,"y":0,"z":-3.5}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', 'UPS主机', 1, 9, '配电区'),
(1760000000000000050, 1760000000000000021, 1760000000000000036, '温湿度传感器T01', 'sensor_T01', NULL, '{"x":0,"y":3.2,"z":0}', '{"x":0,"y":0,"z":0}', '{"x":1,"y":1,"z":1}', '温湿度传感器T01', 1, 10, '吊顶中央');

-- 数据绑定：机柜进风温度 + 服务器负载（表名走白名单，禁止用户输入 SQL）
INSERT IGNORE INTO `scene3d_data_bind` (`id`, `scene_id`, `object_id`, `bind_name`, `data_source_type`, `source_config`, `refresh_interval`, `mapping_rule`, `status`, `remark`) VALUES
(1760000000000000051, 1760000000000000021, 1760000000000000041, '机柜A01进风温度', 'db', '{"table":"scene3d_scene_object","field":"temperature"}', 30, '{"ranges":[{"max":28,"color":"#00b42a"},{"max":32,"color":"#ff7d00"},{"color":"#f53f3f"}]}', 1, '25~28℃绿 / 28~32℃黄 / >32℃红'),
(1760000000000000052, 1760000000000000021, 1760000000000000047, '服务器A01-01负载', 'db', '{"table":"scene3d_scene_object","field":"load"}', 30, '{"ranges":[{"max":40,"color":"#165dff"},{"max":70,"color":"#ff7d00"},{"color":"#f53f3f"}]}', 1, '0~40%蓝 / 40~70%黄 / >70%红');

-- 告警规则：机柜温度两级阈值
INSERT IGNORE INTO `scene3d_alarm_rule` (`id`, `bind_id`, `rule_name`, `compare_operator`, `threshold_value`, `alarm_level`, `alarm_effect`, `is_auto_notice`, `is_auto_workflow`, `status`, `remark`) VALUES
(1760000000000000061, 1760000000000000051, '机柜温度偏高', '>=', '28', 2, '{"blink":true,"glow":true,"color":"#ff7d00"}', 1, 0, 1, '触发黄色闪烁'),
(1760000000000000062, 1760000000000000051, '机柜温度严重过高', '>=', '32', 3, '{"blink":true,"glow":true,"color":"#f53f3f"}', 1, 0, 1, '红色脉冲 + 告警音效');

-- 告警记录：一条未确认、一条已确认
INSERT IGNORE INTO `scene3d_alarm_record` (`id`, `scene_id`, `object_id`, `rule_id`, `alarm_value`, `alarm_level`, `alarm_status`, `confirm_user_id`, `confirm_time`, `remark`) VALUES
(1760000000000000063, 1760000000000000021, 1760000000000000041, 1760000000000000061, '30.5℃', 2, 0, NULL, NULL, '温度超过28℃'),
(1760000000000000064, 1760000000000000021, 1760000000000000049, 1760000000000000061, '82%', 2, 1, 1, '2026-11-04 15:30:12', 'UPS负载偏高，已确认');

-- 巡检路线：入口 → 第1排 → 第2排 → 空调 → UPS → 出口
INSERT IGNORE INTO `scene3d_patrol_route` (`id`, `scene_id`, `route_name`, `route_code`, `way_points`, `speed`, `cycle_flag`, `status`, `remark`) VALUES
(1760000000000000071, 1760000000000000021, '机房日常巡检路线', 'XJ-ROUTE-001', '[{"x":0,"y":5,"z":9,"lookAt":{"x":0,"y":1,"z":0}},{"x":-4,"y":3,"z":3,"lookAt":{"x":-3,"y":1,"z":0}},{"x":0,"y":3,"z":3,"lookAt":{"x":0,"y":1,"z":0}},{"x":4,"y":3,"z":3,"lookAt":{"x":3,"y":1,"z":0}},{"x":0,"y":3,"z":-5,"lookAt":{"x":0,"y":1,"z":-2.2}},{"x":6,"y":3,"z":0,"lookAt":{"x":5.5,"y":1,"z":-1}},{"x":-6,"y":3,"z":-3,"lookAt":{"x":-5.5,"y":1,"z":-3.5}}]', 1.20, 0, 1, '6机柜巡回路线');

-- 巡检记录：一条已完成
INSERT IGNORE INTO `scene3d_patrol_record` (`id`, `scene_id`, `route_id`, `patrol_code`, `patrol_user_id`, `start_time`, `end_time`, `patrol_status`, `abnormal_count`, `remark`) VALUES
(1760000000000000072, 1760000000000000021, 1760000000000000071, 'XJ-20261105-001', 1, '2026-11-05 08:30:00', '2026-11-05 08:52:00', 1, 1, '机柜A01温度偏高，已报修');

-- 场景版本：机房 3 个历史版本
INSERT IGNORE INTO `scene3d_scene_version` (`id`, `scene_id`, `version_no`, `version_desc`, `snapshot_config`, `is_publish`, `create_by`, `create_time`) VALUES
(1760000000000000081, 1760000000000000021, 'v1', '初始搭建6机柜布局', '{}', 1, 'admin', '2026-10-20 10:00:00'),
(1760000000000000082, 1760000000000000021, 'v2', '增加精密空调、UPS模型', '{}', 0, 'admin', '2026-10-28 15:20:00'),
(1760000000000000083, 1760000000000000021, 'v3', '完善数据绑定与告警规则', '{}', 1, 'admin', '2026-11-04 17:40:00');

-- 访问日志：两条样本，用于「场景发布」页的访问记录展示
INSERT IGNORE INTO `scene3d_access_log` (`id`, `scene_id`, `user_id`, `access_ip`, `access_ua`, `access_type`, `stay_seconds`, `access_time`) VALUES
(1760000000000000091, 1760000000000000021, 1, '192.168.0.101', 'Mozilla/5.0 (Windows NT 10.0) Chrome/120.0', '系统登录', 320, '2026-11-05 10:20:15'),
(1760000000000000092, 1760000000000000021, 1, '192.168.0.88', 'Mozilla/5.0 (Windows NT 10.0) Chrome/120.0', '系统登录', 600, '2026-11-04 16:30:40');

SET FOREIGN_KEY_CHECKS = 1;
