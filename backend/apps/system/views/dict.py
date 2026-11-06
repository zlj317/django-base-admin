"""数据字典：字典类型 + 字典项。"""
# 模块用途：维护字典类型及其字典项，并提供前端缓存用的全量启用字典接口。
# 对应路由前缀：/api/system/dict/type/ 与 /api/system/dict/data/（data 额外有 /all）。
# 权限要求：基类按 perm_prefix='system:dict' 生成权限点；all 为登录后可用的公共查询。
# 关键约定：删除类型时级联逻辑删除其字典项；前端按 dict_type 编码分组缓存，编码唯一。
from apps.system.models import SysDictData, SysDictType  # 字典项与字典类型模型
from apps.system.serializers import DictDataSerializer, DictTypeSerializer  # 两个序列化器
from common.auth import LoginRequired  # 登录校验（树/全量接口备用）
from common.response import ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类


class DictTypeViewSet(CrudViewSet):
    """字典类型管理视图：删除类型时级联删除其字典项。"""
    # 基础配置交给通用基类，唯一需要覆盖的是删除动作（要级联处理字典项）。
    model = SysDictType  # 目标模型
    serializer_class = DictTypeSerializer  # 序列化器
    perm_prefix = 'system:dict'  # 权限标识前缀
    module_name = '字典管理'  # 操作日志模块名
    # 类型名称与类型编码都支持模糊搜索，方便按业务含义或编码定位。
    filter_map = {'dict_name': 'icontains', 'dict_type': 'icontains'}  # 列表筛选字段

    # 覆盖基类 delete：类型被删除后其字典项必须一并失效，否则会留下孤儿数据。
    def delete(self, request):
        """删除字典类型时同步删除其字典项。"""
        from rest_framework.decorators import action  # noqa 函数内延迟导入，避免循环依赖
        # 前端表格批量删除提交 {"ids": [...]}，缺省按空列表处理。
        ids = request.data.get('ids') or []  # 待删除类型ID
        # 空集合直接返回提示，避免执行无意义的批量 UPDATE。
        if not ids:  # 未勾选任何类型时直接提示，避免空集合批量更新
            return ok(None, '请选择要删除的数据')  # 未选择数据
        # 先逻辑删除类型本身；get_queryset 已保证只处理未删除记录。
        self.get_queryset().filter(id__in=ids).update(is_deleted=1)  # 逻辑删除类型
        # 再级联逻辑删除字典项，dict_type_id 指向类型主键，用一条 UPDATE 完成。
        SysDictData.objects.filter(dict_type_id__in=ids).update(is_deleted=1)  # 级联删除字典项
        # 与基类删除保持同样的返回结构，前端无需区分调用路径。
        return ok(None, '删除成功')  # 返回成功


class DictDataViewSet(CrudViewSet):
    """字典项管理视图：支持按类型编码查询与全量启用字典输出。"""
    # 字典项与字典类型共用 system:dict 权限前缀，避免两套权限点造成配置负担。
    model = SysDictData  # 目标模型
    serializer_class = DictDataSerializer  # 序列化器
    perm_prefix = 'system:dict'  # 权限标识前缀
    module_name = '字典管理'  # 操作日志模块名
    # 支持按类型主键精确定位，以及按启用状态筛选。
    filter_map = {'dict_type_id': 'exact', 'status': 'exact'}  # 列表筛选字段

    # 重写查询集：除基类的逻辑删除过滤外，额外支持用“类型编码”而不是主键筛选。
    def get_queryset(self):
        """支持按 dict_type 编码（而非ID）过滤字典项。"""
        # 复用基类逻辑，保证 is_deleted=0 的过滤不会漏掉。
        qs = super().get_queryset()  # 基类已过滤逻辑删除
        # 前端下拉通常持有类型编码（如 sys_user_sex），而不是数据库主键。
        dict_type = self.request.query_params.get('dict_type')  # 类型编码参数
        # 未传编码时保持全量查询，兼容列表页按其它字段筛选的场景。
        if dict_type:  # 仅在传入类型编码时换算主键，否则保持全量查询
            type_id = SysDictType.objects.filter(dict_type=dict_type, is_deleted=0) \
                .values_list('id', flat=True).first()  # 编码换算为主键
            # 编码查不到对应类型时返回空集，而不是退化成全量，避免前端误展示。
            qs = qs.filter(dict_type_id=type_id) if type_id else qs.none()  # 无匹配则空集
        # 返回链式查询集，分页/序列化由基类继续处理。
        return qs  # 返回过滤后的查询集

    # 公共接口：一次性返回所有启用字典，前端启动时缓存，减少后续请求。
    def all(self, request):
        """全部启用字典（前端缓存做翻译与下拉）。"""
        # 只取启用的类型；status=0 表示启用，is_deleted=0 排除逻辑删除。
        types = SysDictType.objects.filter(is_deleted=0, status=0)  # 启用的字典类型
        # 结果按类型分组，结构为 [{dict_type, list:[{dict_label, dict_value}]}]。
        data = []  # 汇总各字典类型的结果，保持前端按类型分组的缓存结构
        # 逐类型查询启用项；类型数量有限，N 次小查询可接受且逻辑清晰。
        for t in types:  # 逐类型查询启用字典项
            # 只取未删除且启用的字典项（status=0 为启用）。
            items = SysDictData.objects.filter(dict_type_id=t.id, is_deleted=0, status=0)  # 启用项
            # 类型编码作为分组键；每项只输出标签与值，减少传输体积。
            data.append({'dict_type': t.dict_type,  # 类型编码作为键
                         'list': [{'dict_label': i.dict_label, 'dict_value': i.dict_value}  # 每项只输出标签与键值
                                  for i in items]})  # 标签与键值列表
        # 统一响应结构，前端可直接以 data 覆盖本地字典缓存。
        return ok(data)  # 返回全部字典
