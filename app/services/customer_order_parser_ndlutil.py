# app/services/customer_order_parser_ndlutil.py
# -*- coding: utf-8 -*-
"""
独立的 NDLUtil 解析器（可单测/可复用）
注意：这里返回的 DeliveryDate 为 date 对象；如需入库请转成 'YYYY-MM-DD'
"""
import re
from pathlib import Path
from datetime import datetime, date

# -------- 解析规则 --------
RE_SUPPLIER   = re.compile(r"^\s*Supplier:\s*([A-Za-z0-9\-]+)")
RE_SHIPTO     = re.compile(r"^\s*Ship-To:")
RE_ITEM       = re.compile(r"^\s*Item Number:\s*([A-Z0-9\-]+)", re.I)

RE_PO         = re.compile(r"Purchase Order:\s*([A-Z0-9\-]+)", re.I)
RE_RELID      = re.compile(r"Release ID:\s*([\w\-]+)", re.I)
RE_RELD       = re.compile(r"Release Date:\s*([0-9/]+)", re.I)
RE_RECEIPT_Q  = re.compile(r"Receipt Quantity:\s*([0-9][0-9,]*(?:\.\d+)?)", re.I)
RE_CUM_RECV   = re.compile(r"Cum Received:\s*([0-9][0-9,]*(?:\.\d+)?)", re.I)

# 计划行数量：允许整数或小数（修复老版 \.\d 只能一位小数）
RE_LINE       = re.compile(
    r"^\s*(?:Daily|Weekly|Monthly)?\s*([0-9]{2}/[0-9]{2}/[0-9]{2})\s+([FPfp])\s+([0-9][0-9,]*(?:\.\d+)?)(?:\s+.*)?$"
)

DESIRED_PN_ORDER = [
    "R001H368E","R001H369E","R001P320B","R001P313B",
    "R001J139B","R001J140B","R001J141B","R001J142B"
]

def _parse_date_safe(s):
    try:
        return datetime.strptime(s, "%m/%d/%y").date()
    except Exception:
        return s

def parse_txt(paths):
    """
    返回:
      lines: list[dict]  每条计划行（DeliveryDate 为 date 类型）
      release_info: dict[(supplier,item)] -> {release_date, release_id, purchase_order, receipt_qty, cum_received}
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    lines = []
    release_info = {}

    for p in map(Path, paths):
        raw = p.read_text(encoding="utf-8", errors="ignore")

        sup_code = sup_name = None
        item = None

        header_po = header_rel_id = header_rel_date_txt = None
        header_receipt_qty = header_cum_received = None

        po = rel_id = rel_date_txt = None
        receipt_qty = cum_received = None

        capture_name = False

        def flush():
            if sup_code and item:
                key = (sup_code, item)
                info = release_info.get(key, {})
                if rel_date_txt:
                    info["release_date"] = _parse_date_safe(rel_date_txt)
                if rel_id:
                    info["release_id"] = rel_id
                if po:
                    info["purchase_order"] = po
                if receipt_qty is not None:
                    info["receipt_qty"] = float(str(receipt_qty).replace(",", ""))
                if cum_received is not None:
                    info["cum_received"] = float(str(cum_received).replace(",", ""))
                release_info[key] = info

        for ln in raw.splitlines():
            m = RE_SUPPLIER.search(ln)
            if m:
                flush()
                sup_code = m.group(1)
                sup_name = None
                capture_name = True
                header_po = header_rel_id = header_rel_date_txt = None
                header_receipt_qty = header_cum_received = None
                item = None
                po = rel_id = rel_date_txt = None
                receipt_qty = cum_received = None
                continue

            if capture_name:
                if RE_SHIPTO.search(ln):
                    capture_name = False
                    continue
                t = ln.strip()
                if t:
                    sup_name = sup_name or t
                    capture_name = False
                continue

            # 头字段（允许同行多字段）
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
                if item:  rel_date_txt = m.group(1)
                else:     header_rel_date_txt = m.group(1)
            m = RE_RECEIPT_Q.search(ln)
            if m:
                if item:  receipt_qty = m.group(1)
                else:     header_receipt_qty = m.group(1)
            m = RE_CUM_RECV.search(ln)
            if m:
                if item:  cum_received = m.group(1)
                else:     header_cum_received = m.group(1)

            m = RE_ITEM.search(ln)
            if m:
                flush()
                item = m.group(1)
                po = header_po
                rel_id = header_rel_id
                rel_date_txt = header_rel_date_txt
                receipt_qty = header_receipt_qty
                cum_received = header_cum_received
                continue

            m = RE_LINE.match(ln)
            if m and sup_code and item:
                d_s, fp, qty_s = m.groups()
                d = datetime.strptime(d_s, "%m/%d/%y").date()
                fp = fp.upper() if fp.upper() in ("F", "P") else "P"
                qty = float(qty_s.replace(",", ""))
                lines.append({
                    "Supplier": sup_code,
                    "Item": item,
                    "DeliveryDate": d,
                    "OrderType": fp,
                    "RequiredQty": qty,
                    "ReleaseId": rel_id,
                    "ReleaseDate": rel_date_txt,
                    "PurchaseOrder": po,
                    "ReceiptQuantity": receipt_qty,
                    "CumReceived": cum_received,
                    "SupplierName": sup_name,
                })

        flush()

    return lines, release_info
