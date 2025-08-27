from typing import List, Dict, Optional
from app.db import query_all, query_one, execute


class InventoryService:
    """库存管理服务，操作 InventoryBalance 表"""

    @staticmethod
    def get_all() -> List[Dict]:
        sql = """
            SELECT ib.BalanceId, ib.ItemId, i.ItemCode, i.CnName, ib.QtyOnHand,
                   ib.Warehouse, ib.Location, ib.BatchNo, ib.LastUpdated
            FROM InventoryBalance ib
            JOIN Items i ON ib.ItemId = i.ItemId
            ORDER BY i.ItemCode
        """
        return query_all(sql)

    @staticmethod
    def get_by_item(item_id: int) -> Optional[Dict]:
        sql = """
            SELECT ib.BalanceId, ib.ItemId, i.ItemCode, i.CnName, ib.QtyOnHand,
                   ib.Warehouse, ib.Location, ib.BatchNo, ib.LastUpdated
            FROM InventoryBalance ib
            JOIN Items i ON ib.ItemId = i.ItemId
            WHERE ib.ItemId = ?
        """
        return query_one(sql, (item_id,))

    @staticmethod
    def update_quantity(item_id: int, qty: float, warehouse: str = 'MAIN',
                        location: str = None, batch_no: str = None):
        """更新库存数量，不存在则创建"""
        existing = query_one(
            "SELECT BalanceId FROM InventoryBalance WHERE ItemId = ? AND Warehouse = ? AND ifnull(Location,'') = ifnull(?, '') AND ifnull(BatchNo,'') = ifnull(?, '')",
            (item_id, warehouse, location, batch_no)
        )
        if existing:
            execute(
                """UPDATE InventoryBalance
                       SET QtyOnHand = ?, LastUpdated = CURRENT_TIMESTAMP
                       WHERE BalanceId = ?""",
                (qty, existing['BalanceId'])
            )
        else:
            execute(
                """INSERT INTO InventoryBalance
                       (ItemId, Warehouse, Location, BatchNo, QtyOnHand)
                       VALUES (?, ?, ?, ?, ?)""",
                (item_id, warehouse, location, batch_no, qty)
            )
