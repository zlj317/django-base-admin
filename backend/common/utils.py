"""通用工具：树构建、bcrypt 密码、模型基础类。"""
import bcrypt  # 密码哈希与校验库，业务侧直接调用即可
from django.db import models  # 定义模型字段类型


def hash_password(raw):
    """用 bcrypt 生成带随机盐的密码哈希，返回 str 便于直接入库。"""
    return bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')  # 每次盐随机，相同明文结果不同


def check_password(raw, hashed):
    """恒定时间比较明文与哈希，格式非法时返回 False 而不抛异常。"""
    try:
        return bcrypt.checkpw(raw.encode('utf-8'), hashed.encode('utf-8'))  # 校验时使用哈希内自带的盐
    except (ValueError, TypeError):
        return False  # 旧数据或空密码等异常情况一律按校验失败处理


def build_tree(rows, root_parent=0, pid_key='parent_id'):
    """将含 id/parent_id 的有序列表组装为树。"""
    nodes = {r['id']: {**r, 'children': []} for r in rows}  # 先建索引并初始化 children，避免改动入参
    tree = []  # 存放根节点
    for node_id, node in nodes.items():
        parent = nodes.get(node[pid_key])  # 父节点可能不存在（数据被删除或越权）
        if node[pid_key] == root_parent or parent is None or parent is node:
            tree.append(node)  # 指定根、孤儿节点、自引用都按根处理，避免脏数据导致死循环
        else:
            parent['children'].append(node)  # 挂到父节点下，保持原有顺序
    # 去掉空 children
    def clean(items):
        """递归删除为空的 children 键，输出更紧凑的树结构。"""
        for it in items:
            if not it['children']:
                it.pop('children', None)  # 叶子节点去掉空数组，前端判断更简单
            else:
                clean(it['children'])  # 有子节点则继续向下清理
    clean(tree)  # 自根节点向下统一清理
    return tree  # 返回根节点列表


class BaseModel(models.Model):
    """公共字段基类（表由建表 SQL 手工创建，managed=False）。"""

    create_by = models.CharField('创建人账号', max_length=64, blank=True, null=True)  # 记录创建者账号，便于审计
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 由业务代码写入本地时间
    update_by = models.CharField('更新人账号', max_length=64, blank=True, null=True)  # 最近一次修改人
    update_time = models.DateTimeField('更新时间', blank=True, null=True)  # 最近一次修改时间
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记，查询时统一过滤

    class Meta:
        """抽象基类：不单独建表，仅让子类继承字段。"""
        abstract = True  # 防止 Django 为基类生成独立数据表
