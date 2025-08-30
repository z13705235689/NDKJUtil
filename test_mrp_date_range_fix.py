#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试MRP日期范围自动调整功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from app.ui.mrp_viewer import MRPViewer

def test_mrp_date_range_fix():
    """测试MRP日期范围自动调整功能"""
    print("=== 测试MRP日期范围自动调整功能 ===")
    
    app = QApplication(sys.argv)
    
    # 创建MRP查看器界面
    mrp_viewer = MRPViewer()
    mrp_viewer.show()
    
    print("✓ MRP查看器界面已启动")
    print("✓ 修复后的功能：")
    print("  - 选择客户订单版本后，日期范围自动调整为订单实际时间范围")
    print("  - 计算时使用订单的实际日期范围，不显示多余的周列")
    print("  - 如果用户设置的日期超出订单范围，以订单范围为准")
    print("  - 选择'全部订单汇总'时使用用户设置的日期范围")
    
    print("\n请在界面中测试以下功能：")
    print("1. 选择不同的客户订单版本")
    print("2. 观察开始日期和结束日期是否自动调整为订单实际范围")
    print("3. 点击'生成看板'，验证是否只显示订单相关的周列")
    print("4. 选择'全部订单汇总'，验证是否使用用户设置的日期范围")
    print("5. 验证成品MRP和零部件MRP都能正确显示")
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    test_mrp_date_range_fix()
