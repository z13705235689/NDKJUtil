from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QDialogButtonBox, QDoubleSpinBox, QLabel,
    QMessageBox
)
from PySide6.QtCore import Qt, QDate
from app.services.inventory_service import InventoryService
from app.services.item_service import ItemService

class QtyDialog(QDialog):
    def __init__(self, item_name: str, current: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"调整库存 - {item_name}")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("库存数量:"))
        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(2)
        self.spin.setRange(-1e9, 1e9)
        self.spin.setValue(current)
        layout.addWidget(self.spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def value(self):
        return self.spin.value()

class InventoryManagement(QWidget):
    """库存管理界面"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle("库存管理")
        layout = QVBoxLayout(self)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_data)
        btn_layout.addWidget(refresh_btn)
        adjust_btn = QPushButton("调整库存")
        adjust_btn.clicked.connect(self.adjust_selected)
        btn_layout.addWidget(adjust_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "物料编码", "物料名称", "库存数量", "仓库", "库位"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

    def load_data(self):
        data = InventoryService.get_all()
        self.table.setRowCount(len(data))
        for r, row in enumerate(data):
            self.table.setItem(r, 0, QTableWidgetItem(str(row['ItemCode'])))
            self.table.setItem(r, 1, QTableWidgetItem(str(row['CnName'])))
            self.table.setItem(r, 2, QTableWidgetItem(str(row['QtyOnHand'])))
            self.table.setItem(r, 3, QTableWidgetItem(str(row.get('Warehouse') or '')))
            self.table.setItem(r, 4, QTableWidgetItem(str(row.get('Location') or '')))
            # store item id in row for later
            item_id = row['ItemId']
            for c in range(5):
                self.table.item(r, c).setData(Qt.UserRole, item_id)
        self.table.resizeColumnsToContents()

    def adjust_selected(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "提示", "请先选择一行")
            return
        item_id = self.table.item(selected, 0).data(Qt.UserRole)
        code = self.table.item(selected, 0).text()
        name = self.table.item(selected, 1).text()
        current_qty = float(self.table.item(selected, 2).text())
        dlg = QtyDialog(f"{code} {name}", current_qty, self)
        if dlg.exec() == QDialog.Accepted:
            InventoryService.update_quantity(item_id, dlg.value)
            self.load_data()
