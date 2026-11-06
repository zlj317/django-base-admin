"""通用工具：树构建、bcrypt 密码、模型基础类。"""
# 模块用途：跨 app 复用的小工具集合，包含密码哈希校验、菜单/部门树构建与公共模型字段。
# 被谁调用：登录/用户模块调用密码函数；菜单、部门等模块调用 build_tree；各 models.py 继承 BaseModel。
# 关键约定：密码统一走 bcrypt（不复用 Django 的 make_password，历史数据即为 bcrypt 格式）；
#           BaseModel 的审计字段允许为空，因为数据库表由手工 SQL 创建，模型仅做映射。
import bcrypt  # 密码哈希与校验库，业务侧直接调用即可
from django.db import models  # 定义模型字段类型


# 对外提供密码写入能力；调用方（注册/重置密码/初始化管理员）只需传明文。
def hash_password(raw):
    # 返回值是可打印字符串，可直接存入数据库 varchar/text 列，无需再做编码转换。
    """用 bcrypt 生成带随机盐的密码哈希，返回 str 便于直接入库。"""
    # gensalt() 默认 12 轮成本因子；哈希结果是 bytes，decode 成 str 才能写入 VARCHAR/TEXT 列。
    # raw 必须是 str，若调用方传入 None 会在 encode 处抛 AttributeError。
    return bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')  # 每次盐随机，相同明文结果不同


# 登录校验入口：任何输入都只返回 True/False，不向上抛异常，避免登录接口 500。
def check_password(raw, hashed):
    # hashed 必须是 hash_password 生成的标准 bcrypt 字符串；其他格式走异常分支返回 False。
    """恒定时间比较明文与哈希，格式非法时返回 False 而不抛异常。"""
    # bcrypt.checkpw 内部做恒定时间比较，可避免通过响应时间差来爆破密码。
    try:
        return bcrypt.checkpw(raw.encode('utf-8'), hashed.encode('utf-8'))  # 校验时使用哈希内自带的盐
    except (ValueError, TypeError):
        # ValueError：哈希格式非法或密码为空；TypeError：传入了 None 等非字符串。
        return False  # 旧数据或空密码等异常情况一律按校验失败处理


# 菜单、部门等层级数据的通用组装函数；不依赖模型，传入 dict 列表即可。
def build_tree(rows, root_parent=0, pid_key='parent_id'):
    # 返回值是嵌套结构，调用方（序列化器/接口）直接输出 JSON，无需再递归查询。
    """将含 id/parent_id 的有序列表组装为树。"""
    # 先建 id → 节点 的字典索引，把逐层查找的 O(n^2) 降为 O(n)；{**r} 复制字典，避免污染调用方入参。
    nodes = {r['id']: {**r, 'children': []} for r in rows}  # 先建索引并初始化 children，避免改动入参
    # 最终返回的根节点列表；遍历顺序沿用入参顺序（入参通常已按排序字段查好）。
    tree = []  # 存放根节点
    # 一次遍历即可完成挂载：父节点都已预先建好，因此不依赖列表中父子的先后顺序。
    for node_id, node in nodes.items():
        # 父节点缺失说明父记录被删除或不在当前结果集内，这类孤儿节点需要兜底处理。
        parent = nodes.get(node[pid_key])  # 父节点可能不存在（数据被删除或越权）
        if node[pid_key] == root_parent or parent is None or parent is node:
            # 三种情况都当根：命中配置的根父 ID；孤儿节点；自引用（parent 指向自己）会形成环导致死循环。
            tree.append(node)  # 指定根、孤儿节点、自引用都按根处理，避免脏数据导致死循环
        else:
            # 正常节点挂到父节点的 children 尾部，保持同级原有顺序。
            parent['children'].append(node)  # 挂到父节点下，保持原有顺序
    # 去掉空 children
    # 内部辅助函数：只在 build_tree 内使用，不对外暴露。
    def clean(items):
        # 递归有终止条件：叶子节点 children 为空即停止向下，不会因环状数据无限递归（环已在上面按根处理）。
        """递归删除为空的 children 键，输出更紧凑的树结构。"""
        # 逐层判断：children 为空说明是叶子节点，非空则继续向下一层递归。
        for it in items:
            # 无子节点即叶子：删除 children 键，前端无需处理空数组。
            if not it['children']:
                it.pop('children', None)  # 叶子节点去掉空数组，前端判断更简单
            else:
                # 先处理子层再逐步回溯，所有叶子最终都会被裁剪掉 children 键。
                clean(it['children'])  # 有子节点则继续向下清理
    clean(tree)  # 自根节点向下统一清理
    # 返回根节点列表而非单一对象，因为同一份数据可能包含多棵树（多顶级菜单、多根部门）。
    return tree  # 返回根节点列表


# 业务模型公共基类：子类只需再声明自身业务字段，审计与逻辑删除列由本类统一提供。
class BaseModel(models.Model):
    # 抽象类，Django 不会为它建表；所有字段由子类复制到各自的表中。
    """公共字段基类（表由建表 SQL 手工创建，managed=False）。"""

    # 以下审计字段全部允许为空：初始化脚本、定时任务等系统写入场景没有操作人账号。
    create_by = models.CharField('创建人账号', max_length=64, blank=True, null=True)  # 记录创建者账号，便于审计
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 由业务代码写入本地时间
    update_by = models.CharField('更新人账号', max_length=64, blank=True, null=True)  # 最近一次修改人
    update_time = models.DateTimeField('更新时间', blank=True, null=True)  # 最近一次修改时间
    # 用布尔标记代替物理删除；查询侧（CrudViewSet.get_queryset）统一过滤 is_deleted=0。
    is_deleted = models.BooleanField('逻辑删除', default=False)  # 逻辑删除标记，查询时统一过滤

    # Meta 只负责声明抽象继承，不涉及表名、排序等业务配置。
    class Meta:
        # 抽象基类的 Meta 会被子类继承；abstract 只影响建表，不影响字段继承。
        """抽象基类：不单独建表，仅让子类继承字段。"""
        # abstract=True 时 Django 不会为 BaseModel 生成表，也不会在子类的迁移里出现本类。
        abstract = True  # 防止 Django 为基类生成独立数据表
