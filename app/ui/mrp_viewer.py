from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QDateEdit, QLabel
)
from PySide6.QtCore import Qt, QDate
from app.services.mrp_service import MRPService

class MRPViewer(QWidget):
    """MRP计算结果展示"""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("开始日期:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        control_layout.addWidget(self.start_date)
        control_layout.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate().addDays(30))
        control_layout.addWidget(self.end_date)
        calc_btn = QPushButton("计算MRP")
        calc_btn.clicked.connect(self.calculate)
        control_layout.addWidget(calc_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

    def calculate(self):
        start = self.start_date.date().toString('yyyy-MM-dd')
        end = self.end_date.date().toString('yyyy-MM-dd')
        result = MRPService.calculate(start, end)
        # collect all weeks
        weeks = set()
        for info in result.values():
            weeks.update(info['Weeks'].keys())
        weeks = sorted(weeks)
        # set columns: ItemCode, ItemName, OnHand, then for each week two columns
        headers = ["物料编码", "物料名称", "现有库存"]
        for wk in weeks:
            headers.append(f"{wk}需求")
            headers.append(f"{wk}预计")
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(result))
        for r, (code, info) in enumerate(sorted(result.items())):
            self.table.setItem(r, 0, QTableWidgetItem(code))
            self.table.setItem(r, 1, QTableWidgetItem(info.get('ItemName','')))
            self.table.setItem(r, 2, QTableWidgetItem(str(info.get('OnHand',0))))
            col = 3
            for wk in weeks:
                wkdata = info['Weeks'].get(wk, {'required':0,'projected':info.get('OnHand',0)})
                self.table.setItem(r, col, QTableWidgetItem(str(round(wkdata['required'],2))))
                self.table.setItem(r, col+1, QTableWidgetItem(str(round(wkdata['projected'],2))))
                col += 2
        self.table.resizeColumnsToContents()
