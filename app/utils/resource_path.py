# app/utils/resource_path.py
# -*- coding: utf-8 -*-
"""
资源路径工具模块
用于处理打包后的资源文件路径
"""

import os
import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径
    
    Args:
        relative_path: 相对于项目根目录的路径
        
    Returns:
        资源文件的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe，从临时目录获取
        base_path = sys._MEIPASS
        return os.path.join(base_path, relative_path)
    else:
        # 如果是开发环境，从项目根目录获取
        project_root = Path(__file__).parent.parent.parent
        return str(project_root / relative_path)


def get_app_root() -> Path:
    """
    获取应用程序根目录
    
    Returns:
        应用程序根目录路径
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        return Path(sys.executable).parent
    else:
        # 如果是开发环境
        return Path(__file__).parent.parent.parent


def ensure_directory(path: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
    """
    Path(path).mkdir(parents=True, exist_ok=True)
