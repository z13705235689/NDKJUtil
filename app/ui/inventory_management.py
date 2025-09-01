# app/ui/inventory_management.py
# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QLineEdit, QComboBox, QMessageBox,
    QTabWidget, QHeaderView, QAbstractItemView, QFileDialog, QDialog,
    QFormLayout, QDialogButtonBox, QTextEdit, QSpinBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.services.inventory_service import InventoryService
from app.services.item_service import ItemService
from app.services.warehouse_service import WarehouseService

# -------- 数量/单价/安全库存输入对话框 --------
class QtyPriceDialog(QDialog):
    def __init__(self, parent=None, title="登记数量/单价", default_qty=1, default_price=0, default_loc="", default_rm="", default_safety_stock=0):
        super().__init__(parent)
        self.setWindowTitle(title); self.resize(400, 250)
        f = QFormLayout(self)
        self.ed_qty = QLineEdit(str(default_qty))
        self.ed_price = QLineEdit(str(default_price))
        self.ed_loc = QLineEdit(default_loc)
        self.ed_remark = QLineEdit(default_rm)
        self.ed_safety_stock = QLineEdit(str(default_safety_stock))
        f.addRow("数量：", self.ed_qty)
        f.addRow("单价：", self.ed_price)
        f.addRow("库位：", self.ed_loc)
        f.addRow("备注：", self.ed_remark)
        f.addRow("安全库存：", self.ed_safety_stock)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        f.addRow(btns)

    def get_values(self):
        try:
            qty = float(self.ed_qty.text() or "0")
            price = float(self.ed_price.text() or "0")
            safety_stock = float(self.ed_safety_stock.text() or "0")
        except:
            qty, price, safety_stock = 0, 0, 0
        return qty, price, (self.ed_loc.text().strip() or ""), (self.ed_remark.text().strip() or ""), safety_stock

# -------- 安全库存设置对话框 --------
class SafetyStockDialog(QDialog):
    def __init__(self, parent=None, item_code="", item_name="", current_safety_stock=0):
        super().__init__(parent)
        self.setWindowTitle(f"设置安全库存 - {item_code}")
        self.resize(400, 200)
        f = QFormLayout(self)
        
        f.addRow("物料编码：", QLabel(item_code))
        f.addRow("物料名称：", QLabel(item_name))
        
        self.ed_safety_stock = QSpinBox()
        self.ed_safety_stock.setRange(0, 999999)
        self.ed_safety_stock.setValue(int(current_safety_stock))
        f.addRow("安全库存：", self.ed_safety_stock)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        f.addRow(btns)
    
    def get_safety_stock(self):
        return self.ed_safety_stock.value()

# -------- 物料选择对话框（仅 RM/PKG）--------
class ItemPickerDialog(QDialog):
    def __init__(self, parent=None, multi_select=False):
        super().__init__(parent)
        self.multi_select = multi_select
        self.setWindowTitle("选择物料" + (" - 多选" if multi_select else ""))
        self.resize(720, 520)
        v = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("关键字："))
        self.ed_kw = QLineEdit(); self.ed_kw.setPlaceholderText("物料编码/名称")
        self.ed_kw.returnPressed.connect(self.search)
        top.addWidget(self.ed_kw)
        btn = QPushButton("搜索"); btn.clicked.connect(self.search); top.addWidget(btn)
        top.addStretch()
        v.addLayout(top)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["编码","名称","类型","单位","ID"])
        if multi_select:
            self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tbl.setSelectionMode(QAbstractItemView.MultiSelection)
        else:
            self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for c in [2,3,4]:
            self.tbl.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        v.addWidget(self.tbl)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        v.addWidget(btns)

        self.search()

    def search(self):
        kw = self.ed_kw.text().strip()
        rows = ItemService.search_items(kw)
        # 显示所有物料类型，包括成品(FG)、半成品(SFG)、原材料(RM)、包装材料(PKG)
        self.tbl.setRowCount(len(rows))
        for r, it in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(it["ItemCode"]))
            self.tbl.setItem(r, 1, QTableWidgetItem(it.get("CnName","") or ""))
            self.tbl.setItem(r, 2, QTableWidgetItem(it.get("ItemType","") or ""))
            self.tbl.setItem(r, 3, QTableWidgetItem(it.get("Unit","") or ""))
            self.tbl.setItem(r, 4, QTableWidgetItem(str(it["ItemId"])))
        if rows and not self.multi_select:
            self.tbl.selectRow(0)

    def get_selected(self):
        if self.multi_select:
            # 多选模式：返回所有选中的行
            selected_rows = self.tbl.selectionModel().selectedRows()
            if not selected_rows:
                return []
            result = []
            for index in selected_rows:
                r = index.row()
                result.append(dict(
                    ItemId=int(self.tbl.item(r,4).text()),
                    ItemCode=self.tbl.item(r,0).text(),
                    CnName=self.tbl.item(r,1).text(),
                    ItemType=self.tbl.item(r,2).text(),
                    Unit=self.tbl.item(r,3).text(),
                ))
            return result
        else:
            # 单选模式：返回当前选中的行
            r = self.tbl.currentRow()
            if r < 0:
                return None
            return dict(
                ItemId=int(self.tbl.item(r,4).text()),
                ItemCode=self.tbl.item(r,0).text(),
                CnName=self.tbl.item(r,1).text(),
                ItemType=self.tbl.item(r,2).text(),
                Unit=self.tbl.item(r,3).text(),
            )

# -------- 主界面 --------
class InventoryManagement(QWidget):
    """
    库存管理（增强版）
    - 页签：库存余额 / 日常登记 / 现存登记 / 库存流水
    - “日常登记”：先选仓库→展示列表→每行【入库/出库/编辑】
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("库存管理")
        # 移除最小尺寸设置，让页面适应父容器大小
        # self.setMinimumSize(1200, 800)
        
        # 设置大小策略，让页面适应父容器
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 添加成员变量保存原始数据，避免筛选时丢失数据
        self._original_daily_data = []
        self._init_ui()
        self.reload_all()

    # ---------- UI ----------
    def _init_ui(self):
        main = QVBoxLayout(self)
        title = QLabel("库存管理")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main.addWidget(title)

        self.tabs = QTabWidget()
        main.addWidget(self.tabs)

        # 库存余额
        self.tab_balance = QWidget(); self._build_tab_balance(self.tab_balance)
        self.tabs.addTab(self.tab_balance, "库存余额")

        # 日常登记（行内操作）
        self.tab_daily = QWidget(); self._build_tab_daily(self.tab_daily)
        self.tabs.addTab(self.tab_daily, "日常登记")

        # 现存登记
        self.tab_settle = QWidget(); self._build_tab_settle(self.tab_settle)
        self.tabs.addTab(self.tab_settle, "现存登记")

        # 库存流水
        self.tab_tx = QWidget(); self._build_tab_tx(self.tab_tx)
        self.tabs.addTab(self.tab_tx, "库存流水")

    # ---------- 库存余额 ----------
    def _build_tab_balance(self, w: QWidget):
        layout = QVBoxLayout(w)

        box = QGroupBox("汇总 / 操作"); h = QHBoxLayout(box)
        self.lbl_total_items = QLabel("0")
        self.lbl_instock_items = QLabel("0")
        self.lbl_low_stock = QLabel("0")
        h.addWidget(QLabel("总物料数：")); h.addWidget(self.lbl_total_items); h.addSpacing(20)
        h.addWidget(QLabel("有库存物料：")); h.addWidget(self.lbl_instock_items); h.addSpacing(20)
        h.addWidget(QLabel("低于安全库存：")); h.addWidget(self.lbl_low_stock)
        h.addStretch()
        btn_refresh = QPushButton("刷新"); btn_refresh.clicked.connect(self.reload_all); h.addWidget(btn_refresh)
        btn_export = QPushButton("导出余额CSV"); btn_export.clicked.connect(self.export_balance); h.addWidget(btn_export)
        btn_wh = QPushButton("仓库管理"); btn_wh.clicked.connect(self.open_wh_manager); h.addWidget(btn_wh)
        layout.addWidget(box)

        filt = QGroupBox("筛选"); fh = QHBoxLayout(filt)
        fh.addWidget(QLabel("物料关键词：")); self.ed_item_filter = QLineEdit(); self.ed_item_filter.setMaximumWidth(220); fh.addWidget(self.ed_item_filter)
        fh.addWidget(QLabel("仓库：")); self.cb_wh = QComboBox(); self.cb_wh.setMinimumWidth(200); fh.addWidget(self.cb_wh)
        fh.addStretch(); btn_find = QPushButton("查询"); btn_find.clicked.connect(self.load_balance); fh.addWidget(btn_find)
        layout.addWidget(filt)

        self.tbl_balance = QTableWidget(0, 9)
        self.tbl_balance.setHorizontalHeaderLabels(["物料编码","物料名称","类型","单位","仓库","库位","在手数量","安全库存","操作"])
        self.tbl_balance.setAlternatingRowColors(True)
        self.tbl_balance.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.tbl_balance.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in [2,3,4,5,6,7,8]:
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        
        # 设置表格的大小策略，确保有足够的显示空间
        self.tbl_balance.setMinimumHeight(300)  # 调整最小高度为300像素
        self.tbl_balance.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许表格扩展
        
        # 设置合理的行高，避免行高过高
        self.tbl_balance.verticalHeader().setDefaultSectionSize(30)  # 设置默认行高为30像素
        self.tbl_balance.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # 固定行高
        
        # 设置表格字体大小
        font = self.tbl_balance.font()
        font.setPointSize(9)  # 设置字体大小为9pt
        self.tbl_balance.setFont(font)
        
        layout.addWidget(self.tbl_balance)

    def load_balance(self):
        # 获取当前选择的仓库
        cur_wh = self.cb_wh.currentText()
        
        # 只在第一次加载时初始化仓库下拉框
        if self.cb_wh.count() == 0:
            self.cb_wh.blockSignals(True)
            whs = InventoryService.get_warehouses() or ["默认仓库"]
            self.cb_wh.addItem("全部"); [self.cb_wh.addItem(w) for w in whs]
            self.cb_wh.blockSignals(False)
            # 默认选择"全部"
            self.cb_wh.setCurrentText("全部")
            cur_wh = "全部"

        kw = self.ed_item_filter.text().strip()
        
        # 获取库存余额记录
        if cur_wh == "全部":
            # 全部仓库：按物料筛选
            item_id = None
            if kw:
                items = ItemService.search_items(kw)
                if items:
                    item_id = items[0]["ItemId"]
            rows = InventoryService.get_inventory_balance(item_id=item_id)
        else:
            # 指定仓库：显示该仓库下的所有物料
            rows = InventoryService.get_inventory_balance(warehouse=cur_wh)
            
            # 如果指定了物料关键词，进一步筛选
            if kw:
                filtered_rows = []
                for row in rows:
                    if (kw.lower() in row["ItemCode"].lower() or 
                        kw.lower() in (row.get("CnName", "") or "").lower()):
                        filtered_rows.append(row)
                rows = filtered_rows
            
            # 确保所有物料都显示正确的库存数量
            for row in rows:
                if row.get("QtyOnHand", 0) == 0:
                    # 如果显示为0，从库存服务获取真实数量
                    real_qty = InventoryService.get_onhand(row["ItemId"], cur_wh, row.get("Location"))
                    row["QtyOnHand"] = real_qty
        
        # 对数据进行排序：低于安全库存的排在前面
        def sort_key(row):
            qty = int(row.get("QtyOnHand") or 0)
            safety_stock = int(row.get("SafetyStock") or 0)
            # 如果安全库存为0，则不算作低库存
            if safety_stock == 0:
                return (False, row["ItemCode"])  # 正常库存，按编码排序
            # 低于安全库存的排在前面
            is_low_stock = qty < safety_stock
            return (is_low_stock, row["ItemCode"])  # 低库存优先，然后按编码排序
        
        # 按排序键排序，低库存在前
        rows.sort(key=sort_key, reverse=True)
        
        self.tbl_balance.setRowCount(len(rows))
        for r, it in enumerate(rows):
            # 先创建所有表格项
            self.tbl_balance.setItem(r, 0, QTableWidgetItem(it["ItemCode"]))
            self.tbl_balance.setItem(r, 1, QTableWidgetItem(it["CnName"]))
            self.tbl_balance.setItem(r, 2, QTableWidgetItem(it["ItemType"]))
            self.tbl_balance.setItem(r, 3, QTableWidgetItem(it.get("Unit","") or ""))
            self.tbl_balance.setItem(r, 4, QTableWidgetItem(it.get("Warehouse","") or ""))
            self.tbl_balance.setItem(r, 5, QTableWidgetItem(it.get("Location","") or ""))
            qty = int(it.get("QtyOnHand") or 0)
            cell_qty = QTableWidgetItem(str(qty))
            self.tbl_balance.setItem(r, 6, cell_qty)
            ss = int(it.get("SafetyStock") or 0)
            cell_ss = QTableWidgetItem(str(ss))
            self.tbl_balance.setItem(r, 7, cell_ss)
            
            # 检查是否低于安全库存
            if ss > 0 and qty < ss:
                # 低于安全库存：整行背景标红
                for col in range(8):  # 8列（不包括操作列）
                    item = self.tbl_balance.item(r, col)
                    if item:
                        item.setBackground(QColor(255, 200, 200))  # 浅红色背景
                        if col == 6:  # 在手数量列
                            item.setForeground(QColor(220, 20, 60))     # 红色文字
                        elif col == 7:  # 安全库存列
                            item.setForeground(QColor(220, 20, 60))     # 红色文字
            else:
                # 正常库存：绿色背景（仅在手数量列）
                if qty > 0: 
                    cell_qty.setBackground(QColor(198, 224, 180))
            
            # 操作列：安全库存设置按钮
            btn_safety = QPushButton("设置安全库存")
            btn_safety.clicked.connect(lambda checked, row_data=it: self.edit_safety_stock(row_data))
            self.tbl_balance.setCellWidget(r, 8, btn_safety)

        sm = InventoryService.get_inventory_summary()
        self.lbl_total_items.setText(str(sm["total_items"]))
        self.lbl_instock_items.setText(str(sm["items_with_stock"]))
        self.lbl_low_stock.setText(str(sm["low_stock"]))

    # ---------- 日常登记（选择仓库→展示列表→行内操作） ----------
    def _build_tab_daily(self, w: QWidget):
        layout = QVBoxLayout(w)
        
        # 登记条件组
        ctrl = QGroupBox("登记条件"); h = QHBoxLayout(ctrl)
        h.addWidget(QLabel("仓库：")); self.cb_daily_wh = QComboBox(); self.cb_daily_wh.setMinimumWidth(200); h.addWidget(self.cb_daily_wh)
        btn_load = QPushButton("查询"); btn_load.clicked.connect(self.daily_load_list); h.addWidget(btn_load)
        btn_choose = QPushButton("选择物料"); btn_choose.clicked.connect(self.daily_choose_item); h.addWidget(btn_choose)
        h.addStretch(); layout.addWidget(ctrl)
        
        # 搜索和筛选组
        search_group = QGroupBox("搜索和筛选"); search_layout = QVBoxLayout(search_group)
        
        # 第一行：搜索框和按钮
        search_row1 = QHBoxLayout()
        search_row1.addWidget(QLabel("物料搜索："))
        self.ed_daily_search = QLineEdit()
        self.ed_daily_search.setPlaceholderText("输入物料编码或名称进行搜索")
        self.ed_daily_search.setMinimumWidth(300)
        self.ed_daily_search.textChanged.connect(self.daily_apply_filters)  # 实时搜索
        search_row1.addWidget(self.ed_daily_search)
        
        self.btn_daily_search = QPushButton("搜索")
        self.btn_daily_search.clicked.connect(self.daily_apply_filters)
        search_row1.addWidget(self.btn_daily_search)
        
        search_row1.addStretch()
        search_layout.addLayout(search_row1)
        
        # 第二行：物料类型筛选
        search_row2 = QHBoxLayout()
        search_row2.addWidget(QLabel("物料类型："))
        self.cb_daily_item_type = QComboBox()
        self.cb_daily_item_type.addItem("全部类型", "")
        self.cb_daily_item_type.addItem("成品 (FG)", "FG")
        self.cb_daily_item_type.addItem("半成品 (SFG)", "SFG")
        self.cb_daily_item_type.addItem("原材料 (RM)", "RM")
        self.cb_daily_item_type.addItem("包装材料 (PKG)", "PKG")
        self.cb_daily_item_type.currentTextChanged.connect(self.daily_apply_filters)  # 实时筛选
        search_row2.addWidget(self.cb_daily_item_type)
        
        # 清除筛选按钮
        self.btn_clear_filters = QPushButton("清除筛选")
        self.btn_clear_filters.clicked.connect(self.daily_clear_filters)
        search_row2.addWidget(self.btn_clear_filters)
        
        search_row2.addStretch()
        search_layout.addLayout(search_row2)
        
        layout.addWidget(search_group)

        self.tbl_daily = QTableWidget(0, 7)
        self.tbl_daily.setHorizontalHeaderLabels(["物料编码","物料名称","在手","单位","库位","安全库存","操作"])
        header = self.tbl_daily.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in [2,3,4,5,6]:
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        
        # 设置表格的大小策略，确保有足够的显示空间
        self.tbl_daily.setMinimumHeight(300)  # 调整最小高度为300像素
        self.tbl_daily.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许表格扩展
        
        # 设置合理的行高，避免行高过高
        self.tbl_daily.verticalHeader().setDefaultSectionSize(30)  # 设置默认行高为30像素
        self.tbl_daily.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # 固定行高
        
        # 设置表格字体大小
        font = self.tbl_daily.font()
        font.setPointSize(9)  # 设置字体大小为9pt
        self.tbl_daily.setFont(font)
        
        layout.addWidget(self.tbl_daily)

    def daily_load_list(self):
        # 获取当前选择的仓库
        wh = self.cb_daily_wh.currentText() or "默认仓库"
        
        # 每次加载时都刷新仓库下拉框，确保删除的仓库不会显示
        self.cb_daily_wh.clear()
        warehouses = InventoryService.get_warehouses() or ["默认仓库"]
        for w in warehouses:
            self.cb_daily_wh.addItem(w)
        
        # 如果之前选择的仓库仍然存在，则保持选择；否则选择第一个
        if wh in warehouses:
            self.cb_daily_wh.setCurrentText(wh)
        elif warehouses:
            self.cb_daily_wh.setCurrentText(warehouses[0])
            wh = warehouses[0]
        
        # 获取该仓库中确实存在的物料列表
        warehouse_items = WarehouseService.list_items_by_warehouse_name(wh)
        
        # 为每个物料获取库存信息
        display_rows = []
        for item in warehouse_items:
            # 获取库存余额信息
            balance_info = InventoryService.get_inventory_balance(item_id=item["ItemId"], warehouse=wh)
            
            if balance_info:
                # 有库存余额记录
                for balance in balance_info:
                    display_rows.append({
                        "ItemId": item["ItemId"],
                        "ItemCode": item["ItemCode"],
                        "CnName": item.get("CnName", ""),
                        "ItemType": item.get("ItemType", ""),
                        "Unit": item.get("Unit", ""),
                        "Warehouse": wh,
                        "Location": balance.get("Location", ""),
                        "QtyOnHand": balance.get("QtyOnHand", 0),
                        "SafetyStock": item.get("SafetyStock", 0)
                    })
            else:
                # 没有库存余额记录，从库存服务获取真实数量
                real_qty = InventoryService.get_onhand(item["ItemId"], wh, None)
                display_rows.append({
                    "ItemId": item["ItemId"],
                    "ItemCode": item["ItemCode"],
                    "CnName": item.get("CnName", ""),
                    "ItemType": item.get("ItemType", ""),
                    "Unit": item.get("Unit", ""),
                    "Warehouse": wh,
                    "Location": "",
                    "QtyOnHand": real_qty,
                    "SafetyStock": item.get("SafetyStock", 0)
                })
        
        # 保存原始数据用于筛选
        self._original_daily_data = display_rows.copy()
        
        # 使用统一的渲染方法
        self._render_daily_table(display_rows)

    def row_in(self, rec):
        wh = self.cb_daily_wh.currentText() or "默认仓库"
        d = QtyPriceDialog(self, title=f"入库：{rec['ItemCode']}")
        if d.exec()!=QDialog.Accepted: return
        qty, price, loc, rm, _ = d.get_values()  # 忽略安全库存
        if qty<=0: return
        InventoryService.receive_inventory(rec["ItemId"], qty, warehouse=wh,
            unit_cost=(price or None), location=(loc or None), remark=(rm or "行内入库"))
        self.daily_load_list()

    def row_out(self, rec):
        wh = self.cb_daily_wh.currentText() or "默认仓库"
        # 检查当前库存
        current_stock = InventoryService.get_onhand(rec["ItemId"], wh, rec.get("Location"))
        
        d = QtyPriceDialog(self, title=f"出库：{rec['ItemCode']}", default_price=0)
        if d.exec()!=QDialog.Accepted: return
        qty, _, loc, rm, _ = d.get_values()  # 忽略安全库存
        if qty<=0: return
        
        # 检查出库数量是否超过现有库存
        if qty > current_stock:
            QMessageBox.warning(self, "库存不足", 
                              f"出库数量 {qty} 超过现有库存 {current_stock}\n"
                              f"物料：{rec['ItemCode']} - {rec.get('CnName', '')}\n"
                              f"仓库：{wh}")
            return
        
        # 执行出库
        InventoryService.issue_inventory(rec["ItemId"], qty, warehouse=wh,
            location=(loc or None), remark=(rm or "行内出库"))
        self.daily_load_list()

    def row_edit(self, rec):
        wh = self.cb_daily_wh.currentText() or "默认仓库"
        onhand = InventoryService.get_onhand(rec["ItemId"], wh, rec.get("Location"))
        
        # 查询物料的详细信息，包括安全库存
        item_info = ItemService.get_item_by_id(rec["ItemId"])
        current_safety_stock = item_info.get("SafetyStock", 0) if item_info else 0
        
        # 使用新的对话框，包含安全库存输入
        d = QtyPriceDialog(self, title=f"编辑库存：{rec['ItemCode']} {rec.get('CnName','')}", 
                          default_qty=int(onhand), 
                          default_loc=rec.get("Location") or "",
                          default_safety_stock=current_safety_stock)
        if d.exec()!=QDialog.Accepted: return
        target, _, loc, rm, new_safety_stock = d.get_values()
        
        # 如果安全库存有变化，先更新安全库存
        if new_safety_stock != current_safety_stock:
            try:
                ItemService.update_safety_stock(rec["ItemId"], new_safety_stock)
            except Exception as e:
                QMessageBox.warning(self, "安全库存更新失败", f"更新安全库存时发生错误：{e}")
        
        # 更新库存数量
        InventoryService.set_onhand(rec["ItemId"], warehouse=wh, target_qty=target,
            location=(loc or rec.get("Location")), remark_prefix=(rm or "行内登记现存"))
        self.daily_load_list()

    def row_delete(self, rec):
        """删除物料从仓库"""
        wh = self.cb_daily_wh.currentText() or "默认仓库"
        current_stock = InventoryService.get_onhand(rec["ItemId"], wh, rec.get("Location"))
        
        # 检查物料是否真的存在于该仓库中
        warehouse_items = WarehouseService.list_items_by_warehouse_name(wh)
        item_exists_in_warehouse = any(item["ItemId"] == rec["ItemId"] for item in warehouse_items)
        
        if not item_exists_in_warehouse:
            QMessageBox.warning(self, "删除失败", 
                              f"物料 '{rec['ItemCode']}' 在仓库 '{wh}' 中不存在，无法删除。\n"
                              f"该物料可能只是显示在库存余额中，但并未添加到仓库物料清单中。")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要从仓库 '{wh}' 中删除物料 '{rec['ItemCode']} - {rec.get('CnName', '')}' 吗？\n"
            f"当前库存：{current_stock}\n"
            f"库位：{rec.get('Location', '') or '默认库位'}\n\n"
            f"删除后该物料将不再在此仓库显示。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 如果有库存，先清零库存
            if current_stock > 0:
                InventoryService.set_onhand(
                    rec["ItemId"], 
                    warehouse=wh, 
                    target_qty=0,
                    location=rec.get("Location"),
                    remark_prefix="删除物料前清零库存"
                )
            
            # 从仓库中删除物料
            WarehouseService.remove_item_from_warehouse(rec["ItemId"], wh)
            
            QMessageBox.information(self, "删除成功", f"物料 '{rec['ItemCode']}' 已从仓库 '{wh}' 中删除")
            
            # 立即刷新页面，确保物料从列表中消失
            self.daily_load_list()
            
        except Exception as e:
            QMessageBox.warning(self, "删除失败", f"删除物料时发生错误：{e}")

    def daily_choose_item(self):
        # 获取当前选择的仓库
        wh = self.cb_daily_wh.currentText() or "默认仓库"
        
        # 获取仓库中已存在的物料ID列表
        warehouse_items = WarehouseService.list_items_by_warehouse_name(wh)
        existing_item_ids = {item["ItemId"] for item in warehouse_items}
        
        # 用选择器选择物料（只能选择仓库中不存在的）
        dlg = ItemPickerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            it = dlg.get_selected()
            if not it: return
            
            # 检查物料是否已经在仓库中
            if it["ItemId"] in existing_item_ids:
                QMessageBox.warning(self, "物料已存在", 
                                  f"物料 '{it['ItemCode']}' 已经在仓库 '{wh}' 中存在，无需重复添加。")
                return
            
            # 先添加到仓库中
            try:
                # 获取仓库ID
                warehouse = WarehouseService.get_by_code(wh)
                if not warehouse:
                    QMessageBox.warning(self, "仓库不存在", f"仓库 '{wh}' 不存在")
                    return
                
                # 添加物料到仓库
                WarehouseService.add_item(warehouse["WarehouseId"], it["ItemId"])
                
                # 然后进行库存登记
                d2 = QtyPriceDialog(self, title=f"登记：{it['ItemCode']} {it.get('CnName','')}")
                if d2.exec()!=QDialog.Accepted: return
                qty, price, loc, rm, _ = d2.get_values()  # 忽略安全库存
                if qty==0: return
                
                # 执行入库
                InventoryService.receive_inventory(it["ItemId"], qty, warehouse=wh,
                    unit_cost=(price or None), location=(loc or None), remark=(rm or "选择器登记"))
                
                QMessageBox.information(self, "添加成功", 
                                      f"物料 '{it['ItemCode']}' 已添加到仓库 '{wh}' 并登记库存 {qty}")
                self.daily_load_list()
                
            except Exception as e:
                QMessageBox.warning(self, "添加失败", f"添加物料时发生错误：{e}")

    def daily_apply_filters(self):
        """应用搜索和筛选条件"""
        # 如果没有原始数据，先加载数据
        if not self._original_daily_data:
            self.daily_load_list()
            return
        
        # 从原始数据开始筛选
        filtered_rows = self._original_daily_data.copy()
        
        # 应用搜索条件
        search_text = self.ed_daily_search.text().strip().lower()
        if search_text:
            filtered_rows = [row for row in filtered_rows if 
                           search_text in row["ItemCode"].lower() or 
                           search_text in row["CnName"].lower()]
        
        # 应用物料类型筛选
        selected_type = self.cb_daily_item_type.currentData()
        if selected_type:
            # 创建物料类型映射，支持中英文匹配
            type_mapping = {
                "成品 (FG)": ["FG", "成品"],
                "半成品 (SFG)": ["SFG", "半成品"],
                "原材料 (RM)": ["RM", "原材料"],
                "包装材料 (PKG)": ["PKG", "包装材料"]
            }
            
            # 获取当前选中类型的匹配值列表
            target_types = type_mapping.get(selected_type, [selected_type])
            
            # 筛选匹配的物料
            filtered_rows = [row for row in filtered_rows if row["ItemType"] in target_types]
        
        # 显示筛选后的数据
        self._render_daily_table(filtered_rows)

    def _render_daily_table(self, rows):
        """渲染日常登记表格"""
        # 对数据进行排序：低于安全库存的排在前面
        def sort_key(row):
            qty = int(row.get("QtyOnHand") or 0)
            safety_stock = int(row.get("SafetyStock") or 0)
            # 如果安全库存为0，则不算作低库存
            if safety_stock == 0:
                return (False, row["ItemCode"])  # 正常库存，按编码排序
            # 低于安全库存的排在前面
            is_low_stock = qty < safety_stock
            return (is_low_stock, row["ItemCode"])  # 低库存优先，然后按编码排序
        
        # 按排序键排序，低库存在前
        rows.sort(key=sort_key, reverse=True)
        
        self.tbl_daily.setRowCount(len(rows))
        for r, row_data in enumerate(rows):
            # 重新创建表格项，并保存ItemId和ItemType数据
            item_code_cell = QTableWidgetItem(row_data["ItemCode"])
            item_code_cell.setData(Qt.UserRole, row_data["ItemId"])  # 存储ItemId
            item_code_cell.setData(Qt.UserRole + 1, row_data["ItemType"])  # 存储ItemType
            self.tbl_daily.setItem(r, 0, item_code_cell)
            
            self.tbl_daily.setItem(r, 1, QTableWidgetItem(row_data["CnName"]))
            qty = int(row_data["QtyOnHand"] or 0)
            qty_cell = QTableWidgetItem(str(qty))
            self.tbl_daily.setItem(r, 2, qty_cell)
            
            self.tbl_daily.setItem(r, 3, QTableWidgetItem(row_data["Unit"]))
            self.tbl_daily.setItem(r, 4, QTableWidgetItem(row_data["Location"]))
            ss = int(row_data["SafetyStock"] or 0)
            ss_cell = QTableWidgetItem(str(ss))
            self.tbl_daily.setItem(r, 5, ss_cell)
            
            # 检查是否低于安全库存
            if ss > 0 and qty < ss:
                # 低于安全库存：整行背景标红
                for col in range(6):  # 6列（不包括操作列）
                    item = self.tbl_daily.item(r, col)
                    if item:
                        item.setBackground(QColor(255, 200, 200))  # 浅红色背景
                        if col == 2:  # 在手数量列
                            item.setForeground(QColor(220, 20, 60))     # 红色文字
                        elif col == 5:  # 安全库存列
                            item.setForeground(QColor(220, 20, 60))     # 红色文字
            else:
                # 正常库存：绿色背景（仅在手数量列）
                if qty > 0: 
                    qty_cell.setBackground(QColor(198, 224, 180))
            
            # 重新创建操作按钮
            w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0,0,0,0)
            b_in = QPushButton("入库"); b_out = QPushButton("出库"); b_edit = QPushButton("编辑"); b_delete = QPushButton("删除")
            b_in.clicked.connect(lambda _, rec=row_data: self.row_in(rec))
            b_out.clicked.connect(lambda _, rec=row_data: self.row_out(rec))
            b_edit.clicked.connect(lambda _, rec=row_data: self.row_edit(rec))
            b_delete.clicked.connect(lambda _, rec=row_data: self.row_delete(rec))
            h.addWidget(b_in); h.addWidget(b_out); h.addWidget(b_edit); h.addWidget(b_delete)
            self.tbl_daily.setCellWidget(r, 6, w)

    def daily_clear_filters(self):
        """清除所有筛选条件"""
        self.ed_daily_search.clear()
        self.cb_daily_item_type.setCurrentIndex(0)
        # 重新加载完整数据
        self.daily_load_list()

    # ---------- 现存登记 ----------
    def _build_tab_settle(self, w: QWidget):
        layout = QVBoxLayout(w)
        frm = QGroupBox("登记现有库存"); f = QFormLayout(frm)

        self.lb_settle_item = QLabel("-")
        self.btn_settle_pick = QPushButton("选择物料")
        self.btn_settle_pick.clicked.connect(self.settle_pick_item)
        h1 = QHBoxLayout(); h1.addWidget(self.lb_settle_item); h1.addStretch(); h1.addWidget(self.btn_settle_pick)
        f.addRow(QLabel("物料："), self._wrap(h1))

        self.cb_settle_wh = QComboBox(); f.addRow("仓库：", self.cb_settle_wh)
        self.ed_settle_loc = QLineEdit(); f.addRow("库位：", self.ed_settle_loc)

        self.lb_onhand = QLabel("0"); self.btn_load_onhand = QPushButton("读取当前"); self.btn_load_onhand.clicked.connect(self.load_settle_onhand)
        h2 = QHBoxLayout(); h2.addWidget(self.lb_onhand); h2.addStretch(); h2.addWidget(self.btn_load_onhand)
        f.addRow(QLabel("当前在手："), self._wrap(h2))

        self.ed_target = QLineEdit("0"); f.addRow("登记为：", self.ed_target)

        self.btn_do_settle = QPushButton("登记为现存（自动生成调整）")
        self.btn_do_settle.clicked.connect(self.commit_settle)
        f.addRow("", self.btn_do_settle)

        layout.addWidget(frm)
        tip = QLabel("说明：把在手量直接登记为目标值，系统自动生成 ADJ 差异，适合期初/复核。")
        tip.setStyleSheet("color:#666;"); layout.addWidget(tip)
        self._settle_item = None

    def _wrap(self, lay): w = QWidget(); w.setLayout(lay); return w

    def settle_pick_item(self):
        dlg = ItemPickerDialog(self)
        if dlg.exec() == QDialog.Accepted:
            it = dlg.get_selected()
            if not it: return
            self._settle_item = it
            self.lb_settle_item.setText(f"{it['ItemCode']}  {it.get('CnName','')}")
            self.load_settle_onhand()

    def load_settle_onhand(self):
        self.cb_settle_wh.clear()
        for w in InventoryService.get_warehouses(): self.cb_settle_wh.addItem(w)
        if not self._settle_item: return
        wh = self.cb_settle_wh.currentText() or "默认仓库"
        loc = self.ed_settle_loc.text().strip() or None
        onhand = InventoryService.get_onhand(self._settle_item["ItemId"], wh, loc)
        self.lb_onhand.setText(str(int(onhand)))

    def commit_settle(self):
        if not self._settle_item:
            QMessageBox.information(self,"提示","请先选择物料"); return
        wh = self.cb_settle_wh.currentText() or "默认仓库"
        loc = self.ed_settle_loc.text().strip() or None
        try:
            target = float(self.ed_target.text() or 0)
        except: target = 0
        diff = InventoryService.set_onhand(self._settle_item["ItemId"], wh, target, loc)
        QMessageBox.information(self, "完成", f"已登记为 {target}（差异 {diff:+}）")

    # ---------- 库存流水 ----------
    def _build_tab_tx(self, w: QWidget):
        layout = QVBoxLayout(w)
        filt = QGroupBox("筛选"); h = QHBoxLayout(filt)
        h.addWidget(QLabel("关键词：")); self.ed_tx_kw = QLineEdit(); h.addWidget(self.ed_tx_kw)
        h.addWidget(QLabel("仓库：")); self.cb_tx_wh = QComboBox(); h.addWidget(self.cb_tx_wh)
        h.addStretch()
        btn_q = QPushButton("查询"); btn_q.clicked.connect(self.load_tx); h.addWidget(btn_q)
        layout.addWidget(filt)

        self.tbl_tx = QTableWidget(0, 9)
        self.tbl_tx.setHorizontalHeaderLabels(["日期","类型","仓库","库位","物料编码","物料名称","数量","单价","备注"])
        header = self.tbl_tx.horizontalHeader()
        for c in [0,1,2,3,4,6,7,8]:
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        
        # 设置表格的大小策略，确保有足够的显示空间
        self.tbl_tx.setMinimumHeight(300)  # 调整最小高度为300像素
        self.tbl_tx.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许表格扩展
        
        # 设置合理的行高，避免行高过高
        self.tbl_tx.verticalHeader().setDefaultSectionSize(30)  # 设置默认行高为30像素
        self.tbl_tx.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # 固定行高
        
        # 设置表格字体大小
        font = self.tbl_tx.font()
        font.setPointSize(9)  # 设置字体大小为9pt
        self.tbl_tx.setFont(font)
        
        layout.addWidget(self.tbl_tx)

    def load_tx(self):
        self.cb_tx_wh.clear()
        self.cb_tx_wh.addItem("全部")
        for w in InventoryService.get_warehouses(): self.cb_tx_wh.addItem(w)
        kw = self.ed_tx_kw.text().strip()
        item_id = None
        if kw:
            items = ItemService.search_items(kw)
            # 移除物料类型筛选，显示所有类型的物料
            if items: item_id = items[0]["ItemId"]
        wh = None if self.cb_tx_wh.currentText()=="全部" else self.cb_tx_wh.currentText()
        rows = InventoryService.list_transactions(item_id=item_id, warehouse=wh)
        self.tbl_tx.setRowCount(len(rows))
        for r, t in enumerate(rows):
            self.tbl_tx.setItem(r, 0, QTableWidgetItem(t.get("TxDate","")))
            self.tbl_tx.setItem(r, 1, QTableWidgetItem(t.get("TxType","")))
            self.tbl_tx.setItem(r, 2, QTableWidgetItem(t.get("Warehouse","") or ""))
            self.tbl_tx.setItem(r, 3, QTableWidgetItem(t.get("Location","") or ""))
            self.tbl_tx.setItem(r, 4, QTableWidgetItem(t.get("ItemCode","")))
            self.tbl_tx.setItem(r, 5, QTableWidgetItem(t.get("CnName","") or ""))
            self.tbl_tx.setItem(r, 6, QTableWidgetItem(str(t.get("Qty") or 0)))
            self.tbl_tx.setItem(r, 7, QTableWidgetItem("" if t.get("UnitCost") is None else str(t.get("UnitCost"))))
            self.tbl_tx.setItem(r, 8, QTableWidgetItem(t.get("Remark","") or ""))

    # ---------- 工具 ----------
    def reload_all(self):
        self.load_balance()
        self.daily_load_list()
        self.load_settle_onhand()
        self.load_tx()

    def edit_safety_stock(self, row_data):
        """编辑安全库存"""
        dlg = SafetyStockDialog(
            self, 
            row_data["ItemCode"], 
            row_data["CnName"], 
            row_data.get("SafetyStock", 0)
        )
        if dlg.exec() == QDialog.Accepted:
            new_safety_stock = dlg.get_safety_stock()
            try:
                # 更新物料表中的安全库存
                from app.services.item_service import ItemService
                ItemService.update_safety_stock(row_data["ItemId"], new_safety_stock)
                QMessageBox.information(self, "完成", f"安全库存已更新为 {new_safety_stock}")
                self.load_balance()  # 重新加载数据
            except Exception as e:
                QMessageBox.critical(self, "更新失败", f"更新安全库存时发生错误：{e}")

    def export_balance(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出库存余额", "库存余额.csv", "CSV Files (*.csv)")
        if not path: return
        import csv
        rows = []
        for r in range(self.tbl_balance.rowCount()):
            rows.append([
                self.tbl_balance.item(r,0).text(),
                self.tbl_balance.item(r,1).text(),
                self.tbl_balance.item(r,2).text(),
                self.tbl_balance.item(r,3).text(),
                self.tbl_balance.item(r,4).text(),
                self.tbl_balance.item(r,5).text(),
                self.tbl_balance.item(r,6).text(),
                self.tbl_balance.item(r,7).text(),
            ])
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f); writer.writerow(["物料编码","物料名称","类型","单位","仓库","库位","在手数量","安全库存"]); writer.writerows(rows)
        QMessageBox.information(self, "导出完成", path)

    # ---------- 仓库管理入口 ----------
    def open_wh_manager(self):
        dlg = WarehouseManagerDialog(self)
        dlg.exec()
        self.reload_all()

# -------- 仓库管理对话框（CRUD + 维护仓库物料）--------
class WarehouseManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("仓库管理")
        self.resize(900, 600)
        v = QVBoxLayout(self)

        top = QHBoxLayout()
        btn_add = QPushButton("新增仓库"); btn_add.clicked.connect(self.add_wh)
        btn_edit = QPushButton("编辑仓库"); btn_edit.clicked.connect(self.edit_wh)
        btn_del = QPushButton("删除仓库"); btn_del.clicked.connect(self.del_wh)
        btn_disable = QPushButton("停用仓库"); btn_disable.clicked.connect(self.disable_wh)
        top.addWidget(btn_add); top.addWidget(btn_edit); top.addWidget(btn_del); top.addWidget(btn_disable); top.addStretch()
        v.addLayout(top)

        self.tbl_wh = QTableWidget(0, 4)
        self.tbl_wh.setHorizontalHeaderLabels(["ID","编码","名称","备注"])
        self.tbl_wh.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for c in [1,2,3]: self.tbl_wh.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        
        # 设置表格的大小策略，确保有足够的显示空间
        self.tbl_wh.setMinimumHeight(200)  # 设置最小高度
        self.tbl_wh.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许表格扩展
        
        # 设置合理的行高，避免行高过高
        self.tbl_wh.verticalHeader().setDefaultSectionSize(25)  # 设置默认行高为25像素
        self.tbl_wh.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # 固定行高
        
        # 设置表格字体大小
        font = self.tbl_wh.font()
        font.setPointSize(9)  # 设置字体大小为9pt
        self.tbl_wh.setFont(font)
        
        v.addWidget(self.tbl_wh)

        mid = QHBoxLayout(); v.addLayout(mid)
        mid.addWidget(QLabel("仓库物料清单："))
        btn_ai = QPushButton("添加物料"); btn_ai.clicked.connect(self.add_item); mid.addWidget(btn_ai)
        btn_ri = QPushButton("移除物料"); btn_ri.clicked.connect(self.remove_item); mid.addWidget(btn_ri)
        mid.addStretch()

        self.tbl_items = QTableWidget(0,5)
        self.tbl_items.setHorizontalHeaderLabels(["ItemId","编码","名称","单位","类型"])
        for c in range(5): self.tbl_items.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.tbl_items.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        # 设置表格的大小策略，确保有足够的显示空间
        self.tbl_items.setMinimumHeight(200)  # 设置最小高度
        self.tbl_items.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许表格扩展
        
        # 设置合理的行高，避免行高过高
        self.tbl_items.verticalHeader().setDefaultSectionSize(25)  # 设置默认行高为25像素
        self.tbl_items.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)  # 固定行高
        
        # 设置表格字体大小
        font = self.tbl_items.font()
        font.setPointSize(9)  # 设置字体大小为9pt
        self.tbl_items.setFont(font)
        
        v.addWidget(self.tbl_items)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject); btns.accepted.connect(self.accept)
        v.addWidget(btns)

        self.reload()

        self.tbl_wh.itemSelectionChanged.connect(self.load_items_for_wh)

    def current_wh_id(self):
        r = self.tbl_wh.currentRow()
        if r < 0: return None
        return int(self.tbl_wh.item(r,0).text())

    def reload(self):
        rows = WarehouseService.list_warehouses(active_only=False)
        self.tbl_wh.setRowCount(len(rows))
        for r, w in enumerate(rows):
            self.tbl_wh.setItem(r,0,QTableWidgetItem(str(w["WarehouseId"])))
            self.tbl_wh.setItem(r,1,QTableWidgetItem(w["Code"]))
            self.tbl_wh.setItem(r,2,QTableWidgetItem(w["Name"]))
            self.tbl_wh.setItem(r,3,QTableWidgetItem(w.get("Remark","") or ""))
        if rows: self.tbl_wh.selectRow(0)
        self.load_items_for_wh()

    def load_items_for_wh(self):
        wid = self.current_wh_id()
        if not wid:
            self.tbl_items.setRowCount(0); return
        rows = WarehouseService.list_items(wid)
        self.tbl_items.setRowCount(len(rows))
        for r, it in enumerate(rows):
            self.tbl_items.setItem(r,0,QTableWidgetItem(str(it["ItemId"])))
            self.tbl_items.setItem(r,1,QTableWidgetItem(it["ItemCode"]))
            self.tbl_items.setItem(r,2,QTableWidgetItem(it["CnName"]))
            self.tbl_items.setItem(r,3,QTableWidgetItem(it.get("Unit","") or ""))
            self.tbl_items.setItem(r,4,QTableWidgetItem(it.get("ItemType","") or ""))

    def add_wh(self):
        dlg = QDialog(self); dlg.setWindowTitle("新增仓库"); f = QFormLayout(dlg)
        ed_code=QLineEdit(); ed_name=QLineEdit(); ed_rm=QLineEdit()
        f.addRow("编码：",ed_code); f.addRow("名称：",ed_name); f.addRow("备注：",ed_rm)
        btns=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); f.addRow(btns)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        if dlg.exec()!=QDialog.Accepted: return
        if not ed_code.text().strip(): return
        WarehouseService.create(ed_code.text().strip(), ed_name.text().strip() or ed_code.text().strip(), ed_rm.text().strip())
        self.reload()

    def edit_wh(self):
        wid = self.current_wh_id()
        if not wid: return
        wh = WarehouseService.get_by_id(wid)
        dlg = QDialog(self); dlg.setWindowTitle("编辑仓库"); f = QFormLayout(dlg)
        ed_code=QLineEdit(wh["Code"]); ed_name=QLineEdit(wh["Name"]); ed_rm=QLineEdit(wh.get("Remark","") or "")
        f.addRow("编码：",ed_code); f.addRow("名称：",ed_name); f.addRow("备注：",ed_rm)
        btns=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); f.addRow(btns)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        if dlg.exec()!=QDialog.Accepted: return
        WarehouseService.update(wid, dict(Code=ed_code.text().strip(), Name=ed_name.text().strip(), Remark=ed_rm.text().strip(), IsActive=1))
        self.reload()

    def del_wh(self):
        wid = self.current_wh_id()
        if not wid: return
        
        # 确认删除
        reply = QMessageBox.question(self, "确认删除", 
                                   "确定要删除这个仓库吗？\n\n删除操作将同时删除：\n• 该仓库的所有库存余额记录\n• 该仓库的所有库存流水记录\n• 该仓库的所有物料关联信息\n\n删除后将无法恢复！",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        try:
            WarehouseService.delete(wid)
            QMessageBox.information(self, "完成", "仓库已删除，相关数据已清理")
            self.reload()
            # 通知父窗口刷新仓库列表
            if hasattr(self.parent(), 'reload_all'):
                self.parent().reload_all()
        except Exception as e:
            QMessageBox.critical(self, "删除失败", f"删除仓库时发生错误：{e}")
    
    def disable_wh(self):
        wid = self.current_wh_id()
        if not wid: return
        
        # 确认停用
        reply = QMessageBox.question(self, "确认停用", 
                                   "确定要停用这个仓库吗？\n停用后仓库将不可用，但数据会保留。",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        WarehouseService.disable(wid)
        QMessageBox.information(self, "完成", "仓库已停用")
        self.reload()

    def add_item(self):
        wid = self.current_wh_id()
        if not wid: return
        dlg = ItemPickerDialog(self, multi_select=True)
        if dlg.exec()!=QDialog.Accepted: return
        items = dlg.get_selected()
        if not items: return
        
        # 批量添加物料
        if isinstance(items, list):
            # 多选模式
            added_count = WarehouseService.add_items_batch(wid, [item["ItemId"] for item in items])
            QMessageBox.information(self, "完成", f"已添加 {added_count} 个物料到仓库")
        else:
            # 单选模式（兼容性）
            WarehouseService.add_item(wid, items["ItemId"])
            QMessageBox.information(self, "完成", "已添加物料到仓库")
        
        self.load_items_for_wh()

    def remove_item(self):
        wid = self.current_wh_id()
        r = self.tbl_items.currentRow()
        if not wid or r<0: return
        iid = int(self.tbl_items.item(r,0).text())
        WarehouseService.remove_item(wid, iid)
        self.load_items_for_wh()
