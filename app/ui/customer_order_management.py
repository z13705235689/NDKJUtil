#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import defaultdict
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta, date as _date

from PySide6.QtCore import Qt, QDate, QThread, Signal, QRect
from PySide6.QtGui import QFont, QColor, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QFrame, QLineEdit, QComboBox, QAbstractItemView,
    QMessageBox, QTabWidget, QHeaderView, QDateEdit, QFileDialog,
    QProgressBar, QTextBrowser, QDialog, QAbstractScrollArea, QSizePolicy
)

from app.services.customer_order_service import CustomerOrderService

# Excel导出相关导入
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# -------------------- 小工具 --------------------
def _safe_parse_date(s):
    if not s:
        return None
    if isinstance(s, _date):
        return s
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%y", "%m/%d/%Y"):
        try:
            d = datetime.strptime(str(s), fmt).date()
            if d.year < 2000:
                d = d.replace(year=d.year + 2000)
            return d
        except Exception:
            pass
    return None

def _cw(d: _date) -> int:
    return d.isocalendar()[1]

def _norm_int(v, default=0):
    try:
        if v in (None, ""):
            return default
        return int(float(v))
    except Exception:
        return default

def _get(line: dict, *names, default=None):
    for n in names:
        if n in line and line[n] not in (None, ""):
            return line[n]
    return default

def _week_start(d: _date) -> _date:
    return d - timedelta(days=d.weekday())

def _build_week_cols(min_d: _date, max_d: _date) -> Tuple[List[Tuple[str, _date|int]], Dict[int, List[_date]], List[int]]:
    """根据起止日期构造连续周列以及每年的周分组，并在每年后追加“合计”列。"""
    if not (min_d and max_d):
        return [], {}, []
    start = _week_start(min_d)
    end   = _week_start(max_d)
    weeks = []
    cur = start
    while cur <= end:
        weeks.append(cur)
        cur += timedelta(days=7)
    by_year = defaultdict(list)
    for w in weeks:
        by_year[w.isocalendar()[0]].append(w)
    years = sorted(by_year.keys())
    colspec: List[Tuple[str, _date|int]] = []
    for y in years:
        for w in by_year[y]:
            colspec.append(("week", w))
        colspec.append(("sum", y))
    return colspec, by_year, years


# -------------------- 两行表头 --------------------
class TwoRowHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(Qt.AlignCenter)
        self._top_font = QFont(); self._top_font.setBold(True)
        self._bottom_font = QFont()
        h = self.fontMetrics().height()
        self.setFixedHeight(int(h * 2.4))

    def sizeHint(self):
        s = super().sizeHint()
        h = self.fontMetrics().height()
        s.setHeight(int(h * 2.4))
        return s

    def paintSection(self, painter: QPainter, rect: QRect, logicalIndex: int):
        if not rect.isValid():
            return
        super().paintSection(painter, rect, logicalIndex)

        table = self.parent()
        item = table.horizontalHeaderItem(logicalIndex) if table else None
        top = item.text() if item else ""
        bottom = item.data(Qt.UserRole) if (item and item.data(Qt.UserRole) is not None) else ""

        painter.save()
        painter.setPen(QColor("#333333"))
        painter.setFont(self._top_font)
        topRect = QRect(rect.left(), rect.top() + 2, rect.width(), rect.height() // 2)
        painter.drawText(topRect, Qt.AlignCenter, str(top))
        painter.setFont(self._bottom_font)
        bottomRect = QRect(rect.left(), rect.top() + rect.height() // 2 - 2, rect.width(), rect.height() // 2)
        painter.drawText(bottomRect, Qt.AlignCenter, str(bottom))
        painter.restore()


# -------------------- 主界面 --------------------
class CustomerOrderManagement(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_version_list()

    def init_ui(self):
        self.setWindowTitle("客户订单管理")
        self.setMinimumSize(1200, 800)

        main_layout = QVBoxLayout()

        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        import_btn = QPushButton("导入TXT文件")
        import_btn.setStyleSheet("QPushButton{background:#28a745;color:#fff;border:none;padding:8px 16px;border-radius:4px;font-weight:bold;}"
                                 "QPushButton:hover{background:#218838;}")
        import_btn.clicked.connect(self.import_txt_file)
        toolbar_layout.addWidget(import_btn)

        version_btn = QPushButton("版本管理")
        version_btn.setStyleSheet("QPushButton{background:#17a2b8;color:#fff;border:none;padding:8px 16px;border-radius:4px;font-weight:bold;}"
                                  "QPushButton:hover{background:#138496;}")
        version_btn.clicked.connect(self.show_version_management)
        toolbar_layout.addWidget(version_btn)

        toolbar_layout.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet("QPushButton{background:#6c757d;color:#fff;border:none;padding:8px 16px;}"
                                  "QPushButton:hover{background:#5a6268;}")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar_layout.addWidget(refresh_btn)

        main_layout.addLayout(toolbar_layout)

        # 页签
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(
            "QTabWidget::pane{border:1px solid #dee2e6;background:white;}"
            "QTabBar::tab{background:#f8f9fa;border:1px solid #dee2e6;padding:8px 16px;margin-right:2px;}"
            "QTabBar::tab:selected{background:white;border-bottom:2px solid #007bff;}"
        )

        self.create_kanban_tab()
        self.create_order_details_tab()
        self.create_import_history_tab()

        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

    # ---------- 看板页 ----------
    def create_kanban_tab(self):
        kanban_widget = QWidget()
        kanban_layout = QVBoxLayout()

        control_panel = QFrame()
        control_panel.setFrameStyle(QFrame.StyledPanel)
        control_panel.setStyleSheet("QFrame{background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;}")
        control_layout = QVBoxLayout()

        # 版本选择 + 日期范围
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("订单版本:"))
        self.version_combo = QComboBox()
        self.version_combo.addItem("全部版本汇总")
        self.version_combo.currentTextChanged.connect(self.on_version_changed)
        version_layout.addWidget(self.version_combo)

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("日期范围:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(self.start_date_edit)

        date_layout.addWidget(QLabel("至"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate().addDays(30))
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(self.end_date_edit)

        apply_btn = QPushButton("应用筛选")
        apply_btn.setStyleSheet("QPushButton{background:#007bff;color:#fff;border:none;padding:6px 12px;border-radius:4px;}"
                                "QPushButton:hover{background:#0069d9;}")
        apply_btn.clicked.connect(self.load_kanban_data)

        export_btn = QPushButton("导出Excel")
        export_btn.setStyleSheet("QPushButton{background:#28a745;color:#fff;border:none;padding:6px 12px;border-radius:4px;}"
                                "QPushButton:hover{background:#218838;}")
        export_btn.clicked.connect(self.export_kanban_to_excel)

        version_layout.addLayout(date_layout)
        version_layout.addWidget(apply_btn)
        version_layout.addWidget(export_btn)
        version_layout.addStretch()
        control_layout.addLayout(version_layout)

        # 订单类型过滤
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("订单类型:"))
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["全部", "F(正式)", "P(预测)"])
        self.order_type_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.order_type_combo)
        filter_layout.addStretch()
        control_layout.addLayout(filter_layout)

        control_panel.setLayout(control_layout)
        kanban_layout.addWidget(control_panel)

        # 看板表格
        self.kanban_table = QTableWidget()
        self.kanban_table.setAlternatingRowColors(True)
        self.kanban_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.kanban_table.setHorizontalHeader(TwoRowHeader(Qt.Horizontal, self.kanban_table))
        hdr = self.kanban_table.horizontalHeader()
        hdr.setFixedHeight(int(self.fontMetrics().height()*2.4))
        try:
            hdr.repaint()
            hdr.updateGeometry()
        except Exception:
            pass
        try:
            policy = QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow
        except AttributeError:
            policy = getattr(QAbstractScrollArea, "AdjustToContentsOnFirstShow", QAbstractScrollArea.AdjustToContents)
        self.kanban_table.setSizeAdjustPolicy(policy)
        self.kanban_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        kanban_layout.addWidget(self.kanban_table)
        kanban_widget.setLayout(kanban_layout)
        self.tab_widget.addTab(kanban_widget, "看板视图")

    # ------- 数据加载 -------
    def on_version_changed(self, version_text: str):
        try:
            if version_text == "全部版本汇总":
                self.load_kanban_data()
                return
            import re
            m = re.search(r'^(\d+) - ', version_text)
            if not m:
                self.load_kanban_data()
                return
            version_id = int(m.group(1))
            data = CustomerOrderService.get_order_lines_by_import_version(version_id)
            all_dates = []
            for ln in data or []:
                d = _safe_parse_date(_get(ln, "DeliveryDate", "due_date"))
                if d:
                    all_dates.append(d)
            if all_dates:
                all_dates.sort()
                self.start_date_edit.setDate(QDate(all_dates[0].year, all_dates[0].month, all_dates[0].day))
                self.end_date_edit.setDate(QDate(all_dates[-1].year, all_dates[-1].month, all_dates[-1].day))
            self.load_kanban_data()
        except Exception as e:
            print(f"版本切换失败: {e}")

    def on_filter_changed(self):
        self.load_kanban_data()

    def load_kanban_data(self):
        try:
            version_text = self.version_combo.currentText()
            sd = self.start_date_edit.date().toString("yyyy-MM-dd")
            ed = self.end_date_edit.date().toString("yyyy-MM-dd")
            if version_text != "全部版本汇总":
                import re
                m = re.search(r'^(\d+) - ', version_text)
                version_id = int(m.group(1)) if m else None
            else:
                version_id = None

            if version_id:
                data = CustomerOrderService.get_order_lines_by_import_version(version_id)
                self.display_kanban_data_by_version(data, sd, ed, self.order_type_combo.currentText())
            else:
                # 汇总口径：把 Firm/Predict 拆成伪明细
                rows = CustomerOrderService.get_ndlutil_kanban_data(start_date=sd, end_date=ed)
                expanded = []
                for r in rows or []:
                    common = {
                        "SupplierCode": r.get("SupplierCode",""),
                        "SupplierName": r.get("SupplierName",""),
                        "ItemNumber":   r.get("ItemNumber",""),
                        "ItemDescription": r.get("ItemDescription",""),
                        "DeliveryDate": r.get("DeliveryDate",""),
                        "CalendarWeek": r.get("CalendarWeek",""),
                        "ReleaseDate":  r.get("ReleaseDate",""),
                        "ReleaseId":    r.get("ReleaseId",""),
                        "PurchaseOrder":r.get("PurchaseOrder",""),
                        "ReceiptQuantity": 0,
                        "CumReceived":  0,
                    }
                    f = _norm_int(r.get("FirmQty"), 0)
                    p = _norm_int(r.get("ForecastQty"), 0)
                    if f:
                        e = dict(common); e["OrderType"]="F"; e["RequiredQty"]=f; expanded.append(e)
                    if p:
                        e = dict(common); e["OrderType"]="P"; e["RequiredQty"]=p; expanded.append(e)
                self.display_kanban_data_by_version(expanded, sd, ed, self.order_type_combo.currentText())
        except Exception as e:
            print(f"加载看板数据失败: {e}")

    # ------- 渲染（行集合固定，列按范围变动）-------
    def display_kanban_data_by_version(self, data: list, start_date: str, end_date: str, order_type: str):
        """
        行集合 = 该版本中检索到的所有 (Supplier, PN)，固定展示；
        列（CW/年合计）随页面日期范围变化；
        数量来自【按日期范围 + 类型过滤】后的数据进行周聚合。
        """
        sd = _safe_parse_date(start_date)
        ed = _safe_parse_date(end_date)
        if sd and ed and sd > ed:
            sd, ed = ed, sd
        page_typ = (order_type or "").upper()

        # 1) 构造列
        colspec, by_year, years = _build_week_cols(sd, ed)

        # 2) 行集合：整版数据收集 (Supplier, PN)
        groups_all = defaultdict(lambda: {"release": {}})
        for ln in (data or []):
            sup = _get(ln, "SupplierCode", "supplier_code", "Supplier", "supplier", "") or ""
            pn = _get(ln, "ItemNumber", "item_number", "Item", "item", "") or ""
            key = (sup, pn)
            ri = groups_all[key]["release"]

            def _set_if_val(k, v, cast_int=False):
                if v in (None, ""): return
                if cast_int: v = _norm_int(v, 0)
                if not ri.get(k): ri[k] = v

            _set_if_val("release_date", _get(ln, "ReleaseDate", "release_date", "release_date_text"))
            _set_if_val("release_id", _get(ln, "ReleaseId", "release_id"))
            _set_if_val("purchase_order", _get(ln, "PurchaseOrder", "OrderNumber", "purchase_order", "order_number"))
            _set_if_val("receipt_qty", _get(ln, "ReceiptQuantity", "receipt_qty"), cast_int=True)
            _set_if_val("cum_received", _get(ln, "CumReceived", "cum_received"), cast_int=True)

        # 3) 过滤后的数据
        lines_filtered = []
        for ln in (data or []):
            d = _safe_parse_date(_get(ln, "DeliveryDate", "due_date"))
            if not d: continue
            if sd and d < sd: continue
            if ed and d > ed: continue
            typ = (_get(ln, "OrderType", "order_type", "FP", default="") or "").upper()
            if page_typ in ("F(正式)", "F") and typ != "F": continue
            if page_typ in ("P(预测)", "P") and typ != "P": continue
            ln = dict(ln)
            ln["__week__"] = _week_start(d)
            ln["__fp__"] = "F" if typ == "F" else "P"
            lines_filtered.append(ln)

        week_qty = defaultdict(lambda: defaultdict(int))
        fp_map = {}
        for ln in lines_filtered:
            sup = _get(ln, "SupplierCode", "supplier_code", "Supplier", "supplier", "")
            pn = _get(ln, "ItemNumber", "item_number", "Item", "item", "")
            wk = ln["__week__"]
            q = _norm_int(_get(ln, "RequiredQty", "req_qty", default=0), 0)
            week_qty[(sup, pn)][wk] += q
            cur = fp_map.get((sup, pn, wk))
            if (cur is None) or (cur == "P" and ln["__fp__"] == "F"):
                fp_map[(sup, pn, wk)] = ln["__fp__"]

        # 4) 表头
        fixed_headers = [
            "Release Date", "Release ID", "PN", "Des", "Project", "Item",
            "Purchase Order", "Receipt Quantity", "Cum Received"
        ]
        headers_count = len(fixed_headers) + len(colspec) + 1
        self.kanban_table.clear()
        self.kanban_table.setColumnCount(headers_count)

        for i, title in enumerate(fixed_headers):
            item = QTableWidgetItem(title)
            self.kanban_table.setHorizontalHeaderItem(i, item)

        base_col = len(fixed_headers)
        for i, (kind, val) in enumerate(colspec):
            if kind == "week":
                cw = f"CW{val.isocalendar()[1]:02d}"
                it = QTableWidgetItem(cw)
                it.setData(Qt.UserRole, val.strftime("%Y/%m/%d"))
            else:
                it = QTableWidgetItem(f"{val}合计")
            self.kanban_table.setHorizontalHeaderItem(base_col + i, it)
        self.kanban_table.setHorizontalHeaderItem(headers_count - 1, QTableWidgetItem("Total"))

        # 5) 行集合（按 PN 升序，再 Supplier 升序）
        keys_all = sorted(groups_all.keys(), key=lambda k: (k[1], k[0]))
        data_rows = len(keys_all)
        self.kanban_table.setRowCount(data_rows + 1)  # +1 行留给 TOTAL

        def project_name(pn: str) -> str:
            base = (pn or "")[:-1]
            mp = {"R001H368": "Passat rear double", "R001H369": "Passat rear single",
                  "R001P320": "Tiguan L rear double", "R001P313": "Tiguan L rear single",
                  "R001J139": "A5L rear double", "R001J140": "A5L rear single",
                  "R001J141": "Lavida rear double", "R001J142": "Lavida rear single"}
            return mp.get(base, "UNKNOWN")

        # 6) 填充数据行
        for row_idx, (sup, pn) in enumerate(keys_all):
            ri = groups_all[(sup, pn)]["release"]
            rd_obj = _safe_parse_date(ri.get("release_date"))
            rd_txt = rd_obj.strftime("%Y/%m/%d") if rd_obj else (ri.get("release_date") or "")

            fixed_vals = [
                rd_txt, str(ri.get("release_id", "") or ""), pn,
                "PEMM ASSY", project_name(pn), "Gross Reqs",
                sup, str(_norm_int(ri.get("receipt_qty"), 0)),
                str(_norm_int(ri.get("cum_received"), 0)),
            ]
            for c, v in enumerate(fixed_vals):
                self.kanban_table.setItem(row_idx, c, QTableWidgetItem(v))

            row_total = 0
            cursor_col = base_col
            for kind, val in colspec:
                if kind == "week":
                    qty = _norm_int(week_qty[(sup, pn)].get(val, 0), 0)
                    row_total += qty
                    cell = QTableWidgetItem(str(qty))
                    fp = fp_map.get((sup, pn, val))
                    if qty > 0 and fp:
                        cell.setBackground(QColor("#C6E0B4") if fp == "F" else QColor("#FFF2CC"))
                    self.kanban_table.setItem(row_idx, cursor_col, cell)
                else:
                    s = sum(_norm_int(week_qty[(sup, pn)].get(w, 0), 0) for w in by_year[val])
                    cell = QTableWidgetItem(str(s))
                    f = cell.font();
                    f.setBold(True);
                    cell.setFont(f)
                    cell.setBackground(QColor("#DDEBF7"))
                    self.kanban_table.setItem(row_idx, cursor_col, cell)
                cursor_col += 1

            self.kanban_table.setItem(row_idx, headers_count - 1, QTableWidgetItem(str(row_total)))

        # 7) TOTAL 行
        total_row = data_rows
        self.kanban_table.setItem(total_row, 0, QTableWidgetItem("TOTAL"))
        # 只从 CW 开始统计（前9列不算）
        for col in range(base_col, headers_count):
            s = 0
            for r in range(0, data_rows):
                it = self.kanban_table.item(r, col)
                try:
                    s += int(float(it.text())) if it and it.text().strip() else 0
                except:
                    pass
            item = QTableWidgetItem(str(s))
            f = item.font();
            f.setBold(True);
            item.setFont(f)
            self.kanban_table.setItem(total_row, col, item)

        # 列宽
        hdr = self.kanban_table.horizontalHeader()
        for i in range(9):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        for c in range(9, headers_count):
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)
            self.kanban_table.setColumnWidth(c, 64)

        self.kanban_table.resizeRowsToContents()
        self.apply_kanban_styling()

    # ====== 样式：通用 ======
    def apply_kanban_styling(self):
        # 表头加粗
        hdr = self.kanban_table.horizontalHeader()
        for c in range(self.kanban_table.columnCount()):
            it = self.kanban_table.horizontalHeaderItem(c)
            if it:
                f = QFont(it.font())
                f.setBold(True)
                it.setFont(f)
        # 交替底色
        self.kanban_table.setAlternatingRowColors(True)
        self.kanban_table.setStyleSheet(
            "QTableWidget{gridline-color:#dee2e6;}"
            "QTableWidget::item{padding:2px;}"
            "QTableWidget::item:selected{background:#cfe2ff;}"
        )
        # TOTAL 行仅加粗
        r = self.kanban_table.rowCount() - 1
        if r >= 0:
            for c in range(self.kanban_table.columnCount()):
                it = self.kanban_table.item(r, c)
                if not it:
                    continue
                f = it.font(); f.setBold(True); it.setFont(f)
                it.setBackground(Qt.transparent)  # 保持透明

    # ===================== 订单明细页 =====================
    def create_order_details_tab(self):
        details_widget = QWidget()
        layout = QVBoxLayout(details_widget)

        # 过滤区
        filter_panel = QFrame()
        filter_panel.setFrameStyle(QFrame.StyledPanel)
        filter_panel.setStyleSheet("QFrame{background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;}")
        f_layout = QHBoxLayout(filter_panel)

        f_layout.addWidget(QLabel("版本:"))
        self.detail_version_combo = QComboBox()
        self.detail_version_combo.addItem("全部版本汇总")
        self.detail_version_combo.currentTextChanged.connect(lambda _: self.load_order_details())
        f_layout.addWidget(self.detail_version_combo)

        f_layout.addSpacing(12)
        f_layout.addWidget(QLabel("日期范围:"))
        self.detail_start_date_edit = QDateEdit()
        self.detail_start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.detail_start_date_edit.setDate(QDate.currentDate().addDays(-30))
        f_layout.addWidget(self.detail_start_date_edit)

        f_layout.addWidget(QLabel("至"))
        self.detail_end_date_edit = QDateEdit()
        self.detail_end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.detail_end_date_edit.setDate(QDate.currentDate().addDays(30))
        f_layout.addWidget(self.detail_end_date_edit)

        apply_btn = QPushButton("应用筛选")
        apply_btn.clicked.connect(self.load_order_details)
        f_layout.addWidget(apply_btn)

        f_layout.addStretch()

        export_btn = QPushButton("导出明细CSV")
        export_btn.clicked.connect(self.export_order_data)
        f_layout.addWidget(export_btn)

        layout.addWidget(filter_panel)

        # 明细表
        self.details_table = QTableWidget()
        self.details_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.details_table.setAlternatingRowColors(True)
        hdr = self.details_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.details_table)

        self.tab_widget.addTab(details_widget, "订单明细")

    def load_order_details(self):
        try:
            ver_text = self.detail_version_combo.currentText()
            sd = self.detail_start_date_edit.date().toString("yyyy-MM-dd")
            ed = self.detail_end_date_edit.date().toString("yyyy-MM-dd")

            # 表头
            headers = [
                "Release Date","Release ID","Supplier","PN","ItemDesc",
                "DeliveryDate","CalendarWeek","类型","数量",
                "Purchase Order","Receipt Quantity","Cum Received"
            ]
            self.details_table.clear()
            self.details_table.setRowCount(0)
            self.details_table.setColumnCount(len(headers))
            for i, h in enumerate(headers):
                self.details_table.setHorizontalHeaderItem(i, QTableWidgetItem(h))

            # 数据
            if ver_text == "全部版本汇总":
                rows = CustomerOrderService.get_ndlutil_kanban_data(start_date=sd, end_date=ed)
                expanded = []
                for r in rows or []:
                    common = {
                        "ReleaseDate": r.get("ReleaseDate",""),
                        "ReleaseId": r.get("ReleaseId",""),
                        "SupplierCode": r.get("SupplierCode",""),
                        "ItemNumber": r.get("ItemNumber",""),
                        "ItemDescription": r.get("ItemDescription",""),
                        "DeliveryDate": r.get("DeliveryDate",""),
                        "CalendarWeek": r.get("CalendarWeek",""),
                        "PurchaseOrder": r.get("PurchaseOrder",""),
                        "ReceiptQuantity": 0,
                        "CumReceived": 0,
                    }
                    f = _norm_int(r.get("FirmQty"), 0)
                    p = _norm_int(r.get("ForecastQty"), 0)
                    if f:
                        e = dict(common); e["OrderType"]="F"; e["RequiredQty"]=f; expanded.append(e)
                    if p:
                        e = dict(common); e["OrderType"]="P"; e["RequiredQty"]=p; expanded.append(e)
                data = expanded
            else:
                import re
                m = re.search(r'^(\d+)\s-', ver_text)
                import_id = int(m.group(1)) if m else None
                data = CustomerOrderService.get_order_lines_by_import_version(import_id)

            # 填充
            for r, ln in enumerate(data or []):
                self.details_table.insertRow(r)
                vals = [
                    _get(ln, "ReleaseDate",""),
                    _get(ln, "ReleaseId",""),
                    _get(ln, "SupplierCode",""),
                    _get(ln, "ItemNumber",""),
                    _get(ln, "ItemDescription",""),
                    _get(ln, "DeliveryDate",""),
                    _get(ln, "CalendarWeek",""),
                    _get(ln, "OrderType",""),
                    str(_norm_int(_get(ln, "RequiredQty","req_qty", default=0), 0)),
                    _get(ln, "PurchaseOrder",""),
                    str(_norm_int(_get(ln, "ReceiptQuantity", default=0), 0)),
                    str(_norm_int(_get(ln, "CumReceived", default=0), 0)),
                ]
                for c, v in enumerate(vals):
                    self.details_table.setItem(r, c, QTableWidgetItem(v))

            self.details_table.resizeRowsToContents()
        except Exception as e:
            print(f"加载订单明细失败: {e}")

    def export_order_data(self):
        """把当前明细页数据导出为 CSV（简单直导，满足审阅/备份）"""
        try:
            path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "orders.csv", "CSV Files (*.csv)")
            if not path:
                return
            import csv
            headers = [self.details_table.horizontalHeaderItem(i).text() for i in range(self.details_table.columnCount())]
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                wr = csv.writer(f)
                wr.writerow(headers)
                for r in range(self.details_table.rowCount()):
                    row = []
                    for c in range(self.details_table.columnCount()):
                        it = self.details_table.item(r, c)
                        row.append(it.text() if it else "")
                    wr.writerow(row)
            QMessageBox.information(self, "导出完成", f"已导出到：\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    # ===================== 导入历史页 =====================
    def create_import_history_tab(self):
        history_widget = QWidget()
        layout = QVBoxLayout(history_widget)

        top = QHBoxLayout()
        refresh_btn = QPushButton("刷新历史")
        refresh_btn.clicked.connect(self.load_import_history)
        top.addWidget(refresh_btn)

        delete_btn = QPushButton("删除所选版本")
        delete_btn.clicked.connect(self.delete_selected_import)
        top.addWidget(delete_btn)

        top.addStretch()
        layout.addLayout(top)

        self.history_table = QTableWidget()
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

        self.tab_widget.addTab(history_widget, "导入历史")
        self.load_import_history()

    def load_import_history(self):
        try:
            rows = CustomerOrderService.get_import_history()
            headers = ["ImportId","FileName","ImportDate","OrderCount","LineCount","ImportStatus","ImportedBy"]
            self.history_table.clear()
            self.history_table.setRowCount(0)
            self.history_table.setColumnCount(len(headers))
            for i, h in enumerate(headers):
                self.history_table.setHorizontalHeaderItem(i, QTableWidgetItem(h))
            for r, row in enumerate(rows or []):
                self.history_table.insertRow(r)
                vals = [str(row.get(k,"")) for k in ["ImportId","FileName","ImportDate","OrderCount","LineCount","ImportStatus","ImportedBy"]]
                for c, v in enumerate(vals):
                    self.history_table.setItem(r, c, QTableWidgetItem(v))
            self.history_table.resizeColumnsToContents()

            # 同步两个版本下拉
            self.load_version_list()
        except Exception as e:
            print(f"加载导入历史失败: {e}")

    def delete_selected_import(self):
        r = self.history_table.currentRow()
        if r < 0:
            QMessageBox.information(self, "提示", "请先选中要删除的版本。")
            return
        import_id_item = self.history_table.item(r, 0)
        if not import_id_item:
            return
        import_id = int(import_id_item.text())
        ok = QMessageBox.question(self, "确认删除", f"确定删除版本 {import_id} 及其数据？", QMessageBox.Yes | QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        ok, msg = CustomerOrderService.delete_import(import_id)
        if not ok:
            QMessageBox.warning(self, "删除失败", msg or "未知错误")
            return
        QMessageBox.information(self, "删除成功", f"版本 {import_id} 已删除。")
        self.load_import_history()
        self.refresh_data()

    # ===================== 顶部动作 =====================
    def load_version_list(self):
        """刷新两个版本下拉框"""
        rows = CustomerOrderService.get_import_history()
        items = ["全部版本汇总"]
        for r in rows:
            items.append(f"{r['ImportId']} - {r['FileName']} ({r['ImportDate']})")

        # 看板页下拉
        cur = self.version_combo.currentText() if self.version_combo.count() else None
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        self.version_combo.addItems(items)
        self.version_combo.blockSignals(False)
        if cur and cur in items:
            self.version_combo.setCurrentText(cur)

        # 明细页下拉
        cur2 = self.detail_version_combo.currentText() if self.detail_version_combo.count() else None
        self.detail_version_combo.blockSignals(True)
        self.detail_version_combo.clear()
        self.detail_version_combo.addItems(items)
        self.detail_version_combo.blockSignals(False)
        if cur2 and cur2 in items:
            self.detail_version_combo.setCurrentText(cur2)

    def refresh_data(self):
        """刷新当前页数据"""
        # 先刷新版本列表（可能有新增/删除）
        self.load_version_list()
        # 触发两页数据加载
        self.load_kanban_data()
        self.load_order_details()

    def import_txt_file(self):
        """从 TXT 导入"""
        path, _ = QFileDialog.getOpenFileName(self, "选择客户订单 TXT", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        ok, msg, import_id = CustomerOrderService.import_orders_from_txt(path, import_user="UI")
        if not ok:
            QMessageBox.warning(self, "导入失败", msg or "未知错误")
        else:
            QMessageBox.information(self, "导入成功", msg)
        # 刷新
        self.refresh_data()

    def show_version_management(self):
        dlg = VersionManagementDialog(self)
        dlg.exec()
        # 关闭后刷新
        self.refresh_data()


# ===================== 版本管理对话框 =====================
class VersionManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("版本管理")
        self.resize(800, 480)

        layout = QVBoxLayout(self)

        tip = QLabel("提示：删除将同时清除该版本的头表和明细数据。")
        tip.setStyleSheet("color:#666;")
        layout.addWidget(tip)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        btns = QHBoxLayout()
        delete_btn = QPushButton("删除所选版本")
        delete_btn.clicked.connect(self.delete_selected)
        btns.addWidget(delete_btn)
        btns.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

        self.load()

    def load(self):
        rows = CustomerOrderService.get_import_history()
        headers = ["ImportId","FileName","ImportDate","OrderCount","LineCount","ImportStatus","ImportedBy"]
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(len(headers))
        for i, h in enumerate(headers):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(h))
        for r, row in enumerate(rows or []):
            self.table.insertRow(r)
            vals = [str(row.get(k,"")) for k in ["ImportId","FileName","ImportDate","OrderCount","LineCount","ImportStatus","ImportedBy"]]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(v))
        self.table.resizeColumnsToContents()

    def delete_selected(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.information(self, "提示", "请先选中要删除的版本。")
            return
        import_id_item = self.table.item(r, 0)
        if not import_id_item:
            return
        import_id = int(import_id_item.text())
        ok = QMessageBox.question(self, "确认删除", f"确定删除版本 {import_id} 及其数据？", QMessageBox.Yes | QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        ok, msg = CustomerOrderService.delete_import(import_id)
        if not ok:
            QMessageBox.warning(self, "删除失败", msg or "未知错误")
            return
        QMessageBox.information(self, "删除成功", f"版本 {import_id} 已删除。")
        self.load()
