# app/services/warehouse_service.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
from app.db import query_all, query_one, execute

class WarehouseService:
    """仓库主数据 & 仓库-物料关系"""

    # ---- 仓库 CRUD ----
    @staticmethod
    def list_warehouses(active_only: bool=True) -> List[Dict]:
        sql = "SELECT * FROM Warehouses"
        if active_only:
            sql += " WHERE IsActive=1"
        sql += " ORDER BY Code"
        return [dict(r) for r in query_all(sql)]

    @staticmethod
    def get_by_id(warehouse_id: int) -> Optional[Dict]:
        row = query_one("SELECT * FROM Warehouses WHERE WarehouseId=?", (warehouse_id,))
        return dict(row) if row else None

    @staticmethod
    def get_by_code(warehouse_code: str) -> Optional[Dict]:
        """根据仓库编码获取仓库信息"""
        row = query_one("SELECT * FROM Warehouses WHERE Code=? AND IsActive=1", (warehouse_code,))
        return dict(row) if row else None

    @staticmethod
    def create(code: str, name: str, remark: str="") -> int:
        execute("INSERT INTO Warehouses(Code,Name,Remark) VALUES(?,?,?)", (code, name, remark))
        r = query_one("SELECT last_insert_rowid() AS i"); return r["i"]

    @staticmethod
    def update(warehouse_id: int, data: Dict) -> None:
        execute("""UPDATE Warehouses
                   SET Code=?, Name=?, Remark=?, IsActive=?, UpdatedDate=CURRENT_TIMESTAMP
                   WHERE WarehouseId=?""",
                (data.get("Code"), data.get("Name"), data.get("Remark",""),
                 int(data.get("IsActive",1)), warehouse_id))

    @staticmethod
    def disable(warehouse_id: int) -> None:
        execute("UPDATE Warehouses SET IsActive=0 WHERE WarehouseId=?", (warehouse_id,))
    
    @staticmethod
    def delete(warehouse_id: int) -> None:
        """删除仓库并自动清理相关数据"""
        # 获取仓库编码
        warehouse = query_one("SELECT Code FROM Warehouses WHERE WarehouseId=?", (warehouse_id,))
        if not warehouse:
            raise ValueError("仓库不存在")
        
        warehouse_code = warehouse["Code"]
        
        # 删除相关的库存余额记录
        balance_deleted = execute("DELETE FROM InventoryBalance WHERE Warehouse=?", (warehouse_code,))
        
        # 删除相关的库存流水记录
        tx_deleted = execute("DELETE FROM InventoryTx WHERE Warehouse=?", (warehouse_code,))
        
        # 删除仓库物料关系
        items_deleted = execute("DELETE FROM WarehouseItems WHERE WarehouseId=?", (warehouse_id,))
        
        # 删除仓库
        execute("DELETE FROM Warehouses WHERE WarehouseId=?", (warehouse_id,))
        
        print(f"仓库删除完成：删除了 {balance_deleted} 条库存余额记录，{tx_deleted} 条库存流水记录，{items_deleted} 条物料关联记录")

    # ---- 仓库-物料 ----
    @staticmethod
    def list_items(warehouse_id: int) -> List[Dict]:
        sql = """
        SELECT wi.*, i.ItemCode, i.CnName, i.ItemSpec, i.Unit, i.ItemType
        FROM WarehouseItems wi
        JOIN Items i ON i.ItemId = wi.ItemId
        WHERE wi.WarehouseId=?
        ORDER BY i.ItemType, i.ItemCode
        """
        return [dict(r) for r in query_all(sql, (warehouse_id,))]
    
    @staticmethod
    def list_items_by_warehouse_name(warehouse_name: str) -> List[Dict]:
        """根据仓库名称获取该仓库下的所有物料"""
        sql = """
        SELECT wi.*, i.ItemCode, i.CnName, i.ItemSpec, i.Unit, i.ItemType, i.SafetyStock
        FROM WarehouseItems wi
        JOIN Items i ON i.ItemId = wi.ItemId
        JOIN Warehouses w ON wi.WarehouseId = w.WarehouseId
        WHERE w.Code = ? AND w.IsActive = 1
        ORDER BY i.ItemType, i.ItemCode
        """
        return [dict(r) for r in query_all(sql, (warehouse_name,))]

    @staticmethod
    def add_item(warehouse_id: int, item_id: int, min_qty: float=0, max_qty: float=0, rp: float=0):
        execute("""INSERT OR IGNORE INTO WarehouseItems(WarehouseId,ItemId,MinQty,MaxQty,ReorderPoint)
                   VALUES(?,?,?,?,?)""", (warehouse_id,item_id,min_qty,max_qty,rp))

    @staticmethod
    def remove_item(warehouse_id: int, item_id: int):
        execute("DELETE FROM WarehouseItems WHERE WarehouseId=? AND ItemId=?", (warehouse_id,item_id))
    
    @staticmethod
    def remove_item_from_warehouse(item_id: int, warehouse_name: str):
        """根据仓库名称和物料ID删除物料"""
        # 先获取仓库ID
        warehouse = query_one("SELECT WarehouseId FROM Warehouses WHERE Code=? AND IsActive=1", (warehouse_name,))
        if not warehouse:
            raise ValueError(f"仓库 '{warehouse_name}' 不存在或已停用")
        
        warehouse_id = warehouse["WarehouseId"]
        
        # 删除仓库物料关系
        deleted_count = execute("DELETE FROM WarehouseItems WHERE WarehouseId=? AND ItemId=?", (warehouse_id, item_id))
        
        if deleted_count == 0:
            raise ValueError(f"物料在仓库 '{warehouse_name}' 中不存在")
        
        return deleted_count

    @staticmethod
    def add_items_batch(warehouse_id: int, item_ids: List[int]) -> int:
        """批量添加物料到仓库"""
        added_count = 0
        for item_id in item_ids:
            try:
                execute("""INSERT OR IGNORE INTO WarehouseItems(WarehouseId,ItemId,MinQty,MaxQty,ReorderPoint)
                           VALUES(?,?,0,0,0)""", (warehouse_id, item_id))
                added_count += 1
            except:
                pass
        return added_count

    @staticmethod
    def add_item_by_warehouse_name(warehouse_name: str, item_id: int) -> bool:
        """根据仓库名称添加物料到仓库"""
        try:
            # 先获取仓库ID
            warehouse = query_one("SELECT WarehouseId FROM Warehouses WHERE Code=? AND IsActive=1", (warehouse_name,))
            if not warehouse:
                raise ValueError(f"仓库 '{warehouse_name}' 不存在或已停用")
            
            warehouse_id = warehouse["WarehouseId"]
            
            # 添加物料到仓库
            execute("""INSERT OR IGNORE INTO WarehouseItems(WarehouseId,ItemId,MinQty,MaxQty,ReorderPoint)
                       VALUES(?,?,0,0,0)""", (warehouse_id, item_id))
            
            return True
        except Exception as e:
            print(f"添加物料到仓库失败：{e}")
            return False
