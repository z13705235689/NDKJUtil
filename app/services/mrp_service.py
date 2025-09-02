# app/services/mrp_service.py
# -*- coding: utf-8 -*-
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.db import query_all, query_one
from app.services.bom_service import BomService
from app.services.inventory_service import InventoryService
from app.services.customer_order_service import CustomerOrderService

WEEK_FMT = "CW{0:02d}"

class MRPService:
    """
    MRP 计算服务（看板版）
    - 以"周"为列，输出每个子件两个数据行：生产计划、即时库存
    - 支持按客户订单计算和按成品筛选
    - 仅展开到 RM/PKG（可通过 include_types 调整）
    """

    # ---------------- 公共入口 ----------------
    @staticmethod
    def calculate_mrp_kanban(start_date: str, end_date: str,
                              import_id: Optional[int] = None,
                              search_filter: Optional[str] = None,
                              include_types: Tuple[str, ...] = ("RM", "PKG")) -> Dict:
        """
        返回：
        {
          "weeks": ["CW31","CW32",...],
          "rows": [  # 两行成对出现
             {"ItemId":1,"ItemCode":"RM-001","ItemName":"铝丝", "ItemType":"RM",
              "RowType":"生产计划","StartOnHand": 48611.0, "cells":{"CW31":123,"CW32":0,...}},
             {"ItemId":1,"ItemCode":"RM-001","ItemName":"铝丝", "ItemType":"RM",
              "RowType":"即时库存","StartOnHand": 48611.0, "cells":{"CW31":48488,"CW32":...}},
             ...
          ]
        }
        
        参数：
        - import_id: 指定客户订单版本ID，如果为None则计算所有订单
        - parent_item_filter: 成品筛选，支持模糊匹配，如果为None则计算所有成品
        """
        print(f"📊 [calculate_mrp_kanban] 开始计算零部件MRP看板")
        print(f"📊 [calculate_mrp_kanban] 参数：start_date={start_date}, end_date={end_date}")
        print(f"📊 [calculate_mrp_kanban] 参数：import_id={import_id}, search_filter={search_filter}")
        print(f"📊 [calculate_mrp_kanban] 参数：include_types={include_types}")
        
        # 如果指定了订单版本，使用订单的实际日期范围
        if import_id is not None:
            print(f"📊 [calculate_mrp_kanban] 获取订单版本日期范围")
            order_range = MRPService.get_order_version_date_range(import_id)
            if order_range and order_range.get("earliest_date") and order_range.get("latest_date"):
                start_date = order_range["earliest_date"]
                end_date = order_range["latest_date"]
                print(f"📊 [calculate_mrp_kanban] 使用订单日期范围：{start_date} 到 {end_date}")
        
        print(f"📊 [calculate_mrp_kanban] 生成周列表")
        weeks = MRPService._gen_weeks(start_date, end_date)
        print(f"📊 [calculate_mrp_kanban] 生成周：{weeks}")

        # 1) 成品周需求（ItemCode 维度）
        print(f"📊 [calculate_mrp_kanban] 获取成品周需求")
        parent_weekly = MRPService._fetch_parent_weekly_demand(
            start_date, end_date, import_id, search_filter
        )
        print(f"📊 [calculate_mrp_kanban] 成品周需求：{parent_weekly}")

        # 2) 展开到子件周需求
        print(f"📊 [calculate_mrp_kanban] 展开BOM到子件")
        child_weekly: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        child_meta: Dict[int, Dict] = {}  # ItemId -> {code,name,type}

        for parent_id, wk_map in parent_weekly.items():
            print(f"📊 [calculate_mrp_kanban] 处理父物料ID：{parent_id}")
            for cw, qty in wk_map.items():
                if qty <= 0:
                    continue
                print(f"📊 [calculate_mrp_kanban] 展开BOM：父物料{parent_id}，周{cw}，数量{qty}")
                # 用 BomService.expand_bom 递归展开并考虑损耗
                expanded = BomService.expand_bom(parent_id, qty)
                print(f"📊 [calculate_mrp_kanban] BOM展开结果：{len(expanded)} 个组件")
                for e in expanded:
                    itype = e.get("ItemType") or ""
                    if include_types and itype not in include_types:
                        print(f"📊 [calculate_mrp_kanban] 跳过组件：{e.get('ItemCode', '')}，类型{itype}")
                        continue
                    cid = int(e["ItemId"])
                    child_weekly[cid][cw] += float(e.get("ActualQty") or 0.0)
                    if cid not in child_meta:
                        child_meta[cid] = {
                            "ItemId": cid,
                            "ItemCode": e.get("ItemCode", ""),
                            "ItemName": e.get("ItemName", ""),
                            "ItemSpec": e.get("ItemSpec", ""),
                            "ItemType": itype,
                        }

        print(f"📊 [calculate_mrp_kanban] 子件需求汇总：{len(child_weekly)} 个物料")

        # 3) 期初库存（聚合全部仓）
        print(f"📊 [calculate_mrp_kanban] 获取期初库存")
        onhand_all = MRPService._fetch_onhand_total()  # {ItemId: Qty}
        print(f"📊 [calculate_mrp_kanban] 期初库存：{len(onhand_all)} 个物料")

        # 4) 生成两行（计划/即时库存）
        print(f"📊 [calculate_mrp_kanban] 生成MRP行")
        rows: List[Dict] = []
        for item_id in sorted(child_weekly.keys(),
                              key=lambda i: (child_meta[i].get("ItemType",""), child_meta[i].get("ItemCode",""))):
            meta = child_meta[item_id]
            plan_cells = {w: float(child_weekly[item_id].get(w, 0.0)) for w in weeks}

            # 期初库存（允许缺省为 0）
            start_onhand = float(onhand_all.get(item_id, 0.0))

            # 运行库存：按照 "本周库存 = 上周库存 - 本周计划"
            stock_cells: Dict[str, float] = {}
            running = start_onhand
            for w in weeks:
                running = running - plan_cells[w]
                stock_cells[w] = running  # 允许出现负数以暴露缺口

            plan_row = dict(meta, RowType="生产计划", StartOnHand=start_onhand, cells=plan_cells)
            stock_row = dict(meta, RowType="即时库存", StartOnHand=start_onhand, cells=stock_cells)
            rows.append(plan_row)
            rows.append(stock_row)

        print(f"✅ [calculate_mrp_kanban] 计算完成，返回：weeks={len(weeks)}, rows={len(rows)}")
        return {"weeks": weeks, "rows": rows}

    @staticmethod
    def calculate_parent_mrp_kanban(start_date: str, end_date: str,
                                    import_id: Optional[int] = None,
                                    search_filter: Optional[str] = None) -> Dict:
        """
        计算成品级别的MRP看板（基于BOM和客户订单）
        返回：
        {
          "weeks": ["CW31","CW32",...],
          "rows": [  # 每个成品两行：生产计划、即时库存
             {"ItemId":1,"ItemCode":"FG-001","ItemName":"产品A", "ItemType":"FG",
              "RowType":"生产计划","StartOnHand": 100.0, "SafetyStock": 50.0,
              "cells":{"CW31":50,"CW32":30,...}},
             {"ItemId":1,"ItemCode":"FG-001","ItemName":"产品A", "ItemType":"FG",
              "RowType":"即时库存","StartOnHand": 100.0, "SafetyStock": 50.0,
              "cells":{"CW31":50,"CW32":20,...}},
             ...
          ]
        }
        """
        # 如果指定了订单版本，使用订单的实际日期范围
        if import_id is not None:
            order_range = MRPService.get_order_version_date_range(import_id)
            if order_range and order_range.get("earliest_date") and order_range.get("latest_date"):
                start_date = order_range["earliest_date"]
                end_date = order_range["latest_date"]
        
        weeks = MRPService._gen_weeks(start_date, end_date)

        # 获取成品周需求（基于客户订单）
        parent_weekly = MRPService._fetch_parent_weekly_demand(
            start_date, end_date, import_id, search_filter
        )

        # 获取成品信息（从BOM表获取，确保名称对应）
        parent_meta = MRPService._fetch_parent_items_from_bom(list(parent_weekly.keys()))

        # 生成成品MRP行（每个成品两行：生产计划、即时库存）
        rows: List[Dict] = []
        for item_id in sorted(parent_weekly.keys(),
                              key=lambda i: (parent_meta[i].get("ItemType",""), parent_meta[i].get("ItemCode",""))):
            meta = parent_meta[item_id]
            demand_cells = {w: float(parent_weekly[item_id].get(w, 0.0)) for w in weeks}

            # 期初库存
            start_onhand = MRPService._fetch_item_onhand(item_id)
            
            # 安全库存
            safety_stock = meta.get("SafetyStock", 0.0)

            # 生产计划行：显示每周的需求量
            plan_row = {
                "ItemId": meta.get("ItemId"),
                "ItemCode": meta.get("ItemCode"),
                "ItemName": meta.get("CnName", ""),  # 使用物料名称，不用BOM名称
                "ItemSpec": meta.get("ItemSpec", ""),
                "ItemType": meta.get("ItemType"),
                "RowType": "生产计划", 
                "StartOnHand": start_onhand,
                "SafetyStock": safety_stock,
                "cells": demand_cells  # 显示原始需求
            }
            rows.append(plan_row)

            # 即时库存行：按照 "本周库存 = 上周库存 - 本周计划" 计算
            stock_cells: Dict[str, float] = {}
            running = start_onhand
            for w in weeks:
                running = running - demand_cells.get(w, 0.0)
                stock_cells[w] = running  # 允许出现负数以暴露缺口

            stock_row = {
                "ItemId": meta.get("ItemId"),
                "ItemCode": meta.get("ItemCode"),
                "ItemName": meta.get("CnName", ""),  # 使用物料名称，不用BOM名称
                "ItemSpec": meta.get("ItemSpec", ""),
                "ItemType": meta.get("ItemType"),
                "RowType": "即时库存", 
                "StartOnHand": start_onhand,
                "SafetyStock": safety_stock,
                "cells": stock_cells  # 显示库存变化
            }
            rows.append(stock_row)

        return {"weeks": weeks, "rows": rows}

    # ---------------- 明细方法 ---------------- 
    @staticmethod
    def _gen_weeks(start_date: str, end_date: str) -> List[str]:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        weeks: List[str] = []
        cur = start
        seen = set()
        while cur <= end:
            w = WEEK_FMT.format(cur.isocalendar()[1])
            if w not in seen:
                weeks.append(w); seen.add(w)
            cur += timedelta(days=7)
        return weeks

    @staticmethod
    def _fetch_parent_weekly_demand(start_date: str, end_date: str,
                                    import_id: Optional[int] = None,
                                    search_filter: Optional[str] = None) -> Dict[int, Dict[str, float]]:
        """
        汇总【成品/半成品】的周需求，结果键为 Items.ItemId
        依赖 CustomerOrderLines.CalendarWeek/RequiredQty
        
        参数：
        - import_id: 指定客户订单版本ID
        - parent_item_filter: 成品筛选，支持模糊匹配
        """
        print(f"📊 [_fetch_parent_weekly_demand] 开始获取成品周需求")
        print(f"📊 [_fetch_parent_weekly_demand] 参数：start_date={start_date}, end_date={end_date}")
        print(f"📊 [_fetch_parent_weekly_demand] 参数：import_id={import_id}, search_filter={search_filter}")
        
        # 构建WHERE条件
        where_conditions = ["col.LineStatus='Active'", "col.DeliveryDate BETWEEN ? AND ?"]
        params = [start_date, end_date]
        
        if import_id is not None:
            where_conditions.append("co.ImportId = ?")
            params.append(import_id)
        
        if search_filter:
            # 简化搜索：只对ItemNumber进行搜索
            where_conditions.append("col.ItemNumber LIKE ?")
            filter_pattern = f"%{search_filter}%"
            params.append(filter_pattern)
        
        where_clause = " AND ".join(where_conditions)
        print(f"📊 [_fetch_parent_weekly_demand] WHERE条件：{where_clause}")
        print(f"📊 [_fetch_parent_weekly_demand] 参数：{params}")
        
        # 首先获取订单行数据，然后通过品牌匹配BOM来获取对应的父物料
        sql = f"""
        SELECT col.ItemNumber, col.CalendarWeek, SUM(col.RequiredQty) AS Qty
        FROM CustomerOrderLines col
        JOIN CustomerOrders co ON col.OrderId = co.OrderId
        WHERE {where_clause}
        GROUP BY col.ItemNumber, col.CalendarWeek
        """
        
        rows = query_all(sql, tuple(params))
        print(f"📊 [_fetch_parent_weekly_demand] 查询结果：{len(rows)} 行")
        
        # 通过品牌匹配BOM来获取父物料ID
        out: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for r in rows:
            item_number = r["ItemNumber"]  # 这是品牌字段
            calendar_week = r["CalendarWeek"]
            qty = float(r["Qty"] or 0.0)
            
            # 通过品牌查找BOM，获取父物料ID
            bom = MRPService.find_bom_by_brand(item_number)
            if bom and bom.get("ParentItemId"):
                parent_item_id = bom["ParentItemId"]
                out[parent_item_id][calendar_week] += qty
                print(f"📊 [_fetch_parent_weekly_demand] 品牌 {item_number} 匹配到父物料ID {parent_item_id}")
            else:
                print(f"📊 [_fetch_parent_weekly_demand] 品牌 {item_number} 未找到对应BOM")
        
        print(f"📊 [_fetch_parent_weekly_demand] 汇总结果：{out}")
        return out

    @staticmethod
    def _fetch_parent_items_info(item_ids: List[int]) -> Dict[int, Dict]:
        """获取成品/半成品的基本信息"""
        if not item_ids:
            return {}
        
        placeholders = ",".join(["?"] * len(item_ids))
        sql = f"""
        SELECT ItemId, ItemCode, CnName, ItemType
        FROM Items
        WHERE ItemId IN ({placeholders}) AND IsActive = 1
        """
        
        rows = query_all(sql, tuple(item_ids))
        return {int(r["ItemId"]): dict(r) for r in rows}

    @staticmethod
    def _fetch_parent_items_from_bom(item_ids: List[int]) -> Dict[int, Dict]:
        """从BOM表获取成品/半成品信息，确保名称对应"""
        if not item_ids:
            return {}
        
        placeholders = ",".join(["?"] * len(item_ids))
        sql = f"""
        SELECT DISTINCT 
            i.ItemId, 
            i.ItemCode, 
            i.CnName, 
            i.ItemSpec,
            i.ItemType,
            i.SafetyStock,
            bh.BomName  -- BOM表中的名称
        FROM Items i
        LEFT JOIN BomHeaders bh ON i.ItemId = bh.ParentItemId  -- 通过ItemId关联BOM表
        WHERE i.ItemId IN ({placeholders}) AND i.IsActive = 1
        """
        
        rows = query_all(sql, tuple(item_ids))
        result = {}
        for r in rows:
            item_id = int(r["ItemId"])
            result[item_id] = {
                "ItemId": item_id,
                "ItemCode": r["ItemCode"],
                "CnName": r["CnName"],
                "ItemSpec": r["ItemSpec"],
                "ItemType": r["ItemType"],
                "SafetyStock": float(r["SafetyStock"] or 0.0),
                "BomName": r["BomName"] or r["CnName"]  # 如果没有BOM名称，使用CnName
            }
        return result

    @staticmethod
    def _fetch_item_onhand(item_id: int) -> float:
        """获取指定物料的库存数量"""
        sql = """
        SELECT SUM(QtyOnHand) AS OnHand
        FROM InventoryBalance
        WHERE ItemId = ?
        """
        row = query_one(sql, (item_id,))
        return float(row["OnHand"] or 0.0) if row else 0.0

    @staticmethod
    def _fetch_onhand_total() -> Dict[int, float]:
        # 直接按余额表汇总全部仓库的 QtyOnHand
        sql = """
        SELECT ib.ItemId, SUM(ib.QtyOnHand) AS OnHand
        FROM InventoryBalance ib
        GROUP BY ib.ItemId
        """
        rows = query_all(sql)
        return {int(r["ItemId"]): float(r["OnHand"] or 0.0) for r in rows}

    # ---------------- 新增方法：获取可用的客户订单版本 ---------------- 
    @staticmethod
    def get_available_import_versions() -> List[Dict]:
        """获取可用的客户订单导入版本"""
        return CustomerOrderService.get_import_history()

    @staticmethod
    def get_available_parent_items() -> List[Dict]:
        """获取可用的成品/半成品列表"""
        sql = """
        SELECT ItemId, ItemCode, CnName, ItemType
        FROM Items
        WHERE ItemType IN ('FG', 'SFG') AND IsActive = 1
        ORDER BY ItemType, ItemCode
        """
        rows = query_all(sql)
        return [dict(r) for r in rows]

    @staticmethod
    def get_order_version_date_range(import_id: int) -> Dict[str, str]:
        """获取指定订单版本的日期范围"""
        sql = """
        SELECT 
            MIN(col.DeliveryDate) AS earliest_date,
            MAX(col.DeliveryDate) AS latest_date
        FROM CustomerOrderLines col
        JOIN CustomerOrders co ON col.OrderId = co.OrderId
        WHERE co.ImportId = ? AND col.LineStatus = 'Active'
        """
        
        row = query_one(sql, (import_id,))
        if row:
            return {
                "earliest_date": row["earliest_date"],
                "latest_date": row["latest_date"]
            }
        return {}

    # ---------------- 新增方法：基于商品品牌字段的BOM匹配 ---------------- 
    @staticmethod
    def find_bom_by_brand(brand: str) -> Optional[Dict]:
        """
        根据商品品牌字段查找对应的BOM
        BOM名称格式：品牌_BOM
        """
        try:
            print(f"🔍 [find_bom_by_brand] 开始查找品牌：{brand}")
            
            sql = """
            SELECT bh.*, i.ItemCode as ParentItemCode, i.CnName as ParentItemName,
                   i.ItemSpec as ParentItemSpec, i.Brand as ParentItemBrand
            FROM BomHeaders bh
            LEFT JOIN Items i ON bh.ParentItemId = i.ItemId
            WHERE bh.BomName LIKE ? AND bh.IsActive = 1
            ORDER BY bh.Rev DESC
            LIMIT 1
            """
            bom_pattern = f"%{brand}%"
            print(f"🔍 [find_bom_by_brand] 使用模式：{bom_pattern}")
            
            result = query_one(sql, (bom_pattern,))
            if result:
                bom_dict = dict(result)
                print(f"✅ [find_bom_by_brand] 找到BOM：{bom_dict.get('BomName', '')} - {bom_dict.get('Rev', '')}")
                return bom_dict
            else:
                print(f"❌ [find_bom_by_brand] 未找到品牌 '{brand}' 对应的BOM")
                # 显示所有BOM名称用于调试
                all_boms_sql = "SELECT BomName FROM BomHeaders WHERE IsActive = 1"
                all_boms = query_all(all_boms_sql)
                print(f"📋 [find_bom_by_brand] 所有BOM名称：{[dict(bom)['BomName'] for bom in all_boms]}")
            return None
        except Exception as e:
            print(f"❌ [find_bom_by_brand] 查找BOM时发生错误: {str(e)}")
            raise Exception(f"根据品牌查找BOM失败: {str(e)}")

    @staticmethod
    def get_bom_structure_by_brand(brand: str) -> Dict:
        """
        根据商品品牌字段获取完整的BOM结构
        返回：{
            "bom_info": {...},
            "parent_item": {...},
            "components": [...]
        }
        """
        try:
            print(f"🏗️ [get_bom_structure_by_brand] 开始获取BOM结构，品牌：{brand}")
            
            # 查找BOM
            bom = MRPService.find_bom_by_brand(brand)
            if not bom:
                print(f"❌ [get_bom_structure_by_brand] 未找到BOM，返回空结构")
                return {}
            
            print(f"✅ [get_bom_structure_by_brand] 找到BOM，ID：{bom.get('BomId')}")
            
            # 获取父物料信息
            parent_item = None
            if bom.get("ParentItemId"):
                print(f"🔍 [get_bom_structure_by_brand] 查找父物料，ID：{bom['ParentItemId']}")
                sql = """
                SELECT ItemId, ItemCode, CnName, ItemSpec, ItemType, Brand, Unit
                FROM Items
                WHERE ItemId = ? AND IsActive = 1
                """
                result = query_one(sql, (bom["ParentItemId"],))
                if result:
                    parent_item = dict(result)
                    print(f"✅ [get_bom_structure_by_brand] 找到父物料：{parent_item.get('ItemCode', '')} - {parent_item.get('CnName', '')}")
                else:
                    print(f"❌ [get_bom_structure_by_brand] 未找到父物料")
            else:
                print(f"⚠️ [get_bom_structure_by_brand] BOM没有关联父物料")
            
            # 获取BOM组件
            print(f"🔍 [get_bom_structure_by_brand] 获取BOM组件，BOM ID：{bom['BomId']}")
            components = MRPService.get_bom_components(bom["BomId"])
            print(f"✅ [get_bom_structure_by_brand] 找到 {len(components)} 个组件")
            
            return {
                "bom_info": bom,
                "parent_item": parent_item,
                "components": components
            }
        except Exception as e:
            print(f"❌ [get_bom_structure_by_brand] 获取BOM结构时发生错误: {str(e)}")
            raise Exception(f"获取BOM结构失败: {str(e)}")

    @staticmethod
    def get_bom_components(bom_id: int) -> List[Dict]:
        """获取BOM的所有组件"""
        try:
            print(f"🔍 [get_bom_components] 查询BOM组件，BOM ID：{bom_id}")
            
            sql = """
            SELECT bl.*, i.ItemCode, i.CnName, i.ItemSpec, i.ItemType, i.Brand, i.Unit
            FROM BomLines bl
            JOIN Items i ON bl.ChildItemId = i.ItemId
            WHERE bl.BomId = ? AND i.IsActive = 1
            ORDER BY bl.LineId
            """
            results = query_all(sql, (bom_id,))
            components = [dict(row) for row in results]
            
            print(f"✅ [get_bom_components] 找到 {len(components)} 个组件")
            for i, comp in enumerate(components[:3], 1):  # 显示前3个组件
                print(f"  组件{i}：{comp.get('ItemCode', '')} - {comp.get('CnName', '')} - QtyPer:{comp.get('QtyPer', 1.0)}")
            
            return components
        except Exception as e:
            print(f"❌ [get_bom_components] 获取BOM组件时发生错误: {str(e)}")
            raise Exception(f"获取BOM组件失败: {str(e)}")

    @staticmethod
    def calculate_mrp_by_brand(brand: str, required_qty: float, 
                             include_types: Tuple[str, ...] = ("RM", "PKG")) -> Dict:
        """
        根据商品品牌字段计算MRP需求
        
        参数：
        - brand: 商品品牌字段（对应客户订单的PN）
        - required_qty: 需求数量
        - include_types: 包含的物料类型
        
        返回：
        {
            "bom_info": {...},
            "parent_item": {...},
            "requirements": [
                {
                    "ItemId": 1,
                    "ItemCode": "RM-001",
                    "ItemName": "铝丝",
                    "ItemType": "RM",
                    "RequiredQty": 100.0,
                    "OnHandQty": 50.0,
                    "NetQty": 50.0
                }
            ]
        }
        """
        try:
            print(f"📊 [calculate_mrp_by_brand] 开始MRP计算，品牌：{brand}，需求数量：{required_qty}")
            print(f"📊 [calculate_mrp_by_brand] 包含物料类型：{include_types}")
            
            # 获取BOM结构
            bom_structure = MRPService.get_bom_structure_by_brand(brand)
            if not bom_structure:
                print(f"❌ [calculate_mrp_by_brand] 未找到BOM结构，返回错误")
                return {"error": f"未找到品牌 '{brand}' 对应的BOM"}
            
            bom_info = bom_structure["bom_info"]
            parent_item = bom_structure["parent_item"]
            components = bom_structure["components"]
            
            print(f"📊 [calculate_mrp_by_brand] 开始计算需求，组件数量：{len(components)}")
            
            # 计算需求
            requirements = []
            for i, component in enumerate(components, 1):
                item_type = component.get("ItemType", "")
                print(f"🔍 [calculate_mrp_by_brand] 处理组件{i}：{component.get('ItemCode', '')} - 类型：{item_type}")
                
                # 只处理指定类型的物料
                if include_types and item_type not in include_types:
                    print(f"⏭️ [calculate_mrp_by_brand] 跳过组件{i}，类型 {item_type} 不在包含列表中")
                    continue
                
                # 计算需求数量（考虑损耗）
                qty_per = float(component.get("QtyPer", 1.0))
                scrap_factor = float(component.get("ScrapFactor", 0.0))
                required_qty_with_scrap = required_qty * qty_per * (1 + scrap_factor)
                
                print(f"📊 [calculate_mrp_by_brand] 组件{i}计算：需求{qty_per} × 损耗系数{1+scrap_factor} = {required_qty_with_scrap}")
                
                # 获取库存
                item_id = component["ChildItemId"]
                onhand_qty = MRPService._fetch_item_onhand(item_id)
                print(f"📊 [calculate_mrp_by_brand] 组件{i}库存：{onhand_qty}")
                
                # 计算净需求
                net_qty = max(0, required_qty_with_scrap - onhand_qty)
                print(f"📊 [calculate_mrp_by_brand] 组件{i}净需求：{net_qty}")
                
                requirements.append({
                    "ItemId": item_id,
                    "ItemCode": component["ItemCode"],
                    "ItemName": component["CnName"],
                    "ItemSpec": component.get("ItemSpec", ""),
                    "ItemType": item_type,
                    "Brand": component.get("Brand", ""),
                    "Unit": component.get("Unit", ""),
                    "QtyPer": qty_per,
                    "ScrapFactor": scrap_factor,
                    "RequiredQty": required_qty_with_scrap,
                    "OnHandQty": onhand_qty,
                    "NetQty": net_qty
                })
            
            print(f"✅ [calculate_mrp_by_brand] MRP计算完成，生成 {len(requirements)} 个需求")
            
            return {
                "bom_info": bom_info,
                "parent_item": parent_item,
                "requirements": requirements,
                "total_required_qty": required_qty
            }
            
        except Exception as e:
            print(f"❌ [calculate_mrp_by_brand] MRP计算时发生错误: {str(e)}")
            return {"error": f"MRP计算失败: {str(e)}"}

    @staticmethod
    def calculate_mrp_for_customer_order(import_id: int, 
                                       include_types: Tuple[str, ...] = ("RM", "PKG")) -> Dict:
        """
        根据客户订单计算MRP需求（基于商品品牌字段）
        
        参数：
        - import_id: 客户订单导入版本ID
        - include_types: 包含的物料类型
        
        返回：
        {
            "order_info": {...},
            "mrp_results": [
                {
                    "brand": "品牌A",
                    "required_qty": 100.0,
                    "bom_info": {...},
                    "requirements": [...]
                }
            ]
        }
        """
        try:
            print(f"📋 [calculate_mrp_for_customer_order] 开始客户订单MRP计算，导入ID：{import_id}")
            
            # 获取客户订单信息
            sql = """
            SELECT DISTINCT col.ItemNumber, col.RequiredQty, col.DeliveryDate,
                   i.ItemId, i.ItemCode, i.CnName, i.Brand
            FROM CustomerOrderLines col
            JOIN CustomerOrders co ON col.OrderId = co.OrderId
            LEFT JOIN Items i ON i.ItemCode = col.ItemNumber
            WHERE co.ImportId = ? AND col.LineStatus = 'Active'
            ORDER BY col.ItemNumber
            """
            
            results = query_all(sql, (import_id,))
            order_lines = [dict(row) for row in results]
            
            print(f"📋 [calculate_mrp_for_customer_order] 找到 {len(order_lines)} 个订单行")
            
            # 显示订单行信息
            for i, line in enumerate(order_lines[:5], 1):  # 显示前5行
                print(f"  订单行{i}：{line.get('ItemNumber', '')} - {line.get('CnName', '')} - 品牌：{line.get('Brand', '')} - 数量：{line.get('RequiredQty', 0)}")
            
            # 按品牌分组计算（使用ItemNumber作为品牌）
            brand_requirements = {}
            for line in order_lines:
                # 根据要求，客户订单提供的PN就是对应成品的商品品牌字段
                brand = line.get("ItemNumber", "")
                if not brand:
                    print(f"⚠️ [calculate_mrp_for_customer_order] 订单行没有物料编码")
                    continue
                
                if brand not in brand_requirements:
                    brand_requirements[brand] = 0.0
                
                brand_requirements[brand] += float(line.get("RequiredQty", 0.0))
            
            print(f"📋 [calculate_mrp_for_customer_order] 按品牌分组结果：{brand_requirements}")
            
            # 计算每个品牌的MRP
            mrp_results = []
            for brand, total_qty in brand_requirements.items():
                print(f"📊 [calculate_mrp_for_customer_order] 计算品牌 {brand} 的MRP，总需求：{total_qty}")
                mrp_result = MRPService.calculate_mrp_by_brand(brand, total_qty, include_types)
                if "error" not in mrp_result:
                    mrp_results.append({
                        "brand": brand,
                        "required_qty": total_qty,
                        "bom_info": mrp_result.get("bom_info", {}),
                        "parent_item": mrp_result.get("parent_item", {}),
                        "requirements": mrp_result.get("requirements", [])
                    })
                    print(f"✅ [calculate_mrp_for_customer_order] 品牌 {brand} MRP计算成功")
                else:
                    print(f"❌ [calculate_mrp_for_customer_order] 品牌 {brand} MRP计算失败：{mrp_result['error']}")
            
            print(f"📊 [calculate_mrp_for_customer_order] 客户订单MRP计算完成，处理了 {len(mrp_results)} 个品牌")
            
            return {
                "import_id": import_id,
                "mrp_results": mrp_results,
                "total_brands": len(brand_requirements),
                "processed_brands": len(mrp_results)
            }
            
        except Exception as e:
            print(f"❌ [calculate_mrp_for_customer_order] 客户订单MRP计算时发生错误: {str(e)}")
            return {"error": f"客户订单MRP计算失败: {str(e)}"}
