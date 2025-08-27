from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from app.db import query_all, query_one
from app.services.bom_service import BomService
from app.services.inventory_service import InventoryService


class MRPService:
    """MRP计算服务"""

    @staticmethod
    def calculate(start_date: str, end_date: str) -> Dict[str, Dict]:
        """根据订单、BOM和库存计算物料需求"""
        sql = """
            SELECT ItemNumber, DeliveryDate, RequiredQty
            FROM CustomerOrderLines
            WHERE DeliveryDate BETWEEN ? AND ?
        """
        order_lines = query_all(sql, (start_date, end_date))

        requirements = defaultdict(lambda: defaultdict(float))

        for line in order_lines:
            item_code = line['ItemNumber']
            try:
                date_obj = datetime.strptime(line['DeliveryDate'], '%Y-%m-%d')
            except Exception:
                # 跳过无法解析的日期
                continue
            week = f"CW{date_obj.isocalendar()[1]:02d}"
            qty = line['RequiredQty']

            item_row = query_one("SELECT ItemId FROM Items WHERE ItemCode = ?", (item_code,))
            if not item_row:
                continue

            components = BomService.expand_bom(item_row['ItemId'], qty)
            for comp in components:
                comp_code = comp['ItemCode']
                requirements[comp_code][week] += comp['ActualQty']

        result = {}
        for comp_code, week_data in requirements.items():
            item = query_one("SELECT ItemId, CnName FROM Items WHERE ItemCode = ?", (comp_code,))
            inv = InventoryService.get_by_item(item['ItemId']) if item else None
            on_hand = inv['QtyOnHand'] if inv else 0
            projected = on_hand
            weeks_sorted = sorted(week_data.keys())
            week_result = {}
            for wk in weeks_sorted:
                req = week_data[wk]
                projected -= req
                week_result[wk] = {'required': req, 'projected': projected}
            result[comp_code] = {
                'ItemName': item['CnName'] if item else '',
                'OnHand': on_hand,
                'Weeks': week_result
            }

        return result
