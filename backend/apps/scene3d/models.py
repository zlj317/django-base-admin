"""3D 可视化模块模型（13 张表，表结构由 docs/scene3d_init.sql 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class Scene3dCategory(BaseModel):  # 继承 BaseModel，复用审计字段与逻辑删除
    """场景分类表：机房、档案库房、园区等业务归类。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    category_name = models.CharField('分类名称', max_length=100)  # 分类显示名称
    category_code = models.CharField('分类编码', max_length=50, unique=True)  # 分类唯一编码
    sort = models.IntegerField('排序', default=0)  # 排序号，数值小排前
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_category'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


class Scene3dTemplate(BaseModel):  # 场景模板，提供新建场景的默认配置
    """场景模板表：新建场景时选择模板快速起步。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    template_name = models.CharField('模板名称', max_length=100)  # 模板显示名称
    template_code = models.CharField('模板编码', max_length=50, unique=True)  # 模板唯一编码
    category_id = models.BigIntegerField('所属分类ID', blank=True, null=True)  # 关联 scene3d_category.id
    template_config = models.JSONField('模板默认配置', blank=True, null=True)  # 光照、相机、背景等默认配置
    thumbnail_file_id = models.BigIntegerField('缩略图附件ID', blank=True, null=True)  # 关联附件管理表
    sort = models.IntegerField('排序', default=0)  # 排序号
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_template'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


class Scene3dScene(BaseModel):  # 场景主表，scene_config 同时保存分享令牌
    """3D 场景主表：保存场景名称、分类、状态与全局配置。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_name = models.CharField('场景名称', max_length=100)  # 场景显示名称
    scene_code = models.CharField('场景业务编码', max_length=50, unique=True)  # 场景唯一编码
    category_id = models.BigIntegerField('分类ID')  # 关联 scene3d_category.id
    template_id = models.BigIntegerField('来源模板ID', blank=True, null=True)  # 关联 scene3d_template.id
    scene_status = models.SmallIntegerField('状态', default=0)  # 0 草稿 / 1 已发布 / 2 已下线
    thumbnail_file_id = models.BigIntegerField('缩略图附件ID', blank=True, null=True)  # 场景列表缩略图
    scene_config = models.JSONField('场景全局配置', blank=True, null=True)  # 相机、光照、背景、分享令牌等
    remark = models.CharField('场景描述', max_length=1000, blank=True, null=True)  # 场景备注

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_scene'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新创建在前


class Scene3dModelResource(BaseModel):  # 模型资源，file_id 指向 wf_file 的附件记录
    """模型资源表：登记 glb/gltf 等模型文件的元信息。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    model_name = models.CharField('模型名称', max_length=100)  # 模型显示名称
    model_code = models.CharField('模型编码', max_length=50, unique=True)  # 模型唯一编码
    model_type = models.CharField('模型类型', max_length=30, default='model')  # model/texture/material/env
    file_id = models.BigIntegerField('附件ID', default=0)  # 关联 wf_file.id，0 表示尚未上传
    triangle_count = models.IntegerField('三角面数', default=0)  # 模型三角面数量
    file_size = models.BigIntegerField('文件大小', default=0)  # 文件大小（byte）
    thumbnail_file_id = models.BigIntegerField('缩略图附件ID', blank=True, null=True)  # 模型缩略图
    sort = models.IntegerField('排序', default=0)  # 排序号
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_model_resource'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


class Scene3dSceneObject(BaseModel):  # 场景对象，用 object_code 在场景内做幂等标识
    """场景对象表：场景内模型实例的位置、旋转、缩放与标签。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('所属场景ID')  # 关联 scene3d_scene.id
    resource_id = models.BigIntegerField('模型资源ID')  # 关联 scene3d_model_resource.id
    object_name = models.CharField('对象名称', max_length=100)  # 如机柜A01
    object_code = models.CharField('对象业务编码', max_length=50)  # 场景内唯一编码
    parent_id = models.BigIntegerField('父对象ID', blank=True, null=True)  # 层级树父节点
    position = models.JSONField('坐标')  # {"x":0,"y":0,"z":0}
    rotation = models.JSONField('旋转')  # {"x":0,"y":0,"z":0}
    scale = models.JSONField('缩放')  # {"x":1,"y":1,"z":1}
    label_text = models.CharField('标签文字', max_length=200, blank=True, null=True)  # 漂浮标签
    is_show_label = models.SmallIntegerField('显示标签', default=1)  # 1 显示 / 0 隐藏
    sort = models.IntegerField('层级排序', default=0)  # 对象树排序
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_scene_object'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


class Scene3dDataBind(BaseModel):  # 数据绑定，source_config 仅允许引用白名单表
    """数据绑定表：场景对象与业务数据/接口/实时通道的绑定配置。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    object_id = models.BigIntegerField('场景对象ID')  # 关联 scene3d_scene_object.id
    bind_name = models.CharField('绑定名称', max_length=100)  # 绑定显示名称
    data_source_type = models.CharField('数据源类型', max_length=20, default='db')  # db/api/ws
    source_config = models.JSONField('数据源配置')  # 表名、字段、接口地址等
    refresh_interval = models.IntegerField('刷新间隔', default=30)  # 秒；ws 时为 0
    mapping_rule = models.JSONField('数值映射规则')  # 区间、颜色、状态、动画
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_data_bind'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认最新绑定在前


class Scene3dAlarmRule(BaseModel):  # 告警规则，挂在 binding 上做阈值判定
    """告警规则表：基于数据绑定的阈值规则与视觉表现配置。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    bind_id = models.BigIntegerField('绑定配置ID')  # 关联 scene3d_data_bind.id
    rule_name = models.CharField('规则名称', max_length=100)  # 规则显示名称
    compare_operator = models.CharField('比较符', max_length=20, default='>=')  # > >= < <= = between
    threshold_value = models.CharField('阈值', max_length=100)  # 单值或区间，如 "28" / "28,32"
    alarm_level = models.SmallIntegerField('告警级别', default=1)  # 1 提示 / 2 警告 / 3 严重
    alarm_effect = models.JSONField('视觉表现')  # 闪烁、光晕、颜色、图标
    is_auto_notice = models.SmallIntegerField('自动推送消息', default=1)  # 1 是 / 0 否
    is_auto_workflow = models.SmallIntegerField('自动发起审批', default=0)  # 1 是 / 0 否
    workflow_def_id = models.BigIntegerField('关联流程定义ID', blank=True, null=True)  # 工作流定义
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_alarm_rule'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认最新规则在前


class Scene3dAlarmRecord(models.Model):  # 仅继承 models.Model，表的审计字段由手工 SQL 固定
    """告警记录表（不继承 BaseModel）：本表仅有 create_time/update_time/is_deleted。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    object_id = models.BigIntegerField('对象ID')  # 关联 scene3d_scene_object.id
    rule_id = models.BigIntegerField('告警规则ID')  # 关联 scene3d_alarm_rule.id
    alarm_value = models.CharField('触发值', max_length=100)  # 触发时采集数值
    alarm_level = models.SmallIntegerField('告警级别', default=1)  # 1/2/3
    alarm_status = models.SmallIntegerField('告警状态', default=0)  # 0 未确认 / 1 已确认 / 2 已闭环 / 3 已忽略
    confirm_user_id = models.BigIntegerField('确认人ID', blank=True, null=True)  # 确认操作人
    confirm_time = models.DateTimeField('确认时间', blank=True, null=True)  # 确认时刻
    close_time = models.DateTimeField('闭环时间', blank=True, null=True)  # 闭环时刻
    work_order_id = models.BigIntegerField('关联工单ID', blank=True, null=True)  # 工单模块
    workflow_instance_id = models.BigIntegerField('关联审批实例ID', blank=True, null=True)  # 工作流模块
    remark = models.CharField('处置备注', max_length=1000, blank=True, null=True)  # 处置说明
    create_time = models.DateTimeField('告警发生时间', blank=True, null=True)  # 同 create_time
    update_time = models.DateTimeField('更新时间', blank=True, null=True)  # 最近修改时间
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_alarm_record'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-create_time', '-id']  # 最新告警在前


class Scene3dPatrolRoute(BaseModel):  # 巡检路线，way_points 存相机路径点位数组
    """巡检路线表：路径点位与漫游速度配置。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    route_name = models.CharField('路线名称', max_length=100)  # 路线显示名称
    route_code = models.CharField('路线编码', max_length=50)  # 路线唯一编码
    way_points = models.JSONField('路径点位')  # 相机坐标、视角、停留时长
    speed = models.DecimalField('漫游速度', max_digits=10, decimal_places=2, default=1.0)  # 默认速度
    cycle_flag = models.SmallIntegerField('是否循环', default=0)  # 1 是 / 0 否
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_patrol_route'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认最新路线在前


class Scene3dPatrolRecord(models.Model):  # 巡检执行记录，无 create_by/update_by 审计字段
    """巡检执行记录表（不继承 BaseModel）：仅本表实际存在的字段。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    route_id = models.BigIntegerField('巡检路线ID')  # 关联 scene3d_patrol_route.id
    patrol_code = models.CharField('巡检单号', max_length=50)  # 巡检业务单号
    patrol_user_id = models.BigIntegerField('巡检人ID')  # 执行人
    start_time = models.DateTimeField('开始时间')  # 巡检开始
    end_time = models.DateTimeField('结束时间', blank=True, null=True)  # 巡检结束
    patrol_status = models.SmallIntegerField('巡检状态', default=0)  # 0 进行中 / 1 正常完成 / 2 异常终止
    abnormal_count = models.IntegerField('异常数量', default=0)  # 发现异常数
    report_file_id = models.BigIntegerField('报告附件ID', blank=True, null=True)  # 巡检报告
    remark = models.CharField('巡检备注', max_length=1000, blank=True, null=True)  # 备注说明
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 记录创建时间
    update_time = models.DateTimeField('更新时间', blank=True, null=True)  # 最近修改时间
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_patrol_record'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-start_time', '-id']  # 最新巡检在前


class Scene3dSceneVersion(models.Model):  # 版本快照，snapshot_config 存配置与对象数组
    """场景版本表（不继承 BaseModel）：每次保存生成一条快照。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    version_no = models.CharField('版本号', max_length=30)  # v1/v2/v3
    version_desc = models.CharField('版本描述', max_length=500, blank=True, null=True)  # 版本说明
    snapshot_config = models.JSONField('场景快照配置')  # 全量场景配置
    thumbnail_file_id = models.BigIntegerField('快照缩略图', blank=True, null=True)  # 缩略图附件
    is_publish = models.SmallIntegerField('是否发布版本', default=0)  # 1 是 / 0 否
    create_by = models.CharField('版本创建人', max_length=64, blank=True, null=True)  # 操作人账号
    create_time = models.DateTimeField('版本生成时间', blank=True, null=True)  # 生成时刻
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_scene_version'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-create_time', '-id']  # 最新版本在前


class Scene3dScenePermission(BaseModel):  # 访问授权，target_type 决定目标表的含义
    """场景访问权限表：按角色/用户/部门授权只读、可交互、可编辑。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    target_type = models.CharField('授权对象类型', max_length=20, default='role')  # role/user/dept
    target_id = models.BigIntegerField('授权对象ID')  # 角色/用户/部门主键
    permission_type = models.SmallIntegerField('权限类型', default=1)  # 1 只读 / 2 可交互 / 3 可编辑
    expire_time = models.DateTimeField('授权过期时间', blank=True, null=True)  # 为空永久有效

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_scene_permission'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认最新授权在前


class Scene3dAccessLog(models.Model):  # 访问日志，分享访问时 user_id 为空
    """场景访问日志表（不继承 BaseModel）。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('访问场景ID')  # 关联 scene3d_scene.id
    user_id = models.BigIntegerField('访问用户ID', blank=True, null=True)  # 匿名访问为空
    access_ip = models.CharField('访问IP', max_length=50)  # 客户端 IP
    access_ua = models.CharField('浏览器UA', max_length=1000, blank=True, null=True)  # 浏览器标识
    access_type = models.CharField('访问方式', max_length=20, default='系统登录')  # 系统登录 / 分享链接
    stay_seconds = models.IntegerField('停留时长', default=0)  # 秒
    access_time = models.DateTimeField('访问时间', blank=True, null=True)  # 访问时刻
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记

    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_access_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-access_time', '-id']  # 最新访问在前
