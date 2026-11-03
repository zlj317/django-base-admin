"""通用工具：树构建、bcrypt 密码、模型基础类。"""
import bcrypt
from django.db import models


def hash_password(raw):
    return bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(raw, hashed):
    try:
        return bcrypt.checkpw(raw.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def build_tree(rows, root_parent=0, pid_key='parent_id'):
    """将含 id/parent_id 的有序列表组装为树。"""
    nodes = {r['id']: {**r, 'children': []} for r in rows}
    tree = []
    for node_id, node in nodes.items():
        parent = nodes.get(node[pid_key])
        if node[pid_key] == root_parent or parent is None or parent is node:
            tree.append(node)
        else:
            parent['children'].append(node)
    # 去掉空 children
    def clean(items):
        for it in items:
            if not it['children']:
                it.pop('children', None)
            else:
                clean(it['children'])
    clean(tree)
    return tree


class BaseModel(models.Model):
    """公共字段基类（表由建表 SQL 手工创建，managed=False）。"""

    create_by = models.CharField('创建人账号', max_length=64, blank=True, null=True)
    create_time = models.DateTimeField('创建时间', blank=True, null=True)
    update_by = models.CharField('更新人账号', max_length=64, blank=True, null=True)
    update_time = models.DateTimeField('更新时间', blank=True, null=True)
    is_deleted = models.BooleanField('逻辑删除', default=False)

    class Meta:
        abstract = True
