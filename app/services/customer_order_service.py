#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户订单服务类
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from app.db import DatabaseManager

class CustomerOrderService:
    """客户订单服务类"""
    
    @staticmethod
    def parse_txt_order_file(file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """
        解析TXT格式的订单文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Tuple[List[Dict], List[Dict]]: (订单主表数据, 订单明细数据)
        """
        orders = []
        order_lines = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
            
            # 按订单分割（每个订单以"SUPPLIER SCHEDULE / MATERIAL RELEASE"开始）
            order_sections = content.split("SUPPLIER SCHEDULE / MATERIAL RELEASE")
            
            for section in order_sections[1:]:  # 跳过第一个空部分
                if not section.strip():
                    continue
                    
                # 解析订单主表信息
                order_info = CustomerOrderService._parse_order_header(section)
                if order_info:
                    orders.append(order_info)
                    
                    # 解析订单明细
                    lines = CustomerOrderService._parse_order_lines(section, order_info['OrderNumber'])
                    order_lines.extend(lines)
            
            return orders, order_lines
            
        except Exception as e:
            raise Exception(f"解析订单文件失败: {str(e)}")
    
    @staticmethod
    def _parse_order_header(section: str) -> Optional[Dict]:
        """解析订单主表信息"""
        try:
            order_info = {}
            
            # 提取订单号
            po_match = re.search(r'Purchase Order:\s*(\w+)', section)
            if po_match:
                order_info['OrderNumber'] = po_match.group(1)
            else:
                return None
            
            # 提取供应商信息
            supplier_match = re.search(r'Supplier:\s*(\d+)\s*\n\s*([^\n]+)', section)
            if supplier_match:
                order_info['SupplierCode'] = supplier_match.group(1)
                order_info['SupplierName'] = supplier_match.group(2).strip()
            
            # 提取客户信息
            customer_match = re.search(r'Ship-To:\s*(\d+)\s*\n\s*([^\n]+)', section)
            if customer_match:
                order_info['CustomerCode'] = customer_match.group(1)
                order_info['CustomerName'] = customer_match.group(2).strip()
            
            # 提取发布日期
            release_match = re.search(r'Release Date:\s*(\d{2}/\d{2}/\d{2})', section)
            if release_match:
                try:
                    rd = datetime.strptime(release_match.group(1), '%m/%d/%y')
                    if rd.year < 2000:
                        rd = rd.replace(year=rd.year + 2000)
                    order_info['ReleaseDate'] = rd.strftime('%Y-%m-%d')
                except Exception:
                    order_info['ReleaseDate'] = release_match.group(1)
            
            # 提取采购员
            buyer_match = re.search(r'Buyer:\s*(\w+)', section)
            if buyer_match:
                order_info['Buyer'] = buyer_match.group(1)
            
            # 提取收货地址
            ship_to_match = re.search(r'No\.1-9 Gangcheng Avenue\s*\n\s*([^\n]+)', section)
            if ship_to_match:
                order_info['ShipToAddress'] = ship_to_match.group(1).strip()
            
            return order_info
            
        except Exception as e:
            print(f"解析订单主表失败: {e}")
            return None
    
    @staticmethod
    def _parse_order_lines(section: str, order_number: str) -> List[Dict]:
        """解析订单明细信息"""
        lines = []
        
        try:
            # 提取产品信息
            item_match = re.search(r'Item Number:\s*(\w+)\s*UM:\s*(\w+)\s*In Transit Qty:\s*([\d.]+)', section)
            if not item_match:
                return lines
            
            item_number = item_match.group(1)
            unit_of_measure = item_match.group(2)
            in_transit_qty = float(item_match.group(3))
            
            # 提取产品描述
            desc_match = re.search(r'Item Number:\s*\w+\s*UM:\s*\w+\s*In Transit Qty:\s*[\d.]+[^\n]*\n\s*([^\n]+)', section)
            item_description = desc_match.group(1).strip() if desc_match else ""
            
            # 提取累计收货数量
            cum_received_match = re.search(r'Cum Received:\s*([\d.]+)', section)
            cum_received = float(cum_received_match.group(1)) if cum_received_match else 0.0
            
            # 提取交货明细
            delivery_pattern = r'(\d{2}/\d{2}/\d{2})\s+([FP])\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
            delivery_matches = re.findall(delivery_pattern, section)
            
            for delivery_match in delivery_matches:
                delivery_date_raw = delivery_match[0]
                order_type = delivery_match[1]
                required_qty = float(delivery_match[2].replace(',', ''))
                cumulative_qty = float(delivery_match[3].replace(',', ''))
                net_required_qty = float(delivery_match[4].replace(',', ''))

                # 转换日期并计算日历周
                try:
                    date_obj = datetime.strptime(delivery_date_raw, '%m/%d/%y')
                    if date_obj.year < 2000:
                        date_obj = date_obj.replace(year=date_obj.year + 2000)
                    delivery_date = date_obj.strftime('%Y-%m-%d')
                    calendar_week = f"CW{date_obj.isocalendar()[1]:02d}"
                except Exception:
                    delivery_date = delivery_date_raw
                    calendar_week = ""

                line_data = {
                    'OrderNumber': order_number,
                    'ItemNumber': item_number,
                    'ItemDescription': item_description,
                    'UnitOfMeasure': unit_of_measure,
                    'DeliveryDate': delivery_date,
                    'CalendarWeek': calendar_week,
                    'OrderType': order_type,
                    'RequiredQty': required_qty,
                    'CumulativeQty': cumulative_qty,
                    'NetRequiredQty': net_required_qty,
                    'InTransitQty': in_transit_qty,
                    'ReceivedQty': cum_received
                }

                lines.append(line_data)
            
            return lines
            
        except Exception as e:
            print(f"解析订单明细失败: {e}")
            return lines
    
    @staticmethod
    def import_orders_from_file(file_path: str, file_name: str) -> Dict:
        """
        从文件导入订单数据
        
        Args:
            file_path: 文件路径
            file_name: 文件名
            
        Returns:
            Dict: 导入结果
        """
        try:
            # 解析文件
            orders, order_lines = CustomerOrderService.parse_txt_order_file(file_path)
            
            if not orders:
                return {
                    'success': False,
                    'message': '未找到有效的订单数据',
                    'order_count': 0,
                    'line_count': 0
                }
            
            # 保存到数据库
            db_manager = DatabaseManager()
            with db_manager.get_conn() as conn:
                conn.execute("BEGIN TRANSACTION")

                try:
                    # 创建导入历史记录，获取版本ID
                    import_id = CustomerOrderService._create_import_history(conn, file_name)

                    # 保存订单主表
                    saved_orders = []
                    for order in orders:
                        order_id = CustomerOrderService._save_order_header(conn, order, import_id)
                        if order_id:
                            saved_orders.append((order_id, order['OrderNumber']))

                    # 保存订单明细
                    saved_lines = 0
                    for line in order_lines:
                        order_id = None
                        for oid, onum in saved_orders:
                            if onum == line['OrderNumber']:
                                order_id = oid
                                break
                        if order_id:
                            if CustomerOrderService._save_order_line(conn, order_id, line, import_id):
                                saved_lines += 1

                    # 更新导入历史
                    CustomerOrderService._finalize_import_history(
                        conn, import_id, len(saved_orders), saved_lines, 'Success'
                    )

                    conn.execute("COMMIT")
                    return {
                        'success': True,
                        'message': f'成功导入 {len(saved_orders)} 个订单，{saved_lines} 条明细',
                        'order_count': len(saved_orders),
                        'line_count': saved_lines,
                        'import_id': import_id
                    }

                except Exception as e:
                    conn.execute("ROLLBACK")
                    try:
                        CustomerOrderService._finalize_import_history(
                            conn, import_id, 0, 0, 'Failed', str(e)
                        )
                    except Exception:
                        pass
                    raise e
                    
        except Exception as e:
            return {
                'success': False,
                'message': f'导入失败: {str(e)}',
                'order_count': 0,
                'line_count': 0
            }
    
    @staticmethod
    def _save_order_header(conn, order_data: Dict, import_id: int) -> Optional[int]:
        """保存订单主表"""
        try:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO CustomerOrders
                (OrderNumber, ImportId, SupplierCode, SupplierName, CustomerCode, CustomerName,
                 ReleaseDate, Buyer, ShipToAddress, OrderStatus, Remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_data.get('OrderNumber', ''),
                import_id,
                order_data.get('SupplierCode', ''),
                order_data.get('SupplierName', ''),
                order_data.get('CustomerCode', ''),
                order_data.get('CustomerName', ''),
                order_data.get('ReleaseDate', ''),
                order_data.get('Buyer', ''),
                order_data.get('ShipToAddress', ''),
                'Active',
                f'从文件导入 - {order_data.get("ReleaseDate", "")}'
            ))
            
            # 获取插入的ID
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                # 如果是REPLACE，需要查询ID
                cursor = conn.execute(
                    "SELECT OrderId FROM CustomerOrders WHERE OrderNumber = ?",
                    (order_data['OrderNumber'],)
                )
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            print(f"保存订单主表失败: {e}")
            return None
    
    @staticmethod
    def _save_order_line(conn, order_id: int, line_data: Dict, import_id: int) -> bool:
        """保存订单明细"""
        try:
            conn.execute("""
                INSERT OR REPLACE INTO CustomerOrderLines
                (OrderId, ImportId, ItemNumber, ItemDescription, UnitOfMeasure, DeliveryDate,
                 CalendarWeek, OrderType, RequiredQty, CumulativeQty, NetRequiredQty,
                 InTransitQty, ReceivedQty, LineStatus, Remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                import_id,
                line_data.get('ItemNumber', ''),
                line_data.get('ItemDescription', ''),
                line_data.get('UnitOfMeasure', 'EA'),
                line_data.get('DeliveryDate', ''),
                line_data.get('CalendarWeek', ''),
                line_data.get('OrderType', ''),
                line_data.get('RequiredQty', 0),
                line_data.get('CumulativeQty', 0),
                line_data.get('NetRequiredQty', 0),
                line_data.get('InTransitQty', 0),
                line_data.get('ReceivedQty', 0),
                'Active',
                f'从文件导入 - {line_data.get("DeliveryDate", "")}'
            ))
            
            return True
            
        except Exception as e:
            print(f"保存订单明细失败: {e}")
            return False
    
    @staticmethod
    def _create_import_history(conn, file_name: str) -> int:
        """创建导入历史记录并返回ID"""
        cursor = conn.execute(
            """INSERT INTO OrderImportHistory (FileName, ImportStatus, ImportedBy)
                VALUES (?, 'Processing', 'System')""",
            (file_name,)
        )
        return cursor.lastrowid

    @staticmethod
    def _finalize_import_history(conn, import_id: int, order_count: int, line_count: int,
                                 status: str, error_msg: str = None):
        """更新导入历史记录"""
        conn.execute(
            """UPDATE OrderImportHistory
                SET OrderCount = ?, LineCount = ?, ImportStatus = ?, ErrorMessage = ?,
                    ImportDate = CURRENT_TIMESTAMP
                WHERE ImportId = ?""",
            (order_count, line_count, status, error_msg, import_id)
        )
    
    @staticmethod
    def get_orders_summary(start_date: str = None, end_date: str = None, 
                          order_type: str = None, item_number: str = None) -> List[Dict]:
        """
        获取订单汇总信息（看板视图）
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            order_type: 订单类型 (F/P/All)
            item_number: 产品型号
            
        Returns:
            List[Dict]: 汇总数据
        """
        try:
            db_manager = DatabaseManager()
            
            with db_manager.get_conn() as conn:
                # 构建查询条件
                where_conditions = ["1=1"]
                params = []
                
                if start_date:
                    where_conditions.append("DeliveryDate >= ?")
                    params.append(start_date)
                
                if end_date:
                    where_conditions.append("DeliveryDate <= ?")
                    params.append(end_date)
                
                if order_type and order_type != 'All':
                    where_conditions.append("OrderType = ?")
                    params.append(order_type)
                
                if item_number:
                    where_conditions.append("ItemNumber LIKE ?")
                    params.append(f"%{item_number}%")
                
                where_clause = " AND ".join(where_conditions)
                
                # 查询汇总数据
                cursor = conn.execute(f"""
                    SELECT 
                        DeliveryDate,
                        CalendarWeek,
                        ItemNumber,
                        ItemDescription,
                        OrderType,
                        SUM(CASE WHEN OrderType = 'F' THEN RequiredQty ELSE 0 END) as FormalQty,
                        SUM(CASE WHEN OrderType = 'P' THEN RequiredQty ELSE 0 END) as ForecastQty,
                        SUM(RequiredQty) as TotalQty,
                        COUNT(DISTINCT OrderId) as OrderCount
                    FROM CustomerOrderLines 
                    WHERE {where_clause}
                    GROUP BY DeliveryDate, CalendarWeek, ItemNumber, ItemDescription, OrderType
                    ORDER BY DeliveryDate, ItemNumber
                """, params)
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'DeliveryDate': row[0],
                        'CalendarWeek': row[1],
                        'ItemNumber': row[2],
                        'ItemDescription': row[3],
                        'OrderType': row[4],
                        'FormalQty': row[5],
                        'ForecastQty': row[6],
                        'TotalQty': row[7],
                        'OrderCount': row[8]
                    })
                
                return results
                
        except Exception as e:
            print(f"获取订单汇总失败: {e}")
            return []
    
    @staticmethod
    def get_orders_by_date_range(start_date: str, end_date: str) -> List[Dict]:
        """获取指定日期范围内的订单"""
        try:
            db_manager = DatabaseManager()
            
            with db_manager.get_conn() as conn:
                cursor = conn.execute("""
                    SELECT 
                        co.OrderNumber,
                        co.SupplierName,
                        co.CustomerName,
                        co.ReleaseDate,
                        col.ItemNumber,
                        col.ItemDescription,
                        col.DeliveryDate,
                        col.CalendarWeek,
                        col.OrderType,
                        col.RequiredQty,
                        col.CumulativeQty,
                        col.NetRequiredQty
                    FROM CustomerOrders co
                    JOIN CustomerOrderLines col ON co.OrderId = col.OrderId
                    WHERE col.DeliveryDate BETWEEN ? AND ?
                    ORDER BY col.DeliveryDate, col.ItemNumber
                """, (start_date, end_date))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'OrderNumber': row[0],
                        'SupplierName': row[1],
                        'CustomerName': row[2],
                        'ReleaseDate': row[3],
                        'ItemNumber': row[4],
                        'ItemDescription': row[5],
                        'DeliveryDate': row[6],
                        'CalendarWeek': row[7],
                        'OrderType': row[8],
                        'RequiredQty': row[9],
                        'CumulativeQty': row[10],
                        'NetRequiredQty': row[11]
                    })
                
                return results
                
        except Exception as e:
            print(f"获取订单失败: {e}")
            return []
    
    @staticmethod
    def get_import_history(limit: int = 50) -> List[Dict]:
        """获取导入历史"""
        try:
            db_manager = DatabaseManager()
            
            with db_manager.get_conn() as conn:
                cursor = conn.execute("""
                    SELECT ImportId, FileName, ImportDate, OrderCount, LineCount, 
                           ImportStatus, ErrorMessage, ImportedBy
                    FROM OrderImportHistory
                    ORDER BY ImportDate DESC
                    LIMIT ?
                """, (limit,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'ImportId': row[0],
                        'FileName': row[1],
                        'ImportDate': row[2],
                        'OrderCount': row[3],
                        'LineCount': row[4],
                        'ImportStatus': row[5],
                        'ErrorMessage': row[6],
                        'ImportedBy': row[7]
                    })
                
                return results
                
        except Exception as e:
            print(f"获取导入历史失败: {e}")
            return []

    @staticmethod
    def get_orders_pivot_data(start_date: str = None, end_date: str = None, 
                             order_type: str = None, item_number: str = None, 
                             version_id: int = None) -> Dict:
        """
        获取订单透视表数据（看板视图）
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            order_type: 订单类型 (F/P/All)
            item_number: 产品型号
            version_id: 版本ID（导入历史ID）
            
        Returns:
            Dict: 包含透视表数据的字典
        """
        try:
            print(f"🔍 查询透视表数据: start_date={start_date}, end_date={end_date}, order_type={order_type}, item_number={item_number}, version_id={version_id}")
            
            db_manager = DatabaseManager()
            
            with db_manager.get_conn() as conn:
                # 构建查询条件
                where_conditions = ["1=1"]
                params = []
                
                # 添加版本筛选
                if version_id:
                    where_conditions.append("col.ImportId = ?")
                    params.append(version_id)
                    print(f"   添加版本筛选: ImportId = {version_id}")
                
                if start_date and start_date.strip():
                    # 转换日期格式从 YYYY-MM-DD 到 MM/DD/YY
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                        start_date_formatted = date_obj.strftime('%m/%d/%y')
                        where_conditions.append("col.DeliveryDate >= ?")
                        params.append(start_date_formatted)
                        print(f"   转换开始日期: {start_date} -> {start_date_formatted}")
                    except Exception as e:
                        print(f"   ⚠️ 开始日期格式转换失败: {start_date}, 错误: {e}")
                        # 如果日期转换失败，不添加日期条件，避免数据丢失
                
                if end_date and end_date.strip():
                    # 转换日期格式从 YYYY-MM-DD 到 MM/DD/YY
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                        end_date_formatted = date_obj.strftime('%m/%d/%y')
                        where_conditions.append("col.DeliveryDate <= ?")
                        params.append(end_date_formatted)
                        print(f"   转换结束日期: {end_date} -> {end_date_formatted}")
                    except Exception as e:
                        print(f"   ⚠️ 结束日期格式转换失败: {end_date}, 错误: {e}")
                        # 如果日期转换失败，不添加日期条件，避免数据丢失
                
                if order_type and order_type != 'All':
                    where_conditions.append("col.OrderType = ?")
                    params.append(order_type)
                
                if item_number and item_number.strip():
                    where_conditions.append("col.ItemNumber LIKE ?")
                    params.append(f"%{item_number}%")
                
                where_clause = " AND ".join(where_conditions)
                print(f"   WHERE条件: {where_clause}")
                print(f"   参数: {params}")
                
                # 获取所有产品型号
                cursor = conn.execute(f"""
                    SELECT DISTINCT col.ItemNumber, col.ItemDescription
                    FROM CustomerOrderLines col
                    WHERE {where_clause}
                    ORDER BY col.ItemNumber
                """, params)
                
                items = []
                for row in cursor.fetchall():
                    items.append({
                        'ItemNumber': row[0],
                        'ItemDescription': row[1] or ''
                    })
                
                print(f"   找到产品: {len(items)} 个")
                
                # 如果没有找到产品，尝试不限制日期范围查询
                if not items and (start_date or end_date):
                    print("   ⚠️ 使用日期筛选未找到数据，尝试查询所有数据...")
                    # 重新查询，不使用日期限制
                    base_conditions = ["1=1"]
                    base_params = []
                    if version_id:
                        base_conditions.append("col.ImportId = ?")
                        base_params.append(version_id)
                    
                    base_where = " AND ".join(base_conditions)
                    cursor = conn.execute(f"""
                        SELECT DISTINCT col.ItemNumber, col.ItemDescription
                        FROM CustomerOrderLines col
                        WHERE {base_where}
                        ORDER BY col.ItemNumber
                    """, base_params)
                    
                    items = []
                    for row in cursor.fetchall():
                        items.append({
                            'ItemNumber': row[0],
                            'ItemDescription': row[1] or ''
                        })
                    print(f"   重新查询找到产品: {len(items)} 个")
                
                # 获取所有日历周（按顺序）
                cursor = conn.execute(f"""
                    SELECT DISTINCT col.CalendarWeek, col.DeliveryDate
                    FROM CustomerOrderLines col
                    WHERE {where_clause}
                    ORDER BY col.DeliveryDate
                """, params)
                
                weeks = []
                for row in cursor.fetchall():
                    weeks.append({
                        'CalendarWeek': row[0],
                        'DeliveryDate': row[1]
                    })
                
                print(f"   找到周数: {len(weeks)} 个")
                
                # 如果没有找到周数，尝试不限制日期范围查询
                if not weeks and (start_date or end_date):
                    print("   ⚠️ 使用日期筛选未找到周数，尝试查询所有数据...")
                    # 重新查询，不使用日期限制
                    base_conditions = ["1=1"]
                    base_params = []
                    if version_id:
                        base_conditions.append("col.ImportId = ?")
                        base_params.append(version_id)
                    
                    base_where = " AND ".join(base_conditions)
                    cursor = conn.execute(f"""
                        SELECT DISTINCT col.CalendarWeek, col.DeliveryDate
                        FROM CustomerOrderLines col
                        WHERE {base_where}
                        ORDER BY col.DeliveryDate
                    """, base_params)
                    
                    weeks = []
                    for row in cursor.fetchall():
                        weeks.append({
                            'CalendarWeek': row[0],
                            'DeliveryDate': row[1]
                        })
                    print(f"   重新查询找到周数: {len(weeks)} 个")
                
                # 获取透视表数据
                cursor = conn.execute(f"""
                    SELECT 
                        col.ItemNumber,
                        col.CalendarWeek,
                        col.OrderType,
                        SUM(col.RequiredQty) as TotalQty
                    FROM CustomerOrderLines col
                    WHERE {where_clause}
                    GROUP BY col.ItemNumber, col.CalendarWeek, col.OrderType
                    ORDER BY col.ItemNumber, col.CalendarWeek
                """, params)
                
                # 构建透视表数据
                pivot_data = {}
                for row in cursor.fetchall():
                    item_num = row[0]
                    week = row[1]
                    order_type = row[2]
                    qty = row[3]
                    
                    if item_num not in pivot_data:
                        pivot_data[item_num] = {}
                    
                    if week not in pivot_data[item_num]:
                        pivot_data[item_num][week] = {'F': 0, 'P': 0, 'Total': 0}
                    
                    pivot_data[item_num][week][order_type] = qty
                    pivot_data[item_num][week]['Total'] += qty
                
                print(f"   构建透视数据: {len(pivot_data)} 个产品")
                
                return {
                    'items': items,
                    'weeks': weeks,
                    'pivot_data': pivot_data
                }
                
        except Exception as e:
            print(f"❌ 获取透视表数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {'items': [], 'weeks': [], 'pivot_data': {}}
