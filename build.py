#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NDKJ_MES 打包脚本
一键打包为exe文件
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build():
    """清理之前的构建文件"""
    print("🧹 正在清理之前的构建文件...")
    
    dirs_to_clean = ["build", "dist", "release"]
    cleaned_count = 0
    
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            print(f"   📁 删除 {dir_name} 目录...")
            shutil.rmtree(dir_name)
            cleaned_count += 1
        else:
            print(f"   ✅ {dir_name} 目录不存在，跳过")
    
    # 清理spec文件
    spec_file = Path("NDKJ_MES.spec")
    if spec_file.exists():
        print(f"   📄 删除 {spec_file.name} 文件...")
        spec_file.unlink()
        cleaned_count += 1
    else:
        print(f"   ✅ {spec_file.name} 文件不存在，跳过")
    
    print(f"✅ 清理完成，共清理了 {cleaned_count} 个文件/目录")

def build_exe():
    """执行打包命令"""
    print("🚀 开始打包...")
    print("📋 打包参数:")
    print("   - 单文件打包 (--onefile)")
    print("   - 无控制台窗口 (--windowed)")
    print("   - 优化级别 2 (--optimize=2)")
    print("   - 包含数据文件: schema.sql, 模板文件等")
    print("   - 隐藏导入: sqlite3, pandas, openpyxl 等")
    print("   - 排除模块: matplotlib, scipy, PIL 等")
    print()
    
    cmd = [
        "pyinstaller",
        "--onefile",                    # 打包成单个文件
        "--windowed",                   # 无控制台窗口
        "--name=MRP",                   # 可执行文件名
        "--strip",                      # 去除调试符号
        "--optimize=2",                 # 优化级别
        # 数据文件
        "--add-data=app/schema.sql;app", # SQL文件
        "--add-data=BOM导入模板.xlsx;.", # BOM导入模板
        "--add-data=BOM导入示例.xlsx;.", # BOM导入示例
        "--add-data=bom.csv;.",         # BOM CSV文件
        "--add-data=app/ui/materia_management.xlsx;app/ui", # 物料导入模板
        # 隐藏导入
        "--hidden-import=sqlite3",
        "--hidden-import=pandas",
        "--hidden-import=openpyxl",
        "--hidden-import=app",
        "--hidden-import=app.ui",
        "--hidden-import=app.services",
        "--hidden-import=app.db",
        "--hidden-import=app.utils",
        "--hidden-import=app.utils.resource_path",
        # 排除不需要的模块
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=PIL",
        "--exclude-module=tkinter",
        "--exclude-module=PyQt5",
        "--exclude-module=PyQt6",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=notebook",
        "--exclude-module=sphinx",
        "--exclude-module=docutils",
        "--exclude-module=setuptools",
        "--exclude-module=pip",
        "--exclude-module=wheel",
        "--exclude-module=distutils",
        "--exclude-module=test",
        "--exclude-module=unittest",
        "--exclude-module=pytest",
        "--exclude-module=doctest",
        "--exclude-module=pdb",
        "--exclude-module=profile",
        "--exclude-module=cProfile",
        "--exclude-module=timeit",
        "--exclude-module=trace",
        # 主程序入口
        "app/ui/ui_main.py"
    ]
    
    print("⚙️  正在执行 PyInstaller...")
    print("⏳ 这可能需要几分钟时间，请耐心等待...")
    print()
    
    # 实时显示进度，不使用 capture_output
    result = subprocess.run(cmd, encoding='utf-8', errors='ignore')
    
    print()
    if result.returncode == 0:
        print("✅ 打包成功！")
        return True
    else:
        print("❌ 打包失败！")
        print("请检查上面的错误信息")
        return False

def create_release_package():
    """创建发布包"""
    print("📦 正在创建发布包...")
    
    # 创建release目录
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    print("   📁 创建 release 目录")
    
    # 复制exe文件
    exe_source = Path("dist/MRP.exe")
    exe_target = release_dir / "MRP.exe"
    
    if exe_source.exists():
        print(f"   📄 复制可执行文件: {exe_target.name}")
        shutil.copy2(exe_source, exe_target)
        print(f"   ✅ 复制完成")
    else:
        print(f"   ❌ 找不到 {exe_source}")
        return False
    
    # 复制模板文件
    print("   📋 复制模板文件...")
    template_files = [
        ("BOM导入模板.xlsx", "BOM导入模板.xlsx"),
        ("BOM导入示例.xlsx", "BOM导入示例.xlsx"),
        ("bom.csv", "BOM.CSV"),
        ("app/ui/materia_management.xlsx", "物料导入模板.xlsx"),
        ("库存导入模板.csv", "库存导入模板.csv")
    ]
    
    copied_templates = 0
    for src, dst in template_files:
        src_path = Path(src)
        dst_path = release_dir / dst
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"     ✅ {dst}")
            copied_templates += 1
        else:
            print(f"     ⚠️  {src} 不存在，跳过")
    
    print(f"   📊 共复制了 {copied_templates} 个模板文件")
    
    # 创建使用说明
    print("   📖 创建使用说明文档...")
    readme_content = """MRP 制造执行系统 v1.0

使用说明：
1. 双击 MRP.exe 启动系统
2. 系统使用内置数据库，数据存储在exe同目录的mes.db文件中
3. 数据会自动保存，关闭程序后数据不会丢失
4. 支持数据库备份和恢复功能
5. 支持Excel和TXT文件导入客户订单
6. 支持BOM导入功能

功能模块：
- 物料管理：管理原材料、半成品、成品、包装材料，支持启用/禁用状态
- BOM管理：管理物料清单结构，支持导入导出、历史记录、状态检查
- 库存管理：库存余额、日常登记、库存流水、库存导入，自动过滤禁用物料
- 客户订单管理：管理客户订单，支持版本控制、看板显示、CW日期对应
- MRP计算：基于订单和BOM进行物料需求计划计算，支持综合MRP、零部件MRP、成品MRP
- 数据库管理：数据库备份、恢复、初始化

导入功能：
- 物料导入：支持Excel和CSV格式，提供模板下载
- 库存导入：支持Excel和CSV格式，自动关联仓库
- BOM导入：支持Excel和CSV格式
- 客户订单导入：支持TXT格式

注意事项：
1. 系统使用内置数据库，数据存储在exe同目录的mes.db文件中
2. 数据会自动保存，关闭程序后数据不会丢失
3. 如需备份数据，请使用数据库备份功能
4. 导入前请使用提供的模板格式
5. 系统支持多仓库管理
6. 物料导入支持下载模板功能
7. 库存导入支持CSV格式，提供模板文件

新功能特性：
1. 物料启用/禁用：物料管理支持启用和禁用状态，禁用的物料不会出现在库存和BOM中
2. BOM历史记录：BOM管理支持查看所有操作历史，包括创建、修改、删除记录
3. BOM状态检查：自动检查BOM有效性，失效的BOM会显示在列表底部
4. 综合MRP计算：新增综合MRP计算类型，结合成品库存和零部件库存计算
5. 客户订单看板：支持CW和日期对应显示，看板日期加粗显示
6. 库存自动清理：系统会自动清理禁用物料在仓库中的关联
7. 进度显示：MRP计算时显示进度条，避免误以为程序卡住
8. 数据验证：增强数据验证，防止负数输入和格式错误

数据库管理：
- 内置数据库：数据存储在exe同目录的mes.db文件中，自动保存
- 备份功能：可以将数据库备份到指定位置
- 恢复功能：可以从备份文件恢复数据库
- 清空功能：可以清空整个数据库（自动备份后清空）
- 数据库信息：在数据库管理页面显示当前数据库类型和大小

模板文件说明：
- 物料导入模板.xlsx：物料基础信息导入模板
- 库存导入模板.csv：库存数据导入模板（CSV格式）
- BOM导入模板.xlsx：BOM结构导入模板
- BOM导入示例.xlsx：BOM导入示例文件
- BOM.CSV：BOM导入CSV格式示例

技术支持：如有问题请联系技术支持
"""
    
    readme_file = release_dir / "使用说明.txt"
    readme_file.write_text(readme_content, encoding="utf-8")
    print("   ✅ 使用说明文档创建完成")
    
    # 创建启动脚本
    print("   🚀 创建启动脚本...")
    bat_content = """@echo off
chcp 65001 >nul
echo ========================================
echo        MRP 制造执行系统
echo ========================================
echo.
echo 正在启动系统...
start "" "MRP.exe"
echo.
echo 系统启动完成！
pause
"""
    
    bat_file = release_dir / "启动系统.bat"
    bat_file.write_text(bat_content, encoding="utf-8")
    print("   ✅ 启动脚本创建完成")
    
    # 创建数据库备份脚本
    print("   💾 创建数据库备份脚本...")
    backup_content = """@echo off
chcp 65001 >nul
echo ========================================
echo        MRP 数据库备份
echo ========================================
echo.

if not exist "mes.db" (
    echo 错误：找不到数据库文件 mes.db
    echo 请确保在正确的目录下运行此脚本
    pause
    exit /b 1
)

set backup_name=mes_backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.db
set backup_name=%backup_name: =0%

echo 正在备份数据库...
copy "mes.db" "backup\\%backup_name%" >nul

if exist "backup\\%backup_name%" (
    echo 备份成功：backup\\%backup_name%
) else (
    echo 备份失败！
)

echo.
pause
"""
    
    # 创建backup目录
    backup_dir = release_dir / "backup"
    backup_dir.mkdir(exist_ok=True)
    print("   📁 创建 backup 目录")
    
    backup_file = release_dir / "数据库备份.bat"
    backup_file.write_text(backup_content, encoding="utf-8")
    print("   ✅ 数据库备份脚本创建完成")
    
    print("✅ 发布包创建完成")
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 MRP 制造执行系统 - 打包工具")
    print("=" * 60)
    print("📋 打包内容:")
    print("   • 物料管理：支持启用/禁用状态")
    print("   • BOM管理：支持导入导出、历史记录、状态检查")
    print("   • 库存管理：自动过滤禁用物料")
    print("   • 客户订单管理：CW日期对应显示")
    print("   • MRP计算：综合MRP、零部件MRP、成品MRP")
    print("   • 数据库管理：备份、恢复、初始化")
    print("=" * 60)
    
    # 清理构建
    print("\n📁 步骤 1/3: 清理构建文件...")
    clean_build()
    print("✅ 清理完成")
    
    # 执行打包
    print("\n⚙️  步骤 2/3: 执行打包...")
    if not build_exe():
        print("❌ 打包失败")
        return
    
    # 检查文件大小
    exe_path = Path("dist/MRP.exe")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"📊 可执行文件大小: {size_mb:.1f} MB")
    
    # 创建发布包
    print("\n📦 步骤 3/3: 创建发布包...")
    if not create_release_package():
        print("❌ 创建发布包失败")
        return
    
    print("\n" + "=" * 60)
    print("🎉 打包完成！")
    print("=" * 60)
    print("📁 发布包位置: release/")
    print("📄 可执行文件: release/MRP.exe")
    print("📋 使用说明: release/使用说明.txt")
    print("🚀 启动脚本: release/启动系统.bat")
    print("💾 备份脚本: release/数据库备份.bat")
    print("=" * 60)
    print("✨ 现在可以将 release 文件夹分发给用户使用！")
    print("=" * 60)

if __name__ == "__main__":
    main()
