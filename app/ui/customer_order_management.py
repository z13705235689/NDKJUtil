#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户订单管理界面
"""

import sys
import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QLabel,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QComboBox, QLineEdit, QGroupBox, QGridLayout, QTextEdit,
    QProgressBar, QFrame, QSplitter, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QDate, QTimer
from PySide6.QtGui import QFont, QColor

from app.services.customer_order_service import CustomerOrderService

class OrderImportThread(QThread):
    """订单导入线程"""
    progress_signal = Signal(str)
    finished_signal = Signal(dict)
    
    def __init__(self, file_path, file_name):
        super().__init__()
        self.file_path = file_path
        self.file_name = file_name
    
    def run(self):
        try:
            self.progress_signal.emit("开始解析文件...")
            result = CustomerOrderService.import_orders_from_file(self.file_path, self.file_name)
            self.finished_signal.emit(result)
        except Exception as e:
            self.finished_signal.emit({
                'success': False,
                'message': f'导入失败: {str(e)}',
                'order_count': 0,
                'line_count': 0
            })

class CustomerOrderManagement(QWidget):
    """客户订单管理界面"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # 定时刷新数据
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)  # 30秒刷新一次
        
        # 延迟加载数据，确保界面完全初始化
        QTimer.singleShot(100, self.load_data)
        QTimer.singleShot(200, self.load_version_list)  # 延迟加载版本列表
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("客户订单管理")
        self.setMinimumSize(1200, 800)  # 调整最小尺寸
        self.setMaximumSize(1600, 1000)  # 设置最大尺寸限制
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)  # 减少间距
        main_layout.setContentsMargins(10, 10, 10, 10)  # 减少边距
        
        # 标题
        title_label = QLabel("客户订单管理系统")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))  # 减小字体
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin: 5px;")  # 减少边距
        main_layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 订单看板标签页
        self.kanban_tab = self.create_kanban_tab()
        self.tab_widget.addTab(self.kanban_tab, "订单看板")
        
        # 订单管理标签页
        self.order_tab = self.create_order_tab()
        self.tab_widget.addTab(self.order_tab, "订单管理")
        
        # 文件导入标签页
        self.import_tab = self.create_import_tab()
        self.tab_widget.addTab(self.import_tab, "文件导入")
        
        # 导入历史标签页
        self.history_tab = self.create_history_tab()
        self.tab_widget.addTab(self.history_tab, "导入历史")
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
    
    def create_kanban_tab(self):
        """创建订单看板标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)  # 减少间距
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距
        
        # 筛选控制面板
        filter_group = QGroupBox("筛选条件")
        filter_group.setMaximumHeight(100)  # 增加高度以容纳版本选择
        filter_layout = QGridLayout()
        filter_layout.setSpacing(3)  # 进一步减少间距
        filter_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距
        
        # 版本选择
        version_layout = QHBoxLayout()
        version_layout.setSpacing(2)  # 最小间距
        version_layout.addWidget(QLabel("订单版本:"))
        self.version_combo = QComboBox()
        self.version_combo.addItem("全部版本")
        self.version_combo.setMaximumWidth(120)
        self.version_combo.currentTextChanged.connect(self.on_version_changed)
        version_layout.addWidget(self.version_combo)
        filter_layout.addLayout(version_layout, 0, 0)
        
        # 日期范围 - 使用水平布局减少间距
        date_layout1 = QHBoxLayout()
        date_layout1.setSpacing(2)  # 最小间距
        date_layout1.addWidget(QLabel("开始日期:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setMaximumWidth(100)
        date_layout1.addWidget(self.start_date_edit)
        filter_layout.addLayout(date_layout1, 0, 2)
        
        date_layout2 = QHBoxLayout()
        date_layout2.setSpacing(2)  # 最小间距
        date_layout2.addWidget(QLabel("结束日期:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate().addDays(90))
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setMaximumWidth(100)
        date_layout2.addWidget(self.end_date_edit)
        filter_layout.addLayout(date_layout2, 1, 0)
        
        # 订单类型
        type_layout = QHBoxLayout()
        type_layout.setSpacing(2)  # 最小间距
        type_layout.addWidget(QLabel("订单类型:"))
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["全部", "正式订单(F)", "预测订单(P)"])
        self.order_type_combo.setMaximumWidth(100)
        type_layout.addWidget(self.order_type_combo)
        filter_layout.addLayout(type_layout, 1, 2)
        
        # 产品型号
        item_layout = QHBoxLayout()
        item_layout.setSpacing(2)  # 最小间距
        item_layout.addWidget(QLabel("产品型号:"))
        self.item_number_edit = QLineEdit()
        self.item_number_edit.setPlaceholderText("输入产品型号进行筛选")
        self.item_number_edit.setMaximumWidth(120)
        item_layout.addWidget(self.item_number_edit)
        filter_layout.addLayout(item_layout, 2, 0)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新数据")
        refresh_btn.clicked.connect(self.refresh_kanban_data)
        refresh_btn.setMaximumWidth(80)
        filter_layout.addWidget(refresh_btn, 2, 2)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # 看板显示区域
        kanban_group = QGroupBox("订单看板 - 可视化视图")
        kanban_layout = QVBoxLayout()
        kanban_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建看板表格 - 透视表样式
        self.kanban_table = QTableWidget()
        self.setup_kanban_table()

        # 设置表格大小策略
        self.kanban_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        kanban_layout.addWidget(self.kanban_table)
        kanban_group.setLayout(kanban_layout)
        layout.addWidget(kanban_group)
        
        widget.setLayout(layout)
        return widget
    
    def setup_kanban_table(self):
        """设置看板表格为透视表样式"""
        # 设置表格样式
        self.kanban_table.setAlternatingRowColors(True)
        self.kanban_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.kanban_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 设置表头样式
        header = self.kanban_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignCenter)
        
        # 设置行头样式
        row_header = self.kanban_table.verticalHeader()
        row_header.setDefaultAlignment(Qt.AlignCenter)
        row_header.setVisible(True)
    
    def create_order_tab(self):
        """创建订单管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)  # 减少间距
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距
        
        # 筛选控制
        filter_group = QGroupBox("筛选条件")
        filter_group.setMaximumHeight(70)  # 限制高度
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)  # 减少间距
        filter_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距
        
        filter_layout.addWidget(QLabel("日期范围:"))
        
        self.order_start_date = QDateEdit()
        self.order_start_date.setDate(QDate.currentDate().addDays(-30))
        self.order_start_date.setCalendarPopup(True)
        self.order_start_date.setMaximumWidth(100)  # 限制宽度
        filter_layout.addWidget(self.order_start_date)
        
        filter_layout.addWidget(QLabel("至"))
        
        self.order_end_date = QDateEdit()
        self.order_end_date.setDate(QDate.currentDate().addDays(90))
        self.order_end_date.setCalendarPopup(True)
        self.order_end_date.setMaximumWidth(100)  # 限制宽度
        filter_layout.addWidget(self.order_end_date)
        
        search_btn = QPushButton("查询订单")
        search_btn.clicked.connect(self.search_orders)
        search_btn.setMaximumWidth(80)  # 限制宽度
        filter_layout.addWidget(search_btn)
        
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # 订单表格
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(13)  # 增加一列用于操作按钮
        self.order_table.setHorizontalHeaderLabels([
            "订单号", "供应商", "客户", "发布日期", "产品型号", "产品描述", 
            "交货日期", "日历周", "订单类型", "需求数量", "累计数量", "净需求数量", "操作"
        ])
        
        # 设置表格样式
        header = self.order_table.horizontalHeader()
        # 设置关键列的宽度
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 订单号
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 供应商
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 客户
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 发布日期
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 产品型号
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # 产品描述 - 自适应
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 交货日期
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 日历周
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # 订单类型
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # 需求数量
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents) # 累计数量
        header.setSectionResizeMode(11, QHeaderView.ResizeToContents) # 净需求数量
        header.setSectionResizeMode(12, QHeaderView.ResizeToContents) # 操作
        
        layout.addWidget(self.order_table)
        widget.setLayout(layout)
        return widget
    
    def create_import_tab(self):
        """创建文件导入标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 文件选择区域
        file_group = QGroupBox("选择订单文件")
        file_layout = QVBoxLayout()
        
        # 文件路径显示
        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setStyleSheet("padding: 10px; border: 1px solid #bdc3c7; background-color: #ecf0f1;")
        file_layout.addWidget(self.file_path_label)
        
        # 文件选择按钮
        file_btn_layout = QHBoxLayout()
        select_file_btn = QPushButton("选择TXT文件")
        select_file_btn.clicked.connect(self.select_file)
        file_btn_layout.addWidget(select_file_btn)
        
        self.import_btn = QPushButton("开始导入")
        self.import_btn.clicked.connect(self.start_import)
        self.import_btn.setEnabled(False)
        file_btn_layout.addWidget(self.import_btn)
        
        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 导入进度
        progress_group = QGroupBox("导入进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("准备就绪")
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 导入结果
        result_group = QGroupBox("导入结果")
        result_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)
        result_layout.addWidget(self.result_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_history_tab(self):
        """创建导入历史标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "导入ID", "文件名", "导入日期", "订单数量", "明细数量", "状态", "错误信息", "导入用户"
        ])
        
        # 设置表格样式
        header = self.history_table.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.history_table)
        widget.setLayout(layout)
        return widget
    
    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择订单文件", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            self.file_path_label.setText(file_path)
            self.import_btn.setEnabled(True)
    
    def start_import(self):
        """开始导入"""
        file_path = self.file_path_label.text()
        if file_path == "未选择文件":
            QMessageBox.warning(self, "警告", "请先选择文件！")
            return
        
        # 获取文件名
        file_name = os.path.basename(file_path)
        
        # 禁用导入按钮
        self.import_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("正在导入...")
        
        # 创建导入线程
        self.import_thread = OrderImportThread(file_path, file_name)
        self.import_thread.progress_signal.connect(self.update_progress)
        self.import_thread.finished_signal.connect(self.import_finished)
        self.import_thread.start()
    
    def update_progress(self, message):
        """更新进度信息"""
        self.progress_label.setText(message)
    
    def import_finished(self, result):
        """导入完成"""
        self.import_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if result['success']:
            self.progress_label.setText("导入完成")
            self.result_text.append(f"✅ {result['message']}")
            
            # 刷新数据
            self.load_data()
            self.load_version_list() # 刷新版本列表
            
            QMessageBox.information(self, "成功", result['message'])
        else:
            self.progress_label.setText("导入失败")
            self.result_text.append(f"❌ {result['message']}")
            
            QMessageBox.critical(self, "错误", result['message'])
    
    def load_data(self):
        """加载数据"""
        self.load_kanban_data()
        self.load_order_data()
        self.load_history_data()
    
    def load_kanban_data(self):
        """加载看板数据"""
        try:
            print("🔍 开始加载看板数据...")
            
            # 获取筛选条件
            start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
            end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
            order_type = self.order_type_combo.currentText()
            version_id = self.get_selected_version_id()
            
            print(f"   筛选条件: {start_date} 到 {end_date}, 类型: {order_type}, 版本: {version_id}")
            
            # 转换订单类型
            if order_type == "正式订单(F)":
                order_type = "F"
            elif order_type == "预测订单(P)":
                order_type = "P"
            else:
                order_type = "All"
            
            # 获取产品型号筛选
            item_number = self.item_number_edit.text().strip()
            if not item_number:
                item_number = None
            
            print(f"   产品型号筛选: {item_number}")
            
            # 获取透视表数据
            data = CustomerOrderService.get_orders_pivot_data(
                start_date, end_date, order_type, item_number, version_id
            )
            
            print(f"   获取到数据: 产品={len(data['items'])}, 周数={len(data['weeks'])}, 透视数据={len(data['pivot_data'])}")
            
            if not data['items'] or not data['weeks']:
                print("   ⚠️ 没有找到数据，清空表格")
                self.kanban_table.setRowCount(0)
                self.kanban_table.setColumnCount(0)
                return
            
            # 设置表格列数和行数
            # 列：PN产品编码 + Purchase Order + 订单类型 + 每个周的数量列 + 总计列
            col_count = 3 + len(data['weeks']) + 1  # PN + PO + 订单类型 + 周数 + 总计
            row_count = len(data['items']) * 2  # 每个产品显示正式订单和预测订单两行
            
            print(f"   设置表格: {col_count} 列 x {row_count} 行")
            
            self.kanban_table.setColumnCount(col_count)
            self.kanban_table.setRowCount(row_count)
            
            # 设置表头
            headers = ["PN产品编码", "Purchase Order", "订单类型"]
            for week in data['weeks']:
                headers.append(f"{week['CalendarWeek']}\n{week['DeliveryDate']}")
            headers.append("总计")
            
            self.kanban_table.setHorizontalHeaderLabels(headers)
            print(f"   设置表头完成: {len(headers)} 列")
            
            # 设置列宽
            header = self.kanban_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # PN产品编码
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Purchase Order
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 订单类型
            
            # 设置周数列宽
            for i in range(3, col_count - 1):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
            header.setSectionResizeMode(col_count - 1, QHeaderView.ResizeToContents)  # 总计列
            
            # 填充数据
            row_index = 0
            for item in data['items']:
                item_num = item['ItemNumber']
                item_desc = item['ItemDescription']
                
                print(f"   处理产品: {item_num}")
                
                # 正式订单行
                self.kanban_table.setItem(row_index, 0, QTableWidgetItem(item_num))
                self.kanban_table.setItem(row_index, 1, QTableWidgetItem("嘉兴牛大"))  # 默认供应商
                
                type_item = QTableWidgetItem("正式订单")
                type_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                self.kanban_table.setItem(row_index, 2, type_item)
                
                # 填充每周的数量
                total_qty = 0
                for col_idx, week in enumerate(data['weeks']):
                    week_data = data['pivot_data'].get(item_num, {}).get(week['CalendarWeek'], {})
                    qty = week_data.get('F', 0)
                    total_qty += qty
                    
                    cell_item = QTableWidgetItem(str(int(qty)) if qty > 0 else "")
                    if qty > 0:
                        cell_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                    self.kanban_table.setItem(row_index, col_idx + 3, cell_item)
                
                # 总计列
                total_item = QTableWidgetItem(str(int(total_qty)) if total_qty > 0 else "")
                total_item.setFont(QFont("Arial", 10, QFont.Bold))
                if total_qty > 0:
                    total_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                self.kanban_table.setItem(row_index, col_count - 1, total_item)
                
                row_index += 1
                
                # 预测订单行
                self.kanban_table.setItem(row_index, 0, QTableWidgetItem(item_num))
                self.kanban_table.setItem(row_index, 1, QTableWidgetItem("嘉兴牛大"))  # 默认供应商
                
                type_item = QTableWidgetItem("预测订单")
                type_item.setBackground(QColor(255, 255, 224))  # 浅黄色
                self.kanban_table.setItem(row_index, 2, type_item)
                
                # 填充每周的数量
                total_qty = 0
                for col_idx, week in enumerate(data['weeks']):
                    week_data = data['pivot_data'].get(item_num, {}).get(week['CalendarWeek'], {})
                    qty = week_data.get('P', 0)
                    total_qty += qty
                    
                    cell_item = QTableWidgetItem(str(int(qty)) if qty > 0 else "")
                    if qty > 0:
                        cell_item.setBackground(QColor(255, 255, 224))  # 浅黄色
                    self.kanban_table.setItem(row_index, col_idx + 3, cell_item)
                
                # 总计列
                total_item = QTableWidgetItem(str(int(total_qty)) if total_qty > 0 else "")
                total_item.setFont(QFont("Arial", 10, QFont.Bold))
                if total_qty > 0:
                    total_item.setBackground(QColor(255, 255, 224))  # 浅黄色
                self.kanban_table.setItem(row_index, col_count - 1, total_item)
                
                row_index += 1
            
            print(f"   ✅ 看板数据加载完成，共 {row_count} 行数据")
            
        except Exception as e:
            print(f"❌ 加载看板数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def load_order_data(self):
        """加载订单数据"""
        try:
            start_date = self.order_start_date.date().toString("yyyy-MM-dd")
            end_date = self.order_end_date.date().toString("yyyy-MM-dd")
            
            data = CustomerOrderService.get_orders_by_date_range(start_date, end_date)
            
            # 填充表格
            self.order_table.setRowCount(len(data))
            
            for row, item in enumerate(data):
                self.order_table.setItem(row, 0, QTableWidgetItem(item['OrderNumber']))
                self.order_table.setItem(row, 1, QTableWidgetItem(item['SupplierName']))
                self.order_table.setItem(row, 2, QTableWidgetItem(item['CustomerName']))
                self.order_table.setItem(row, 3, QTableWidgetItem(item['ReleaseDate']))
                self.order_table.setItem(row, 4, QTableWidgetItem(item['ItemNumber']))
                self.order_table.setItem(row, 5, QTableWidgetItem(item['ItemDescription']))
                self.order_table.setItem(row, 6, QTableWidgetItem(item['DeliveryDate']))
                self.order_table.setItem(row, 7, QTableWidgetItem(item['CalendarWeek']))
                
                # 订单类型（带颜色标识）
                type_item = QTableWidgetItem(item['OrderType'])
                if item['OrderType'] == 'F':
                    type_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                    type_item.setText("正式订单")
                else:
                    type_item.setBackground(QColor(255, 255, 224))  # 浅黄色
                    type_item.setText("预测订单")
                self.order_table.setItem(row, 8, type_item)
                
                self.order_table.setItem(row, 9, QTableWidgetItem(str(item['RequiredQty'])))
                self.order_table.setItem(row, 10, QTableWidgetItem(str(item['CumulativeQty'])))
                self.order_table.setItem(row, 11, QTableWidgetItem(str(item['NetRequiredQty'])))

                # 操作列 - 查看详情按钮
                detail_btn = QPushButton("详情")
                detail_btn.clicked.connect(lambda _, d=item: self.show_order_detail(d))
                self.order_table.setCellWidget(row, 12, detail_btn)
                
        except Exception as e:
            print(f"加载订单数据失败: {e}")

    def show_order_detail(self, order):
        """显示订单详情信息"""
        info = (
            f"订单号: {order['OrderNumber']}\n"
            f"供应商: {order['SupplierName']}\n"
            f"客户: {order['CustomerName']}\n"
            f"交货日期: {order['DeliveryDate']}\n"
            f"订单类型: {order['OrderType']}\n"
            f"需求数量: {order['RequiredQty']}\n"
        )
        QMessageBox.information(self, "订单详情", info)
    
    def load_history_data(self):
        """加载导入历史数据"""
        try:
            data = CustomerOrderService.get_import_history()
            
            # 填充表格
            self.history_table.setRowCount(len(data))
            
            for row, item in enumerate(data):
                self.history_table.setItem(row, 0, QTableWidgetItem(str(item['ImportId'])))
                self.history_table.setItem(row, 1, QTableWidgetItem(item['FileName']))
                self.history_table.setItem(row, 2, QTableWidgetItem(item['ImportDate']))
                self.history_table.setItem(row, 3, QTableWidgetItem(str(item['OrderCount'])))
                self.history_table.setItem(row, 4, QTableWidgetItem(str(item['LineCount'])))
                
                # 状态（带颜色标识）
                status_item = QTableWidgetItem(item['ImportStatus'])
                if item['ImportStatus'] == 'Success':
                    status_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                else:
                    status_item.setBackground(QColor(255, 182, 193))  # 浅红色
                self.history_table.setItem(row, 5, status_item)
                
                self.history_table.setItem(row, 6, QTableWidgetItem(item.get('ErrorMessage', '')))
                self.history_table.setItem(row, 7, QTableWidgetItem(item['ImportedBy']))
                
        except Exception as e:
            print(f"加载导入历史失败: {e}")
    
    def refresh_kanban_data(self):
        """刷新看板数据"""
        self.load_kanban_data()
    
    def search_orders(self):
        """查询订单"""
        self.load_order_data()
    
    def refresh_data(self):
        """定时刷新数据"""
        self.load_kanban_data()
        self.load_order_data()
    
    def on_version_changed(self, version_text):
        """版本选择变化处理"""
        print(f"版本选择变化: {version_text}")
        # 如果选择了特定版本，可以在这里添加特殊处理逻辑
        self.refresh_kanban_data()
    
    def load_version_list(self):
        """加载版本列表"""
        try:
            # 记录当前选择的版本ID以便刷新后恢复
            current_id = self.get_selected_version_id()

            # 获取导入历史记录作为版本列表
            history_data = CustomerOrderService.get_import_history()

            # 清空现有版本并重新填充
            self.version_combo.clear()
            self.version_combo.addItem("全部版本")

            for record in history_data:
                if record['ImportStatus'] == 'Success':
                    version_text = f"{record['FileName']} ({record['ImportDate']})"
                    self.version_combo.addItem(version_text, record['ImportId'])

            # 如果之前选中的版本仍然存在，则恢复选择
            if current_id is not None:
                index = self.version_combo.findData(current_id)
                if index != -1:
                    self.version_combo.setCurrentIndex(index)

            print(f"加载了 {len(history_data)} 个版本记录")

        except Exception as e:
            print(f"加载版本列表失败: {e}")
    
    def get_selected_version_id(self):
        """获取选中的版本ID"""
        current_data = self.version_combo.currentData()
        if current_data is None:
            return None
        try:
            return int(current_data)
        except (TypeError, ValueError):
            # 如果转换失败，返回 None 以避免后续计算错误
            return None
