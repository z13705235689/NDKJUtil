#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理界面
参考Navicat 16设计，提供专业的数据库管理功能
"""

import sys
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, 
    QTableWidgetItem, QFrame, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, 
    QMessageBox, QTabWidget, QHeaderView, QAbstractItemView, QGroupBox, 
    QFormLayout, QTextEdit, QDialog, QCheckBox, QDialogButtonBox, QGridLayout,
    QSpacerItem, QSizePolicy, QScrollArea, QSplitter, QDateEdit, QFileDialog,
    QProgressBar, QTextBrowser, QTreeWidget, QTreeWidgetItem, QSplitter,
    QMenu, QToolBar, QStatusBar, QMainWindow, QApplication
)
from PySide6.QtCore import Qt, QDate, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QBrush, QAction
from app.db import get_conn
import sqlite3


class DatabaseTreeWidget(QTreeWidget):
    """数据库树形控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("数据库对象")
        self.setMinimumWidth(280)
        self.setMaximumWidth(350)  # 增加最大宽度
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 4px;
                border-bottom: 1px solid #e9ecef;
            }
            QTreeWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #e3f2fd;
            }
        """)
        
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # 根据项目类型添加不同的菜单项
        if item.parent() is None:  # 根组
            if "表" in item.text(0):
                refresh_action = QAction("刷新表列表", self)
                refresh_action.triggered.connect(self.parent().load_table_list)
                menu.addAction(refresh_action)
        else:  # 具体对象
            if item.parent().text(0).startswith("表"):
                # 表操作
                open_action = QAction("打开表", self)
                open_action.triggered.connect(lambda: self.parent().open_table(item.text(0)))
                menu.addAction(open_action)
                
                design_action = QAction("设计表", self)
                design_action.triggered.connect(lambda: self.parent().design_table(item.text(0)))
                menu.addAction(design_action)
                
                menu.addSeparator()
                
                export_action = QAction("导出数据", self)
                export_action.triggered.connect(lambda: self.parent().export_table(item.text(0)))
                menu.addAction(export_action)
                
                menu.addSeparator()
                
                # 清空表
                clear_action = QAction("清空表", self)
                clear_action.triggered.connect(lambda: self.parent().clear_table_from_tree(item.text(0)))
                menu.addAction(clear_action)
        
        if menu.actions():
            menu.exec_(self.mapToGlobal(position))


class DatabaseManagement(QWidget):
    """数据库管理界面"""
    
    def __init__(self):
        super().__init__()
        self.current_table = None
        
        # 分页相关变量
        self.current_page = 1
        self.page_size = 100
        self.total_rows = 0
        self.total_pages = 1
        
        self.init_ui()
        self.load_database_info()
        self.load_table_list()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("数据库管理")
        self.setMinimumSize(1600, 1000)  # 增加最小尺寸
        self.resize(1800, 1200)  # 设置默认尺寸
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        self.create_toolbar()
        main_layout.addWidget(self.toolbar)
        
        # 状态栏
        self.create_statusbar()
        main_layout.addWidget(self.statusbar)
        
        # 主内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧：数据库对象树
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel)
        
        # 右侧：数据操作区域
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel)
        
        # 设置分割器比例
        content_layout.setStretch(0, 1)  # 左侧面板
        content_layout.setStretch(1, 4)  # 右侧面板 - 增加比例
        
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)
    
    def create_toolbar(self):
        """创建工具栏"""
        self.toolbar = QToolBar()
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                spacing: 8px;
                padding: 4px;
            }
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QToolButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QToolButton:pressed {
                background-color: #dee2e6;
            }
        """)
        
        # 连接按钮
        connect_btn = QPushButton("连接数据库")
        connect_btn.clicked.connect(self.connect_database)
        self.toolbar.addWidget(connect_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_all)
        self.toolbar.addWidget(refresh_btn)
        
        self.toolbar.addSeparator()
        
        # 新建表按钮
        new_table_btn = QPushButton("新建表")
        new_table_btn.clicked.connect(self.create_new_table)
        self.toolbar.addWidget(new_table_btn)
        
        # 备份按钮
        backup_btn = QPushButton("备份数据库")
        backup_btn.clicked.connect(self.backup_database)
        self.toolbar.addWidget(backup_btn)
        
        # 恢复按钮
        restore_btn = QPushButton("恢复数据库")
        restore_btn.clicked.connect(self.restore_database)
        self.toolbar.addWidget(restore_btn)
        
        # 清空数据库按钮
        clear_db_btn = QPushButton("清空数据库")
        clear_db_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        clear_db_btn.clicked.connect(self.clear_database)
        self.toolbar.addWidget(clear_db_btn)
        
        # 数据库信息显示
        self.db_info_label = QLabel("数据库信息")
        self.db_info_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 11px;
                padding: 4px 8px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        self.toolbar.addWidget(self.db_info_label)
        
        # 更新数据库信息显示
        self.update_db_info_display()
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.statusbar.setStyleSheet("""
            QStatusBar {
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
                color: #6c757d;
                font-size: 11px;
            }
        """)
        
        # 状态信息
        self.status_label = QLabel("就绪")
        self.statusbar.addWidget(self.status_label)
        
        # 数据库信息
        self.db_info_label = QLabel("")
        self.statusbar.addPermanentWidget(self.db_info_label)
    
    def create_left_panel(self):
        """创建左侧面板"""
        left_frame = QFrame()
        left_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-right: 1px solid #dee2e6;
            }
        """)
        
        left_layout = QVBoxLayout(left_frame)
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("数据库对象")
        title_label.setStyleSheet("""
            QLabel {
                background-color: #007bff;
                color: white;
                padding: 8px;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_label)
        
        # 数据库对象树
        self.db_tree = DatabaseTreeWidget(self)
        self.db_tree.itemClicked.connect(self.on_tree_item_clicked)
        left_layout.addWidget(self.db_tree)
        
        return left_frame
    
    def create_right_panel(self):
        """创建右侧面板"""
        right_frame = QFrame()
        right_frame.setStyleSheet("""
            QFrame {
                background-color: white;
            }
        """)
        
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-top: none;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)
        
        # 数据标签页
        self.data_tab = self.create_data_tab()
        self.tab_widget.addTab(self.data_tab, "数据")
        
        # 结构标签页
        self.structure_tab = self.create_structure_tab()
        self.tab_widget.addTab(self.structure_tab, "结构")
        
        # SQL标签页
        self.sql_tab = self.create_sql_tab()
        self.tab_widget.addTab(self.sql_tab, "SQL")
        
        right_layout.addWidget(self.tab_widget)
        
        return right_frame
    
    def create_data_tab(self):
        """创建数据标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        data_toolbar = QHBoxLayout()
        
        # 当前表标签
        self.current_table_label = QLabel("当前表: 未选择")
        self.current_table_label.setStyleSheet("font-weight: bold; color: #495057;")
        data_toolbar.addWidget(self.current_table_label)
        
        data_toolbar.addStretch()
        
        # 操作按钮
        add_row_btn = QPushButton("添加行")
        add_row_btn.clicked.connect(self.add_table_row)
        add_row_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        data_toolbar.addWidget(add_row_btn)
        
        delete_row_btn = QPushButton("删除行")
        delete_row_btn.clicked.connect(self.delete_table_row)
        delete_row_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        data_toolbar.addWidget(delete_row_btn)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_table_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        data_toolbar.addWidget(refresh_btn)
        
        # 分页控件
        data_toolbar.addStretch()
        
        # 每页显示行数选择
        page_size_label = QLabel("每页:")
        page_size_label.setStyleSheet("color: #495057; font-size: 11px;")
        data_toolbar.addWidget(page_size_label)
        
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(['50', '100', '200', '500', '1000'])
        self.page_size_combo.setCurrentText('100')
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        self.page_size_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 60px;
            }
        """)
        data_toolbar.addWidget(self.page_size_combo)
        
        # 分页导航按钮
        self.first_page_btn = QPushButton("首页")
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        self.first_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        data_toolbar.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.clicked.connect(self.go_to_prev_page)
        self.prev_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        data_toolbar.addWidget(self.prev_page_btn)
        
        # 页码显示
        self.page_info_label = QLabel("第 1 页 / 共 1 页")
        self.page_info_label.setStyleSheet("color: #495057; font-size: 11px; padding: 0 8px;")
        data_toolbar.addWidget(self.page_info_label)
        
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.next_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        data_toolbar.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton("末页")
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        self.last_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        data_toolbar.addWidget(self.last_page_btn)
        
        layout.addLayout(data_toolbar)
        
        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setEditTriggers(QTableWidget.DoubleClicked)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.itemChanged.connect(self.on_table_item_changed)
        
        # 启用右键菜单
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self.show_table_context_menu)
        
        # 设置表格属性 - 关键：启用滚动条和列宽管理
        self.data_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.data_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.data_table.setWordWrap(False)  # 禁用自动换行
        
        # 设置列宽策略
        header = self.data_table.horizontalHeader()
        header.setStretchLastSection(False)  # 最后一列不自动拉伸
        header.setDefaultAlignment(Qt.AlignLeft)
        
        # 启用水平滚动条 - 强制显示
        self.data_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.data_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 关键：确保滚动条立即可见
        self.data_table.horizontalScrollBar().setVisible(True)
        
        # 关键：使用Preferred策略，让表格能够正确显示滚动条
        self.data_table.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustToContents)
        
        # 设置表格的最小尺寸，确保滚动条有足够空间
        self.data_table.setMinimumHeight(400)
        
        # 关键：使用Preferred策略，让表格能够正确显示滚动条
        self.data_table.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        # 设置滚动条样式
        self.data_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 6px;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
        """)
        
        # 关键：确保表格能够正确显示滚动条
        self.data_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.data_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.data_table)
        
        return tab
    
    def create_structure_tab(self):
        """创建结构标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 结构表格
        self.structure_table = QTableWidget()
        self.structure_table.setColumnCount(6)
        self.structure_table.setHorizontalHeaderLabels([
            "字段名", "数据类型", "长度", "允许空", "默认值", "主键"
        ])
        self.structure_table.setAlternatingRowColors(True)
        
        # 设置表格属性
        self.structure_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.structure_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.structure_table.setWordWrap(False)
        
        # 设置列宽策略
        header = self.structure_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignLeft)
        
        # 启用滚动条 - 强制显示水平滚动条
        self.structure_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.structure_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 设置表格大小策略
        self.structure_table.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustToContents)
        
        # 设置表格的最小尺寸
        self.structure_table.setMinimumHeight(300)
        self.structure_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.structure_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 6px;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
        """)
        layout.addWidget(self.structure_table)
        
        return tab
    
    def create_sql_tab(self):
        """创建SQL标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # SQL输入框
        sql_label = QLabel("SQL查询:")
        sql_label.setStyleSheet("font-weight: bold; color: #495057;")
        layout.addWidget(sql_label)
        
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText("输入SQL查询语句...")
        self.sql_editor.setMaximumHeight(100)
        self.sql_editor.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.sql_editor)
        
        # SQL按钮
        sql_buttons = QHBoxLayout()
        
        execute_btn = QPushButton("执行查询")
        execute_btn.clicked.connect(self.execute_sql)
        execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        sql_buttons.addWidget(execute_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.sql_editor.clear)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        sql_buttons.addWidget(clear_btn)
        
        sql_buttons.addStretch()
        layout.addLayout(sql_buttons)
        
        # 结果表格
        result_label = QLabel("查询结果:")
        result_label.setStyleSheet("font-weight: bold; color: #495057;")
        layout.addWidget(result_label)
        
        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        
        # 设置表格属性
        self.result_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.result_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.result_table.setWordWrap(False)
        
        # 设置列宽策略
        header = self.result_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignLeft)
        
        # 启用滚动条 - 强制显示水平滚动条
        self.result_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.result_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 设置表格大小策略
        self.result_table.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustToContents)
        
        # 设置表格的最小尺寸
        self.result_table.setMinimumHeight(300)
        self.result_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.result_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 6px;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
        """)
        layout.addWidget(self.result_table)
        
        return tab
    
    def load_database_info(self):
        """加载数据库信息"""
        try:
            from app.db import DatabaseManager
            db_manager = DatabaseManager()
            
            # 更新状态栏
            self.db_info_label.setText(f"数据库: {db_manager.db_path.name}")
            
            # 更新状态
            self.status_label.setText("数据库已连接")
            
        except Exception as e:
            self.status_label.setText(f"数据库连接失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载数据库信息失败: {str(e)}")
    
    def load_table_list(self):
        """加载表列表"""
        try:
            self.db_tree.clear()
            
            with get_conn() as conn:
                # 获取所有表
                cursor = conn.execute("""
                    SELECT name, type FROM sqlite_master 
                    WHERE type IN ('table', 'view') 
                    ORDER BY type, name
                """)
                
                tables = cursor.fetchall()
                
                # 创建表组
                table_group = QTreeWidgetItem(self.db_tree, ["📊 表 (Tables)"])
                table_group.setExpanded(True)
                
                view_group = QTreeWidgetItem(self.db_tree, ["👁️ 视图 (Views)"])
                view_group.setExpanded(True)
                
                for table_name, table_type in tables:
                    if table_type == 'table':
                        item = QTreeWidgetItem(table_group, [table_name])
                        # 设置图标颜色
                        item.setForeground(0, QColor("#007bff"))
                    else:
                        item = QTreeWidgetItem(view_group, [table_name])
                        item.setForeground(0, QColor("#28a745"))
                
                # 展开所有组
                self.db_tree.expandAll()
                
                # 更新状态
                self.status_label.setText(f"已加载 {len(tables)} 个数据库对象")
                
        except Exception as e:
            self.status_label.setText(f"加载表列表失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载表列表失败: {str(e)}")
    
    def on_tree_item_clicked(self, item, column):
        """树形项目被点击时的处理"""
        if item.parent() is not None:  # 不是根组
            table_name = item.text(0)
            self.current_table = table_name
            self.current_table_label.setText(f"当前表: {table_name}")
            self.current_page = 1  # 重置到第一页
            self.load_table_data(table_name, self.current_page)
            self.load_table_structure(table_name)
            self.status_label.setText(f"已选择表: {table_name}")
    
    def load_table_data(self, table_name, page=1):
        """加载表数据"""
        try:
            with get_conn() as conn:
                # 获取表结构
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns_info = cursor.fetchall()
                
                # 设置表格列
                self.data_table.setColumnCount(len(columns_info))
                headers = [col[1] for col in columns_info]  # 列名
                self.data_table.setHorizontalHeaderLabels(headers)
                
                # 获取总行数
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                self.total_rows = cursor.fetchone()[0]
                
                # 计算分页信息
                self.total_pages = (self.total_rows + self.page_size - 1) // self.page_size
                self.current_page = max(1, min(page, self.total_pages))
                
                # 计算偏移量
                offset = (self.current_page - 1) * self.page_size
                
                # 获取分页数据
                cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT {self.page_size} OFFSET {offset}")
                rows = cursor.fetchall()
                
                # 设置行数
                self.data_table.setRowCount(len(rows))
                
                # 填充数据
                for row_idx, row_data in enumerate(rows):
                    for col_idx, cell_data in enumerate(row_data):
                        # 处理长文本，截断显示
                        cell_text = str(cell_data) if cell_data is not None else ""
                        if len(cell_text) > 100:  # 超过100字符截断
                            display_text = cell_text[:97] + "..."
                            # 设置工具提示显示完整内容
                            item = QTableWidgetItem(display_text)
                            item.setToolTip(cell_text)
                        else:
                            item = QTableWidgetItem(cell_text)
                        
                        self.data_table.setItem(row_idx, col_idx, item)
                
                # 智能列宽管理
                self._optimize_column_widths(table_name, columns_info)
                
                # 关键：强制刷新滚动条状态
                self.data_table.horizontalScrollBar().setVisible(True)
                self.data_table.horizontalScrollBar().update()
                
                # 确保滚动条策略正确设置
                self.data_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
                self.data_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                
                # 更新分页信息
                self.update_pagination_info()
                
                # 更新状态
                self.status_label.setText(f"表 {table_name} 数据加载完成，第 {self.current_page} 页，共 {len(rows)} 行 / 总计 {self.total_rows} 行")
                
        except Exception as e:
            self.status_label.setText(f"加载表数据失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载表数据失败: {str(e)}")
    
    def update_pagination_info(self):
        """更新分页信息显示"""
        self.page_info_label.setText(f"第 {self.current_page} 页 / 共 {self.total_pages} 页")
        
        # 更新按钮状态
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)
    
    def on_page_size_changed(self, new_size):
        """每页显示行数改变时的处理"""
        self.page_size = int(new_size)
        self.current_page = 1  # 重置到第一页
        if self.current_table:
            self.load_table_data(self.current_table, self.current_page)
    
    def go_to_first_page(self):
        """跳转到第一页"""
        if self.current_table and self.current_page > 1:
            self.current_page = 1
            self.load_table_data(self.current_table, self.current_page)
    
    def go_to_prev_page(self):
        """跳转到上一页"""
        if self.current_table and self.current_page > 1:
            self.current_page -= 1
            self.load_table_data(self.current_table, self.current_page)
    
    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_table and self.current_page < self.total_pages:
            self.current_page += 1
            self.load_table_data(self.current_table, self.current_page)
    
    def go_to_last_page(self):
        """跳转到最后一页"""
        if self.current_table and self.current_page < self.total_pages:
            self.current_page = self.total_pages
            self.load_table_data(self.current_table, self.current_page)
    
    def _optimize_column_widths(self, table_name, columns_info):
        """优化列宽设置"""
        try:
            # 获取列名
            column_names = [col[1] for col in columns_info]
            
            # 计算每列的最佳宽度
            for col_idx, col_name in enumerate(column_names):
                # 列标题宽度
                header_width = len(col_name) * 10 + 20
                
                # 内容最大宽度
                max_content_width = 0
                for row_idx in range(min(50, self.data_table.rowCount())):  # 检查前50行
                    item = self.data_table.item(row_idx, col_idx)
                    if item:
                        content_width = len(item.text()) * 8 + 20
                        max_content_width = max(max_content_width, content_width)
                
                # 设置列宽（最小80，最大200）- 缩小范围让更多列能显示
                optimal_width = min(max(header_width, max_content_width, 80), 200)
                self.data_table.setColumnWidth(col_idx, optimal_width)
                
                # 设置列宽调整策略 - 所有列都允许用户调整
                self.data_table.horizontalHeader().setSectionResizeMode(col_idx, QHeaderView.ResizeMode.Interactive)
                
                # 设置最小列宽
                self.data_table.horizontalHeader().setMinimumSectionSize(80)
                
        except Exception as e:
            # 如果优化失败，使用默认的自动调整
            self.data_table.resizeColumnsToContents()
            
        # 强制启用水平滚动条，确保所有列都能通过滚动查看
        self.data_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        # 确保表格能够正确显示所有列
        self.data_table.horizontalHeader().setStretchLastSection(False)
        
        # 关键：确保水平滚动条正常工作
        total_columns_width = sum(self.data_table.columnWidth(i) for i in range(self.data_table.columnCount()))
        
        # 设置表格的最小宽度，确保有足够空间显示滚动条
        min_width = max(total_columns_width + 50, 800)
        self.data_table.setMinimumWidth(min_width)
        
        # 确保水平滚动条可见和可用
        self.data_table.horizontalScrollBar().setVisible(True)
        self.data_table.horizontalScrollBar().setEnabled(True)
    
    def load_table_structure(self, table_name):
        """加载表结构"""
        try:
            with get_conn() as conn:
                # 获取表结构
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns_info = cursor.fetchall()
                
                # 设置表格行数
                self.structure_table.setRowCount(len(columns_info))
                
                # 填充结构信息
                for row_idx, col_info in enumerate(columns_info):
                    # 字段名
                    name_item = QTableWidgetItem(col_info[1])
                    self.structure_table.setItem(row_idx, 0, name_item)
                    
                    # 数据类型
                    type_item = QTableWidgetItem(col_info[2])
                    self.structure_table.setItem(row_idx, 1, type_item)
                    
                    # 长度
                    length_item = QTableWidgetItem(str(col_info[3]) if col_info[3] else "")
                    self.structure_table.setItem(row_idx, 2, length_item)
                    
                    # 允许空
                    not_null = "否" if col_info[3] else "是"
                    not_null_item = QTableWidgetItem(not_null)
                    self.structure_table.setItem(row_idx, 3, not_null_item)
                    
                    # 默认值
                    default_item = QTableWidgetItem(str(col_info[4]) if col_info[4] else "")
                    self.structure_table.setItem(row_idx, 4, default_item)
                    
                    # 主键
                    pk = "是" if col_info[5] else "否"
                    pk_item = QTableWidgetItem(pk)
                    self.structure_table.setItem(row_idx, 5, pk_item)
                
                # 调整列宽
                self.structure_table.resizeColumnsToContents()
                
                # 设置列宽调整策略 - 所有列都允许调整
                header = self.structure_table.horizontalHeader()
                for i in range(6):
                    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                    header.setMinimumSectionSize(100)  # 设置最小列宽
                
                # 强制启用水平滚动条
                self.structure_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载表结构失败: {str(e)}")
    
    def add_table_row(self):
        """添加表行"""
        if not self.current_table:
            QMessageBox.warning(self, "警告", "请先选择一个表")
            return
        
        try:
            # 获取表结构
            with get_conn() as conn:
                cursor = conn.execute(f"PRAGMA table_info({self.current_table})")
                columns_info = cursor.fetchall()
                
                # 创建新行
                new_row = self.data_table.rowCount()
                self.data_table.setRowCount(new_row + 1)
                
                # 为每列创建空项
                for col_idx in range(len(columns_info)):
                    item = QTableWidgetItem("")
                    self.data_table.setItem(new_row, col_idx, item)
                
                # 滚动到新行
                self.data_table.scrollToBottom()
                
                # 自动选中新行并进入编辑模式
                self.data_table.selectRow(new_row)
                
                # 不自动进入编辑模式，让用户自己选择何时编辑
                self.status_label.setText(f"已添加新行到表 {self.current_table}，请双击单元格进行编辑")
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加行失败: {str(e)}")
    

    
    def delete_table_row(self):
        """删除表行"""
        if not self.current_table:
            QMessageBox.warning(self, "警告", "请先选择一个表")
            return
        
        # 获取选中的行
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除选中的 {len(selected_rows)} 行吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 获取表的主键信息
                with get_conn() as conn:
                    cursor = conn.execute(f"PRAGMA table_info({self.current_table})")
                    columns_info = cursor.fetchall()
                    
                    # 查找主键列
                    pk_columns = []
                    for col_info in columns_info:
                        if col_info[5] == 1:  # 是主键
                            pk_columns.append(col_info[1])
                    
                    if not pk_columns:
                        QMessageBox.warning(self, "警告", "该表没有主键，无法安全删除行")
                        return
                    
                    # 删除选中的行
                    deleted_count = 0
                    for row_idx in sorted(selected_rows, reverse=True):
                        # 构建WHERE条件
                        where_conditions = []
                        for pk_col in pk_columns:
                            pk_col_idx = next(i for i, col in enumerate(columns_info) if col[1] == pk_col)
                            pk_value = self.data_table.item(row_idx, pk_col_idx).text()
                            where_conditions.append(f"{pk_col} = '{pk_value}'")
                        
                        where_clause = " AND ".join(where_conditions)
                        
                        # 执行删除
                        conn.execute(f"DELETE FROM {self.current_table} WHERE {where_clause}")
                        deleted_count += 1
                    
                    conn.commit()
                    
                    # 刷新表格
                    self.load_table_data(self.current_table)
                    
                    self.status_label.setText(f"已删除 {deleted_count} 行数据")
                    
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除行失败: {str(e)}")
    
    def refresh_table_data(self):
        """刷新表数据"""
        if self.current_table:
            self.load_table_data(self.current_table, self.current_page)
    
    def on_table_item_changed(self, item):
        """表格项改变时的处理"""
        if not self.current_table:
            return
        
        try:
            # 获取行和列索引
            row = item.row()
            col = item.column()
            
            # 获取列名
            column_name = self.data_table.horizontalHeaderItem(col).text()
            
            # 获取新值
            new_value = item.text()
            
            # 获取表的主键信息
            with get_conn() as conn:
                cursor = conn.execute(f"PRAGMA table_info({self.current_table})")
                columns_info = cursor.fetchall()
                
                # 查找主键列
                pk_columns = []
                for col_info in columns_info:
                    if col_info[5] == 1:  # 是主键
                        pk_columns.append(col_info[1])
                
                if not pk_columns:
                    QMessageBox.warning(self, "警告", "该表没有主键，无法更新数据")
                    return
                
                # 构建WHERE条件
                where_conditions = []
                for pk_col in pk_columns:
                    pk_col_idx = next(i for i, col_info in enumerate(columns_info) if col_info[1] == pk_col)
                    pk_value = self.data_table.item(row, pk_col_idx).text()
                    where_conditions.append(f"{pk_col} = '{pk_value}'")
                
                where_clause = " AND ".join(where_conditions)
                
                # 执行更新
                if new_value == "":
                    # 空值设为NULL
                    conn.execute(f"UPDATE {self.current_table} SET {column_name} = NULL WHERE {where_clause}")
                else:
                    conn.execute(f"UPDATE {self.current_table} SET {column_name} = ? WHERE {where_clause}", (new_value,))
                
                conn.commit()
                
                self.status_label.setText(f"已更新表 {self.current_table} 的 {column_name} 列")
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"更新数据失败: {str(e)}")
    
    def execute_sql(self):
        """执行SQL查询"""
        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "警告", "请输入SQL查询语句")
            return
        
        try:
            with get_conn() as conn:
                cursor = conn.execute(sql)
                
                if sql.strip().upper().startswith('SELECT'):
                    # SELECT查询，显示结果
                    rows = cursor.fetchall()
                    
                    if rows:
                        # 设置列
                        column_names = [description[0] for description in cursor.description]
                        self.result_table.setColumnCount(len(column_names))
                        self.result_table.setHorizontalHeaderLabels(column_names)
                        
                        # 设置行
                        self.result_table.setRowCount(len(rows))
                        
                        # 填充数据
                        for row_idx, row_data in enumerate(rows):
                            for col_idx, cell_data in enumerate(row_data):
                                item = QTableWidgetItem(str(cell_data) if cell_data is not None else "")
                                self.result_table.setItem(row_idx, col_idx, item)
                        
                        # 调整列宽
                        self.result_table.resizeColumnsToContents()
                        
                        # 设置列宽调整策略 - 所有列都允许调整
                        header = self.result_table.horizontalHeader()
                        for i in range(self.result_table.columnCount()):
                            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                            header.setMinimumSectionSize(100)  # 设置最小列宽
                        
                        # 强制启用水平滚动条
                        self.result_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
                        
                        self.status_label.setText(f"查询执行成功，返回 {len(rows)} 行结果")
                    else:
                        self.status_label.setText("查询执行成功，无结果返回")
                else:
                    # 非SELECT查询
                    conn.commit()
                    self.status_label.setText("SQL执行成功")
                    
                    # 如果是修改表结构的操作，刷新表列表
                    if any(keyword in sql.upper() for keyword in ['CREATE', 'DROP', 'ALTER']):
                        self.load_table_list()
                
        except Exception as e:
            self.status_label.setText(f"SQL执行失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"SQL执行失败: {str(e)}")
    
    def connect_database(self):
        """连接数据库"""
        self.load_database_info()
        self.load_table_list()
    
    def refresh_all(self):
        """刷新所有"""
        self.load_database_info()
        self.load_table_list()
        if self.current_table:
            self.load_table_data(self.current_table, self.current_page)
            self.load_table_structure(self.current_table)
    
    def create_new_table(self):
        """创建新表"""
        QMessageBox.information(self, "信息", "创建新表功能开发中...")
    
    def update_db_info_display(self):
        """更新数据库信息显示"""
        try:
            from app.db import get_database_info
            db_info = get_database_info()
            
            if db_info["embedded"]:
                db_type = "内置数据库"
            else:
                db_type = "外部数据库"
            
            size_mb = db_info["size"] / (1024 * 1024) if db_info["size"] > 0 else 0
            
            info_text = f"{db_type} | {size_mb:.1f}MB"
            self.db_info_label.setText(info_text)
            
        except Exception as e:
            self.db_info_label.setText("数据库信息获取失败")
    
    def backup_database(self):
        """备份数据库"""
        try:
            from app.db import DatabaseManager
            db_manager = DatabaseManager()
            
            # 选择备份文件路径
            backup_path, _ = QFileDialog.getSaveFileName(
                self, 
                "选择备份文件位置", 
                f"mes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                "Database Files (*.db);;All Files (*)"
            )
            
            if backup_path:
                import shutil
                shutil.copy2(db_manager.db_path, backup_path)
                
                self.status_label.setText(f"数据库已备份到: {backup_path}")
                QMessageBox.information(self, "成功", f"数据库已备份到: {backup_path}")
                
                # 更新数据库信息显示
                self.update_db_info_display()
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"备份数据库失败: {str(e)}")
    
    def restore_database(self):
        """恢复数据库"""
        try:
            from app.db import DatabaseManager
            db_manager = DatabaseManager()
            
            # 选择要恢复的备份文件
            backup_path, _ = QFileDialog.getOpenFileName(
                self, 
                "选择要恢复的备份文件", 
                "",
                "Database Files (*.db);;All Files (*)"
            )
            
            if not backup_path:
                return
            
            # 验证备份文件
            if not os.path.exists(backup_path):
                QMessageBox.warning(self, "错误", "选择的备份文件不存在")
                return
            
            # 验证备份文件是否为有效的SQLite数据库
            try:
                test_conn = sqlite3.connect(backup_path)
                cursor = test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                # 获取备份文件的基本信息
                backup_info = {}
                for table_name, in tables:
                    cursor = test_conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    backup_info[table_name] = row_count
                
                test_conn.close()
                
                if not tables:
                    QMessageBox.warning(self, "错误", "选择的文件不是有效的数据库文件或数据库为空")
                    return
                    
            except sqlite3.Error as e:
                QMessageBox.warning(self, "错误", f"选择的文件不是有效的SQLite数据库: {str(e)}")
                return
            
            # 显示备份文件详细信息
            backup_details = "\n".join([f"  • {table}: {count} 行" for table, count in backup_info.items()])
            
            # 确认恢复操作
            reply = QMessageBox.question(
                self, 
                "确认恢复数据库", 
                f"确定要恢复数据库吗？\n\n"
                f"⚠️  警告：此操作将完全替换当前数据库！\n"
                f"当前数据库的所有数据将被备份文件的内容覆盖。\n\n"
                f"📁 备份文件: {os.path.basename(backup_path)}\n"
                f"📊 包含 {len(tables)} 个表:\n{backup_details}\n\n"
                f"此操作不可撤销！确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 显示进度对话框
                progress_dialog = QMessageBox(self)
                progress_dialog.setWindowTitle("正在恢复数据库")
                progress_dialog.setText("正在恢复数据库，请稍候...\n\n注意：请勿关闭此窗口，恢复完成后会自动关闭")
                progress_dialog.setStandardButtons(QMessageBox.Ok)
                progress_dialog.setModal(False)  # 非模态，允许用户看到进度
                progress_dialog.show()
                
                # 处理事件，让进度对话框显示
                QApplication.processEvents()
                
                try:
                    # 关闭所有数据库连接
                    try:
                        # 强制关闭当前连接
                        import gc
                        gc.collect()
                    except:
                        pass
                    
                    # 备份当前数据库到程序运行目录
                    try:
                        import shutil
                        from pathlib import Path
                        
                        # 获取程序运行目录
                        program_dir = Path.cwd()
                        
                        # 生成备份文件名：当前数据库名_恢复前备份_时间戳.db
                        current_db_name = db_manager.db_path.stem  # 获取不带扩展名的文件名
                        backup_filename = f"{current_db_name}_恢复前备份_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                        current_backup_path = program_dir / backup_filename
                        
                        if db_manager.db_path.exists():
                            # 复制当前数据库到程序运行目录
                            shutil.copy2(db_manager.db_path, current_backup_path)
                            print(f"✅ 当前数据库已备份到: {current_backup_path}")
                            
                            # 更新进度对话框信息
                            progress_dialog.setText(f"正在恢复数据库，请稍候...\n\n已备份当前数据库到:\n{backup_filename}")
                            QApplication.processEvents()
                        else:
                            print("⚠️ 当前数据库文件不存在，跳过备份")
                            current_backup_path = None
                            
                    except Exception as e:
                        QMessageBox.warning(self, "警告", f"无法备份当前数据库: {str(e)}")
                        current_backup_path = None
                    
                    # 恢复数据库
                    import shutil
                    
                    # 删除当前数据库文件
                    if db_manager.db_path.exists():
                        db_manager.db_path.unlink()
                    
                    # 复制备份文件到当前数据库位置
                    shutil.copy2(backup_path, db_manager.db_path)
                    
                    # 验证恢复后的数据库
                    test_conn = sqlite3.connect(db_manager.db_path)
                    cursor = test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    restored_tables = cursor.fetchall()
                    
                    # 获取恢复后的表信息
                    restored_info = {}
                    for table_name, in restored_tables:
                        cursor = test_conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = cursor.fetchone()[0]
                        restored_info[table_name] = row_count
                    
                    test_conn.close()
                    
                    # 关闭进度对话框
                    progress_dialog.close()
                    
                    # 刷新界面
                    self.load_database_info()
                    self.load_table_list()
                    
                    # 更新数据库信息显示
                    self.update_db_info_display()
                    
                    # 清空当前选择
                    self.current_table = None
                    self.current_table_label.setText("当前表: 未选择")
                    self.data_table.setRowCount(0)
                    self.data_table.setColumnCount(0)
                    self.structure_table.setRowCount(0)
                    
                    self.status_label.setText(f"✅ 数据库恢复成功！恢复了 {len(restored_tables)} 个表")
                    
                    # 显示恢复成功信息
                    restored_details = "\n".join([f"  • {table}: {count} 行" for table, count in restored_info.items()])
                    
                    # 构建成功信息
                    success_message = f"✅ 数据库恢复成功！\n\n"
                    success_message += f"📊 恢复了 {len(restored_tables)} 个表:\n{restored_details}\n\n"
                    success_message += f"🔄 当前数据库已更新为备份文件的内容。\n\n"
                    
                    if current_backup_path and current_backup_path.exists():
                        success_message += f"💾 重要提示：原数据库已自动备份到程序目录:\n"
                        success_message += f"   文件名：{current_backup_path.name}\n"
                        success_message += f"   位置：{current_backup_path.parent}\n\n"
                        success_message += f"📝 如需恢复原数据，请使用此备份文件。"
                    else:
                        success_message += f"⚠️ 警告：原数据库备份失败，请手动检查数据完整性"
                    
                    QMessageBox.information(
                        self, 
                        "✅ 恢复成功", 
                        success_message
                    )
                    
                except Exception as e:
                    # 关闭进度对话框
                    progress_dialog.close()
                    
                    # 恢复失败，尝试恢复原数据库
                    try:
                        if current_backup_path and current_backup_path.exists():
                            shutil.copy2(current_backup_path, db_manager.db_path)
                            QMessageBox.warning(
                                self, 
                                "❌ 恢复失败", 
                                f"恢复失败，已恢复原数据库。\n\n"
                                f"错误详情: {str(e)}\n\n"
                                f"原数据库备份位置:\n{current_backup_path.name}"
                            )
                        else:
                            QMessageBox.critical(
                                self, 
                                "💥 严重错误", 
                                f"恢复失败且无法恢复原数据库！\n\n"
                                f"错误详情: {str(e)}\n\n"
                                f"请手动恢复数据库文件！"
                            )
                    except Exception as restore_error:
                        QMessageBox.critical(
                            self, 
                            "💥 严重错误", 
                            f"恢复失败且无法恢复原数据库！\n\n"
                            f"恢复错误: {str(e)}\n"
                            f"回滚错误: {str(restore_error)}\n\n"
                            f"请手动恢复数据库文件！"
                        )
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"恢复数据库失败: {str(e)}")
    
    def open_table(self, table_name):
        """打开表"""
        self.current_table = table_name
        self.current_table_label.setText(f"当前表: {table_name}")
        self.current_page = 1  # 重置到第一页
        self.load_table_data(table_name, self.current_page)
        self.load_table_structure(table_name)
        self.tab_widget.setCurrentIndex(0)  # 切换到数据标签页
    
    def design_table(self, table_name):
        """设计表"""
        QMessageBox.information(self, "信息", f"表 {table_name} 设计功能开发中...")
    
    def export_table(self, table_name):
        """导出表数据"""
        QMessageBox.information(self, "信息", f"导出表 {table_name} 功能开发中...")
    
    def show_table_context_menu(self, position):
        """显示表格右键菜单"""
        if not self.current_table:
            return
        
        menu = QMenu(self)
        
        # 获取点击位置的行和列
        item = self.data_table.itemAt(position)
        if item:
            # 右键点击具体记录
            row = item.row()
            col = item.column()
            
            # 编辑记录
            edit_action = QAction("编辑记录", self)
            edit_action.triggered.connect(lambda: self.edit_table_row(row))
            menu.addAction(edit_action)
            
            # 删除记录
            delete_action = QAction("删除记录", self)
            delete_action.triggered.connect(lambda: self.delete_specific_row(row))
            menu.addAction(delete_action)
            
            menu.addSeparator()
            
            # 复制记录
            copy_action = QAction("复制记录", self)
            copy_action.triggered.connect(lambda: self.copy_table_row(row))
            menu.addAction(copy_action)
            
        else:
            # 右键点击空白区域
            # 添加新记录
            add_action = QAction("添加新记录", self)
            add_action.triggered.connect(self.add_table_row)
            menu.addAction(add_action)
            
            menu.addSeparator()
            
            # 刷新数据
            refresh_action = QAction("刷新数据", self)
            refresh_action.triggered.connect(self.refresh_table_data)
            menu.addAction(refresh_action)
            
            # 清空表
            clear_action = QAction("清空表", self)
            clear_action.triggered.connect(self.clear_table)
            menu.addAction(clear_action)
        
        if menu.actions():
            menu.exec_(self.data_table.mapToGlobal(position))
    
    def edit_table_row(self, row):
        """编辑表格行"""
        # 双击编辑
        for col in range(self.data_table.columnCount()):
            item = self.data_table.item(row, col)
            if item:
                self.data_table.editItem(item)
                break
    
    def delete_specific_row(self, row):
        """删除指定行"""
        # 获取表的主键信息
        try:
            with get_conn() as conn:
                cursor = conn.execute(f"PRAGMA table_info({self.current_table})")
                columns_info = cursor.fetchall()
                
                # 查找主键列
                pk_columns = []
                for col_info in columns_info:
                    if col_info[5] == 1:  # 是主键
                        pk_columns.append(col_info[1])
                
                if not pk_columns:
                    QMessageBox.warning(self, "警告", "该表没有主键，无法安全删除行")
                    return
                
                # 构建WHERE条件
                where_conditions = []
                for pk_col in pk_columns:
                    pk_col_idx = next(i for i, col in enumerate(columns_info) if col[1] == pk_col)
                    pk_value = self.data_table.item(row, pk_col_idx).text()
                    where_conditions.append(f"{pk_col} = '{pk_value}'")
                
                where_clause = " AND ".join(where_conditions)
                
                # 确认删除
                reply = QMessageBox.question(
                    self, 
                    "确认删除", 
                    f"确定要删除第 {row + 1} 行吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # 执行删除
                    conn.execute(f"DELETE FROM {self.current_table} WHERE {where_clause}")
                    conn.commit()
                    
                    # 刷新表格
                    self.load_table_data(self.current_table, self.current_page)
                    
                    self.status_label.setText(f"已删除第 {row + 1} 行数据")
                    
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除行失败: {str(e)}")
    
    def copy_table_row(self, row):
        """复制表格行"""
        try:
            # 获取行数据
            row_data = []
            for col in range(self.data_table.columnCount()):
                item = self.data_table.item(row, col)
                if item:
                    row_data.append(item.text())
                else:
                    row_data.append("")
            
            # 复制到剪贴板
            clipboard_text = "\t".join(row_data)
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(clipboard_text)
            
            self.status_label.setText("行数据已复制到剪贴板")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"复制行失败: {str(e)}")
    
    def clear_table(self):
        """清空表"""
        if not self.current_table:
            return
        
        # 确认清空
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            f"确定要清空表 {self.current_table} 的所有数据吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with get_conn() as conn:
                    # 清空表数据
                    conn.execute(f"DELETE FROM {self.current_table}")
                    conn.commit()
                    
                    # 刷新表格
                    self.load_table_data(self.current_table, 1)
                    
                    self.status_label.setText(f"表 {self.current_table} 已清空")
                    
            except Exception as e:
                QMessageBox.warning(self, "错误", f"清空表失败: {str(e)}")
    
    def clear_table_from_tree(self, table_name):
        """从树形控件清空表"""
        # 确认清空
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            f"确定要清空表 {table_name} 的所有数据吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                with get_conn() as conn:
                    # 清空表数据
                    conn.execute(f"DELETE FROM {table_name}")
                    conn.commit()
                    
                    # 如果当前选中的是这个表，刷新表格
                    if self.current_table == table_name:
                        self.load_table_data(table_name, 1)
                    
                    self.status_label.setText(f"表 {table_name} 已清空")
                    
            except Exception as e:
                QMessageBox.warning(self, "错误", f"清空表失败: {str(e)}")
    
    def clear_database(self):
        """清空数据库"""
        try:
            from app.db import DatabaseManager, get_conn
            db_manager = DatabaseManager()
            
            # 获取数据库信息
            with get_conn() as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                if not tables:
                    QMessageBox.information(self, "信息", "数据库已经是空的，无需清空")
                    return
                
                # 获取每个表的记录数
                table_info = {}
                total_records = 0
                for table_name, in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                    record_count = cursor.fetchone()[0]
                    table_info[table_name] = record_count
                    total_records += record_count
                
                if total_records == 0:
                    QMessageBox.information(self, "信息", "数据库中没有数据，无需清空")
                    return
            
            # 显示详细的警告信息
            warning_message = f"""
⚠️  危险操作警告 ⚠️

您即将清空整个数据库，这将删除所有数据！

📊 当前数据库包含：
• {len(tables)} 个表
• {total_records} 条记录

📋 将被清空的表：
"""
            
            for table_name, record_count in table_info.items():
                warning_message += f"  • {table_name}: {record_count} 条记录\n"
            
            warning_message += f"""

💾 强烈建议：
1. 在清空前先备份数据库
2. 确认您真的需要清空所有数据
3. 此操作不可撤销！

🔴 确定要继续清空数据库吗？
"""
            
            # 显示确认对话框
            reply = QMessageBox.question(
                self, 
                "⚠️ 确认清空数据库", 
                warning_message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 再次确认
                final_reply = QMessageBox.question(
                    self,
                    "🔴 最终确认",
                    "这是最后一次确认！\n\n"
                    "清空数据库后，所有数据将永久丢失！\n"
                    "此操作不可撤销！\n\n"
                    "确定要清空数据库吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if final_reply == QMessageBox.Yes:
                    # 显示进度对话框
                    progress_dialog = QMessageBox(self)
                    progress_dialog.setWindowTitle("正在清空数据库")
                    progress_dialog.setText("正在清空数据库，请稍候...\n\n注意：请勿关闭此窗口")
                    progress_dialog.setStandardButtons(QMessageBox.Ok)
                    progress_dialog.setModal(False)
                    progress_dialog.show()
                    
                    # 处理事件，让进度对话框显示
                    QApplication.processEvents()
                    
                    try:
                        # 备份当前数据库到程序运行目录
                        try:
                            import shutil
                            from pathlib import Path
                            from datetime import datetime
                            
                            # 获取程序运行目录
                            program_dir = Path.cwd()
                            
                            # 生成备份文件名：当前数据库名_清空前备份_时间戳.db
                            current_db_name = db_manager.db_path.stem
                            backup_filename = f"{current_db_name}_清空前备份_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                            backup_path = program_dir / backup_filename
                            
                            if db_manager.db_path.exists():
                                # 复制当前数据库到程序运行目录
                                shutil.copy2(db_manager.db_path, backup_path)
                                print(f"✅ 数据库已自动备份到: {backup_path}")
                                
                                # 更新进度对话框信息
                                progress_dialog.setText(f"正在清空数据库，请稍候...\n\n已自动备份数据库到:\n{backup_filename}")
                                QApplication.processEvents()
                            else:
                                print("⚠️ 数据库文件不存在，跳过备份")
                                backup_path = None
                                
                        except Exception as e:
                            QMessageBox.warning(self, "警告", f"无法备份数据库: {str(e)}")
                            backup_path = None
                        
                        # 清空数据库
                        with get_conn() as conn:
                            # 禁用外键约束
                            conn.execute("PRAGMA foreign_keys = OFF")
                            
                            # 清空所有表
                            cleared_tables = []
                            for table_name, in tables:
                                conn.execute(f"DELETE FROM {table_name}")
                                cleared_tables.append(table_name)
                            
                            # 重置自增ID
                            for table_name, in tables:
                                conn.execute(f"DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))
                            
                            # 启用外键约束
                            conn.execute("PRAGMA foreign_keys = ON")
                            
                            conn.commit()
                        
                        # 关闭进度对话框
                        progress_dialog.close()
                        
                        # 刷新界面
                        self.load_database_info()
                        self.load_table_list()
                        
                        # 更新数据库信息显示
                        self.update_db_info_display()
                        
                        # 清空当前选择
                        self.current_table = None
                        self.current_table_label.setText("当前表: 未选择")
                        self.data_table.setRowCount(0)
                        self.data_table.setColumnCount(0)
                        self.structure_table.setRowCount(0)
                        
                        self.status_label.setText(f"✅ 数据库清空成功！已清空 {len(cleared_tables)} 个表")
                        
                        # 显示成功信息
                        success_message = f"✅ 数据库清空成功！\n\n"
                        success_message += f"📊 已清空 {len(cleared_tables)} 个表:\n"
                        for table_name in cleared_tables:
                            success_message += f"  • {table_name}\n"
                        success_message += f"\n🔄 数据库已重置为初始状态。\n\n"
                        
                        if backup_path and backup_path.exists():
                            success_message += f"💾 重要提示：原数据库已自动备份到程序目录:\n"
                            success_message += f"   文件名：{backup_path.name}\n"
                            success_message += f"   位置：{backup_path.parent}\n\n"
                            success_message += f"📝 如需恢复原数据，请使用此备份文件。"
                        else:
                            success_message += f"⚠️ 警告：数据库备份失败，请手动检查数据完整性"
                        
                        QMessageBox.information(
                            self, 
                            "✅ 清空成功", 
                            success_message
                        )
                        
                    except Exception as e:
                        # 关闭进度对话框
                        progress_dialog.close()
                        
                        QMessageBox.critical(
                            self, 
                            "❌ 清空失败", 
                            f"清空数据库失败！\n\n"
                            f"错误详情: {str(e)}\n\n"
                            f"请检查数据库文件权限或联系技术支持。"
                        )
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"清空数据库失败: {str(e)}")
