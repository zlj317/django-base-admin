from .auth import AuthViewSet
from .config import ConfigViewSet
from .dept import DeptViewSet
from .dict import DictDataViewSet, DictTypeViewSet
from .logs import LoginLogViewSet, OperLogViewSet
from .menu import MenuViewSet
from .role import RoleViewSet
from .user import UserViewSet

__all__ = [
    'AuthViewSet', 'UserViewSet', 'RoleViewSet', 'MenuViewSet', 'DeptViewSet',
    'DictTypeViewSet', 'DictDataViewSet', 'ConfigViewSet', 'OperLogViewSet', 'LoginLogViewSet',
]
