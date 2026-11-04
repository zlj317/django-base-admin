# django-base-admin 独立部署中间件部署手册

| 文档版本 | V1.0 |
| --- | --- |
| 文档状态 | 初稿 |
| 编写日期 | 2026-11-04 |
| 适配系统 | django-base-admin（Django + Vue3 + MySQL） |
| 适用环境 | Windows（开发）/ 银河麒麟 Linux（生产，含 x86 与飞腾 ARM 架构） |

---

## 0. 文档说明

本文档整理 `django-base-admin` 系统运行**需要单独部署的外部中间件与服务**，每项均给出：用途、必装性、依赖、**下载地址（官网 + 国内高速镜像）**、**Windows 与银河麒麟双环境部署详细步骤**、验证方法、与系统的对接配置。

> **核心原则**：以下中间件均为**独立进程/独立服务**，不可内嵌打包进 Django 后端；系统通过 HTTP 接口、网络协议、或 Docker 编排与其对接。

---

## 1. 中间件总览

| 序号 | 中间件 | 用途 | 必装性 | 端口 |
| --- | --- | --- | --- | --- |
| 1 | MySQL 8.0.21 | 主数据库 | 必装（本机已有则跳过） | 3306 |
| 2 | Redis | Celery 调度 + 消息中心 + 实时推送 | 必装 | 6379 |
| 3 | kkFileView | 文件只读在线预览 | 推荐必装 | 8012 |
| 4 | OnlyOffice DocumentServer | Office 在线协同编辑 | 按需（需编辑功能） | 80/443 |
| 5 | MinIO | 附件对象存储 | 可选（替代本地存储） | 9000/9001 |
| 6 | Nginx | 前后端反向代理、静态托管 | 生产推荐 | 80/443 |
| 7 | Celery Worker | 后台异步/定时任务进程 | 必装（随项目启动） | 无（进程） |

---

# 1. MySQL 8.0.21

## 1.1 说明
系统主数据库。当前本地实例 `192.168.0.76:3306`（root/root）已有则跳过本节。

## 1.2 下载地址
- 官网：https://dev.mysql.com/downloads/installer/（MSI 图形安装）
- 国内镜像（ZIP 免安装包，推荐）：
  - 清华：https://mirrors.tuna.tsinghua.edu.cn/mysql/downloads/MySQL-8.0/
  - 中科大：https://mirrors.ustc.edu.cn/mysql-ftp/Downloads/MySQL-8.0/
  - 华为云：https://mirrors.huaweicloud.com/mysql/Downloads/MySQL-8.0/
  - 阿里云：https://mirrors.aliyun.com/mysql/Downloads/MySQL-8.0/
- Linux 麒麟（银河麒麟 V10，aarch64/amd64 均有官方源）：建议用系统仓库或麒麟软件源安装

## 1.3 Windows 部署
```bat
:: 1. 解压 mysql-8.0.21-winx64.zip 到 D:\mysql-8.0.21（路径不能含中文/空格）
:: 2. 管理员 cmd，初始化（生成 data 目录）
D:\mysql-8.0.21\bin\mysqld --initialize-insecure
:: 3. 注册服务
D:\mysql-8.0.21\bin\mysqld install MySQL80
:: 4. 启动
net start MySQL80
:: 5. 登录并改 root 密码
D:\mysql-8.0.21\bin\mysql -u root -p
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root';
ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY 'root';
FLUSH PRIVILEGES;
```

## 1.4 银河麒麟 Linux 部署（含 ARM）
```bash
# 方式A：麒麟软件源安装（最省事，自动适配 aarch64/amd64）
sudo apt-get install -y mysql-server   # 或 mysql-server-8.0
# 方式B：官网二进制包安装（跨架构）
wget https://mirrors.huaweicloud.com/mysql/Downloads/MySQL-8.0/mysql-8.0.21-linux-${ARCH}.tar.gz
# ${ARCH}=aarch64(飞腾ARM) 或 x86_64

# 初始化与启动（麒麟 systemd）
sudo systemctl enable --now mysqld
# 默认 root 初始密码在 /var/log/mysqld.log，登录后修改
```

## 1.5 验证
```bash
mysql -V
mysql -u root -p -e "SELECT VERSION();"
```

## 1.6 对接配置（Django settings.py）
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gen_admin', 'USER': 'root', 'PASSWORD': 'root',
        'HOST': '192.168.0.76', 'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}
```

---

# 2. Redis

## 2.1 说明
作为 Celery 的消息代理（broker）与结果后端，同时支撑消息中心、Django Channels 实时推送、报表实时查询的通道。

## 2.2 下载地址
- 官网：https://redis.io/download/
- Linux 源码：https://download.redis.io/releases/redis-7.2.x.tar.gz
- 国内镜像：
  - 清华：https://mirrors.tuna.tsinghua.edu.cn/redis/
  - 华为云：https://mirrors.huaweicloud.com/redis/
- Windows（非官方，开发用）：
  - https://github.com/tporadowski/redis/releases
  - 或 Memurai（商业授权）：https://www.memurai.com/

## 2.3 Windows 部署
```bat
:: 下载 redis-x64-7.2.x.zip 解压
:: 启动（前台）
redis-server.exe redis.windows.conf
:: 或注册为服务
redis-server --service-install redis.windows.conf --service-name Redis
redis-server --service-start
:: 客户端验证
redis-cli.exe ping   :: 返回 PONG
```

## 2.4 银河麒麟 Linux 部署（含 ARM）
```bash
# 源码编译安装（ARM/x86 通用）
sudo apt-get install -y build-essential tcl
wget https://download.redis.io/releases/redis-7.2.4.tar.gz
tar xzf redis-7.2.4.tar.gz && cd redis-7.2.4
make && make install
# 以守护方式启动
redis-server /usr/local/etc/redis.conf --daemonize yes
redis-cli ping
```
> 生产建议：设置 `requirepass` 密码、开启 `appendonly yes`。

## 2.5 验证
```bash
redis-cli ping   # PONG
redis-cli info server
```

## 2.6 对接配置（Django settings.py）
```python
CELERY_BROKER_URL = 'redis://192.168.0.76:6379/0'
CELERY_RESULT_BACKEND = 'redis://192.168.0.76:6379/1'
CHANNEL_LAYERS = {
    'default': {'BACKEND': 'channels_redis.core.RedisChannelLayer',
                'CONFIG': {'hosts': ['redis://192.168.0.76:6379/2']}},
}
```

---

# 3. kkFileView（文件在线预览服务）

## 3.1 说明
独立 Java（SpringBoot）服务，负责 PDF、Office、图片、文本、CAD 等文件的只读在线预览。Django 通过 HTTP 传文件 URL 调用，前端 iframe 嵌入预览页面。**需单独部署，不可内嵌。**

## 3.2 下载地址
- 官方 GitHub 发布页：https://github.com/kekingcn/kkFileView/releases
- 国内 Gitee 镜像（加速）：https://gitee.com/kekingcn/kkFileView （Release 内下载）
- Windows 包：`kkFileView-4.x-windows-xxx.zip`
- Linux 包：`kkFileView-4.x-linux-xxx.tar.gz`

> 提示：kkFileView 官方 Linux 包以 x86 为主；**飞腾 ARM（aarch64）环境需自带 JRE(ARM版) + 源码编译，或选用支持 ARM 的版本**，麒麟系统请预先安装 ARM 版 OpenJDK。

## 3.3 环境要求
- JDK 1.8+（推荐 8/11；ARM 用 aarch64 JDK）
- 依赖 LibreOffice（Office 转 PDF，Linux 必须装）：`sudo apt-get install -y libreoffice`

## 3.4 Windows 部署
```bat
:: 1. 解压 kkFileView-4.x-windows.zip
:: 2. 进入 bin 目录，启动
startup.bat
:: 3. 验证
浏览器访问 http://127.0.0.1:8012/index.html
```

## 3.5 银河麒麟 Linux 部署
```bash
# 安装依赖
sudo apt-get install -y openjdk-8-jre-headless libreoffice
# 解压 linux 包
tar -xzf kkFileView-4.x-linux-*.tar.gz -C /opt/kkfileview
cd /opt/kkfileview/bin
chmod +x *.sh
# 前台启动测试
./startup.sh
# 生产后台运行
nohup ./startup.sh > /var/log/kkfileview.log 2>&1 &
```

## 3.6 验证
```bash
curl http://192.168.0.76:8012/index.html
curl "http://192.168.0.76:8012/onlinePreview?url=<编码后的文件访问地址>"
```

## 3.7 对接配置（附件管理）
```python
KKFILEVIEW_URL = 'http://192.168.0.76:8012'
# 系统通过拼接：KKFILEVIEW_URL + '/onlinePreview?url=' + quote(文件下载URL)
```

---

# 4. OnlyOffice DocumentServer（Office 在线协同编辑）

## 4.1 说明
独立文档转换 + 协同编辑服务（内含 Nginx/Node/PostgreSQL/Redis），负责 docx/xlsx/pptx 在线编辑，基于 WOPI 协议与 Django 交互，保存时回调回写文件。**重量级服务，必须独立部署。**

> 推荐 Docker 部署（生产标准）。飞腾 ARM 使用 ARM64 专用镜像。

## 4.2 下载地址
- 官方发布：https://github.com/ONLYOFFICE/DocumentServer/releases
- Docker Hub 镜像：https://hub.docker.com/r/onlyoffice/documentserver
- ARM64 镜像：`onlyoffice/documentserver-aa`
- Linux 安装包（x86 deb/rpm）：https://www.onlyoffice.com/download-docs.aspx
- 国内镜像加速（拉取 Docker 镜像）：
  - 配置 registry-mirror（阿里云/华为云镜像加速器），或在 `docker pull` 后打标签

## 4.3 银河麒麟 Linux + Docker 部署（推荐）
```bash
# 安装 Docker（麒麟软件源或官方）
sudo apt-get install -y docker.io docker-compose

# 拉取镜像（ARM 用 -aa；x86 用 documentserver）
sudo docker pull onlyoffice/documentserver:latest        # x86
# sudo docker pull onlyoffice/documentserver-aa:latest   # 飞腾ARM

# 启动
sudo docker run -i -t -d -p 80:80 \
  --restart=always --name onlyoffice \
  -e JWT_ENABLED=true \
  -e JWT_SECRET=your_secret_key \
  -v /opt/onlyoffice/logs:/var/log/onlyoffice \
  -v /opt/onlyoffice/data:/var/www/onlyoffice/Data \
  -v /opt/onlyoffice/lib:/var/lib/onlyoffice \
  onlyoffice/documentserver:latest
```
> 也可用 docker-compose.yml 一键编排（附录提供模板）。

## 4.4 Windows 部署
- OnlyOffice 官方不提供 Windows 原生安装包，**Windows 开发机建议用 Docker Desktop**（需开启 WSL2），拉取同一镜像启动；或仅连远程 Linux 部署的 OnlyOffice 服务。

## 4.5 验证
```bash
curl http://192.168.0.76/       # 出现 OnlyOffice 欢迎页
curl http://192.168.0.76/healthcheck   # 返回 {"status":"ok"}
```

## 4.6 对接配置（附件管理 + 系统）
```python
ONLYOFFICE_SERVER_URL = 'http://192.168.0.76'   # 注意不含端口（默认80）
ONLYOFFICE_JWT_SECRET = 'your_secret_key'       # 必须与启动时的 JWT_SECRET 一致
ONLYOFFICE_CALLBACK_URL = 'http://django后端地址/api/file/onlyoffice/callback'
```

## 4.7 关键注意
- **OnlyOffice 必须能反向访问到 Django 的文件下载/回调接口**（双向网络通），否则编辑保存失败；
- 若 Django 在 `192.168.0.76`，OnlyOffice 与 Django 之间需相互可达；
- 飞腾 ARM 务必使用 `-aa` 镜像，普通 x86 镜像无法运行。

---

# 5. MinIO（附件对象存储，可选）

## 5.1 说明
当附件存储切换为对象存储模式（替代本地磁盘）时部署，预留扩展，国产化友好。

## 5.2 下载地址
- 官方下载（跨架构）：https://dl.min.io/server/minio/release/
  - Linux x86：`linux-amd64/minio`
  - Linux ARM：`linux-arm64/minio`
  - Windows：`windows-amd64/minio.exe`
- 国内镜像：https://mirrors.huaweicloud.com/minio/ （部分版本）
- Docker：https://hub.docker.com/r/minio/minio

## 5.3 Windows 部署
```bat
minio.exe server D:\minio-data --console-address :9001
:: 浏览器 http://127.0.0.1:9001  默认 minioadmin/minioadmin
```

## 5.4 银河麒麟 Linux 部署
```bash
wget https://dl.min.io/server/minio/release/linux-arm64/minio   # ARM
# 或 linux-amd64/minio（x86）
chmod +x minio && mv minio /usr/local/bin/
export MINIO_ROOT_USER=minioadmin
export MINIO_ROOT_PASSWORD=minioadmin
nohup minio server /data/minio --console-address :9001 > /var/log/minio.log 2>&1 &
```

## 5.5 验证
```bash
# 使用 mc 客户端
mc alias set local http://192.168.0.76:9000 minioadmin minioadmin
mc ls local
```

## 5.6 对接配置
```python
# 附件模块 storage_type=minio 时启用
MINIO_ENDPOINT = '192.168.0.76:9000'
MINIO_ACCESS_KEY = 'minioadmin'
MINIO_SECRET_KEY = 'minioadmin'
MINIO_BUCKET = 'django-base-admin'
```

---

# 6. Nginx（反向代理，生产推荐）

## 6.1 说明
生产环境统一入口：前端静态资源托管 + `/api` 反向代理到 Django、`/ws` 代理到 Django Channels、静态媒体文件代理到 kkFileView 等。

## 6.2 下载地址
- 官网：https://nginx.org/en/download.html
- 国内镜像：
  - 华为云：https://mirrors.huaweicloud.com/nginx/
  - 清华：https://mirrors.tuna.tsinghua.edu.cn/nginx/
- 麒麟：`sudo apt-get install -y nginx`

## 6.3 Windows 部署
```bat
:: 解压 nginx-1.24.x.zip
start nginx            :: 启动
nginx -t               :: 测试配置
nginx -s reload        :: 重载
```

## 6.4 银河麒麟 Linux 部署
```bash
sudo apt-get install -y nginx
sudo systemctl enable --now nginx
sudo nginx -t && sudo nginx -s reload
```

## 6.5 核心配置要点（conf 示例）
```nginx
server {
    listen 80;
    location /api/  { proxy_pass http://127.0.0.1:8000/; proxy_set_header Host $host; }
    location /ws/   { proxy_pass http://127.0.0.1:8001/; proxy_http_version 1.1;
                      proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; }
    location /      { root /opt/frontend/dist; try_files $uri $uri/ /index.html; }
}
```

---

# 7. Celery Worker（后台任务进程）

## 7.1 说明
非独立中间件，而是与 Django 项目一起的后台任务进程（异步 + 定时任务），需单独以进程方式启动（不随 runserver 自动运行）。定时任务模块、消息推送、报表定时生成、附件过期清理都依赖它。

## 7.2 部署步骤（Windows / 麒麟通用）
```bash
# 安装依赖（requirements.txt 已含 celery）
pip install celery redis

# 启动 Worker（消费队列）
cd backend
celery -A config worker -l info

# 启动定时任务调度 Beat（单独进程）
celery -A config beat -l info

# 生产后台运行（麒麟）
nohup celery -A config worker -l info > /var/log/celery_worker.log 2>&1 &
nohup celery -A config beat  -l info > /var/log/celery_beat.log 2>&1 &
```
> Windows 开发调试：Worker 前台运行即可；Beat 与 Worker 分开两个终端。

## 7.3 验证
- Worker 日志出现 `ready.` 即就绪；
- 在【定时任务】模块立即执行一次任务，观察任务日志状态为成功。

---

## 附录 A：部署顺序建议

| 顺序 | 中间件 | 说明 |
| --- | --- | --- |
| 1 | MySQL | 先建库建表 |
| 2 | Redis | 供 Celery/Channels |
| 3 | Django + Celery | 主程序 + Worker |
| 4 | Vue 前端构建 | npm run build |
| 5 | Nginx | 统一入口 |
| 6 | kkFileView | 预览 |
| 7 | OnlyOffice | 在线编辑（按需） |
| 8 | MinIO | 对象存储（按需） |

---

## 附录 B：OnlyOffice + kkFileView 一键 docker-compose.yml（模板）

```yaml
version: '3'
services:
  onlyoffice:
    image: onlyoffice/documentserver:latest   # 飞腾ARM改用 onlyoffice/documentserver-aa:latest
    container_name: onlyoffice
    ports: ["80:80"]
    environment:
      - JWT_ENABLED=true
      - JWT_SECRET=your_secret_key
    volumes:
      - /opt/onlyoffice/logs:/var/log/onlyoffice
      - /opt/onlyoffice/data:/var/www/onlyoffice/Data
      - /opt/onlyoffice/lib:/var/lib/onlyoffice
    restart: always
```

---

## 附录 C：国产化（飞腾 ARM + 银河麒麟）注意事项汇总

| 中间件 | ARM 注意事项 |
| --- | --- |
| MySQL | 麒麟源自动装 aarch64 版，或下载 aarch64 二进制 |
| Redis | 源码编译通用（ARM 编译无问题） |
| kkFileView | 官方包以 x86 为主，ARM 需 ARM 版 JRE + 源码编译 |
| OnlyOffice | **必须用 `documentserver-aa` ARM64 镜像** |
| MinIO | 下载 `linux-arm64` 版本 |
| Nginx | 麒麟源自动装 aarch64 版 |
