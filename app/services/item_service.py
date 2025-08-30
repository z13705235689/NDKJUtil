# app/services/item_service.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
from app.db import query_all, query_one, execute, get_last_id

class ItemService:
    """物料服务类（统一返回 dict）"""

    @staticmethod
    def _rows_to_dicts(rows):
        return [dict(r) for r in rows]

    @staticmethod
    def get_all_items() -> List[Dict]:
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.IsActive = 1
            ORDER BY i.ItemCode
        """
        return ItemService._rows_to_dicts(query_all(sql))

    @staticmethod
    def get_item_by_id(item_id) -> Optional[Dict]:
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.ItemId = ? AND i.IsActive = 1
        """
        row = query_one(sql, (item_id,))
        return dict(row) if row else None

    @staticmethod
    def create_item(item_data) -> int:
        sql = """
            INSERT INTO Items (
                ItemCode, CnName, ItemSpec, ItemType, Unit, Quantity,
                SafetyStock, Remark, ParentItemId
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            item_data.get('ItemCode'),
            item_data.get('CnName'),
            item_data.get('ItemSpec', ''),
            item_data.get('ItemType') or 'RM',     # 与库存口径一致
            item_data.get('Unit', '个'),
            item_data.get('Quantity', 1.0),
            item_data.get('SafetyStock', 0),
            item_data.get('Remark', ''),
            item_data.get('ParentItemId')
        )
        execute(sql, params)
        return get_last_id()

    @staticmethod
    def update_item(item_id, item_data) -> None:
        sql = """
            UPDATE Items SET
                ItemCode = ?, CnName = ?, ItemSpec = ?, ItemType = ?,
                Unit = ?, Quantity = ?, SafetyStock = ?, Remark = ?,
                ParentItemId = ?, UpdatedDate = CURRENT_TIMESTAMP
            WHERE ItemId = ?
        """
        params = (
            item_data.get('ItemCode'),
            item_data.get('CnName'),
            item_data.get('ItemSpec', ''),
            item_data.get('ItemType') or 'RM',
            item_data.get('Unit', '个'),
            item_data.get('Quantity', 1.0),
            item_data.get('SafetyStock', 0),
            item_data.get('Remark', ''),
            item_data.get('ParentItemId'),
            item_id
        )
        execute(sql, params)

    @staticmethod
    def delete_item(item_id) -> None:
        execute("UPDATE Items SET IsActive = 0 WHERE ItemId = ?", (item_id,))

    @staticmethod
    def search_items(search_text: str) -> List[Dict]:
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.IsActive = 1 AND (
                i.ItemCode LIKE ? OR i.CnName LIKE ? OR i.ItemSpec LIKE ?
            )
            ORDER BY i.ItemCode
        """
        pattern = f"%{search_text}%"
        return ItemService._rows_to_dicts(query_all(sql, (pattern, pattern, pattern)))

    @staticmethod
    def get_items_by_type(item_type: str) -> List[Dict]:
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.ItemType = ? AND i.IsActive = 1
            ORDER BY i.ItemCode
        """
        return ItemService._rows_to_dicts(query_all(sql, (item_type,)))

    @staticmethod
    def get_parent_items(exclude_item_id: Optional[int] = None) -> List[Dict]:
        sql = """
            SELECT ItemId, ItemCode, CnName, ItemType
            FROM Items
            WHERE IsActive = 1 AND ItemType IN ('FG', 'SFG', 'RM', 'PKG')
        """
        params: List = []
        if exclude_item_id:
            sql += " AND ItemId != ?"
            params.append(exclude_item_id)
        sql += " ORDER BY ItemType, ItemCode"
        return ItemService._rows_to_dicts(query_all(sql, params))

    @staticmethod
    def check_circular_reference(item_id: int, parent_item_id: Optional[int]) -> bool:
        if not parent_item_id:
            return False
        current_parent_id = parent_item_id
        depth = 0
        while current_parent_id and depth < 10:
            if current_parent_id == item_id:
                return True
            row = query_one("SELECT ParentItemId FROM Items WHERE ItemId=? AND IsActive=1",
                            (current_parent_id,))
            current_parent_id = row['ParentItemId'] if row else None
            depth += 1
        return False

    @staticmethod
    def get_item_hierarchy(item_id: int) -> List[Dict]:
        out: List[Dict] = []
        cur = item_id; depth = 0
        while cur and depth < 10:
            row = query_one("""
                SELECT i.ItemId, i.ItemCode, i.CnName, i.ParentItemId,
                       p.ItemCode as ParentItemCode, p.CnName as ParentItemName
                FROM Items i
                LEFT JOIN Items p ON i.ParentItemId = p.ItemId
                WHERE i.ItemId=? AND i.IsActive=1
            """, (cur,))
            if not row: break
            out.append(dict(row))
            cur = row['ParentItemId']; depth += 1
        return out

    @staticmethod
    def get_item_children(item_id: int) -> List[Dict]:
        sql = """
            SELECT ItemId, ItemCode, CnName, ItemType, ItemSpec, Unit, Quantity
            FROM Items
            WHERE ParentItemId = ? AND IsActive = 1
            ORDER BY ItemCode
        """
        return ItemService._rows_to_dicts(query_all(sql, (item_id,)))
    
    @staticmethod
    def update_safety_stock(item_id: int, safety_stock: float) -> None:
        """更新物料的安全库存"""
        execute("UPDATE Items SET SafetyStock = ?, UpdatedDate = CURRENT_TIMESTAMP WHERE ItemId = ?", 
                (safety_stock, item_id))
