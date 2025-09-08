#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库中的品牌和项目数据
"""

from app.db import query_all, query_one

def test_brand_and_project_data():
    """测试品牌和项目数据"""
    print("=== 测试品牌和项目数据 ===")
    
    # 1. 检查Items表中的品牌数据
    print("\n1. Items表中的品牌数据:")
    items_sql = """
        SELECT ItemId, ItemCode, CnName, Brand 
        FROM Items 
        WHERE Brand IS NOT NULL AND Brand != ''
        LIMIT 5
    """
    items = query_all(items_sql)
    for item in items:
        print(f"  ItemId: {item['ItemId']}, Code: {item['ItemCode']}, Name: {item['CnName']}, Brand: {item['Brand']}")
    
    # 2. 检查ProjectMappings表中的项目数据
    print("\n2. ProjectMappings表中的项目数据:")
    project_sql = """
        SELECT MappingId, ProjectCode, ProjectName, ItemId, ItemCode, ItemName, Brand
        FROM ProjectMappings 
        WHERE IsActive = 1
        LIMIT 5
    """
    projects = query_all(project_sql)
    for project in projects:
        print(f"  Project: {project['ProjectName']}, Item: {project['ItemCode']}, Brand: {project['Brand']}")
    
    # 3. 检查排产订单产品数据
    print("\n3. 排产订单产品数据:")
    scheduling_sql = """
        SELECT sop.ItemId, sop.ItemCode, sop.ItemName, sop.ItemSpec, sop.Brand,
               i.Brand as ItemBrand, pm.ProjectName
        FROM SchedulingOrderProducts sop
        LEFT JOIN Items i ON sop.ItemId = i.ItemId
        LEFT JOIN ProjectMappings pm ON sop.ItemId = pm.ItemId AND pm.IsActive = 1
        LIMIT 5
    """
    scheduling = query_all(scheduling_sql)
    for item in scheduling:
        print(f"  ItemId: {item['ItemId']}, Code: {item['ItemCode']}, Name: {item['ItemName']}")
        print(f"    SOP Brand: {item['Brand']}, Item Brand: {item['ItemBrand']}, Project: {item['ProjectName']}")
    
    # 4. 检查BOM数据
    print("\n4. BOM数据:")
    bom_sql = """
        SELECT bl.BomId, bl.ChildItemId, i.ItemCode, i.CnName, i.Brand,
               pm.ProjectName
        FROM BomLines bl
        JOIN Items i ON bl.ChildItemId = i.ItemId
        LEFT JOIN ProjectMappings pm ON i.ItemId = pm.ItemId AND pm.IsActive = 1
        LIMIT 5
    """
    bom_data = query_all(bom_sql)
    for item in bom_data:
        print(f"  BomId: {item['BomId']}, ItemId: {item['ChildItemId']}, Code: {item['ItemCode']}")
        print(f"    Brand: {item['Brand']}, Project: {item['ProjectName']}")
    
    # 5. 测试BOM展开
    print("\n5. 测试BOM展开:")
    from app.services.bom_service import BomService
    try:
        # 找一个有BOM的物料进行测试
        expanded = BomService.expand_bom(78, 1.0)  # ItemId 78
        print(f"  展开BOM结果数量: {len(expanded)}")
        for i, item in enumerate(expanded[:3]):  # 只显示前3个
            print(f"    {i+1}. ItemId: {item['ItemId']}, Code: {item['ItemCode']}")
            print(f"       Brand: {item.get('Brand', 'None')}, Project: {item.get('ProjectName', 'None')}")
    except Exception as e:
        print(f"  BOM展开失败: {e}")

if __name__ == "__main__":
    test_brand_and_project_data()
