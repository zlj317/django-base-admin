# 模块用途：system 应用视图包的统一出口，汇总各子模块 ViewSet 供路由层引用。
# 对应路由前缀：系统管理接口挂载在 /api/system/ 下；认证接口单独走 /api/auth/。
# 权限要求：本文件不做权限校验，各 ViewSet 通过 perm_prefix + PermissionCheck 控制细粒度权限。
# 关键约定：仅做 re-export，不写业务逻辑；import 顺序与 __all__ 保持一致，避免遗漏或重复导出。
from .auth import AuthViewSet  # 认证：登录、当前用户信息、退出
from .config import ConfigViewSet  # 参数配置 CRUD
from .dept import DeptViewSet  # 部门 CRUD 与部门树
from .dict import DictDataViewSet, DictTypeViewSet  # 字典项与字典类型
from .logs import LoginLogViewSet, OperLogViewSet  # 登录日志与操作日志
from .menu import MenuViewSet  # 菜单 CRUD 与菜单树
from .role import RoleViewSet  # 角色 CRUD 与菜单授权
from .user import UserViewSet  # 用户 CRUD、状态切换与角色分配

# __all__ 显式声明公开符号，防止 `from apps.system.views import *` 时导出意外名称。
__all__ = [  # 对外导出的视图集合清单，供 system/urls.py 统一注册
    'AuthViewSet', 'UserViewSet', 'RoleViewSet', 'MenuViewSet', 'DeptViewSet',  # 认证/用户/角色/菜单/部门
    'DictTypeViewSet', 'DictDataViewSet', 'ConfigViewSet', 'OperLogViewSet', 'LoginLogViewSet',  # 字典/参数/两类日志
]
