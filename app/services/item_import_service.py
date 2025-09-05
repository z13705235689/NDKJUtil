# app/services/item_import_service.py
# -*- coding: utf-8 -*-
import pandas as pd
from typing import List, Dict, Optional, Tuple
from app.services.item_service import ItemService

class ItemImportService:
    """物料导入服务类"""
    
    @staticmethod
    def parse_item_type_from_fullname(fullname: str) -> str:
        """
        根据全名的前4-5个字解析物资类型
        检查各种可能的物资类型标识
        """
        if not fullname:
            return 'RM'
        
        # 转换为小写以便匹配
        fullname_lower = fullname.lower()
        
        # 检查前5个字符的匹配
        if len(fullname) >= 5:
            prefix5 = fullname[:5]
            if '原材料' in prefix5:
                return 'RM'
            elif '包装材料' in prefix5:
                return 'PKG'
        
        # 检查前4个字符的匹配
        if len(fullname) >= 4:
            prefix4 = fullname[:4]
            if '半成品' in prefix4:
                return 'SFG'
            elif '包装材' in prefix4:
                return 'PKG'
        
        # 检查前3个字符的匹配
        if len(fullname) >= 3:
            prefix3 = fullname[:3]
            if '原材' in prefix3:
                return 'RM'
        
        # 检查前2个字符的匹配
        if len(fullname) >= 2:
            prefix2 = fullname[:2]
            if prefix2 == '成品':
                return 'FG'
            elif prefix2 == '原材':
                return 'RM'
        
        # 如果都没匹配到，检查整个字符串是否包含关键词（注意顺序，先检查更具体的）
        if '原材料' in fullname:
            return 'RM'
        elif '半成品' in fullname:
            return 'SFG'
        elif '成品' in fullname:
            return 'FG'
        elif '包装' in fullname:
            return 'PKG'
        
        # 默认返回原材料
        return 'RM'
    
    @staticmethod
    def validate_import_data(data: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        验证导入数据
        返回: (有效数据列表, 错误信息列表)
        """
        valid_data = []
        errors = []
        
        for i, row in enumerate(data, start=1):
            row_errors = []
            
            # 检查必填字段
            if not row.get('代码'):
                row_errors.append(f"第{i}行：代码不能为空")
            if not row.get('名称'):
                row_errors.append(f"第{i}行：名称不能为空")
            
            # 检查代码格式和长度
            code = row.get('代码', '').strip()
            if code and len(code) > 50:
                row_errors.append(f"第{i}行：代码长度不能超过50个字符")
            
            # 检查名称长度
            name = row.get('名称', '').strip()
            if name and len(name) > 100:
                row_errors.append(f"第{i}行：名称长度不能超过100个字符")
            
            if row_errors:
                errors.extend(row_errors)
            else:
                valid_data.append(row)
        
        return valid_data, errors
    
    @staticmethod
    def convert_to_item_data(row: Dict) -> Dict:
        """
        将导入行数据转换为物料数据格式
        """
        # 解析物资类型
        fullname = row.get('全名', '')
        item_type = ItemImportService.parse_item_type_from_fullname(fullname)
        
        # 处理商品品牌字段 - 只有成品才保存品牌信息
        brand = ''
        if item_type == 'FG' and row.get('商品品牌'):
            brand = str(row.get('商品品牌', '')).strip()
        
        return {
            'ItemCode': str(row.get('代码', '')).strip(),
            'CnName': str(row.get('名称', '')).strip(),
            'ItemSpec': str(row.get('规格型号', '')).strip(),
            'ItemType': item_type,
            'Unit': '个',  # 默认单位
            'Quantity': 1.0,  # 默认数量
            'SafetyStock': 0,  # 默认安全库存
            'Remark': f"通过导入创建，全名：{fullname}" if fullname else "通过导入创建",
            'Brand': brand,
            'ParentItemId': None,  # 导入时不设置上级物资
            'IsActive': 1  # 导入时默认启用
        }
    
    @staticmethod
    def check_duplicate_codes(data: List[Dict]) -> Tuple[List[str], List[str]]:
        """
        检查重复的物料编码
        返回: (导入数据中重复的编码, 与数据库中重复的编码)
        """
        import_codes = [row.get('代码', '').strip() for row in data if row.get('代码')]
        
        # 检查导入数据内部重复
        seen_codes = set()
        import_duplicates = []
        for code in import_codes:
            if code in seen_codes:
                if code not in import_duplicates:
                    import_duplicates.append(code)
            else:
                seen_codes.add(code)
        
        # 检查与数据库中的重复
        db_duplicates = []
        for code in seen_codes:
            if code:
                existing_items = ItemService.search_items(code)
                if any(item['ItemCode'] == code for item in existing_items):
                    db_duplicates.append(code)
        
        return import_duplicates, db_duplicates
    
    @staticmethod
    def import_items(data: List[Dict]) -> Tuple[int, List[str], List[str]]:
        """
        批量导入物料
        返回: (成功导入数量, 错误信息列表, 跳过的编码列表)
        """
        success_count = 0
        errors = []
        skipped_codes = []
        
        # 数据验证
        valid_data, validation_errors = ItemImportService.validate_import_data(data)
        if validation_errors:
            errors.extend(validation_errors)
            return 0, errors, skipped_codes
        
        # 检查导入数据内部重复编码
        import_duplicates, _ = ItemImportService.check_duplicate_codes(valid_data)
        if import_duplicates:
            errors.append(f"导入数据中存在重复编码: {', '.join(import_duplicates)}")
            return 0, errors, skipped_codes
        
        # 执行导入
        for i, row in enumerate(valid_data, start=1):
            try:
                code = row.get('代码', '').strip()
                
                # 检查编码是否已存在
                existing_items = ItemService.search_items(code)
                if any(item['ItemCode'] == code for item in existing_items):
                    skipped_codes.append(code)
                    continue  # 跳过已存在的编码
                
                # 执行导入
                item_data = ItemImportService.convert_to_item_data(row)
                ItemService.create_item(item_data)
                success_count += 1
                
            except Exception as e:
                errors.append(f"第{i}行导入失败: {str(e)}")
        
        return success_count, errors, skipped_codes
    
    @staticmethod
    def read_excel_file(file_path: str) -> Tuple[List[Dict], List[str]]:
        """
        读取Excel文件
        返回: (数据列表, 错误信息列表)
        """
        try:
            # 尝试读取Excel文件
            df = pd.read_excel(file_path)
            
            # 检查必需的列
            required_columns = ['代码', '名称', '全名', '规格型号']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return [], [f"缺少必需的列: {', '.join(missing_columns)}"]
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 过滤空行
            filtered_data = []
            for row in data:
                if any(pd.notna(row.get(col)) and str(row.get(col)).strip() for col in required_columns[:2]):
                    # 处理NaN值
                    cleaned_row = {}
                    for key, value in row.items():
                        if pd.isna(value):
                            cleaned_row[key] = ''
                        else:
                            cleaned_row[key] = str(value).strip()
                    filtered_data.append(cleaned_row)
            
            return filtered_data, []
            
        except Exception as e:
            return [], [f"读取Excel文件失败: {str(e)}"]
    
    @staticmethod
    def read_csv_file(file_path: str, encoding: str = 'utf-8') -> Tuple[List[Dict], List[str]]:
        """
        读取CSV文件
        返回: (数据列表, 错误信息列表)
        """
        try:
            # 尝试不同的编码
            encodings = [encoding, 'utf-8', 'gbk', 'gb2312', 'utf-8-sig']
            df = None
            
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                return [], ["无法读取CSV文件，请检查文件编码"]
            
            # 检查必需的列
            required_columns = ['代码', '名称', '全名', '规格型号']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return [], [f"缺少必需的列: {', '.join(missing_columns)}"]
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 过滤空行
            filtered_data = []
            for row in data:
                if any(pd.notna(row.get(col)) and str(row.get(col)).strip() for col in required_columns[:2]):
                    # 处理NaN值
                    cleaned_row = {}
                    for key, value in row.items():
                        if pd.isna(value):
                            cleaned_row[key] = ''
                        else:
                            cleaned_row[key] = str(value).strip()
                    filtered_data.append(cleaned_row)
            
            return filtered_data, []
            
        except Exception as e:
            return [], [f"读取CSV文件失败: {str(e)}"]
