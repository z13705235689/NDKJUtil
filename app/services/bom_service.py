from typing import List, Dict, Optional, Tuple
from app.db import query_all, query_one, execute, get_last_id


class BomService:
    """BOM管理服务"""
    
    @staticmethod
    def get_bom_headers() -> List[Dict]:
        """获取所有BOM主表"""
        try:
            sql = """
                SELECT bh.BomId, bh.BomName, bh.ParentItemId, bh.Rev, bh.EffectiveDate, 
                       bh.ExpireDate, bh.Remark, bh.CreatedDate,
                       i.ItemCode as ParentItemCode, i.CnName as ParentItemName,
                       i.ItemType as ParentItemType
                FROM BomHeaders bh
                LEFT JOIN Items i ON bh.ParentItemId = i.ItemId
                ORDER BY bh.BomName, bh.Rev
            """
            return query_all(sql)
        except Exception as e:
            raise Exception(f"获取BOM列表失败: {str(e)}")
    
    @staticmethod
    def get_bom_by_id(bom_id: int) -> Optional[Dict]:
        """根据ID获取BOM"""
        try:
            sql = """
                SELECT bh.*, i.ItemCode as ParentItemCode, i.CnName as ParentItemName
                FROM BomHeaders bh
                LEFT JOIN Items i ON bh.ParentItemId = i.ItemId
                WHERE bh.BomId = ?
            """
            return query_one(sql, (bom_id,))
        except Exception as e:
            raise Exception(f"获取BOM失败: {str(e)}")
    
    @staticmethod
    def get_bom_by_parent_item(parent_item_id: int, rev: str = None) -> Optional[Dict]:
        """根据父物料获取BOM"""
        try:
            if rev:
                sql = """
                    SELECT bh.*, i.ItemCode as ParentItemCode, i.CnName as ParentItemName
                    FROM BomHeaders bh
                    JOIN Items i ON bh.ParentItemId = i.ItemId
                    WHERE bh.ParentItemId = ? AND bh.Rev = ?
                """
                return query_one(sql, (parent_item_id, rev))
            else:
                sql = """
                    SELECT bh.*, i.ItemCode as ParentItemCode, i.CnName as ParentItemName
                    FROM BomHeaders bh
                    JOIN Items i ON bh.ParentItemId = i.ItemId
                    WHERE bh.ParentItemId = ?
                    ORDER BY bh.Rev DESC
                    LIMIT 1
                """
                return query_one(sql, (parent_item_id,))
        except Exception as e:
            raise Exception(f"获取BOM失败: {str(e)}")
    
    @staticmethod
    def get_bom_lines(bom_id: int) -> List[Dict]:
        """获取BOM明细"""
        try:
            sql = """
                SELECT bl.*, i.ItemCode as ChildItemCode, i.CnName as ChildItemName,
                       i.ItemType as ChildItemType
                FROM BomLines bl
                JOIN Items i ON bl.ChildItemId = i.ItemId
                WHERE bl.BomId = ?
                ORDER BY bl.LineId
            """
            return query_all(sql, (bom_id,))
        except Exception as e:
            raise Exception(f"获取BOM明细失败: {str(e)}")
    
    @staticmethod
    def create_bom_header(bom_data: Dict) -> int:
        """创建BOM主表"""
        try:
            # 验证数据
            if not bom_data.get('BomName'):
                raise ValueError("BOM名称不能为空")
            if not bom_data.get('Rev'):
                raise ValueError("版本号不能为空")
            if not bom_data.get('EffectiveDate'):
                raise ValueError("生效日期不能为空")
            
            # 检查是否已存在相同BOM名称和版本
            existing = query_one(
                "SELECT BomId FROM BomHeaders WHERE BomName = ? AND Rev = ?",
                (bom_data['BomName'], bom_data['Rev'])
            )
            if existing:
                raise ValueError("该BOM名称的版本号已存在")
            
            # 插入BOM主表
            sql = """
                INSERT INTO BomHeaders (BomName, ParentItemId, Rev, EffectiveDate, ExpireDate, Remark)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            bom_id = execute(sql, (
                bom_data['BomName'],
                bom_data.get('ParentItemId'),  # 可选字段
                bom_data['Rev'],
                bom_data['EffectiveDate'],
                bom_data.get('ExpireDate'),
                bom_data.get('Remark', '')
            ))
            
            return bom_id
            
        except Exception as e:
            raise Exception(f"创建BOM失败: {str(e)}")
    
    @staticmethod
    def create_bom_line(bom_id: int, line_data: Dict) -> int:
        """创建BOM明细"""
        try:
            # 验证数据
            if not line_data.get('ChildItemId'):
                raise ValueError("子物料ID不能为空")
            if not line_data.get('QtyPer'):
                raise ValueError("用量不能为空")
            
            # 检查是否已存在相同子物料
            existing = query_one(
                "SELECT LineId FROM BomLines WHERE BomId = ? AND ChildItemId = ?",
                (bom_id, line_data['ChildItemId'])
            )
            if existing:
                raise ValueError("该子物料已存在于BOM中")
            
            # 插入BOM明细
            sql = """
                INSERT INTO BomLines (BomId, ChildItemId, QtyPer, ScrapFactor)
                VALUES (?, ?, ?, ?)
            """
            line_id = execute(sql, (
                bom_id,
                line_data['ChildItemId'],
                line_data['QtyPer'],
                line_data.get('ScrapFactor', 0)
            ))
            
            return line_id
            
        except Exception as e:
            raise Exception(f"创建BOM明细失败: {str(e)}")
    
    @staticmethod
    def update_bom_header(bom_id: int, bom_data: Dict) -> bool:
        """更新BOM主表"""
        try:
            # 验证数据
            if not bom_data.get('BomName'):
                raise ValueError("BOM名称不能为空")
            if not bom_data.get('Rev'):
                raise ValueError("版本号不能为空")
            if not bom_data.get('EffectiveDate'):
                raise ValueError("生效日期不能为空")
            
            # 检查BOM名称和版本号是否被其他BOM使用
            existing = query_one(
                "SELECT BomId FROM BomHeaders WHERE BomName = ? AND Rev = ? AND BomId != ?",
                (bom_data['BomName'], bom_data['Rev'], bom_id)
            )
            if existing:
                raise ValueError("该BOM名称的版本号已被其他BOM使用")
            
            # 更新BOM主表
            sql = """
                UPDATE BomHeaders 
                SET BomName = ?, ParentItemId = ?, Rev = ?, EffectiveDate = ?, ExpireDate = ?, Remark = ?
                WHERE BomId = ?
            """
            execute(sql, (
                bom_data['BomName'],
                bom_data.get('ParentItemId'),
                bom_data['Rev'],
                bom_data['EffectiveDate'],
                bom_data.get('ExpireDate'),
                bom_data.get('Remark', ''),
                bom_id
            ))
            
            return True
            
        except Exception as e:
            raise Exception(f"更新BOM失败: {str(e)}")
    
    @staticmethod
    def update_bom_line(line_id: int, line_data: Dict) -> bool:
        """更新BOM明细"""
        try:
            # 验证数据
            if not line_data.get('ChildItemId'):
                raise ValueError("子物料ID不能为空")
            if not line_data.get('QtyPer'):
                raise ValueError("用量不能为空")
            
            # 更新BOM明细
            sql = """
                UPDATE BomLines 
                SET ChildItemId = ?, QtyPer = ?, ScrapFactor = ?
                WHERE LineId = ?
            """
            execute(sql, (
                line_data['ChildItemId'],
                line_data['QtyPer'],
                line_data.get('ScrapFactor', 0),
                line_id
            ))
            
            return True
            
        except Exception as e:
            raise Exception(f"更新BOM明细失败: {str(e)}")
    
    @staticmethod
    def delete_bom_header(bom_id: int) -> bool:
        """删除BOM主表（会级联删除明细）"""
        try:
            # 删除BOM主表（明细会通过外键约束自动删除）
            execute("DELETE FROM BomHeaders WHERE BomId = ?", (bom_id,))
            return True
            
        except Exception as e:
            raise Exception(f"删除BOM失败: {str(e)}")
    
    @staticmethod
    def delete_bom_line(line_id: int) -> bool:
        """删除BOM明细"""
        try:
            execute("DELETE FROM BomLines WHERE LineId = ?", (line_id,))
            return True
            
        except Exception as e:
            raise Exception(f"删除BOM明细失败: {str(e)}")
    
    @staticmethod
    def expand_bom(parent_item_id: int, qty: float, rev: str = None) -> List[Dict]:
        """展开BOM结构"""
        try:
            # 获取BOM
            bom = BomService.get_bom_by_parent_item(parent_item_id, rev)
            if not bom:
                return []
            
            # 获取BOM明细
            bom_lines = BomService.get_bom_lines(bom['BomId'])
            
            expanded_items = []
            for line in bom_lines:
                # 计算实际用量（考虑损耗）
                actual_qty = line['QtyPer'] * qty * (1 + line['ScrapFactor'])
                
                expanded_items.append({
                    'ItemId': line['ChildItemId'],
                    'ItemCode': line['ChildItemCode'],
                    'ItemName': line['ChildItemName'],
                    'ItemType': line['ChildItemType'],
                    'QtyPer': line['QtyPer'],
                    'ActualQty': actual_qty,
                    'ScrapFactor': line['ScrapFactor'],
                    'Level': 1,
                    'ParentItemId': parent_item_id
                })
                
                # 递归展开子物料的BOM
                child_bom = BomService.get_bom_by_parent_item(line['ChildItemId'])
                if child_bom:
                    child_items = BomService.expand_bom(line['ChildItemId'], actual_qty)
                    for child_item in child_items:
                        child_item['Level'] = child_item.get('Level', 1) + 1
                        expanded_items.append(child_item)
            
            return expanded_items
            
        except Exception as e:
            raise Exception(f"展开BOM失败: {str(e)}")
    
    @staticmethod
    def get_bom_tree(parent_item_id: int, rev: str = None) -> Dict:
        """获取BOM树形结构"""
        try:
            # 获取BOM主表
            bom = BomService.get_bom_by_parent_item(parent_item_id, rev)
            if not bom:
                return {}
            
            # 获取BOM明细
            bom_lines = BomService.get_bom_lines(bom['BomId'])
            
            # 构建树形结构
            tree = {
                'BomId': bom['BomId'],
                'ParentItem': {
                    'ItemId': bom['ParentItemId'],
                    'ItemCode': bom['ParentItemCode'],
                    'ItemName': bom['ParentItemName'],
                    'ItemType': bom['ParentItemType']
                },
                'Rev': bom['Rev'],
                'EffectiveDate': bom['EffectiveDate'],
                'ExpireDate': bom['ExpireDate'],
                'Children': []
            }
            
            for line in bom_lines:
                child_item = {
                    'LineId': line['LineId'],
                    'ItemId': line['ChildItemId'],
                    'ItemCode': line['ChildItemCode'],
                    'ItemName': line['ChildItemName'],
                    'ItemType': line['ChildItemType'],
                    'QtyPer': line['QtyPer'],
                    'ScrapFactor': line['ScrapFactor'],
                    'Children': []
                }
                
                # 递归获取子物料的BOM
                child_bom = BomService.get_bom_by_parent_item(line['ChildItemId'])
                if child_bom:
                    child_tree = BomService.get_bom_tree(line['ChildItemId'])
                    if child_tree:
                        child_item['Children'] = child_tree.get('Children', [])
                
                tree['Children'].append(child_item)
            
            return tree
            
        except Exception as e:
            raise Exception(f"获取BOM树失败: {str(e)}")
    
    @staticmethod
    def validate_bom_structure(bom_id: int) -> List[str]:
        """验证BOM结构（检查循环引用等）"""
        try:
            errors = []
            
            # 获取BOM明细
            bom_lines = BomService.get_bom_lines(bom_id)
            
            # 检查是否有循环引用
            for line in bom_lines:
                if BomService._has_circular_reference(bom_id, line['ChildItemId']):
                    errors.append(f"检测到循环引用: {line['ChildItemCode']}")
            
            # 检查用量是否合理
            for line in bom_lines:
                if line['QtyPer'] <= 0:
                    errors.append(f"用量必须大于0: {line['ChildItemCode']}")
                if line['ScrapFactor'] < 0:
                    errors.append(f"损耗率不能为负数: {line['ChildItemCode']}")
            
            return errors
            
        except Exception as e:
            raise Exception(f"验证BOM结构失败: {str(e)}")
    
    @staticmethod
    def _has_circular_reference(parent_bom_id: int, child_item_id: int, visited: set = None) -> bool:
        """检查是否有循环引用"""
        if visited is None:
            visited = set()
        
        if child_item_id in visited:
            return True
        
        visited.add(child_item_id)
        
        # 获取子物料的BOM
        child_bom = BomService.get_bom_by_parent_item(child_item_id)
        if child_bom:
            bom_lines = BomService.get_bom_lines(child_bom['BomId'])
            for line in bom_lines:
                if BomService._has_circular_reference(parent_bom_id, line['ChildItemId'], visited):
                    return True
        
        visited.remove(child_item_id)
        return False
