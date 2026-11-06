
# 模块：apps/notice/__init__.py —— 公告（通知）模块的包入口
# 用途：仅作包标识，聚合 apps/notice 下的模型、序列化器、视图与路由，供 config/urls.py 以 include 方式挂载。
# 对应表：notice_category（公告分类）、notice_info（公告信息）、notice_read（阅读记录），三张表均为手工建表。
# 路由前缀：/api/notice/，下分 category / info / read 三组资源。
# 关键约定：本文件不导入子模块，避免 Django 启动阶段出现循环导入。
