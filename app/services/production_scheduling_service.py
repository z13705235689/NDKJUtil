# app/services/production_scheduling_service.py
# -*- coding: utf-8 -*-
"""
生产排产服务类
- 支持按天排产的生产计划管理
- 提供看板式的排产界面
- 集成MRP计算功能，细化到每一天
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, date
from collections import defaultdict

from app.db import query_all, query_one, get_conn
from app.services.mrp_service import MRPService
from app.services.bom_service import BomService


class ProductionSchedulingService:
    """生产排产服务类"""
    
    @staticmethod
    def create_schedule(schedule_name: str, start_date: str, end_date: str, 
                      created_by: str = "System", remark: str = "") -> Tuple[bool, str, int]:
        """创建新的生产排产计划"""
        try:
            with get_conn() as conn:
                cur = conn.execute("""
                    INSERT INTO ProductionSchedules 
                    (ScheduleName, StartDate, EndDate, Status, CreatedBy, Remark)
                    VALUES (?, ?, ?, 'Draft', ?, ?)
                """, (schedule_name, start_date, end_date, created_by, remark))
                schedule_id = cur.lastrowid
                conn.commit()
            return True, f"成功创建排产计划：{schedule_name}", schedule_id
        except Exception as e:
            return False, f"创建排产计划失败: {str(e)}", 0
    
    @staticmethod
    def get_schedules() -> List[Dict]:
        """获取所有生产排产计划"""
        try:
            sql = """
                SELECT ScheduleId, ScheduleName, StartDate, EndDate, Status, 
                       CreatedBy, CreatedDate, UpdatedBy, UpdatedDate, Remark
                FROM ProductionSchedules
                ORDER BY CreatedDate DESC
            """
            rows = query_all(sql)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取排产计划失败: {e}")
            return []
    
    @staticmethod
    def get_schedule_by_id(schedule_id: int) -> Optional[Dict]:
        """根据ID获取排产计划"""
        try:
            sql = """
                SELECT ScheduleId, ScheduleName, StartDate, EndDate, Status, 
                       CreatedBy, CreatedDate, UpdatedBy, UpdatedDate, Remark
                FROM ProductionSchedules
                WHERE ScheduleId = ?
            """
            row = query_one(sql, (schedule_id,))
            return dict(row) if row else None
        except Exception as e:
            print(f"获取排产计划失败: {e}")
            return None
    
    @staticmethod
    def update_schedule(schedule_id: int, schedule_name: str = None, 
                       start_date: str = None, end_date: str = None,
                       status: str = None, updated_by: str = "System", 
                       remark: str = None) -> Tuple[bool, str]:
        """更新排产计划"""
        try:
            update_fields = []
            params = []
            
            if schedule_name is not None:
                update_fields.append("ScheduleName = ?")
                params.append(schedule_name)
            if start_date is not None:
                update_fields.append("StartDate = ?")
                params.append(start_date)
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
            params.extend([updated_by, schedule_id])
            
            sql = f"""
                UPDATE ProductionSchedules 
                SET {', '.join(update_fields)}
                WHERE ScheduleId = ?
            """
            
            with get_conn() as conn:
                conn.execute(sql, params)
                conn.commit()
            return True, "更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
    
    @staticmethod
    def delete_schedule(schedule_id: int) -> Tuple[bool, str]:
        """删除排产计划（级联删除相关数据）"""
        try:
            with get_conn() as conn:
                conn.execute("DELETE FROM ProductionScheduleMRP WHERE ScheduleId = ?", (schedule_id,))
                conn.execute("DELETE FROM ProductionScheduleLines WHERE ScheduleId = ?", (schedule_id,))
                conn.execute("DELETE FROM ProductionSchedules WHERE ScheduleId = ?", (schedule_id,))
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
    def get_schedule_kanban_data(schedule_id: int) -> Dict:
        """
        获取排产看板数据
        返回格式：
        {
            "schedule_info": {...},
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
            # 获取排产计划信息
            schedule_info = ProductionSchedulingService.get_schedule_by_id(schedule_id)
            if not schedule_info:
                return {"error": "排产计划不存在"}
            
            # 生成日期范围
            start_date = datetime.strptime(schedule_info["StartDate"], "%Y-%m-%d").date()
            end_date = datetime.strptime(schedule_info["EndDate"], "%Y-%m-%d").date()
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)
            
            # 获取排产明细数据
            sql = """
                SELECT 
                    psl.ItemId, psl.ProductionDate, psl.PlannedQty,
                    i.ItemCode, i.CnName, i.ItemSpec, i.Brand,
                    pm.ProjectName
                FROM ProductionScheduleLines psl
                JOIN Items i ON psl.ItemId = i.ItemId
                LEFT JOIN ProjectMappings pm ON i.ItemId = pm.ItemId
                WHERE psl.ScheduleId = ?
                ORDER BY i.ItemCode, psl.ProductionDate
            """
            rows = query_all(sql, (schedule_id,))
            
            # 按产品分组数据
            products_data = defaultdict(lambda: {
                "ItemId": None,
                "ItemCode": "",
                "ItemName": "",
                "ItemSpec": "",
                "Brand": "",
                "ProjectName": "",
                "cells": {}
            })
            
            for row in rows:
                item_id = row["ItemId"]
                if products_data[item_id]["ItemId"] is None:
                    products_data[item_id].update({
                        "ItemId": item_id,
                        "ItemCode": row["ItemCode"],
                        "ItemName": row["CnName"],
                        "ItemSpec": row["ItemSpec"] or "",
                        "Brand": row["Brand"] or "",
                        "ProjectName": row["ProjectName"] or ""
                    })
                
                products_data[item_id]["cells"][row["ProductionDate"]] = float(row["PlannedQty"])
            
            # 转换为列表并排序
            products = []
            for item_id in sorted(products_data.keys()):
                product_data = products_data[item_id]
                # 确保所有日期都有值（默认为0）
                for date_str in date_range:
                    if date_str not in product_data["cells"]:
                        product_data["cells"][date_str] = 0.0
                products.append(product_data)
            
            return {
                "schedule_info": schedule_info,
                "date_range": date_range,
                "products": products
            }
        except Exception as e:
            print(f"获取排产看板数据失败: {e}")
            return {"error": f"获取排产看板数据失败: {str(e)}"}
    
    @staticmethod
    def update_schedule_line(schedule_id: int, item_id: int, production_date: str, 
                           planned_qty: float, updated_by: str = "System") -> Tuple[bool, str]:
        """更新排产明细"""
        try:
            with get_conn() as conn:
                # 检查是否存在记录
                existing = conn.execute("""
                    SELECT LineId FROM ProductionScheduleLines
                    WHERE ScheduleId = ? AND ItemId = ? AND ProductionDate = ?
                """, (schedule_id, item_id, production_date)).fetchone()
                
                if existing:
                    # 更新现有记录
                    conn.execute("""
                        UPDATE ProductionScheduleLines
                        SET PlannedQty = ?, UpdatedDate = CURRENT_TIMESTAMP
                        WHERE LineId = ?
                    """, (planned_qty, existing["LineId"]))
                else:
                    # 插入新记录
                    conn.execute("""
                        INSERT INTO ProductionScheduleLines
                        (ScheduleId, ItemId, ProductionDate, PlannedQty, Status)
                        VALUES (?, ?, ?, ?, 'Planned')
                    """, (schedule_id, item_id, production_date, planned_qty))
                
                conn.commit()
            return True, "更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
    
    @staticmethod
    def batch_update_schedule_lines(schedule_id: int, updates: List[Dict], 
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
                        SELECT LineId FROM ProductionScheduleLines
                        WHERE ScheduleId = ? AND ItemId = ? AND ProductionDate = ?
                    """, (schedule_id, item_id, production_date)).fetchone()
                    
                    if existing:
                        # 更新现有记录
                        conn.execute("""
                            UPDATE ProductionScheduleLines
                            SET PlannedQty = ?, UpdatedDate = CURRENT_TIMESTAMP
                            WHERE LineId = ?
                        """, (planned_qty, existing["LineId"]))
                    else:
                        # 插入新记录
                        conn.execute("""
                            INSERT INTO ProductionScheduleLines
                            (ScheduleId, ItemId, ProductionDate, PlannedQty, Status)
                            VALUES (?, ?, ?, ?, 'Planned')
                        """, (schedule_id, item_id, production_date, planned_qty))
                
                conn.commit()
            return True, f"批量更新成功，共更新 {len(updates)} 条记录"
        except Exception as e:
            return False, f"批量更新失败: {str(e)}"
    
    @staticmethod
    def calculate_daily_mrp(schedule_id: int, include_types: Tuple[str, ...] = ("RM", "PKG")) -> Dict:
        """
        根据排产计划计算每日MRP
        返回格式：
        {
            "schedule_info": {...},
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
            # 获取排产计划信息
            schedule_info = ProductionSchedulingService.get_schedule_by_id(schedule_id)
            if not schedule_info:
                return {"error": "排产计划不存在"}
            
            # 生成日期范围
            start_date = datetime.strptime(schedule_info["StartDate"], "%Y-%m-%d").date()
            end_date = datetime.strptime(schedule_info["EndDate"], "%Y-%m-%d").date()
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)
            
            # 获取排产明细数据
            sql = """
                SELECT 
                    psl.ItemId, psl.ProductionDate, psl.PlannedQty,
                    i.ItemCode, i.CnName, i.ItemSpec, i.ItemType, i.Brand
                FROM ProductionScheduleLines psl
                JOIN Items i ON psl.ItemId = i.ItemId
                WHERE psl.ScheduleId = ? AND psl.PlannedQty > 0
                ORDER BY psl.ProductionDate
            """
            rows = query_all(sql, (schedule_id,))
            
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
            onhand_all = ProductionSchedulingService._fetch_onhand_total()
            
            for production_date in date_range:
                print(f"📊 [calculate_daily_mrp] 计算日期 {production_date} 的MRP")
                
                # 获取该日期的生产计划
                daily_items = daily_production.get(production_date, {})
                if not daily_items:
                    print(f"📊 [calculate_daily_mrp] 日期 {production_date} 无生产计划")
                    continue
                
                # 计算该日期的零部件需求
                child_requirements = defaultdict(float)
                child_meta = {}
                
                for item_id, qty in daily_items.items():
                    print(f"📊 [calculate_daily_mrp] 展开BOM：父物料{item_id}，数量{qty}")
                    
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
            ProductionSchedulingService._save_mrp_results(schedule_id, mrp_results, date_range)
            
            # 转换为列表并排序
            mrp_list = []
            for item_id in sorted(mrp_results.keys(), 
                                key=lambda i: (mrp_results[i]["ItemType"], mrp_results[i]["ItemCode"])):
                mrp_list.append(mrp_results[item_id])
            
            return {
                "schedule_info": schedule_info,
                "date_range": date_range,
                "mrp_results": mrp_list
            }
        except Exception as e:
            print(f"计算每日MRP失败: {e}")
            return {"error": f"计算每日MRP失败: {str(e)}"}
    
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
    def _save_mrp_results(schedule_id: int, mrp_results: Dict, date_range: List[str]):
        """保存MRP计算结果到数据库"""
        try:
            with get_conn() as conn:
                # 先删除该计划的旧MRP数据
                conn.execute("DELETE FROM ProductionScheduleMRP WHERE ScheduleId = ?", (schedule_id,))
                
                # 插入新的MRP数据
                for item_id, mrp_data in mrp_results.items():
                    for date_str in date_range:
                        cell_data = mrp_data["cells"].get(date_str, {})
                        conn.execute("""
                            INSERT INTO ProductionScheduleMRP
                            (ScheduleId, ItemId, ProductionDate, RequiredQty, OnHandQty, NetQty)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            schedule_id, item_id, date_str,
                            cell_data.get("RequiredQty", 0.0),
                            cell_data.get("OnHandQty", 0.0),
                            cell_data.get("NetQty", 0.0)
                        ))
                
                conn.commit()
        except Exception as e:
            print(f"保存MRP结果失败: {e}")
    
    @staticmethod
    def get_mrp_results(schedule_id: int) -> List[Dict]:
        """获取已保存的MRP计算结果"""
        try:
            sql = """
                SELECT 
                    psm.ItemId, psm.ProductionDate, psm.RequiredQty, 
                    psm.OnHandQty, psm.NetQty,
                    i.ItemCode, i.CnName, i.ItemSpec, i.ItemType, i.Brand
                FROM ProductionScheduleMRP psm
                JOIN Items i ON psm.ItemId = i.ItemId
                WHERE psm.ScheduleId = ?
                ORDER BY i.ItemType, i.ItemCode, psm.ProductionDate
            """
            rows = query_all(sql, (schedule_id,))
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"获取MRP结果失败: {e}")
            return []
    
    @staticmethod
    def get_product_info_by_pn(pn: str) -> Optional[Dict]:
        """根据PN字段获取成品信息"""
        try:
            print(f"🔍 [get_product_info_by_pn] 查找PN: {pn}")
            
            sql = """
                SELECT 
                    i.ItemId,
                    i.ItemCode,
                    i.CnName,
                    i.ItemSpec,
                    i.Brand,
                    i.ItemType,
                    pm.ProjectCode,
                    pm.ProjectName
                FROM Items i
                LEFT JOIN ProjectMappings pm ON i.ItemId = pm.ItemId
                WHERE i.Brand = ? AND i.ItemType = 'FG' AND i.IsActive = 1
            """
            row = query_one(sql, (pn,))
            if row:
                result = dict(row)
                print(f"✅ [get_product_info_by_pn] 找到成品信息: {result}")
                return result
            else:
                print(f"❌ [get_product_info_by_pn] 未找到PN '{pn}' 对应的成品")
                # 显示所有可用的成品用于调试
                all_fg_sql = "SELECT ItemCode, CnName, Brand FROM Items WHERE ItemType = 'FG' AND IsActive = 1 LIMIT 10"
                all_fg = query_all(all_fg_sql)
                print(f"📋 [get_product_info_by_pn] 可用的成品示例: {[dict(item) for item in all_fg]}")
            return None
        except Exception as e:
            print(f"根据PN获取成品信息失败: {e}")
            return None
