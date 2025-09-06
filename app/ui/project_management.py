#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QMessageBox, QDialog,
    QDialogButtonBox, QFormLayout, QTextEdit, QHeaderView, QFrame,
    QGroupBox, QCheckBox, QSplitter, QAbstractItemView, QSizePolicy,
    QSpinBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon

from app.services.project_service import ProjectService

class ProjectMappingDialog(QDialog):
    """项目映射编辑对话框"""
    
    def __init__(self, parent=None, mapping_data=None):
        super().__init__(parent)
        self.mapping_data = mapping_data
        self.is_edit_mode = mapping_data is not None
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        self.setWindowTitle("编辑项目映射" if self.is_edit_mode else "新建项目映射")
        self.setModal(True)
        self.resize(600, 500)
        self.setMinimumSize(500, 400)
        self.setMaximumSize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("编辑项目映射" if self.is_edit_mode else "新建项目映射")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                padding: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # 项目代码
        self.project_code_edit = QLineEdit()
        self.project_code_edit.setPlaceholderText("请输入项目代码")
        form_layout.addRow("项目代码 *:", self.project_code_edit)
        
        # 项目名称
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText("请输入项目名称")
        form_layout.addRow("项目名称 *:", self.project_name_edit)
        
        # 物料选择
        self.item_combo = QComboBox()
        self.item_combo.setEditable(False)
        self.load_items()
        form_layout.addRow("成品物料 *:", self.item_combo)
        
        # 备注
        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(100)
        self.remark_edit.setPlaceholderText("请输入备注信息")
        form_layout.addRow("备注:", self.remark_edit)
        
        main_layout.addLayout(form_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #666;
                border: 1px solid #ccc;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #1890ff;
                color: #1890ff;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLineEdit, QComboBox, QTextEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                min-width: 200px;
                min-height: 15px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border-color: #1890ff;
            }
        """)
    
    def load_items(self):
        """加载成品物料列表"""
        try:
            items = ProjectService.get_available_finished_goods()
            self.item_combo.clear()
            
            for item in items:
                # 显示格式：编码 - 名称 (品牌: 品牌值)
                brand_text = f" (品牌: {item['Brand']})" if item['Brand'] else " (品牌: 无)"
                display_text = f"{item['ItemCode']} - {item['CnName']}{brand_text}"
                self.item_combo.addItem(display_text, item['ItemId'])
            
            print(f"📊 [load_items] 加载了 {len(items)} 个成品物料")
            
        except Exception as e:
            print(f"❌ [load_items] 加载成品物料失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载成品物料失败: {str(e)}")
    
    def load_data(self):
        """加载现有数据（编辑模式）"""
        if self.is_edit_mode and self.mapping_data:
            self.project_code_edit.setText(self.mapping_data.get('ProjectCode', ''))
            self.project_name_edit.setText(self.mapping_data.get('ProjectName', ''))
            self.remark_edit.setPlainText(self.mapping_data.get('Remark', ''))
            
            # 设置物料选择
            item_id = self.mapping_data.get('ItemId')
            if item_id:
                for i in range(self.item_combo.count()):
                    if self.item_combo.itemData(i) == item_id:
                        self.item_combo.setCurrentIndex(i)
                        break
    
    def get_form_data(self):
        """获取表单数据"""
        project_code = self.project_code_edit.text().strip()
        project_name = self.project_name_edit.text().strip()
        item_id = self.item_combo.currentData()
        remark = self.remark_edit.toPlainText().strip()
        
        return {
            'project_code': project_code,
            'project_name': project_name,
            'item_id': item_id,
            'remark': remark
        }
    
    def accept(self):
        """确认保存"""
        data = self.get_form_data()
        
        # 验证必填字段
        if not data['project_code']:
            QMessageBox.warning(self, "验证错误", "请输入项目代码")
            return
        
        if not data['project_name']:
            QMessageBox.warning(self, "验证错误", "请输入项目名称")
            return
        
        if not data['item_id']:
            QMessageBox.warning(self, "验证错误", "请选择成品物料")
            return
        
        super().accept()

class OrderAdjustDialog(QDialog):
    """顺序调整对话框"""
    
    def __init__(self, parent=None, mapping_id=None, project_code=None, current_order=None):
        super().__init__(parent)
        self.mapping_id = mapping_id
        self.project_code = project_code
        self.current_order = current_order
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("调整项目顺序")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("调整项目顺序")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 项目信息
        info_label = QLabel(f"项目代码: {self.project_code}")
        info_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(info_label)
        
        # 当前顺序
        current_label = QLabel(f"当前顺序: {self.current_order}")
        current_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(current_label)
        
        # 新顺序输入
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("新顺序:"))
        
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 9999)
        self.order_spin.setValue(self.current_order)
        self.order_spin.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                min-width: 100px;
            }
            QSpinBox:focus {
                border-color: #1890ff;
            }
        """)
        order_layout.addWidget(self.order_spin)
        order_layout.addStretch()
        
        layout.addLayout(order_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #666;
                border: 1px solid #ccc;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #1890ff;
                color: #1890ff;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def get_new_order(self):
        """获取新的顺序值"""
        return self.order_spin.value()

class ProjectManagementWidget(QWidget):
    """项目管理主界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 设置主窗口尺寸策略
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)
        
        # 按钮栏
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        
        # 新建映射按钮
        self.add_btn = QPushButton("新建映射")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 90px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
            QPushButton:pressed {
                background: #096dd9;
            }
        """)
        self.add_btn.clicked.connect(self.add_mapping)
        
        # 编辑映射按钮
        self.edit_btn = QPushButton("编辑映射")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #1890ff;
                border: 1px solid #1890ff;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 90px;
            }
            QPushButton:hover {
                background: #1890ff;
                color: white;
            }
            QPushButton:disabled {
                background: #f5f5f5;
                color: #bfbfbf;
                border: 1px solid #d9d9d9;
            }
        """)
        self.edit_btn.clicked.connect(self.edit_mapping)
        self.edit_btn.setEnabled(False)
        
        # 删除映射按钮
        self.delete_btn = QPushButton("删除映射")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #ff4d4f;
                border: 1px solid #ff4d4f;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 90px;
            }
            QPushButton:hover {
                background: #ff4d4f;
                color: white;
            }
            QPushButton:disabled {
                background: #f5f5f5;
                color: #bfbfbf;
                border: 1px solid #d9d9d9;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_mapping)
        self.delete_btn.setEnabled(False)
        
        # 切换状态按钮
        self.toggle_status_btn = QPushButton("切换状态")
        self.toggle_status_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #faad14;
                border: 1px solid #faad14;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 90px;
            }
            QPushButton:hover {
                background: #faad14;
                color: white;
            }
            QPushButton:disabled {
                background: #f5f5f5;
                color: #bfbfbf;
                border: 1px solid #d9d9d9;
            }
        """)
        self.toggle_status_btn.clicked.connect(self.toggle_status)
        self.toggle_status_btn.setEnabled(False)
        
        # 调整顺序按钮
        self.adjust_order_btn = QPushButton("调整顺序")
        self.adjust_order_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #722ed1;
                border: 1px solid #722ed1;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 90px;
            }
            QPushButton:hover {
                background: #722ed1;
                color: white;
            }
            QPushButton:disabled {
                background: #f5f5f5;
                color: #bfbfbf;
                border: 1px solid #d9d9d9;
            }
        """)
        self.adjust_order_btn.clicked.connect(self.adjust_order)
        self.adjust_order_btn.setEnabled(False)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #595959;
                border: 1px solid #d9d9d9;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 70px;
            }
            QPushButton:hover {
                background: #f5f5f5;
                border: 1px solid #40a9ff;
                color: #40a9ff;
            }
        """)
        self.refresh_btn.clicked.connect(self.load_data)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.toggle_status_btn)
        button_layout.addWidget(self.adjust_order_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_frame)
        
        # 搜索框和按钮
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)
        
        search_label = QLabel("搜索:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入项目代码、项目名称、物料编码或品牌搜索...")
        self.search_edit.textChanged.connect(self.filter_data)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 14px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 13px;
                min-width: 280px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #1890ff;
                box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
            }
        """)
        
        # 清空搜索按钮
        self.clear_search_btn = QPushButton("清空")
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #595959;
                border: 1px solid #d9d9d9;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 70px;
            }
            QPushButton:hover {
                background: #f5f5f5;
                border: 1px solid #40a9ff;
                color: #40a9ff;
            }
        """)
        self.clear_search_btn.clicked.connect(self.clear_search)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.clear_search_btn)
        
        layout.addWidget(search_frame)
        
        # 表格
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        # 设置表格样式
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e9ecef;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e3f2fd;
                selection-color: #1a1a1a;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: 600;
                font-size: 13px;
                position: relative;
            }
            QHeaderView::section:hover {
                background-color: #e9ecef;
            }
            QHeaderView::section:checked {
                background-color: #1890ff;
                color: white;
            }
        """)
        
        # 设置行号列样式
        self.table.verticalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                padding: 8px 4px;
                border: none;
                border-right: 1px solid #dee2e6;
                font-size: 13px;
                font-weight: 500;
                text-align: center;
            }
        """)
        
        # 设置表格属性
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 设置行高
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.verticalHeader().setMinimumSectionSize(40)
        
        # 设置表格尺寸策略
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 设置表格列
        headers = [
            "顺序", "映射ID", "项目代码", "项目名称", "物料编码", 
            "物料名称", "品牌", "状态", "创建时间", "备注"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # 调整列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 顺序
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 映射ID
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 项目代码
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # 项目名称
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 物料编码
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # 物料名称
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 品牌
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # 创建时间
        header.setSectionResizeMode(9, QHeaderView.Stretch)           # 备注
        
        layout.addWidget(self.table)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.status_label)
    
    def load_data(self):
        """加载项目映射数据"""
        try:
            self.status_label.setText("正在加载数据...")
            
            mappings = ProjectService.get_all_project_mappings()
            self.all_mappings = mappings
            
            self.populate_table(mappings)
            self.status_label.setText(f"已加载 {len(mappings)} 条映射记录")
            
        except Exception as e:
            print(f"❌ [load_data] 加载数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载数据失败: {str(e)}")
            self.status_label.setText("加载失败")
    
    def populate_table(self, mappings):
        """填充表格数据"""
        self.table.setRowCount(len(mappings))
        
        for row, mapping in enumerate(mappings):
            # 顺序
            display_order = mapping.get('DisplayOrder', 0)
            self.table.setItem(row, 0, QTableWidgetItem(str(display_order)))
            
            # 映射ID
            self.table.setItem(row, 1, QTableWidgetItem(str(mapping.get('MappingId', ''))))
            
            # 项目代码
            self.table.setItem(row, 2, QTableWidgetItem(mapping.get('ProjectCode', '')))
            
            # 项目名称
            self.table.setItem(row, 3, QTableWidgetItem(mapping.get('ProjectName', '')))
            
            # 物料编码
            self.table.setItem(row, 4, QTableWidgetItem(mapping.get('ItemCode', '')))
            
            # 物料名称
            self.table.setItem(row, 5, QTableWidgetItem(mapping.get('ItemName', '')))
            
            # 品牌
            brand_text = mapping.get('Brand', '') or '无'
            self.table.setItem(row, 6, QTableWidgetItem(brand_text))
            
            # 状态（可点击切换）
            status = "启用" if mapping.get('IsActive', False) else "禁用"
            status_item = QTableWidgetItem(status)
            status_item.setData(Qt.UserRole, mapping.get('MappingId'))  # 存储映射ID
            self.table.setItem(row, 7, status_item)
            
            # 创建时间
            created_date = mapping.get('CreatedDate', '')
            if created_date:
                # 只显示日期部分
                date_part = created_date.split(' ')[0] if ' ' in created_date else created_date
                self.table.setItem(row, 8, QTableWidgetItem(date_part))
            else:
                self.table.setItem(row, 8, QTableWidgetItem(''))
            
            # 备注
            self.table.setItem(row, 9, QTableWidgetItem(mapping.get('Remark', '')))
    
    def filter_data(self):
        """过滤数据"""
        search_text = self.search_edit.text().strip().lower()
        
        if not search_text:
            self.populate_table(self.all_mappings)
            return
        
        filtered_mappings = []
        for mapping in self.all_mappings:
            # 搜索项目代码、项目名称、物料编码、物料名称、品牌
            if (search_text in mapping.get('ProjectCode', '').lower() or
                search_text in mapping.get('ProjectName', '').lower() or
                search_text in mapping.get('ItemCode', '').lower() or
                search_text in mapping.get('ItemName', '').lower() or
                search_text in (mapping.get('Brand', '') or '').lower()):
                filtered_mappings.append(mapping)
        
        self.populate_table(filtered_mappings)
    
    def clear_search(self):
        """清空搜索"""
        self.search_edit.clear()
        self.populate_table(self.all_mappings)
    
    def on_selection_changed(self):
        """选择改变时的处理"""
        has_selection = len(self.table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.toggle_status_btn.setEnabled(has_selection)
        self.adjust_order_btn.setEnabled(has_selection)
    
    def add_mapping(self):
        """添加新映射"""
        dialog = ProjectMappingDialog(self)
        if dialog.exec() == QDialog.Accepted:
            try:
                data = dialog.get_form_data()
                
                ProjectService.create_project_mapping(
                    project_code=data['project_code'],
                    project_name=data['project_name'],
                    item_id=data['item_id'],
                    created_by="系统用户",
                    remark=data['remark']
                )
                
                QMessageBox.information(self, "成功", "项目映射创建成功！")
                self.load_data()
                
            except Exception as e:
                print(f"❌ [add_mapping] 创建映射失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"创建映射失败: {str(e)}")
    
    def edit_mapping(self):
        """编辑映射"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            return
        
        mapping_id = int(self.table.item(selected_row, 1).text())  # 映射ID现在是第1列
        
        try:
            mapping_data = ProjectService.get_project_mapping_by_id(mapping_id)
            if not mapping_data:
                QMessageBox.warning(self, "错误", "找不到指定的映射记录")
                return
            
            dialog = ProjectMappingDialog(self, mapping_data)
            if dialog.exec() == QDialog.Accepted:
                data = dialog.get_form_data()
                
                ProjectService.update_project_mapping(
                    mapping_id=mapping_id,
                    project_code=data['project_code'],
                    project_name=data['project_name'],
                    updated_by="系统用户",
                    remark=data['remark']
                )
                
                QMessageBox.information(self, "成功", "项目映射更新成功！")
                self.load_data()
                
        except Exception as e:
            print(f"❌ [edit_mapping] 更新映射失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"更新映射失败: {str(e)}")
    
    def delete_mapping(self):
        """删除映射"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            return
        
        mapping_id = int(self.table.item(selected_row, 1).text())  # 映射ID现在是第1列
        project_code = self.table.item(selected_row, 2).text()  # 项目代码现在是第2列
        item_code = self.table.item(selected_row, 4).text()  # 物料编码现在是第4列
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除项目映射吗？\n\n项目: {project_code}\n物料: {item_code}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                ProjectService.delete_project_mapping(mapping_id)
                QMessageBox.information(self, "成功", "项目映射删除成功！")
                self.load_data()
                
            except Exception as e:
                print(f"❌ [delete_mapping] 删除映射失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"删除映射失败: {str(e)}")
    
    def toggle_status(self):
        """切换映射状态"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            return
        
        mapping_id = int(self.table.item(selected_row, 1).text())  # 映射ID现在是第1列
        project_code = self.table.item(selected_row, 2).text()  # 项目代码现在是第2列
        current_status = self.table.item(selected_row, 7).text()  # 状态现在是第7列
        
        try:
            ProjectService.toggle_mapping_status(mapping_id)
            
            new_status = "禁用" if current_status == "启用" else "启用"
            QMessageBox.information(self, "成功", f"项目映射状态已切换为：{new_status}")
            self.load_data()
            
        except Exception as e:
            print(f"❌ [toggle_status] 切换状态失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"切换状态失败: {str(e)}")
    
    def adjust_order(self):
        """调整映射顺序"""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            return
        
        mapping_id = int(self.table.item(selected_row, 1).text())  # 映射ID现在是第1列
        project_code = self.table.item(selected_row, 2).text()  # 项目代码现在是第2列
        current_order = int(self.table.item(selected_row, 0).text())  # 顺序现在是第0列
        
        # 创建顺序调整对话框
        dialog = OrderAdjustDialog(self, mapping_id, project_code, current_order)
        if dialog.exec() == QDialog.Accepted:
            new_order = dialog.get_new_order()
            try:
                ProjectService.update_mapping_order(mapping_id, new_order)
                QMessageBox.information(self, "成功", f"项目映射顺序已更新为：{new_order}")
                self.load_data()
                
            except Exception as e:
                print(f"❌ [adjust_order] 调整顺序失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"调整顺序失败: {str(e)}")
