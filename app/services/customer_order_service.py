#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户订单服务类（含 OrderYear 修复）
- TXT 解析遵循 NDLUtil 逻辑：头字段行内匹配；Item 切换继承 header_*；计划行支持整数/小数
- 导入时 CustomerOrders 必填列 OrderYear 由 DeliveryDate 推算写入
- 查询接口与 UI 适配：get_order_lines_by_import_version 不再引用不存在列
"""

import os
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from app.db import get_conn


class CustomerOrderService:
    # ------------------------- 工具 -------------------------
    @staticmethod
    def _parse_mmddyy_to_iso(s: str) -> str:
        """把 08/21/25 转为 2025-08-21（<2000 年补 +2000）"""
        dt = datetime.strptime(s, "%m/%d/%y")
        if dt.year < 2000:
            dt = dt.replace(year=dt.year + 2000)
        return dt.strftime("%Y-%m-%d")

    # ------------------------- 解析 TXT -------------------------
    @staticmethod
    def parse_txt_order_file(file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """
        返回 (orders, order_lines)

        orders: 每个 (Supplier, Item) 的头信息（ReleaseDate/ReleaseId/ReceiptQty/CumReceived...）
        order_lines: 明细行（按日期、F/P、数量）
        """
        from pathlib import Path
        import re

        RE_SUPPLIER  = re.compile(r"^\s*Supplier:\s*([A-Za-z0-9\-]+)")
        RE_SHIPTO    = re.compile(r"^\s*Ship-To:")
        RE_ITEM      = re.compile(r"^\s*Item Number:\s*([A-Z0-9\-]+)", re.I)

        RE_PO        = re.compile(r"Purchase Order:\s*([A-Z0-9\-]+)", re.I)
        RE_RELID     = re.compile(r"Release ID:\s*([\w\-]+)", re.I)
        RE_RELD      = re.compile(r"Release Date:\s*([0-9/]+)", re.I)
        # 数量支持整数或小数
        RE_RECEIPT_Q = re.compile(r"Receipt Quantity:\s*([0-9][0-9,]*(?:\.\d+)?)", re.I)
        RE_CUM_RECV  = re.compile(r"Cum Received:\s*([0-9][0-9,]*(?:\.\d+)?)", re.I)

        # 计划行：日期 + F/P + 数量
        RE_LINE      = re.compile(
            r"^\s*(?:Daily|Weekly|Monthly)?\s*([0-9]{2}/[0-9]{2}/[0-9]{2})\s+([FPfp])\s+([0-9][0-9,]*(?:\.\d+)?)(?:\s+.*)?$"
        )

        def mmddyy_to_dt(s: str) -> datetime:
            dt = datetime.strptime(s, "%m/%d/%y")
            if dt.year < 2000:
                dt = dt.replace(year=dt.year + 2000)
            return dt

        orders: List[Dict] = []
        order_lines: List[Dict] = []

        raw = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        lines = raw.splitlines()

        sup_code = sup_name = None
        item = None

        # header_*: Supplier 段落的头字段；后续 Item 出现时继承
        header_po = header_rel_id = header_rel_date = None
        header_receipt_qty = header_cum_received = None

        # 当前 Item 的头字段（默认继承 header_*，若遇到新值则覆盖）
        po = rel_id = rel_date = None
        receipt_qty = cum_received = None

        capture_sup_name = False

        def flush_order_header():
            """把当前 supplier+item 的头信息写入 orders"""
            nonlocal po, rel_id, rel_date, receipt_qty, cum_received
            if not (sup_code and item):
                return
            rec = {
                "OrderNumber": f"{sup_code}_{item}",
                "SupplierCode": sup_code,
                "SupplierName": sup_name or "",
                "CustomerCode": "",
                "CustomerName": "",
                "ReleaseDate": "",
                "ReleaseId": rel_id or "",
                "Buyer": "",
                "ShipToAddress": "",
                "ReceiptQuantity": 0.0,
                "CumReceived": 0.0,
                "Project": "",
                "PurchaseOrder": po or "",
            }
            if rel_date:
                try:
                    rec["ReleaseDate"] = CustomerOrderService._parse_mmddyy_to_iso(rel_date)
                except Exception:
                    rec["ReleaseDate"] = rel_date  # 兜底存原文
            if receipt_qty is not None:
                rec["ReceiptQuantity"] = float(str(receipt_qty).replace(",", ""))
            if cum_received is not None:
                rec["CumReceived"] = float(str(cum_received).replace(",", ""))
            orders.append(rec)

        for ln in lines:
            # Supplier 行
            m = RE_SUPPLIER.search(ln)
            if m:
                flush_order_header()
                sup_code = m.group(1)
                sup_name = None
                capture_sup_name = True
                # 重置 header_* 与当前 item 值
                header_po = header_rel_id = header_rel_date = None
                header_receipt_qty = header_cum_received = None
                item = None
                po = rel_id = rel_date = None
                receipt_qty = cum_received = None
                continue

            # Supplier 名称：在 Supplier: 行之后直到 Ship-To: 之前的第一行非空白
            if capture_sup_name:
                if RE_SHIPTO.search(ln):
                    capture_sup_name = False
                    continue
                t = ln.strip()
                if t:
                    sup_name = sup_name or t
                    capture_sup_name = False
                continue

            # 头字段（同一行可多字段同时出现，不使用 continue）
            m = RE_PO.search(ln)
            if m:
                if item:  po = m.group(1)
                else:     header_po = m.group(1)
            m = RE_RELID.search(ln)
            if m:
                if item:  rel_id = m.group(1)
                else:     header_rel_id = m.group(1)
            m = RE_RELD.search(ln)
            if m:
                if item:  rel_date = m.group(1)
                else:     header_rel_date = m.group(1)
            m = RE_RECEIPT_Q.search(ln)
            if m:
                if item:  receipt_qty = m.group(1)
                else:     header_receipt_qty = m.group(1)
            m = RE_CUM_RECV.search(ln)
            if m:
                if item:  cum_received = m.group(1)
                else:     header_cum_received = m.group(1)

            # Item Number 行：切换当前 PN，并继承 header_* 值
            m = RE_ITEM.search(ln)
            if m:
                flush_order_header()
                item = m.group(1)
                po = header_po
                rel_id = header_rel_id
                rel_date = header_rel_date
                receipt_qty = header_receipt_qty
                cum_received = header_cum_received
                continue

            # 计划行（日期 + FP + 数量）
            m = RE_LINE.match(ln)
            if m and sup_code and item:
                d_s, fp, qty_s = m.groups()
                dt = mmddyy_to_dt(d_s)
                qty = float(qty_s.replace(",", ""))
                order_lines.append({
                    "OrderNumber": f"{sup_code}_{item}",
                    "ItemNumber": item,
                    "ItemDescription": "PEMM ASSY",
                    "UnitOfMeasure": "EA",
                    "DeliveryDate": dt.strftime("%Y-%m-%d"),
                    "CalendarWeek": f"CW{dt.isocalendar()[1]:02d}",
                    "OrderType": fp.upper() if fp.upper() in ("F", "P") else "P",
                    "RequiredQty": qty,
                    "CumulativeQty": qty,
                    "NetRequiredQty": qty,
                    "InTransitQty": 0,
                    "ReceivedQty": 0,
                    "LineStatus": "Active",
                    "SupplierCode": sup_code,
                    "SupplierName": sup_name or "",
                    "ReleaseId": rel_id or "",
                    "ReleaseDate": (CustomerOrderService._parse_mmddyy_to_iso(rel_date) if rel_date else ""),
                    "PurchaseOrder": po or "",
                    "ReceiptQuantity": float(str(receipt_qty or "0").replace(",", "")),
                    "CumReceived": float(str(cum_received or "0").replace(",", "")),
                })

        # 收尾：最后一个 item 的头信息落盘
        flush_order_header()
        return orders, order_lines

    # ------------------------- 导入/删除 -------------------------
    @staticmethod
    def import_orders_from_txt(file_path: str, import_user: str = "System") -> Tuple[bool, str, int]:
        """导入 TXT 到 DB；保证 CustomerOrders.OrderYear（NOT NULL）被正确写入。"""
        try:
            orders, order_lines = CustomerOrderService.parse_txt_order_file(file_path)
            if not orders:
                return False, "没有解析到有效的订单数据", 0

            file_name = os.path.basename(file_path)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with get_conn() as conn:
                # 新建导入历史
                cur = conn.execute("""
                    INSERT INTO OrderImportHistory
                    (FileName, ImportDate, OrderCount, LineCount, ImportStatus, ImportedBy)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (file_name, now, len(orders), len(order_lines), 'Success', import_user))
                import_id = cur.lastrowid

                # 以 (Supplier, Item) 维度聚合
                groups: Dict[Tuple[str, str], Dict] = {}
                for ln in order_lines:
                    key = (ln["SupplierCode"], ln["ItemNumber"])
                    g = groups.setdefault(key, {"order_info": {}, "weeks": set(), "lines": []})
                    g["weeks"].add(ln["CalendarWeek"])
                    g["lines"].append(ln)

                order_map = {o["OrderNumber"]: o for o in orders}
                for (sup, item), g in groups.items():
                    g["order_info"] = order_map.get(f"{sup}_{item}", {})

                # 写入头表 + 行表；头表按 (Supplier, CW, OrderYear) 唯一
                for (sup, item), g in groups.items():
                    for cw in sorted(g["weeks"]):
                        # 计算 OrderYear：取该周任意一条 DeliveryDate 的 ISO 年
                        order_year = None
                        for ln in g["lines"]:
                            if ln["CalendarWeek"] == cw:
                                d = datetime.strptime(ln["DeliveryDate"], "%Y-%m-%d").date()
                                order_year = d.isocalendar()[0]
                                break
                        if order_year is None:
                            order_year = datetime.now().year

                        # 是否已存在
                        row = conn.execute("""
                            SELECT OrderId FROM CustomerOrders
                            WHERE ImportId = ? AND SupplierCode = ? AND CalendarWeek = ? AND OrderYear = ?
                        """, (import_id, sup, cw, order_year)).fetchone()

                        if row:
                            order_id = row["OrderId"]
                        else:
                            oi = g["order_info"]
                            cur = conn.execute("""
                                INSERT INTO CustomerOrders
                                (OrderNumber, ImportId, CalendarWeek, OrderYear,
                                 SupplierCode, SupplierName,
                                 CustomerCode, CustomerName,
                                 ReleaseDate, ReleaseId, Buyer, ShipToAddress,
                                 ReceiptQuantity, CumReceived, Project, OrderStatus,
                                 CreatedDate, UpdatedDate)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                f"{sup}_{item}_{cw}",
                                import_id, cw, order_year,
                                sup, oi.get("SupplierName", ""),
                                oi.get("CustomerCode", ""), oi.get("CustomerName", ""),
                                oi.get("ReleaseDate", ""), oi.get("ReleaseId", ""),
                                oi.get("Buyer", ""), oi.get("ShipToAddress", ""),
                                oi.get("ReceiptQuantity", 0.0), oi.get("CumReceived", 0.0),
                                oi.get("Project", ""), "Active",
                                now, now
                            ))
                            order_id = cur.lastrowid

                        # 行表：仅写当前 CW 的行
                        for ln in g["lines"]:
                            if ln["CalendarWeek"] != cw:
                                continue
                            exists = conn.execute("""
                                SELECT LineId FROM CustomerOrderLines
                                WHERE OrderId = ? AND ItemNumber = ? AND DeliveryDate = ?
                            """, (order_id, ln["ItemNumber"], ln["DeliveryDate"])).fetchone()
                            if not exists:
                                conn.execute("""
                                    INSERT INTO CustomerOrderLines
                                    (OrderId, ImportId, ItemNumber, ItemDescription, UnitOfMeasure,
                                     DeliveryDate, CalendarWeek, OrderType, RequiredQty, CumulativeQty,
                                     NetRequiredQty, InTransitQty, ReceivedQty, LineStatus,
                                     CreatedDate, UpdatedDate)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    order_id, import_id, ln["ItemNumber"], ln["ItemDescription"], ln["UnitOfMeasure"],
                                    ln["DeliveryDate"], ln["CalendarWeek"], ln["OrderType"], ln["RequiredQty"],
                                    ln["CumulativeQty"], ln["NetRequiredQty"], ln["InTransitQty"], ln["ReceivedQty"],
                                    ln["LineStatus"], now, now
                                ))
                conn.commit()

            return True, f"成功导入 {len(orders)} 个订单，{len(order_lines)} 行明细", import_id
        except Exception as e:
            return False, f"导入失败: {e}", 0

    @staticmethod
    def delete_import(import_id: int) -> Tuple[bool, str]:
        try:
            with get_conn() as conn:
                conn.execute("DELETE FROM CustomerOrderLines WHERE ImportId = ?", (import_id,))
                conn.execute("DELETE FROM CustomerOrders     WHERE ImportId = ?", (import_id,))
                conn.execute("DELETE FROM OrderImportHistory WHERE ImportId = ?", (import_id,))
                conn.commit()
            return True, ""
        except Exception as e:
            return False, str(e)

    # ------------------------- 查询 -------------------------
    @staticmethod
    def get_import_history() -> List[Dict]:
        try:
            with get_conn() as conn:
                cur = conn.execute("""
                    SELECT ImportId, FileName, ImportDate, OrderCount, LineCount,
                           ImportStatus, ErrorMessage, ImportedBy
                    FROM OrderImportHistory
                    ORDER BY ImportId DESC
                """)
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print("获取导入历史失败:", e)
            return []

    @staticmethod
    def _get_project_match_code(item_number: str) -> str:
        """获取产品型号的项目匹配码（去掉最后一位）"""
        if not item_number or len(item_number) <= 1:
            return item_number
        return item_number[:-1]

    @staticmethod
    def get_ndlutil_kanban_data(import_id: Optional[int] = None,
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> List[Dict]:
        """汇总视图（全部版本）。返回聚合：FirmQty/ForecastQty/TotalQty。"""
        try:
            where, params = [], []
            if import_id:
                where.append("co.ImportId = ?"); params.append(import_id)
            if start_date:
                where.append("col.DeliveryDate >= ?"); params.append(start_date)
            if end_date:
                where.append("col.DeliveryDate <= ?"); params.append(end_date)
            where_clause = " AND ".join(where) if where else "1=1"

            sql = f"""
                SELECT
                    co.SupplierCode,
                    co.SupplierName,
                    col.ItemNumber,
                    col.ItemDescription,
                    co.ReleaseDate,
                    co.ReleaseId,
                    co.Project,
                    co.SupplierCode AS PurchaseOrder,
                    col.DeliveryDate,
                    col.CalendarWeek,
                    SUM(CASE WHEN col.OrderType='F' THEN col.RequiredQty ELSE 0 END) AS FirmQty,
                    SUM(CASE WHEN col.OrderType='P' THEN col.RequiredQty ELSE 0 END) AS ForecastQty,
                    SUM(col.RequiredQty) AS TotalQty,
                    co.ImportId
                FROM CustomerOrderLines col
                JOIN CustomerOrders co ON col.OrderId = co.OrderId
                WHERE {where_clause}
                GROUP BY
                    co.SupplierCode, co.SupplierName,
                    col.ItemNumber, col.ItemDescription,
                    co.ReleaseDate, co.ReleaseId, co.Project,
                    co.ImportId, col.DeliveryDate, col.CalendarWeek
                ORDER BY co.SupplierCode, col.ItemNumber, col.DeliveryDate
            """
            with get_conn() as conn:
                cur = conn.execute(sql, params)
                rows = [dict(r) for r in cur.fetchall()]
                
                # 按照项目匹配码排序
                for row in rows:
                    row['ProjectMatchCode'] = CustomerOrderService._get_project_match_code(row.get('ItemNumber', ''))
                
                # 定义项目优先级顺序（完整的产品型号）
                priority_projects = [
                    "R001H368", "R001H369",  # Passat
                    "R001P320", "R001P313",  # Tiguan L
                    "R001J139", "R001J140",  # A5L
                    "R001J141", "R001J142"   # Lavida
                ]
                
                def sort_key(row):
                    project_code = row.get('ProjectMatchCode', '')
                    supplier = row.get('SupplierCode', '')
                    
                    # 优先按项目优先级排序
                    if project_code in priority_projects:
                        priority_index = priority_projects.index(project_code)
                    else:
                        # 如果完整匹配失败，尝试基础项目匹配
                        if len(project_code) > 1 and project_code[-1].isdigit():
                            base = project_code[:-1]  # 去掉最后一位数字
                        else:
                            base = project_code
                        
                        base_priority_map = {
                            "R001H36": 10,  # Passat
                            "R001P32": 20,  # Tiguan L
                            "R001J13": 30,  # A5L
                            "R001J14": 40,  # Lavida
                        }
                        priority_index = base_priority_map.get(base, 999)  # 未匹配的项目排在最后
                    
                    return (priority_index, supplier, project_code, row.get('ItemNumber', ''))
                
                rows.sort(key=sort_key)
                return rows
        except Exception as e:
            print("获取NDLUtil看板数据失败:", e)
            return []

    @staticmethod
    def get_orders_by_import_version(import_id: int) -> List[Dict]:
        try:
            with get_conn() as conn:
                cur = conn.execute("""
                    SELECT 
                        co.OrderId, co.OrderNumber, co.SupplierCode, co.SupplierName,
                        co.CustomerCode, co.CustomerName, co.ReleaseDate, co.ReleaseId,
                        co.Buyer, co.ShipToAddress, co.ReceiptQuantity, co.CumReceived,
                        co.Project, co.OrderStatus, co.CreatedDate, co.UpdatedDate,
                        co.Remark, co.ImportId
                    FROM CustomerOrders co
                    WHERE co.ImportId = ?
                    ORDER BY co.OrderNumber
                """, (import_id,))
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print("获取版本订单数据失败:", e)
            return []

    @staticmethod
    def get_order_lines_by_import_version(import_id: int) -> List[Dict]:
        """返回明细行（注意：不再 SELECT 不存在的列）"""
        try:
            with get_conn() as conn:
                cur = conn.execute("""
                    SELECT
                        col.LineId,
                        col.ItemNumber,
                        col.ItemDescription,
                        col.DeliveryDate,
                        col.CalendarWeek,
                        col.OrderType,
                        col.RequiredQty,
                        co.SupplierCode,
                        co.SupplierName,
                        co.ReleaseDate,
                        co.ReleaseId,
                        co.SupplierCode AS PurchaseOrder,
                        COALESCE(co.ReceiptQuantity, 0) AS ReceiptQuantity,
                        COALESCE(co.CumReceived, 0)  AS CumReceived
                    FROM CustomerOrderLines col
                    JOIN CustomerOrders     co  ON col.OrderId = co.OrderId
                    WHERE co.ImportId = ?
                    ORDER BY co.SupplierCode, col.ItemNumber, col.DeliveryDate
                """, (import_id,))
                rows = [dict(r) for r in cur.fetchall()]
                
                # 按照项目匹配码排序
                for row in rows:
                    row['ProjectMatchCode'] = CustomerOrderService._get_project_match_code(row.get('ItemNumber', ''))
                
                # 定义项目优先级顺序（完整的产品型号）
                priority_projects = [
                    "R001H368", "R001H369",  # Passat
                    "R001P320", "R001P313",  # Tiguan L
                    "R001J139", "R001J140",  # A5L
                    "R001J141", "R001J142"   # Lavida
                ]
                
                def sort_key(row):
                    project_code = row.get('ProjectMatchCode', '')
                    supplier = row.get('SupplierCode', '')
                    
                    # 优先按项目优先级排序
                    if project_code in priority_projects:
                        priority_index = priority_projects.index(project_code)
                    else:
                        # 如果完整匹配失败，尝试基础项目匹配
                        if len(project_code) > 1 and project_code[-1].isdigit():
                            base = project_code[:-1]  # 去掉最后一位数字
                        else:
                            base = project_code
                        
                        base_priority_map = {
                            "R001H36": 10,  # Passat
                            "R001P32": 20,  # Tiguan L
                            "R001J13": 30,  # A5L
                            "R001J14": 40,  # Lavida
                        }
                        priority_index = base_priority_map.get(base, 999)  # 未匹配的项目排在最后
                    
                    return (priority_index, supplier, project_code, row.get('ItemNumber', ''))
                
                rows.sort(key=sort_key)
                return rows
        except Exception as e:
            print("获取版本订单明细数据失败:", e)
            return []
