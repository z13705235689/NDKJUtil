#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Dict, Optional, Tuple
from app.db import query_all, query_one, execute

class ProjectService:
    """项目管理服务类 - 管理成品物料和project的映射关系"""
    
    @staticmethod
    def get_all_project_mappings() -> List[Dict]:
        """
        获取所有项目映射关系
        返回：List[Dict] 包含映射信息的列表
        """
        try:
            sql = """
            SELECT 
                pm.MappingId,
                pm.ProjectCode,
                pm.ProjectName,
                pm.ItemId,
                pm.ItemCode,
                pm.ItemName,
                pm.Brand,
                pm.IsActive,
                pm.DisplayOrder,
                pm.CreatedDate,
                pm.UpdatedDate,
                pm.CreatedBy,
                pm.UpdatedBy,
                pm.Remark
            FROM ProjectMappings pm
            ORDER BY pm.DisplayOrder ASC, pm.ProjectCode, pm.ItemCode
            """
            
            results = query_all(sql)
            mappings = [dict(row) for row in results]
            
            print(f"📊 [get_all_project_mappings] 获取到 {len(mappings)} 条项目映射记录")
            return mappings
            
        except Exception as e:
            print(f"❌ [get_all_project_mappings] 获取项目映射失败: {str(e)}")
            raise Exception(f"获取项目映射失败: {str(e)}")
    
    @staticmethod
    def get_project_mapping_by_id(mapping_id: int) -> Optional[Dict]:
        """
        根据ID获取项目映射
        参数：mapping_id - 映射ID
        返回：Dict 映射信息，如果不存在返回None
        """
        try:
            sql = """
            SELECT 
                pm.MappingId,
                pm.ProjectCode,
                pm.ProjectName,
                pm.ItemId,
                pm.ItemCode,
                pm.ItemName,
                pm.Brand,
                pm.IsActive,
                pm.CreatedDate,
                pm.UpdatedDate,
                pm.CreatedBy,
                pm.UpdatedBy,
                pm.Remark
            FROM ProjectMappings pm
            WHERE pm.MappingId = ?
            """
            
            result = query_one(sql, (mapping_id,))
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            print(f"❌ [get_project_mapping_by_id] 获取项目映射失败: {str(e)}")
            raise Exception(f"获取项目映射失败: {str(e)}")
    
    @staticmethod
    def get_project_mappings_by_project_code(project_code: str) -> List[Dict]:
        """
        根据项目代码获取映射关系
        参数：project_code - 项目代码
        返回：List[Dict] 映射信息列表
        """
        try:
            sql = """
            SELECT 
                pm.MappingId,
                pm.ProjectCode,
                pm.ProjectName,
                pm.ItemId,
                pm.ItemCode,
                pm.ItemName,
                pm.Brand,
                pm.IsActive,
                pm.DisplayOrder,
                pm.CreatedDate,
                pm.UpdatedDate,
                pm.CreatedBy,
                pm.UpdatedBy,
                pm.Remark
            FROM ProjectMappings pm
            WHERE pm.ProjectCode = ? AND pm.IsActive = 1
            ORDER BY pm.DisplayOrder, pm.ItemCode
            """
            
            results = query_all(sql, (project_code,))
            mappings = [dict(row) for row in results]
            
            print(f"📊 [get_project_mappings_by_project_code] 项目 {project_code} 有 {len(mappings)} 条映射记录")
            return mappings
            
        except Exception as e:
            print(f"❌ [get_project_mappings_by_project_code] 获取项目映射失败: {str(e)}")
            raise Exception(f"获取项目映射失败: {str(e)}")
    
    @staticmethod
    def get_project_mapping_by_item_id(item_id: int) -> Optional[Dict]:
        """
        根据物料ID获取项目映射
        参数：item_id - 物料ID
        返回：Dict 映射信息，如果不存在返回None
        """
        try:
            sql = """
            SELECT 
                pm.MappingId,
                pm.ProjectCode,
                pm.ProjectName,
                pm.ItemId,
                pm.ItemCode,
                pm.ItemName,
                pm.Brand,
                pm.IsActive,
                pm.CreatedDate,
                pm.UpdatedDate,
                pm.CreatedBy,
                pm.UpdatedBy,
                pm.Remark
            FROM ProjectMappings pm
            WHERE pm.ItemId = ? AND pm.IsActive = 1
            """
            
            result = query_one(sql, (item_id,))
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            print(f"❌ [get_project_mapping_by_item_id] 获取项目映射失败: {str(e)}")
            raise Exception(f"获取项目映射失败: {str(e)}")
    
    @staticmethod
    def get_available_finished_goods() -> List[Dict]:
        """
        获取所有可用的成品物料
        返回：List[Dict] 成品物料列表
        """
        try:
            sql = """
            SELECT 
                i.ItemId,
                i.ItemCode,
                i.CnName,
                i.ItemSpec,
                i.Brand,
                i.IsActive
            FROM Items i
            WHERE i.ItemType = 'FG' AND i.IsActive = 1
            ORDER BY i.ItemCode
            """
            
            results = query_all(sql)
            items = [dict(row) for row in results]
            
            print(f"📊 [get_available_finished_goods] 获取到 {len(items)} 个成品物料")
            return items
            
        except Exception as e:
            print(f"❌ [get_available_finished_goods] 获取成品物料失败: {str(e)}")
            raise Exception(f"获取成品物料失败: {str(e)}")
    
    @staticmethod
    def create_project_mapping(project_code: str, project_name: str, item_id: int, 
                              created_by: str = None, remark: str = None) -> int:
        """
        创建项目映射
        参数：
        - project_code: 项目代码
        - project_name: 项目名称
        - item_id: 物料ID
        - created_by: 创建人
        - remark: 备注
        返回：int 新创建的映射ID
        """
        try:
            # 获取物料信息
            item_sql = "SELECT ItemCode, CnName, Brand FROM Items WHERE ItemId = ?"
            item_result = query_one(item_sql, (item_id,))
            if not item_result:
                raise Exception(f"物料ID {item_id} 不存在")
            
            item_code = item_result["ItemCode"]
            item_name = item_result["CnName"]
            brand = item_result["Brand"]
            
            # 检查是否已存在相同的映射
            check_sql = "SELECT COUNT(*) FROM ProjectMappings WHERE ProjectCode = ? AND ItemId = ?"
            count_result = query_one(check_sql, (project_code, item_id))
            if count_result[0] > 0:
                raise Exception(f"项目 {project_code} 和物料 {item_code} 的映射关系已存在")
            
            # 创建映射
            insert_sql = """
            INSERT INTO ProjectMappings (
                ProjectCode, ProjectName, ItemId, ItemCode, ItemName, Brand,
                CreatedBy, Remark
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            mapping_id = execute(insert_sql, (
                project_code, project_name, item_id, item_code, item_name, brand,
                created_by, remark
            ))
            
            print(f"✅ [create_project_mapping] 成功创建项目映射: {project_code} -> {item_code}")
            return mapping_id
            
        except Exception as e:
            print(f"❌ [create_project_mapping] 创建项目映射失败: {str(e)}")
            raise Exception(f"创建项目映射失败: {str(e)}")
    
    @staticmethod
    def update_project_mapping(mapping_id: int, project_code: str = None, 
                              project_name: str = None, updated_by: str = None, 
                              remark: str = None) -> bool:
        """
        更新项目映射
        参数：
        - mapping_id: 映射ID
        - project_code: 项目代码（可选）
        - project_name: 项目名称（可选）
        - updated_by: 更新人
        - remark: 备注（可选）
        返回：bool 是否更新成功
        """
        try:
            # 构建更新字段
            update_fields = []
            params = []
            
            if project_code is not None:
                update_fields.append("ProjectCode = ?")
                params.append(project_code)
            
            if project_name is not None:
                update_fields.append("ProjectName = ?")
                params.append(project_name)
            
            if updated_by is not None:
                update_fields.append("UpdatedBy = ?")
                params.append(updated_by)
            
            if remark is not None:
                update_fields.append("Remark = ?")
                params.append(remark)
            
            if not update_fields:
                return True  # 没有需要更新的字段
            
            update_fields.append("UpdatedDate = CURRENT_TIMESTAMP")
            params.append(mapping_id)
            
            update_sql = f"""
            UPDATE ProjectMappings 
            SET {', '.join(update_fields)}
            WHERE MappingId = ?
            """
            
            execute(update_sql, params)
            
            print(f"✅ [update_project_mapping] 成功更新项目映射 ID: {mapping_id}")
            return True
            
        except Exception as e:
            print(f"❌ [update_project_mapping] 更新项目映射失败: {str(e)}")
            raise Exception(f"更新项目映射失败: {str(e)}")
    
    @staticmethod
    def delete_project_mapping(mapping_id: int) -> bool:
        """
        删除项目映射（软删除，设置为不活跃）
        参数：mapping_id - 映射ID
        返回：bool 是否删除成功
        """
        try:
            sql = """
            UPDATE ProjectMappings 
            SET IsActive = 0, UpdatedDate = CURRENT_TIMESTAMP
            WHERE MappingId = ?
            """
            
            execute(sql, (mapping_id,))
            
            print(f"✅ [delete_project_mapping] 成功删除项目映射 ID: {mapping_id}")
            return True
            
        except Exception as e:
            print(f"❌ [delete_project_mapping] 删除项目映射失败: {str(e)}")
            raise Exception(f"删除项目映射失败: {str(e)}")
    
    @staticmethod
    def get_all_project_codes() -> List[str]:
        """
        获取所有项目代码
        返回：List[str] 项目代码列表
        """
        try:
            sql = """
            SELECT DISTINCT ProjectCode 
            FROM ProjectMappings 
            WHERE IsActive = 1
            ORDER BY ProjectCode
            """
            
            results = query_all(sql)
            project_codes = [row["ProjectCode"] for row in results]
            
            print(f"📊 [get_all_project_codes] 获取到 {len(project_codes)} 个项目代码")
            return project_codes
            
        except Exception as e:
            print(f"❌ [get_all_project_codes] 获取项目代码失败: {str(e)}")
            raise Exception(f"获取项目代码失败: {str(e)}")
    
    @staticmethod
    def get_project_by_item_brand(brand: str) -> Optional[str]:
        """
        根据物料品牌获取对应的项目代码
        参数：brand - 物料品牌
        返回：str 项目代码，如果不存在返回None
        """
        try:
            sql = """
            SELECT ProjectCode 
            FROM ProjectMappings 
            WHERE Brand = ? AND IsActive = 1
            ORDER BY DisplayOrder ASC
            LIMIT 1
            """
            
            result = query_one(sql, (brand,))
            if result:
                return result["ProjectCode"]
            return None
            
        except Exception as e:
            print(f"❌ [get_project_by_item_brand] 根据品牌获取项目失败: {str(e)}")
            raise Exception(f"根据品牌获取项目失败: {str(e)}")
    
    @staticmethod
    def toggle_mapping_status(mapping_id: int) -> bool:
        """
        切换映射状态（启用/禁用）
        参数：mapping_id - 映射ID
        返回：bool 是否切换成功
        """
        try:
            # 先获取当前状态
            sql = "SELECT IsActive FROM ProjectMappings WHERE MappingId = ?"
            result = query_one(sql, (mapping_id,))
            if not result:
                raise Exception(f"映射ID {mapping_id} 不存在")
            
            current_status = result["IsActive"]
            new_status = 0 if current_status else 1
            
            # 更新状态
            update_sql = """
            UPDATE ProjectMappings 
            SET IsActive = ?, UpdatedDate = CURRENT_TIMESTAMP
            WHERE MappingId = ?
            """
            
            execute(update_sql, (new_status, mapping_id))
            
            status_text = "启用" if new_status else "禁用"
            print(f"✅ [toggle_mapping_status] 成功{status_text}映射 ID: {mapping_id}")
            return True
            
        except Exception as e:
            print(f"❌ [toggle_mapping_status] 切换映射状态失败: {str(e)}")
            raise Exception(f"切换映射状态失败: {str(e)}")
    
    @staticmethod
    def update_mapping_order(mapping_id: int, new_order: int) -> bool:
        """
        更新映射显示顺序
        参数：
        - mapping_id: 映射ID
        - new_order: 新的顺序值
        返回：bool 是否更新成功
        """
        try:
            sql = """
            UPDATE ProjectMappings 
            SET DisplayOrder = ?, UpdatedDate = CURRENT_TIMESTAMP
            WHERE MappingId = ?
            """
            
            execute(sql, (new_order, mapping_id))
            
            print(f"✅ [update_mapping_order] 成功更新映射顺序 ID: {mapping_id}, Order: {new_order}")
            return True
            
        except Exception as e:
            print(f"❌ [update_mapping_order] 更新映射顺序失败: {str(e)}")
            raise Exception(f"更新映射顺序失败: {str(e)}")
    
    @staticmethod
    def batch_update_orders(order_updates: List[Tuple[int, int]]) -> bool:
        """
        批量更新映射顺序
        参数：order_updates - List[Tuple[mapping_id, new_order]]
        返回：bool 是否更新成功
        """
        try:
            for mapping_id, new_order in order_updates:
                ProjectService.update_mapping_order(mapping_id, new_order)
            
            print(f"✅ [batch_update_orders] 成功批量更新 {len(order_updates)} 个映射顺序")
            return True
            
        except Exception as e:
            print(f"❌ [batch_update_orders] 批量更新映射顺序失败: {str(e)}")
            raise Exception(f"批量更新映射顺序失败: {str(e)}")
    
    @staticmethod
    def get_project_mappings_for_display() -> List[Dict]:
        """
        获取用于显示的项目映射（按顺序排列）
        返回：List[Dict] 按DisplayOrder排序的映射列表
        """
        try:
            sql = """
            SELECT 
                pm.MappingId,
                pm.ProjectCode,
                pm.ProjectName,
                pm.ItemId,
                pm.ItemCode,
                pm.ItemName,
                pm.Brand,
                pm.IsActive,
                pm.DisplayOrder,
                pm.CreatedDate,
                pm.UpdatedDate,
                pm.CreatedBy,
                pm.UpdatedBy,
                pm.Remark
            FROM ProjectMappings pm
            ORDER BY pm.DisplayOrder ASC, pm.ProjectCode, pm.ItemCode
            """
            
            results = query_all(sql)
            mappings = [dict(row) for row in results]
            
            print(f"📊 [get_project_mappings_for_display] 获取到 {len(mappings)} 条项目映射记录")
            return mappings
            
        except Exception as e:
            print(f"❌ [get_project_mappings_for_display] 获取项目映射失败: {str(e)}")
            raise Exception(f"获取项目映射失败: {str(e)}")
