#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MRP功能增强演示脚本
展示新增的客户订单选择、成品筛选和成品MRP计算功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_mrp_features():
    """演示MRP增强功能"""
    print("🎯 MRP功能增强演示")
    print("=" * 60)
    
    try:
        from app.services.mrp_service import MRPService
        
        # 设置演示参数
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        
        print(f"📅 演示日期范围: {start_date} 到 {end_date}")
        print()
        
        # 1. 演示客户订单版本选择
        print("1️⃣ 客户订单版本选择功能")
        print("-" * 40)
        versions = MRPService.get_available_import_versions()
        print(f"系统中共有 {len(versions)} 个客户订单版本:")
        
        for i, version in enumerate(versions, 1):
            print(f"   {i}. 版本 {version['ImportId']}: {version['FileName']}")
            print(f"      导入时间: {version['ImportDate']}")
            print(f"      订单数量: {version['OrderCount']}, 明细行数: {version['LineCount']}")
            print()
        
        if not versions:
            print("⚠️  没有可用的客户订单版本，请先导入订单数据")
            return
        
        # 选择第一个版本进行演示
        selected_version = versions[0]['ImportId']
        print(f"🎯 选择版本 {selected_version} 进行演示")
        print()
        
        # 2. 演示成品筛选功能
        print("2️⃣ 成品筛选功能")
        print("-" * 40)
        parent_items = MRPService.get_available_parent_items()
        print(f"系统中共有 {len(parent_items)} 个成品/半成品:")
        
        if parent_items:
            for item in parent_items[:5]:  # 只显示前5个
                print(f"   - {item['ItemCode']}: {item['CnName']} ({item['ItemType']})")
            if len(parent_items) > 5:
                print(f"   ... 还有 {len(parent_items) - 5} 个")
            print()
            
            # 演示筛选功能
            filter_example = parent_items[0]['ItemCode'][:3]  # 取前3个字符作为筛选条件
            print(f"🔍 使用筛选条件 '{filter_example}' 进行演示")
            print()
        else:
            print("⚠️  没有可用的成品数据")
            print()
        
        # 3. 演示零部件MRP计算
        print("3️⃣ 零部件MRP计算（展开BOM）")
        print("-" * 40)
        print("计算中...")
        
        result = MRPService.calculate_mrp_kanban(
            start_date, end_date,
            import_id=selected_version,
            parent_item_filter=None
        )
        
        weeks = result.get('weeks', [])
        rows = result.get('rows', [])
        
        print(f"✅ 计算完成！")
        print(f"   周数: {len(weeks)} 周 ({', '.join(weeks[:5])}{'...' if len(weeks) > 5 else ''})")
        print(f"   数据行数: {len(rows)} 行")
        
        # 统计物料类型
        item_types = {}
        for row in rows:
            item_type = row.get('ItemType', 'Unknown')
            item_types[item_type] = item_types.get(item_type, 0) + 1
        
        print(f"   物料类型分布:")
        for item_type, count in item_types.items():
            print(f"     - {item_type}: {count} 行")
        print()
        
        # 4. 演示成品MRP计算
        print("4️⃣ 成品MRP计算（直接需求）")
        print("-" * 40)
        print("计算中...")
        
        parent_result = MRPService.calculate_parent_mrp_kanban(
            start_date, end_date,
            import_id=selected_version,
            parent_item_filter=None
        )
        
        parent_weeks = parent_result.get('weeks', [])
        parent_rows = parent_result.get('rows', [])
        
        print(f"✅ 计算完成！")
        print(f"   周数: {len(parent_weeks)} 周")
        print(f"   成品数量: {len(parent_rows)} 个")
        
        if parent_rows:
            print(f"   成品列表:")
            for row in parent_rows[:5]:  # 只显示前5个
                item_code = row.get('ItemCode', 'Unknown')
                item_name = row.get('ItemName', 'Unknown')
                item_type = row.get('ItemType', 'Unknown')
                start_onhand = row.get('StartOnHand', 0)
                print(f"     - {item_code}: {item_name} ({item_type}), 期初库存: {start_onhand}")
            
            if len(parent_rows) > 5:
                print(f"     ... 还有 {len(parent_rows) - 5} 个成品")
        print()
        
        # 5. 演示筛选功能
        if parent_items:
            print("5️⃣ 成品筛选功能演示")
            print("-" * 40)
            
            # 使用第一个成品的编码作为筛选条件
            filter_code = parent_items[0]['ItemCode'][:3]
            print(f"🔍 筛选条件: '{filter_code}' (匹配以 '{filter_code}' 开头的成品)")
            
            filtered_result = MRPService.calculate_parent_mrp_kanban(
                start_date, end_date,
                import_id=selected_version,
                parent_item_filter=filter_code
            )
            
            filtered_rows = filtered_result.get('rows', [])
            print(f"✅ 筛选完成！")
            print(f"   筛选前成品数量: {len(parent_rows)} 个")
            print(f"   筛选后成品数量: {len(filtered_rows)} 个")
            
            if filtered_rows:
                print(f"   筛选后的成品:")
                for row in filtered_rows:
                    item_code = row.get('ItemCode', 'Unknown')
                    item_name = row.get('ItemName', 'Unknown')
                    print(f"     - {item_code}: {item_name}")
            print()
        
        # 6. 功能总结
        print("🎉 功能演示完成！")
        print("=" * 60)
        print("📋 新增功能总结:")
        print("✅ 客户订单版本选择 - 支持按特定订单版本计算MRP")
        print("✅ 成品筛选功能 - 支持按编码/名称筛选成品")
        print("✅ 成品MRP计算 - 直接显示成品需求，不展开BOM")
        print("✅ 零部件MRP计算 - 展开BOM计算原材料需求")
        print("✅ 多线程处理 - 避免界面卡顿")
        print("✅ 美观展示 - 支持颜色区分和动态列标题")
        print()
        print("💡 使用建议:")
        print("   - 零部件MRP：适用于采购计划和库存管理")
        print("   - 成品MRP：适用于生产计划和产能规划")
        print("   - 成品筛选：减少计算量，提高效率")
        print("   - 订单版本：精确控制需求来源")
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("🚀 启动MRP功能增强演示")
    print(f"演示时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    demo_mrp_features()
    
    print("\n" + "=" * 60)
    print("🎯 演示结束，感谢使用！")
    print("=" * 60)

if __name__ == "__main__":
    main()
