# NDKJ_MES 制造执行系统

## 📦 项目简介

NDKJ_MES是一个基于Python和PySide6开发的制造执行系统，提供完整的生产管理功能。

## 🚀 快速开始

### 使用exe版本（推荐）
1. 进入 `release` 目录
2. 双击运行 `NDKJ_MES.exe`
3. 或使用 `启动系统.bat` 启动

### 使用源码版本```bash
# 安装依赖
pip install PySide6

# 运行程序
python app/ui/ui_main.py
```

## 📋 功能模块

- **物料管理** - 管理物料信息
- **BOM管理** - 管理产品结构
- **库存管理** - 管理库存信息
- **客户订单管理** - 管理客户订单
- **MRP计算** - 物料需求计划
- **数据库管理** - 备份恢复数据库

## 💾 数据库功能

### 备份数据库
1. 点击"数据库管理"模块
2. 点击工具栏"备份数据库"按钮
3. 选择备份位置和文件名

### 恢复数据库
1. 点击"数据库管理"模块
2. 点击工具栏"恢复数据库"按钮
3. 选择要恢复的备份文件
4. 确认恢复操作

## 📁 项目结构

```
NDKJ_MES/
├── app/                    # 应用程序源码
│   ├── db.py              # 数据库管理
│   ├── schema.sql         # 数据库结构
│   ├── services/          # 业务服务
│   └── ui/                # 用户界面
├── release/               # 发布包
│   ├── NDKJ_MES.exe       # 可执行文件
│   ├── 使用说明.txt       # 使用说明
│   └── 启动系统.bat       # 启动脚本
├── dist/                  # 构建输出
├── mes.db                 # 数据库文件
├── bom.csv                # BOM数据
└── README.md              # 项目说明
```

## 🔧 技术栈

- **Python 3.10+**
- **PySide6** - GUI框架
- **SQLite** - 数据库
- **PyInstaller** - 打包工具

## 📊 系统要求

- **操作系统**: Windows 10/11
- **内存**: 建议 4GB 以上
- **存储**: 至少 100MB 可用空间

## 🛠️ 开发说明

### 环境设置
```bash
# 创建虚拟环境
python -m venv myenv
myenv\Scripts\activate

# 安装依赖
pip install PySide6
```

### 打包exe
```bash
# 安装PyInstaller
pip install pyinstaller

# 打包
pyinstaller --onefile --windowed --name=NDKJ_MES app/ui/ui_main.py
```

## 📝 更新日志

### v1.0.0
- ✅ 完成基础功能开发
- ✅ 实现数据库备份恢复
- ✅ 完成exe打包
- ✅ 通过基础测试

## 📞 技术支持

如有问题或建议，请联系技术支持。

---

**NDKJ_MES 系统 v1.0.0**  
*制造执行系统 - 让生产管理更简单*
