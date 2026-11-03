================================================================
{{ table.module_comment }}（{{ table.table_name }}）代码部署说明
================================================================

本次由代码生成器生成，包含后端 Django 模块与前端 Vue 页面。

一、后端部署
1. 将 backend/apps/{{ table.module_name }} 目录拷贝到 Django 项目的 apps/ 目录下；
2. 在 config/settings.py 的 INSTALLED_APPS 中添加 'apps.{{ table.module_name }}'；
3. 在 config/urls.py 中添加路由：
   path('api/', include('apps.{{ table.module_name }}.urls')),
4. 重启 Django 服务（模型 managed=False，无需 migrate；
   若业务表尚未建表，请先在数据库中执行建表 SQL 后再启动）。

二、前端部署
1. 将 frontend/src/api/{{ table.module_name }}.js 拷贝到前端项目的 src/api/ 目录；
2. 将 frontend/src/views/{{ table.gen_path }}.vue 拷贝到前端项目的 src/views/ 目录；
3. 刷新页面即可（菜单已自动注册，或在菜单管理中手动分配权限）。

三、接口清单
- GET  {{ table.url_prefix }}/list             分页列表 + 条件查询
- GET  {{ table.url_prefix }}/update/<pk>/     详情（PUT update 同路径）
- POST {{ table.url_prefix }}/create           新增
- PUT  {{ table.url_prefix }}/update/<pk>      修改
- DELETE {{ table.url_prefix }}/delete         删除（批量 ids）
{% if table.import_enable %}- GET  {{ table.url_prefix }}/importTemplate   下载导入模板
- POST {{ table.url_prefix }}/importData        Excel 导入
{% endif %}{% if table.export_enable %}- GET  {{ table.url_prefix }}/exportData       按条件导出 Excel
{% endif %}
四、权限标识
{% for b in buttons %}  - {{ b.1 }}：{{ b.0 }}
{% endfor %}
注意：重新生成会覆盖本次生成的文件，请做好版本管理。
