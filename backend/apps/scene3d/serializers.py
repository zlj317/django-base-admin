# 模块：apps/scene3d/serializers.py —— 3D 可视化模块的 DRF 序列化器
# 用途：13 张 scene3d_ 表各对应一个 ModelSerializer，物理字段原样输出，并追加前端列表需要的展示名称。
# 路由前缀：scene3d（最终 URL 形如 /api/scene3d/list，见 apps/scene3d/urls.py；视图在 apps/scene3d/views.py）。
# 覆盖范围：分类、模板、场景、模型资源、场景对象、数据绑定、告警规则、告警记录、
#           巡检路线、巡检记录、场景版本、场景权限、访问日志，共 13 个序列化器。
# 数据约定：
#   1) 所有 SerializerMethodField 均为 read_only，只影响输出，不参与新增/编辑的参数校验；
#   2) 名称类字段按外键 id 逐条查询，详情页可接受；列表页数据量大时应在视图侧做批量预取优化；
#   3) 关联查询统一带 is_deleted=False，避免展示已被逻辑删除的分类/对象/规则；
#   4) 模型文件地址输出 wf_file.storage_path 相对路径，由前端拼接下载/预览基地址；
#   5) 分享链接为匿名访问，访问日志的 user_id 为空，序列化时用“匿名”兜底文案；
#   6) 场景版本快照 snapshot_config 体积大，列表场景由视图剔除，序列化器本身不裁剪字段。
"""3D 可视化模块序列化器：统一输出物理字段，并补充列表需要的展示名称。"""
from rest_framework import serializers  # DRF 序列化框架

from .models import (  # 引入本模块 13 张表的模型
    Scene3dCategory,  # 场景分类
    Scene3dTemplate,  # 场景模板
    Scene3dScene,  # 场景主表
    Scene3dModelResource,  # 模型资源
    Scene3dSceneObject,  # 场景对象
    Scene3dDataBind,  # 数据绑定
    Scene3dAlarmRule,  # 告警规则
    Scene3dAlarmRecord,  # 告警记录
    Scene3dPatrolRoute,  # 巡检路线
    Scene3dPatrolRecord,  # 巡检记录
    Scene3dSceneVersion,  # 场景版本
    Scene3dScenePermission,  # 场景权限
    Scene3dAccessLog,  # 访问日志
)  # 模型导入结束


# 场景分类：字段与表一一对应，管理与下拉共用同一份输出，不额外拼装展示名
class Scene3dCategorySerializer(serializers.ModelSerializer):  # 直接复用模型字段，仅做增删改查
    """场景分类：管理与列表共用。"""

    # Meta：绑定分类模型，输出全部物理字段（含审计列），由视图决定是否裁剪
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dCategory  # 绑定分类模型
        fields = '__all__'  # 输出全部字段


# 场景模板：列表要显示所属分类名，故额外输出 category_name，避免前端逐条再查分类
class Scene3dTemplateSerializer(serializers.ModelSerializer):  # 追加分类名称展示字段
    """场景模板：补充分类名称，列表无需二次查询。"""

    category_name = serializers.SerializerMethodField(read_only=True)  # 分类名称，只读

    # 分类名为计算字段：category_id 可为空（通用模板），为空时直接输出 None
    def get_category_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """按 category_id 查分类名称，查不到返回 None。"""
        if not obj.category_id:  # 未关联分类时直接返回
            return None
        row = Scene3dCategory.objects.filter(id=obj.category_id, is_deleted=False).first()  # 过滤逻辑删除
        return row.category_name if row else None  # 返回名称或空

    # Meta：输出全部字段，DRF 会把追加的 category_name 一并输出
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dTemplate  # 绑定模板模型
        fields = '__all__'  # 输出全部字段，含追加的 category_name


# 场景主表：列表需要同时展示分类名与模板名，均以只读计算字段补充，不改变写入字段集
class Scene3dSceneSerializer(serializers.ModelSerializer):  # 追加分类/模板名称，列表免二次查询
    """场景主表：补充分类名与模板名，供列表直接展示。"""

    category_name = serializers.SerializerMethodField(read_only=True)  # 分类显示名称
    template_name = serializers.SerializerMethodField(read_only=True)  # 模板显示名称

    # 分类为必填外键，正常情况下都能查到；查不到（被逻辑删除）时输出 None 由前端显示占位符
    def get_category_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询分类名称。"""
        row = Scene3dCategory.objects.filter(id=obj.category_id, is_deleted=False).first()  # 按主键精确查询
        return row.category_name if row else None  # 无匹配返回 None

    # 模板为可空外键：未选模板时直接返回 None，避免一次无意义查询
    def get_template_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询模板名称。"""
        if not obj.template_id:  # 无模板直接返回
            return None  # 模板未设置时输出空值
        row = Scene3dTemplate.objects.filter(id=obj.template_id, is_deleted=False).first()  # 按主键查询
        return row.template_name if row else None  # 返回模板名称

    # Meta：输出全部物理字段并附带两个名称字段
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dScene  # 绑定场景模型
        fields = '__all__'  # 输出全部字段，含两个名称字段


# 模型资源：file_id 只是附件主键，前端需要可用的相对路径，因此增加 file_url 计算字段
class Scene3dModelResourceSerializer(serializers.ModelSerializer):  # 追加模型文件访问地址
    """模型资源：列表提供文件下载/预览地址。"""

    file_url = serializers.SerializerMethodField(read_only=True)  # 模型文件访问地址

    # 附件在文件模块，采用函数内延迟导入避免 apps 间循环依赖；file_id=0 为占位资源
    def get_file_url(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """file_id=0 表示尚未上传真实文件，返回 None。"""
        if not obj.file_id:  # 未上传
            return None  # 无附件时不返回地址，前端显示“未上传”
        from apps.file.models import WfFile  # 延迟导入，避免模块循环依赖
        row = WfFile.objects.filter(id=obj.file_id).first()  # 查询附件表
        return row.storage_path if row else None  # 返回相对存储路径

    # Meta：输出全部字段，含文件地址
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dModelResource  # 绑定模型资源
        fields = '__all__'  # 输出全部字段


# 场景对象：编辑器对象树需要资源名称与类型来决定图标/加载方式，故补充两个只读字段
class Scene3dSceneObjectSerializer(serializers.ModelSerializer):  # 追加资源名称/类型，编辑器展示更直观
    """场景对象：补充模型名称，编辑器展示更直观。"""

    resource_name = serializers.SerializerMethodField(read_only=True)  # 模型资源名称
    resource_type = serializers.SerializerMethodField(read_only=True)  # 模型资源类型

    # 对象一定绑定了资源（数据库非空），被删除的资源返回 None 由前端提示“资源缺失”
    def get_resource_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询模型资源名称。"""
        row = Scene3dModelResource.objects.filter(id=obj.resource_id, is_deleted=False).first()  # 精确查询
        return row.model_name if row else None  # 无资源返回 None

    # 类型用于前端区分模型/贴图/材质/环境，决定加载器
    def get_resource_type(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询模型资源类型（model/texture/env）。"""
        row = Scene3dModelResource.objects.filter(id=obj.resource_id, is_deleted=False).first()  # 精确查询
        return row.model_type if row else None  # 无资源返回 None

    # Meta：输出全部字段，含资源名称与类型
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dSceneObject  # 绑定场景对象
        fields = '__all__'  # 输出全部字段


# 数据绑定：绑定列表只存 object_id，补充 object_name 让运维能直接看出绑在哪个设备上
class Scene3dDataBindSerializer(serializers.ModelSerializer):  # 追加绑定对象的名称
    """数据绑定：补充对象名称，列表可读性更好。"""

    object_name = serializers.SerializerMethodField(read_only=True)  # 绑定的场景对象名称

    # 对象被删除时返回 None，不阻断绑定列表展示
    def get_object_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """按 object_id 查询对象名称。"""
        row = Scene3dSceneObject.objects.filter(id=obj.object_id, is_deleted=False).first()  # 精确查询
        return row.object_name if row else None  # 无对象返回 None

    # Meta：输出全部字段，含对象名称
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dDataBind  # 绑定数据绑定模型
        fields = '__all__'  # 输出全部字段


# 告警规则：规则挂在绑定上，列表需要“绑定名 + 对象名”才能快速判断告警位置
class Scene3dAlarmRuleSerializer(serializers.ModelSerializer):  # 追加绑定/对象名称便于列表阅读
    """告警规则：补充绑定名称与对象名称。"""

    bind_name = serializers.SerializerMethodField(read_only=True)  # 数据绑定名称
    object_name = serializers.SerializerMethodField(read_only=True)  # 场景对象名称

    # 绑定被删除时返回 None
    def get_bind_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询绑定名称。"""
        row = Scene3dDataBind.objects.filter(id=obj.bind_id, is_deleted=False).first()  # 精确查询
        return row.bind_name if row else None  # 无绑定返回 None

    # 规则本身没有 object_id，需先经 bind_id 找到绑定，再取绑定的 object_id 反查对象名
    def get_object_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """通过绑定关系反查对象名称。"""
        row = Scene3dDataBind.objects.filter(id=obj.bind_id, is_deleted=False).first()  # 先找绑定
        if not row:  # 绑定不存在时终止
            return None  # 绑定已删除则无法反查对象
        obj_row = Scene3dSceneObject.objects.filter(id=row.object_id, is_deleted=False).first()  # 再找对象
        return obj_row.object_name if obj_row else None  # 返回对象名称

    # Meta：输出全部字段，含两个名称字段
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dAlarmRule  # 绑定告警规则模型
        fields = '__all__'  # 输出全部字段


# 告警记录：历史记录只保存 id 快照，列表补充场景/对象/规则名称，便于直接阅读与筛选
class Scene3dAlarmRecordSerializer(serializers.ModelSerializer):  # 追加场景/对象/规则名称
    """告警记录：补充场景名与对象名，无需前端再查。"""

    scene_name = serializers.SerializerMethodField(read_only=True)  # 场景名称
    object_name = serializers.SerializerMethodField(read_only=True)  # 对象名称
    rule_name = serializers.SerializerMethodField(read_only=True)  # 规则名称

    # 场景被删除时返回 None，告警记录仍保留原始 id 供追溯
    def get_scene_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询场景名称。"""
        row = Scene3dScene.objects.filter(id=obj.scene_id, is_deleted=False).first()  # 精确查询
        return row.scene_name if row else None  # 无场景返回 None

    # 对象名用于定位“哪台设备”报警
    def get_object_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询对象名称。"""
        row = Scene3dSceneObject.objects.filter(id=obj.object_id, is_deleted=False).first()  # 精确查询
        return row.object_name if row else None  # 无对象返回 None

    # 规则名说明“为什么报警”，规则被删除时返回 None
    def get_rule_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询规则名称。"""
        row = Scene3dAlarmRule.objects.filter(id=obj.rule_id, is_deleted=False).first()  # 精确查询
        return row.rule_name if row else None  # 无规则返回 None

    # Meta：输出全部字段，含三个名称字段
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dAlarmRecord  # 绑定告警记录
        fields = '__all__'  # 输出全部字段


# 巡检路线：列表展示场景名与点位数量，点位数量由 way_points 数组长度实时计算
class Scene3dPatrolRouteSerializer(serializers.ModelSerializer):  # 追加场景名称与点位数量
    """巡检路线：补充场景名称与点位数量。"""

    scene_name = serializers.SerializerMethodField(read_only=True)  # 场景名称
    point_count = serializers.SerializerMethodField(read_only=True)  # 点位数量

    # 场景名用于路线列表归类
    def get_scene_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询场景名称。"""
        row = Scene3dScene.objects.filter(id=obj.scene_id, is_deleted=False).first()  # 精确查询
        return row.scene_name if row else None  # 无场景返回 None

    # 历史数据可能存成字符串而非数组，故用 isinstance 防御，避免 len() 抛 TypeError
    def get_point_count(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """统计 way_points 数组长度，异常结构返回 0。"""
        return len(obj.way_points) if isinstance(obj.way_points, list) else 0  # 只接受数组

    # Meta：输出全部字段，含场景名与点位数量
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dPatrolRoute  # 绑定巡检路线
        fields = '__all__'  # 输出全部字段


# 巡检记录：记录列表需要展示场景与路线名称，避免前端分别查两张配置表
class Scene3dPatrolRecordSerializer(serializers.ModelSerializer):  # 追加场景/路线名称
    """巡检记录：补充场景名称与路线名称。"""

    scene_name = serializers.SerializerMethodField(read_only=True)  # 场景名称
    route_name = serializers.SerializerMethodField(read_only=True)  # 路线名称

    # 场景名与记录一一对应，删除后返回 None
    def get_scene_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询场景名称。"""
        row = Scene3dScene.objects.filter(id=obj.scene_id, is_deleted=False).first()  # 精确查询
        return row.scene_name if row else None  # 无场景返回 None

    # 路线名说明本次巡检按哪条路线执行
    def get_route_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """查询路线名称。"""
        row = Scene3dPatrolRoute.objects.filter(id=obj.route_id, is_deleted=False).first()  # 精确查询
        return row.route_name if row else None  # 无路线返回 None

    # Meta：输出全部字段，含场景名与路线名
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dPatrolRecord  # 绑定巡检记录
        fields = '__all__'  # 输出全部字段


# 场景版本：不追加计算字段，snapshot_config 体积大，列表场景由视图剔除该键
class Scene3dSceneVersionSerializer(serializers.ModelSerializer):  # 快照正文体积大，列表由视图剔除
    """场景版本：快照可能较大，列表场景下由视图剔除。"""

    # Meta：输出全部字段；详情/回滚接口才需要 snapshot_config 全量内容
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dSceneVersion  # 绑定版本模型
        fields = '__all__'  # 输出全部字段


# 场景权限：target_id 本身不可读，需按 target_type 到对应系统表换出角色/用户/部门名称
class Scene3dScenePermissionSerializer(serializers.ModelSerializer):  # 追加授权对象显示名称
    """场景权限：补充授权对象显示名称。"""

    target_name = serializers.SerializerMethodField(read_only=True)  # 角色/用户/部门名称

    # 三类授权对象分散在不同表，用映射表避免 if/elif；系统模型延迟导入防止循环依赖
    def get_target_name(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """按 target_type 分别查询角色、用户、部门名称。"""
        from apps.system.models import SysRole, SysUser, SysDept  # 延迟导入避免循环依赖
        mapping = {'role': (SysRole, 'role_name'), 'user': (SysUser, 'username'), 'dept': (SysDept, 'dept_name')}  # 类型映射
        conf = mapping.get(obj.target_type)  # 取对应模型与名称字段
        if not conf:  # 未知类型直接返回
            return None  # 类型不在枚举内，不做查询
        model, field = conf  # 解包模型与字段
        row = model.objects.filter(id=obj.target_id).first()  # 按主键查询
        return getattr(row, field, None) if row else None  # 返回名称

    # Meta：输出全部字段，含授权对象显示名
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dScenePermission  # 绑定权限模型
        fields = '__all__'  # 输出全部字段


# 访问日志：分享链接为匿名访问，user_id 为空时输出“匿名”，用户被删时输出“已删除用户”
class Scene3dAccessLogSerializer(serializers.ModelSerializer):  # 追加访问者账号，匿名有兜底文案
    """访问日志：补充用户名，匿名访问显示“匿名”。"""

    username = serializers.SerializerMethodField(read_only=True)  # 访问者账号

    # 两种空值语义不同：user_id 为空是匿名访问，查不到用户是账号已删除，故分别兜底
    def get_username(self, obj):  # SerializerMethodField 回调入口，obj 为当前记录
        """user_id 为空时返回“匿名”。"""
        if not obj.user_id:  # 匿名访问
            return '匿名'  # 分享链接访问没有登录用户
        from apps.system.models import SysUser  # 延迟导入
        row = SysUser.objects.filter(id=obj.user_id).first()  # 查询用户
        return row.username if row else '已删除用户'  # 用户已删时给出兜底文案

    # Meta：输出全部字段，含访问者账号
    class Meta:  # 序列化元数据：绑定模型与输出字段
        model = Scene3dAccessLog  # 绑定访问日志
        fields = '__all__'  # 输出全部字段
