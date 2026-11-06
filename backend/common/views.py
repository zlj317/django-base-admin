"""通用 CRUD 视图基类：统一分页/筛选/增删改 + 权限校验。"""
# 模块用途：把各业务模块高度相似的“列表/新增/修改/删除/启停”接口收敛到一个 ViewSet 基类。
# 被谁调用：apps/*/views.py 中多数 ViewSet 继承 CrudViewSet，并通过类属性声明模型与序列化器。
# 关键约定：查询统一过滤 is_deleted=0；时间字段由后端生成字符串（与手工建表 SQL 的 DATETIME 对齐）；
#           权限由 PermissionCheck + perm_map 控制；响应统一为 {code, msg, data}（见 common/response.py）。
import time  # 生成创建/更新时间字符串，与手工 SQL 的 datetime 字段对齐

from rest_framework import viewsets  # 提供 ViewSet 基类与 action 语义

from common.pagination import StandardPagination  # 统一分页输出
from common.permissions import PermissionCheck  # 登录 + 权限标识校验
from common.response import fail, ok  # 统一成功/失败响应


# 继承 DRF 的 ViewSet 而非 GenericViewSet：路由与 action 映射在 urls.py 中显式声明，不走 router。
class CrudViewSet(viewsets.ViewSet):
    # docstring 列出子类需要覆盖的类属性，是接入本基类的唯一约定说明。
    """通用 CRUD。

    子类配置：
      model:            模型类
      serializer_class: 序列化器
      perm_prefix:      权限前缀，如 'system:user'
      filter_map:       {查询参数: lookup}，如 {'username': 'icontains', 'status': 'exact'}
      order_by:         排序字段，默认 'id'（编号升序）
      module_name:      操作日志模块名
    """

    # 类属性即配置项：子类继承后按需覆盖，基类方法统一读取 self.xxx，避免每个接口重复传参。
    model = None  # 子类必须指定模型类
    serializer_class = None  # 子类必须指定序列化器
    # 权限前缀决定各 action 的权限标识，例如 'system:user' 会生成 system:user:list 等。
    perm_prefix = ''  # 权限前缀，如 system:user，用于拼出各 action 的权限标识
    # filter_map 为空表示不支持筛选；键是查询参数名（同时也是模型字段名），值是 ORM lookup。
    filter_map = {}  # 查询参数到 ORM lookup 的映射，声明后即可支持筛选
    order_by = 'id'  # 默认按编号升序，保证分页结果稳定
    # module_name 供子类写操作日志时使用（本基类不直接读取），保持向后兼容。
    module_name = ''  # 操作日志模块名，子类可覆盖为中文名

    # DRF 会读取 permission_classes 决定权限类；用 property 可保证每次请求都基于子类属性现算。
    @property
    def permission_classes(self):
        # 返回权限类列表而非实例，DRF 会自行实例化并调用 has_permission。
        """按 perm_prefix 动态生成 perm_map，并固定使用 PermissionCheck。"""
        # property 让 DRF 在每次请求实例化视图后读取，从而能基于子类属性动态生成映射。
        prefix = self.perm_prefix  # 取子类配置的权限前缀
        # 这里只覆盖 4 个标准 action；子类的自定义动作（如 upload/export）需自行扩展 perm_map，
        # 否则 PermissionCheck 遇到未配置的 action 会直接放行（见 common/permissions.py）。
        self.perm_map = {
            'list': f'{prefix}:list',  # 列表查询权限
            'create': f'{prefix}:create',  # 新增权限
            'update': f'{prefix}:update',  # 编辑权限
            'delete': f'{prefix}:delete',  # 删除权限
        }
        return [PermissionCheck]  # 只挂自定义权限类，登录校验已在其内部完成

    # 所有读写动作都从这里取数据，逻辑删除过滤只需维护这一处，避免某个接口漏过滤。
    def get_queryset(self):
        # 返回 QuerySet 而非 list，便于调用方继续 filter/update，且延迟执行可减少查询次数。
        """返回过滤逻辑删除后的基础查询集，供各类操作复用。"""
        # is_deleted 用 0 而非 False 比较，因为手工建表 SQL 里该列是 tinyint；数据库两种值都能匹配。
        return self.model.objects.filter(is_deleted=0).order_by(self.order_by)  # 逻辑删除条件在此统一收敛

    # 与 DRF 的同名钩子保持一致，子类若需按 action 区分序列化器可直接覆盖本方法。
    def get_serializer_class(self):
        # 只返回类本身，不实例化；是否绑定 data 由调用方决定。
        """序列化器统一取类属性，子类只需声明一次。"""
        # 保留该方法是为了将来支持按 action 切换读写序列化器（例如列表用精简版）。
        return self.serializer_class  # 基类不做动态选择

    # 筛选逻辑集中在这里，子类只需声明 filter_map，无需重写 list。
    def apply_filters(self, queryset, request):
        # 只拼接白名单中的参数与 lookup，用户无法控制字段名，因此不存在注入风险。
        """按 filter_map 把非空查询参数拼成 ORM 过滤条件。"""
        # 逐个参数拼接；lookup 由子类显式声明，不存在用户可控的字段名注入风险。
        for param, lookup in self.filter_map.items():
            value = request.query_params.get(param)  # 取前端传入的筛选值
            # 空串与 None 视为“未筛选”，避免空条件把结果集过滤成空。
            if value not in (None, ''):
                queryset = queryset.filter(**{f'{param}__{lookup}': value})  # 动态拼接 ORM lookup
        return queryset  # 返回链式过滤后的查询集

    # 列表接口返回统一分页结构 {code, msg, data}，前端表格组件可直接复用。
    def list(self, request):
        # 过滤后的 QuerySet 交给分页器，由它负责 count、切片与序列化。
        """列表接口：筛选 + 分页 + 序列化。"""
        # 先过滤后分页：total 必须反映筛选后的条数，否则前端页码会算错。
        queryset = self.apply_filters(self.get_queryset(), request)  # 先过滤再分页，保证 total 准确
        # 传入 get_serializer_class() 的结果（类本身），分页器内部会实例化并序列化当前页。
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())  # 输出统一分页结构

    # 新增流程：唯一性预检 → 序列化校验 → 补审计字段 → 落库 → 回写完整对象。
    def create(self, request):
        # 唯一性预检能给出比数据库 IntegrityError 更友好的提示文案。
        """新增接口：校验入参后补审计字段并回写完整对象。"""
        # 逻辑删除记录仍占用数据库唯一索引，新增前先给出明确提示，避免直接落库时报 500
        # 遍历模型字段：只关心 unique 且非主键的业务字段（如用户名、部门编码）。
        for field in self.model._meta.fields:
            # primary_key 的唯一性由数据库负责；没有 is_deleted 列的日志表跳过整套检查。
            if not field.unique or field.primary_key or not hasattr(self.model, 'is_deleted'):
                continue  # 只校验业务唯一字段
            value = request.data.get(field.attname)  # 取提交的唯一字段值
            # 未提交的值交给序列化器处理 required 校验，这里不重复报错。
            if value in (None, ''):
                continue  # 未提交则交给序列化器处理
            # 这里的查询刻意不带逻辑删除过滤，目的是同时识别“被已删除记录占用”的情况。
            qs = self.model.objects.filter(**{field.attname: value})  # 含已删除记录
            if qs.filter(is_deleted=0).exists():  # 未删除记录已占用
                return fail(f'{field.verbose_name}已存在', code=400)  # 明确提示
            # 只剩已删除记录占用时，数据库唯一索引仍会拒绝插入，因此提前给出可操作提示。
            if qs.exists():  # 仅被已删除记录占用（数据库唯一键冲突）
                return fail(f'{field.verbose_name}已被已删除记录占用，请更换{field.verbose_name}', code=400)  # 明确提示
        serializer = self.get_serializer_class()(data=request.data)  # 绑定请求体做字段校验

        serializer.is_valid(raise_exception=True)  # 校验失败交给全局异常处理器转 400
        # 手工建表 SQL 的 DATETIME 列不做时区转换，因此这里直接写入本地时间字符串。
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一时间格式，与手写 SQL 的写入方式保持一致
        # user_info 由认证中间件/认证类挂到 request 上，正常流程不会在这里为空。
        user = getattr(request, 'user_info', None)  # 当前登录用户，用于审计字段
        audit = {}  # 仅对继承 BaseModel 的模型补审计字段，日志类模型无这些列
        # 用 hasattr 判断模型是否继承 BaseModel，避免向无此列的模型 save 时抛 TypeError。
        if hasattr(self.model, 'create_by'):
            # 用 dict 一次性构造，save(**audit) 等价于显式传这些关键字参数。
            audit = dict(
                create_by=user.username if user else '',  # 未登录时留空（正常流程不会出现）
                create_time=now,  # 创建时间
                update_by=user.username if user else '',  # 初始更新人与创建人一致
                update_time=now,  # 初始更新时间
            )
        # save 返回已落库实例（含雪花主键），后续序列化才能拿到 id 等由后端生成的值。
        instance = serializer.save(**audit)  # 落库并返回带雪花主键的实例，供下一步回写完整数据
        self.after_create(request, instance)  # 子类可在此做关联数据写入
        # 重新序列化已落库实例：确保输出包含默认值与数据库回填后的完整数据。
        return ok(self.get_serializer_class()(instance).data, '新增成功')  # 返回落库后的完整数据

    # 编辑流程：定位未删除记录 → 部分校验 → 强制覆盖审计字段 → 保存 → 返回最新对象。
    def update(self, request, pk=None):
        # pk 由路由的 <int:pk> 传入，ORM 会自动按主键类型转换后匹配。
        """编辑接口：部分更新，并记录更新人与更新时间。"""
        # 从 get_queryset 取，天然排除已逻辑删除的记录，防止通过接口“复活”数据。
        instance = self.get_queryset().filter(pk=pk).first()  # 只在未删除的数据中查找
        if not instance:
            return self._not_found()  # 不存在时返回业务码 404
        # partial=True 允许前端只提交变更字段；未提交字段保持数据库原值。
        serializer = self.serializer_class(instance, data=request.data, partial=True)  # partial 允许只传变更字段
        serializer.is_valid(raise_exception=True)  # 校验失败统一转 400
        user = getattr(request, 'user_info', None)  # 操作人，用于审计字段
        audit = {}  # 日志类模型没有审计列，跳过即可
        # 审计字段由后端强制覆盖，避免前端伪造 create_by/update_by 修改操作人记录。
        if hasattr(self.model, 'update_by'):
            # 编辑时只覆盖 update_*，create_* 保持新增时的原始值。
            audit = dict(
                update_by=user.username if user else '',  # 更新人账号
                update_time=time.strftime('%Y-%m-%d %H:%M:%S'),  # 更新时刻
            )
        serializer.save(**audit)  # 只提交本次变更字段，审计字段由后端强制覆盖
        self.after_update(request, instance)  # 子类钩子，如同步更新关联表
        return ok(self.serializer_class(instance).data, '修改成功')  # 返回最新对象

    # 批量删除由请求体携带 ids（避免 URL 过长），接口本身不回传数据。
    def delete(self, request):
        # 业务表做逻辑删除以保留审计与回收能力，只有日志类表才物理删除。
        """批量删除接口：按 ids 做逻辑删除。"""
        # 前端表格批量删除通常提交 {"ids": [...]}；`or []` 兼容未传或传 null 的情况。
        ids = request.data.get('ids') or []  # 兼容未传或传 null 的情况
        if not ids:
            # 注意：这里用的是 ok 而非 fail，业务码仍为 200，仅靠 msg 提示用户。
            return ok(None, '请选择要删除的数据')  # 未选数据时给出提示而不是报错
        user = getattr(request, 'user_info', None)  # 操作人，用于记录删除者
        # id__in 只查一次数据库，避免逐个 get；get_queryset 保证不会重复处理已删除数据。
        queryset = self.get_queryset().filter(id__in=ids)  # 先定位本次要删除的记录
        if hasattr(self.model, 'is_deleted'):
            # update() 只发一条 UPDATE 语句，不触发模型 save/信号，批量删除性能更好。
            queryset.update(
                is_deleted=1, update_by=user.username if user else '')  # 业务表统一逻辑删除，数据保留可追溯
        else:
            # 日志类表没有 is_deleted 列，按业务约定直接物理删除。
            queryset.delete()  # 日志类模型无逻辑删除列，直接物理删除
        return ok(None, '删除成功')  # 无需回传数据

    # ---- 钩子 ----
    # 下面依次是自定义动作与扩展点：status 由子类路由通过 as_view({'post': 'status'}) 暴露。
    # 状态切换是高频操作，单独成 action，避免前端传全量对象触发完整字段校验。
    def status(self, request, pk=None):
        # 只改动状态字段，其余字段保持原值。
        """启用/停用：按请求体的 status 或 enabled 字段更新指定记录。"""
        instance = self.get_queryset().filter(pk=pk).first()  # 只在未删除数据中查找
        if not instance:
            return self._not_found()  # 不存在时返回业务码 404
        data = request.data or {}  # 兼容空请求体，避免下面的 in 判断报错
        # 不同模块的状态列命名不一致（status/enabled），这里同时支持两种写法。
        fields = [f for f in ('status', 'enabled') if f in data]  # 兼容两种状态字段名
        if not fields:
            return fail('未提供状态字段', code=400)  # 参数缺失给出明确提示
        # setattr 动态赋值，避免为两种字段名写两套分支。
        for field in fields:
            setattr(instance, field, data[field])  # 逐个赋值，兼容 status/enabled
        user = getattr(request, 'user_info', None)
        # 只在模型确实有审计列时才写，防止日志类模型 save 时报错。
        if hasattr(instance, 'update_by'):
            # 有审计列时记录操作人；空串表示系统/匿名操作。
            instance.update_by = user.username if user else ''
        if hasattr(instance, 'update_time'):
            # 与新增保持同一时间格式，避免前端解析差异。
            instance.update_time = time.strftime('%Y-%m-%d %H:%M:%S')
        # 走模型 save（而非 queryset.update），以便子类重写的 save 逻辑/信号生效。
        instance.save()  # 只保存本次改动
        return ok(self.serializer_class(instance).data, '状态更新成功')

    # 钩子默认空实现，供子类覆盖（例如同时写关联表、刷新缓存）。
    def after_create(self, request, instance):
        # 有意留空：不引入额外副作用，子类不覆盖也不会报错。
        """新增后的扩展点，默认不做任何事。"""
        pass  # 子类按需覆盖

    # 编辑后钩子：用于同步关联数据或清理缓存，与 after_create 对称。
    def after_update(self, request, instance):
        # 有意留空：保证基类行为最小化，子类按需覆盖。
        """编辑后的扩展点，默认不做任何事。"""
        pass  # 子类按需覆盖

    # 静态方法：不依赖 self，可在任意视图/工具函数中直接调用。
    @staticmethod
    # 统一 404 文案，避免各子类各写一份导致前端提示不一致。
    def _not_found():
        # 返回 Response 对象，视图层直接 return 即可。
        """构造 404 业务响应，供按主键查询失败时复用。"""
        # 方法内导入：只有错误分支才需要 fail，同时避免影响模块顶部的导入顺序。
        from common.response import fail  # 局部导入，避免与模块顶部导入产生冗余
        return fail('记录不存在', code=404)  # 业务码 404，HTTP 状态仍为 200
