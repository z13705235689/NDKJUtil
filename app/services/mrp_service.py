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
                             parent_item_filter: Optional[str] = None,
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
        # 如果指定了订单版本，使用订单的实际日期范围
        if import_id is not None:
            order_range = MRPService.get_order_version_date_range(import_id)
            if order_range and order_range.get("earliest_date") and order_range.get("latest_date"):
                start_date = order_range["earliest_date"]
                end_date = order_range["latest_date"]
        
        weeks = MRPService._gen_weeks(start_date, end_date)

        # 1) 成品周需求（ItemCode 维度）
        parent_weekly = MRPService._fetch_parent_weekly_demand(
            start_date, end_date, import_id, parent_item_filter
        )

        # 2) 展开到子件周需求
        child_weekly: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        child_meta: Dict[int, Dict] = {}  # ItemId -> {code,name,type}

        for parent_id, wk_map in parent_weekly.items():
            for cw, qty in wk_map.items():
                if qty <= 0:
                    continue
                # 用 BomService.expand_bom 递归展开并考虑损耗
                expanded = BomService.expand_bom(parent_id, qty)
                for e in expanded:
                    itype = e.get("ItemType") or ""
                    if include_types and itype not in include_types:
                        continue
                    cid = int(e["ItemId"])
                    child_weekly[cid][cw] += float(e.get("ActualQty") or 0.0)
                    if cid not in child_meta:
                        child_meta[cid] = {
                            "ItemId": cid,
                            "ItemCode": e.get("ItemCode", ""),
                            "ItemName": e.get("ItemName", ""),
                            "ItemType": itype,
                        }

        # 3) 期初库存（聚合全部仓）
        onhand_all = MRPService._fetch_onhand_total()  # {ItemId: Qty}

        # 4) 生成两行（计划/即时库存）
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

        return {"weeks": weeks, "rows": rows}

    @staticmethod
    def calculate_parent_mrp_kanban(start_date: str, end_date: str,
                                   import_id: Optional[int] = None,
                                   parent_item_filter: Optional[str] = None) -> Dict:
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
            start_date, end_date, import_id, parent_item_filter
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
                "ItemName": meta.get("BomName", meta.get("CnName", "")),  # 优先使用BOM名称
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
                "ItemName": meta.get("BomName", meta.get("CnName", "")),  # 优先使用BOM名称
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
                                   parent_item_filter: Optional[str] = None) -> Dict[int, Dict[str, float]]:
        """
        汇总【成品/半成品】的周需求，结果键为 Items.ItemId
        依赖 CustomerOrderLines.CalendarWeek/RequiredQty
        
        参数：
        - import_id: 指定客户订单版本ID
        - parent_item_filter: 成品筛选，支持模糊匹配
        """
        # 构建WHERE条件
        where_conditions = ["col.LineStatus='Active'", "col.DeliveryDate BETWEEN ? AND ?"]
        params = [start_date, end_date]
        
        if import_id is not None:
            where_conditions.append("co.ImportId = ?")
            params.append(import_id)
        
        if parent_item_filter:
            where_conditions.append("(i.ItemCode LIKE ? OR i.CnName LIKE ?)")
            filter_pattern = f"%{parent_item_filter}%"
            params.extend([filter_pattern, filter_pattern])
        
        where_clause = " AND ".join(where_conditions)
        
        sql = f"""
        SELECT i.ItemId, col.CalendarWeek, SUM(col.RequiredQty) AS Qty
        FROM CustomerOrderLines col
        JOIN CustomerOrders co ON col.OrderId = co.OrderId
        JOIN Items i ON i.ItemCode = col.ItemNumber
        WHERE {where_clause}
        GROUP BY i.ItemId, col.CalendarWeek
        """
        
        rows = query_all(sql, tuple(params))
        out: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for r in rows:
            out[int(r["ItemId"])][r["CalendarWeek"]] += float(r["Qty"] or 0.0)
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
