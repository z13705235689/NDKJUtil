from typing import List, Dict, Optional, Tuple
from app.db import query_all, query_one, execute, get_last_id
from app.services.bom_history_service import BomHistoryService


class BomService:
    """BOM管理服务"""
    
    @staticmethod
    def get_bom_headers(search_filter: str = None) -> List[Dict]:
        """获取所有BOM主表，支持搜索"""
        try:
            if search_filter:
                # 搜索使用了特定零部件的BOM
                sql = """
                    SELECT DISTINCT bh.BomId, bh.BomName, bh.ParentItemId, bh.Rev, bh.EffectiveDate, 
                           bh.ExpireDate, bh.Remark, bh.CreatedDate,
                           i.ItemCode as ParentItemCode, i.CnName as ParentItemName,
                           i.ItemType as ParentItemType, i.ItemSpec as ParentItemSpec
                    FROM BomHeaders bh
                    LEFT JOIN Items i ON bh.ParentItemId = i.ItemId
                    JOIN BomLines bl ON bh.BomId = bl.BomId
                    JOIN Items child_item ON bl.ChildItemId = child_item.ItemId
                    WHERE (child_item.ItemCode LIKE ? OR child_item.CnName LIKE ? OR child_item.ItemSpec LIKE ?)
                    ORDER BY bh.BomName, bh.Rev
                """
                search_pattern = f"%{search_filter}%"
                results = query_all(sql, (search_pattern, search_pattern, search_pattern))
            else:
                # 获取所有BOM
                sql = """
                    SELECT bh.BomId, bh.BomName, bh.ParentItemId, bh.Rev, bh.EffectiveDate, 
                           bh.ExpireDate, bh.Remark, bh.CreatedDate,
                           i.ItemCode as ParentItemCode, i.CnName as ParentItemName,
                           i.ItemType as ParentItemType, i.ItemSpec as ParentItemSpec
                    FROM BomHeaders bh
                    LEFT JOIN Items i ON bh.ParentItemId = i.ItemId
                    ORDER BY bh.BomName, bh.Rev
                """
                results = query_all(sql)
            
            return [dict(row) for row in results]
        except Exception as e:
            raise Exception(f"获取BOM列表失败: {str(e)}")
    
    @staticmethod
    def get_bom_by_id(bom_id: int) -> Optional[Dict]:
        """根据ID获取BOM"""
        try:
            sql = """
                SELECT bh.*, i.ItemCode as ParentItemCode, i.CnName as ParentItemName,
                       i.ItemSpec as ParentItemSpec, i.Brand as ParentItemBrand
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
                    WHERE bh.ParentItemId = ? AND bh.Rev = ? AND bh.IsActive = 1
                """
                return query_one(sql, (parent_item_id, rev))
            else:
                sql = """
                    SELECT bh.*, i.ItemCode as ParentItemCode, i.CnName as ParentItemName
                    FROM BomHeaders bh
                    JOIN Items i ON bh.ParentItemId = i.ItemId
                    WHERE bh.ParentItemId = ? AND bh.IsActive = 1
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
                       i.ItemType as ChildItemType, i.ItemSpec as ChildItemSpec,
                       i.Brand as ChildItemBrand, 
                       COALESCE(pm.ProjectName, '') as ChildItemProjectName
                FROM BomLines bl
                JOIN Items i ON bl.ChildItemId = i.ItemId
                LEFT JOIN ProjectMappings pm ON i.ItemId = pm.ItemId AND pm.IsActive = 1
                WHERE bl.BomId = ?
                ORDER BY bl.LineId
            """
            results = query_all(sql, (bom_id,))
            return [dict(row) for row in results]
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
            if not bom_data.get('ParentItemId'):
                raise ValueError("父产品不能为空")
            
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
            
            # 记录操作历史
            BomHistoryService.log_operation(
                bom_id=bom_id,
                operation_type='CREATE',
                operation_target='HEADER',
                new_data=bom_data,
                operation_user='系统',
                operation_source='UI',
                remark=f"创建BOM: {bom_data['BomName']}"
            )
            
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
            
            # 记录操作历史
            BomHistoryService.log_operation(
                bom_id=bom_id,
                operation_type='CREATE',
                operation_target='LINE',
                target_id=line_id,
                new_data=line_data,
                operation_user='系统',
                operation_source='UI',
                remark=f"添加零部件到BOM"
            )
            
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
            
            # 获取更新前的数据用于历史记录
            old_bom_data = query_one("SELECT * FROM BomHeaders WHERE BomId = ?", (bom_id,))
            old_data = dict(old_bom_data) if old_bom_data else None
            
            # 检查是否有字段变化
            has_changes = False
            if old_data:
                # 比较关键字段
                changes = []
                if old_data.get('BomName') != bom_data['BomName']:
                    changes.append(f"BOM名称: {old_data.get('BomName')} → {bom_data['BomName']}")
                    has_changes = True
                if old_data.get('ParentItemId') != bom_data.get('ParentItemId'):
                    changes.append(f"父产品ID: {old_data.get('ParentItemId')} → {bom_data.get('ParentItemId')}")
                    has_changes = True
                if old_data.get('Rev') != bom_data['Rev']:
                    changes.append(f"版本号: {old_data.get('Rev')} → {bom_data['Rev']}")
                    has_changes = True
                if old_data.get('EffectiveDate') != bom_data['EffectiveDate']:
                    changes.append(f"生效日期: {old_data.get('EffectiveDate')} → {bom_data['EffectiveDate']}")
                    has_changes = True
                if old_data.get('ExpireDate') != bom_data.get('ExpireDate'):
                    changes.append(f"失效日期: {old_data.get('ExpireDate')} → {bom_data.get('ExpireDate')}")
                    has_changes = True
                if old_data.get('Remark', '') != bom_data.get('Remark', ''):
                    changes.append(f"备注: {old_data.get('Remark', '')} → {bom_data.get('Remark', '')}")
                    has_changes = True
                
                # 如果没有变化，直接返回
                if not has_changes:
                    print(f"调试 - BOM主表无变化，跳过更新")
                    return True
                
                print(f"调试 - BOM主表变化: {'; '.join(changes)}")
            else:
                has_changes = True
            
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
            
            # 记录更新历史（只有变化时才记录）
            if has_changes:
                BomHistoryService.log_operation(
                    bom_id=bom_id,
                    operation_type='UPDATE',
                    operation_target='HEADER',
                    old_data=old_data,
                    new_data=bom_data,
                    operation_user='系统',
                    operation_source='UI',
                    remark=f"编辑BOM: {bom_data['BomName']}"
                )
            
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
            
            # 获取更新前的数据用于历史记录
            old_line_data = query_one("SELECT * FROM BomLines WHERE LineId = ?", (line_id,))
            old_data = dict(old_line_data) if old_line_data else None
            
            # 获取BOM ID用于历史记录
            bom_id = old_line_data['BomId'] if old_line_data else None
            
            # 检查是否有字段变化
            has_changes = False
            if old_data:
                # 比较关键字段
                changes = []
                if old_data.get('ChildItemId') != line_data['ChildItemId']:
                    changes.append(f"子物料ID: {old_data.get('ChildItemId')} → {line_data['ChildItemId']}")
                    has_changes = True
                if old_data.get('QtyPer', 0) != line_data['QtyPer']:
                    changes.append(f"用量: {old_data.get('QtyPer', 0)} → {line_data['QtyPer']}")
                    has_changes = True
                if old_data.get('ScrapFactor', 0) != line_data.get('ScrapFactor', 0):
                    changes.append(f"损耗率: {old_data.get('ScrapFactor', 0)} → {line_data.get('ScrapFactor', 0)}")
                    has_changes = True
                
                # 如果没有变化，直接返回
                if not has_changes:
                    print(f"调试 - BOM明细无变化，跳过更新")
                    return True
                
                print(f"调试 - BOM明细变化: {'; '.join(changes)}")
            else:
                has_changes = True
            
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
            
            # 记录更新历史（只有变化时才记录）
            if bom_id and has_changes:
                BomHistoryService.log_operation(
                    bom_id=bom_id,
                    operation_type='UPDATE',
                    operation_target='LINE',
                    target_id=line_id,
                    old_data=old_data,
                    new_data=line_data,
                    operation_user='系统',
                    operation_source='UI',
                    remark=f"编辑BOM明细"
                )
            
            return True
            
        except Exception as e:
            raise Exception(f"更新BOM明细失败: {str(e)}")
    
    @staticmethod
    def delete_bom_header(bom_id: int) -> bool:
        """删除BOM主表（会级联删除明细）"""
        try:
            # 获取删除前的数据用于历史记录
            old_bom_data = query_one("SELECT * FROM BomHeaders WHERE BomId = ?", (bom_id,))
            old_data = dict(old_bom_data) if old_bom_data else None
            
            # 获取BOM明细数据用于历史记录
            old_lines_data = query_all("SELECT * FROM BomLines WHERE BomId = ?", (bom_id,))
            old_lines = [dict(line) for line in old_lines_data] if old_lines_data else []
            
            # 记录BOM明细删除历史（在删除前记录）
            for line in old_lines:
                BomHistoryService.log_operation(
                    bom_id=bom_id,
                    operation_type='DELETE',
                    operation_target='LINE',
                    target_id=line['LineId'],
                    old_data=line,
                    operation_user='系统',
                    operation_source='UI',
                    remark=f"删除BOM时删除明细"
                )
            
            # 记录BOM主表删除历史
            BomHistoryService.log_operation(
                bom_id=bom_id,
                operation_type='DELETE',
                operation_target='HEADER',
                old_data=old_data,
                operation_user='系统',
                operation_source='UI',
                remark=f"删除BOM: {old_data.get('BomName', '') if old_data else ''}"
            )
            
            # 删除BOM主表（明细会通过外键约束自动删除）
            execute("DELETE FROM BomHeaders WHERE BomId = ?", (bom_id,))
            return True
            
        except Exception as e:
            raise Exception(f"删除BOM失败: {str(e)}")
    
    @staticmethod
    def delete_bom_line(line_id: int) -> bool:
        """删除BOM明细"""
        try:
            # 获取删除前的数据用于历史记录
            old_line_data = query_one("SELECT * FROM BomLines WHERE LineId = ?", (line_id,))
            old_data = dict(old_line_data) if old_line_data else None
            
            # 获取BOM ID用于历史记录
            bom_id = old_line_data['BomId'] if old_line_data else None
            
            # 记录删除历史
            if bom_id and old_data:
                BomHistoryService.log_operation(
                    bom_id=bom_id,
                    operation_type='DELETE',
                    operation_target='LINE',
                    target_id=line_id,
                    old_data=old_data,
                    operation_user='系统',
                    operation_source='UI',
                    remark=f"删除BOM明细"
                )
            
            execute("DELETE FROM BomLines WHERE LineId = ?", (line_id,))
            return True
            
        except Exception as e:
            raise Exception(f"删除BOM明细失败: {str(e)}")
    
    @staticmethod
    def get_bom_status(bom_id: int) -> str:
        """
        获取BOM状态
        返回: '有效' 或 '失效'
        """
        try:
            # 获取BOM信息
            bom = query_one("SELECT * FROM BomHeaders WHERE BomId = ?", (bom_id,))
            if not bom:
                return '未知'
            
            bom = dict(bom)
            
            # 检查父产品状态
            parent_item = query_one("SELECT IsActive FROM Items WHERE ItemId = ?", (bom.get('ParentItemId'),))
            if not parent_item or parent_item['IsActive'] != 1:
                return '失效'
            
            # 检查所有零部件状态
            bom_lines = query_all("""
                SELECT i.IsActive 
                FROM BomLines bl 
                JOIN Items i ON bl.ChildItemId = i.ItemId 
                WHERE bl.BomId = ?
            """, (bom_id,))
            
            for line in bom_lines:
                if line['IsActive'] != 1:
                    return '失效'
            
            return '有效'
            
        except Exception as e:
            print(f"获取BOM状态失败: {str(e)}")
            return '未知'
    
    @staticmethod
    def get_bom_status_details(bom_id: int) -> Dict:
        """
        获取BOM状态详细信息
        返回: {
            'status': '有效'/'失效',
            'parent_status': '启用'/'禁用',
            'disabled_components': [{'name': 'xxx', 'code': 'xxx'}]
        }
        """
        try:
            # 获取BOM信息
            bom = query_one("SELECT * FROM BomHeaders WHERE BomId = ?", (bom_id,))
            if not bom:
                return {'status': '未知', 'parent_status': '未知', 'disabled_components': []}
            
            bom = dict(bom)
            disabled_components = []
            
            # 检查父产品状态
            parent_item = query_one("""
                SELECT IsActive, CnName, ItemCode 
                FROM Items 
                WHERE ItemId = ?
            """, (bom.get('ParentItemId'),))
            
            parent_status = '未知'
            if parent_item:
                parent_status = '启用' if parent_item['IsActive'] == 1 else '禁用'
                if parent_item['IsActive'] != 1:
                    disabled_components.append({
                        'name': parent_item['CnName'],
                        'code': parent_item['ItemCode'],
                        'type': '父产品'
                    })
            
            # 检查所有零部件状态
            bom_lines = query_all("""
                SELECT i.IsActive, i.CnName, i.ItemCode 
                FROM BomLines bl 
                JOIN Items i ON bl.ChildItemId = i.ItemId 
                WHERE bl.BomId = ?
            """, (bom_id,))
            
            for line in bom_lines:
                if line['IsActive'] != 1:
                    disabled_components.append({
                        'name': line['CnName'],
                        'code': line['ItemCode'],
                        'type': '零部件'
                    })
            
            # 确定整体状态
            status = '有效' if parent_status == '启用' and len(disabled_components) == 0 else '失效'
            
            return {
                'status': status,
                'parent_status': parent_status,
                'disabled_components': disabled_components
            }
            
        except Exception as e:
            print(f"获取BOM状态详情失败: {str(e)}")
            return {'status': '未知', 'parent_status': '未知', 'disabled_components': []}

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
                
                # 获取Brand和ProjectName数据
                brand_value = line.get('ChildItemBrand', '')  # 商品品牌字段
                project_name_value = line.get('ChildItemProjectName', '')
                
                # 如果ProjectName为空，根据商品品牌字段从项目映射表获取
                if not project_name_value and brand_value:
                    try:
                        from app.services.project_service import ProjectService
                        project_code = ProjectService.get_project_by_item_brand(brand_value)
                        if project_code:
                            mappings = ProjectService.get_project_mappings_by_project_code(project_code)
                            if mappings:
                                project_name_value = mappings[0].get('ProjectName', project_code)
                    except Exception as e:
                        print(f"获取项目名称失败: {e}")
                
                print(f"🔍 [expand_bom] 展开物料 {line['ChildItemCode']}: Brand='{brand_value}', ProjectName='{project_name_value}'")
                
                expanded_items.append({
                    'ItemId': line['ChildItemId'],
                    'ItemCode': line['ChildItemCode'],
                    'ItemName': line['ChildItemName'],
                    'ItemSpec': line['ChildItemSpec'],
                    'ItemType': line['ChildItemType'],
                    'Brand': brand_value,
                    'ProjectName': project_name_value,
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
