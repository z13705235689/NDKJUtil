#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOM数据导入脚本
根据CSV文件导入物料和BOM数据
"""

import csv
import pandas as pd
from pathlib import Path
from app.db import get_conn, execute, query_one

def import_bom_data():
    """导入BOM数据"""
    print("开始导入BOM数据...")
    
    # 读取CSV文件
    csv_file = Path(__file__).parent / 'bom.csv'
    if not csv_file.exists():
        print(f"错误：找不到CSV文件 {csv_file}")
        return False
    
    try:
        # 使用pandas读取CSV
        df = pd.read_csv(csv_file, header=None)
        print(f"成功读取CSV文件，共 {len(df)} 行数据")
        
        # 第一行：成品名称和编码
        # 第二行：成品对应的规格
        # 第一列：原材料名称
        # 第二列：原材料的编码和规格
        
        # 获取成品信息（第一行和第二行）
        finished_goods = []
        for col in range(2, len(df.columns)):  # 从第3列开始（跳过前两列）
            item_code = df.iloc[0, col]  # 第一行：成品编码
            item_spec = df.iloc[1, col]  # 第二行：成品规格
            if pd.notna(item_code) and str(item_code).strip():
                finished_goods.append({
                    'code': str(item_code).strip(),
                    'spec': str(item_spec).strip() if pd.notna(item_spec) else '',
                    'col_index': col
                })
        
        print(f"找到 {len(finished_goods)} 个成品")
        
        # 获取原材料信息（第一列和第二列）
        raw_materials = []
        for row in range(2, len(df)):  # 从第3行开始（跳过前两行）
            item_name = df.iloc[row, 0]  # 第一列：原材料名称
            item_spec = df.iloc[row, 1]  # 第二列：原材料规格
            if pd.notna(item_name) and str(item_name).strip():
                raw_materials.append({
                    'name': str(item_name).strip(),
                    'spec': str(item_spec).strip() if pd.notna(item_spec) else '',
                    'row_index': row
                })
        
        print(f"找到 {len(raw_materials)} 个原材料")
        
        # 导入物料数据
        print("\n开始导入物料数据...")
        
        # 先导入成品
        finished_item_ids = {}
        for fg in finished_goods:
            item_id = import_item(
                item_code=fg['code'],
                item_name=fg['code'],  # 使用编码作为名称
                item_spec=fg['spec'],
                item_type='成品',
                unit='个'
            )
            if item_id:
                finished_item_ids[fg['col_index']] = item_id
                print(f"导入成品: {fg['code']} (ID: {item_id})")
        
        # 再导入原材料
        raw_item_ids = {}
        for rm in raw_materials:
            # 生成原材料编码（使用规格作为编码）
            item_code = rm['spec'] if rm['spec'] else f"RM_{rm['row_index']}"
            item_id = import_item(
                item_code=item_code,
                item_name=rm['name'],
                item_spec=rm['spec'],
                item_type='RM',
                unit='个'
            )
            if item_id:
                raw_item_ids[rm['row_index']] = item_id
                print(f"导入原材料: {rm['name']} - {rm['spec']} (ID: {item_id})")
        
        # 导入BOM数据
        print("\n开始导入BOM数据...")
        
        for fg in finished_goods:
            fg_item_id = finished_item_ids.get(fg['col_index'])
            if not fg_item_id:
                continue
                
            # 创建BOM头
            bom_name = f"BOM_{fg['code']}"
            bom_id = create_bom_header(
                bom_name=bom_name,
                parent_item_id=fg_item_id,
                rev="1.0"
            )
            
            if bom_id:
                print(f"创建BOM: {bom_name} (ID: {bom_id})")
                
                # 添加BOM明细
                for rm in raw_materials:
                    rm_item_id = raw_item_ids.get(rm['row_index'])
                    if not rm_item_id:
                        continue
                    
                    # 获取数量（交叉点的值）
                    qty = df.iloc[rm['row_index'], fg['col_index']]
                    if pd.notna(qty) and str(qty).strip() and float(str(qty).strip()) > 0:
                        qty_value = float(str(qty).strip())
                        
                        # 创建BOM明细
                        create_bom_line(
                            bom_id=bom_id,
                            child_item_id=rm_item_id,
                            qty_per=qty_value,
                            unit='个'
                        )
                        print(f"  - 添加明细: {rm['name']} x {qty_value}")
        
        print("\nBOM数据导入完成！")
        return True
        
    except Exception as e:
        print(f"导入BOM数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def import_item(item_code, item_name, item_spec, item_type, unit):
    """导入物料"""
    try:
        with get_conn() as conn:
            # 检查是否已存在
            cursor = conn.execute(
                "SELECT ItemId FROM Items WHERE ItemCode = ?", 
                (item_code,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有物料
                conn.execute("""
                    UPDATE Items SET 
                        CnName = ?, ItemSpec = ?, ItemType = ?, Unit = ?, UpdatedDate = CURRENT_TIMESTAMP
                    WHERE ItemCode = ?
                """, (item_name, item_spec, item_type, unit, item_code))
                return existing[0]
            else:
                # 创建新物料
                cursor = conn.execute("""
                    INSERT INTO Items (ItemCode, CnName, ItemSpec, ItemType, Unit, Quantity, SafetyStock, IsActive)
                    VALUES (?, ?, ?, ?, ?, 1.0, 0, 1)
                """, (item_code, item_name, item_spec, item_type, unit))
                conn.commit()
                return cursor.lastrowid
                
    except Exception as e:
        print(f"导入物料失败 {item_code}: {e}")
        return None

def create_bom_header(bom_name, parent_item_id, rev):
    """创建BOM头"""
    try:
        with get_conn() as conn:
            # 检查是否已存在
            cursor = conn.execute(
                "SELECT BomId FROM BomHeaders WHERE BomName = ? AND Rev = ?", 
                (bom_name, rev)
            )
            existing = cursor.fetchone()
            
            if existing:
                return existing[0]
            else:
                # 创建新BOM
                cursor = conn.execute("""
                    INSERT INTO BomHeaders (BomName, ParentItemId, Rev, EffectiveDate, BomType, IsActive)
                    VALUES (?, ?, ?, DATE('now'), 'Production', 1)
                """, (bom_name, parent_item_id, rev))
                conn.commit()
                return cursor.lastrowid
                
    except Exception as e:
        print(f"创建BOM头失败 {bom_name}: {e}")
        return None

def create_bom_line(bom_id, child_item_id, qty_per, unit):
    """创建BOM明细"""
    try:
        with get_conn() as conn:
            # 检查是否已存在
            cursor = conn.execute(
                "SELECT LineId FROM BomLines WHERE BomId = ? AND ChildItemId = ?", 
                (bom_id, child_item_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有明细
                conn.execute("""
                    UPDATE BomLines SET QtyPer = ?, Unit = ?
                    WHERE BomId = ? AND ChildItemId = ?
                """, (qty_per, unit, bom_id, child_item_id))
            else:
                # 创建新明细
                conn.execute("""
                    INSERT INTO BomLines (BomId, ChildItemId, QtyPer, Unit)
                    VALUES (?, ?, ?, ?)
                """, (bom_id, child_item_id, qty_per, unit))
            
            conn.commit()
            return True
                
    except Exception as e:
        print(f"创建BOM明细失败: {e}")
        return False

def verify_import():
    """验证导入结果"""
    print("\n验证导入结果...")
    
    try:
        with get_conn() as conn:
            # 检查物料数量
            cursor = conn.execute("SELECT COUNT(*) FROM Items")
            item_count = cursor.fetchone()[0]
            print(f"物料总数: {item_count}")
            
            # 检查BOM数量
            cursor = conn.execute("SELECT COUNT(*) FROM BomHeaders")
            bom_count = cursor.fetchone()[0]
            print(f"BOM总数: {bom_count}")
            
            # 检查BOM明细数量
            cursor = conn.execute("SELECT COUNT(*) FROM BomLines")
            bom_line_count = cursor.fetchone()[0]
            print(f"BOM明细总数: {bom_line_count}")
            
            # 显示成品物料
            print("\n成品物料:")
            cursor = conn.execute("SELECT ItemCode, CnName, ItemSpec FROM Items WHERE ItemType = 'FG'")
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]} ({row[2]})")
            
            # 显示原材料
            print("\n原材料:")
            cursor = conn.execute("SELECT ItemCode, CnName, ItemSpec FROM Items WHERE ItemType = 'RM'")
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]} ({row[2]})")
                
    except Exception as e:
        print(f"验证导入结果失败: {e}")

def main():
    """主函数"""
    print("=" * 50)
    print("BOM数据导入工具")
    print("=" * 50)
    
    # 导入数据
    if import_bom_data():
        # 验证结果
        verify_import()
        print("\n数据导入完成！")
    else:
        print("\n数据导入失败！")

if __name__ == "__main__":
    main()
