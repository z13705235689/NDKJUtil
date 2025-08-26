from typing import List, Dict, Optional
from app.db import query_all, query_one, execute, get_last_id


class ItemService:
    """物料服务类"""
    
    @staticmethod
    def get_all_items():
        """获取所有物料"""
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.IsActive = 1
            ORDER BY i.ItemCode
        """
        return query_all(sql)
    
    @staticmethod
    def get_item_by_id(item_id):
        """根据ID获取物料"""
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.ItemId = ? AND i.IsActive = 1
        """
        return query_one(sql, (item_id,))
    
    @staticmethod
    def create_item(item_data):
        """创建物料"""
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
            item_data.get('ItemType', '物资'),
            item_data.get('Unit', '个'),
            item_data.get('Quantity', 1.0),
            item_data.get('SafetyStock', 0),
            item_data.get('Remark', ''),
            item_data.get('ParentItemId')
        )
        execute(sql, params)
        return get_last_id()
    
    @staticmethod
    def update_item(item_id, item_data):
        """更新物料"""
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
            item_data.get('ItemType', '物资'),
            item_data.get('Unit', '个'),
            item_data.get('Quantity', 1.0),
            item_data.get('SafetyStock', 0),
            item_data.get('Remark', ''),
            item_data.get('ParentItemId'),
            item_id
        )
        execute(sql, params)
    
    @staticmethod
    def delete_item(item_id):
        """删除物料（软删除）"""
        sql = "UPDATE Items SET IsActive = 0 WHERE ItemId = ?"
        execute(sql, (item_id,))
    
    @staticmethod
    def search_items(search_text):
        """搜索物料"""
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.IsActive = 1 AND (
                i.ItemCode LIKE ? OR i.CnName LIKE ? OR i.ItemSpec LIKE ?
            )
            ORDER BY i.ItemCode
        """
        search_pattern = f"%{search_text}%"
        params = (search_pattern, search_pattern, search_pattern)
        return query_all(sql, params)
    
    @staticmethod
    def get_items_by_type(item_type):
        """根据类型获取物料"""
        sql = """
            SELECT i.*, p.ItemCode as ParentItemCode, p.CnName as ParentItemName
            FROM Items i
            LEFT JOIN Items p ON i.ParentItemId = p.ItemId
            WHERE i.ItemType = ? AND i.IsActive = 1
            ORDER BY i.ItemCode
        """
        return query_all(sql, (item_type,))
    
    @staticmethod
    def get_parent_items(exclude_item_id=None):
        """获取可作为上级物料的物料列表"""
        sql = """
            SELECT ItemId, ItemCode, CnName, ItemType
            FROM Items
            WHERE IsActive = 1 AND ItemType IN ('FG', 'SFG', 'RM', 'PKG')
        """
        params = []
        
        # 排除指定的物料ID（防止自己设置自己为父物料）
        if exclude_item_id:
            sql += " AND ItemId != ?"
            params.append(exclude_item_id)
        
        sql += " ORDER BY ItemType, ItemCode"
        return query_all(sql, params)
    
    @staticmethod
    def check_circular_reference(item_id, parent_item_id):
        """检查是否会形成循环引用"""
        if not parent_item_id:
            return False
        
        # 检查父物料的父物料链，看是否存在当前物料
        current_parent_id = parent_item_id
        max_depth = 10  # 防止无限循环
        depth = 0
        
        while current_parent_id and depth < max_depth:
            if current_parent_id == item_id:
                return True  # 发现循环引用
            
            # 获取当前父物料的父物料
            sql = "SELECT ParentItemId FROM Items WHERE ItemId = ? AND IsActive = 1"
            result = query_one(sql, (current_parent_id,))
            current_parent_id = result['ParentItemId'] if result else None
            depth += 1
        
        return False
    
    @staticmethod
    def get_item_hierarchy(item_id):
        """获取物料的层级关系"""
        hierarchy = []
        current_id = item_id
        max_depth = 10  # 防止无限循环
        depth = 0
        
        while current_id and depth < max_depth:
            sql = """
                SELECT i.ItemId, i.ItemCode, i.CnName, i.ParentItemId,
                       p.ItemCode as ParentItemCode, p.CnName as ParentItemName
                FROM Items i
                LEFT JOIN Items p ON i.ParentItemId = p.ItemId
                WHERE i.ItemId = ? AND i.IsActive = 1
            """
            result = query_one(sql, (current_id,))
            if result:
                hierarchy.append(result)
                current_id = result['ParentItemId']
            else:
                break
            depth += 1
        
        return hierarchy
    
    @staticmethod
    def get_item_children(item_id):
        """获取物料的子物料列表"""
        sql = """
            SELECT ItemId, ItemCode, CnName, ItemType, ItemSpec, Unit, Quantity
            FROM Items
            WHERE ParentItemId = ? AND IsActive = 1
            ORDER BY ItemCode
        """
        return query_all(sql, (item_id,))
