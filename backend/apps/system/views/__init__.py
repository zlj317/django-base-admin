from .auth import AuthViewSet  # 认证：登录、当前用户信息、退出
from .config import ConfigViewSet  # 参数配置 CRUD
from .dept import DeptViewSet  # 部门 CRUD 与部门树
from .dict import DictDataViewSet, DictTypeViewSet  # 字典项与字典类型
from .logs import LoginLogViewSet, OperLogViewSet  # 登录日志与操作日志
from .menu import MenuViewSet  # 菜单 CRUD 与菜单树
from .role import RoleViewSet  # 角色 CRUD 与菜单授权
from .user import UserViewSet  # 用户 CRUD、状态切换与角色分配

__all__ = [  # 对外导出的视图集合清单，供 system/urls.py 统一注册
    'AuthViewSet', 'UserViewSet', 'RoleViewSet', 'MenuViewSet', 'DeptViewSet',  # 认证/用户/角色/菜单/部门
    'DictTypeViewSet', 'DictDataViewSet', 'ConfigViewSet', 'OperLogViewSet', 'LoginLogViewSet',  # 字典/参数/两类日志
]
