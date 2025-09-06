#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新的排产订单管理界面
- 创建排产订单
- 选择需要排产的成品
- 管理排产订单列表
"""

from typing import Optional, List, Dict
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QDate, Signal, QTimer, QRect
from PySide6.QtGui import QFont, QColor, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QFrame, QLineEdit, QComboBox, QAbstractItemView,
    QMessageBox, QTabWidget, QGroupBox, QGridLayout, QCheckBox, QDialog,
    QHeaderView, QDateEdit, QListWidget, QListWidgetItem, QSplitter,
    QSizePolicy, QScrollArea, QFormLayout, QDialogButtonBox, QTextEdit,
    QSpacerItem, QAbstractScrollArea
)

from app.services.scheduling_order_service import SchedulingOrderService


class TwoRowHeader(QHeaderView):
    """自定义两行表头，支持周日列背景色"""
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(Qt.AlignCenter)
        self._top_font = QFont()
        self._top_font.setBold(True)
        self._bottom_font = QFont()
        self._bottom_font.setPointSize(self._bottom_font.pointSize() - 1)
        self._bottom_font.setBold(True)
        h = self.fontMetrics().height()
        self.setFixedHeight(int(h * 3.5))  # 增加高度，让两行之间有更多间距

    def sizeHint(self):
        s = super().sizeHint()
        h = self.fontMetrics().height()
        s.setHeight(int(h * 3.5))  # 与setFixedHeight保持一致
        return s

    def paintSection(self, painter: QPainter, rect: QRect, logicalIndex: int):
        if not rect.isValid():
            return
        
        # 完全自定义绘制，不使用父类方法
        painter.save()
        
        table = self.parent()
        item = table.horizontalHeaderItem(logicalIndex) if table else None
        top = item.text() if item else ""
        bottom = item.data(Qt.UserRole) if (item and item.data(Qt.UserRole) is not None) else ""

        # 检查是否是周日，设置整列黄色背景
        if bottom == "日":
            painter.fillRect(rect, QColor("#fff3cd"))  # 使用更柔和的黄色
        else:
            painter.fillRect(rect, QColor("#fafafa"))  # 默认背景
        
        # 绘制边框
        painter.setPen(QColor("#d9d9d9"))
        painter.drawRect(rect)

        # 计算两行的矩形区域，增加间距
        top_height = int(rect.height() * 0.6)  # 第一行占60%
        bottom_height = rect.height() - top_height  # 第二行占剩余部分
        
        # 绘制第一行（日期）
        painter.setPen(QColor("#333333"))
        painter.setFont(self._top_font)
        topRect = QRect(rect.left() + 1, rect.top() + 1, rect.width() - 2, top_height - 2)
        painter.drawText(topRect, Qt.AlignCenter, str(top))
        
        # 绘制第二行（周几）
        if bottom:  # 只有当有周几数据时才绘制
            painter.setFont(self._bottom_font)
            painter.setPen(QColor("#666666"))
            
            # 为周几预留更多边距
            margin = 2
            bottomRect = QRect(
                rect.left() + margin, 
                rect.top() + top_height, 
                rect.width() - margin * 2, 
                bottom_height - margin
            )
            
            painter.drawText(bottomRect, Qt.AlignCenter | Qt.TextWrapAnywhere, str(bottom))
        
        painter.restore()


class ProductSelectionDialog(QDialog):
    """产品选择对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择排产产品")
        self.setModal(True)
        self.resize(800, 600)
        
        self.selected_products = []
        self.init_ui()
        self.load_products()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.filter_products)
        search_layout.addWidget(self.search_edit)
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # 产品列表
        self.product_list = QListWidget()
        self.product_list.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.product_list)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all)
        self.clear_selection_btn = QPushButton("清空选择")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.clear_selection_btn)
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_products(self):
        """加载可排产的产品列表"""
        try:
            products = SchedulingOrderService.get_available_products()
            self.all_products = products
            
            for product in products:
                item_text = f"{product['ItemCode']} - {product['CnName']}"
                if product.get('ItemSpec'):
                    item_text += f" ({product['ItemSpec']})"
                if product.get('Brand'):
                    item_text += f" [品牌: {product['Brand']}]"
                if product.get('ProjectName'):
                    item_text += f" [项目: {product['ProjectName']}]"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, product)
                self.product_list.addItem(item)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载产品列表失败: {str(e)}")
    
    def filter_products(self, text):
        """过滤产品列表"""
        for i in range(self.product_list.count()):
            item = self.product_list.item(i)
            product = item.data(Qt.UserRole)
            if product:
                search_text = text.lower()
                match = (
                    search_text in product['ItemCode'].lower() or
                    search_text in product['CnName'].lower() or
                    (product.get('ItemSpec', '').lower() and search_text in product['ItemSpec'].lower()) or
                    (product.get('Brand', '').lower() and search_text in product['Brand'].lower()) or
                    (product.get('ProjectName', '').lower() and search_text in product['ProjectName'].lower())
                )
                item.setHidden(not match)
    
    def select_all(self):
        """全选"""
        for i in range(self.product_list.count()):
            item = self.product_list.item(i)
            if not item.isHidden():
                item.setSelected(True)
    
    def clear_selection(self):
        """清空选择"""
        self.product_list.clearSelection()
    
    def get_selected_products(self):
        """获取选中的产品"""
        selected_items = self.product_list.selectedItems()
        return [item.data(Qt.UserRole) for item in selected_items]


class SchedulingOrderManagementWidget(QWidget):
    """排产订单管理主界面"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_orders()
    
    def init_ui(self):
        self.setWindowTitle("排产订单管理")
        
        # 设置大小策略
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        main_layout = QVBoxLayout()
        
        # 页签
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(
            "QTabWidget::pane{border:1px solid #dee2e6;background:white;}"
            "QTabBar::tab{background:#f8f9fa;border:1px solid #dee2e6;padding:8px 16px;margin-right:2px;}"
            "QTabBar::tab:selected{background:white;border-bottom:2px solid #007bff;}"
        )
        
        self.create_order_list_tab()
        self.create_order_detail_tab()
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
    
    def create_order_list_tab(self):
        """创建订单列表页签"""
        order_widget = QWidget()
        order_layout = QVBoxLayout()
        
        # 控制面板
        control_panel = QFrame()
        control_panel.setFrameStyle(QFrame.StyledPanel)
        control_panel.setStyleSheet("QFrame{background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;}")
        control_layout = QVBoxLayout()
        
        # 创建订单按钮
        create_layout = QHBoxLayout()
        self.create_order_btn = QPushButton("新建排产订单")
        self.create_order_btn.setStyleSheet("QPushButton{background:#007bff;color:#fff;border:none;padding:8px 16px;border-radius:4px;}"
                                           "QPushButton:hover{background:#0069d9;}")
        self.create_order_btn.clicked.connect(self.create_new_order)
        create_layout.addWidget(self.create_order_btn)
        create_layout.addStretch()
        control_layout.addLayout(create_layout)
        
        control_panel.setLayout(control_layout)
        order_layout.addWidget(control_panel)
        
        # 订单列表表格
        self.order_table = QTableWidget()
        self.order_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: 600;
                font-size: 14px;
            }
        """)
        self.order_table.setAlternatingRowColors(True)
        self.order_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.order_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.order_table.itemSelectionChanged.connect(self.on_order_selected)
        
        # 设置表头
        headers = ["订单ID", "订单名称", "开始日期", "结束日期", "状态", "创建人", "创建时间", "备注", "操作"]
        self.order_table.setColumnCount(len(headers))
        self.order_table.setHorizontalHeaderLabels(headers)
        
        # 设置列宽
        header = self.order_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 订单ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # 订单名称
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # 开始日期
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # 结束日期
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # 状态
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # 创建人
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) # 创建时间
        header.setSectionResizeMode(7, QHeaderView.Stretch)          # 备注
        header.setSectionResizeMode(8, QHeaderView.Fixed)             # 操作列固定宽度
        self.order_table.setColumnWidth(8, 280)  # 设置操作列宽度为280像素
        
        order_layout.addWidget(self.order_table)
        order_widget.setLayout(order_layout)
        self.tab_widget.addTab(order_widget, "排产列表")
    
    def create_order_detail_tab(self):
        """创建排产详情页签"""
        detail_widget = QWidget()
        detail_layout = QVBoxLayout()
        
        # 排产订单选择面板
        selection_group = QGroupBox("选择排产订单")
        selection_layout = QVBoxLayout()
        
        # 订单选择下拉框
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("排产订单:"))
        self.order_selection_combo = QComboBox()
        self.order_selection_combo.setMinimumWidth(300)
        self.order_selection_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background: white;
                min-width: 300px;
            }
            QComboBox:focus {
                border-color: #007bff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6c757d;
                margin-right: 5px;
            }
        """)
        self.order_selection_combo.currentTextChanged.connect(self.on_order_selection_changed)
        order_layout.addWidget(self.order_selection_combo)
        order_layout.addStretch()
        selection_layout.addLayout(order_layout)
        
        selection_group.setLayout(selection_layout)
        detail_layout.addWidget(selection_group)
        
        # 排产看板面板
        kanban_group = QGroupBox("排产看板")
        kanban_layout = QVBoxLayout()
        
        # 看板控制按钮
        kanban_btn_layout = QHBoxLayout()
        self.refresh_kanban_btn = QPushButton("刷新看板")
        self.refresh_kanban_btn.setStyleSheet("QPushButton{background:#6c757d;color:#fff;border:none;padding:8px 16px;border-radius:4px;}"
                                             "QPushButton:hover{background:#5a6268;}")
        self.refresh_kanban_btn.clicked.connect(self.refresh_kanban_data)
        self.refresh_kanban_btn.setEnabled(False)
        
        self.save_kanban_btn = QPushButton("保存排产")
        self.save_kanban_btn.setStyleSheet("QPushButton{background:#007bff;color:#fff;border:none;padding:8px 16px;border-radius:4px;}"
                                          "QPushButton:hover{background:#0056b3;}")
        self.save_kanban_btn.clicked.connect(self.save_kanban_data)
        self.save_kanban_btn.setEnabled(False)
        
        kanban_btn_layout.addWidget(self.refresh_kanban_btn)
        kanban_btn_layout.addWidget(self.save_kanban_btn)
        kanban_btn_layout.addStretch()
        kanban_layout.addLayout(kanban_btn_layout)
        
        # 看板表格
        self.kanban_table = QTableWidget()
        # 完全移除CSS样式，让背景色设置生效
        self.kanban_table.setStyleSheet("")
        
        # 设置自定义表头
        self.kanban_table.setHorizontalHeader(TwoRowHeader(Qt.Horizontal, self.kanban_table))
        
        # 禁用交替行颜色，避免覆盖我们的背景色设置
        self.kanban_table.setAlternatingRowColors(False)
        self.kanban_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.kanban_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.kanban_table.horizontalHeader().setStretchLastSection(True)
        
        # 设置行高
        self.kanban_table.verticalHeader().setDefaultSectionSize(35)
        
        # 连接单元格编辑信号
        self.kanban_table.itemChanged.connect(self.on_kanban_item_changed)
        self.kanban_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 设置表格大小调整策略
        try:
            policy = QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow
        except AttributeError:
            policy = getattr(QAbstractScrollArea, "AdjustToContentsOnFirstShow", QAbstractScrollArea.AdjustToContents)
        self.kanban_table.setSizeAdjustPolicy(policy)
        self.kanban_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        kanban_layout.addWidget(self.kanban_table)
        kanban_group.setLayout(kanban_layout)
        detail_layout.addWidget(kanban_group)
        
        detail_widget.setLayout(detail_layout)
        self.tab_widget.addTab(detail_widget, "排产详情")
        
        # 初始化订单选择下拉框
        self.load_order_selection()
    
    def load_order_selection(self):
        """加载订单选择下拉框"""
        try:
            orders = SchedulingOrderService.get_scheduling_orders()
            
            self.order_selection_combo.clear()
            self.order_selection_combo.addItem("请选择排产订单", None)
            
            for order in orders:
                order_text = f"{order['OrderName']} ({order['StartDate']} - {order['EndDate']})"
                self.order_selection_combo.addItem(order_text, order['OrderId'])
                
        except Exception as e:
            print(f"加载订单选择列表失败: {e}")
    
    def on_order_selection_changed(self, text):
        """订单选择改变时的处理"""
        try:
            order_id = self.order_selection_combo.currentData()
            if order_id:
                self.current_order_id = order_id
                self.load_kanban_data()
                self.refresh_kanban_btn.setEnabled(True)
                self.save_kanban_btn.setEnabled(True)
            else:
                self.current_order_id = None
                self.clear_kanban_table()
                self.refresh_kanban_btn.setEnabled(False)
                self.save_kanban_btn.setEnabled(False)
        except Exception as e:
            print(f"订单选择处理失败: {e}")
    
    def load_kanban_data(self):
        """加载看板数据"""
        if not hasattr(self, 'current_order_id') or not self.current_order_id:
            return
            
        try:
            # 获取看板数据
            data = SchedulingOrderService.get_scheduling_kanban_data(self.current_order_id)
            
            if "error" in data:
                QMessageBox.critical(self, "错误", data["error"])
                return
            
            order_info = data["order_info"]
            date_range = data["date_range"]
            products = data["products"]
            
            # 设置表格列数
            # 固定列：产品名称、规格、品牌、项目名称
            # 动态列：每天的日期
            fixed_cols = 4
            total_cols = fixed_cols + len(date_range)
            self.kanban_table.setColumnCount(total_cols)
            
            # 设置表头
            headers = ["产品名称", "规格", "品牌", "项目名称"]
            for date_str in date_range:
                # 将日期转换为显示格式
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    # 周几改为中文显示
                    weekday_map = {
                        0: "一", 1: "二", 2: "三", 3: "四", 
                        4: "五", 5: "六", 6: "日"
                    }
                    weekday = weekday_map[date_obj.weekday()]
                    headers.append(date_str)  # 只添加日期，周几通过UserRole设置
                except:
                    headers.append(date_str)
            
            self.kanban_table.setHorizontalHeaderLabels(headers)
            
            # 为日期列设置周几数据
            fixed_cols = 4
            for i, date_str in enumerate(date_range):
                col_index = fixed_cols + i
                header_item = self.kanban_table.horizontalHeaderItem(col_index)
                if header_item:
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        weekday_map = {
                            0: "一", 1: "二", 2: "三", 3: "四", 
                            4: "五", 5: "六", 6: "日"
                        }
                        weekday = weekday_map[date_obj.weekday()]
                        header_item.setData(Qt.UserRole, weekday)
                    except:
                        header_item.setData(Qt.UserRole, "")
            
            # 清空表格并设置行数
            self.kanban_table.clearContents()
            self.kanban_table.setRowCount(len(products))
            
            # 填充数据
            # 临时禁用所有信号
            self.kanban_table.blockSignals(True)
            
            for row, product in enumerate(products):
                # 固定列数据
                item_name = product.get("ItemName", "") or ""
                item_spec = product.get("ItemSpec", "") or ""
                item_brand = product.get("Brand", "") or ""
                project_name = product.get("ProjectName", "") or ""
                
                # 创建QTableWidgetItem并设置文本
                item0 = QTableWidgetItem()
                item0.setText(item_name)
                item1 = QTableWidgetItem()
                item1.setText(item_spec)
                item2 = QTableWidgetItem()
                item2.setText(item_brand)
                item3 = QTableWidgetItem()
                item3.setText(project_name)
                
                self.kanban_table.setItem(row, 0, item0)
                self.kanban_table.setItem(row, 1, item1)
                self.kanban_table.setItem(row, 2, item2)
                self.kanban_table.setItem(row, 3, item3)
                
                # 设置固定列不可编辑
                for col in range(fixed_cols):
                    item = self.kanban_table.item(row, col)
                    if item:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setBackground(QColor("#f8f9fa"))
                
                # 动态列数据（排产数量）
                for col, date_str in enumerate(date_range):
                    col_index = fixed_cols + col
                    qty = product["cells"].get(date_str, 0.0)
                    
                    item = QTableWidgetItem(str(qty))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    # 背景色将在set_sunday_column_backgrounds方法中统一设置
                    self.kanban_table.setItem(row, col_index, item)
            
            # 重新启用信号
            self.kanban_table.blockSignals(False)
            
            # 设置列宽和固定列效果
            header = self.kanban_table.horizontalHeader()
            
            # 设置固定列的宽度和调整模式
            for i in range(fixed_cols):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
                # 设置固定列的具体宽度
                if i == 0:  # 产品名称
                    self.kanban_table.setColumnWidth(i, 150)
                elif i == 1:  # 规格
                    self.kanban_table.setColumnWidth(i, 100)
                elif i == 2:  # 品牌
                    self.kanban_table.setColumnWidth(i, 80)
                elif i == 3:  # 项目名称
                    self.kanban_table.setColumnWidth(i, 120)
            
            # 设置日期列为固定宽度
            for c in range(fixed_cols, total_cols):
                header.setSectionResizeMode(c, QHeaderView.Fixed)
                self.kanban_table.setColumnWidth(c, 80)  # 增加列宽从64到80
            
            # 设置水平滚动模式
            self.kanban_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
            
            # 设置周日整列的单元格背景色
            self.set_sunday_column_backgrounds()
            
            # 刷新表格显示
            self.kanban_table.viewport().update()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载看板数据失败: {str(e)}")
    
    def set_sunday_column_backgrounds(self):
        """设置所有日期列的单元格背景色"""
        try:
            fixed_cols = 4
            col_count = self.kanban_table.columnCount()
            row_count = self.kanban_table.rowCount()
            
            for col in range(fixed_cols, col_count):
                # 检查是否是周日列
                header_item = self.kanban_table.horizontalHeaderItem(col)
                is_sunday = False
                if header_item:
                    weekday = header_item.data(Qt.UserRole)
                    is_sunday = weekday == "日"
                
                # 设置整列的单元格背景色
                for row in range(row_count):
                    item = self.kanban_table.item(row, col)
                    if item:
                        try:
                            qty = float(item.text() or 0)
                            if qty != 0:
                                # 有数量时显示绿色背景
                                item.setBackground(QColor("#d4edda"))  # 使用更柔和的绿色
                            elif is_sunday:
                                # 周日列且数量为0时显示黄色背景
                                item.setBackground(QColor("#fff3cd"))  # 使用更柔和的黄色
                            else:
                                # 非周日列且数量为0时显示白色背景
                                item.setBackground(QColor("#FFFFFF"))
                        except Exception as e:
                            print(f"解析数量失败: {e}, 文本: {item.text()}")
                            # 如果解析失败，根据是否周日设置背景色
                            if is_sunday:
                                item.setBackground(QColor("#fff3cd"))  # 使用更柔和的黄色
                            else:
                                item.setBackground(QColor("#FFFFFF"))
        except Exception as e:
            print(f"设置列背景色失败: {e}")
        
        # 刷新表格显示
        self.kanban_table.viewport().update()
    
    def clear_kanban_table(self):
        """清空看板表格"""
        self.kanban_table.clear()
        self.kanban_table.setRowCount(0)
        self.kanban_table.setColumnCount(0)
    
    def refresh_kanban_data(self):
        """刷新看板数据"""
        self.load_kanban_data()
    
    def on_kanban_item_changed(self, item):
        """看板单元格内容改变时的处理"""
        if item is None:
            return
        
        # 临时断开信号连接，避免递归
        self.kanban_table.itemChanged.disconnect(self.on_kanban_item_changed)
        
        try:
            # 获取单元格的值
            text = item.text().strip()
            if text == "":
                qty = 0.0
            else:
                qty = float(text)
            
            # 获取列索引
            col = item.column()
            fixed_cols = 4  # 前4列是固定列
            
            # 只处理日期列（非固定列）
            if col >= fixed_cols:
                # 检查是否是周日列
                header_item = self.kanban_table.horizontalHeaderItem(col)
                is_sunday = False
                if header_item:
                    weekday = header_item.data(Qt.UserRole)
                    is_sunday = weekday == "日"
                
                # 根据数量和是否周日设置背景色
                if qty != 0:
                    # 数量不为0时显示绿色背景
                    item.setBackground(QColor("#d4edda"))  # 使用更柔和的绿色
                elif is_sunday:
                    # 周日列且数量为0时显示黄色背景
                    item.setBackground(QColor("#fff3cd"))  # 使用更柔和的黄色
                else:
                    # 非周日列且数量为0时显示白色背景
                    item.setBackground(QColor("#FFFFFF"))
                        
        except ValueError:
            # 如果输入的不是有效数字，恢复为0
            item.setText("0")
            # 检查是否是周日列来决定背景色
            col = item.column()
            fixed_cols = 4
            if col >= fixed_cols:
                header_item = self.kanban_table.horizontalHeaderItem(col)
                is_sunday = False
                if header_item:
                    weekday = header_item.data(Qt.UserRole)
                    is_sunday = weekday == "日"
                
                if is_sunday:
                    item.setBackground(QColor("#fff3cd"))  # 使用更柔和的黄色
                else:
                    item.setBackground(QColor("#FFFFFF"))
        
        finally:
            # 重新连接信号
            self.kanban_table.itemChanged.connect(self.on_kanban_item_changed)
    
    def save_kanban_data(self):
        """保存看板数据"""
        if not hasattr(self, 'current_order_id') or not self.current_order_id:
            return
            
        try:
            # 获取看板数据
            data = SchedulingOrderService.get_scheduling_kanban_data(self.current_order_id)
            if "error" in data:
                QMessageBox.critical(self, "错误", data["error"])
                return
            
            date_range = data["date_range"]
            products = data["products"]
            fixed_cols = 4  # 前4列是固定列：产品名称、规格、品牌、项目名称
            
            # 收集更新的数据
            updates = []
            for row, product in enumerate(products):
                item_id = product["ItemId"]
                
                for col, date_str in enumerate(date_range):
                    col_index = fixed_cols + col
                    item = self.kanban_table.item(row, col_index)
                    
                    if item:
                        try:
                            planned_qty = float(item.text() or 0)
                            updates.append({
                                "ItemId": item_id,
                                "ProductionDate": date_str,
                                "PlannedQty": planned_qty
                            })
                        except ValueError:
                            QMessageBox.warning(self, "警告", f"第{row+1}行第{col+1}列的数据格式不正确")
                            return
            
            # 批量更新
            success, message = SchedulingOrderService.batch_update_scheduling_lines(
                self.current_order_id, updates
            )
            
            if success:
                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.critical(self, "错误", message)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存看板数据失败: {str(e)}")
    
    def load_orders(self):
        """加载排产订单列表"""
        try:
            orders = SchedulingOrderService.get_scheduling_orders()
            
            self.order_table.setRowCount(len(orders))
            for row, order in enumerate(orders):
                self.order_table.setItem(row, 0, QTableWidgetItem(str(order["OrderId"])))
                self.order_table.setItem(row, 1, QTableWidgetItem(order["OrderName"]))
                self.order_table.setItem(row, 2, QTableWidgetItem(order["StartDate"]))
                self.order_table.setItem(row, 3, QTableWidgetItem(order["EndDate"]))
                
                # 状态列设置颜色
                status_item = QTableWidgetItem(order["Status"])
                if order["Status"] == "Draft":
                    status_item.setBackground(QColor("#fff3cd"))
                elif order["Status"] == "Active":
                    status_item.setBackground(QColor("#d4edda"))
                elif order["Status"] == "Completed":
                    status_item.setBackground(QColor("#d1ecf1"))
                elif order["Status"] == "Cancelled":
                    status_item.setBackground(QColor("#f8d7da"))
                self.order_table.setItem(row, 4, status_item)
                
                self.order_table.setItem(row, 5, QTableWidgetItem(order["CreatedBy"] or ""))
                self.order_table.setItem(row, 6, QTableWidgetItem(order["CreatedDate"]))
                self.order_table.setItem(row, 7, QTableWidgetItem(order["Remark"] or ""))
                
                # 操作按钮
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(8, 4, 8, 4)
                button_layout.setSpacing(6)
                
                # 查看按钮
                view_btn = QPushButton("查看")
                view_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #17a2b8;
                        color: white;
                        border: none;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                        min-width: 50px;
                    }
                    QPushButton:hover {
                        background-color: #138496;
                    }
                    QPushButton:pressed {
                        background-color: #117a8b;
                    }
                """)
                view_btn.clicked.connect(lambda checked, order_id=order['OrderId']: self.view_order_details(order_id))
                button_layout.addWidget(view_btn)
                
                
                # 编辑按钮
                edit_btn = QPushButton("编辑")
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffc107;
                        color: black;
                        border: none;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                        min-width: 50px;
                    }
                    QPushButton:hover {
                        background-color: #e0a800;
                    }
                    QPushButton:pressed {
                        background-color: #d39e00;
                    }
                """)
                edit_btn.clicked.connect(lambda checked, order_id=order['OrderId']: self.edit_order(order_id))
                button_layout.addWidget(edit_btn)
                
                # 删除按钮
                delete_btn = QPushButton("删除")
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #dc3545;
                        color: white;
                        border: none;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                        min-width: 50px;
                    }
                    QPushButton:hover {
                        background-color: #c82333;
                    }
                    QPushButton:pressed {
                        background-color: #bd2130;
                    }
                """)
                delete_btn.clicked.connect(lambda checked, order_id=order['OrderId']: self.delete_order(order_id))
                button_layout.addWidget(delete_btn)
                
                self.order_table.setCellWidget(row, 8, button_widget)
            
            self.order_table.resizeRowsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载订单列表失败: {str(e)}")
    
    def create_new_order(self):
        """创建新的排产订单"""
        dialog = CreateOrderDialog(self)
        if dialog.exec() == QDialog.Accepted:
            order_data = dialog.get_order_data()
            
            if not order_data["order_name"]:
                QMessageBox.warning(self, "警告", "请输入订单名称")
                return
            
            if not order_data["selected_products"]:
                QMessageBox.warning(self, "警告", "请至少选择一个成品物料")
                return
            
            # 创建排产订单
            success, message, order_id = SchedulingOrderService.create_scheduling_order(
                order_data["order_name"],
                order_data["start_date"],
                order_data["end_date"],
                "System",
                order_data["remark"]
            )
            
            if success:
                # 添加选中的产品到订单
                product_ids = [p['ItemId'] for p in order_data["selected_products"]]
                add_success, add_message = SchedulingOrderService.add_products_to_order(
                    order_id, product_ids
                )
                
                if add_success:
                    QMessageBox.information(self, "成功", f"{message}\n{add_message}")
                    self.load_orders()
                else:
                    QMessageBox.warning(self, "部分成功", f"{message}\n但添加产品失败: {add_message}")
                    self.load_orders()
            else:
                QMessageBox.critical(self, "错误", message)
    
    def on_order_selected(self):
        """订单选择事件 - 取消自动跳转到详情页"""
        current_row = self.order_table.currentRow()
        if current_row >= 0:
            order_id = int(self.order_table.item(current_row, 0).text())
            self.current_order_id = order_id
            # 不再自动跳转到详情页，用户需要点击"查看"按钮
        else:
            self.current_order_id = None
    
    
    def calculate_mrp(self):
        """计算MRP"""
        if not hasattr(self, 'current_order_id') or not self.current_order_id:
            return
        
        try:
            from app.ui.scheduling_mrp_calculation import SchedulingMRPDialog
            dialog = SchedulingMRPDialog(self.current_order_id, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开MRP计算界面失败: {str(e)}")
    
    def view_order_details(self, order_id):
        """查看订单详情"""
        # 切换到详情页签
        self.tab_widget.setCurrentIndex(1)
        # 设置订单选择下拉框为当前订单
        for i in range(self.order_selection_combo.count()):
            if self.order_selection_combo.itemData(i) == order_id:
                self.order_selection_combo.setCurrentIndex(i)
                break
    
    
    def edit_order(self, order_id):
        """编辑订单基础信息"""
        try:
            # 获取订单信息
            orders = SchedulingOrderService.get_scheduling_orders()
            order_info = None
            for order in orders:
                if order['OrderId'] == order_id:
                    order_info = order
                    break
            
            if not order_info:
                QMessageBox.critical(self, "错误", "找不到指定的订单信息")
                return
            
            # 打开编辑对话框
            dialog = EditOrderDialog(order_info, self)
            if dialog.exec() == QDialog.Accepted:
                updated_data = dialog.get_order_data()
                
                # 更新订单基础信息
                success, message = SchedulingOrderService.update_scheduling_order(
                    order_id,
                    updated_data["order_name"],
                    updated_data["start_date"],
                    updated_data["end_date"],
                    updated_data["remark"]
                )
                
                if success:
                    # 检查是否需要更新产品列表
                    if updated_data["selected_products"]:
                        # 获取当前订单的产品ID列表
                        current_products = SchedulingOrderService.get_order_products(order_id)
                        current_product_ids = [p['ItemId'] for p in current_products]
                        new_product_ids = [p['ItemId'] for p in updated_data["selected_products"]]
                        
                        # 如果产品列表有变化，需要更新
                        if set(current_product_ids) != set(new_product_ids):
                            # 先删除所有现有产品
                            SchedulingOrderService.remove_all_products_from_order(order_id)
                            # 再添加新产品
                            SchedulingOrderService.add_products_to_order(order_id, new_product_ids)
                    
                    QMessageBox.information(self, "成功", "订单信息更新成功")
                    self.load_orders()
                    self.load_order_selection()  # 刷新订单选择下拉框
                    
                    # 如果当前正在查看这个订单的详情，需要重新加载
                    if hasattr(self, 'current_order_id') and self.current_order_id == order_id:
                        self.load_kanban_data()
                else:
                    QMessageBox.critical(self, "错误", message)
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑订单失败: {str(e)}")
    
    def delete_order(self, order_id):
        """删除订单"""
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这个排产订单吗？删除后将无法恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = SchedulingOrderService.delete_scheduling_order(order_id)
            
            if success:
                QMessageBox.information(self, "成功", message)
                self.load_orders()
            else:
                QMessageBox.critical(self, "错误", message)


class CreateOrderDialog(QDialog):
    """创建排产订单对话框 - 美化版本"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建排产订单")
        self.setModal(True)
        self.resize(600, 700)
        self.setMinimumSize(500, 600)
        self.init_ui()
        self.load_products()
    
    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # 标题
        title_label = QLabel("新建排产订单")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 5px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 表单区域
        form_layout = QVBoxLayout()
        
        # 订单名称
        name_group = QGroupBox("订单信息")
        name_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #495057;
                border: 1px solid #ccc;
                margin-top: 5px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 5px;
                padding: 0 3px 0 3px;
            }
        """)
        name_layout = QFormLayout(name_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入排产订单名称")
        self.name_edit.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        """)
        name_layout.addRow("订单名称 *:", self.name_edit)
        
        # 日期选择
        date_layout = QHBoxLayout()
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setStyleSheet("""
            QDateEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QDateEdit:focus {
                border-color: #007bff;
            }
        """)
        self.start_date_edit.dateChanged.connect(self.update_end_date)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setStyleSheet("""
            QDateEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QDateEdit:focus {
                border-color: #007bff;
            }
        """)
        # 结束日期可以手动修改，默认是一个月后
        
        # 初始化结束日期
        self.update_end_date()
        
        date_layout.addWidget(QLabel("开始日期 *:"))
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(QLabel("结束日期:"))
        date_layout.addWidget(self.end_date_edit)
        name_layout.addRow(date_layout)
        
        # 备注
        self.remark_edit = QTextEdit()
        self.remark_edit.setPlaceholderText("请输入备注信息（可选）")
        self.remark_edit.setMaximumHeight(60)
        self.remark_edit.setStyleSheet("""
            QTextEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #007bff;
            }
        """)
        name_layout.addRow("备注:", self.remark_edit)
        
        form_layout.addWidget(name_group)
        
        # 产品选择区域
        product_group = QGroupBox("选择成品物料")
        product_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #495057;
                border: 1px solid #ccc;
                margin-top: 5px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 5px;
                padding: 0 3px 0 3px;
            }
        """)
        product_layout = QVBoxLayout(product_group)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入产品编码或名称进行搜索...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        """)
        self.search_edit.textChanged.connect(self.filter_products)
        search_layout.addWidget(self.search_edit)
        product_layout.addLayout(search_layout)
        
        # 产品列表 - 使用QTableWidget替代QListWidget以支持复选框
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(2)
        self.product_table.setHorizontalHeaderLabels(["选择", "产品信息"])
        self.product_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 4px;
                border: none;
                font-weight: bold;
            }
        """)
        self.product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.product_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.product_table.setMaximumHeight(250)
        self.product_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        product_layout.addWidget(self.product_table)
        
        # 产品操作按钮
        product_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.select_all_btn.clicked.connect(self.select_all_products)
        product_btn_layout.addWidget(self.select_all_btn)
        
        self.clear_selection_btn = QPushButton("清空选择")
        self.clear_selection_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.clear_selection_btn.clicked.connect(self.clear_product_selection)
        product_btn_layout.addWidget(self.clear_selection_btn)
        
        product_btn_layout.addStretch()
        product_layout.addLayout(product_btn_layout)
        
        form_layout.addWidget(product_group)
        main_layout.addLayout(form_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("创建订单")
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.ok_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(button_layout)
    
    def load_products(self):
        """加载可排产的产品列表"""
        try:
            products = SchedulingOrderService.get_available_products()
            self.all_products = products
            
            self.product_table.setRowCount(len(products))
            
            for row, product in enumerate(products):
                # 复选框
                checkbox = QCheckBox()
                self.product_table.setCellWidget(row, 0, checkbox)
                
                # 产品信息
                item_text = f"{product['ItemCode']} - {product['CnName']}"
                if product.get('ItemSpec'):
                    item_text += f" ({product['ItemSpec']})"
                if product.get('Brand'):
                    item_text += f" [品牌: {product['Brand']}]"
                if product.get('ProjectName'):
                    item_text += f" [项目: {product['ProjectName']}]"
                
                item = QTableWidgetItem(item_text)
                item.setData(Qt.UserRole, product)
                self.product_table.setItem(row, 1, item)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载产品列表失败: {str(e)}")
    
    def filter_products(self, text):
        """过滤产品列表"""
        for row in range(self.product_table.rowCount()):
            item = self.product_table.item(row, 1)
            if item:
                product = item.data(Qt.UserRole)
                if product:
                    item_text = f"{product['ItemCode']} - {product['CnName']}"
                    if product.get('ItemSpec'):
                        item_text += f" ({product['ItemSpec']})"
                    if product.get('Brand'):
                        item_text += f" [品牌: {product['Brand']}]"
                    if product.get('ProjectName'):
                        item_text += f" [项目: {product['ProjectName']}]"
                    
                    self.product_table.setRowHidden(row, text.lower() not in item_text.lower())
    
    def select_all_products(self):
        """全选产品"""
        for row in range(self.product_table.rowCount()):
            if not self.product_table.isRowHidden(row):
                checkbox = self.product_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    def clear_product_selection(self):
        """清空产品选择"""
        for row in range(self.product_table.rowCount()):
            checkbox = self.product_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def update_end_date(self):
        """更新结束日期（开始日期后1个月）"""
        start_date = self.start_date_edit.date()
        end_date = start_date.addDays(30)  # 添加30天
        self.end_date_edit.setDate(end_date)
    
    def get_order_data(self):
        """获取订单数据"""
        selected_products = []
        for row in range(self.product_table.rowCount()):
            checkbox = self.product_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # 从表格项中获取产品数据
                item = self.product_table.item(row, 1)
                if item:
                    product = item.data(Qt.UserRole)
                    selected_products.append(product)
        
        return {
            "order_name": self.name_edit.text().strip(),
            "start_date": self.start_date_edit.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date_edit.date().toString("yyyy-MM-dd"),
            "remark": self.remark_edit.toPlainText().strip(),
            "selected_products": selected_products
        }
    
    def accept(self):
        """确认创建"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入订单名称")
            return
        
        super().accept()


class EditOrderDialog(QDialog):
    """编辑排产订单对话框"""
    
    def __init__(self, order_info, parent=None):
        super().__init__(parent)
        self.order_info = order_info
        self.setWindowTitle("编辑排产订单")
        self.setModal(True)
        self.resize(600, 700)
        self.setMinimumSize(500, 600)
        self.init_ui()
        self.load_current_data()
    
    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # 标题
        title_label = QLabel("编辑排产订单")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 5px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 表单区域
        form_layout = QVBoxLayout()
        
        # 订单名称
        name_group = QGroupBox("订单信息")
        name_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #495057;
                border: 1px solid #ccc;
                margin-top: 5px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 5px;
                padding: 0 3px 0 3px;
            }
        """)
        name_layout = QFormLayout(name_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入排产订单名称")
        self.name_edit.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        """)
        name_layout.addRow("订单名称 *:", self.name_edit)
        
        # 日期选择
        date_layout = QHBoxLayout()
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setStyleSheet("""
            QDateEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QDateEdit:focus {
                border-color: #007bff;
            }
        """)
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setStyleSheet("""
            QDateEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QDateEdit:focus {
                border-color: #007bff;
            }
        """)
        
        date_layout.addWidget(QLabel("开始日期 *:"))
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(QLabel("结束日期 *:"))
        date_layout.addWidget(self.end_date_edit)
        name_layout.addRow(date_layout)
        
        # 备注
        self.remark_edit = QTextEdit()
        self.remark_edit.setPlaceholderText("请输入备注信息（可选）")
        self.remark_edit.setMaximumHeight(60)
        self.remark_edit.setStyleSheet("""
            QTextEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #007bff;
            }
        """)
        name_layout.addRow("备注:", self.remark_edit)
        
        form_layout.addWidget(name_group)
        
        # 产品选择区域
        product_group = QGroupBox("选择成品物料")
        product_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #495057;
                border: 1px solid #ccc;
                margin-top: 5px;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 5px;
                padding: 0 3px 0 3px;
            }
        """)
        product_layout = QVBoxLayout(product_group)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入产品编码或名称进行搜索...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 4px 8px;
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        """)
        self.search_edit.textChanged.connect(self.filter_products)
        search_layout.addWidget(self.search_edit)
        product_layout.addLayout(search_layout)
        
        # 产品列表
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(2)
        self.product_table.setHorizontalHeaderLabels(["选择", "产品信息"])
        self.product_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 4px;
                border: none;
                font-weight: bold;
            }
        """)
        self.product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.product_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.product_table.setMaximumHeight(250)
        self.product_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        product_layout.addWidget(self.product_table)
        
        # 产品操作按钮
        product_btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.select_all_btn.clicked.connect(self.select_all_products)
        product_btn_layout.addWidget(self.select_all_btn)
        
        self.clear_selection_btn = QPushButton("清空选择")
        self.clear_selection_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.clear_selection_btn.clicked.connect(self.clear_product_selection)
        product_btn_layout.addWidget(self.clear_selection_btn)
        
        product_btn_layout.addStretch()
        product_layout.addLayout(product_btn_layout)
        
        form_layout.addWidget(product_group)
        main_layout.addLayout(form_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("保存修改")
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.ok_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(button_layout)
    
    def load_current_data(self):
        """加载当前订单数据"""
        try:
            # 设置基本信息
            self.name_edit.setText(self.order_info['OrderName'])
            
            # 设置日期
            from datetime import datetime
            start_date = datetime.strptime(self.order_info['StartDate'], "%Y-%m-%d").date()
            end_date = datetime.strptime(self.order_info['EndDate'], "%Y-%m-%d").date()
            self.start_date_edit.setDate(QDate(start_date.year, start_date.month, start_date.day))
            self.end_date_edit.setDate(QDate(end_date.year, end_date.month, end_date.day))
            
            # 设置备注
            self.remark_edit.setPlainText(self.order_info.get('Remark', ''))
            
            # 加载产品列表
            products = SchedulingOrderService.get_available_products()
            self.all_products = products
            
            # 获取当前订单的产品
            current_products = SchedulingOrderService.get_order_products(self.order_info['OrderId'])
            current_product_ids = {p['ItemId'] for p in current_products}
            
            self.product_table.setRowCount(len(products))
            
            for row, product in enumerate(products):
                # 复选框
                checkbox = QCheckBox()
                # 如果当前产品在订单中，则选中
                if product['ItemId'] in current_product_ids:
                    checkbox.setChecked(True)
                self.product_table.setCellWidget(row, 0, checkbox)
                
                # 产品信息
                item_text = f"{product['ItemCode']} - {product['CnName']}"
                if product.get('ItemSpec'):
                    item_text += f" ({product['ItemSpec']})"
                if product.get('Brand'):
                    item_text += f" [品牌: {product['Brand']}]"
                if product.get('ProjectName'):
                    item_text += f" [项目: {product['ProjectName']}]"
                
                item = QTableWidgetItem(item_text)
                item.setData(Qt.UserRole, product)
                self.product_table.setItem(row, 1, item)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载订单数据失败: {str(e)}")
    
    def filter_products(self, text):
        """过滤产品列表"""
        for row in range(self.product_table.rowCount()):
            item = self.product_table.item(row, 1)
            if item:
                product = item.data(Qt.UserRole)
                if product:
                    item_text = f"{product['ItemCode']} - {product['CnName']}"
                    if product.get('ItemSpec'):
                        item_text += f" ({product['ItemSpec']})"
                    if product.get('Brand'):
                        item_text += f" [品牌: {product['Brand']}]"
                    if product.get('ProjectName'):
                        item_text += f" [项目: {product['ProjectName']}]"
                    
                    self.product_table.setRowHidden(row, text.lower() not in item_text.lower())
    
    def select_all_products(self):
        """全选产品"""
        for row in range(self.product_table.rowCount()):
            if not self.product_table.isRowHidden(row):
                checkbox = self.product_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    def clear_product_selection(self):
        """清空产品选择"""
        for row in range(self.product_table.rowCount()):
            checkbox = self.product_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def get_order_data(self):
        """获取订单数据"""
        selected_products = []
        for row in range(self.product_table.rowCount()):
            checkbox = self.product_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # 从表格项中获取产品数据
                item = self.product_table.item(row, 1)
                if item:
                    product = item.data(Qt.UserRole)
                    selected_products.append(product)
        
        return {
            "order_name": self.name_edit.text().strip(),
            "start_date": self.start_date_edit.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date_edit.date().toString("yyyy-MM-dd"),
            "remark": self.remark_edit.toPlainText().strip(),
            "selected_products": selected_products
        }
    
    def accept(self):
        """确认修改"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入订单名称")
            return
        
        super().accept()
