#!/usr/bin/env python
"""Django 管理入口。"""
import os  # 读写环境变量，用于指定配置模块
import sys  # 取命令行参数，交给 Django 分发子命令


def main():
    """命令行入口：设置配置模块并交由 Django 执行对应的管理命令。"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 未显式指定时默认使用本项目配置
    try:
        from django.core.management import execute_from_command_line  # 延迟导入，未装依赖时给出可读提示
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django，请先安装依赖：pip install -r requirements.txt"
        ) from exc  # 保留原始异常链，便于定位环境问题
    execute_from_command_line(sys.argv)  # 按 argv 分发到 migrate / runserver / check 等命令


if __name__ == '__main__':
    main()  # 仅直接运行本文件时执行，被当作模块导入时不会触发
