
# 包初始化文件：apps/imprint 是“导入模板 + 打印模板”应用包。
# 用途：声明 Python 包，使 apps.imprint.models / serializers / views / urls 可被正常导入。
# 对应表：imp_template、imp_template_column、print_template。
# 路由前缀：/api/imprint/（见 config/urls.py）。
# 幂等性：空实现，重复导入不执行任何逻辑、无副作用。
