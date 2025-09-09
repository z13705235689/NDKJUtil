# app/services/scheduling_order_service.py
# -*- coding: utf-8 -*-
"""
新的排产订单服务类
- 支持创建排产订单，选择需要排产的成品
- 支持设置初始日期，自动计算30天排产周期
- 提供排产看板数据
- 集成MRP计算功能
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, date
from collections import defaultdict

from app.db import query_all, query_one, get_conn
from app.services.bom_service import BomService


class SchedulingOrderService:
    """新的排产订单服务类"""
    
    @staticmethod
    def create_scheduling_order(order_name: str, start_date: str, end_date: str = None,
                              created_by: str = "System", remark: str = "") -> Tuple[bool, str, int]:
        """创建新的排产订单"""
        try:
            # 如果没有提供结束日期，则计算结束日期（初始日期+30天）
            if end_date is None:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_dt = start_dt + timedelta(days=30)
                end_date = end_dt.strftime("%Y-%m-%d")
            
            with get_conn() as conn:
                cur = conn.execute("""
                    INSERT INTO SchedulingOrders 
                    (OrderName, StartDate, EndDate, Status, CreatedBy, Remark)
                    VALUES (?, ?, ?, 'Draft', ?, ?)
                """, (order_name, start_date, end_date, created_by, remark))
                order_id = cur.lastrowid
                conn.commit()
            return True, f"成功创建排产订单：{order_name}", order_id
        except Exception as e:
            return False, f"创建排产订单失败: {str(e)}", 0
    
    @staticmethod
    def get_scheduling_orders() -> List[Dict]:
        """获取所有排产订单"""
        try:
            sql = """
                SELECT OrderId, OrderName, StartDate, EndDate, Status, 
                       CreatedBy, CreatedDate, UpdatedBy, UpdatedDate, Remark
                FROM SchedulingOrders
                ORDER BY CreatedDate DESC
            """
            rows = query_all(sql)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取排产订单失败: {e}")
            return []
    
    @staticmethod
    def get_scheduling_order_by_id(order_id: int) -> Optional[Dict]:
        """根据ID获取排产订单"""
        try:
            sql = """
                SELECT OrderId, OrderName, StartDate, EndDate, Status, 
                       CreatedBy, CreatedDate, UpdatedBy, UpdatedDate, Remark
                FROM SchedulingOrders
                WHERE OrderId = ?
            """
            row = query_one(sql, (order_id,))
            return dict(row) if row else None
        except Exception as e:
            print(f"获取排产订单失败: {e}")
            return None
    
    @staticmethod
    def update_scheduling_order(order_id: int, order_name: str = None, 
                              start_date: str = None, end_date: str = None, status: str = None, 
                              updated_by: str = "System", remark: str = None) -> Tuple[bool, str]:
        """更新排产订单"""
        try:
            update_fields = []
            params = []
            
            if order_name is not None:
                update_fields.append("OrderName = ?")
                params.append(order_name)
            if start_date is not None:
                update_fields.append("StartDate = ?")
                params.append(start_date)
                
                # 如果没有提供结束日期，则自动计算
                if end_date is None:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end_dt = start_dt + timedelta(days=30)
                    end_date = end_dt.strftime("%Y-%m-%d")
            
            if end_date is not None:
                update_fields.append("EndDate = ?")
                params.append(end_date)
            if status is not None:
                update_fields.append("Status = ?")
                params.append(status)
            if remark is not None:
                update_fields.append("Remark = ?")
                params.append(remark)
            
            update_fields.append("UpdatedBy = ?")
            update_fields.append("UpdatedDate = CURRENT_TIMESTAMP")
            params.extend([updated_by, order_id])
            
            sql = f"""
                UPDATE SchedulingOrders 
                SET {', '.join(update_fields)}
                WHERE OrderId = ?
            """
            
            with get_conn() as conn:
                conn.execute(sql, params)
                conn.commit()
            return True, "更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
    
    @staticmethod
    def delete_scheduling_order(order_id: int) -> Tuple[bool, str]:
        """删除排产订单（级联删除相关数据）"""
        try:
            with get_conn() as conn:
                conn.execute("DELETE FROM SchedulingOrderMRP WHERE OrderId = ?", (order_id,))
                conn.execute("DELETE FROM SchedulingOrderLines WHERE OrderId = ?", (order_id,))
                conn.execute("DELETE FROM SchedulingOrderProducts WHERE OrderId = ?", (order_id,))
                conn.execute("DELETE FROM SchedulingOrders WHERE OrderId = ?", (order_id,))
                conn.commit()
            return True, "删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"
    
    @staticmethod
    def get_available_products() -> List[Dict]:
        """获取可排产的成品列表（有BOM的成品）"""
        try:
            sql = """
                SELECT DISTINCT 
                    i.ItemId, i.ItemCode, i.CnName, i.ItemSpec, i.Brand,
                    pm.ProjectCode, pm.ProjectName
                FROM Items i
                JOIN BomHeaders bh ON i.ItemId = bh.ParentItemId
                LEFT JOIN ProjectMappings pm ON i.ItemId = pm.ItemId
                WHERE i.ItemType IN ('FG', 'SFG') AND i.IsActive = 1 AND bh.IsActive = 1
                ORDER BY i.ItemType, i.ItemCode
            """
            rows = query_all(sql)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取可排产成品失败: {e}")
            return []
    
    @staticmethod
    def add_products_to_order(order_id: int, product_ids: List[int], 
                             created_by: str = "System") -> Tuple[bool, str]:
        """向排产订单添加产品"""
        try:
            with get_conn() as conn:
                for item_id in product_ids:
                    # 获取产品信息
                    product_info = SchedulingOrderService._get_product_info(item_id)
                    if not product_info:
                        continue
                    
                    # 插入产品记录
                    conn.execute("""
                        INSERT OR IGNORE INTO SchedulingOrderProducts
                        (OrderId, ItemId, ItemCode, ItemName, ItemSpec, Brand, ProjectName)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        order_id, item_id, product_info["ItemCode"], 
                        product_info["CnName"], product_info["ItemSpec"] or "",
                        product_info["Brand"] or "", product_info["ProjectName"] or ""
                    ))
                
                conn.commit()
            return True, f"成功添加 {len(product_ids)} 个产品到排产订单"
        except Exception as e:
            return False, f"添加产品失败: {str(e)}"
    
    @staticmethod
    def remove_product_from_order(order_id: int, item_id: int) -> Tuple[bool, str]:
        """从排产订单中移除产品"""
        try:
            with get_conn() as conn:
                # 删除相关的排产明细
                conn.execute("DELETE FROM SchedulingOrderLines WHERE OrderId = ? AND ItemId = ?", 
                           (order_id, item_id))
                # 删除产品记录
                conn.execute("DELETE FROM SchedulingOrderProducts WHERE OrderId = ? AND ItemId = ?", 
                           (order_id, item_id))
                conn.commit()
            return True, "移除产品成功"
        except Exception as e:
            return False, f"移除产品失败: {str(e)}"
    
    @staticmethod
    def get_order_products(order_id: int) -> List[Dict]:
        """获取排产订单的产品列表"""
        try:
            sql = """
                SELECT ProductId, OrderId, ItemId, ItemCode, ItemName, 
                       ItemSpec, Brand, ProjectName, CreatedDate
                FROM SchedulingOrderProducts
                WHERE OrderId = ?
                ORDER BY CreatedDate
            """
            rows = query_all(sql, (order_id,))
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取订单产品失败: {e}")
            return []
    
    @staticmethod
    def get_scheduling_kanban_data(order_id: int) -> Dict:
        """
        获取排产看板数据
        返回格式：
        {
            "order_info": {...},
            "date_range": ["2024-01-01", "2024-01-02", ...],
            "products": [
                {
                    "ItemId": 1,
                    "ItemCode": "FG-001",
                    "ItemName": "产品A",
                    "ItemSpec": "规格A",
                    "Brand": "品牌A",
                    "ProjectName": "项目A",
                    "cells": {
                        "2024-01-01": 100,
                        "2024-01-02": 150,
                        ...
                    }
                }
            ]
        }
        """
        try:
            # 获取排产订单信息
            order_info = SchedulingOrderService.get_scheduling_order_by_id(order_id)
            if not order_info:
                return {"error": "排产订单不存在"}
            
            # 生成日期范围（30天）
            start_date = datetime.strptime(order_info["StartDate"], "%Y-%m-%d").date()
            end_date = datetime.strptime(order_info["EndDate"], "%Y-%m-%d").date()
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)
            
            # 首先获取订单中的所有产品
            products_sql = """
                SELECT sop.ItemId, sop.ItemCode, sop.ItemName, sop.ItemSpec, 
                       COALESCE(i.Brand, '') as Brand,
                       COALESCE(pm.ProjectName, '') as ProjectName,
                       i.ItemType
                FROM SchedulingOrderProducts sop
                LEFT JOIN Items i ON sop.ItemId = i.ItemId
                LEFT JOIN ProjectMappings pm ON sop.ItemId = pm.ItemId AND pm.IsActive = 1
                WHERE sop.OrderId = ?
                ORDER BY sop.ItemCode
            """
            product_rows = query_all(products_sql, (order_id,))
            
            if not product_rows:
                return {"error": "订单中没有产品"}
            
            # 获取已有的排产明细数据
            lines_sql = """
                SELECT ItemId, ProductionDate, PlannedQty
                FROM SchedulingOrderLines
                WHERE OrderId = ?
            """
            lines_rows = query_all(lines_sql, (order_id,))
            
            # 将排产数据转换为字典便于查找
            lines_data = {}
            for row in lines_rows:
                row_dict = dict(row)  # 转换为字典
                key = f"{row_dict['ItemId']}_{row_dict['ProductionDate']}"
                lines_data[key] = float(row_dict["PlannedQty"])
            
            # 构建产品数据
            products = []
            for product_row in product_rows:
                # 将sqlite3.Row转换为字典
                row_dict = dict(product_row)
                
                item_id = row_dict["ItemId"]
                product_data = {
                    "ItemId": item_id,
                    "ItemCode": row_dict["ItemCode"],
                    "ItemName": row_dict["ItemName"],
                    "ItemSpec": row_dict["ItemSpec"] or "",
                    "Brand": row_dict["Brand"] or "",
                    "ProjectName": row_dict["ProjectName"] or "",
                    "ItemType": row_dict["ItemType"] or "",
                    "cells": {}
                }
                
                # 为每个日期设置排产数量（从已有数据或默认为0）
                for date_str in date_range:
                    key = f"{item_id}_{date_str}"
                    product_data["cells"][date_str] = lines_data.get(key, 0.0)
                
                products.append(product_data)
            
            return {
                "order_info": order_info,
                "date_range": date_range,
                "products": products
            }
        except Exception as e:
            print(f"获取排产看板数据失败: {e}")
            return {"error": f"获取排产看板数据失败: {str(e)}"}
    
    @staticmethod
    def update_scheduling_line(order_id: int, item_id: int, production_date: str, 
                              planned_qty: float, updated_by: str = "System") -> Tuple[bool, str]:
        """更新排产明细"""
        try:
            with get_conn() as conn:
                # 检查是否存在记录
                existing = conn.execute("""
                    SELECT LineId FROM SchedulingOrderLines
                    WHERE OrderId = ? AND ItemId = ? AND ProductionDate = ?
                """, (order_id, item_id, production_date)).fetchone()
                
                if existing:
                    # 更新现有记录
                    conn.execute("""
                        UPDATE SchedulingOrderLines
                        SET PlannedQty = ?, UpdatedDate = CURRENT_TIMESTAMP
                        WHERE LineId = ?
                    """, (planned_qty, existing["LineId"]))
                else:
                    # 插入新记录
                    conn.execute("""
                        INSERT INTO SchedulingOrderLines
                        (OrderId, ItemId, ProductionDate, PlannedQty, Status)
                        VALUES (?, ?, ?, ?, 'Planned')
                    """, (order_id, item_id, production_date, planned_qty))
                
                conn.commit()
            return True, "更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
    
    @staticmethod
    def batch_update_scheduling_lines(order_id: int, updates: List[Dict], 
                                    updated_by: str = "System") -> Tuple[bool, str]:
        """批量更新排产明细"""
        try:
            with get_conn() as conn:
                for update in updates:
                    item_id = update["ItemId"]
                    production_date = update["ProductionDate"]
                    planned_qty = update["PlannedQty"]
                    
                    # 检查是否存在记录
                    existing = conn.execute("""
                        SELECT LineId FROM SchedulingOrderLines
                        WHERE OrderId = ? AND ItemId = ? AND ProductionDate = ?
                    """, (order_id, item_id, production_date)).fetchone()
                    
                    if existing:
                        # 更新现有记录
                        conn.execute("""
                            UPDATE SchedulingOrderLines
                            SET PlannedQty = ?, UpdatedDate = CURRENT_TIMESTAMP
                            WHERE LineId = ?
                        """, (planned_qty, existing["LineId"]))
                    else:
                        # 插入新记录
                        conn.execute("""
                            INSERT INTO SchedulingOrderLines
                            (OrderId, ItemId, ProductionDate, PlannedQty, Status)
                            VALUES (?, ?, ?, ?, 'Planned')
                        """, (order_id, item_id, production_date, planned_qty))
                
                conn.commit()
            return True, f"批量更新成功，共更新 {len(updates)} 条记录"
        except Exception as e:
            return False, f"批量更新失败: {str(e)}"
    
    @staticmethod
    def calculate_child_mrp_for_order(order_id: int, start_date: str, end_date: str) -> Dict:
        """计算零部件MRP - 与订单MRP管理保持一致"""
        try:
            print(f"📊 [calculate_child_mrp_for_order] 开始计算零部件MRP")
            
            # 生成周列表
            weeks = SchedulingOrderService._gen_weeks_from_dates(start_date, end_date)
            
            # 获取排产订单的成品周需求
            parent_weekly = SchedulingOrderService._fetch_scheduling_parent_weekly_demand(order_id, weeks)
            
            # 展开到子件周需求
            child_weekly, child_meta = SchedulingOrderService._expand_to_child_weekly(parent_weekly, ("RM", "PKG"))
            
            # 获取期初库存
            onhand_all = SchedulingOrderService._fetch_onhand_total()
            
            # 构建结果
            rows = []
            for item_id, meta in child_meta.items():
                # 订单计划行
                plan_row = {
                    "ItemId": item_id,
                    "ItemCode": meta["ItemCode"],
                    "ItemName": meta["ItemName"],
                    "ItemSpec": meta["ItemSpec"],
                    "ItemType": meta["ItemType"],
                    "Brand": meta.get("Brand", ""),
                    "ProjectName": meta.get("ProjectName", ""),
                    "RowType": "生产计划",
                    "StartOnHand": onhand_all.get(item_id, 0.0),
                    "cells": {}
                }
                
                # 即时库存行
                stock_row = {
                    "ItemId": item_id,
                    "ItemCode": meta["ItemCode"],
                    "ItemName": meta["ItemName"],
                    "ItemSpec": meta["ItemSpec"],
                    "ItemType": meta["ItemType"],
                    "Brand": meta.get("Brand", ""),
                    "ProjectName": meta.get("ProjectName", ""),
                    "RowType": "即时库存",
                    "StartOnHand": onhand_all.get(item_id, 0.0),
                    "cells": {}
                }
                
                # 填充周数据
                start_onhand = onhand_all.get(item_id, 0.0)
                running_stock = start_onhand
                
                for week in weeks:
                    plan_qty = child_weekly.get(item_id, {}).get(week, 0.0)
                    plan_row["cells"][week] = plan_qty
                    
                    # 即时库存：本周库存 = 上周库存 - 本周计划
                    running_stock = running_stock - plan_qty
                    stock_row["cells"][week] = running_stock
                
                rows.extend([plan_row, stock_row])
            
            return {
                "weeks": weeks,
                "rows": rows
            }
            
        except Exception as e:
            return {"error": f"计算零部件MRP失败: {str(e)}"}
    
    @staticmethod
    def calculate_parent_mrp_for_order(order_id: int, start_date: str, end_date: str) -> Dict:
        """计算成品MRP - 与订单MRP管理保持一致"""
        try:
            print(f"📊 [calculate_parent_mrp_for_order] 开始计算成品MRP")
            
            # 生成周列表
            weeks = SchedulingOrderService._gen_weeks_from_dates(start_date, end_date)
            
            # 获取排产订单的成品周需求
            parent_weekly = SchedulingOrderService._fetch_scheduling_parent_weekly_demand(order_id, weeks)
            
            # 获取成品信息
            parent_meta = SchedulingOrderService._fetch_parent_meta_from_scheduling(order_id)
            
            # 获取期初库存
            onhand_all = SchedulingOrderService._fetch_onhand_total()
            
            # 构建结果
            rows = []
            for item_id, meta in parent_meta.items():
                # 订单计划行
                plan_row = {
                    "ItemId": item_id,
                    "ItemCode": meta["ItemCode"],
                    "ItemName": meta["ItemName"],
                    "ItemSpec": meta["ItemSpec"],
                    "ItemType": meta["ItemType"],
                    "Brand": meta.get("Brand", ""),
                    "ProjectName": meta.get("ProjectName", ""),
                    "RowType": "生产计划",
                    "StartOnHand": onhand_all.get(item_id, 0.0),
                    "cells": {}
                }
                
                # 即时库存行
                stock_row = {
                    "ItemId": item_id,
                    "ItemCode": meta["ItemCode"],
                    "ItemName": meta["ItemName"],
                    "ItemSpec": meta["ItemSpec"],
                    "ItemType": meta["ItemType"],
                    "Brand": meta.get("Brand", ""),
                    "ProjectName": meta.get("ProjectName", ""),
                    "RowType": "即时库存",
                    "StartOnHand": onhand_all.get(item_id, 0.0),
                    "cells": {}
                }
                
                # 填充周数据
                start_onhand = onhand_all.get(item_id, 0.0)
                running_stock = start_onhand
                
                for week in weeks:
                    plan_qty = parent_weekly.get(item_id, {}).get(week, 0.0)
                    plan_row["cells"][week] = plan_qty
                    
                    # 即时库存：本周库存 = 上周库存 - 本周计划
                    running_stock = running_stock - plan_qty
                    stock_row["cells"][week] = running_stock
                
                rows.extend([plan_row, stock_row])
            
            return {
                "weeks": weeks,
                "rows": rows
            }
            
        except Exception as e:
            return {"error": f"计算成品MRP失败: {str(e)}"}
    
    @staticmethod
    def calculate_comprehensive_mrp_for_order(order_id: int, start_date: str, end_date: str) -> Dict:
        """计算综合MRP - 与订单MRP管理保持一致"""
        try:
            print(f"📊 [calculate_comprehensive_mrp_for_order] 开始计算综合MRP")
            
            # 生成周列表
            weeks = SchedulingOrderService._gen_weeks_from_dates(start_date, end_date)
            
            # 获取排产订单的成品周需求
            parent_weekly = SchedulingOrderService._fetch_scheduling_parent_weekly_demand(order_id, weeks)
            
            # 展开到子件周需求
            child_weekly, child_meta = SchedulingOrderService._expand_to_child_weekly(parent_weekly, ("RM", "PKG"))
            
            # 获取成品信息
            parent_meta = SchedulingOrderService._fetch_parent_meta_from_scheduling(order_id)
            
            # 获取期初库存
            onhand_all = SchedulingOrderService._fetch_onhand_total()
            
            # 构建结果 - 综合MRP只显示零部件，不显示成品
            rows = []
            
            # 添加零部件行
            for item_id, meta in child_meta.items():
                # 计算总库存（期初库存+第一周生产计划）
                start_onhand = onhand_all.get(item_id, 0.0)
                first_week_plan = child_weekly.get(item_id, {}).get(weeks[0], 0.0)
                total_stock = start_onhand + first_week_plan
                
                # 订单计划行
                plan_row = {
                    "ItemId": item_id,
                    "ItemCode": meta["ItemCode"],
                    "ItemName": meta["ItemName"],
                    "ItemSpec": meta["ItemSpec"],
                    "ItemType": meta["ItemType"],
                    "Brand": meta.get("Brand", ""),
                    "ProjectName": meta.get("ProjectName", ""),
                    "RowType": "生产计划",
                    "StartOnHand": f"{start_onhand}+{first_week_plan}",
                    "TotalStock": total_stock,
                    "cells": {}
                }
                
                # 即时库存行
                stock_row = {
                    "ItemId": item_id,
                    "ItemCode": meta["ItemCode"],
                    "ItemName": meta["ItemName"],
                    "ItemSpec": meta["ItemSpec"],
                    "ItemType": meta["ItemType"],
                    "Brand": meta.get("Brand", ""),
                    "ProjectName": meta.get("ProjectName", ""),
                    "RowType": "即时库存",
                    "StartOnHand": f"{start_onhand}+{first_week_plan}",
                    "TotalStock": total_stock,
                    "cells": {}
                }
                
                # 填充周数据
                start_onhand = onhand_all.get(item_id, 0.0)
                running_stock = start_onhand
                
                for week in weeks:
                    plan_qty = child_weekly.get(item_id, {}).get(week, 0.0)
                    plan_row["cells"][week] = plan_qty
                    
                    # 即时库存：本周库存 = 上周库存 - 本周计划
                    running_stock = running_stock - plan_qty
                    stock_row["cells"][week] = running_stock
                
                rows.extend([plan_row, stock_row])
            
            return {
                "weeks": weeks,
                "rows": rows
            }
            
        except Exception as e:
            return {"error": f"计算综合MRP失败: {str(e)}"}
    
    @staticmethod
    def _gen_weeks_from_dates(start_date: str, end_date: str) -> List[str]:
        """从日期范围生成周列表"""
        weeks = []
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        current_dt = start_dt
        while current_dt <= end_dt:
            weeks.append(current_dt.strftime("%Y-%m-%d"))
            current_dt += timedelta(days=1)
        
        return weeks
    
    @staticmethod
    def _fetch_scheduling_parent_weekly_demand(order_id: int, weeks: List[str]) -> Dict[int, Dict[str, float]]:
        """获取排产订单的成品周需求"""
        parent_weekly = defaultdict(lambda: defaultdict(float))
        
        # 获取排产订单的成品和排产数据
        kanban_data = SchedulingOrderService.get_scheduling_kanban_data(order_id)
        products = kanban_data.get("products", [])
        
        for product in products:
            item_id = product["ItemId"]
            cells = product.get("cells", {})
            
            # 获取该物料的排产数据
            for date_str in weeks:
                qty = float(cells.get(date_str, 0.0))
                if qty > 0:
                    parent_weekly[item_id][date_str] = qty
        
        return parent_weekly
    
    @staticmethod
    def _expand_to_child_weekly(parent_weekly: Dict[int, Dict[str, float]], include_types: Tuple[str, ...]) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Dict]]:
        """展开到子件周需求"""
        child_weekly = defaultdict(lambda: defaultdict(float))
        child_meta = {}
        
        for parent_id, wk_map in parent_weekly.items():
            for week, qty in wk_map.items():
                if qty <= 0:
                    continue
                
                # 展开BOM
                expanded = BomService.expand_bom(parent_id, qty)
                for e in expanded:
                    itype = e.get("ItemType") or ""
                    if include_types and itype not in include_types:
                        continue
                    
                    cid = int(e["ItemId"])
                    child_weekly[cid][week] += float(e.get("ActualQty") or 0.0)
                    
                    if cid not in child_meta:
                        child_meta[cid] = {
                            "ItemId": cid,
                            "ItemCode": e.get("ItemCode", ""),
                            "ItemName": e.get("ItemName", ""),
                            "ItemSpec": e.get("ItemSpec", ""),
                            "ItemType": itype,
                            "Brand": e.get("Brand", ""),
                            "ProjectName": e.get("ProjectName", ""),
                        }
        
        return child_weekly, child_meta
    
    @staticmethod
    def _fetch_parent_meta_from_scheduling(order_id: int) -> Dict[int, Dict]:
        """获取排产订单的成品信息"""
        parent_meta = {}
        
        # 获取排产订单的成品信息
        kanban_data = SchedulingOrderService.get_scheduling_kanban_data(order_id)
        products = kanban_data.get("products", [])
        
        for product in products:
            item_id = product["ItemId"]
            if item_id not in parent_meta:
                parent_meta[item_id] = {
                    "ItemId": item_id,
                    "ItemCode": product.get("ItemCode", ""),
                    "ItemName": product.get("ItemName", ""),
                    "ItemSpec": product.get("ItemSpec", ""),
                    "ItemType": product.get("ItemType", ""),
                    "Brand": product.get("Brand", ""),
                    "ProjectName": product.get("ProjectName", ""),
                }
        
        return parent_meta
    
    @staticmethod
    def _fetch_onhand_total() -> Dict[int, float]:
        """获取期初库存"""
        onhand_all = {}
        
        try:
            # 获取所有物料的库存
            inventory_data = query_all("""
                SELECT ItemId, SUM(Qty) as TotalQty
                FROM Inventory
                GROUP BY ItemId
            """)
            
            for row in inventory_data:
                onhand_all[row["ItemId"]] = float(row["TotalQty"] or 0.0)
        except Exception as e:
            print(f"获取库存数据失败: {e}")
        
        return onhand_all

    @staticmethod
    def calculate_mrp_for_order(order_id: int, include_types: Tuple[str, ...] = ("RM", "PKG")) -> Dict:
        """
        根据排产订单计算MRP
        返回格式：
        {
            "order_info": {...},
            "date_range": ["2024-01-01", "2024-01-02", ...],
            "mrp_results": [
                {
                    "ItemId": 1,
                    "ItemCode": "RM-001",
                    "ItemName": "原料A",
                    "ItemType": "RM",
                    "cells": {
                        "2024-01-01": {"RequiredQty": 100, "OnHandQty": 50, "NetQty": 50},
                        "2024-01-02": {"RequiredQty": 150, "OnHandQty": 0, "NetQty": 150},
                        ...
                    }
                }
            ]
        }
        """
        try:
            # 获取排产订单信息
            order_info = SchedulingOrderService.get_scheduling_order_by_id(order_id)
            if not order_info:
                return {"error": "排产订单不存在"}
            
            # 生成日期范围
            start_date = datetime.strptime(order_info["StartDate"], "%Y-%m-%d").date()
            end_date = datetime.strptime(order_info["EndDate"], "%Y-%m-%d").date()
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)
            
            # 获取排产明细数据
            sql = """
                SELECT 
                    sol.ItemId, sol.ProductionDate, sol.PlannedQty,
                    i.ItemCode, i.CnName, i.ItemSpec, i.ItemType, i.Brand
                FROM SchedulingOrderLines sol
                JOIN Items i ON sol.ItemId = i.ItemId
                WHERE sol.OrderId = ? AND sol.PlannedQty > 0
                ORDER BY sol.ProductionDate
            """
            rows = query_all(sql, (order_id,))
            
            # 按日期分组排产数据
            daily_production = defaultdict(lambda: defaultdict(float))
            for row in rows:
                daily_production[row["ProductionDate"]][row["ItemId"]] = float(row["PlannedQty"])
            
            # 计算每个日期的MRP需求
            mrp_results = defaultdict(lambda: {
                "ItemId": None,
                "ItemCode": "",
                "ItemName": "",
                "ItemSpec": "",
                "ItemType": "",
                "Brand": "",
                "cells": {}
            })
            
            # 获取期初库存
            onhand_all = SchedulingOrderService._fetch_onhand_total()
            
            for production_date in date_range:
                print(f"📊 [calculate_mrp_for_order] 计算日期 {production_date} 的MRP")
                
                # 获取该日期的生产计划
                daily_items = daily_production.get(production_date, {})
                if not daily_items:
                    print(f"📊 [calculate_mrp_for_order] 日期 {production_date} 无生产计划")
                    continue
                
                # 计算该日期的零部件需求
                child_requirements = defaultdict(float)
                child_meta = {}
                
                for item_id, qty in daily_items.items():
                    print(f"📊 [calculate_mrp_for_order] 展开BOM：父物料{item_id}，数量{qty}")
                    
                    # 展开BOM
                    expanded = BomService.expand_bom(item_id, qty)
                    for e in expanded:
                        itype = e.get("ItemType") or ""
                        if include_types and itype not in include_types:
                            continue
                        
                        cid = int(e["ItemId"])
                        child_requirements[cid] += float(e.get("ActualQty") or 0.0)
                        
                        if cid not in child_meta:
                            child_meta[cid] = {
                                "ItemId": cid,
                                "ItemCode": e.get("ItemCode", ""),
                                "ItemName": e.get("ItemName", ""),
                                "ItemSpec": e.get("ItemSpec", ""),
                                "ItemType": itype,
                                "Brand": e.get("Brand", "")
                            }
                
                # 更新MRP结果
                for item_id, required_qty in child_requirements.items():
                    if item_id not in mrp_results:
                        mrp_results[item_id] = {
                            "ItemId": item_id,
                            "ItemCode": child_meta[item_id]["ItemCode"],
                            "ItemName": child_meta[item_id]["ItemName"],
                            "ItemSpec": child_meta[item_id]["ItemSpec"],
                            "ItemType": child_meta[item_id]["ItemType"],
                            "Brand": child_meta[item_id]["Brand"],
                            "cells": {}
                        }
                    
                    onhand_qty = float(onhand_all.get(item_id, 0.0))
                    net_qty = max(0, required_qty - onhand_qty)
                    
                    mrp_results[item_id]["cells"][production_date] = {
                        "RequiredQty": required_qty,
                        "OnHandQty": onhand_qty,
                        "NetQty": net_qty
                    }
                    
                    # 更新库存（假设当天生产完成后库存增加）
                    onhand_all[item_id] = onhand_qty + required_qty
            
            # 确保所有日期都有数据
            for item_id in mrp_results:
                for date_str in date_range:
                    if date_str not in mrp_results[item_id]["cells"]:
                        mrp_results[item_id]["cells"][date_str] = {
                            "RequiredQty": 0.0,
                            "OnHandQty": float(onhand_all.get(item_id, 0.0)),
                            "NetQty": 0.0
                        }
            
            # 保存MRP计算结果到数据库
            SchedulingOrderService._save_mrp_results(order_id, mrp_results, date_range)
            
            # 转换为列表并排序
            mrp_list = []
            for item_id in sorted(mrp_results.keys(), 
                                key=lambda i: (mrp_results[i]["ItemType"], mrp_results[i]["ItemCode"])):
                mrp_list.append(mrp_results[item_id])
            
            return {
                "order_info": order_info,
                "date_range": date_range,
                "mrp_results": mrp_list
            }
        except Exception as e:
            print(f"计算MRP失败: {e}")
            return {"error": f"计算MRP失败: {str(e)}"}
    
    @staticmethod
    def _get_product_info(item_id: int) -> Optional[Dict]:
        """获取产品信息"""
        try:
            sql = """
                SELECT 
                    i.ItemId, i.ItemCode, i.CnName, i.ItemSpec, i.Brand,
                    pm.ProjectCode, pm.ProjectName
                FROM Items i
                LEFT JOIN ProjectMappings pm ON i.ItemId = pm.ItemId
                WHERE i.ItemId = ? AND i.IsActive = 1
            """
            row = query_one(sql, (item_id,))
            return dict(row) if row else None
        except Exception as e:
            print(f"获取产品信息失败: {e}")
            return None
    
    @staticmethod
    def _fetch_onhand_total() -> Dict[int, float]:
        """获取所有物料的库存总量"""
        sql = """
            SELECT ib.ItemId, SUM(ib.QtyOnHand) AS OnHand
            FROM InventoryBalance ib
            GROUP BY ib.ItemId
        """
        rows = query_all(sql)
        return {int(r["ItemId"]): float(r["OnHand"] or 0.0) for r in rows}
    
    @staticmethod
    def _save_mrp_results(order_id: int, mrp_results: Dict, date_range: List[str]):
        """保存MRP计算结果到数据库"""
        try:
            with get_conn() as conn:
                # 先删除该订单的旧MRP数据
                conn.execute("DELETE FROM SchedulingOrderMRP WHERE OrderId = ?", (order_id,))
                
                # 插入新的MRP数据
                for item_id, mrp_data in mrp_results.items():
                    for date_str in date_range:
                        cell_data = mrp_data["cells"].get(date_str, {})
                        conn.execute("""
                            INSERT INTO SchedulingOrderMRP
                            (OrderId, ItemId, ProductionDate, RequiredQty, OnHandQty, NetQty)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            order_id, item_id, date_str,
                            cell_data.get("RequiredQty", 0.0),
                            cell_data.get("OnHandQty", 0.0),
                            cell_data.get("NetQty", 0.0)
                        ))
                
                conn.commit()
        except Exception as e:
            print(f"保存MRP结果失败: {e}")
    
    @staticmethod
    def get_mrp_results(order_id: int) -> List[Dict]:
        """获取已保存的MRP计算结果"""
        try:
            sql = """
                SELECT 
                    som.ItemId, som.ProductionDate, som.RequiredQty, 
                    som.OnHandQty, som.NetQty,
                    i.ItemCode, i.CnName, i.ItemSpec, i.ItemType, i.Brand
                FROM SchedulingOrderMRP som
                JOIN Items i ON som.ItemId = i.ItemId
                WHERE som.OrderId = ?
                ORDER BY i.ItemType, i.ItemCode, som.ProductionDate
            """
            rows = query_all(sql, (order_id,))
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取MRP结果失败: {e}")
            return []
