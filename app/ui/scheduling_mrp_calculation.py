#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排产订单MRP计算对话框
- 采用现有零部件MRP计算逻辑
- 显示MRP计算结果
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta, date

from PySide6.QtCore import Qt, QDate, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QFrame, QLineEdit, QAbstractItemView, QMessageBox,
    QHeaderView, QSizePolicy, QAbstractScrollArea, QComboBox, QGroupBox,
    QProgressBar, QCheckBox
)

from app.services.scheduling_order_service import SchedulingOrderService


class SchedulingMRPDialog(QDialog):
    """排产订单MRP计算对话框"""
    
    def __init__(self, order_id: int, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.setWindowTitle("排产订单MRP计算")
        self.setModal(True)
        self.resize(1400, 900)
        self.setMinimumSize(1000, 700)
        
        self.init_ui()
        self.load_order_info()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题区域
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        title_layout = QHBoxLayout(title_frame)
        
        self.title_label = QLabel("排产订单MRP计算")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
            }
        """)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #6c757d;
                padding: 4px 8px;
                background-color: #e9ecef;
                border-radius: 3px;
            }
        """)
        title_layout.addWidget(self.status_label)
        
        layout.addWidget(title_frame)
        
        # 控制区域
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        control_layout = QHBoxLayout(control_frame)
        
        # 物料类型过滤
        control_layout.addWidget(QLabel("物料类型:"))
        self.material_type_combo = QComboBox()
        self.material_type_combo.addItems(["全部", "RM", "PKG", "RM+PKG"])
        self.material_type_combo.setCurrentText("RM+PKG")
        control_layout.addWidget(self.material_type_combo)
        
        control_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入物料名称或规格进行搜索...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 12px;
                min-width: 200px;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """)
        self.search_edit.textChanged.connect(self.filter_mrp_results)
        control_layout.addWidget(self.search_edit)
        
        control_layout.addStretch()
        
        # 计算按钮
        self.calculate_btn = QPushButton("计算MRP")
        self.calculate_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        self.calculate_btn.clicked.connect(self.calculate_mrp)
        control_layout.addWidget(self.calculate_btn)
        
        # 导出按钮
        self.export_btn = QPushButton("导出Excel")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.export_btn.clicked.connect(self.export_to_excel)
        self.export_btn.setEnabled(False)
        control_layout.addWidget(self.export_btn)
        
        layout.addWidget(control_frame)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 5px;
                text-align: center;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # MRP结果表格
        self.mrp_table = QTableWidget()
        self.mrp_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #dee2e6;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
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
        
        self.mrp_table.setAlternatingRowColors(True)
        self.mrp_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mrp_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.mrp_table.horizontalHeader().setStretchLastSection(True)
        self.mrp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 设置表格大小调整策略
        try:
            policy = QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow
        except AttributeError:
            policy = getattr(QAbstractScrollArea, "AdjustToContentsOnFirstShow", QAbstractScrollArea.AdjustToContents)
        self.mrp_table.setSizeAdjustPolicy(policy)
        self.mrp_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout.addWidget(self.mrp_table)
        
        # 警告信息区域
        self.warning_frame = QFrame()
        self.warning_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.warning_frame.setVisible(False)
        warning_layout = QHBoxLayout(self.warning_frame)
        
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("""
            QLabel {
                color: #856404;
                font-size: 12px;
            }
        """)
        warning_layout.addWidget(self.warning_label)
        warning_layout.addStretch()
        
        layout.addWidget(self.warning_frame)
        
        # 按钮区域
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.addStretch()
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #495057;
            }
        """)
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addWidget(button_frame)
    
    def load_order_info(self):
        """加载订单信息"""
        try:
            order = SchedulingOrderService.get_scheduling_order_by_id(self.order_id)
            if order:
                self.title_label.setText(f"排产订单MRP计算 - {order['OrderName']}")
        except Exception as e:
            print(f"加载订单信息失败: {e}")
    
    def calculate_mrp(self):
        """计算MRP"""
        try:
            self.status_label.setText("计算中...")
            self.calculate_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 获取物料类型过滤
            material_type = self.material_type_combo.currentText()
            include_types = []
            if material_type == "RM":
                include_types = ["RM"]
            elif material_type == "PKG":
                include_types = ["PKG"]
            elif material_type == "RM+PKG":
                include_types = ["RM", "PKG"]
            else:  # 全部
                include_types = None
            
            self.progress_bar.setValue(30)
            
            # 计算MRP
            mrp_data = SchedulingOrderService.calculate_mrp_for_order(
                self.order_id, include_types
            )
            
            self.progress_bar.setValue(80)
            
            if "error" in mrp_data:
                QMessageBox.critical(self, "错误", mrp_data["error"])
                return
            
            # 显示结果
            self.display_mrp_results(mrp_data)
            
            self.progress_bar.setValue(100)
            self.status_label.setText("计算完成")
            self.export_btn.setEnabled(True)
            
            # 隐藏进度条
            QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算MRP失败: {str(e)}")
            self.status_label.setText("计算失败")
        finally:
            self.calculate_btn.setEnabled(True)
    
    def display_mrp_results(self, mrp_data):
        """显示MRP计算结果"""
        try:
            order_info = mrp_data["order_info"]
            date_range = mrp_data["date_range"]
            mrp_results = mrp_data["mrp_results"]
            
            # 设置表格列数
            # 固定列：物料编码、物料名称、规格、类型、品牌
            # 动态列：每天的MRP数据（需求数量、在手库存、净需求）
            fixed_cols = 5
            total_cols = fixed_cols + len(date_range) * 3  # 每天3列
            
            self.mrp_table.setColumnCount(total_cols)
            
            # 设置表头
            headers = ["物料编码", "物料名称", "规格", "类型", "品牌"]
            for date_str in date_range:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    weekday = date_obj.strftime("%A")[:3]
                    date_display = f"{date_str}\n{weekday}"
                except:
                    date_display = date_str
                
                headers.extend([
                    f"{date_display}\n需求数量",
                    f"{date_display}\n在手库存", 
                    f"{date_display}\n净需求"
                ])
            
            self.mrp_table.setHorizontalHeaderLabels(headers)
            
            # 设置行数
            self.mrp_table.setRowCount(len(mrp_results))
            
            # 填充数据
            for row, mrp_item in enumerate(mrp_results):
                # 固定列数据
                self.mrp_table.setItem(row, 0, QTableWidgetItem(mrp_item["ItemCode"]))
                self.mrp_table.setItem(row, 1, QTableWidgetItem(mrp_item["ItemName"]))
                self.mrp_table.setItem(row, 2, QTableWidgetItem(mrp_item.get("ItemSpec", "")))
                self.mrp_table.setItem(row, 3, QTableWidgetItem(mrp_item["ItemType"]))
                self.mrp_table.setItem(row, 4, QTableWidgetItem(mrp_item.get("Brand", "")))
                
                # 设置固定列不可编辑
                for col in range(fixed_cols):
                    item = self.mrp_table.item(row, col)
                    if item:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setBackground(QBrush(QColor("#f8f9fa")))
                
                # 动态列数据（MRP数据）
                for col, date_str in enumerate(date_range):
                    col_index = fixed_cols + col * 3
                    cell_data = mrp_item["cells"].get(date_str, {})
                    
                    required_qty = cell_data.get("RequiredQty", 0.0)
                    onhand_qty = cell_data.get("OnHandQty", 0.0)
                    net_qty = cell_data.get("NetQty", 0.0)
                    
                    # 需求数量
                    req_item = QTableWidgetItem(self._format_number(required_qty))
                    req_item.setTextAlignment(Qt.AlignCenter)
                    if required_qty > 0:
                        req_item.setBackground(QBrush(QColor("#d4edda")))  # 绿色背景
                    self.mrp_table.setItem(row, col_index, req_item)
                    
                    # 在手库存
                    onhand_item = QTableWidgetItem(self._format_number(onhand_qty))
                    onhand_item.setTextAlignment(Qt.AlignCenter)
                    self.mrp_table.setItem(row, col_index + 1, onhand_item)
                    
                    # 净需求
                    net_item = QTableWidgetItem(self._format_number(net_qty))
                    net_item.setTextAlignment(Qt.AlignCenter)
                    if net_qty > 0:
                        net_item.setBackground(QBrush(QColor("#f8d7da")))  # 红色背景
                        net_item.setForeground(QBrush(QColor("#721c24")))  # 红色文字
                    self.mrp_table.setItem(row, col_index + 2, net_item)
            
            # 调整列宽
            header = self.mrp_table.horizontalHeader()
            for col in range(fixed_cols):
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            for col in range(fixed_cols, total_cols):
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            
            # 显示警告信息
            warnings = []
            for mrp_item in mrp_results:
                for date_str in date_range:
                    cell_data = mrp_item["cells"].get(date_str, {})
                    net_qty = cell_data.get("NetQty", 0.0)
                    if net_qty > 0:
                        warnings.append(f"{mrp_item['ItemCode']} 在 {date_str} 需要 {net_qty} 个")
            
            if warnings:
                self.warning_label.setText(f"发现 {len(warnings)} 个物料需求缺口")
                self.warning_frame.setVisible(True)
            else:
                self.warning_frame.setVisible(False)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示MRP结果失败: {str(e)}")
    
    def filter_mrp_results(self):
        """过滤MRP结果"""
        search_text = self.search_edit.text().lower()
        for row in range(self.mrp_table.rowCount()):
            item_code_item = self.mrp_table.item(row, 0)
            item_name_item = self.mrp_table.item(row, 1)
            item_spec_item = self.mrp_table.item(row, 2)
            
            if item_code_item and item_name_item and item_spec_item:
                item_code = item_code_item.text().lower()
                item_name = item_name_item.text().lower()
                item_spec = item_spec_item.text().lower()
                
                match = (search_text in item_code or 
                        search_text in item_name or 
                        search_text in item_spec)
                
                self.mrp_table.setRowHidden(row, not match)
    
    def export_to_excel(self):
        """导出Excel"""
        # TODO: 实现Excel导出功能
        QMessageBox.information(self, "提示", "Excel导出功能待实现")
    
    def _format_number(self, value):
        """格式化数字显示"""
        if abs(value - int(value)) < 1e-6:
            return f"{int(value):,}"
        return f"{value:,.3f}"