
# 模块：apps/sys_no/__init__.py —— 编码规则（单据编号生成）模块的包初始化文件
# 用途：标识 sys_no 为独立 Django app 包，供 apps.sys_no.models / views / urls 等子模块导入时定位。
# 约定：本文件不导出任何符号、不执行任何副作用，保持轻量以免应用启动阶段产生额外开销。
# 关联：应用配置见 apps.py（SysNoConfig）；表映射见 models.py（sys_no_rule / sys_no_log）；
#       接口与路由见 views.py、urls.py；菜单权限初始化见 seed.py。
