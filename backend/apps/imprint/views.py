"""导入模板 + 打印模板模块视图集。"""
# 模块：apps/imprint/views.py —— 三个模板相关资源的 CRUD 视图集。
# 用途：为“导入模板管理”“导入模板列”“打印模板管理”页面提供 list/create/update/delete/status 接口。
# 对应表：imp_template、imp_template_column、print_template。
# 路由前缀：/api/imprint/，由 urls.py 的 crud() 工厂分别挂到 template、column、print 下。
# 幂等性：读接口天然幂等；写接口由 CrudViewSet 做逻辑删除与唯一性预检，status 只改状态字段。
from common.views import CrudViewSet

# 本模块三张表对应的模型
from apps.imprint.models import ImpTemplate, ImpTemplateColumn, PrintTemplate
# 三个序列化器：基类用它们做入参校验与结果输出（导入顺序沿用原文件）
from apps.imprint.serializers import (ImpTemplateColumnSerializer, ImpTemplateSerializer,
                                      PrintTemplateSerializer)


# 导入模板视图集：继承基类即自动获得 list/create/update/delete/status 五个动作。
class ImpTemplateViewSet(CrudViewSet):
    """导入模板表 CRUD。"""
    # 基类据此构造查询集、遍历唯一字段做新增预检
    model = ImpTemplate
    # 基类用它做入参校验与结果输出
    serializer_class = ImpTemplateSerializer
    # 权限前缀：拼出 imprint:list/create/update/delete，与 seed.py 中的按钮权限一致
    perm_prefix = 'imprint'
    filter_map = {
        # 模板名称模糊搜索，符合页面“按名称查”的习惯
        'template_name': 'icontains',
        # 模板编码模糊搜索，便于按编码前缀定位
        'template_key': 'icontains',
        # 启停状态精确匹配，前端下拉只有启用/停用两个值
        'status': 'exact',
    }
    # 主键倒序：新建的模板排在最前，符合列表默认预期
    order_by = '-id'
    # 操作日志中展示的模块中文名
    module_name = '导入模板管理'


# 导入模板列视图集：管理某个导入模板下的列级规则（必填、类型、长度、正则、枚举等）。
class ImpTemplateColumnViewSet(CrudViewSet):
    """导入模板列定义表 CRUD（无 BaseModel）。"""
    # 列定义模型，无审计字段、仅 is_deleted
    model = ImpTemplateColumn
    # 列定义序列化器
    serializer_class = ImpTemplateColumnSerializer
    # 与导入模板共用 imprint 权限前缀，页面级权限统一
    perm_prefix = 'imprint'
    filter_map = {
        # 按所属模板精确过滤，前端在模板详情页只查本模板的列
        'template_id': 'exact',
        # 字段名模糊搜索，方便快速定位某一列配置
        'column_name': 'icontains',
    }
    # 列表按主键倒序（会覆盖 Meta 的 sort 排序，即最近创建的列在前）
    order_by = '-id'
    # 操作日志模块名
    module_name = '导入模板列管理'

    # 覆盖基类查询集：本模型没有 BaseModel 的审计列，但仍需过滤逻辑删除并应用排序。
    def get_queryset(self):
        # 只在未删除列中查询，避免已删配置回显
        return self.model.objects.filter(is_deleted=0).order_by(self.order_by)


# 打印模板视图集：管理 HTML 打印模板及其纸张、业务类型、默认标记等配置。
class PrintTemplateViewSet(CrudViewSet):
    """打印模板表 CRUD。"""
    # 打印模板模型
    model = PrintTemplate
    # 打印模板序列化器（含 html_content 长文本）
    serializer_class = PrintTemplateSerializer
    # 与导入模板共用权限点，便于统一授权
    perm_prefix = 'imprint'
    filter_map = {
        # 模板名称模糊搜索
        'template_name': 'icontains',
        # 模板编码模糊搜索
        'template_key': 'icontains',
        # 业务类型精确匹配，用于按业务线筛模板
        'biz_type': 'exact',
        # 启停状态精确匹配
        'status': 'exact',
    }
    # 主键倒序，最新模板优先
    order_by = '-id'
    # 操作日志模块名
    module_name = '打印模板管理'
