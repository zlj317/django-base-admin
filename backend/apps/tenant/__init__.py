# 文件：apps/tenant/__init__.py —— 多租户应用的包入口
# 用途：声明 apps.tenant 是一个 Python 包，使 Django 能按点分路径加载 AppConfig、models、views、urls。
# 对应表：本文件无逻辑；应用涉及 sys_tenant（租户主体）、sys_tenant_user（租户成员）、
#         sys_tenant_package（租户套餐）三张表，均由 docs 建表 SQL 手工创建。
# 路由前缀：/api/tenant/（租户/tenant/、成员/tenant_user/、套餐/package/），由 config/urls.py 挂载。
# 租户隔离：包初始化不做任何租户上下文设置；统一隔离过滤未在代码中实现，当前仅为配置/演示能力。
# 约定：保持空实现，避免在导入阶段访问数据库或产生循环导入；应用配置见 apps.py 的 TenantConfig。
