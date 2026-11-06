#!/usr/bin/env python
"""Django 管理入口。"""
# ============================== 文件说明 ==============================
# 作用：命令行入口，所有 manage.py 子命令（runserver/migrate/check/...）都经此分发。
# 被谁加载：开发者或部署脚本直接执行 python manage.py <command>。
# 关键约定：
#   1) 通过 DJANGO_SETTINGS_MODULE 指定配置模块，默认回退到 config.settings；
#   2) Django 管理命令采用延迟导入，未安装依赖时给出可读的安装提示；
#   3) 本文件不承载业务逻辑，自定义命令放在 core/management/commands/ 下；
#   4) if __name__ == '__main__' 保护，保证被当作模块导入时不会误执行命令。
# 常用命令：runserver 启动开发服务 / migrate 应用迁移 / check 自检 / init_db 初始化数据。
# 参数约定：sys.argv 原样透传，第一个元素是脚本名，第二个是子命令，其余为命令选项。
# 编码说明：文件声明可执行 shebang，Linux/macOS 下可直接 ./manage.py 运行。
# 标准库导入：os 用于设置环境变量，sys 用于读取命令行参数
import os  # 读写环境变量，用于指定配置模块
# 与 os 同属标准库，二者均为纯内置模块，导入无第三方依赖
import sys  # 取命令行参数，交给 Django 分发子命令


# 主函数：Django 官方脚手架约定的入口，便于被外部脚本复用或测试调用
def main():
    """命令行入口：设置配置模块并交由 Django 执行对应的管理命令。"""
    # 函数职责：完成三件事——选配置、导入命令框架、按 argv 执行命令
    # 使用 setdefault：外部已设置 DJANGO_SETTINGS_MODULE 时以外部为准（测试/多环境场景）
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 未显式指定时默认使用本项目配置
    # try 包裹延迟导入：Django 未安装时会抛出 ImportError，在此转换成带安装指引的提示
    try:
        # 延迟导入管理命令分发器：只有真正执行命令时才需要 Django 已安装
        from django.core.management import execute_from_command_line  # 延迟导入，未装依赖时给出可读提示
    # 捕获导入失败：exc 保留原始错误，便于判断是缺依赖还是环境损坏
    except ImportError as exc:
        # 抛出自定义异常：提示用户安装依赖，而不是暴露难懂的模块找不到堆栈
        raise ImportError(
            # 异常文案：直接给出可复制的安装命令，降低新环境上手成本
            "无法导入 Django，请先安装依赖：pip install -r requirements.txt"
        ) from exc  # 保留原始异常链，便于定位环境问题
    # 执行命令：Django 内部按子命令名查找并调用对应 Command，如 check/migrate
    execute_from_command_line(sys.argv)  # 按 argv 分发到 migrate / runserver / check 等命令
    # 执行完毕后由 Django 命令自身决定返回值/退出码，main 不再额外处理


# 入口保护：仅直接运行本文件时执行 main，被 python -m 或测试导入时不触发
# 这样单元测试或打包工具导入本模块时不会产生副作用
# 注意：Windows 下通过 python manage.py 调用，Linux/macOS 也可依赖 shebang 直接执行
if __name__ == '__main__':
    main()  # 仅直接运行本文件时执行，被当作模块导入时不会触发
