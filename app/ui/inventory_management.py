# app/ui/inventory_management.py
# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QLineEdit, QComboBox, QMessageBox,
    QTabWidget, QHeaderView, QAbstractItemView, QFileDialog, QDialog,
    QFormLayout, QDialogButtonBox, QTextEdit, QSpinBox, QSizePolicy,
    QProgressBar, QScrollArea, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.services.inventory_service import InventoryService
from app.services.item_service import ItemService
from app.services.warehouse_service import WarehouseService
from app.services.inventory_import_service import InventoryImportService

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
            
            # 数据验证
            if qty < 0:
                QMessageBox.warning(self, "数据错误", "数量不能为负数")
                return None, None, None, None, None
            if price < 0:
                QMessageBox.warning(self, "数据错误", "单价不能为负数")
                return None, None, None, None, None
            if safety_stock < 0:
                QMessageBox.warning(self, "数据错误", "安全库存不能为负数")
                return None, None, None, None, None
                
        except ValueError as e:
            QMessageBox.warning(self, "数据格式错误", f"请输入有效的数字格式：{e}")
            return None, None, None, None, None
        except Exception as e:
            QMessageBox.warning(self, "数据错误", f"数据验证失败：{e}")
            return None, None, None, None, None
            
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
        # 过滤禁用状态的物料，只显示启用的物料
        enabled_rows = [item for item in rows if item.get("IsActive", 1) == 1]
        self.tbl.setRowCount(len(enabled_rows))
        for r, it in enumerate(enabled_rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(it["ItemCode"]))
            self.tbl.setItem(r, 1, QTableWidgetItem(it.get("CnName","") or ""))
            self.tbl.setItem(r, 2, QTableWidgetItem(it.get("ItemType","") or ""))
            self.tbl.setItem(r, 3, QTableWidgetItem(it.get("Unit","") or ""))
            self.tbl.setItem(r, 4, QTableWidgetItem(str(it["ItemId"])))
        if enabled_rows and not self.multi_select:
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
        btn_import = QPushButton("库存导入"); btn_import.clicked.connect(self.open_import_dialog); h.addWidget(btn_import)
        btn_wh = QPushButton("仓库管理"); btn_wh.clicked.connect(self.open_wh_manager); h.addWidget(btn_wh)
        layout.addWidget(box)

        filt = QGroupBox("筛选"); fh = QHBoxLayout(filt)
        fh.addWidget(QLabel("物料关键词：")); self.ed_item_filter = QLineEdit(); self.ed_item_filter.setMaximumWidth(220); fh.addWidget(self.ed_item_filter)
        fh.addWidget(QLabel("仓库：")); self.cb_wh = QComboBox(); self.cb_wh.setMinimumWidth(150); fh.addWidget(self.cb_wh)
        fh.addWidget(QLabel("物料类型：")); self.cb_item_type = QComboBox(); self.cb_item_type.setMinimumWidth(120); fh.addWidget(self.cb_item_type)
        fh.addStretch()
        
        # 连接信号，实现自动更新
        self.ed_item_filter.textChanged.connect(self.load_balance)
        self.cb_wh.currentTextChanged.connect(self.load_balance)
        self.cb_item_type.currentTextChanged.connect(self.load_balance)
        layout.addWidget(filt)

        self.tbl_balance = QTableWidget(0, 9)
        self.tbl_balance.setHorizontalHeaderLabels(["物料编码","物料名称","物料规格","类型","单位","库位","在手数量","安全库存","操作"])
        self.tbl_balance.setAlternatingRowColors(True)
        self.tbl_balance.setSelectionBehavior(QAbstractItemView.SelectRows)
        # 优化选择性能，避免exe中的延迟问题
        self.tbl_balance.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_balance.setFocusPolicy(Qt.StrongFocus)
        # 禁用一些可能导致性能问题的功能
        self.tbl_balance.setSortingEnabled(False)
        self.tbl_balance.setDragDropMode(QAbstractItemView.NoDragDrop)
        # 强制立即更新选择状态
        self.tbl_balance.itemSelectionChanged.connect(self._force_selection_update)
        header = self.tbl_balance.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 物料规格
        for c in [3,4,5,6,7,8]:
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
        # 获取当前选择的仓库和物料类型
        cur_wh = self.cb_wh.currentText()
        cur_item_type = self.cb_item_type.currentText()
        
        # 每次加载时都刷新仓库下拉框，确保新增的仓库能显示出来
        self.cb_wh.blockSignals(True)
        self.cb_wh.clear()
        warehouses = WarehouseService.list_warehouses(active_only=True)
        whs = [w["Code"] for w in warehouses] if warehouses else ["默认仓库"]
        self.cb_wh.addItem("全部")
        for w in whs:
            self.cb_wh.addItem(w)
        self.cb_wh.blockSignals(False)
        
        # 如果之前选择的仓库仍然存在，则保持选择；否则默认选择"全部"
        self.cb_wh.blockSignals(True)
        if cur_wh and cur_wh in whs:
            self.cb_wh.setCurrentText(cur_wh)
        else:
            self.cb_wh.setCurrentText("全部")
            cur_wh = "全部"
        self.cb_wh.blockSignals(False)
        
        if self.cb_item_type.count() == 0:
            self.cb_item_type.blockSignals(True)
            self.cb_item_type.addItem("全部")
            self.cb_item_type.addItem("原材料")
            self.cb_item_type.addItem("半成品")
            self.cb_item_type.addItem("成品")
            self.cb_item_type.addItem("包装")
            self.cb_item_type.blockSignals(False)
            # 默认选择"全部"
            self.cb_item_type.setCurrentText("全部")
            cur_item_type = "全部"

        kw = self.ed_item_filter.text().strip()
        
                    # 获取库存余额记录
        if cur_wh == "全部":
            # 全部仓库：显示所有启用的物料
            if kw:
                # 如果有关键词，先搜索物料（模糊搜索：物料编码、物料名称、物料规格、商品品牌）
                items = ItemService.search_items(kw)
                if items:
                    # 为每个搜索到的物料获取库存信息
                    rows = []
                    for item in items:
                        # 过滤禁用状态的物料
                        if item.get("IsActive", 1) != 1:
                            continue
                        
                        # 物料类型筛选
                        if cur_item_type != "全部":
                            item_type_map = {"原材料": "RM", "半成品": "SFG", "成品": "FG", "包装": "PKG"}
                            if item.get("ItemType") != item_type_map.get(cur_item_type):
                                continue
                        
                        balances = InventoryService.get_inventory_balance(item_id=item["ItemId"])
                        if balances:
                            rows.extend(balances)
                        else:
                            # 没有库存记录，显示为0
                            rows.append({
                                "ItemId": item["ItemId"],
                                "ItemCode": item["ItemCode"],
                                "CnName": item.get("CnName", ""),
                                "ItemSpec": item.get("ItemSpec", ""),
                                "ItemType": item.get("ItemType", ""),
                                "Unit": item.get("Unit", ""),
                                "Warehouse": "",
                                "Location": "",
                                "QtyOnHand": 0,
                                "SafetyStock": item.get("SafetyStock", 0)
                            })
                else:
                    rows = []
            else:
                # 没有关键词，显示所有启用的物料
                all_items = ItemService.get_all_items()
                rows = []
                for item in all_items:
                    # 过滤禁用状态的物料
                    if item.get("IsActive", 1) != 1:
                        continue
                    
                    # 物料类型筛选
                    if cur_item_type != "全部":
                        item_type_map = {"原材料": "RM", "半成品": "SFG", "成品": "FG", "包装": "PKG"}
                        if item.get("ItemType") != item_type_map.get(cur_item_type):
                            continue
                    
                    balances = InventoryService.get_inventory_balance(item_id=item["ItemId"])
                    if balances:
                        rows.extend(balances)
                    else:
                        # 没有库存记录，显示为0
                        rows.append({
                            "ItemId": item["ItemId"],
                            "ItemCode": item["ItemCode"],
                            "CnName": item.get("CnName", ""),
                            "ItemSpec": item.get("ItemSpec", ""),
                            "ItemType": item.get("ItemType", ""),
                            "Unit": item.get("Unit", ""),
                            "Warehouse": "",
                            "Location": "",
                            "QtyOnHand": 0,
                            "SafetyStock": item.get("SafetyStock", 0)
                        })
        else:
            # 指定仓库：显示该仓库下的所有启用的物料
            try:
                rows = InventoryService.get_inventory_balance(warehouse=cur_wh)
            except Exception as e:
                print(f"获取仓库 {cur_wh} 的库存余额时出错: {e}")
                rows = []  # 如果出错，显示空列表
            
            # 过滤禁用状态的物料
            filtered_rows = []
            for row in rows:
                # 获取物料的详细信息，检查IsActive状态
                item_info = ItemService.get_item_by_id(row["ItemId"])
                if item_info and item_info.get("IsActive", 1) == 1:
                    filtered_rows.append(row)
            rows = filtered_rows
            
            # 物料类型筛选
            if cur_item_type != "全部":
                item_type_map = {"原材料": "RM", "半成品": "SFG", "成品": "FG", "包装": "PKG"}
                filtered_rows = []
                for row in rows:
                    if row.get("ItemType") == item_type_map.get(cur_item_type):
                        filtered_rows.append(row)
                rows = filtered_rows
            
            # 如果指定了物料关键词，进一步筛选（模糊搜索：物料编码、物料名称、物料规格、商品品牌）
            if kw:
                filtered_rows = []
                for row in rows:
                    if (kw.lower() in row["ItemCode"].lower() or 
                        kw.lower() in (row.get("CnName", "") or "").lower() or
                        kw.lower() in (row.get("ItemSpec", "") or "").lower() or
                        kw.lower() in (row.get("Brand", "") or "").lower()):
                        filtered_rows.append(row)
                rows = filtered_rows
            
            # 确保所有物料都显示正确的库存数量
            for row in rows:
                if row.get("QtyOnHand", 0) == 0:
                    # 如果显示为0，从库存服务获取真实数量
                    real_qty = InventoryService.get_onhand(row["ItemId"], cur_wh, row.get("Location"))
                    row["QtyOnHand"] = real_qty
        
        # 对数据进行排序：低于安全库存的标红最上面，然后优先展示有库存的，最后是库存为0的
        def sort_key(row):
            qty = int(row.get("QtyOnHand") or 0)
            safety_stock = int(row.get("SafetyStock") or 0)
            
            # 第一优先级：低于安全库存的（标红最上面）
            if safety_stock > 0 and qty < safety_stock:
                return (0, row["ItemCode"])  # 最低值，排在最前面
            
            # 第二优先级：有库存的（qty > 0）
            elif qty > 0:
                return (1, row["ItemCode"])
            
            # 第三优先级：库存为0的
            else:
                return (2, row["ItemCode"])
        
        # 按排序键排序
        rows.sort(key=sort_key)
        
        self.tbl_balance.setRowCount(len(rows))
        for r, it in enumerate(rows):
            # 先创建所有表格项
            self.tbl_balance.setItem(r, 0, QTableWidgetItem(it["ItemCode"]))
            self.tbl_balance.setItem(r, 1, QTableWidgetItem(it["CnName"]))
            self.tbl_balance.setItem(r, 2, QTableWidgetItem(it.get("ItemSpec", "") or ""))
            self.tbl_balance.setItem(r, 3, QTableWidgetItem(it["ItemType"]))
            self.tbl_balance.setItem(r, 4, QTableWidgetItem(it.get("Unit","") or ""))
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
        self.ed_daily_search.setPlaceholderText("输入物料编码、名称或规格进行搜索")
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

        self.tbl_daily = QTableWidget(0, 8)  # 默认8列，动态调整
        self.tbl_daily.setHorizontalHeaderLabels(["物料编码","物料名称","物料规格","在手","单位","库位","安全库存","操作"])
        # 优化选择性能，避免exe中的延迟问题
        self.tbl_daily.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_daily.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_daily.setFocusPolicy(Qt.StrongFocus)
        # 禁用一些可能导致性能问题的功能
        self.tbl_daily.setSortingEnabled(False)
        self.tbl_daily.setDragDropMode(QAbstractItemView.NoDragDrop)
        # 强制立即更新选择状态
        self.tbl_daily.itemSelectionChanged.connect(self._force_selection_update)
        header = self.tbl_daily.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in [2,3,4,5,6,7]:
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
        wh = self.cb_daily_wh.currentText()
        
        # 每次加载时都刷新仓库下拉框，确保删除的仓库不会显示
        self.cb_daily_wh.clear()
        warehouses = InventoryService.get_warehouses() or []
        
        # 添加"全部"选项
        self.cb_daily_wh.addItem("全部")
        for w in warehouses:
            self.cb_daily_wh.addItem(w)
        
        # 如果之前选择的仓库仍然存在，则保持选择；否则默认选择"全部"
        if wh and wh in warehouses:
            self.cb_daily_wh.setCurrentText(wh)
        else:
            self.cb_daily_wh.setCurrentText("全部")
            wh = "全部"
        
        # 根据选择的仓库获取物料列表
        if wh == "全部":
            # 全部仓库：显示所有启用的物料
            all_items = ItemService.get_all_items()
            warehouse_items = [item for item in all_items if item.get("IsActive", 1) == 1]
        else:
            # 特定仓库：获取该仓库中确实存在的启用的物料列表
            warehouse_items_raw = WarehouseService.list_items_by_warehouse_name(wh)
            warehouse_items = [item for item in warehouse_items_raw if item.get("IsActive", 1) == 1]
        
        # 为每个物料获取库存信息
        display_rows = []
        for item in warehouse_items:
            if wh == "全部":
                # 全部仓库：汇总所有仓库的库存信息
                all_warehouses = InventoryService.get_warehouses() or []
                total_qty = 0
                has_stock_in_any_warehouse = False
                
                # 计算所有仓库的总库存
                for warehouse in all_warehouses:
                    balance_info = InventoryService.get_inventory_balance(item_id=item["ItemId"], warehouse=warehouse)
                    if balance_info:
                        has_stock_in_any_warehouse = True
                        for balance in balance_info:
                            total_qty += balance.get("QtyOnHand", 0)
                    else:
                        real_qty = InventoryService.get_onhand(item["ItemId"], warehouse, None)
                        if real_qty > 0:
                            has_stock_in_any_warehouse = True
                        total_qty += real_qty
                
                # 显示汇总后的记录
                display_rows.append({
                    "ItemId": item["ItemId"],
                    "ItemCode": item["ItemCode"],
                    "CnName": item.get("CnName", ""),
                    "ItemSpec": item.get("ItemSpec", ""),
                    "ItemType": item.get("ItemType", ""),
                    "Unit": item.get("Unit", ""),
                    "Warehouse": "全部",  # 标记为全部仓库
                    "Location": "",
                    "QtyOnHand": total_qty,
                    "SafetyStock": item.get("SafetyStock", 0)
                })
                
                # 如果物料在所有仓库中都没有库存，也要显示一条记录
                if not has_stock_in_any_warehouse and not all_warehouses:
                    display_rows.append({
                        "ItemId": item["ItemId"],
                        "ItemCode": item["ItemCode"],
                        "CnName": item.get("CnName", ""),
                        "ItemSpec": item.get("ItemSpec", ""),
                        "ItemType": item.get("ItemType", ""),
                        "Unit": item.get("Unit", ""),
                        "Warehouse": "",
                        "Location": "",
                        "QtyOnHand": 0,
                        "SafetyStock": item.get("SafetyStock", 0)
                    })
            else:
                # 特定仓库：获取该仓库的库存信息
                balance_info = InventoryService.get_inventory_balance(item_id=item["ItemId"], warehouse=wh)
                
                if balance_info:
                    # 有库存余额记录
                    for balance in balance_info:
                        display_rows.append({
                            "ItemId": item["ItemId"],
                            "ItemCode": item["ItemCode"],
                            "CnName": item.get("CnName", ""),
                            "ItemSpec": item.get("ItemSpec", ""),
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
                        "ItemSpec": item.get("ItemSpec", ""),
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
        # 如果选择"全部"仓库，需要用户选择具体仓库
        if self.cb_daily_wh.currentText() == "全部":
            warehouses = InventoryService.get_warehouses() or []
            if not warehouses:
                QMessageBox.warning(self, "无可用仓库", "系统中没有可用的仓库，请先创建仓库。")
                return
            
            # 让用户选择仓库
            warehouse, ok = QInputDialog.getItem(
                self, "选择仓库", "请选择要入库的仓库：", warehouses, 0, False
            )
            if not ok:
                return
            wh = warehouse
        else:
            wh = self.cb_daily_wh.currentText()
        
        # 检查物料是否已关联到仓库，如果没有则自动关联
        warehouse_items = WarehouseService.list_items_by_warehouse_name(wh)
        item_exists_in_warehouse = any(item["ItemId"] == rec["ItemId"] for item in warehouse_items)
        
        if not item_exists_in_warehouse:
            # 自动关联物料到仓库
            success = WarehouseService.add_item_by_warehouse_name(wh, rec["ItemId"])
            if success:
                print(f"已自动将物料 {rec['ItemCode']} 关联到仓库 {wh}")
            else:
                QMessageBox.warning(self, "关联失败", f"无法将物料 {rec['ItemCode']} 关联到仓库 {wh}，请检查仓库是否存在。")
                return
        
        d = QtyPriceDialog(self, title=f"入库：{rec['ItemCode']}")
        if d.exec()!=QDialog.Accepted: return
        values = d.get_values()
        if values[0] is None:  # 数据验证失败
            return
        qty, price, loc, rm, _ = values  # 忽略安全库存
        if qty<=0: 
            QMessageBox.warning(self, "数据错误", "入库数量必须大于0")
            return
        InventoryService.receive_inventory(rec["ItemId"], qty, warehouse=wh,
            unit_cost=(price or None), location=(loc or None), remark=(rm or "行内入库"))
        self.daily_load_list()

    def row_out(self, rec):
        # 如果选择"全部"仓库，需要用户选择具体仓库
        if self.cb_daily_wh.currentText() == "全部":
            warehouses = InventoryService.get_warehouses() or []
            if not warehouses:
                QMessageBox.warning(self, "无可用仓库", "系统中没有可用的仓库，请先创建仓库。")
                return
            
            # 让用户选择仓库
            warehouse, ok = QInputDialog.getItem(
                self, "选择仓库", "请选择要出库的仓库：", warehouses, 0, False
            )
            if not ok:
                return
            wh = warehouse
        else:
            wh = self.cb_daily_wh.currentText()
        
        # 检查物料是否已关联到仓库，如果没有则自动关联
        warehouse_items = WarehouseService.list_items_by_warehouse_name(wh)
        item_exists_in_warehouse = any(item["ItemId"] == rec["ItemId"] for item in warehouse_items)
        
        if not item_exists_in_warehouse:
            # 自动关联物料到仓库
            success = WarehouseService.add_item_by_warehouse_name(wh, rec["ItemId"])
            if success:
                print(f"已自动将物料 {rec['ItemCode']} 关联到仓库 {wh}")
            else:
                QMessageBox.warning(self, "关联失败", f"无法将物料 {rec['ItemCode']} 关联到仓库 {wh}，请检查仓库是否存在。")
                return
        
        # 检查当前库存
        current_stock = InventoryService.get_onhand(rec["ItemId"], wh, rec.get("Location"))
        
        d = QtyPriceDialog(self, title=f"出库：{rec['ItemCode']}", default_price=0)
        if d.exec()!=QDialog.Accepted: return
        values = d.get_values()
        if values[0] is None:  # 数据验证失败
            return
        qty, _, loc, rm, _ = values  # 忽略安全库存
        if qty<=0: 
            QMessageBox.warning(self, "数据错误", "出库数量必须大于0")
            return
        
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
        # 如果选择"全部"仓库，需要用户选择具体仓库
        if self.cb_daily_wh.currentText() == "全部":
            warehouses = InventoryService.get_warehouses() or []
            if not warehouses:
                QMessageBox.warning(self, "无可用仓库", "系统中没有可用的仓库，请先创建仓库。")
                return
            
            # 让用户选择仓库
            warehouse, ok = QInputDialog.getItem(
                self, "选择仓库", "请选择要编辑的仓库：", warehouses, 0, False
            )
            if not ok:
                return
            wh = warehouse
        else:
            wh = self.cb_daily_wh.currentText()
        
        # 检查物料是否已关联到仓库，如果没有则自动关联
        warehouse_items = WarehouseService.list_items_by_warehouse_name(wh)
        item_exists_in_warehouse = any(item["ItemId"] == rec["ItemId"] for item in warehouse_items)
        
        if not item_exists_in_warehouse:
            # 自动关联物料到仓库
            success = WarehouseService.add_item_by_warehouse_name(wh, rec["ItemId"])
            if success:
                print(f"已自动将物料 {rec['ItemCode']} 关联到仓库 {wh}")
            else:
                QMessageBox.warning(self, "关联失败", f"无法将物料 {rec['ItemCode']} 关联到仓库 {wh}，请检查仓库是否存在。")
                return
        
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
        values = d.get_values()
        if values[0] is None:  # 数据验证失败
            return
        target, _, loc, rm, new_safety_stock = values
        
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
        # 如果选择"全部"仓库，需要用户选择具体仓库
        if self.cb_daily_wh.currentText() == "全部":
            warehouses = InventoryService.get_warehouses() or []
            if not warehouses:
                QMessageBox.warning(self, "无可用仓库", "系统中没有可用的仓库，请先创建仓库。")
                return
            
            # 让用户选择仓库
            warehouse, ok = QInputDialog.getItem(
                self, "选择仓库", "请选择要删除的仓库：", warehouses, 0, False
            )
            if not ok:
                return
            wh = warehouse
        else:
            wh = self.cb_daily_wh.currentText()
        
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
                # 再次确认库存数量（防止并发修改）
                final_stock = InventoryService.get_onhand(rec["ItemId"], wh, rec.get("Location"))
                if final_stock > 0:
                    InventoryService.set_onhand(
                        rec["ItemId"], 
                        warehouse=wh, 
                        target_qty=0,
                        location=rec.get("Location"),
                        remark_prefix="删除物料前清零库存"
                    )
                    print(f"已清零物料 {rec['ItemCode']} 的库存: {final_stock}")
            
            # 从仓库中删除物料
            WarehouseService.remove_item_from_warehouse(rec["ItemId"], wh)
            
            QMessageBox.information(self, "删除成功", f"物料 '{rec['ItemCode']}' 已从仓库 '{wh}' 中删除")
            
            # 立即刷新页面，确保物料从列表中消失
            self.daily_load_list()
            
        except Exception as e:
            QMessageBox.warning(self, "删除失败", f"删除物料时发生错误：{e}")
            print(f"删除物料详细错误: {e}")

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
                values = d2.get_values()
                if values[0] is None:  # 数据验证失败
                    return
                qty, price, loc, rm, _ = values  # 忽略安全库存
                if qty==0: 
                    QMessageBox.warning(self, "数据错误", "登记数量不能为0")
                    return
                
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
                           search_text in row["CnName"].lower() or
                           search_text in row.get("ItemSpec", "").lower()]
        
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
        # 检查是否选择"全部"仓库
        is_all_warehouses = self.cb_daily_wh.currentText() == "全部"
        
        # 统一使用8列，不显示仓库列
        self.tbl_daily.setColumnCount(8)
        self.tbl_daily.setHorizontalHeaderLabels(["物料编码","物料名称","物料规格","在手","单位","库位","安全库存","操作"])
        
        # 完全重置表格，避免任何残留内容影响显示
        self.tbl_daily.clearContents()
        # 确保表格完全清空，但不清除列标题
        for row in range(self.tbl_daily.rowCount()):
            for col in range(self.tbl_daily.columnCount()):
                self.tbl_daily.takeItem(row, col)
                self.tbl_daily.removeCellWidget(row, col)
        
        # 重新设置列宽模式
        header = self.tbl_daily.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 物料编码
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 物料名称
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 物料规格
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 在手
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 单位
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 库位
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 安全库存
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # 操作列固定宽度
        self.tbl_daily.setColumnWidth(7, 200)  # 设置操作列固定宽度
        
        # 对数据进行排序：低于安全库存的标红最上面，然后优先展示有库存的，最后是库存为0的
        def sort_key(row):
            qty = int(row.get("QtyOnHand") or 0)
            safety_stock = int(row.get("SafetyStock") or 0)
            
            # 第一优先级：低于安全库存的（标红最上面）
            if safety_stock > 0 and qty < safety_stock:
                return (0, row["ItemCode"])  # 最低值，排在最前面
            
            # 第二优先级：有库存的（qty > 0）
            elif qty > 0:
                return (1, row["ItemCode"])
            
            # 第三优先级：库存为0的
            else:
                return (2, row["ItemCode"])
        
        # 按排序键排序
        rows.sort(key=sort_key)
        
        self.tbl_daily.setRowCount(len(rows))
        for r, row_data in enumerate(rows):
            # 重新创建表格项，并保存ItemId和ItemType数据
            item_code_cell = QTableWidgetItem(row_data["ItemCode"])
            item_code_cell.setData(Qt.UserRole, row_data["ItemId"])  # 存储ItemId
            item_code_cell.setData(Qt.UserRole + 1, row_data["ItemType"])  # 存储ItemType
            self.tbl_daily.setItem(r, 0, item_code_cell)
            
            self.tbl_daily.setItem(r, 1, QTableWidgetItem(row_data["CnName"]))
            self.tbl_daily.setItem(r, 2, QTableWidgetItem(row_data.get("ItemSpec", "")))
            qty = int(row_data["QtyOnHand"] or 0)
            qty_cell = QTableWidgetItem(str(qty))
            self.tbl_daily.setItem(r, 3, qty_cell)
            
            self.tbl_daily.setItem(r, 4, QTableWidgetItem(row_data["Unit"]))
            
            # 统一不显示仓库列
            self.tbl_daily.setItem(r, 5, QTableWidgetItem(row_data["Location"]))
            ss = int(row_data["SafetyStock"] or 0)
            ss_cell = QTableWidgetItem(str(ss))
            self.tbl_daily.setItem(r, 6, ss_cell)
            operation_col = 7
            
            # 检查是否低于安全库存
            if ss > 0 and qty < ss:
                # 低于安全库存：整行背景标红
                for col in range(operation_col):  # 不包括操作列
                    item = self.tbl_daily.item(r, col)
                    if item:
                        item.setBackground(QColor(255, 200, 200))  # 浅红色背景
                        if col == 3:  # 在手数量列
                            item.setForeground(QColor(220, 20, 60))     # 红色文字
                        elif col == 6:  # 安全库存列
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
            self.tbl_daily.setCellWidget(r, operation_col, w)

    def daily_clear_filters(self):
        """清除所有筛选条件"""
        self.ed_daily_search.clear()
        self.cb_daily_item_type.setCurrentIndex(0)
        # 重新加载完整数据
        self.daily_load_list()





    # ---------- 库存流水 ----------
    def _build_tab_tx(self, w: QWidget):
        layout = QVBoxLayout(w)
        
        # 筛选区域
        filt = QGroupBox("筛选"); h = QHBoxLayout(filt)
        h.addWidget(QLabel("关键词：")); self.ed_tx_kw = QLineEdit(); self.ed_tx_kw.setPlaceholderText("搜索物料编码、名称、规格"); h.addWidget(self.ed_tx_kw)
        h.addWidget(QLabel("仓库：")); self.cb_tx_wh = QComboBox(); h.addWidget(self.cb_tx_wh)
        h.addStretch()
        
        # 连接信号，实现自动更新
        self.ed_tx_kw.textChanged.connect(self.load_tx)
        self.cb_tx_wh.currentTextChanged.connect(self.load_tx)
        
        layout.addWidget(filt)
        
        # 操作按钮区域
        btn_group = QGroupBox("操作"); btn_layout = QHBoxLayout(btn_group)
        btn_refresh = QPushButton("刷新"); btn_refresh.clicked.connect(self.load_tx); btn_layout.addWidget(btn_refresh)
        btn_export = QPushButton("导出流水"); btn_export.clicked.connect(self.export_transactions); btn_layout.addWidget(btn_export)
        btn_clear = QPushButton("清空流水"); btn_clear.clicked.connect(self.clear_transactions); btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        layout.addWidget(btn_group)

        self.tbl_tx = QTableWidget(0, 9)
        self.tbl_tx.setHorizontalHeaderLabels(["日期","类型","仓库","库位","物料编码","物料名称","数量","单价","备注"])
        # 优化选择性能，避免exe中的延迟问题
        self.tbl_tx.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_tx.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_tx.setFocusPolicy(Qt.StrongFocus)
        # 禁用一些可能导致性能问题的功能
        self.tbl_tx.setSortingEnabled(False)
        self.tbl_tx.setDragDropMode(QAbstractItemView.NoDragDrop)
        # 强制立即更新选择状态
        self.tbl_tx.itemSelectionChanged.connect(self._force_selection_update)
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
        # 初始化仓库下拉框（只在第一次加载时）
        if self.cb_tx_wh.count() == 0:
            self.cb_tx_wh.blockSignals(True)
            self.cb_tx_wh.addItem("全部")
            for w in InventoryService.get_warehouses(): 
                self.cb_tx_wh.addItem(w)
            self.cb_tx_wh.blockSignals(False)
            # 默认选择"全部"
            self.cb_tx_wh.setCurrentText("全部")
        
        kw = self.ed_tx_kw.text().strip()
        wh = None if self.cb_tx_wh.currentText()=="全部" else self.cb_tx_wh.currentText()
        
        # 获取交易记录
        if kw:
            # 如果有关键词，先搜索物料（模糊搜索：物料编码、物料名称、物料规格、商品品牌）
            items = ItemService.search_items(kw)
            if items:
                # 为每个搜索到的启用的物料获取交易记录
                rows = []
                for item in items:
                    # 只处理启用状态的物料
                    if item.get("IsActive", 1) == 1:
                        item_transactions = InventoryService.list_transactions(item_id=item["ItemId"], warehouse=wh)
                        rows.extend(item_transactions)
            else:
                rows = []
        else:
            # 没有关键词，获取所有启用的物料的交易记录
            rows = InventoryService.list_transactions(warehouse=wh, item_types=["RM", "SFG", "FG", "PKG"])
            # 过滤掉禁用物料的交易记录
            filtered_rows = []
            for row in rows:
                item_info = ItemService.get_item_by_id(row.get("ItemId"))
                if item_info and item_info.get("IsActive", 1) == 1:
                    filtered_rows.append(row)
            rows = filtered_rows
        
        # 按日期倒序排列（最新的在前面）
        rows.sort(key=lambda x: x.get("TxDate", ""), reverse=True)
        
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
    
    def export_transactions(self):
        """导出库存流水"""
        path, _ = QFileDialog.getSaveFileName(self, "导出库存流水", "库存流水.csv", "CSV Files (*.csv)")
        if not path:
            return
        
        try:
            import csv
            from app.services.inventory_import_service import InventoryImportService
            
            rows = []
            for r in range(self.tbl_tx.rowCount()):
                # 获取物料类型并转换为中文显示名称
                item_type = self.tbl_tx.item(r, 1).text()
                item_type_display = InventoryImportService.get_item_type_display_name(item_type)
                
                rows.append([
                    self.tbl_tx.item(r, 0).text(),  # 日期
                    item_type_display,  # 类型（中文名称）
                    self.tbl_tx.item(r, 2).text(),  # 仓库
                    self.tbl_tx.item(r, 3).text(),  # 库位
                    self.tbl_tx.item(r, 4).text(),  # 物料编码
                    self.tbl_tx.item(r, 5).text(),  # 物料名称
                    self.tbl_tx.item(r, 6).text(),  # 数量
                    self.tbl_tx.item(r, 7).text(),  # 单价
                    self.tbl_tx.item(r, 8).text(),  # 备注
                ])
            
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["日期", "类型", "仓库", "库位", "物料代码", "物料名称", "数量", "单价", "备注"])
                writer.writerows(rows)
            
            QMessageBox.information(self, "导出完成", f"库存流水已导出到：{path}\n\n注意：导出格式已调整为与导入功能兼容的格式")
            
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出库存流水时发生错误：{str(e)}")
    
    def clear_transactions(self):
        """清空库存流水"""
        # 确认清空操作
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            "确定要清空所有库存流水记录吗？\n\n"
            "此操作将删除所有库存交易记录，且无法恢复！\n"
            "建议在清空前先导出备份。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 执行清空操作
            from app.db import execute
            execute("DELETE FROM InventoryTx")
            
            QMessageBox.information(self, "清空完成", "所有库存流水记录已清空")
            
            # 刷新显示
            self.load_tx()
            
        except Exception as e:
            QMessageBox.critical(self, "清空失败", f"清空库存流水时发生错误：{str(e)}")

    # ---------- 工具 ----------
    def _force_selection_update(self):
        """强制更新选择状态，解决exe中的延迟问题"""
        sender = self.sender()
        if sender:
            # 强制重绘表格
            sender.viewport().update()
            # 强制处理所有待处理的事件（使用QApplication）
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
    
    def reload_all(self):
        # 清理禁用物料从仓库中的关联
        self._cleanup_disabled_items_from_warehouses()
        
        self.load_balance()
        # 确保日常登记页面默认选择"全部"
        if hasattr(self, 'cb_daily_wh'):
            self.cb_daily_wh.setCurrentText("全部")
        self.daily_load_list()
        self.load_tx()
    
    def _cleanup_disabled_items_from_warehouses(self):
        """清理禁用物料从仓库中的关联"""
        try:
            from app.services.warehouse_service import WarehouseService
            
            # 获取所有仓库
            warehouses = WarehouseService.list_warehouses(active_only=True)
            
            for warehouse in warehouses:
                warehouse_id = warehouse["WarehouseId"]
                warehouse_name = warehouse["Code"]
                
                # 获取该仓库中的所有物料
                warehouse_items = WarehouseService.list_items(warehouse_id)
                
                # 检查每个物料是否被禁用
                for item in warehouse_items:
                    item_info = ItemService.get_item_by_id(item["ItemId"])
                    if item_info and item_info.get("IsActive", 1) != 1:
                        # 物料被禁用，先检查是否有库存
                        try:
                            # 获取该物料在该仓库的所有库存记录
                            inventory_records = InventoryService.get_inventory_balance(
                                warehouse=warehouse_name, item_id=item["ItemId"]
                            )
                            
                            # 如果有库存，先清零库存
                            for inv_record in inventory_records:
                                current_qty = inv_record.get("QtyOnHand", 0)
                                if current_qty > 0:
                                    # 执行出库操作清零库存
                                    InventoryService.issue_inventory(
                                        item["ItemId"], 
                                        current_qty, 
                                        warehouse=warehouse_name,
                                        location=inv_record.get("Location"),
                                        remark="物料禁用自动清零"
                                    )
                                    print(f"已清零禁用物料 {item['ItemCode']} 在仓库 {warehouse_name} 的库存: {current_qty}")
                            
                            # 然后从仓库中移除
                            WarehouseService.remove_item(warehouse_id, item["ItemId"])
                            print(f"已从仓库 {warehouse_name} 中移除禁用物料: {item['ItemCode']}")
                            
                        except Exception as e:
                            print(f"处理禁用物料 {item['ItemCode']} 时出错: {e}")
                            
        except Exception as e:
            print(f"清理禁用物料时出错: {e}")

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
        
        # 检查是否有数据可导出
        if self.tbl_balance.rowCount() == 0:
            QMessageBox.warning(self, "无数据", "当前没有库存数据可导出")
            return
            
        import csv
        from app.services.inventory_import_service import InventoryImportService
        
        rows = []
        try:
            for r in range(self.tbl_balance.rowCount()):
                # 检查每一行的数据完整性
                row_data = []
                for c in range(8):  # 8列数据
                    item = self.tbl_balance.item(r, c)
                    if item is None:
                        row_data.append("")
                    else:
                        row_data.append(item.text())
                
                # 获取物料类型并转换为中文显示名称
                item_type = row_data[3]
                item_type_display = InventoryImportService.get_item_type_display_name(item_type)
                
                rows.append([
                    row_data[0],  # 物料编码
                    row_data[1],  # 物料名称
                    row_data[2],  # 物料规格
                    item_type_display,  # 类型（中文名称）
                    row_data[4],  # 单位
                    row_data[5],  # 库位
                    row_data[6],  # 在手数量
                    row_data[7],  # 安全库存
                ])
            
            # 使用与导入功能一致的字段名
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["物料代码","物料名称","规格型号","类型","单位","库位","基本单位数量","安全库存"])
                writer.writerows(rows)
            QMessageBox.information(self, "导出完成", f"已导出到：{path}\n\n注意：导出格式已调整为与导入功能兼容的格式")
            
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出库存余额时发生错误：{e}")
            print(f"导出库存余额详细错误: {e}")

    # ---------- 库存导入对话框入口 ----------
    def open_import_dialog(self):
        """打开库存导入对话框"""
        dlg = InventoryImportDialog(self)
        if dlg.exec() == QDialog.Accepted:
            # 导入完成后刷新数据
            self.reload_all()

    # ---------- 仓库管理入口 ----------
    def open_wh_manager(self):
        dlg = WarehouseManagerDialog(self)
        dlg.exec()
        self.reload_all()

# -------- 库存导入对话框 --------
class InventoryImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("库存导入 - 智能同步更新")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # 导入说明
        info_group = QGroupBox("导入说明")
        info_layout = QVBoxLayout(info_group)
        info_text = QTextEdit()
        info_text.setMaximumHeight(100)
        info_text.setPlainText("""文件格式要求：
1. 第一行为标题行
2. 必须包含以下列：
   - 物料代码：必须包含此列
   - 规格型号（可选）：此列可以有也可以没有
   - 基本单位数量：数量列，重复物资自动累计计算

支持格式：
- Excel文件（.xlsx、.xls）
- CSV文件（.csv，支持UTF-8、GBK、GB2312等编码）

编码处理：
- 系统会自动检测CSV文件编码
- 支持UTF-8、GBK、GB2312、GB18030、Big5等编码
- 如果导入失败，请检查文件编码或重新保存为UTF-8格式

列识别规则：
- 系统会精确匹配列名："物料代码"、"规格型号"、"基本单位数量"
- 即使表格有很多列，也能准确找到需要的列
- 规格型号列是可选的，如果没有则跳过
- 系统会自动检测CSV文件编码，支持多种中文编码格式

智能匹配规则：
- 编码匹配：去掉空格、连接符（-、_、.等）后进行匹配
- 规格匹配：如果有规格列，则规格也必须匹配
- 系统会自动跳过最后一行合计行
- 只处理启用状态的物料，禁用物料会被自动过滤

重复物资处理：
- 自动识别重复的物料代码和规格
- 将相同物料的数量进行累计计算
- 导入后会显示累计计算的详细信息

自动关联功能：
- 导入时会自动将物料关联到选择的仓库
- 无需手动在仓库管理中建立关联关系
- 确保物料在仓库管理中可见

数据安全特性：
- 自动过滤禁用物料，确保数据一致性
- 支持增量更新，只更新有变化的库存数量
- 自动清理禁用物料的仓库关联和库存记录
- 提供详细的导入结果和错误信息

注意事项：
- 禁用的物料不会出现在库存列表中
- 如果物料被禁用，系统会自动从仓库中移除
- 建议导入前先导出现有库存作为备份
- 所有库存变动都会记录详细的操作历史""")
        info_text.setReadOnly(True)
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)
        
        # 导入操作
        import_group = QGroupBox("导入操作")
        import_layout = QVBoxLayout(import_group)
        
        # 第一行：仓库选择
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("目标仓库："))
        self.cb_import_wh = QComboBox()
        self.cb_import_wh.setMinimumWidth(200)
        row1.addWidget(self.cb_import_wh)
        row1.addStretch()
        import_layout.addLayout(row1)
        
        # 第二行：文件选择
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("文件："))
        self.ed_import_file = QLineEdit()
        self.ed_import_file.setPlaceholderText("请选择Excel或CSV文件")
        self.ed_import_file.setReadOnly(True)
        row2.addWidget(self.ed_import_file)
        
        self.btn_import_browse = QPushButton("浏览")
        self.btn_import_browse.clicked.connect(self.browse_file)
        row2.addWidget(self.btn_import_browse)
        row2.addStretch()
        import_layout.addLayout(row2)
        
        # 第三行：导入按钮
        row3 = QHBoxLayout()
        self.btn_import_start = QPushButton("开始导入")
        self.btn_import_start.clicked.connect(self.start_import)
        self.btn_import_start.setEnabled(False)
        row3.addWidget(self.btn_import_start)
        
        self.progress_import = QProgressBar()
        self.progress_import.setVisible(False)
        row3.addWidget(self.progress_import)
        
        row3.addStretch()
        import_layout.addLayout(row3)
        
        layout.addWidget(import_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        
        # 初始化仓库下拉框
        self.init_warehouse_combo()
    
    def init_warehouse_combo(self):
        """初始化仓库下拉框"""
        self.cb_import_wh.clear()
        warehouses = InventoryService.get_warehouses()
        for wh in warehouses:
            self.cb_import_wh.addItem(wh)
        if warehouses:
            self.cb_import_wh.setCurrentText(warehouses[0])
    
    def browse_file(self):
        """浏览选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择文件", 
            "", 
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.ed_import_file.setText(file_path)
            self.btn_import_start.setEnabled(True)
    
    def start_import(self):
        """开始导入"""
        file_path = self.ed_import_file.text().strip()
        if not file_path:
            QMessageBox.warning(self, "提示", "请先选择Excel文件")
            return
        
        warehouse = self.cb_import_wh.currentText()
        if not warehouse:
            QMessageBox.warning(self, "提示", "请选择目标仓库")
            return
        
        # 确认导入
        reply = QMessageBox.question(
            self, 
            "确认导入", 
            f"确定要导入库存数据到仓库 '{warehouse}' 吗？\n"
            f"文件：{file_path}\n\n"
            f"导入将：\n"
            f"• 更新匹配物料的库存数量（只处理启用状态的物料）\n"
            f"• 自动将物料关联到仓库 '{warehouse}'\n"
            f"• 自动过滤禁用物料，确保数据一致性\n"
            f"• 支持重复物资的累计计算\n"
            f"• 记录详细的操作历史",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # 显示进度条
            self.progress_import.setVisible(True)
            self.progress_import.setRange(0, 0)  # 不确定进度
            
            # 执行导入
            success, message, results, duplicate_items = InventoryImportService.import_inventory_from_file(file_path, warehouse)
            
            # 隐藏进度条
            self.progress_import.setVisible(False)
            
            # 显示结果
            if success:
                # 如果有累计计算的物资，显示详细提示
                if duplicate_items:
                    # 构建累计物资的提示信息
                    duplicate_info = "发现重复物资，已进行累计计算：\n\n"
                    for i, item in enumerate(duplicate_items, 1):
                        duplicate_info += f"{i}. 物料编码：{item['item_code']}\n"
                        if item['item_spec']:
                            duplicate_info += f"   规格型号：{item['item_spec']}\n"
                        duplicate_info += f"   涉及行数：{len(item['rows'])}行\n"
                        duplicate_info += f"   各行数量：{', '.join(map(str, item['individual_qtys']))}\n"
                        duplicate_info += f"   累计总数：{item['total_qty']}\n\n"
                    
                    # 显示累计信息对话框
                    QMessageBox.information(self, "累计计算信息", duplicate_info)
                
                QMessageBox.information(self, "导入完成", message)
                
                # 显示详细结果对话框
                if results:
                    dlg = ImportResultDialog(self, results)
                    dlg.exec()
                
                # 关闭导入对话框
                self.accept()
            else:
                QMessageBox.critical(self, "导入失败", message)
                
        except Exception as e:
            self.progress_import.setVisible(False)
            QMessageBox.critical(self, "导入错误", f"导入过程中发生错误：{str(e)}")

# -------- 导入结果对话框 --------
class ImportResultDialog(QDialog):
    def __init__(self, parent=None, results=None):
        super().__init__(parent)
        self.setWindowTitle("导入结果")
        self.resize(800, 600)
        self.results = results or []
        
        layout = QVBoxLayout(self)
        
        # 统计信息
        success_count = len([r for r in self.results if r.get("status") == "成功"])
        error_count = len([r for r in self.results if r.get("status") == "失败"])
        
        stats_label = QLabel(f"导入结果：成功 {success_count} 条，失败 {error_count} 条")
        stats_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(stats_label)
        
        # 详细结果表格
        self.result_table = QTableWidget(0, 8)
        self.result_table.setHorizontalHeaderLabels(["物料代码", "规格型号", "数量", "状态", "匹配物料", "消息", "涉及行数", "累计计算"])
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 物料代码
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 规格型号
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 数量
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 匹配物料
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # 消息
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 涉及行数
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 累计计算
        
        layout.addWidget(self.result_table)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_export = QPushButton("导出结果")
        btn_export.clicked.connect(self.export_results)
        btn_layout.addWidget(btn_export)
        
        btn_layout.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
        self.load_results()
    
    def load_results(self):
        """加载导入结果到表格"""
        self.result_table.setRowCount(len(self.results))
        
        for r, result in enumerate(self.results):
            # 物料代码
            self.result_table.setItem(r, 0, QTableWidgetItem(str(result.get("item_code", ""))))
            
            # 规格型号
            self.result_table.setItem(r, 1, QTableWidgetItem(str(result.get("item_spec", ""))))
            
            # 数量
            self.result_table.setItem(r, 2, QTableWidgetItem(str(result.get("qty", ""))))
            
            # 状态
            status_item = QTableWidgetItem(result.get("status", ""))
            if result.get("status") == "成功":
                status_item.setBackground(QColor(200, 255, 200))  # 绿色背景
            else:
                status_item.setBackground(QColor(255, 200, 200))  # 红色背景
            self.result_table.setItem(r, 3, status_item)
            
            # 匹配物料
            matched_item = QTableWidgetItem(result.get("matched_item", ""))
            self.result_table.setItem(r, 4, matched_item)
            
            # 消息
            self.result_table.setItem(r, 5, QTableWidgetItem(result.get("message", "")))
            
            # 涉及行数
            rows = result.get("rows", [])
            rows_text = f"{len(rows)}行" if len(rows) > 1 else "1行"
            self.result_table.setItem(r, 6, QTableWidgetItem(rows_text))
            
            # 累计计算
            is_accumulated = result.get("is_accumulated", False)
            accumulated_text = "是" if is_accumulated else "否"
            accumulated_item = QTableWidgetItem(accumulated_text)
            if is_accumulated:
                accumulated_item.setBackground(QColor(255, 255, 200))  # 黄色背景
            self.result_table.setItem(r, 7, accumulated_item)
    
    def export_results(self):
        """导出导入结果到CSV文件"""
        path, _ = QFileDialog.getSaveFileName(self, "导出导入结果", "导入结果.csv", "CSV Files (*.csv)")
        if not path:
            return
        
        import csv
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["行号", "物料代码", "规格型号", "数量", "状态", "匹配物料", "消息"])
            for result in self.results:
                writer.writerow([
                    result.get("row", ""),
                    result.get("item_code", ""),
                    result.get("item_spec", ""),
                    result.get("qty", ""),
                    result.get("status", ""),
                    result.get("matched_item", ""),
                    result.get("message", "")
                ])
        
        QMessageBox.information(self, "导出完成", f"结果已导出到：{path}")

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
