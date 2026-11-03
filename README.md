# 代码生成型后台管理系统

**简体中文** | [English](#english)

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Vue](https://img.shields.io/badge/Vue-3-42B883?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-2.x-409EFF)](https://element-plus.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)

一个基于 **Django 4.2 + DRF + MySQL 8 + Vue 3 + Element Plus** 的后台管理系统。
内置完整的平台基础模块（用户、角色、菜单、部门、字典、参数、日志）与**代码生成器**：读取数据库业务表 → 可视化配置字段 → 预览/下载前后端代码 ZIP → 自动注册菜单，一键获得带 Excel 导入导出的 CRUD 页面。

---

## 功能截图

| 登录页 | 首页仪表盘 |
|---|---|
| <img src="docs/images/01-login.png" alt="登录页" width="100%"> | <img src="docs/images/02-dashboard.png" alt="首页仪表盘" width="100%"> |

| 用户管理 | 角色管理 |
|---|---|
| <img src="docs/images/03-user.png" alt="用户管理" width="100%"> | <img src="docs/images/04-role.png" alt="角色管理" width="100%"> |

| 菜单管理 | 部门管理 |
|---|---|
| <img src="docs/images/05-menu.png" alt="菜单管理" width="100%"> | <img src="docs/images/06-dept.png" alt="部门管理" width="100%"> |

| 字典管理 | 参数配置 |
|---|---|
| <img src="docs/images/07-dict.png" alt="字典管理" width="100%"> | <img src="docs/images/08-config.png" alt="参数配置" width="100%"> |

| 操作日志 | 登录日志 |
|---|---|
| <img src="docs/images/09-operlog.png" alt="操作日志" width="100%"> | <img src="docs/images/10-loginlog.png" alt="登录日志" width="100%"> |

| 代码生成 - 表列表 | 代码生成 - 字段配置 |
|---|---|
| <img src="docs/images/11-gen-list.png" alt="代码生成列表" width="100%"> | <img src="docs/images/12-gen-edit.png" alt="字段配置" width="100%"> |

| 代码生成 - 建表 SQL | 字典数据维护 |
|---|---|
| <img src="docs/images/14-gen-ddl.png" alt="建表 SQL" width="100%"> | <img src="docs/images/15-dict-data.png" alt="字典数据" width="100%"> |

| 生成模块示例（学生信息表） |
|---|
| <img src="docs/images/13-student.png" alt="生成模块示例" width="100%"> |

---

## 功能特性

- **认证与权限**：自研 JWT（Token 2 小时，剩余 30 分钟静默续期）、bcrypt 密码、按钮级权限 `v-perm`、后端 `PermissionCheck` 校验、`admin` 通配权限。
- **动态菜单与路由**：登录后由后端下发菜单树，前端动态注册路由；菜单类型支持目录（M）/页面（C）/按钮（F）。
- **平台基础模块**：用户管理（角色分配、重置密码、状态开关）、角色管理（分配菜单）、菜单管理、部门树、字典管理（类型 + 数据）、参数配置、操作日志、登录日志。
- **代码生成器**：读取 `information_schema` → 导入业务表 → 字段级配置（表单类型、查询方式、字典、列表/查询/必填/导入/导出）→ 预览 9 个产物 → DDL 查看 → ZIP 下载 → 自动注册菜单与按钮权限。
- **生成模块能力**：标准 CRUD、条件查询、分页、批量删除、Excel 模板下载、批量导入（错误行提示）、条件导出。
- **工程规范**：统一响应 `{code, msg, data}`（HTTP 状态恒 200）、统一分页、全局异常处理、逻辑删除 `is_deleted`、操作日志中间件、`managed=False` 的 SQL-first 表结构、Element Plus 主题定制。
- **中英文文档**：本 README 提供中英文切换，`docs/` 下提供结构图、功能说明、运行部署与零基础学习路线。

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Django 4.2 + Django REST Framework | `ViewSet` + 自定义路由，统一响应与全局异常 |
| 认证 | 自研 JWT + bcrypt | `Authorization: Bearer`，`X-Refresh-Token` 静默续期 |
| 数据库 | MySQL 8 | 表由 SQL 脚本创建，模型 `managed=False` |
| 前端 | Vue 3（Composition API）+ Vite 5 | 无 Pinia，使用 `reactive` 轻量状态 |
| UI | Element Plus 2.x | 全局 CSS 变量主题覆盖 |
| 路由/请求 | vue-router 4 + axios | 动态路由、请求/响应拦截器 |

## 目录结构

```
django-base-admin/
├─ backend/                 # Django 后端
│  ├─ manage.py             # 管理入口（runserver / init_db / check）
│  ├─ config/               # settings、全局路由、wsgi/asgi
│  ├─ common/               # JWT、权限、分页、响应、异常、中间件、通用 CRUD
│  ├─ apps/
│  │  ├─ system/            # 用户/角色/菜单/部门/字典/配置/日志/认证
│  │  ├─ gen/               # 代码生成器（引擎 + 模板）
│  │  └─ student/           # 生成模块示例（学生信息表）
│  └─ core/management/commands/init_db.py   # 建库建表与初始化数据
├─ frontend/                # Vue3 前端
│  └─ src/
│     ├─ router/            # 静态路由 + 动态路由
│     ├─ store/auth.js      # 登录态、权限、菜单
│     ├─ utils/request.js   # axios 封装
│     ├─ layout/            # 侧边栏、导航栏、布局
│     └─ views/             # 登录、首页、system/*、gen/*、student
└─ docs/                    # 需求、建表 SQL 与 01~05 总结文档、截图
```

## 快速开始

> 详细步骤见 [docs/03-运行启动指南.md](docs/03-运行启动指南.md)。

**1. 准备数据库**

```sql
CREATE DATABASE gen_admin DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

执行 `docs/后台管理系统-初始化建表SQL.sql` 创建系统表；修改 `backend/config/settings.py` 中的 `DATABASES` 连接信息。

**2. 启动后端**

```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate    macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py init_db        # 初始化菜单/按钮权限/管理员密码（注意 SQL_FILE 路径）
python manage.py runserver 0.0.0.0:8000
```

**3. 启动前端**

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173，/api 自动代理到 8000
```

**4. 登录**

| 账号 | 密码 | 说明 |
|---|---|---|
| `admin` | `123456` | 超级管理员，拥有全部权限 |

## 文档索引

| 编号 | 文档 | 内容 |
|---|---|---|
| 00 | [文档导航](docs/00-文档导航.md) | 全部文档索引与推荐阅读路径 |
| 01 | [项目结构与调用关系](docs/01-项目结构与调用关系.md) | 架构图、时序图、**文件级调用矩阵**、数据库关系 |
| 02 | [功能说明文档](docs/02-功能说明文档.md) | 全部功能、接口清单、权限与业务规则 |
| 03 | [运行启动指南](docs/03-运行启动指南.md) | 环境、建库、初始化、启动、验证、FAQ |
| 04 | [多平台部署指南](docs/04-多平台部署指南.md) | Linux / Windows / Docker / 云平台部署 |
| 05 | [Java 开发者零基础学习路线](docs/05-Java开发者零基础学习路线.md) | Python/Django 与 Java/Spring 对照、分阶段读码与练习 |

## 代码生成器使用流程

1. 在 MySQL 中创建业务表；
2. 进入 **系统工具 → 代码生成**，点击「导入数据表」；
3. 在字段配置页调整表单类型、查询方式、字典、列表/查询/导入/导出等；
4. 「预览」查看 9 个生成文件，「DDL」查看建表语句；
5. 「下载」得到 ZIP，按包内 `README-部署说明.txt` 复制到 `backend/apps/` 与 `frontend/src/`；
6. 注册 `INSTALLED_APPS`、`config/urls.py`，重启后端并刷新菜单；
7. 新菜单出现，即可使用 CRUD、导入、导出与操作日志。

## 部署

支持 Linux（Nginx + Gunicorn + systemd）、Windows Server（Waitress + Nginx/IIS）、Docker / docker-compose，以及阿里云/腾讯云等云平台与对象存储/CDN 前端托管。完整配置与命令见 [docs/04-多平台部署指南.md](docs/04-多平台部署指南.md)。

## 许可

本项目仅用于学习与内部项目参考，未附带开源许可证文件；如需开源发布请自行补充 LICENSE。

---

<h1 id="english">English</h1>

[简体中文](#代码生成型后台管理系统) | **English**

# Code-Generating Admin System

An admin system built with **Django 4.2 + DRF + MySQL 8 + Vue 3 + Element Plus**. It ships with a complete platform foundation (users, roles, menus, departments, dictionaries, configs, logs) and a **code generator**: read a MySQL business table → configure fields in the UI → preview/download a ZIP of backend & frontend code → menus auto-register, giving you a full CRUD page with Excel import/export in one step.

## Screenshots

| Login | Dashboard |
|---|---|
| <img src="docs/images/01-login.png" alt="Login" width="100%"> | <img src="docs/images/02-dashboard.png" alt="Dashboard" width="100%"> |

| User Management | Role Management |
|---|---|
| <img src="docs/images/03-user.png" alt="Users" width="100%"> | <img src="docs/images/04-role.png" alt="Roles" width="100%"> |

| Menu Management | Department Management |
|---|---|
| <img src="docs/images/05-menu.png" alt="Menus" width="100%"> | <img src="docs/images/06-dept.png" alt="Departments" width="100%"> |

| Dictionary Management | System Config |
|---|---|
| <img src="docs/images/07-dict.png" alt="Dictionaries" width="100%"> | <img src="docs/images/08-config.png" alt="Configs" width="100%"> |

| Operation Log | Login Log |
|---|---|
| <img src="docs/images/09-operlog.png" alt="Operation log" width="100%"> | <img src="docs/images/10-loginlog.png" alt="Login log" width="100%"> |

| Code Generator - Tables | Code Generator - Field Config |
|---|---|
| <img src="docs/images/11-gen-list.png" alt="Gen tables" width="100%"> | <img src="docs/images/12-gen-edit.png" alt="Field config" width="100%"> |

| Code Generator - DDL | Dictionary Data |
|---|---|
| <img src="docs/images/14-gen-ddl.png" alt="DDL" width="100%"> | <img src="docs/images/15-dict-data.png" alt="Dictionary data" width="100%"> |

| Generated Module (Students) |
|---|
| <img src="docs/images/13-student.png" alt="Generated module" width="100%"> |

## Features

- **Auth & permissions**: custom JWT (2-hour token, silent refresh when 30 minutes remain), bcrypt passwords, button-level `v-perm` directive, backend `PermissionCheck`, wildcard permission for `admin`.
- **Dynamic menus & routes**: menus are delivered by the backend after login and registered as Vue routes at runtime (directory / page / button types).
- **Platform modules**: users (role assignment, password reset, status toggle), roles (menu assignment), menus, department tree, dictionaries (types + data), system configs, operation logs, login logs.
- **Code generator**: inspect `information_schema` → import business tables → per-field configuration (form widget, query type, dictionary, list/query/required/import/export) → preview 9 artifacts → view DDL → download ZIP → auto-register menus and button permissions.
- **Generated module capabilities**: standard CRUD, conditional search, pagination, batch delete, Excel template download, batch import with row-level error messages, conditional export.
- **Engineering conventions**: unified response `{code, msg, data}` (HTTP status always 200), unified pagination, global exception handler, logical delete `is_deleted`, operation-log middleware, SQL-first schema with `managed=False`, custom Element Plus theme.
- **Bilingual docs**: this README supports Chinese/English switching; the `docs/` folder contains architecture, feature, run/deploy and beginner guides.

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend | Django 4.2 + Django REST Framework | `ViewSet` + hand-written routes, unified response & exceptions |
| Auth | Custom JWT + bcrypt | `Authorization: Bearer`, `X-Refresh-Token` silent renewal |
| Database | MySQL 8 | Schema created by SQL script, models use `managed=False` |
| Frontend | Vue 3 (Composition API) + Vite 5 | No Pinia; a lightweight `reactive` store |
| UI | Element Plus 2.x | Global CSS variable theme overrides |
| Routing / HTTP | vue-router 4 + axios | Dynamic routes, request/response interceptors |

## Quick Start

> Full steps: [docs/03-运行启动指南.md](docs/03-运行启动指南.md) (Chinese).

**1. Database**

```sql
CREATE DATABASE gen_admin DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Run `docs/后台管理系统-初始化建表SQL.sql`, then update `DATABASES` in `backend/config/settings.py`.

**2. Backend**

```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate    macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py init_db
python manage.py runserver 0.0.0.0:8000
```

**3. Frontend**

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173, proxies /api to port 8000
```

**4. Login**: `admin / 123456`

## Documentation

| No. | Document | Content |
|---|---|---|
| 00 | [Doc index](docs/00-文档导航.md) | Index and recommended reading paths |
| 01 | [Architecture & call graph](docs/01-项目结构与调用关系.md) | Architecture diagrams, sequences, file-level call matrix, DB relations |
| 02 | [Feature specification](docs/02-功能说明文档.md) | All features, API list, permissions and rules |
| 03 | [Run guide](docs/03-运行启动指南.md) | Setup, initialization, startup, verification, FAQ |
| 04 | [Deployment guide](docs/04-多平台部署指南.md) | Linux / Windows / Docker / cloud deployment |
| 05 | [Learning path for Java developers](docs/05-Java开发者零基础学习路线.md) | Python/Django vs Java/Spring mapping, staged code-reading plan |

## Code Generator Workflow

1. Create a business table in MySQL.
2. In **System Tools → Code Generator**, click "Import tables".
3. Adjust each field: widget type, query type, dictionary, list/search/required/import/export.
4. "Preview" the 9 generated files; "DDL" shows the table definition.
5. "Download" the ZIP and follow `README-部署说明.txt` to copy files into `backend/apps/` and `frontend/src/`.
6. Register the new app in `INSTALLED_APPS` and `config/urls.py`, restart the backend and refresh the menu.
7. The new menu appears with CRUD, import, export and operation logging ready.

## Deployment

Linux (Nginx + Gunicorn + systemd), Windows Server (Waitress + Nginx/IIS), Docker / docker-compose, and cloud platforms with object storage/CDN for the frontend. See [docs/04-多平台部署指南.md](docs/04-多平台部署指南.md) for complete configs and commands.

## License

This project is provided for learning and internal reference only. No license file is included; add your own LICENSE before open-sourcing.
