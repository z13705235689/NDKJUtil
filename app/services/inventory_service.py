# app/services/inventory_service.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
from datetime import date
from app.db import query_all, query_one, execute

class InventoryService:
    """
    库存管理服务（增强版）
    - 统一“流水→余额”联动：IN/OUT/ADJ 自动更新 InventoryBalance
    - 默认只针对 RM/PKG 查询；FG/SFG 可按需传参
    """

    # -------------------- 查询与概览 --------------------
    @staticmethod
    def get_inventory_balance(item_id: int = None,
                              warehouse: Optional[str] = None,
                              item_types: Optional[List[str]] = None) -> List[Dict]:
        """获取库存余额（默认 RM/PKG）"""
        where = ["i.IsActive = 1", "ib.ItemId = i.ItemId"]
        params: List = []

        if item_types:
            where.append(f"i.ItemType IN ({','.join(['?']*len(item_types))})")
            params.extend(item_types)

        if item_id:
            where.append("ib.ItemId = ?")
            params.append(item_id)

        if warehouse:
            where.append("ib.Warehouse = ?")
            params.append(warehouse)

        sql = f"""
            SELECT ib.*, i.ItemCode, i.CnName, i.ItemType, i.Unit, i.SafetyStock
            FROM InventoryBalance ib
            JOIN Items i ON ib.ItemId = i.ItemId
            WHERE {' AND '.join(where)}
            ORDER BY i.ItemType, i.ItemCode, ib.Warehouse, ib.Location
        """
        return [dict(r) for r in query_all(sql, tuple(params))]

    @staticmethod
    def get_warehouses() -> List[str]:
        # 优先读新表 Warehouses；没有则从余额/流水兜底
        rows = query_all("SELECT Code FROM Warehouses WHERE IsActive=1 ORDER BY Code")
        if rows:
            return [r["Code"] for r in rows]
        rows = query_all("""
            SELECT Warehouse FROM (
                SELECT DISTINCT Warehouse FROM InventoryBalance
                UNION
                SELECT DISTINCT Warehouse FROM InventoryTx
            ) t WHERE Warehouse IS NOT NULL AND Warehouse <> ''
            ORDER BY Warehouse
        """)
        return [r["Warehouse"] for r in rows] or ["默认仓库"]

    @staticmethod
    def get_inventory_summary() -> Dict:
        total_items = query_one("SELECT COUNT(*) AS c FROM Items WHERE IsActive=1")["c"]
        items_with_stock = query_one("""
            SELECT COUNT( DISTINCT ib.ItemId ) AS c
            FROM InventoryBalance ib
            JOIN Items i ON i.ItemId = ib.ItemId
            WHERE i.IsActive=1 AND ib.QtyOnHand > 0
        """)["c"]
        total_value = query_one("""
            SELECT COALESCE(SUM(ib.QtyOnHand*COALESCE(ib.UnitCost,0)),0) AS v
            FROM InventoryBalance ib
        """)["v"]
        low_sql = """
            SELECT COUNT(1) AS c
            FROM (
                SELECT i.ItemId, i.SafetyStock, COALESCE(SUM(ib.QtyOnHand),0) AS onhand
                FROM Items i
                LEFT JOIN InventoryBalance ib ON ib.ItemId=i.ItemId
                WHERE i.IsActive=1
                GROUP BY i.ItemId
            ) t WHERE SafetyStock>0 AND onhand < SafetyStock
        """
        low_count = query_one(low_sql)["c"]
        return dict(total_items=total_items, items_with_stock=items_with_stock,
                    total_value=total_value, low_stock=low_count)

    # -------------------- 余额联动底层 --------------------
    @staticmethod
    def _upsert_balance(item_id: int, warehouse: str, qty_delta: float,
                        unit_cost: Optional[float] = None, location: Optional[str] = None) -> None:
        row = query_one("""
            SELECT QtyOnHand, UnitCost
            FROM InventoryBalance
            WHERE ItemId=? AND Warehouse=? AND IFNULL(Location,'')=IFNULL(?, '')
        """, (item_id, warehouse, location))
        if row:
            new_qty = max(0, (row["QtyOnHand"] or 0) + qty_delta)
            new_cost = unit_cost if unit_cost is not None else row["UnitCost"]
            execute("""
                UPDATE InventoryBalance
                SET QtyOnHand=?, UnitCost=?, LastUpdated=CURRENT_TIMESTAMP
                WHERE ItemId=? AND Warehouse=? AND IFNULL(Location,'')=IFNULL(?, '')
            """, (new_qty, new_cost, item_id, warehouse, location))
        else:
            if qty_delta > 0:  # 首次正数才建余额
                execute("""
                    INSERT INTO InventoryBalance
                    (ItemId, Warehouse, Location, QtyOnHand, UnitCost, LastUpdated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (item_id, warehouse, location, qty_delta, unit_cost or 0))

    # -------------------- 流水接口（统一入口） --------------------
    @staticmethod
    def add_inventory_transaction(tx: Dict) -> int:
        """
        tx = {ItemId, TxDate, TxType(IN/OUT/ADJ), Qty, UnitCost?,
              Warehouse, Location?, BatchNo?, RefType?, RefId?, Remark?}
        """
        qty = float(tx.get("Qty", 0) or 0)
        if qty == 0:
            return 0

        tx_id = execute("""
            INSERT INTO InventoryTx
            (ItemId, TxDate, TxType, Qty, UnitCost, TotalCost,
             Warehouse, Location, BatchNo, RefType, RefId, Remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tx["ItemId"], tx.get("TxDate") or date.today().strftime("%Y-%m-%d"),
            tx["TxType"], qty, tx.get("UnitCost"),
            (qty*(tx.get("UnitCost") or 0)) if tx.get("TxType")!="OUT" else None,
            tx.get("Warehouse") or "默认仓库",
            tx.get("Location"), tx.get("BatchNo"),
            tx.get("RefType"), tx.get("RefId"), tx.get("Remark","")
        ))

        if tx["TxType"] == "IN":
            InventoryService._upsert_balance(tx["ItemId"], tx.get("Warehouse") or "默认仓库",
                                             qty, unit_cost=tx.get("UnitCost"),
                                             location=tx.get("Location"))
        elif tx["TxType"] == "OUT":
            InventoryService._upsert_balance(tx["ItemId"], tx.get("Warehouse") or "默认仓库",
                                             -qty, location=tx.get("Location"))
        elif tx["TxType"] == "ADJ":
            InventoryService._upsert_balance(tx["ItemId"], tx.get("Warehouse") or "默认仓库",
                                             qty, unit_cost=tx.get("UnitCost"),
                                             location=tx.get("Location"))
        return tx_id

    @staticmethod
    def receive_inventory(item_id: int, qty: float, warehouse: str,
                          unit_cost: float = None, location: Optional[str]=None,
                          remark: str = "收货入库") -> bool:
        InventoryService.add_inventory_transaction(dict(
            ItemId=item_id, TxType="IN", Qty=qty,
            UnitCost=unit_cost, Warehouse=warehouse,
            Location=location, Remark=remark
        ))
        return True

    @staticmethod
    def issue_inventory(item_id: int, qty: float, warehouse: str,
                        location: Optional[str]=None, remark: str = "发料出库") -> bool:
        InventoryService.add_inventory_transaction(dict(
            ItemId=item_id, TxType="OUT", Qty=qty,
            Warehouse=warehouse, Location=location, Remark=remark
        ))
        return True

    @staticmethod
    def adjust_inventory(item_id: int, qty: float, warehouse: str,
                         unit_cost: float = None, location: Optional[str]=None,
                         reason: str = "库存调整") -> bool:
        InventoryService.add_inventory_transaction(dict(
            ItemId=item_id, TxType="ADJ", Qty=qty,
            UnitCost=unit_cost, Warehouse=warehouse, Location=location, Remark=reason
        ))
        return True

    # -------------------- 登记现存 / 快速消耗 --------------------
    @staticmethod
    def get_onhand(item_id: int, warehouse: str, location: Optional[str]=None) -> float:
        row = query_one("""
            SELECT COALESCE(QtyOnHand,0) AS q
            FROM InventoryBalance
            WHERE ItemId=? AND Warehouse=? AND IFNULL(Location,'')=IFNULL(?, '')
        """, (item_id, warehouse, location))
        return float(row["q"]) if row else 0.0

    @staticmethod
    def set_onhand(item_id: int, warehouse: str, target_qty: float,
                   location: Optional[str]=None, remark_prefix: str="现存登记") -> float:
        onhand = InventoryService.get_onhand(item_id, warehouse, location)
        diff = float(target_qty) - float(onhand)
        if abs(diff) < 1e-9:
            return 0.0
        InventoryService.add_inventory_transaction(dict(
            ItemId=item_id, TxType="ADJ", Qty=diff, Warehouse=warehouse,
            Location=location, Remark=f"{remark_prefix}({onhand}→{target_qty})"
        ))
        return diff

    @staticmethod
    def consume(item_id: int, qty: float, warehouse: str,
                location: Optional[str]=None, remark: str="消耗出库") -> bool:
        return InventoryService.issue_inventory(item_id, qty, warehouse, location, remark)

    # -------------------- 批量与流水查询 --------------------
    @staticmethod
    def batch_post(trans: List[Dict]) -> int:
        ok = 0
        for t in trans:
            try:
                InventoryService.add_inventory_transaction(t); ok += 1
            except Exception as e:
                print("批量记账失败:", e, t)
        return ok

    @staticmethod
    def list_transactions(item_id: int = None, tx_type: str = None,
                          start_date: str = None, end_date: str = None,
                          warehouse: Optional[str]=None,
                          item_types: Optional[List[str]] = None) -> List[Dict]:
        where = ["i.ItemId = it.ItemId", "i.IsActive=1"]
        params: List = []
        if not item_types:
            item_types = ["RM","PKG"]
        where.append(f"i.ItemType IN ({','.join(['?']*len(item_types))})")
        params.extend(item_types)
        if item_id:   where.append("it.ItemId = ?");   params.append(item_id)
        if tx_type:   where.append("it.TxType = ?");   params.append(tx_type)
        if start_date:where.append("it.TxDate >= ?");  params.append(start_date)
        if end_date:  where.append("it.TxDate <= ?");  params.append(end_date)
        if warehouse: where.append("it.Warehouse = ?");params.append(warehouse)

        sql = f"""
            SELECT it.*, i.ItemCode, i.CnName, i.ItemType, i.Unit
            FROM InventoryTx it
            JOIN Items i ON i.ItemId = it.ItemId
            WHERE {' AND '.join(where)}
            ORDER BY it.TxDate DESC, it.TxId DESC
        """
        return [dict(r) for r in query_all(sql, tuple(params))]