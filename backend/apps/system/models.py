# 模块：apps/system/models.py —— 平台基础模块（系统管理）的 ORM 模型定义
# 用途：映射用户、角色、菜单、部门、字典、参数配置及操作/登录日志等表，
#       供 apps/system/views 下的 ViewSet 与 apps/system/serializers.py 中的序列化器使用。
# 数据表：sys_dept、sys_user、sys_role、sys_menu、sys_dict_type、sys_dict_data、
#         sys_oper_log、sys_login_log、sys_config（均由 docs 建表 SQL 手工维护，managed=False）。
# 路由：apps/system/urls.py 将各模型对应的 ViewSet 挂载到 /api/system/ 前缀下。
# 说明：继承 BaseModel 的模型自动获得 create_by/create_time/update_by/update_time/is_deleted 公共字段。
"""系统基础模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 部门表映射：sys_dept，树形组织架构节点，parent_id=0 表示顶级部门
class SysDept(BaseModel):
    """部门表：树形组织结构，默认按排序号与主键升序。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    parent_id = models.BigIntegerField('父部门ID', default=0)  # 0 表示顶级部门
    dept_name = models.CharField('部门名称', max_length=50)  # 部门名称
    order_num = models.IntegerField('排序', default=0)  # 显示顺序，越小越靠前
    leader = models.CharField('负责人', max_length=50, blank=True, null=True)  # 负责人姓名
    phone = models.CharField('联系电话', max_length=20, blank=True, null=True)  # 联系电话
    status = models.CharField('状态', max_length=1, default='0')  # 0 正常 / 1 停用

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_dept'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['order_num', 'id']  # 默认排序：排序号、主键升序


# 用户表映射：sys_user，登录账号及昵称、联系方式、所属部门等基本信息
class SysUser(BaseModel):
    """用户表：账号、密码及所属部门等基本信息。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    username = models.CharField('用户名', max_length=50, unique=True)  # 登录账号，唯一
    password = models.CharField('密码', max_length=100)  # bcrypt 哈希后的密码
    nickname = models.CharField('昵称', max_length=50, blank=True, null=True)  # 显示昵称
    phone = models.CharField('手机号', max_length=20, blank=True, null=True)  # 手机号
    email = models.CharField('邮箱', max_length=100, blank=True, null=True)  # 邮箱
    avatar = models.CharField('头像地址', max_length=255, blank=True, null=True)  # 头像 URL
    dept_id = models.BigIntegerField('所属部门ID', blank=True, null=True)  # 所属部门
    status = models.BooleanField('状态', default=False)  # 0启用 1禁用

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_user'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表


# 角色表映射：sys_role，role_key 作为权限标识，data_scope 控制该角色可见的数据范围
class SysRole(BaseModel):
    """角色表：角色编码用于权限标识匹配，data_scope 控制数据范围。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    role_name = models.CharField('角色名称', max_length=50)  # 角色显示名称
    role_key = models.CharField('角色编码', max_length=50, unique=True)  # 权限判断用编码
    role_sort = models.IntegerField('角色排序', default=0)  # 显示顺序
    status = models.BooleanField('状态', default=False)  # 0启用 1禁用
    data_scope = models.SmallIntegerField('数据权限', default=1)  # 数据范围级别
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_role'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['role_sort', 'id']  # 默认排序：排序号、主键升序


# 菜单表映射：sys_menu，M/C/F 三类节点构成前端路由与按钮权限树
class SysMenu(BaseModel):
    """菜单表：M 目录 / C 菜单 / F 按钮，树形组织并可挂权限标识。"""
    TYPE_CHOICES = (('M', '目录'), ('C', '菜单'), ('F', '按钮'))  # 菜单类型可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    parent_id = models.BigIntegerField('父级菜单ID', default=0)  # 0 表示顶级菜单
    menu_name = models.CharField('菜单名称', max_length=50)  # 菜单显示名称
    path = models.CharField('路由地址', max_length=200, blank=True, null=True)  # 前端路由
    component = models.CharField('前端组件路径', max_length=255, blank=True, null=True)  # 组件
    perms = models.CharField('权限标识', max_length=100, blank=True, null=True)  # 权限串
    menu_type = models.CharField('菜单类型', max_length=1, choices=TYPE_CHOICES, default='M')  # 类型
    icon = models.CharField('图标', max_length=100, blank=True, null=True)  # 图标名称
    order_num = models.IntegerField('排序', default=0)  # 同级显示顺序
    visible = models.CharField('是否可见', max_length=1, default='0')  # 0 显示 / 1 隐藏
    status = models.CharField('状态', max_length=1, default='0')  # 0 正常 / 1 停用

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_menu'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['order_num', 'id']  # 默认排序：排序号、主键升序


# 字典类型表映射：sys_dict_type，一个类型下挂多个字典项（如性别、启用状态）
class SysDictType(BaseModel):
    """字典类型表：一个类型下挂多个字典项。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    dict_name = models.CharField('字典名称', max_length=100)  # 类型显示名称
    dict_type = models.CharField('字典类型编码', max_length=100, unique=True)  # 唯一编码
    status = models.BooleanField('状态', default=False)  # 0启用 1禁用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_dict_type'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表


# 字典项表映射：sys_dict_data，dict_type_id 关联字典类型，提供展示标签与实际存储值
class SysDictData(BaseModel):
    """字典项表：以 dict_type_id 关联字典类型，提供标签与键值。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    dict_type_id = models.BigIntegerField('字典类型ID')  # 所属字典类型主键
    dict_label = models.CharField('字典标签', max_length=100)  # 展示文本
    dict_value = models.CharField('字典键值', max_length=100)  # 实际存储值
    dict_sort = models.IntegerField('排序', default=0)  # 显示顺序
    status = models.BooleanField('状态', default=False)  # 0启用 1禁用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_dict_data'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['dict_sort', 'id']  # 默认排序：排序号、主键升序


# 操作日志表映射：sys_oper_log，按接口记录增删改操作；字段按手工表结构裁剪，故不继承 BaseModel
class SysOperLog(models.Model):
    """操作日志表（不继承 BaseModel）：仅保留本表 SQL 中实际存在的字段。"""

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    oper_user = models.CharField('操作人', max_length=64, blank=True, null=True)  # 操作人账号
    module_name = models.CharField('操作模块', max_length=50, blank=True, null=True)  # 模块名
    oper_type = models.CharField('操作类型', max_length=20, blank=True, null=True)  # 增删改查
    request_url = models.CharField('请求地址', max_length=255, blank=True, null=True)  # 请求地址
    request_param = models.TextField('请求参数', blank=True, null=True)  # 请求参数快照
    response_result = models.TextField('响应结果', blank=True, null=True)  # 响应内容快照
    cost_time = models.BigIntegerField('耗时毫秒', blank=True, null=True)  # 接口耗时
    oper_time = models.DateTimeField('操作时间', blank=True, null=True)  # 发生时间
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 1 表示已删除

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_oper_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新日志在前


# 登录日志表映射：sys_login_log，记录登录结果、IP 与浏览器信息；同样不继承 BaseModel
class SysLoginLog(models.Model):
    """登录日志表（不继承 BaseModel）：记录登录结果与客户端信息。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    username = models.CharField('登录账号', max_length=50, blank=True, null=True)  # 登录账号
    ip = models.CharField('登录IP', max_length=50, blank=True, null=True)  # 客户端 IP
    login_time = models.DateTimeField('登录时间', blank=True, null=True)  # 登录时间
    status = models.BooleanField('登录状态', default=False)  # 0成功 1失败
    browser = models.CharField('浏览器信息', max_length=100, blank=True, null=True)  # UA 信息
    msg = models.CharField('提示消息', max_length=255, blank=True, null=True)  # 结果提示
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 1 表示已删除

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_login_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新日志在前


# 参数配置表映射：sys_config，config_key 唯一标识一项系统参数，业务代码按 key 读取
class SysConfig(BaseModel):
    """参数配置表：以 config_key 唯一标识一项系统参数。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    config_key = models.CharField('配置键', max_length=100, unique=True)  # 参数唯一键
    config_value = models.CharField('配置值', max_length=500, blank=True, null=True)  # 参数值
    config_name = models.CharField('配置名称', max_length=100, blank=True, null=True)  # 参数名
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'sys_config'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表