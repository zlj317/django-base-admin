# 模块：apps/scene3d/models.py —— 3D 可视化（数字孪生）模块 13 张 scene3d_ 表的 ORM 映射
# 用途：覆盖分类、模板、场景、模型资源、场景对象、数据绑定、告警规则、告警记录、
#       巡检路线、巡检记录、场景版本、场景权限、访问日志，共 13 张业务表。
# 覆盖表：scene3d_category、scene3d_template、scene3d_scene、scene3d_model_resource、
#         scene3d_scene_object、scene3d_data_bind、scene3d_alarm_rule、scene3d_alarm_record、
#         scene3d_patrol_route、scene3d_patrol_record、scene3d_scene_version、
#         scene3d_scene_permission、scene3d_access_log。
# 路由前缀：scene3d（最终 URL 形如 /api/scene3d/list，见 apps/scene3d/urls.py；视图实现位于 apps/scene3d/views.py）。
# 3D 数据约定：
#   1) 模型资源：file_id 关联 apps/file 的 wf_file.id，0 表示尚未上传真实 glb/gltf 文件，
#      此时前端用程序化几何体占位渲染（初始化 SQL 中的样例数据即为此种情况）；
#   2) 场景对象：position/rotation/scale 统一为 {"x":..,"y":..,"z":..} JSON，parent_id 组织对象层级树，
#      object_code 在同一场景内唯一，作为保存/版本回滚时比对新旧对象的幂等标识；
#   3) 数据绑定：source_config 只允许引用白名单内的表与字段（禁止用户输入 SQL，避免注入），
#      refresh_interval 单位为秒，ws 实时源固定为 0；
#   4) 告警：规则挂在数据绑定上，记录由规则命中触发；alarm_status 0未确认/1已确认/2已闭环/3已忽略；
#   5) 巡检：路线 way_points 为相机点位数组（坐标 + lookAt + 停留时长），记录表示一次巡检执行；
#   6) 分享：分享令牌保存在 scene3d_scene.scene_config 的 share 键中（token/expire/create_by），
#      由 apps/scene3d/views.py 的 share 动作生成、ShareView 免登录校验。
# 表结构约定：全部物理表由 docs/scene3d_init.sql 手工创建，managed=False 不参与 migrate；
#             继承 BaseModel 的表带 create_by/create_time/update_by/update_time/is_deleted 审计列，
#             未继承 BaseModel 的表只映射建表 SQL 中真实存在的字段，避免 ORM 访问不存在的列。
"""3D 可视化模块模型（13 张表，表结构由 docs/scene3d_init.sql 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 场景分类：场景与模板的一级归类，列表按 sort/id 升序输出；category_code 全表唯一供接口引用
class Scene3dCategory(BaseModel):  # 继承 BaseModel，复用审计字段与逻辑删除
    """场景分类表：机房、档案库房、园区等业务归类。"""
    # 主键与唯一编码：category_code 是稳定标识，改名/改排序不影响已引用它的模板与场景
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    category_name = models.CharField('分类名称', max_length=100)  # 分类显示名称
    category_code = models.CharField('分类编码', max_length=50, unique=True)  # 分类唯一编码
    # 展示与启停：sort 控制下拉顺序，status 控制该分类下能否新建场景（停用分类仍保留历史数据）
    sort = models.IntegerField('排序', default=0)  # 排序号，数值小排前
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta：物理表名固定为 scene3d_category，禁止 migrate 改表；sort 相同再按主键保证列表顺序稳定
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_category'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


# 场景模板：新建场景时把 template_config 复制为初始相机/光照/背景配置，减少重复搭建
class Scene3dTemplate(BaseModel):  # 场景模板，提供新建场景的默认配置
    """场景模板表：新建场景时选择模板快速起步。"""
    # 主键与唯一编码：template_code 供接口按编码取模板，名称仅用于展示
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    template_name = models.CharField('模板名称', max_length=100)  # 模板显示名称
    template_code = models.CharField('模板编码', max_length=50, unique=True)  # 模板唯一编码
    # 归属与默认配置：category_id 可为空（通用模板）；template_config 为 JSON，避免为新参数频繁加列
    category_id = models.BigIntegerField('所属分类ID', blank=True, null=True)  # 关联 scene3d_category.id
    template_config = models.JSONField('模板默认配置', blank=True, null=True)  # 光照、相机、背景等默认配置
    # 展示与启停：thumbnail_file_id 复用文件模块的附件记录，sort/status 控制列表展示与可选性
    thumbnail_file_id = models.BigIntegerField('缩略图附件ID', blank=True, null=True)  # 关联附件管理表
    sort = models.IntegerField('排序', default=0)  # 排序号
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta：物理表名固定为 scene3d_template，不参与迁移，默认按排序号升序
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_template'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


# 场景主表：3D 编辑器的根记录，scene_config 承载相机/光照/背景等全局配置，并保存分享令牌
class Scene3dScene(BaseModel):  # 场景主表，scene_config 同时保存分享令牌
    """3D 场景主表：保存场景名称、分类、状态与全局配置。"""
    # 标识与归属：scene_code 对外唯一稳定；category_id 必填（建表 SQL 非空），template_id 记录来源模板
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_name = models.CharField('场景名称', max_length=100)  # 场景显示名称
    scene_code = models.CharField('场景业务编码', max_length=50, unique=True)  # 场景唯一编码
    category_id = models.BigIntegerField('分类ID')  # 关联 scene3d_category.id
    template_id = models.BigIntegerField('来源模板ID', blank=True, null=True)  # 关联 scene3d_template.id
    # 运行状态：0 草稿不对外分享，1 已发布可分享访问，2 已下线保留数据但不可访问
    scene_status = models.SmallIntegerField('状态', default=0)  # 0 草稿 / 1 已发布 / 2 已下线
    # 展示与全局配置：thumbnail_file_id 为列表缩略图；scene_config 是 JSON，分享令牌 share 亦存于此
    thumbnail_file_id = models.BigIntegerField('缩略图附件ID', blank=True, null=True)  # 场景列表缩略图
    scene_config = models.JSONField('场景全局配置', blank=True, null=True)  # 相机、光照、背景、分享令牌等
    remark = models.CharField('场景描述', max_length=1000, blank=True, null=True)  # 场景备注

    # Meta：物理表名固定为 scene3d_scene，不参与迁移，默认按主键倒序让最新场景在前
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_scene'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新创建在前


# 模型资源：只登记模型文件元信息，二进制由文件模块托管；model_type 决定前端按模型还是贴图加载
class Scene3dModelResource(BaseModel):  # 模型资源，file_id 指向 wf_file 的附件记录
    """模型资源表：登记 glb/gltf 等模型文件的元信息。"""
    # 主键与唯一编码：model_code 供场景对象/接口引用，避免依赖可修改的展示名
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    model_name = models.CharField('模型名称', max_length=100)  # 模型显示名称
    model_code = models.CharField('模型编码', max_length=50, unique=True)  # 模型唯一编码
    model_type = models.CharField('模型类型', max_length=30, default='model')  # model/texture/material/env
    # 文件关联：file_id=0 表示尚未上传（占位），上传成功后写入真实 wf_file.id
    file_id = models.BigIntegerField('附件ID', default=0)  # 关联 wf_file.id，0 表示尚未上传
    # 渲染开销指标：三角面数与文件大小用于列表提示，不做业务强校验
    triangle_count = models.IntegerField('三角面数', default=0)  # 模型三角面数量
    file_size = models.BigIntegerField('文件大小', default=0)  # 文件大小（byte）
    # 展示与启停：缩略图复用附件模块，sort/status 控制资源库列表
    thumbnail_file_id = models.BigIntegerField('缩略图附件ID', blank=True, null=True)  # 模型缩略图
    sort = models.IntegerField('排序', default=0)  # 排序号
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta：物理表名固定为 scene3d_model_resource，不参与迁移，默认按排序号升序
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_model_resource'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


# 场景对象：模型资源在场景中的一次摆放实例；scene_id + object_code 唯一标识，保存/回滚时据此做差量
class Scene3dSceneObject(BaseModel):  # 场景对象，用 object_code 在场景内做幂等标识
    """场景对象表：场景内模型实例的位置、旋转、缩放与标签。"""
    # 归属：scene_id 决定所属场景，resource_id 决定渲染成哪个模型；二者删除后对象需级联清理
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('所属场景ID')  # 关联 scene3d_scene.id
    resource_id = models.BigIntegerField('模型资源ID')  # 关联 scene3d_model_resource.id
    # 命名：object_name 给用户看（如机柜A01），object_code 给程序做幂等匹配（同一场景内唯一）
    object_name = models.CharField('对象名称', max_length=100)  # 如机柜A01
    object_code = models.CharField('对象业务编码', max_length=50)  # 场景内唯一编码
    parent_id = models.BigIntegerField('父对象ID', blank=True, null=True)  # 层级树父节点
    # 三维变换：三组 JSON 直接传给 three.js；缺键时由前端补默认值（位置 0、旋转 0、缩放 1）
    position = models.JSONField('坐标')  # {"x":0,"y":0,"z":0}
    rotation = models.JSONField('旋转')  # {"x":0,"y":0,"z":0}
    scale = models.JSONField('缩放')  # {"x":1,"y":1,"z":1}
    # 标签与层级排序：label_text 为漂浮标签内容，is_show_label 控制显隐，sort 控制对象树顺序
    label_text = models.CharField('标签文字', max_length=200, blank=True, null=True)  # 漂浮标签
    is_show_label = models.SmallIntegerField('显示标签', default=1)  # 1 显示 / 0 隐藏
    sort = models.IntegerField('层级排序', default=0)  # 对象树排序
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta：物理表名固定为 scene3d_scene_object，不参与迁移，默认按 sort/id 升序还原对象树顺序
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_scene_object'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


# 数据绑定：把一个场景对象的可变量（颜色/数值/状态）接到业务数据源，按 refresh_interval 轮询
class Scene3dDataBind(BaseModel):  # 数据绑定，source_config 仅允许引用白名单表
    """数据绑定表：场景对象与业务数据/接口/实时通道的绑定配置。"""
    # 归属：scene_id 便于按场景批量拉取绑定，object_id 指向被驱动的场景对象
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    object_id = models.BigIntegerField('场景对象ID')  # 关联 scene3d_scene_object.id
    bind_name = models.CharField('绑定名称', max_length=100)  # 绑定显示名称
    # 数据源：db 查白名单表、api 调接口、ws 走推送；source_config 里存表名/字段或接口地址
    data_source_type = models.CharField('数据源类型', max_length=20, default='db')  # db/api/ws
    source_config = models.JSONField('数据源配置')  # 表名、字段、接口地址等
    refresh_interval = models.IntegerField('刷新间隔', default=30)  # 秒；ws 时为 0
    # 映射规则：把读数区间映射为颜色/状态/动画，前端直接按 rule 渲染，避免在前端硬编码阈值
    mapping_rule = models.JSONField('数值映射规则')  # 区间、颜色、状态、动画
    # 启停与备注：停用后不再轮询，但仍保留配置便于恢复
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta：物理表名固定为 scene3d_data_bind，不参与迁移，默认最新绑定在前
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_data_bind'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认最新绑定在前


# 告警规则：对绑定读数做阈值判定，命中后按 alarm_effect 渲染并联动通知/审批
class Scene3dAlarmRule(BaseModel):  # 告警规则，挂在 binding 上做阈值判定
    """告警规则表：基于数据绑定的阈值规则与视觉表现配置。"""
    # 归属：bind_id 必填，规则随绑定生效；规则删除/停用后不再产生新记录
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    bind_id = models.BigIntegerField('绑定配置ID')  # 关联 scene3d_data_bind.id
    rule_name = models.CharField('规则名称', max_length=100)  # 规则显示名称
    # 阈值：比较符 + 阈值字符串；between 用 "28,32" 表示区间，字符串保存避免浮点精度问题
    compare_operator = models.CharField('比较符', max_length=20, default='>=')  # > >= < <= = between
    threshold_value = models.CharField('阈值', max_length=100)  # 单值或区间，如 "28" / "28,32"
    alarm_level = models.SmallIntegerField('告警级别', default=1)  # 1 提示 / 2 警告 / 3 严重
    # 视觉表现：blink/glow/color/icon 等由前端读取，规则不关心具体渲染实现
    alarm_effect = models.JSONField('视觉表现')  # 闪烁、光晕、颜色、图标
    # 联动动作：自动推送消息、自动发起审批；workflow_def_id 指向工作流模型定义
    is_auto_notice = models.SmallIntegerField('自动推送消息', default=1)  # 1 是 / 0 否
    is_auto_workflow = models.SmallIntegerField('自动发起审批', default=0)  # 1 是 / 0 否
    workflow_def_id = models.BigIntegerField('关联流程定义ID', blank=True, null=True)  # 工作流定义
    # 启停与备注：停用规则保留历史记录，便于回溯当时配置
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta：物理表名固定为 scene3d_alarm_rule，不参与迁移，默认最新规则在前
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_alarm_rule'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认最新规则在前


# 告警记录：规则命中后的历史快照，确认/闭环由运维推进，状态只增不改
class Scene3dAlarmRecord(models.Model):  # 仅继承 models.Model，表的审计字段由手工 SQL 固定
    """告警记录表（不继承 BaseModel）：本表仅有 create_time/update_time/is_deleted。"""
    # 触发快照：scene_id/object_id/rule_id 冗余保存，规则或对象删除后仍能定位当时命中的位置
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    object_id = models.BigIntegerField('对象ID')  # 关联 scene3d_scene_object.id
    rule_id = models.BigIntegerField('告警规则ID')  # 关联 scene3d_alarm_rule.id
    alarm_value = models.CharField('触发值', max_length=100)  # 触发时采集数值
    alarm_level = models.SmallIntegerField('告警级别', default=1)  # 1/2/3
    # 处置状态：0 未确认 → 1 已确认 → 2 已闭环，3 为忽略；确认人/时间与闭环时间留痕
    alarm_status = models.SmallIntegerField('告警状态', default=0)  # 0 未确认 / 1 已确认 / 2 已闭环 / 3 已忽略
    confirm_user_id = models.BigIntegerField('确认人ID', blank=True, null=True)  # 确认操作人
    confirm_time = models.DateTimeField('确认时间', blank=True, null=True)  # 确认时刻
    close_time = models.DateTimeField('闭环时间', blank=True, null=True)  # 闭环时刻
    # 外部联动：工单模块与工作流模块的关联 id，便于从告警跳转到处置单据
    work_order_id = models.BigIntegerField('关联工单ID', blank=True, null=True)  # 工单模块
    workflow_instance_id = models.BigIntegerField('关联审批实例ID', blank=True, null=True)  # 工作流模块
    remark = models.CharField('处置备注', max_length=1000, blank=True, null=True)  # 处置说明
    # 审计列：本表未继承 BaseModel，仅映射建表 SQL 真实存在的三列；create_time 语义为告警发生时间
    create_time = models.DateTimeField('告警发生时间', blank=True, null=True)  # 同 create_time
    update_time = models.DateTimeField('更新时间', blank=True, null=True)  # 最近修改时间
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记

    # Meta：物理表名固定为 scene3d_alarm_record，不参与迁移，按发生时间倒序展示最新告警
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_alarm_record'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-create_time', '-id']  # 最新告警在前


# 巡检路线：相机漫游路径，way_points 每项含坐标/lookAt/停留时长，供前端播放巡检动画
class Scene3dPatrolRoute(BaseModel):  # 巡检路线，way_points 存相机路径点位数组
    """巡检路线表：路径点位与漫游速度配置。"""
    # 归属与编码：scene_id 限定路线所属场景，route_code 供巡检记录与接口引用
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    route_name = models.CharField('路线名称', max_length=100)  # 路线显示名称
    route_code = models.CharField('路线编码', max_length=50)  # 路线唯一编码
    # 路径数据：JSON 数组而非子表，点位随路线整体保存/播放，避免频繁增删子表记录
    way_points = models.JSONField('路径点位')  # 相机坐标、视角、停留时长
    speed = models.DecimalField('漫游速度', max_digits=10, decimal_places=2, default=1.0)  # 默认速度
    # 播放参数：cycle_flag 控制循环播放，status 控制路线是否可选
    cycle_flag = models.SmallIntegerField('是否循环', default=0)  # 1 是 / 0 否
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta：物理表名固定为 scene3d_patrol_route，不参与迁移，默认最新路线在前
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_patrol_route'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认最新路线在前


# 巡检记录：一次巡检执行的结果；只记录结果，不承担点位播放逻辑
class Scene3dPatrolRecord(models.Model):  # 巡检执行记录，无 create_by/update_by 审计字段
    """巡检执行记录表（不继承 BaseModel）：仅本表实际存在的字段。"""
    # 归属：scene_id/route_id 定位本次执行的场景与路线，patrol_code 为业务单号（对外展示）
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    route_id = models.BigIntegerField('巡检路线ID')  # 关联 scene3d_patrol_route.id
    patrol_code = models.CharField('巡检单号', max_length=50)  # 巡检业务单号
    patrol_user_id = models.BigIntegerField('巡检人ID')  # 执行人
    # 执行窗口与结果：end_time 为空表示仍在进行；patrol_status 描述正常完成或异常终止
    start_time = models.DateTimeField('开始时间')  # 巡检开始
    end_time = models.DateTimeField('结束时间', blank=True, null=True)  # 巡检结束
    patrol_status = models.SmallIntegerField('巡检状态', default=0)  # 0 进行中 / 1 正常完成 / 2 异常终止
    abnormal_count = models.IntegerField('异常数量', default=0)  # 发现异常数
    report_file_id = models.BigIntegerField('报告附件ID', blank=True, null=True)  # 巡检报告
    remark = models.CharField('巡检备注', max_length=1000, blank=True, null=True)  # 备注说明
    # 审计列：本表无 create_by/update_by，操作人由 patrol_user_id 表达，故只映射三列
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 记录创建时间
    update_time = models.DateTimeField('更新时间', blank=True, null=True)  # 最近修改时间
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记

    # Meta：物理表名固定为 scene3d_patrol_record，不参与迁移，按开始时间倒序展示最新巡检
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_patrol_record'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-start_time', '-id']  # 最新巡检在前


# 场景版本：每次保存/发布对场景配置与对象数组做全量快照，支持版本列表与回滚
class Scene3dSceneVersion(models.Model):  # 版本快照，snapshot_config 存配置与对象数组
    """场景版本表（不继承 BaseModel）：每次保存生成一条快照。"""
    # 归属与版本号：scene_id 定位场景，version_no 为可读版本号（v1/v2/v3），非全局唯一
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    version_no = models.CharField('版本号', max_length=30)  # v1/v2/v3
    version_desc = models.CharField('版本描述', max_length=500, blank=True, null=True)  # 版本说明
    # 快照正文：包含 scene_config 与对象数组，体积较大；列表查询时由视图剔除该字段
    snapshot_config = models.JSONField('场景快照配置')  # 全量场景配置
    thumbnail_file_id = models.BigIntegerField('快照缩略图', blank=True, null=True)  # 缩略图附件
    is_publish = models.SmallIntegerField('是否发布版本', default=0)  # 1 是 / 0 否
    # 审计列：本表只有 create_by/create_time/is_deleted，没有 update_* 列，故不使用 BaseModel
    create_by = models.CharField('版本创建人', max_length=64, blank=True, null=True)  # 操作人账号
    create_time = models.DateTimeField('版本生成时间', blank=True, null=True)  # 生成时刻
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记

    # Meta：物理表名固定为 scene3d_scene_version，不参与迁移，按生成时间倒序展示最新版本
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_scene_version'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-create_time', '-id']  # 最新版本在前


# 场景权限：按角色/用户/部门授权访问级别；target_type 决定 target_id 指向哪张系统表
class Scene3dScenePermission(BaseModel):  # 访问授权，target_type 决定目标表的含义
    """场景访问权限表：按角色/用户/部门授权只读、可交互、可编辑。"""
    # 归属：scene_id 指定被授权场景；target_type 与 target_id 组合定位授权对象
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('场景ID')  # 关联 scene3d_scene.id
    target_type = models.CharField('授权对象类型', max_length=20, default='role')  # role/user/dept
    target_id = models.BigIntegerField('授权对象ID')  # 角色/用户/部门主键
    # 权限级别与时效：1 只读 / 2 可交互 / 3 可编辑；expire_time 为空表示永久有效
    permission_type = models.SmallIntegerField('权限类型', default=1)  # 1 只读 / 2 可交互 / 3 可编辑
    expire_time = models.DateTimeField('授权过期时间', blank=True, null=True)  # 为空永久有效

    # Meta：物理表名固定为 scene3d_scene_permission，不参与迁移，默认最新授权在前
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_scene_permission'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认最新授权在前


# 访问日志：场景打开行为留痕，供发布页统计访问量与平均停留时长；分享访问的连接没有登录用户
class Scene3dAccessLog(models.Model):  # 访问日志，分享访问时 user_id 为空
    """场景访问日志表（不继承 BaseModel）。"""
    # 访问主体：user_id 为空即匿名（分享链接免登录），access_ip/access_ua 用于审计与来源分析
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    scene_id = models.BigIntegerField('访问场景ID')  # 关联 scene3d_scene.id
    user_id = models.BigIntegerField('访问用户ID', blank=True, null=True)  # 匿名访问为空
    access_ip = models.CharField('访问IP', max_length=50)  # 客户端 IP
    access_ua = models.CharField('浏览器UA', max_length=1000, blank=True, null=True)  # 浏览器标识
    # 统计维度：access_type 区分登录访问与分享访问，stay_seconds 由前端上报，用于计算平均停留
    access_type = models.CharField('访问方式', max_length=20, default='系统登录')  # 系统登录 / 分享链接
    stay_seconds = models.IntegerField('停留时长', default=0)  # 秒
    access_time = models.DateTimeField('访问时间', blank=True, null=True)  # 访问时刻
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记

    # Meta：物理表名固定为 scene3d_access_log，不参与迁移，按访问时间倒序展示最新访问
    class Meta:  # 表级元数据：物理表名、托管方式与默认排序
        db_table = 'scene3d_access_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-access_time', '-id']  # 最新访问在前
