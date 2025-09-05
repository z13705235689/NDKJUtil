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
    def get_all_items_with_status() -> List[Dict]:
        """获取所有物料（包括启用和禁用状态），启用的优先显示"""
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            ORDER BY i.IsActive DESC, i.ItemCode
        """
        return ItemService._rows_to_dicts(query_all(sql))

    @staticmethod
    def get_item_by_id(item_id) -> Optional[Dict]:
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.ItemId = ?
        """
        row = query_one(sql, (item_id,))
        return dict(row) if row else None

    @staticmethod
    def create_item(item_data) -> int:
        sql = """
            INSERT INTO Items (
                ItemCode, CnName, ItemSpec, ItemType, Unit, Quantity,
                SafetyStock, Remark, Brand, ParentItemId, IsActive
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            item_data.get('Brand', ''),
            item_data.get('ParentItemId'),
            item_data.get('IsActive', 1)  # 默认启用
        )
        execute(sql, params)
        return get_last_id()

    @staticmethod
    def update_item(item_id, item_data) -> None:
        sql = """
            UPDATE Items SET
                ItemCode = ?, CnName = ?, ItemSpec = ?, ItemType = ?,
                Unit = ?, Quantity = ?, SafetyStock = ?, Remark = ?,
                Brand = ?, ParentItemId = ?, IsActive = ?, UpdatedDate = CURRENT_TIMESTAMP
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
            item_data.get('Brand', ''),
            item_data.get('ParentItemId'),
            item_data.get('IsActive', 1),
            item_id
        )
        execute(sql, params)

    @staticmethod
    def delete_item(item_id) -> None:
        execute("DELETE FROM Items WHERE ItemId = ?", (item_id,))

    @staticmethod
    def toggle_item_status(item_id: int, is_active: bool) -> None:
        """切换物料启用状态"""
        execute("UPDATE Items SET IsActive = ?, UpdatedDate = CURRENT_TIMESTAMP WHERE ItemId = ?", 
                (1 if is_active else 0, item_id))

    @staticmethod
    def search_items(search_text: str) -> List[Dict]:
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE (
                i.ItemCode LIKE ? OR i.CnName LIKE ? OR i.ItemSpec LIKE ? OR i.Brand LIKE ?
            ) AND i.IsActive = 1
            ORDER BY i.ItemCode
        """
        pattern = f"%{search_text}%"
        return ItemService._rows_to_dicts(query_all(sql, (pattern, pattern, pattern, pattern)))

    @staticmethod
    def search_items_with_status(search_text: str) -> List[Dict]:
        """搜索物料（包括启用和禁用状态）"""
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE (
                i.ItemCode LIKE ? OR i.CnName LIKE ? OR i.ItemSpec LIKE ? OR i.Brand LIKE ?
            )
            ORDER BY i.IsActive DESC, i.ItemCode
        """
        pattern = f"%{search_text}%"
        return ItemService._rows_to_dicts(query_all(sql, (pattern, pattern, pattern, pattern)))

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
    def get_items_by_type_with_status(item_type: str) -> List[Dict]:
        """根据类型获取物料（包括启用和禁用状态）"""
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.ItemType = ?
            ORDER BY i.IsActive DESC, i.ItemCode
        """
        return ItemService._rows_to_dicts(query_all(sql, (item_type,)))

    @staticmethod
    def get_parent_items(exclude_item_id: Optional[int] = None) -> List[Dict]:
        sql = """
            SELECT ItemId, ItemCode, CnName, ItemType
            FROM Items
            WHERE ItemType IN ('FG', 'SFG', 'RM', 'PKG') AND IsActive = 1
        """
        params: List = []
        if exclude_item_id:
            sql += " AND ItemId != ?"
            params.append(exclude_item_id)
        sql += " ORDER BY ItemType, ItemCode"
        return ItemService._rows_to_dicts(query_all(sql, params))

    @staticmethod
    def get_parent_items_with_status(exclude_item_id: Optional[int] = None) -> List[Dict]:
        """获取上级物资（包括启用和禁用状态）"""
        sql = """
            SELECT ItemId, ItemCode, CnName, ItemType, IsActive
            FROM Items
            WHERE ItemType IN ('FG', 'SFG', 'RM', 'PKG')
        """
        params: List = []
        if exclude_item_id:
            sql += " AND ItemId != ?"
            params.append(exclude_item_id)
        sql += " ORDER BY IsActive DESC, ItemType, ItemCode"
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
            row = query_one("SELECT ParentItemId FROM Items WHERE ItemId=?",
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
                WHERE i.ItemId=?
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
