# app/services/inventory_import_service.py
# -*- coding: utf-8 -*-
import pandas as pd
import re
from typing import List, Dict, Tuple, Optional
from app.services.inventory_service import InventoryService
from app.services.item_service import ItemService

class InventoryImportService:
    """库存导入服务"""
    
    @staticmethod
    def normalize_code(code: str) -> str:
        """标准化编码：去掉空格、连接符等"""
        if not code:
            return ""
        # 去掉空格、连接符（-、_、.等）
        normalized = re.sub(r'[\s\-_\.]+', '', str(code))
        return normalized.upper()
    
    @staticmethod
    def normalize_spec(spec: str) -> str:
        """标准化规格：去掉空格、连接符等"""
        if not spec:
            return ""
        # 去掉空格、连接符（-、_、.等）
        normalized = re.sub(r'[\s\-_\.]+', '', str(spec))
        return normalized.upper()
    
    @staticmethod
    def find_matching_item(item_code: str, item_spec: str = None) -> Optional[Dict]:
        """根据编码和规格查找匹配的物料"""
        normalized_code = InventoryImportService.normalize_code(item_code)
        normalized_spec = InventoryImportService.normalize_spec(item_spec) if item_spec else ""
        
        # 获取所有物料
        all_items = ItemService.get_all_items()
        
        for item in all_items:
            # 标准化系统物料编码和规格
            sys_code = InventoryImportService.normalize_code(item.get("ItemCode", ""))
            sys_spec = InventoryImportService.normalize_spec(item.get("ItemSpec", ""))
            
            # 编码必须匹配
            if sys_code != normalized_code:
                continue
            
            # 如果导入数据有规格，则规格也必须匹配
            if normalized_spec:
                if sys_spec != normalized_spec:
                    continue
            
            return item
        
        return None
    
    @staticmethod
    def import_inventory_from_excel(file_path: str, warehouse: str = "默认仓库") -> Tuple[bool, str, List[Dict]]:
        """
        从Excel文件导入库存数据（支持重复物资累计计算）
        
        Args:
            file_path: Excel文件路径
            warehouse: 仓库名称
            
        Returns:
            (success, message, details, accumulated_items)
            success: 是否成功
            message: 结果消息
            details: 详细结果列表，包含成功和失败的记录
            accumulated_items: 累计计算的物资列表
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, header=0)
            
            # 智能识别列
            item_code_column = None
            spec_column = None
            qty_column = None
            
            # 查找物料代码列
            for col in df.columns:
                if "物料代码" in str(col):
                    item_code_column = col
                    break
            
            if not item_code_column:
                return False, "Excel文件中未找到'物料代码'列", [], []
            
            # 查找规格型号列
            for col in df.columns:
                if "规格型号" in str(col):
                    spec_column = col
                    break
            
            # 查找数量列
            for col in df.columns:
                if "基本单位数量" in str(col):
                    qty_column = col
                    break
            
            if not qty_column:
                return False, "Excel文件中未找到'基本单位数量'列", [], []
            
            # 记录找到的列信息
            found_columns = f"找到列：物料代码({item_code_column})"
            if spec_column:
                found_columns += f", 规格型号({spec_column})"
            found_columns += f", 数量({qty_column})"
            
            # 预处理：收集所有有效数据并进行累计计算
            raw_data = []
            for index, row in df.iterrows():
                # 跳过最后一行合计行
                if index == len(df) - 1:
                    item_code = str(row.get(item_code_column, "")).strip()
                    if "合计" in item_code or "总计" in item_code or item_code == "":
                        continue
                
                # 获取数据
                item_code = str(row.get(item_code_column, "")).strip()
                item_spec = str(row.get(spec_column, "")).strip() if spec_column else None
                
                try:
                    qty = float(row.get(qty_column, 0))
                except (ValueError, TypeError):
                    qty = 0
                
                # 跳过空行
                if not item_code or item_code == "":
                    continue
                
                raw_data.append({
                    "row": index + 1,
                    "item_code": item_code,
                    "item_spec": item_spec,
                    "qty": qty
                })
            
            # 累计计算：按物料代码和规格分组
            accumulated_data = {}
            duplicate_items = []
            
            for data in raw_data:
                # 创建唯一键：编码+规格
                key = (data["item_code"], data["item_spec"])
                
                if key in accumulated_data:
                    # 重复物资，进行累计
                    accumulated_data[key]["qty"] += data["qty"]
                    accumulated_data[key]["rows"].append(data["row"])
                    accumulated_data[key]["individual_qtys"].append(data["qty"])
                else:
                    # 新物资
                    accumulated_data[key] = {
                        "item_code": data["item_code"],
                        "item_spec": data["item_spec"],
                        "qty": data["qty"],
                        "rows": [data["row"]],
                        "individual_qtys": [data["qty"]]
                    }
            
            # 识别重复物资
            for key, data in accumulated_data.items():
                if len(data["rows"]) > 1:
                    duplicate_items.append({
                        "item_code": data["item_code"],
                        "item_spec": data["item_spec"],
                        "total_qty": data["qty"],
                        "rows": data["rows"],
                        "individual_qtys": data["individual_qtys"]
                    })
            
            # 处理累计后的数据
            results = []
            success_count = 0
            error_count = 0
            
            for key, data in accumulated_data.items():
                # 查找匹配的物料
                matched_item = InventoryImportService.find_matching_item(data["item_code"], data["item_spec"])
                
                if matched_item:
                    try:
                        # 更新库存
                        current_qty = InventoryService.get_onhand(matched_item["ItemId"], warehouse)
                        diff = data["qty"] - current_qty
                        
                        if abs(diff) > 0.001:  # 有差异才更新
                            InventoryService.set_onhand(
                                matched_item["ItemId"], 
                                warehouse, 
                                data["qty"], 
                                remark_prefix=f"Excel导入累计({current_qty}→{data['qty']})"
                            )
                        
                        # 生成消息
                        if len(data["rows"]) > 1:
                            message = f"累计计算：{len(data['rows'])}行数据，总数量 {data['qty']}"
                        else:
                            message = f"库存已更新为 {data['qty']}"
                        
                        results.append({
                            "item_code": data["item_code"],
                            "item_spec": data["item_spec"],
                            "qty": data["qty"],
                            "status": "成功",
                            "message": message,
                            "matched_item": matched_item["ItemCode"],
                            "matched_name": matched_item.get("CnName", ""),
                            "rows": data["rows"],
                            "is_accumulated": len(data["rows"]) > 1
                        })
                        success_count += 1
                        
                    except Exception as e:
                        results.append({
                            "item_code": data["item_code"],
                            "item_spec": data["item_spec"],
                            "qty": data["qty"],
                            "status": "失败",
                            "message": f"更新库存失败：{str(e)}",
                            "matched_item": "",
                            "matched_name": "",
                            "rows": data["rows"],
                            "is_accumulated": len(data["rows"]) > 1
                        })
                        error_count += 1
                else:
                    results.append({
                        "item_code": data["item_code"],
                        "item_spec": data["item_spec"],
                        "qty": data["qty"],
                        "status": "失败",
                        "message": f"未找到匹配的物料（编码：{data['item_code']}" + 
                                 (f"，规格：{data['item_spec']}" if data["item_spec"] else "") + "）",
                        "matched_item": "",
                        "matched_name": "",
                        "rows": data["rows"],
                        "is_accumulated": len(data["rows"]) > 1
                    })
                    error_count += 1
            
            # 生成结果消息
            if success_count > 0 and error_count == 0:
                message = f"导入成功！共处理 {success_count} 条记录\n{found_columns}"
            elif success_count > 0 and error_count > 0:
                message = f"部分成功！成功 {success_count} 条，失败 {error_count} 条\n{found_columns}"
            else:
                message = f"导入失败！共处理 {error_count} 条记录，全部失败\n{found_columns}"
            
            return True, message, results, duplicate_items
            
        except Exception as e:
            return False, f"导入过程中发生错误：{str(e)}", [], []
    
    @staticmethod
    def get_all_inventory_summary() -> List[Dict]:
        """获取所有物料的库存汇总信息"""
        # 获取所有物料
        all_items = ItemService.get_all_items()
        
        summary = []
        for item in all_items:
            # 获取该物料在所有仓库的库存
            balances = InventoryService.get_inventory_balance(item_id=item["ItemId"])
            
            if balances:
                # 有库存记录
                for balance in balances:
                    summary.append({
                        "ItemId": item["ItemId"],
                        "ItemCode": item["ItemCode"],
                        "CnName": item.get("CnName", ""),
                        "ItemType": item.get("ItemType", ""),
                        "ItemSpec": item.get("ItemSpec", ""),
                        "Unit": item.get("Unit", ""),
                        "Warehouse": balance.get("Warehouse", ""),
                        "Location": balance.get("Location", ""),
                        "QtyOnHand": balance.get("QtyOnHand", 0),
                        "SafetyStock": item.get("SafetyStock", 0),
                        "UnitCost": balance.get("UnitCost", 0)
                    })
            else:
                # 没有库存记录，显示为0
                summary.append({
                    "ItemId": item["ItemId"],
                    "ItemCode": item["ItemCode"],
                    "CnName": item.get("CnName", ""),
                    "ItemType": item.get("ItemType", ""),
                    "ItemSpec": item.get("ItemSpec", ""),
                    "Unit": item.get("Unit", ""),
                    "Warehouse": "",
                    "Location": "",
                    "QtyOnHand": 0,
                    "SafetyStock": item.get("SafetyStock", 0),
                    "UnitCost": 0
                })
        
        return summary
