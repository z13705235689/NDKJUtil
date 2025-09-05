#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from typing import List, Dict, Optional
from datetime import datetime
from app.db import query_all, query_one, execute, get_last_id


class BomHistoryService:
    """BOM操作历史服务"""
    
    @staticmethod
    def log_operation(
        bom_id: int,
        operation_type: str,
        operation_target: str,
        target_id: Optional[int] = None,
        old_data: Optional[Dict] = None,
        new_data: Optional[Dict] = None,
        operation_user: str = "系统",
        operation_source: str = "UI",
        remark: str = ""
    ) -> int:
        """
        记录BOM操作历史
        
        Args:
            bom_id: BOM ID
            operation_type: 操作类型 (CREATE, UPDATE, DELETE, IMPORT)
            operation_target: 操作目标 (HEADER, LINE)
            target_id: 目标ID (BomLineId，如果是LINE操作)
            old_data: 操作前的数据
            new_data: 操作后的数据
            operation_user: 操作用户
            operation_source: 操作来源
            remark: 备注
            
        Returns:
            int: 历史记录ID
        """
        try:
            # 将数据转换为JSON字符串
            old_data_json = json.dumps(old_data, ensure_ascii=False) if old_data else None
            new_data_json = json.dumps(new_data, ensure_ascii=False) if new_data else None
            
            sql = """
                INSERT INTO BomOperationHistory (
                    BomId, OperationType, OperationTarget, TargetId,
                    OldData, NewData, OperationUser, OperationSource, Remark
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            history_id = execute(sql, (
                bom_id, operation_type, operation_target, target_id,
                old_data_json, new_data_json, operation_user, operation_source, remark
            ))
            
            print(f"记录BOM操作历史: BOM {bom_id}, {operation_type} {operation_target}")
            return history_id
            
        except Exception as e:
            print(f"记录BOM操作历史失败: {str(e)}")
            return 0
    
    @staticmethod
    def get_bom_history(bom_id: int, limit: int = 100) -> List[Dict]:
        """
        获取BOM操作历史
        
        Args:
            bom_id: BOM ID
            limit: 限制返回数量
            
        Returns:
            List[Dict]: 历史记录列表
        """
        try:
            sql = """
                SELECT h.*, bh.BomName, bh.ParentItemId,
                       pi.ItemCode as ParentItemCode, pi.CnName as ParentItemName
                FROM BomOperationHistory h
                LEFT JOIN BomHeaders bh ON h.BomId = bh.BomId
                LEFT JOIN Items pi ON bh.ParentItemId = pi.ItemId
                WHERE h.BomId = ?
                ORDER BY h.CreatedDate DESC
                LIMIT ?
            """
            
            history_records = query_all(sql, (bom_id, limit))
            
            # 解析JSON数据
            processed_records = []
            for record in history_records:
                # 将Row对象转换为字典
                record_dict = dict(record)
                try:
                    if record_dict['OldData']:
                        record_dict['OldData'] = json.loads(record_dict['OldData'])
                    if record_dict['NewData']:
                        record_dict['NewData'] = json.loads(record_dict['NewData'])
                except json.JSONDecodeError:
                    pass
                processed_records.append(record_dict)
            
            return processed_records
            
        except Exception as e:
            print(f"获取BOM历史失败: {str(e)}")
            return []
    
    @staticmethod
    def get_all_bom_history(limit: int = 200) -> List[Dict]:
        """
        获取所有BOM操作历史
        
        Args:
            limit: 限制返回数量
            
        Returns:
            List[Dict]: 历史记录列表
        """
        try:
            sql = """
                SELECT h.*, bh.BomName, bh.ParentItemId,
                       pi.ItemCode as ParentItemCode, pi.CnName as ParentItemName,
                       ci.ItemCode as ChildItemCode, ci.CnName as ChildItemName
                FROM BomOperationHistory h
                LEFT JOIN BomHeaders bh ON h.BomId = bh.BomId
                LEFT JOIN Items pi ON bh.ParentItemId = pi.ItemId
                LEFT JOIN BomLines bl ON h.TargetId = bl.LineId
                LEFT JOIN Items ci ON bl.ChildItemId = ci.ItemId
                ORDER BY h.CreatedDate DESC
                LIMIT ?
            """
            
            history_records = query_all(sql, (limit,))
            
            # 解析JSON数据
            processed_records = []
            for record in history_records:
                # 将Row对象转换为字典
                record_dict = dict(record)
                try:
                    if record_dict['OldData']:
                        record_dict['OldData'] = json.loads(record_dict['OldData'])
                    if record_dict['NewData']:
                        record_dict['NewData'] = json.loads(record_dict['NewData'])
                except json.JSONDecodeError:
                    pass
                processed_records.append(record_dict)
            
            return processed_records
            
        except Exception as e:
            print(f"获取所有BOM历史失败: {str(e)}")
            return []
    
    @staticmethod
    def get_operation_summary(bom_id: Optional[int] = None) -> Dict:
        """
        获取操作统计摘要
        
        Args:
            bom_id: BOM ID，如果为None则统计所有BOM
            
        Returns:
            Dict: 统计摘要
        """
        try:
            if bom_id:
                sql = """
                    SELECT OperationType, COUNT(*) as Count
                    FROM BomOperationHistory
                    WHERE BomId = ?
                    GROUP BY OperationType
                """
                params = (bom_id,)
            else:
                sql = """
                    SELECT OperationType, COUNT(*) as Count
                    FROM BomOperationHistory
                    GROUP BY OperationType
                """
                params = ()
            
            summary = query_all(sql, params)
            
            result = {
                'total': sum(record['Count'] for record in summary),
                'by_type': {record['OperationType']: record['Count'] for record in summary}
            }
            
            return result
            
        except Exception as e:
            print(f"获取操作统计失败: {str(e)}")
            return {'total': 0, 'by_type': {}}
    
    @staticmethod
    def format_operation_description(record: Dict) -> str:
        """
        格式化操作描述
        
        Args:
            record: 历史记录
            
        Returns:
            str: 格式化的描述
        """
        try:
            bom_name = record.get('BomName', '未知BOM')
            operation_type = record.get('OperationType', '')
            operation_target = record.get('OperationTarget', '')
            created_date = record.get('CreatedDate', '')
            operation_user = record.get('OperationUser', '系统')
            remark = record.get('Remark', '')
            
            # 格式化时间
            if created_date:
                try:
                    dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = created_date
            else:
                time_str = '未知时间'
            
            # 构建描述
            if operation_target == 'HEADER':
                if operation_type == 'CREATE':
                    desc = f"创建BOM: {bom_name}"
                elif operation_type == 'UPDATE':
                    desc = f"更新BOM: {bom_name}"
                elif operation_type == 'DELETE':
                    desc = f"删除BOM: {bom_name}"
                elif operation_type == 'IMPORT':
                    desc = f"导入BOM: {bom_name}"
                else:
                    desc = f"{operation_type} BOM: {bom_name}"
            else:  # LINE
                child_item_name = record.get('ChildItemName', '未知零部件')
                if operation_type == 'CREATE':
                    desc = f"添加零部件: {child_item_name} 到 {bom_name}"
                elif operation_type == 'UPDATE':
                    desc = f"更新零部件: {child_item_name} 在 {bom_name}"
                elif operation_type == 'DELETE':
                    desc = f"删除零部件: {child_item_name} 从 {bom_name}"
                else:
                    desc = f"{operation_type} 零部件: {child_item_name} 在 {bom_name}"
            
            if remark:
                desc += f" ({remark})"
            
            return f"{time_str} - {operation_user} - {desc}"
            
        except Exception as e:
            return f"格式化描述失败: {str(e)}"


if __name__ == "__main__":
    # 测试历史服务
    print("BOM历史服务测试")
    
    # 测试获取历史
    history = BomHistoryService.get_all_bom_history(10)
    print(f"获取到 {len(history)} 条历史记录")
    
    # 测试统计
    summary = BomHistoryService.get_operation_summary()
    print(f"操作统计: {summary}")
