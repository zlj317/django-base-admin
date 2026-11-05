# 05 - Java 开发者零基础学习路线

> 适用人群：有多年 Java / Spring Boot 经验，但**从未系统接触过 Python / Django**，希望通过阅读与动手，快速掌握本项目的技术栈、代码结构与全部功能。
>
> 配套文档：
> - [01-项目结构与调用关系](./01-项目结构与调用关系.md)：文件级调用矩阵、架构图、时序图
> - [02-功能说明文档](./02-功能说明文档.md)：每个模块的功能、接口、权限与规则
> - [03-运行启动指南](./03-运行启动指南.md)：环境、建库、启动、验证
> - [04-多平台部署指南](./04-多平台部署指南.md)：Linux / Windows / Docker / 云平台部署
>
> 本文档的目标不是教你"Python 的全部"，而是教你**只学本项目用得到的部分**，并把它们映射到你熟悉的 Java 概念上。

---

## 0. 如何使用这份文档

### 0.1 学习总原则

1. **对照迁移**：每学一个 Python/Django 概念，立刻问自己"它在 Spring Boot 里对应什么"。
2. **以请求为主线**：不要从上到下逐文件背代码，而是跟着一次 HTTP 请求穿过前端 → 后端 → 数据库。
3. **先跑通，再读码**：先按 03 文档把系统跑起来，用浏览器与接口验证，再回头读实现。
4. **小步验证**：每读完一个阶段，做一个能观察到结果的小练习（改一个返回字段、加一个查询条件），而不是只"看懂了"。
5. **只读真实代码**：本文所有路径都指向仓库里的真实文件，遇到疑问直接打开对应文件确认。

### 0.2 推荐阅读顺序

```
03 运行启动 → 05 本文（语言/框架对照 + 分阶段路线）→ 01 结构调用关系 → 02 功能说明 → 04 部署
```

理由：先让系统在你机器上跑起来（有反馈），再建立语言与框架的对照（降低陌生感），然后建立全局地图（01），再逐个功能深入（02），最后学习上线（04）。

### 0.3 学习成果自检

完成本文档后，你应当能够独立回答：

- 一个 `/api/system/user/list` 请求经过了哪些文件、哪些类、哪些 SQL？
- 新增一个业务表后，如何用代码生成器产出前后端代码并注册菜单？
- 如何给一个新接口加权限、给新页面加菜单、给按钮加 `v-perm`？
- 出现 401 / 403 / 404 / 500 时，分别先查哪里？

---

## 1. 先建立地图：这个项目是什么

### 1.1 一句话架构

- **后端**：Django 4.2 + Django REST Framework（DRF），MySQL 8，自研 JWT 鉴权，bcrypt 密码，逻辑删除，统一响应体。
- **前端**：Vue 3 + Vite 5 + Element Plus + vue-router 4 + axios，**不使用 Pinia**（用 `reactive` 轻量全局状态），菜单与路由由后端下发。
- **核心特色**：内置**代码生成器**。读取 MySQL 业务表 → 配置字段 → 预览/下载前后端代码 ZIP → 自动注册菜单，生成 CRUD + Excel 导入导出页面。

### 1.2 与典型 Java 项目对照

| 维度 | 本项目（Python/Django） | 你熟悉的 Java 体系 |
|---|---|---|
| 项目构建 | `requirements.txt` + `pip` | `pom.xml` / `build.gradle` |
| 虚拟环境 | `backend/venv`（venv） | Maven/Gradle 本地仓库 + JDK 版本 |
| 启动入口 | `backend/manage.py` | `SpringApplication.run` / `mvn spring-boot:run` |
| 全局配置 | `backend/config/settings.py` | `application.yml` / `application.properties` |
| 组件扫描 | `INSTALLED_APPS` 列表 | `@ComponentScan` / `@SpringBootApplication` |
| 路由 | `config/urls.py` + 各 app `urls.py` | `@RequestMapping` / `@GetMapping` |
| 控制器 | DRF `ViewSet`（`as_view({...})` 映射 action） | `@RestController` |
| DTO / 校验 | `serializers.py`（序列化 + 校验一体） | DTO + Jackson + Bean Validation |
| ORM | Django ORM（`models.py`） | JPA / MyBatis / MyBatis-Plus |
| 事务 | `transaction.atomic()` | `@Transactional` |
| 过滤器/拦截器 | `MIDDLEWARE`（`common/middleware.py`） | `Filter` / `HandlerInterceptor` |
| 全局异常 | `common/exception.py` 的 `exception_handler` | `@RestControllerAdvice` |
| 分页 | `common/pagination.py` 手写 | PageHelper / Spring Data Pageable |
| 鉴权 | 自研 JWT（`common/auth.py`）+ 自定义权限类 | Spring Security + JWT Filter |
| 日志 | `logging` + 操作日志中间件写库 | Logback + AOP 切面写库 |
| 数据库版本管理 | **无 migrations**（`managed=False`，表由 SQL 手工创建） | Flyway / Liquibase |
| 前端 | Vue3 单页应用（`frontend/src`） | 若习惯 Thymeleaf/JSP，需要切换思维 |

### 1.3 目录快速导读（只看自有代码）

```
django-base-admin/
├─ docs/                          # 需求、建表 SQL、以及本套总结文档（01~05）
├─ backend/
│  ├─ manage.py                   # 命令行入口：runserver / init_db / check
│  ├─ requirements.txt            # Python 依赖清单
│  ├─ config/
│  │  ├─ settings.py              # 数据库、JWT、中间件、DRF、CORS 配置
│  │  ├─ urls.py                  # 全局路由挂载点（api/auth、api/system、api/gen、api/）
│  │  └─ wsgi.py / asgi.py        # 部署入口
│  ├─ common/                     # 公共能力（相当于项目的 common/infra 包）
│  │  ├─ auth.py                  # JWT 认证类 + LoginRequired
│  │  ├─ permissions.py           # 权限标识校验（system:user:list）
│  │  ├─ views.py                 # 通用 CRUD ViewSet 基类
│  │  ├─ pagination.py            # 统一分页
│  │  ├─ response.py              # ok / fail 统一响应
│  │  ├─ exception.py             # 全局异常处理
│  │  ├─ middleware.py            # 操作日志 + token 静默续期
│  │  └─ utils.py                 # bcrypt、树构建、基础模型
│  ├─ apps/
│  │  ├─ system/                  # 平台基础模块（用户/角色/菜单/部门/字典/配置/日志/认证）
│  │  ├─ gen/                     # 代码生成器（配置表、引擎、模板）
│  │  └─ student/                 # 生成示例模块（学生信息表 CRUD + 导入导出）
│  └─ core/management/commands/   # 自定义命令 init_db.py（建库建表初始化）
└─ frontend/
   ├─ vite.config.js              # 端口 5173，/api 代理到 127.0.0.1:8000
   └─ src/
      ├─ main.js                  # 应用入口，注册 Element Plus / 图标 / 指令
      ├─ router/index.js          # 静态路由 + 基于后端菜单的动态路由
      ├─ store/auth.js            # 登录态、权限、菜单（reactive，替代 Pinia）
      ├─ utils/request.js         # axios 封装：token、统一响应、续期、错误提示
      ├─ directive/perm.js        # 按钮级权限指令 v-perm
      ├─ layout/                  # 布局：Sidebar / SidebarItem / Navbar
      └─ views/                   # 页面：login、dashboard、system/*、gen/*、student
```

---

## 2. Python 速成（只学本项目用到的）

> 目标：能读懂 `backend/**/*.py` 的每一行。以下内容都配了项目中的真实写法。

### 2.1 语法最小集

**缩进即代码块**：Python 没有 `{}`，用 4 个空格表示层级；没有分号结尾。

```python
# Java: if (user != null && !user.isDeleted()) { ... }
if user is not None and not user.is_deleted:
    return ok(data)
```

**动态类型**：变量不需要声明类型，类型跟着值走。

```python
page = 1              # int
page = "1"            # 重新赋值为 str 是允许的（但项目里会用 int(...) 转换）
```

**常见运算符差异**：

| 场景 | Python | Java |
|---|---|---|
| 逻辑与/或/非 | `and` / `or` / `not` | `&&` / `\|\|` / `!` |
| 空值 | `None` | `null` |
| 判空惯用 | `if not value` / `if value is None` | `if (value == null)` |
| 三元表达式 | `a if cond else b` | `cond ? a : b` |
| 字符串格式化 | f-string：`f'{name}: {count}'` | `String.format` / 模板字符串 |
| 相等 | `==`（值比较） | `equals` |

### 2.2 数据结构

```python
users = []                          # list ≈ ArrayList
user = {'id': 1, 'username': 'admin'}   # dict ≈ HashMap
ids = {row[0] for row in rows}     # set ≈ HashSet
pair = (1, 'admin')                # tuple：不可变序列，常用于数据库查询返回值
```

项目中的典型用法：

- `query_params.get('page', 1)`：读取 GET 参数，第二个参数是默认值。
- `[r[0] for r in cursor.fetchall()]`：**列表推导式**，等价于 Java 的 stream map + collect。
- `{**r, 'children': []}`：字典展开，等价于"复制 Map 再覆盖一个 key"。
- `next(iter(msg.values()))`：取第一个值，等价于 `map.values().iterator().next()`。

### 2.3 函数与参数

```python
def ok(data=None, msg='success'):       # 默认参数
    return Response({'code': 200, 'msg': msg, 'data': data})
```

- 关键字参数调用：`fail('不能修改自己的状态', code=400)`。
- `*args` / `**kwargs` ≈ Java 可变参数，但 `**kwargs` 可接收任意关键字参数。
- 函数可作为参数传递（如 DRF 的 `get_response`）。

### 2.4 类、继承与 self

```python
class UserViewSet(CrudViewSet):          # 继承 ≈ extends
    model = SysUser                      # 类属性 ≈ static 字段/配置常量
    perm_prefix = 'system:user'

    def get_serializer_class(self):      # self ≈ this，但必须显式写在参数里
        if self.action == 'list':
            return UserListSerializer
        return UserCreateSerializer
```

- **没有接口（interface）**，靠多继承/约定；DRF 用"继承 + 覆写钩子"实现模板方法，类似 Spring 的抽象基类。
- 没有方法重载：同名方法后者覆盖前者；需要不同参数就换方法名或用默认参数。
- 不需要写 getter/setter，直接访问属性：`user.status`。

### 2.5 模块、包与导入

```
backend/common/response.py  →  import common.response 或 from common.response import ok
backend/apps/system/views/user.py → from apps.system.models import SysUser
```

- 一个 `.py` 文件就是一个模块；包含 `__init__.py` 的目录是包（`__init__.py` 可为空）。
- 导入是**运行时执行模块顶层代码**，因此要避免循环导入；项目里用"函数内局部 import"打破循环（如 `common/auth.py` 里 `from apps.system.models import SysUser` 放在函数内）。

### 2.6 装饰器 ≈ 注解 + AOP

```python
@action(detail=True, methods=['put'])
def status(self, request, pk=None):
    ...
```

`@action` 是 DRF 装饰器，把普通方法暴露成一个路由动作（类似在 Controller 上加 `@PutMapping("/status/{id}")`）。项目里 `@property` 也是装饰器，等价于"只读 getter"。

### 2.7 异常与 with

```python
try:
    payload = decode_token(token)
except jwt.ExpiredSignatureError:
    raise AuthFailed('登录已过期，请重新登录')
```

- `except` ≈ `catch`，`raise` ≈ `throw`。
- `with connection.cursor() as cursor:` ≈ try-with-resources（自动关闭资源）。

### 2.8 运行环境：venv + pip

| 操作 | 命令（在 backend 目录） |
|---|---|
| 创建虚拟环境 | `python -m venv venv` |
| 激活（Windows PowerShell） | `.\venv\Scripts\Activate.ps1` |
| 激活（macOS/Linux） | `source venv/bin/activate` |
| 安装依赖 | `pip install -r requirements.txt` |
| 运行 Django 命令 | `python manage.py ...`（虚拟环境激活后） |

> 类比：`venv` ≈ 项目级 JDK + 本地仓库隔离；`requirements.txt` ≈ `pom.xml` 的依赖坐标集合。

### 2.9 思维差异清单

| 你可能的第一反应（Java） | Python 实际 |
|---|---|
| 先声明类型 | 不声明；靠命名与代码可读性 |
| `null` 检查用 `== null` | 用 `is None` 更规范 |
| 大括号划分作用域 | 缩进划分，Tab/空格混用会报错 |
| 接口先行 | 鸭子类型：能调用就行，靠约定与文档 |
| 编译期发现错误 | 运行期发现；靠 `python manage.py check`、测试、类型注解可选 |
| 字符串不可变（Java 也是） | 同；但列表/字典是可变对象 |
| `for (int i=0;...)` | 直接 `for item in list`，需要索引才用 `enumerate` |
| 异常必须声明 | 不强制声明 |

---

## 3. Django / DRF 与 Spring Boot 对照

### 3.1 一次请求的生命周期（务必先建立这个模型）

```
浏览器
  → Nginx/Vite（静态资源 + /api 反向代理）
  → Django URL 解析（config/urls.py → apps/*/urls.py）
  → MIDDLEWARE 链（CORS → Common → OperLog → TokenRefresh）
  → DRF 认证（common/auth.py: JWTAuthentication → request.user_info）
  → 权限（common/permissions.py: PermissionCheck + perm_map）
  → ViewSet 方法（list/create/update/delete/自定义 action）
  → Serializer（校验 + 序列化）
  → Model / ORM / 原生 SQL（MySQL）
  → common/response.py ok()/fail()
  → 中间件回写（操作日志、X-Refresh-Token）
  → 前端 axios 拦截器（toast / 401 跳登录）
```

### 3.2 关键映射表

| Spring Boot | 本项目 | 位置 |
|---|---|---|
| `application.yml` | `settings.py` | `backend/config/settings.py` |
| `@SpringBootApplication` | `INSTALLED_APPS` + `manage.py` | `settings.py` |
| `@RestController` + `@GetMapping` | `ViewSet` + `urls.py` 的 `as_view({...})` | `apps/*/urls.py` |
| `@RequestBody` DTO | `request.data` + Serializer | `views/*.py`、`serializers.py` |
| `@RequestParam` | `request.query_params` | `views/*.py` |
| Bean Validation | Serializer 的 `validate_xxx` / `validate` | `serializers.py` |
| `@Transactional` | `with transaction.atomic():` | `apps/gen/views.py` |
| `Filter` / `Interceptor` | `MIDDLEWARE` 中的类 | `common/middleware.py` |
| `@RestControllerAdvice` | `EXCEPTION_HANDLER` | `common/exception.py` |
| Spring Security Filter | DRF `JWTAuthentication` | `common/auth.py` |
| `Pageable` | `StandardPagination` | `common/pagination.py` |
| MyBatis Mapper XML SQL | `connection.cursor()` 执行 SQL | `common/permissions.py` 等 |

### 3.3 阅读练习：把"登录"走一遍

1. 前端：`frontend/src/views/login/index.vue` 调 `login(form)`（来自 `store/auth.js`）。
2. `store/auth.js` 发 `POST /auth/login`（request 的 baseURL 是 `/api`，最终 `/api/auth/login`）。
3. 后端路由：`config/urls.py` → `api/auth/` → `apps/system/urls_auth.py` → `AuthViewSet.login`。
4. `login` 校验：查 `SysUser`、`check_password`（bcrypt）、检查 `status`、写 `SysLoginLog`、`create_token`。
5. 返回 `{token, user, perms, menus}`，前端写入 `localStorage` 并跳转 `/dashboard`。
6. 全局守卫：`router/index.js` 的 `beforeEach` 用 `auth.menus` 调 `buildDynamicRoutes` 注册页面路由。

**验收**：你能不看代码说出"token 存在哪、菜单从哪来、动态路由什么时候注册"。

---

## 4. 数据库层：SQL-first + `managed=False`

### 4.1 与 JPA 最大的不同

| 方面 | 本项目 | 典型 Spring Boot |
|---|---|---|
| 建表 | `docs/后台管理系统-初始化建表SQL.sql` 手工执行 | Flyway/Liquibase 或 JPA 自动建表 |
| 模型角色 | 只做"表到对象"的映射，不管理表结构 | 实体类即表结构来源 |
| 迁移 | **没有 migrations** | `mvn flyway:migrate` |
| 表结构变更 | 改 SQL + 改模型字段 | 写迁移脚本 + 改实体 |

`apps/system/models.py` 中每个模型都有：

```python
class Meta:
    db_table = 'sys_user'
    managed = False        # 告诉 Django：不要创建/修改此表
```

### 4.2 公共字段与逻辑删除

- `common/utils.py:BaseModel` 定义 `create_by/create_time/update_by/update_time/is_deleted`。
- 查询一律 `filter(is_deleted=0)`；删除一律 `update(is_deleted=1)`。
- `is_deleted` 用 `BooleanField`，数据库里是 0/1。

> 类比：相当于所有实体继承一个 `BaseEntity`，并在 Repository 层统一加 `deleted = false` 条件。

### 4.3 你需要注意的"坑"

- `SysUser.status` 是 `BooleanField`（False=正常，True=停用），但前端需要 0/1，所以 `UserListSerializer` 用 `SerializerMethodField` 转成 0/1。
- 模型字段类型必须与 SQL 表一致，否则 MySQL 报错或数据错乱。
- `python manage.py makemigrations` **不要执行**：`managed=False` 不会生成有效迁移，本项目也不用迁移。

### 4.4 初始化命令 `init_db`

`backend/core/management/commands/init_db.py`：

1. 用 `pymysql` 直接连 MySQL 实例创建 `gen_admin` 库；
2. 读取 SQL 文件按分号拆分执行；
3. 把 admin 密码重置为 bcrypt('123456')；
4. 插入 12 个菜单与按钮权限，并授权给超级管理员角色。

> 注意：`SQL_FILE` 是写死的 Windows 路径，换平台前要改（详见 03/04 文档）。

---

## 5. 认证与权限：本项目最值得精读的一段

### 5.1 JWT 认证类

`common/auth.py`：

- `create_token(user)`：payload `{uid, username, exp}`，HS256，有效期 2 小时。
- `JWTAuthentication.authenticate`：从 `Authorization: Bearer <token>` 取 token，解析失败抛 401。
- 成功时同时挂两处：`request.user_info`（DRF Request）与 `request._request.user_info`（Django 原生 Request），供中间件使用。
- **用户状态**：认证时 `filter(status=0)`，即停用用户无法通过认证。

### 5.2 token 静默续期

`common/middleware.py:TokenRefreshMiddleware`：

- 剩余有效期 < 30 分钟且 > 0 时，在响应头写 `X-Refresh-Token`；
- 前端 `utils/request.js` 发现该响应头就 `setToken` 覆盖本地 token。

> 与 Spring Security 的 "refresh token" 思路类似，但这里不换发新 token 类型，只是滚动续期。

### 5.3 权限校验

- 后端：`PermissionCheck` 读取视图的 `perm_map`（action → 权限标识），查询"用户-角色-菜单"关联得到 perms；`admin` 角色自动拥有 `*:*:*`。
- 前端：`v-perm="'system:user:create'"` 指令在无权限时隐藏按钮。
- 按钮权限不是安全边界（前端可绕过），真正的边界在后端 `PermissionCheck`。

**练习**：把 `apps/system/views/user.py` 的 `reset_pwd` 权限标识从 `system:user:resetPwd` 改成 `system:user:reset`，观察前端按钮是否消失、后端是否 403（记得同步 `init_db.py` 的 BUTTONS 与数据库菜单）。

---

## 6. 通用 CRUD 框架：读懂 4 个 CRUD 页面靠它

### 6.1 `common/views.py:CrudViewSet`

它把"列表/新增/修改/删除"写成模板方法，子类只需声明：

```python
class UserViewSet(CrudViewSet):
    model = SysUser
    perm_prefix = 'system:user'          # 自动生成 :list/:create/:update/:delete
    filter_map = {'username': 'icontains', 'status': 'exact'}
    module_name = '用户管理'               # 操作日志模块名
```

- `list`：`apply_filters` → `StandardPagination.paginate` → 序列化；
- `create`：Serializer 校验 → `save(create_by/create_time/...)` → `after_create` 钩子；
- `update`：`partial=True`（相当于 PATCH 语义）→ `after_update` 钩子；
- `delete`：接收 `ids` 数组，批量 `is_deleted=1`。

这相当于 Java 里的 `BaseController<T>` + `BaseService<T>` + `MyBatis-Plus` 的组合体，但钩子更轻量。

### 6.2 路由生成器

`apps/system/urls.py` 的 `crud(prefix, viewset, extras)` 会生成：

```
/system/user/list        GET | POST | DELETE
/system/user/create      POST
/system/user/delete      DELETE
/system/user/update/<pk> PUT
```

并允许追加自定义动作（如 `status/<int:pk>`、`assign_roles/<int:pk>`）。

> 注意：路径**没有尾斜杠**。Django 默认 `APPEND_SLASH=True` 会把 `/list/` 301 到 `/list`；对 PUT 请求，301 后方法可能变化，所以前端一律用无尾斜杠地址。

### 6.3 阅读任务（按顺序）

1. `common/views.py`：找到 `permission_classes` 里生成 `perm_map` 的写法。
2. `apps/system/views/user.py`：看 `after_create/after_update` 如何维护 `sys_user_role`。
3. `apps/system/urls.py`：对照 `crud()` 与最终 URL。
4. 用浏览器 F12 看 `/api/system/user/list?page=1&page_size=10` 的请求与响应。

---

## 7. 代码生成器：本项目的核心能力

### 7.1 数据流

```
业务表（MySQL）
  → GET /api/gen/db/tables（engine.list_db_tables，读 information_schema）
  → POST /api/gen/db/import（engine.import_table，写 sys_gen_table + sys_gen_table_column）
  → 前端 gen/edit 配置字段（表单类型、查询方式、字典、列表/导入/导出）
  → PUT /api/gen/table/{id}（保存配置）
  → GET /api/gen/table/{id}/preview（engine.render_files，返回 9 个文件内容）
  → GET /api/gen/table/{id}/ddl（engine.get_table_ddl）
  → GET /api/gen/table/{id}/download（ZIP + 自动注册菜单）
  → 部署生成代码（后端 app + 前端页面）
  → 重新登录/刷新菜单，新菜单出现
```

### 7.2 `engine.py` 函数地图（读这个文件按此顺序）

| 函数 | 作用 | 你要关注的点 |
|---|---|---|
| `list_db_tables` | 读当前库业务表，排除 `sys_`/`django_`/`auth_` | 如何判断"已导入" |
| `get_table_ddl` | `SHOW CREATE TABLE` | 表名白名单正则防注入 |
| `get_db_columns` | 读列信息 | 字段类型、主键、可空 |
| `guess_form_type` | 列名/类型 → 表单控件 | 图片/文件/日期/多行/数字判断 |
| `guess_query_type` | 类型 → 查询方式 | 字符串用 like，其他用 eq |
| `import_table` | 写生成配置 + 默认字段配置 | 公共字段（create_by 等）跳过 |
| `render_files` | 渲染 9 个产物 | 产物路径约定 |
| `build_*` | 拼接 Vue/JS 字符串 | 为什么用字符串拼而不是模板 |

### 7.3 生成的 9 个文件

```
backend/apps/{module_name}/__init__.py
backend/apps/{module_name}/apps.py
backend/apps/{module_name}/models.py
backend/apps/{module_name}/serializers.py
backend/apps/{module_name}/views.py
backend/apps/{module_name}/urls.py
README-部署说明.txt
frontend/src/api/{module_name}.js
frontend/src/views/{gen_path}.vue
```

### 7.4 模板机制

- 后端 Python 文件用 Django Template（`backend/apps/gen/templates/gen/*.tpl`，如 `models.py.tpl`），类似 FreeMarker/Velocity。
- 前端 Vue 页面因为要按字段动态生成大量重复片段，采用 **Python 字符串拼接**（`build_vue_page`），比模板更灵活。
- 模板中 `{{ }}` 是 Django 模板变量；生成的目标 Vue 文件里的 `{{ }}` 必须转义/避免被模板引擎解析，阅读时注意区分。

### 7.5 练习：完整走一遍生成流程

1. 在 MySQL 里建一张业务表（如 `biz_book`，包含 `title/price/publish_date/cover_img`）。
2. 登录 → 系统工具 → 代码生成 → 导入数据表 → 勾选 `biz_book`。
3. 进入配置页，观察默认推断结果，修改 1-2 个字段（如 `cover_img` 用 image、`title` 必填）。
4. 预览 9 个文件，对照第 7.3 节路径。
5. 下载 ZIP，解压后把后端目录复制到 `backend/apps/`，前端文件复制到 `frontend/src/`。
6. 在 `config/settings.py` 的 `INSTALLED_APPS` 与 `config/urls.py` 注册新模块（生成器的 README 会提示）。
7. 重启后端、刷新菜单，验证新页面 CRUD。

**验收**：能解释"为什么导入后菜单会自动出现""为什么下载前要先配置 parent_menu_id"。

---

## 8. 前端 Vue3：给 Java 后端开发者的最小集

> 你不需要成为前端专家，但必须能改页面、加查询条件、加按钮。

### 8.1 思维对照

| Java Web 经验 | Vue3 本项目 |
|---|---|
| JSP/Thymeleaf 模板渲染 | 单文件组件（`.vue`：template/script/style） |
| jQuery DOM 操作 | 数据驱动：改状态 → 视图自动更新 |
| `@Controller` 返回页面 | 路由 `router/index.js` 按路径加载组件 |
| 表单提交 + 刷新 | axios 调接口 → `ElMessage` 提示 → 重新拉列表 |
| Session 保存登录态 | `localStorage` + `store/auth.js` 的 reactive 对象 |
| 拦截器 | axios `interceptors.request/response` |
| 权限标签库 | 自定义指令 `v-perm` |

### 8.2 Composition API 四个核心

```js
const list = ref([])                 // 响应式基本/数组，读写用 list.value
const query = reactive({ name: '' }) // 响应式对象，直接 query.name
const total = computed(() => list.value.length)  // 派生值（只读）
onMounted(() => { fetchList() })     // 生命周期：组件挂载后执行
```

- `ref` ≈ 包装对象（`.value`）；`reactive` ≈ 可观察对象。
- 页面通过 `import request from '@/utils/request'` 调接口，返回的 `res` 已是 `{code,msg,data}`（拦截器已剥壳）。

### 8.3 三个必须读的文件

1. `utils/request.js`：baseURL `/api`、token 注入、`code!==200` 弹错、401 跳登录、`X-Refresh-Token` 续期、blob 下载放行。
2. `router/index.js`：静态路由（登录/首页/生成配置/404）+ 动态路由（后端 menus → `addRoute`）+ 守卫（首次加载 userinfo → 注册动态路由 → 重新解析当前路径）。
3. `store/auth.js`：`login/fetchUserinfo/logout`、`hasPerm`、`clearDynamicRoutes` 配合。

### 8.4 页面阅读模板（任意 `views/system/*/index.vue` 都适用）

```
<template>  页面结构：page-header + search-card + table-card + dialog
<script>    fetchList（request.get） / handleSave（request.post|put） / handleDelete
<style>     仅局部样式，全局主题在 styles/index.css
```

---

## 9. 分阶段学习计划

> 每个阶段都有「目标 / 必读文件 / 关键问题 / 动手练习 / 验收标准」。按顺序完成，不要跳阶段。

### Phase 0：把系统跑起来

- **目标**：能独立完成 03 文档中的环境准备、建库、启动、登录。
- **必读**：`docs/03-运行启动指南.md`。
- **关键问题**：数据库连接参数在哪？`init_db` 做了什么？前端为什么能访问 `/api`？
- **动手**：修改 `settings.py` 的数据库密码，重新启动成功；用 admin/123456 登录。
- **验收**：能用 curl 拿到 `/api/system/user/list` 的 200 响应。

### Phase 1：Python + Django 骨架

- **目标**：读懂 `manage.py`、`settings.py`、`config/urls.py`，理解"配置即装配"。
- **必读**：`backend/manage.py`、`config/settings.py`、`config/urls.py`、`common/response.py`、`common/utils.py`。
- **关键问题**：`INSTALLED_APPS` 与 Spring 的组件扫描有何不同？为什么响应 HTTP 恒 200？
- **动手**：写一个 `GET /api/system/ping` 返回 `ok({'pong': true})`（临时加在 `apps/system/urls.py` 与视图）。
- **验收**：能用浏览器/curl 访问并看到 `{code:200,msg:'success',data:{pong:true}}`，然后删除临时代码。

### Phase 2：认证链路

- **目标**：完全掌握 JWT 签发、校验、续期、前后端配合。
- **必读**：`views/login/index.vue`、`store/auth.js`、`utils/request.js`、`apps/system/views/auth.py`、`apps/system/urls_auth.py`、`common/auth.py`、`common/middleware.py`。
- **关键问题**：`request.user_info` 在哪里被设置？401 时前端做了什么？token 剩余多久会续期？
- **动手**：把 `JWT_CONFIG['EXPIRE']` 改为 10 分钟，重启后用 F12 观察 `X-Refresh-Token` 响应头。
- **验收**：能画出登录 + 续期的时序图。

### Phase 3：通用 CRUD 与权限

- **目标**：掌握 `CrudViewSet`、`StandardPagination`、`PermissionCheck`、`v-perm`。
- **必读**：`common/views.py`、`common/pagination.py`、`common/permissions.py`、`apps/system/views/user.py`、`apps/system/urls.py`、`serializers.py`。
- **关键问题**：`perm_map` 如何生成？为什么 `status` 前端是 0/1 而模型是布尔？逻辑删除在哪一层？
- **动手**：新增一个查询参数（如按邮箱模糊查询），从前端到后端完整实现。
- **验收**：能在 15 分钟内给任意 CRUD 模块加一个字段/查询条件。

### Phase 4：菜单、角色、动态路由

- **目标**：理解"菜单即权限即路由"的联动。
- **必读**：`apps/system/models.py`（SysMenu）、`views/menu.py`、`views/role.py`、`router/index.js`、`layout/components/Sidebar*.vue`。
- **关键问题**：`menu_type` M/C/F 各是什么？新增菜单后前端何时能看见？`component` 字符串如何映射到 `.vue`？
- **动手**：手动在菜单管理新增一个页面菜单（component 指向已有页面），分配给角色，重新登录验证。
- **验收**：能解释"为什么刷新深层链接会 404 以及守卫如何修复"。

### Phase 5：代码生成器

- **目标**：读透 `engine.py`，能独立生成并部署一个业务模块。
- **必读**：`apps/gen/engine.py`、`views.py`、`urls.py`、`templates/gen/*.tpl`、`frontend/src/views/gen/*`。
- **关键问题**：默认字段配置怎么推断？前端页面为什么用字符串拼接？菜单注册如何防重复？
- **动手**：完成 7.5 节的 `biz_book` 全流程。
- **验收**：生成模块的 CRUD、导入、导出全部可用，操作日志有记录。

### Phase 6：前端页面与联调

- **目标**：能独立修改任意系统页面。
- **必读**：`views/system/user/index.vue`（最完整）、`gen/table/index.vue`、`gen/edit/index.vue`、`student/index.vue`、`styles/index.css`。
- **关键问题**：查询/重置/分页/弹窗表单/批量删除的标准写法是什么？
- **动手**：给用户管理加一个"导出用户"按钮（可只做前端假实现或后端简单 CSV）。
- **验收**：改动后 `npm run build` 通过，页面交互正常。

---

## 10. 功能全链路练习清单（覆盖所有功能）

| 编号 | 练习 | 验收标准 |
|---|---|---|
| 1 | 登录、退出、token 过期续期 | 401 自动跳登录；响应头出现新 token |
| 2 | 用户增删改查、批量删除、重置密码、分配角色 | 数据落库且逻辑删除，密码可用新值登录 |
| 3 | 用户状态开关 | admin 自己不可改；他人状态切换生效 |
| 4 | 角色管理 + 分配菜单权限 | 新角色登录后只看到被授权菜单 |
| 5 | 菜单管理（M/C/F、排序、隐藏） | 改菜单后刷新侧边栏生效 |
| 6 | 部门树管理 | 新增子部门、树形展示正确 |
| 7 | 字典类型 + 字典数据 | 前端下拉/标签翻译生效（`dictLabel`） |
| 8 | 参数配置 | 修改 `sys.export.max_rows` 影响导出 |
| 9 | 操作日志 | 任意写操作产生一条记录（模块/类型/耗时） |
| 10 | 登录日志 | 成功与失败登录各产生记录，IP/UA 正确 |
| 11 | 代码生成全流程 | 新表 → 导入 → 配置 → 预览 → 下载 → 部署 → 菜单出现 |
| 12 | 生成模块导入导出 | 模板下载、错误行提示、批量导入、条件导出 |

---

## 11. 调试与排错

### 11.1 后端

- **看日志**：`runserver` 控制台会打印每个请求与异常栈；全局异常还会写 `logger.exception`。
- **断点**：在代码里插入 `import pdb; pdb.set_trace()`（类似 IDE 断点，命令行输入 `n` 单步、`c` 继续、`p 变量` 打印）。
- **检查配置**：`python manage.py check`。
- **SQL 排查**：项目大量使用 `connection.cursor()` 原生 SQL，可直接在 MySQL 客户端复现。
- **接口验证**：用 curl / PowerShell / Postman，注意 `Authorization: Bearer <token>`、路径无尾斜杠。

### 11.2 前端

- F12 Network：看请求 URL、Header、响应 `code/msg`。
- Console：看 Vue 报错（常见是字段名不一致、`undefined` 取值）。
- 路由问题：确认动态路由是否已注册（登录后菜单是否为空）。

### 11.3 业务码速查

| code | 含义 | 优先排查 |
|---|---|---|
| 401 | 未登录 / token 失效 | token 是否存在、是否过期、用户是否停用 |
| 403 | 无权限 | 角色是否分配对应菜单/按钮权限；`perm_map` 拼写 |
| 404 | 资源不存在 / 路径错 | URL 是否缺 `/gen` 等前缀、是否多/少尾斜杠 |
| 400 | 参数校验失败 | Serializer 的 `validate_*`、必填字段、类型 |
| 500 | 服务器异常 | 看后端控制台异常栈（响应 msg 也会带出） |

> 本项目 HTTP 状态码恒为 200，**业务结果一定看响应体 `code`**，不要只看 HTTP status。

---

## 12. 常见坑（Python / Django / 前端）

1. **缩进错误**：混用 Tab 与空格 → `IndentationError`。
2. **可变默认参数**：`def f(x=[])` 是陷阱（本项目未使用，但你要避免）。
3. **`is None` vs `== None`**：判空用 `is None`。
4. **模型没注册 app**：新模块忘记加入 `INSTALLED_APPS` → 表找不到。
5. **`managed=False` 却执行 migrate**：不会建表，别浪费时间。
6. **URL 尾斜杠**：`APPEND_SLASH` 会把 PUT 301 成 GET，务必用无尾斜杠路径。
7. **DRF `as_view` 遮蔽 `detail`**：ViewSet 里不要定义名为 `detail` 的方法，本项目改用 `retrieve`。
8. **响应 HTTP 200**：前端判断必须以 `res.code` 为准。
9. **布尔与 0/1**：`BooleanField` 序列化为 true/false，前端 `el-switch` 严格比较会显示反向，需要转换。
10. **循环导入**：`common/auth.py` 在函数内 import 模型，避免 `apps` 与 `common` 互相依赖。
11. **前端请求前缀**：`request` 的 baseURL 已是 `/api`，业务路径不要再写 `/api`。
12. **动态路由 404**：刷新深层链接时路由守卫要用 `path` 重新解析，不能保留 404 的 `name`。
13. **代码生成后忘记注册**：`INSTALLED_APPS`、`config/urls.py`、前端文件缺一不可。
14. **菜单缓存**：菜单在登录/刷新 userinfo 时下发，改菜单后需重新登录或刷新页面。
15. **时区**：`USE_TZ=False`，`TIME_ZONE='Asia/Shanghai'`，时间字符串由 `time.strftime` 生成。

---

## 13. 进阶扩展任务（从"会读"到"会写"）

1. **给已有模块加字段**：改 SQL → 改模型 → 改 Serializer → 改前端表单/表格 → 验证。
2. **给代码生成器加控件类型**：`SysGenTableColumn.FORM_CHOICES` → `guess_form_type` → 模板/拼装代码。
3. **手写一个新模块（不用生成器）**：复制 `apps/student` 结构，改模型/路由/权限，注册菜单。
4. **加单元测试**：用 DRF `APITestCase` 覆盖登录、权限、CRUD（可用 SQLite 或测试库，注意 `managed=False` 的建表）。
5. **权限细化**：把按钮权限拆到数据行级（如仅本人可改）。
6. **导出增强**：异步导出大文件、任务队列（对应 Java 的 `@Async` + MQ）。
7. **前端主题**：阅读 `styles/index.css` 的 Element Plus CSS 变量覆盖，改主色。

---

## 14. 术语表

| 术语 | 含义 | Java 近似 |
|---|---|---|
| venv | Python 虚拟环境 | 项目级 JDK/依赖隔离 |
| pip | Python 包管理器 | Maven |
| Django | Python Web 框架 | Spring Boot |
| DRF | Django REST Framework | Spring MVC + Jackson |
| ViewSet | 一组 REST 动作的集合 | `@RestController` |
| Serializer | 序列化/反序列化 + 校验 | DTO + Jackson + Validation |
| Middleware | 请求/响应管道 | Filter |
| `request.user_info` | 认证后挂在请求上的用户对象 | `SecurityContext` 中的 Principal |
| 逻辑删除 | `is_deleted=1` 代替物理删除 | `@TableLogic` |
| 动态路由 | 登录后按菜单注册前端路由 | 前端权限路由（如 vue-admin 模板） |
| 代码生成器 | 读表生成前后端 CRUD 代码 | MyBatis-Plus Generator / 若依生成器 |

---

## 15. 自测题（答案在文末）

**选择/填空**

1. 项目 HTTP 状态码通常是多少？业务结果看什么字段？
2. `request` 封装的 baseURL 是什么？业务接口路径还能不能再写 `/api`？
3. JWT 有效期与续期阈值分别是多少？
4. `SysUser.status` 的数据库语义是什么？为什么前端要转 0/1？
5. `CrudViewSet` 的 `filter_map` 作用是什么？
6. 菜单 `menu_type` 的 M/C/F 分别代表什么？
7. 代码生成器生成的后端文件有哪些？前端文件有哪些？
8. 为什么项目没有 `migrations`？
9. 操作日志中间件如何得到"操作模块"名称？
10. 动态路由在哪一步注册？依赖后端哪个接口？

**简答**

11. 画出 `/api/system/user/list` 的调用链（至少 8 个环节）。
12. 新增一个业务表的完整步骤（从建表到菜单出现）。
13. 401/403/404/500 的排查顺序。
14. 为什么前端必须使用无尾斜杠的 URL？
15. 如何给按钮加权限（前后端各做什么）？

### 参考答案

1. 恒为 200；看 `code`。
2. `/api`；不能再写 `/api`，否则变成 `/api/api/...`。
3. 2 小时；剩余 30 分钟时下发 `X-Refresh-Token`。
4. False=正常，True=停用；前端 `el-switch` 的 `active-value=0` 严格比较 true/false 会反向。
5. 把查询参数映射到 ORM lookup（如 `username__icontains`）。
6. M=目录，C=菜单页面，F=按钮权限。
7. 后端 6 个 py/apps 文件 + README；前端 api.js + 页面 vue（共 9 个产物）。
8. 表由 SQL 手工创建，模型 `managed=False`，不需要迁移。
9. 中间件读 `resolver_match` 的 view 的 `module_name`（DRF 用 `cls.module_name`）。
10. `router/index.js` 的 `beforeEach`，依赖 `/api/auth/userinfo` 返回的 `menus`。
11. 浏览器 → Vite 代理 → `config/urls.py` → `apps/system/urls.py` → 中间件 → JWT 认证 → `PermissionCheck` → `UserViewSet.list` → `apply_filters` → `StandardPagination` → `UserListSerializer` → MySQL → `ok()` → axios 拦截器。
12. 建表 → 代码生成导入 → 配置字段 → 预览/下载 → 复制后端到 `apps/` → 注册 `INSTALLED_APPS` 与 `config/urls.py` → 复制前端文件 → 重启后端 → 重新登录/刷新菜单 → 验证 CRUD。
13. 401 查 token/用户状态；403 查角色菜单与 perm_map；404 查 URL 前缀/尾斜杠/路由注册；500 看后端异常栈。
14. Django `APPEND_SLASH` 会对缺失尾斜杠做 301，浏览器跟随 301 可能把 PUT 变成 GET，导致请求失败或被拒。
15. 后端在菜单表加按钮权限并在视图 `perm_map` 声明；前端按钮加 `v-perm="'xxx:yyy:zzz'"`；角色分配该菜单权限。

---

## 16. 学习资源

- Python 官方教程（中文）：https://docs.python.org/zh-cn/3/tutorial/
- Django 4.2 文档：https://docs.djangoproject.com/zh-hans/4.2/
- Django REST framework：https://www.django-rest-framework.org/
- Vue 3 文档（中文）：https://cn.vuejs.org/guide/
- Element Plus：https://element-plus.org/zh-CN/
- Vue Router 4：https://router.vuejs.org/zh/
- Axios：https://axios-http.com/zh/docs/intro
- MySQL 8 文档：https://dev.mysql.com/doc/refman/8.0/en/

---

## 17. 学习完成后的建议

1. 把 10 节的 12 个练习全部做一遍（尤其是第 11、12 个）。
2. 阅读 [01-项目结构与调用关系](./01-项目结构与调用关系.md) 的调用矩阵，验证你对每个文件的职责判断。
3. 用 [04-多平台部署指南](./04-多平台部署指南.md) 在虚拟机或 Docker 里完整部署一次（这是检验理解的最好方式）。
4. 尝试用代码生成器生成一个你自己业务领域的模块，并做二次开发。

> 到这里，你应当已经完成从"Java 开发者"到"能独立维护本 Django 项目"的迁移。后续遇到新需求，按"路由 → 权限 → ViewSet → Serializer → Model → 前端页面 → 菜单"的顺序定位即可。
