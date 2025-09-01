#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NDKJ_MES 一键打包脚本
自动打包为exe文件，包含所有必要的依赖和数据文件
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_dependencies():
    """检查必要的依赖是否安装"""
    try:
        import PySide6
        print("✅ PySide6 已安装")
    except ImportError:
        print("❌ PySide6 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PySide6"], check=True)
    
    try:
        import pyinstaller
        print("✅ PyInstaller 已安装")
    except ImportError:
        print("❌ PyInstaller 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

def check_files():
    """检查必要的文件是否存在"""
    required_files = [
        "app/ui/ui_main.py",
        "mes.db",
        "app/schema.sql",
        "bom.csv"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少必要文件: {missing_files}")
        return False
    
    print("✅ 所有必要文件存在")
    return True

def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            print(f"🧹 清理 {dir_name} 目录...")
            shutil.rmtree(dir_name)
    
    # 清理spec文件
    spec_file = Path("NDKJ_MES.spec")
    if spec_file.exists():
        spec_file.unlink()
        print("🧹 清理 spec 文件")

def build_exe():
    """执行打包命令"""
    print("🚀 开始打包...")
    
    cmd = [
        "pyinstaller",
        "--onefile",                    # 打包成单个文件
        "--windowed",                   # 无控制台窗口
        "--name=NDKJ_MES",              # 可执行文件名
        "--add-data=mes.db;.",          # 数据库文件
        "--add-data=app/schema.sql;app", # SQL文件
        "--add-data=bom.csv;.",         # BOM数据文件
        # 隐藏导入
        "--hidden-import=PySide6",
        "--hidden-import=sqlite3",
        "--hidden-import=app.services.bom_service",
        "--hidden-import=app.services.customer_order_service",
        "--hidden-import=app.services.inventory_service",
        "--hidden-import=app.services.item_service",
        "--hidden-import=app.services.mrp_service",
        "--hidden-import=app.services.warehouse_service",
        "--hidden-import=app.ui.bom_management",
        "--hidden-import=app.ui.customer_order_management",
        "--hidden-import=app.ui.database_management",
        "--hidden-import=app.ui.inventory_management",
        "--hidden-import=app.ui.materia_management",
        "--hidden-import=app.ui.mrp_viewer",
        "--hidden-import=app.ui.ui_main",
        # 主程序入口
        "app/ui/ui_main.py"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ 打包成功！")
        return True
    else:
        print("❌ 打包失败！")
        print("错误信息:")
        print(result.stderr)
        return False

def create_release_package():
    """创建发布包"""
    print("📦 创建发布包...")
    
    # 创建release目录
    release_dir = Path("release")
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()
    
    # 复制exe文件
    exe_source = Path("dist/NDKJ_MES.exe")
    exe_target = release_dir / "NDKJ_MES.exe"
    
    if exe_source.exists():
        shutil.copy2(exe_source, exe_target)
        print(f"✅ 复制 {exe_target}")
    else:
        print(f"❌ 找不到 {exe_source}")
        return False
    
    # 创建使用说明
    readme_content = """NDKJ_MES 制造执行系统

使用说明：
1. 双击 NDKJ_MES.exe 启动系统
2. 系统会自动创建数据库文件
3. 支持数据库备份和恢复功能
4. 支持TXT文件导入客户订单

功能模块：
- 物料管理
- BOM管理  
- 库存管理
- 客户订单管理
- MRP计算
- 数据库管理

技术支持：如有问题请联系技术支持
"""
    
    readme_file = release_dir / "使用说明.txt"
    readme_file.write_text(readme_content, encoding="utf-8")
    print("✅ 创建使用说明")
    
    # 创建启动脚本
    bat_content = """@echo off
echo 正在启动 NDKJ_MES 系统...
start "" "NDKJ_MES.exe"
"""
    
    bat_file = release_dir / "启动系统.bat"
    bat_file.write_text(bat_content, encoding="utf-8")
    print("✅ 创建启动脚本")
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("NDKJ_MES 一键打包工具")
    print("=" * 50)
    
    # 检查依赖
    print("\n1. 检查依赖...")
    check_dependencies()
    
    # 检查文件
    print("\n2. 检查文件...")
    if not check_files():
        print("❌ 文件检查失败，请确保所有必要文件存在")
        return
    
    # 清理构建
    print("\n3. 清理构建...")
    clean_build()
    
    # 执行打包
    print("\n4. 执行打包...")
    if not build_exe():
        print("❌ 打包失败")
        return
    
    # 创建发布包
    print("\n5. 创建发布包...")
    if not create_release_package():
        print("❌ 创建发布包失败")
        return
    
    print("\n" + "=" * 50)
    print("🎉 打包完成！")
    print("📁 发布包位置: release/")
    print("📄 可执行文件: release/NDKJ_MES.exe")
    print("📋 使用说明: release/使用说明.txt")
    print("🚀 启动脚本: release/启动系统.bat")
    print("=" * 50)

if __name__ == "__main__":
    main()
