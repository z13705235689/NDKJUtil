# app/ui/mrp_viewer.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QDateEdit, QLabel, QComboBox, QGroupBox,
    QMessageBox, QHeaderView, QTabWidget, QLineEdit, QCheckBox,
    QFileDialog
)
from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtGui import QFont, QColor, QBrush

from app.services.mrp_service import MRPService
from typing import Optional
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

class MRPCalcThread(QThread):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, start_date: str, end_date: str, import_id: Optional[int] = None, 
                 parent_item_filter: Optional[str] = None, calc_type: str = "child"):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        self.import_id = import_id
        self.parent_item_filter = parent_item_filter
        self.calc_type = calc_type  # "child" 或 "parent"

    def run(self):
        try:
            if self.calc_type == "child":
                # 计算零部件MRP
                data = MRPService.calculate_mrp_kanban(
                    self.start_date, self.end_date, 
                    self.import_id, self.parent_item_filter
                )
            else:
                # 计算成品MRP
                data = MRPService.calculate_parent_mrp_kanban(
                    self.start_date, self.end_date, 
                    self.import_id, self.parent_item_filter
                )
            self.finished.emit(data)
        except Exception as e:
            self.failed.emit(str(e))

class MRPViewer(QWidget):
    """MRP 看板（支持零部件和成品两种计算模式）"""
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._thread = None
        self._load_available_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # 标题
        title = QLabel("MRP 看板（周）")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)

        # 控制区
        ctrl = QGroupBox("计算参数")
        ctrl.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        cly = QVBoxLayout(ctrl)
        
        # 第一行：日期范围
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("开始日期"))
        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDate(QDate.currentDate())
        date_layout.addWidget(self.dt_start)

        date_layout.addWidget(QLabel("结束日期"))
        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDate(QDate.currentDate().addDays(56))
        date_layout.addWidget(self.dt_end)
        
        date_layout.addStretch()
        cly.addLayout(date_layout)
        
        # 第二行：客户订单版本选择
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("客户订单版本:"))
        self.order_version_combo = QComboBox()
        self.order_version_combo.addItem("全部订单汇总", None)
        self.order_version_combo.setMinimumWidth(300)
        order_layout.addWidget(self.order_version_combo)
        
        order_layout.addWidget(QLabel("成品筛选:"))
        self.parent_item_filter_edit = QLineEdit()
        self.parent_item_filter_edit.setPlaceholderText("输入成品编码或名称进行筛选（留空表示所有成品）")
        self.parent_item_filter_edit.setMinimumWidth(300)
        order_layout.addWidget(self.parent_item_filter_edit)
        
        order_layout.addStretch()
        cly.addLayout(order_layout)
        
        # 第三行：计算类型和按钮
        calc_layout = QHBoxLayout()
        
        # 计算类型选择
        calc_layout.addWidget(QLabel("计算类型:"))
        self.calc_type_combo = QComboBox()
        self.calc_type_combo.addItems(["零部件MRP", "成品MRP"])
        self.calc_type_combo.setCurrentText("零部件MRP")
        calc_layout.addWidget(self.calc_type_combo)
        
        # 说明标签
        type_desc_label = QLabel("零部件MRP：展开BOM计算原材料需求；成品MRP：直接显示成品需求")
        type_desc_label.setStyleSheet("color: #666; font-size: 11px;")
        calc_layout.addWidget(type_desc_label)
        
        calc_layout.addStretch()
        
        # 生成看板按钮
        self.btn_calc = QPushButton("生成看板")
        self.btn_calc.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.btn_calc.clicked.connect(self.on_calc)
        calc_layout.addWidget(self.btn_calc)
        
        # 导出Excel按钮
        self.btn_export = QPushButton("导出Excel")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.btn_export.clicked.connect(self.on_export)
        self.btn_export.setEnabled(False)  # 初始状态禁用
        calc_layout.addWidget(self.btn_export)
        
        cly.addLayout(calc_layout)
        layout.addWidget(ctrl)

        # 表格
        self.tbl = QTableWidget()
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setStretchLastSection(True)
        
        # 设置表格样式
        self.tbl.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                padding: 8px 6px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        
        layout.addWidget(self.tbl)

    def _load_available_data(self):
        """加载可用的客户订单版本和成品信息"""
        try:
            # 加载客户订单版本
            versions = MRPService.get_available_import_versions()
            self.order_version_combo.clear()
            self.order_version_combo.addItem("全部订单汇总", None)
            
            for version in versions:
                display_text = f"{version['ImportId']} - {version['FileName']} ({version['ImportDate']})"
                self.order_version_combo.addItem(display_text, version['ImportId'])
            
            # 连接订单版本选择变化事件
            self.order_version_combo.currentIndexChanged.connect(self.on_order_version_changed)
                
        except Exception as e:
            print(f"加载客户订单版本失败: {e}")

    def on_order_version_changed(self):
        """当选择的客户订单版本变化时，自动调整日期范围"""
        import_id = self.order_version_combo.currentData()
        if import_id is None:
            # 选择"全部订单汇总"时，使用默认日期范围
            self.dt_start.setDate(QDate.currentDate())
            self.dt_end.setDate(QDate.currentDate().addDays(56))
            return
        
        try:
            # 获取指定订单版本的时间范围
            order_range = MRPService.get_order_version_date_range(import_id)
            if order_range:
                start_date = order_range.get("earliest_date")
                end_date = order_range.get("latest_date")
                
                if start_date and end_date:
                    # 转换为QDate对象
                    q_start = QDate.fromString(start_date, "yyyy-MM-dd")
                    q_end = QDate.fromString(end_date, "yyyy-MM-dd")
                    
                    if q_start.isValid() and q_end.isValid():
                        # 直接设置为订单的实际时间范围
                        self.dt_start.setDate(q_start)
                        self.dt_end.setDate(q_end)
        except Exception as e:
            print(f"自动调整日期范围失败: {e}")

    # ---- 交互 ----
    def on_calc(self):
        s = self.dt_start.date().toString("yyyy-MM-dd")
        e = self.dt_end.date().toString("yyyy-MM-dd")
        if self.dt_start.date() >= self.dt_end.date():
            QMessageBox.warning(self, "提示", "结束日期必须大于开始日期")
            return
            
        # 获取选择的客户订单版本ID
        import_id = self.order_version_combo.currentData()
        
        # 获取成品筛选条件
        parent_item_filter = self.parent_item_filter_edit.text().strip() or None
        
        # 获取计算类型
        calc_type = "child" if self.calc_type_combo.currentText() == "零部件MRP" else "parent"
        
        self.btn_calc.setEnabled(False)
        self.btn_export.setEnabled(False)  # 禁用导出按钮
        self.tbl.clear()
        
        # 显示计算状态
        self.tbl.setRowCount(1)
        self.tbl.setColumnCount(1)
        self.tbl.setHorizontalHeaderLabels(["计算中..."])
        self.tbl.setItem(0, 0, QTableWidgetItem("正在计算MRP，请稍候..."))
        
        self._thread = MRPCalcThread(s, e, import_id, parent_item_filter, calc_type)
        self._thread.finished.connect(self.render_board)
        self._thread.failed.connect(self.show_error)
        self._thread.start()

    def show_error(self, msg: str):
        self.btn_calc.setEnabled(True)
        QMessageBox.critical(self, "错误", msg)

    # ---- 渲染 ----
    def render_board(self, data: dict):
        self.btn_calc.setEnabled(True)
        self.btn_export.setEnabled(True)  # 启用导出按钮
        
        # 保存当前数据用于导出
        self._current_data = data
        
        if not data:
            self.tbl.setRowCount(0); self.tbl.setColumnCount(0); return

        weeks = data.get("weeks", [])
        rows = data.get("rows", [])

        # 根据计算类型设置不同的列标题
        calc_type = self.calc_type_combo.currentText()
        if calc_type == "零部件MRP":
            # 零部件MRP：物料编码、名称、类型、行别、期初库存、各周
            headers = ["物料编码", "物料名称", "物料类型", "行别", "期初库存"] + weeks
        else:
            # 成品MRP：物料编码、名称、类型、行别、期初库存、各周
            headers = ["成品编码", "成品名称", "成品类型", "行别", "期初库存"] + weeks
            
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)

        # 增加一行用于显示日期
        self.tbl.setRowCount(len(rows) + 1)
        
        # 设置颜色
        green_bg = QBrush(QColor(235, 252, 239))
        red_bg = QBrush(QColor(255, 235, 238))
        blue_bg = QBrush(QColor(235, 245, 251))
        date_bg = QBrush(QColor(248, 249, 250))  # 日期行的背景色

        # 第一行：显示CW对应的日期
        date_row = 0
        for ci, w in enumerate(weeks, start=5):
            # 将CW转换为对应的日期
            date_str = self._convert_cw_to_date(w)
            it = self._set_item(date_row, ci, date_str)
            it.setBackground(date_bg)
            # 设置日期行的字体样式
            font = it.font()
            font.setPointSize(9)
            it.setFont(font)
        
        # 设置日期行的基本信息列
        for c in range(5):
            it = self._set_item(date_row, c, "")
            it.setBackground(date_bg)

        # 数据行（从第二行开始）
        for r, row in enumerate(rows):
            actual_row = r + 1  # 实际行号要+1，因为第一行是日期行
            
            # 基本信息列
            self._set_item(actual_row, 0, row.get("ItemCode", ""))
            self._set_item(actual_row, 1, row.get("ItemName", ""))
            self._set_item(actual_row, 2, row.get("ItemType", ""))
            self._set_item(actual_row, 3, row.get("RowType", ""))
            self._set_item(actual_row, 4, self._fmt(row.get("StartOnHand", 0)))

            # 根据计算类型设置不同的行底色
            if calc_type == "零部件MRP":
                # 零部件MRP：库存行上绿；如果库存为负则对应单元格染红
                is_stock_row = (row.get("RowType") == "即时库存")
                if is_stock_row:
                    for c in range(0, 5):
                        it = self.tbl.item(actual_row, c)
                        if it: it.setBackground(green_bg)
            else:
                # 成品MRP：所有行都上蓝色背景
                for c in range(0, 5):
                    it = self.tbl.item(actual_row, c)
                    if it: it.setBackground(blue_bg)

            # 周数据列
            for ci, w in enumerate(weeks, start=5):
                val = float(row["cells"].get(w, 0.0))
                it = self._set_item(actual_row, ci, self._fmt(val))
                
                if calc_type == "零部件MRP":
                    # 零部件MRP：库存为负时染红
                    is_stock_row = (row.get("RowType") == "即时库存")
                    if is_stock_row and val < 0:
                        it.setBackground(red_bg)
                else:
                    # 成品MRP：即时库存行为负数时染红，生产计划行大于0时染绿
                    is_stock_row = (row.get("RowType") == "即时库存")
                    if is_stock_row and val < 0:
                        it.setBackground(red_bg)  # 库存不足，标红
                    elif not is_stock_row and val > 0:
                        it.setBackground(green_bg)  # 有需求，标绿

        # 小优化：把计划/库存两行当作一个分组阅读
        if calc_type == "零部件MRP":
            self.tbl.setAlternatingRowColors(False)
        else:
            self.tbl.setAlternatingRowColors(True)

    def _set_item(self, r: int, c: int, text: str):
        it = QTableWidgetItem(str(text))
        it.setTextAlignment(Qt.AlignCenter)
        self.tbl.setItem(r, c, it)
        return it

    @staticmethod
    def _fmt(v: float) -> str:
        # 千分位，不带多余小数
        if abs(v - int(v)) < 1e-6:
            return f"{int(v):,}"
        return f"{v:,.3f}"

    def _convert_cw_to_date(self, cw: str) -> str:
        """将CW格式转换为对应的日期字符串"""
        try:
            # 从CW中提取周数
            if cw.startswith("CW"):
                week_num = int(cw[2:])
                
                # 获取当前年份
                current_year = QDate.currentDate().year()
                
                # 计算该年的第week_num周的第一天
                # 使用QDate的fromString和addDays来计算
                jan1 = QDate(current_year, 1, 1)
                
                # 找到该年第一个周一
                days_to_monday = (8 - jan1.dayOfWeek()) % 7
                if days_to_monday == 0:
                    days_to_monday = 7
                
                first_monday = jan1.addDays(days_to_monday - 1)
                
                # 计算目标周的第一天
                target_week_start = first_monday.addDays((week_num - 1) * 7)
                
                # 返回格式化的日期字符串
                return target_week_start.toString("yyyy/MM/dd")
            else:
                return cw
        except:
            return cw

    def on_export(self):
        """导出Excel文件"""
        if not hasattr(self, '_current_data') or not self._current_data:
            QMessageBox.warning(self, "提示", "请先生成看板数据")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "导出Excel文件", 
            f"MRP看板_{QDate.currentDate().toString('yyyyMMdd')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            self.export_to_excel(file_path, self._current_data)
            QMessageBox.information(self, "导出成功", f"文件已保存到：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出过程中发生错误：\n{str(e)}")

    def export_to_excel(self, file_path: str, data: dict):
        """导出数据到Excel文件"""
        weeks = data.get("weeks", [])
        rows = data.get("rows", [])
        calc_type = self.calc_type_combo.currentText()
        
        # 创建工作簿和工作表
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"MRP看板_{calc_type}"
        
        # 定义颜色样式
        green_fill = PatternFill(start_color="E7F5E7", end_color="E7F5E7", fill_type="solid")
        red_fill = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")
        blue_fill = PatternFill(start_color="EBF3FB", end_color="EBF3FB", fill_type="solid")
        date_fill = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
        
        # 定义字体样式
        header_font = Font(bold=True, size=12)
        date_font = Font(size=9)
        normal_font = Font(size=10)
        
        # 定义对齐方式
        center_alignment = Alignment(horizontal="center", vertical="center")
        left_alignment = Alignment(horizontal="left", vertical="center")
        
        # 定义边框
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # 设置列标题
        if calc_type == "零部件MRP":
            headers = ["物料编码", "物料名称", "物料类型", "行别", "期初库存"] + weeks
        else:
            headers = ["成品编码", "成品名称", "成品类型", "行别", "期初库存"] + weeks
        
        # 写入列标题
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = center_alignment
            cell.border = thin_border
            cell.fill = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
        
        # 写入日期行（第二行）
        row_num = 2
        for col in range(1, 6):  # 基本信息列
            cell = ws.cell(row=row_num, column=col, value="")
            cell.fill = date_fill
            cell.border = thin_border
        
        for col, week in enumerate(weeks, 6):  # 周数据列
            date_str = self._convert_cw_to_date(week)
            cell = ws.cell(row=row_num, column=col, value=date_str)
            cell.font = date_font
            cell.alignment = center_alignment
            cell.fill = date_fill
            cell.border = thin_border
        
        # 写入数据行
        for row_data in rows:
            row_num += 1
            
            # 基本信息列
            basic_info = [
                row_data.get("ItemCode", ""),
                row_data.get("ItemName", ""),
                row_data.get("ItemType", ""),
                row_data.get("RowType", ""),
                self._fmt(row_data.get("StartOnHand", 0))
            ]
            
            for col, value in enumerate(basic_info, 1):
                cell = ws.cell(row=row_num, column=col, value=value)
                cell.font = normal_font
                cell.alignment = center_alignment
                cell.border = thin_border
                
                # 根据计算类型设置背景色
                if calc_type == "零部件MRP":
                    if row_data.get("RowType") == "即时库存":
                        cell.fill = green_fill
                else:  # 成品MRP
                    cell.fill = blue_fill
            
            # 周数据列
            for col, week in enumerate(weeks, 6):
                val = float(row_data["cells"].get(week, 0.0))
                cell = ws.cell(row=row_num, column=col, value=val)
                cell.font = normal_font
                cell.alignment = center_alignment
                cell.border = thin_border
                
                # 根据计算类型和数值设置背景色
                if calc_type == "零部件MRP":
                    if row_data.get("RowType") == "即时库存" and val < 0:
                        cell.fill = red_fill  # 库存不足，标红
                else:  # 成品MRP
                    if row_data.get("RowType") == "即时库存" and val < 0:
                        cell.fill = red_fill  # 库存不足，标红
                    elif row_data.get("RowType") != "即时库存" and val > 0:
                        cell.fill = green_fill  # 有需求，标绿
        
        # 调整列宽
        for col in range(1, len(headers) + 1):
            if col <= 5:  # 基本信息列
                ws.column_dimensions[get_column_letter(col)].width = 15
            else:  # 周数据列
                ws.column_dimensions[get_column_letter(col)].width = 12
        
        # 保存文件
        wb.save(file_path)
        wb.close()
