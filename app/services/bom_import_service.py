#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from app.db import query_one, query_all, execute, get_last_id
from app.services.bom_service import BomService
from app.services.item_service import ItemService


class BomImportService:
    """BOM导入服务"""
    
    @staticmethod
    def parse_bom_csv(file_path: str) -> Tuple[List[Dict], List[str]]:
        """
        解析BOM CSV文件
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            Tuple[List[Dict], List[str]]: (BOM数据列表, 错误信息列表)
        """
        try:
            print(f"开始解析BOM文件: {file_path}")
            
            # 读取CSV文件
            df = pd.read_csv(file_path, header=None)
            print(f"CSV文件形状: {df.shape}")
            print(f"CSV文件内容预览:")
            print(df.head())
            
            if df.empty:
                return [], ["CSV文件为空"]
            
            # 验证文件格式
            if df.shape[0] < 3:
                return [], ["CSV文件格式错误：至少需要3行数据"]
            
            # 第一行：成品商品品牌（从第2列开始）
            product_brands = df.iloc[0, 1:].tolist()
            product_brands = [str(brand).strip() for brand in product_brands if pd.notna(brand) and str(brand).strip()]
            
            # 第二行：成品规格型号（从第2列开始）
            product_specs = df.iloc[1, 1:].tolist()
            product_specs = [str(spec).strip() for spec in product_specs if pd.notna(spec) and str(spec).strip()]
            
            # 第一列：零部件规格（从第3行开始）
            component_specs = df.iloc[2:, 0].tolist()
            component_specs = [str(spec).strip() for spec in component_specs if pd.notna(spec) and str(spec).strip()]
            
            print(f"成品商品品牌: {product_brands}")
            print(f"成品规格型号: {product_specs}")
            print(f"零部件规格: {component_specs}")
            
            # 验证数据完整性
            if len(product_brands) != len(product_specs):
                return [], [f"成品数据不匹配：品牌数量({len(product_brands)}) != 规格数量({len(product_specs)})"]
            
            if len(product_brands) == 0:
                return [], ["没有找到成品数据"]
            
            if len(component_specs) == 0:
                return [], ["没有找到零部件数据"]
            
            # 解析BOM关系数据（从第3行第2列开始）
            bom_data_list = []
            
            for i, component_spec in enumerate(component_specs):
                if not component_spec:
                    continue
                    
                # 获取该零部件的用量数据
                quantities = df.iloc[i + 2, 1:].tolist()
                
                for j, (brand, spec, qty) in enumerate(zip(product_brands, product_specs, quantities)):
                    if not brand or not spec:
                        continue
                        
                    # 转换数量
                    try:
                        quantity = float(qty) if pd.notna(qty) and str(qty).strip() != '' else 0
                    except (ValueError, TypeError):
                        quantity = 0
                    
                    if quantity > 0:  # 只处理有数量的关系
                        bom_data = {
                            'product_brand': brand,
                            'product_spec': spec,
                            'component_spec': component_spec,
                            'quantity': quantity,
                            'row_index': i + 2,
                            'col_index': j + 1
                        }
                        bom_data_list.append(bom_data)
                        print(f"BOM关系: {brand}({spec}) -> {component_spec} = {quantity}")
            
            print(f"解析完成，共找到 {len(bom_data_list)} 个BOM关系")
            return bom_data_list, []
            
        except Exception as e:
            return [], [f"解析CSV文件失败: {str(e)}"]
    
    @staticmethod
    def normalize_spec(spec: str) -> str:
        """
        标准化规格字符串，去除空格和特殊字符
        
        Args:
            spec: 原始规格字符串
            
        Returns:
            str: 标准化后的规格字符串
        """
        if not spec:
            return ""
        
        # 去除首尾空格
        normalized = spec.strip()
        
        # 将多个空格替换为单个空格
        normalized = " ".join(normalized.split())
        
        # 将连字符和下划线都替换为空格
        normalized = normalized.replace("-", " ").replace("_", " ")
        
        # 去除所有空格
        normalized = normalized.replace(" ", "")
        
        return normalized
    
    @staticmethod
    def find_product_item(brand: str, spec: str) -> Tuple[Optional[int], List[str]]:
        """
        查找成品物料（不创建新物料）
        
        Args:
            brand: 商品品牌
            spec: 规格型号
            
        Returns:
            Tuple[Optional[int], List[str]]: (物料ID, 错误信息列表)
        """
        try:
            # 标准化规格字符串
            normalized_spec = BomImportService.normalize_spec(spec)
            
            # 使用标准化规格查找，同时也要对数据库中的规格进行标准化比较
            sql = """
                SELECT ItemId, ItemSpec FROM Items 
                WHERE Brand = ? AND ItemType = 'FG'
            """
            items = query_all(sql, (brand,))
            
            # 遍历所有匹配品牌的物料，比较标准化后的规格
            for item in items:
                db_spec = item['ItemSpec']
                db_normalized_spec = BomImportService.normalize_spec(db_spec)
                
                # 比较标准化后的规格
                if db_normalized_spec == normalized_spec:
                    print(f"找到成品物料: {brand}({spec}) -> ID: {item['ItemId']} (匹配: {db_spec})")
                    return item['ItemId'], []
            
            # 如果还是没找到，返回错误信息
            return None, [f"未找到成品物料: {brand}({spec})"]
            
        except Exception as e:
            return None, [f"查找成品物料失败 {brand}({spec}): {str(e)}"]
    
    @staticmethod
    def find_component_item(spec: str) -> Tuple[Optional[int], List[str]]:
        """
        查找零部件物料（不创建新物料）
        
        Args:
            spec: 规格型号
            
        Returns:
            Tuple[Optional[int], List[str]]: (物料ID, 错误信息列表)
        """
        try:
            # 标准化规格字符串
            normalized_spec = BomImportService.normalize_spec(spec)
            
            # 获取所有RM和SFG类型的物料，进行标准化比较
            sql = """
                SELECT ItemId, ItemSpec FROM Items 
                WHERE ItemType IN ('RM', 'SFG')
            """
            items = query_all(sql)
            
            # 遍历所有零部件物料，比较标准化后的规格
            for item in items:
                db_spec = item['ItemSpec']
                db_normalized_spec = BomImportService.normalize_spec(db_spec)
                
                # 比较标准化后的规格
                if db_normalized_spec == normalized_spec:
                    print(f"找到零部件物料: {spec} -> ID: {item['ItemId']} (匹配: {db_spec})")
                    return item['ItemId'], []
            
            # 如果还是没找到，返回错误信息
            return None, [f"未找到零部件物料: {spec}"]
            
        except Exception as e:
            return None, [f"查找零部件物料失败 {spec}: {str(e)}"]
    
    @staticmethod
    def import_bom_from_csv(file_path: str) -> Tuple[int, List[str], List[str]]:
        """
        从CSV文件导入BOM数据
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            Tuple[int, List[str], List[str]]: (成功数量, 错误信息列表, 警告信息列表)
        """
        try:
            print("=== 开始导入BOM数据 ===")
            
            # 解析CSV文件
            bom_data_list, parse_errors = BomImportService.parse_bom_csv(file_path)
            if parse_errors:
                return 0, parse_errors, []
            
            if not bom_data_list:
                return 0, ["没有找到有效的BOM关系数据"], []
            
            # 按成品分组处理BOM
            success_count = 0
            errors = []
            warnings = []
            
            # 按成品品牌分组
            product_groups = {}
            for bom_data in bom_data_list:
                brand = bom_data['product_brand']
                if brand not in product_groups:
                    product_groups[brand] = []
                product_groups[brand].append(bom_data)
            
            print(f"按成品品牌分组: {list(product_groups.keys())}")
            
            # 处理每个成品品牌
            for brand, bom_items in product_groups.items():
                try:
                    print(f"\n处理成品品牌: {brand}")
                    
                    # 获取该品牌下的所有规格
                    specs = list(set([item['product_spec'] for item in bom_items]))
                    print(f"该品牌下的规格: {specs}")
                    
                    # 为每个规格创建BOM
                    for spec in specs:
                        try:
                            print(f"  处理规格: {spec}")
                            
                            # 查找成品物料
                            product_id, product_errors = BomImportService.find_product_item(brand, spec)
                            if product_errors:
                                errors.extend(product_errors)
                                continue
                            
                            if not product_id:
                                errors.append(f"未找到成品物料: {brand}({spec})")
                                continue
                            
                            # 创建BOM主表
                            bom_name = f"{brand}_BOM"
                            rev = "A"
                            effective_date = datetime.now().strftime("%Y-%m-%d")
                            
                            # 检查是否已存在相同BOM
                            existing_bom = query_one(
                                "SELECT BomId FROM BomHeaders WHERE BomName = ? AND Rev = ?",
                                (bom_name, rev)
                            )
                            
                            if existing_bom:
                                warnings.append(f"BOM已存在: {bom_name}({rev})，跳过")
                                continue
                            
                            bom_id = BomService.create_bom_header({
                                'BomName': bom_name,
                                'ParentItemId': product_id,
                                'Rev': rev,
                                'EffectiveDate': effective_date,
                                'Remark': f"从CSV导入的BOM - {brand}({spec})"
                            })
                            
                            print(f"    创建BOM主表: {bom_name} -> ID: {bom_id}")
                            
                            # 创建BOM明细
                            spec_bom_items = [item for item in bom_items if item['product_spec'] == spec]
                            
                            for bom_item in spec_bom_items:
                                try:
                                    # 查找零部件物料
                                    component_id, component_errors = BomImportService.find_component_item(
                                        bom_item['component_spec']
                                    )
                                    if component_errors:
                                        errors.extend(component_errors)
                                        continue
                                    
                                    if not component_id:
                                        errors.append(f"未找到零部件物料: {bom_item['component_spec']}")
                                        continue
                                    
                                    # 创建BOM明细
                                    BomService.create_bom_line(bom_id, {
                                        'ChildItemId': component_id,
                                        'QtyPer': bom_item['quantity'],
                                        'ScrapFactor': 0
                                    })
                                    
                                    print(f"      创建BOM明细: {bom_item['component_spec']} -> {bom_item['quantity']}")
                                    success_count += 1
                                    
                                except Exception as e:
                                    error_msg = f"创建BOM明细失败 {bom_item['component_spec']}: {str(e)}"
                                    errors.append(error_msg)
                                    print(f"      错误: {error_msg}")
                            
                        except Exception as e:
                            error_msg = f"处理规格失败 {spec}: {str(e)}"
                            errors.append(error_msg)
                            print(f"  错误: {error_msg}")
                
                except Exception as e:
                    error_msg = f"处理成品品牌失败 {brand}: {str(e)}"
                    errors.append(error_msg)
                    print(f"错误: {error_msg}")
            
            print(f"\n=== 导入完成 ===")
            print(f"成功导入: {success_count} 个BOM关系")
            print(f"错误数量: {len(errors)}")
            print(f"警告数量: {len(warnings)}")
            
            return success_count, errors, warnings
            
        except Exception as e:
            return 0, [f"导入BOM数据失败: {str(e)}"], []


if __name__ == "__main__":
    # 测试导入
    file_path = "bom.csv"
    success_count, errors, warnings = BomImportService.import_bom_from_csv(file_path)
    
    print(f"\n导入结果:")
    print(f"成功: {success_count}")
    print(f"错误: {errors}")
    print(f"警告: {warnings}")
