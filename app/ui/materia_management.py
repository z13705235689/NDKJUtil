from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QFrame, QLineEdit, QComboBox, QSpinBox, 
                               QDoubleSpinBox, QDateEdit, QMessageBox,
                               QTabWidget, QHeaderView, QAbstractItemView,
                               QGroupBox, QFormLayout, QTextEdit, QDialog,
                               QCheckBox, QDialogButtonBox, QGridLayout,
                               QSpacerItem, QSizePolicy, QScrollArea,
                               QRadioButton, QButtonGroup, QTreeWidget, 
                               QTreeWidgetItem, QFileDialog, QProgressBar,
                               QPlainTextEdit, QSplitter, QMenu, QApplication)
from PySide6.QtCore import Qt, QDate, QThread, Signal
from PySide6.QtGui import QFont, QColor
from app.services.item_service import ItemService
from app.services.bom_service import BomService
from app.services.item_import_service import ItemImportService


class ItemAddDialog(QDialog):
    """物料新增对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增物料")
        self.resize(550, 650)
        self.setMinimumSize(500, 500)
        self.setMaximumSize(800, 900)
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("新增物料")
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
        
        # 物资编码
        self.item_code_edit = QLineEdit()
        self.item_code_edit.setPlaceholderText("请输入物资编码")
        form_layout.addRow("物资编码 *:", self.item_code_edit)
        
        # 物资名称
        self.item_name_edit = QLineEdit()
        self.item_name_edit.setPlaceholderText("请输入物资名称")
        form_layout.addRow("物资名称 *:", self.item_name_edit)
        
        # 物资规格
        self.item_spec_edit = QLineEdit()
        self.item_spec_edit.setPlaceholderText("请输入物资规格")
        form_layout.addRow("物资规格:", self.item_spec_edit)
        
        # 物资类型
        self.item_type_combo = QComboBox()
        self.item_type_combo.addItems(["FG - 成品", "SFG - 半成品", "RM - 原材料", "PKG - 包装材料"])
        self.item_type_combo.currentTextChanged.connect(self.on_item_type_changed)
        form_layout.addRow("物资类型 *:", self.item_type_combo)
        
        # 单位
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["个", "件", "米", "千克", "升", "套", "包", "箱"])
        form_layout.addRow("单位 *:", self.unit_combo)
        
        # 组成数量
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 999999)
        self.quantity_spin.setDecimals(2)
        self.quantity_spin.setValue(1.0)
        form_layout.addRow("组成数量 *:", self.quantity_spin)
        
        # 安全库存
        self.safety_stock_spin = QDoubleSpinBox()
        self.safety_stock_spin.setRange(0, 999999)
        self.safety_stock_spin.setDecimals(2)
        self.safety_stock_spin.setValue(0)
        form_layout.addRow("安全库存:", self.safety_stock_spin)
        
        # 归属物资
        parent_layout = QHBoxLayout()
        self.parent_item_combo = QComboBox()
        self.parent_item_combo.setPlaceholderText("请选择上级物资")
        self.parent_item_combo.setEnabled(False)
        self.parent_item_combo.setEditable(True)  # 设为可编辑以支持搜索
        
        # 刷新上级物资按钮
        refresh_parent_btn = QPushButton("🔄")
        refresh_parent_btn.setMaximumWidth(30)
        refresh_parent_btn.setToolTip("刷新上级物资列表")
        refresh_parent_btn.clicked.connect(self.load_parent_items)
        refresh_parent_btn.setStyleSheet("""
            QPushButton {
                background: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
        """)
        
        parent_layout.addWidget(self.parent_item_combo)
        parent_layout.addWidget(refresh_parent_btn)
        form_layout.addRow("归属物资:", parent_layout)
        
        # 商品品牌
        self.brand_edit = QLineEdit()
        self.brand_edit.setPlaceholderText("请输入商品品牌（仅成品物料）")
        self.brand_edit.setEnabled(False)  # 默认禁用
        form_layout.addRow("商品品牌:", self.brand_edit)
        
        # 备注
        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(60)
        self.remark_edit.setPlaceholderText("请输入备注信息")
        form_layout.addRow("备注:", self.remark_edit)
        
        main_layout.addLayout(form_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        # 确定按钮
        confirm_btn = QPushButton("确定")
        confirm_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)
        
        main_layout.addLayout(button_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                min-width: 200px;
                min-height: 15px;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
                border-color: #1890ff;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton[text="确定"] {
                background: #1890ff;
                color: white;
                border: none;
            }
            QPushButton[text="确定"]:hover {
                background: #40a9ff;
            }
            QPushButton[text="取消"] {
                background: white;
                color: #666;
                border: 1px solid #ccc;
            }
            QPushButton[text="取消"]:hover {
                border-color: #1890ff;
                color: #1890ff;
            }
        """)
        
        # 初始化时加载上级物资列表
        self.load_parent_items()
        
        # 初始化时设置商品品牌字段的状态
        self.on_item_type_changed()
    
    def on_item_type_changed(self):
        """物资类型改变时的处理"""
        current_type = self.item_type_combo.currentText()
        
        # 根据物料类型启用/禁用上级物资选择
        # 逻辑：原材料(RM)和包装材料(PKG)通常没有上级物资
        # 半成品(SFG)和成品(FG)可能有上级物资
        if current_type in ["SFG - 半成品", "FG - 成品"]:
            self.parent_item_combo.setEnabled(True)
        else:
            self.parent_item_combo.setEnabled(False)
            self.parent_item_combo.setCurrentIndex(0)  # 设置为"无"
        
        # 根据物料类型启用/禁用商品品牌字段
        # 只有成品(FG)才启用商品品牌字段
        if current_type == "FG - 成品":
            self.brand_edit.setEnabled(True)
            self.brand_edit.setStyleSheet("")  # 恢复正常样式
        else:
            self.brand_edit.setEnabled(False)
            self.brand_edit.clear()  # 清空内容
            self.brand_edit.setStyleSheet("background-color: #f5f5f5;")  # 设置禁用样式
    
    def load_parent_items(self):
        """加载上级物资列表"""
        try:
            # 获取所有物资作为上级物资选项
            items = ItemService.get_parent_items()
            self.parent_item_combo.clear()
            self.parent_item_combo.addItem("无", None)  # 空选项
            
            current_type = None
            for item in items:
                # 按类型分组显示
                if current_type != item['ItemType']:
                    current_type = item['ItemType']
                    type_name = {
                        'FG': '成品',
                        'SFG': '半成品', 
                        'RM': '原材料',
                        'PKG': '包装材料'
                    }.get(item['ItemType'], item['ItemType'])
                    
                    # 添加分组标题（禁用选择）
                    self.parent_item_combo.addItem(f"--- {type_name} ---", None)
                    self.parent_item_combo.setItemData(
                        self.parent_item_combo.count() - 1, 
                        False, 
                        Qt.UserRole - 1  # 设为不可选择
                    )
                
                display_text = f"  {item['ItemCode']} - {item['CnName']}"
                self.parent_item_combo.addItem(display_text, item['ItemId'])
                
        except Exception as e:
            print(f"加载上级物资失败: {e}")
    
    def get_item_data(self):
        """获取表单数据"""
        # 获取上级物资ID
        parent_item_id = None
        if self.parent_item_combo.currentData() is not None:
            parent_item_id = self.parent_item_combo.currentData()
        
        # 提取类型代码（FG, SFG, RM, PKG）
        item_type_text = self.item_type_combo.currentText()
        item_type = item_type_text.split(" - ")[0]
        
        return {
            'ItemCode': self.item_code_edit.text().strip(),
            'CnName': self.item_name_edit.text().strip(),
            'ItemSpec': self.item_spec_edit.text().strip(),
            'ItemType': item_type,
            'Unit': self.unit_combo.currentText(),
            'Quantity': self.quantity_spin.value(),
            'SafetyStock': self.safety_stock_spin.value(),
            'Remark': self.remark_edit.toPlainText().strip(),
            'Brand': self.brand_edit.text().strip() if item_type == 'FG' else '',
            'ParentItemId': parent_item_id
        }


class ItemEditDialog(QDialog):
    """物料编辑对话框"""
    
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.setWindowTitle("编辑物料")
        self.resize(500, 600)
        self.setMinimumSize(450, 500)
        self.setMaximumSize(800, 900)
        self.setModal(True)
        self.setup_ui()
        self.load_item_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_group.setStyleSheet("""
            QGroupBox {
                font-weight: 500;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: #262626;
            }
        """)
        
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(8)
        
        # 物资编码
        self.item_code_edit = QLineEdit()
        self.item_code_edit.setPlaceholderText("请输入物资编码")
        basic_layout.addRow("物资编码*:", self.item_code_edit)
        
        # 物资名称
        self.item_name_edit = QLineEdit()
        self.item_name_edit.setPlaceholderText("请输入物资名称")
        basic_layout.addRow("物资名称*:", self.item_name_edit)
        
        # 物资规格
        self.item_spec_edit = QLineEdit()
        self.item_spec_edit.setPlaceholderText("请输入物资规格")
        basic_layout.addRow("物资规格:", self.item_spec_edit)
        
        # 物资类型
        self.item_type_combo = QComboBox()
        self.item_type_combo.addItems([
            "FG - 成品", "SFG - 半成品", "RM - 原材料", "PKG - 包装材料"
        ])
        self.item_type_combo.currentTextChanged.connect(self.on_item_type_changed)
        basic_layout.addRow("物资类型*:", self.item_type_combo)
        
        # 单位
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["个", "件", "米", "千克", "升", "套", "包", "箱"])
        basic_layout.addRow("单位*:", self.unit_combo)
        
        # 组成数量
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 999999)
        self.quantity_spin.setDecimals(2)
        self.quantity_spin.setValue(1.0)
        basic_layout.addRow("组成数量*:", self.quantity_spin)
        
        # 安全库存
        self.safety_stock_spin = QDoubleSpinBox()
        self.safety_stock_spin.setRange(0, 999999)
        self.safety_stock_spin.setDecimals(2)
        self.safety_stock_spin.setValue(0)
        basic_layout.addRow("安全库存:", self.safety_stock_spin)
        
        # 归属物资
        self.parent_item_combo = QComboBox()
        self.parent_item_combo.setPlaceholderText("请选择上级物资")
        basic_layout.addRow("归属物资:", self.parent_item_combo)
        
        # 商品品牌
        self.brand_edit = QLineEdit()
        self.brand_edit.setPlaceholderText("请输入商品品牌（仅成品物料）")
        self.brand_edit.setEnabled(False)  # 默认禁用
        basic_layout.addRow("商品品牌:", self.brand_edit)
        
        # 备注
        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(60)
        self.remark_edit.setPlaceholderText("请输入备注信息")
        basic_layout.addRow("备注:", self.remark_edit)
        
        scroll_layout.addWidget(basic_group)
        


        
        # 设置滚动区域
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(500)
        layout.addWidget(scroll_area)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 6px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                padding: 8px 10px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 13px;
                min-height: 18px;
                background: white;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
                border-color: #1890ff;
                box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
            }
            QLabel {
                font-weight: 500;
                color: #262626;
                font-size: 13px;
            }
            QDialogButtonBox QPushButton {
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 70px;
            }
            QDialogButtonBox QPushButton[text="OK"] {
                background: #1890ff;
                color: white;
                border: none;
            }
            QDialogButtonBox QPushButton[text="OK"]:hover {
                background: #40a9ff;
            }
            QDialogButtonBox QPushButton[text="Cancel"] {
                background: white;
                color: #595959;
                border: 1px solid #d9d9d9;
            }
            QDialogButtonBox QPushButton[text="Cancel"]:hover {
                border-color: #40a9ff;
                color: #40a9ff;
            }
        """)
        
        # 初始化时加载上级物资列表
        self.load_parent_items()
        
        # 初始化时设置商品品牌字段的状态
        self.on_item_type_changed()
    
    def on_item_type_changed(self):
        """物资类型改变时的处理"""
        current_type = self.item_type_combo.currentText()
        
        # 根据物料类型启用/禁用商品品牌字段
        # 只有成品(FG)才启用商品品牌字段
        if current_type == "FG - 成品":
            self.brand_edit.setEnabled(True)
            self.brand_edit.setStyleSheet("")  # 恢复正常样式
        else:
            self.brand_edit.setEnabled(False)
            self.brand_edit.clear()  # 清空内容
            self.brand_edit.setStyleSheet("background-color: #f5f5f5;")  # 设置禁用样式
    
    def load_parent_items(self):
        """加载上级物资列表"""
        try:
            # 获取所有物资作为上级物资选项（编辑时排除自己）
            exclude_id = None
            if hasattr(self, 'item_data') and self.item_data and 'ItemId' in self.item_data:
                exclude_id = self.item_data['ItemId']
            
            items = ItemService.get_parent_items(exclude_id)
            self.parent_item_combo.clear()
            self.parent_item_combo.addItem("无", None)  # 空选项
            
            current_type = None
            for item in items:
                # 按类型分组显示
                if current_type != item['ItemType']:
                    current_type = item['ItemType']
                    type_name = {
                        'FG': '成品',
                        'SFG': '半成品', 
                        'RM': '原材料',
                        'PKG': '包装材料'
                    }.get(item['ItemType'], item['ItemType'])
                    
                    # 添加分组标题（禁用选择）
                    self.parent_item_combo.addItem(f"--- {type_name} ---", None)
                    self.parent_item_combo.setItemData(
                        self.parent_item_combo.count() - 1, 
                        False, 
                        Qt.UserRole - 1  # 设为不可选择
                    )
                
                display_text = f"  {item['ItemCode']} - {item['CnName']}"
                self.parent_item_combo.addItem(display_text, item['ItemId'])
                
        except Exception as e:
            print(f"加载上级物资失败: {e}")
    
    def load_item_data(self):
        """加载物料数据到表单"""
        try:
            print(f"正在加载物料数据: {self.item_data}")  # 调试信息
            
            # 基本信息 - 使用字典式访问
            self.item_code_edit.setText(str(self.item_data['ItemCode'] if self.item_data['ItemCode'] else ''))
            self.item_name_edit.setText(str(self.item_data['CnName'] if self.item_data['CnName'] else ''))
            self.item_spec_edit.setText(str(self.item_data['ItemSpec'] if self.item_data['ItemSpec'] else ''))
            
            # 设置物料类型
            item_type = self.item_data['ItemType'] if self.item_data['ItemType'] else 'RM'
            print(f"物料类型: {item_type}")  # 调试信息
            
            for i in range(self.item_type_combo.count()):
                combo_text = self.item_type_combo.itemText(i)
                print(f"检查类型 {i}: {combo_text}")  # 调试信息
                if combo_text.startswith(item_type):
                    self.item_type_combo.setCurrentIndex(i)
                    print(f"设置类型索引: {i}")  # 调试信息
                    break
            
            self.unit_combo.setCurrentText(str(self.item_data['Unit'] if self.item_data['Unit'] else '个'))
            self.quantity_spin.setValue(float(self.item_data['Quantity'] if self.item_data['Quantity'] else 1.0))
            self.safety_stock_spin.setValue(float(self.item_data['SafetyStock'] if self.item_data['SafetyStock'] else 0))
            
            # 设置归属物资
            parent_item_id = self.item_data['ParentItemId'] if self.item_data['ParentItemId'] else None
            if parent_item_id:
                for i in range(self.parent_item_combo.count()):
                    if self.parent_item_combo.itemData(i) == parent_item_id:
                        self.parent_item_combo.setCurrentIndex(i)
                        break
            
            # 设置商品品牌
            self.brand_edit.setText(str(self.item_data['Brand'] if self.item_data['Brand'] else ''))
            # 根据物料类型启用/禁用商品品牌字段
            if item_type == 'FG':
                self.brand_edit.setEnabled(True)
                self.brand_edit.setStyleSheet("")
            else:
                self.brand_edit.setEnabled(False)
                self.brand_edit.setStyleSheet("background-color: #f5f5f5;")
            
            self.remark_edit.setPlainText(str(self.item_data['Remark'] if self.item_data['Remark'] else ''))
            
            print("物料数据加载完成")  # 调试信息
            
        except Exception as e:
            print(f"加载物料数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def get_updated_item_data(self):
        """获取更新后的物料数据"""
        # 提取类型代码（FG, SFG, RM, PKG）
        item_type_text = self.item_type_combo.currentText()
        item_type = item_type_text.split(" - ")[0]
        
        # 获取上级物资ID
        parent_item_id = None
        if self.parent_item_combo.currentData() is not None:
            parent_item_id = self.parent_item_combo.currentData()
        
        return {
            'ItemCode': self.item_code_edit.text().strip(),
            'CnName': self.item_name_edit.text().strip(),
            'ItemSpec': self.item_spec_edit.text().strip(),
            'ItemType': item_type,
            'Unit': self.unit_combo.currentText(),
            'Quantity': self.quantity_spin.value(),
            'SafetyStock': self.safety_stock_spin.value(),
            'Remark': self.remark_edit.toPlainText().strip(),
            'Brand': self.brand_edit.text().strip() if item_type == 'FG' else '',
            'ParentItemId': parent_item_id
        }


class ItemEditor(QWidget):
    """物料编辑器UI"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_items = []  # 存储选中的物料ID
        self.setup_ui()
        self.load_items()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)  # 减小边距
        layout.setSpacing(16)  # 减小间距
        
        # 设置主窗口尺寸策略
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)
        
        # 按钮栏
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)  # 减小间距
        
        # 新增物料按钮
        self.add_btn = QPushButton("新增物料")
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
        self.add_btn.clicked.connect(self.add_item)
        
        # 导入物料按钮
        self.import_btn = QPushButton("导入物料")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background: #52c41a;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 90px;
            }
            QPushButton:hover {
                background: #73d13d;
            }
            QPushButton:pressed {
                background: #389e0d;
            }
        """)
        self.import_btn.clicked.connect(self.import_items)
        
        # 删除选中按钮
        self.delete_btn = QPushButton("删除选中")
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
        self.delete_btn.clicked.connect(self.delete_selected_items)
        self.delete_btn.setEnabled(False)
        
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
        self.refresh_btn.clicked.connect(self.load_items)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.refresh_btn)
        
        # 全选按钮
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #1890ff;
                border: 1px solid #1890ff;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 70px;
            }
            QPushButton:hover {
                background: #1890ff;
                color: white;
            }
        """)
        self.select_all_btn.clicked.connect(self.select_all_items)
        
        button_layout.addWidget(self.select_all_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_frame)
        
        # 搜索框和按钮
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)
        
        search_label = QLabel("搜索:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入物料编码、名称、规格或商品品牌搜索...")
        self.search_edit.textChanged.connect(self.on_search_text_changed)  # 添加实时搜索
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
        
        # 搜索按钮
        self.search_btn = QPushButton("搜索")
        self.search_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 70px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        self.search_btn.clicked.connect(self.search_items)
        
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
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_search_btn)
        
        # 添加物料类型筛选
        filter_label = QLabel("物料类型:")
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItem("全部", "")
        self.type_filter_combo.addItem("成品", "FG")
        self.type_filter_combo.addItem("半成品", "SFG")
        self.type_filter_combo.addItem("原材料", "RM")
        self.type_filter_combo.addItem("包装材料", "PKG")
        self.type_filter_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 14px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 13px;
                min-width: 120px;
                background: white;
            }
            QComboBox:focus {
                border-color: #1890ff;
                box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
            }
        """)
        self.type_filter_combo.currentTextChanged.connect(self.filter_by_type)
        
        search_layout.addWidget(filter_label)
        search_layout.addWidget(self.type_filter_combo)
        search_layout.addStretch()
        
        layout.addWidget(search_frame)
        
        # 物料表格
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(10)  # 选择列 + 9个数据列
        self.items_table.setHorizontalHeaderLabels([
            "全选", "物资编码", "物资名称", "物资规格", "物资类型", "单位", "组成数量", "安全库存", "商品品牌", "操作"
        ])
        
        # 启用排序功能
        self.items_table.setSortingEnabled(True)
        
        # 设置表格样式
        self.items_table.setStyleSheet("""
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
            QHeaderView::section:first {
                font-size: 13px;
                padding: 12px 8px;
                text-align: center;
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
        self.items_table.verticalHeader().setStyleSheet("""
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
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 启用复制功能
        self.items_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.items_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 设置快捷键
        self.items_table.setShortcutEnabled(True)
        
        # 添加键盘事件处理
        self.items_table.keyPressEvent = self.table_key_press_event
        
        # 启用选择模式
        self.items_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # 设置行高
        self.items_table.verticalHeader().setDefaultSectionSize(45)
        self.items_table.verticalHeader().setMinimumSectionSize(40)
        
        # 设置表格尺寸策略 - 自动填充可用空间
        self.items_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 调整列宽 - 根据内容动态调整
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)             # 选择列固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 编码根据内容调整
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # 名称自适应剩余空间
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 规格根据内容调整
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 类型根据内容调整
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 单位根据内容调整
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 数量根据内容调整
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 安全库存根据内容调整
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # 商品品牌根据内容调整
        header.setSectionResizeMode(9, QHeaderView.Fixed)             # 操作列固定宽度
        
        # 设置固定列宽
        self.items_table.setColumnWidth(0, 50)   # 选择列宽度
        self.items_table.setColumnWidth(9, 120)  # 操作列宽度
        
        # 在表头第一列添加全选复选框
        self.header_checkbox = QCheckBox()
        self.header_checkbox.stateChanged.connect(self.toggle_all_selection)
        
        # 设置表头复选框样式
        self.header_checkbox.setStyleSheet("""
            QCheckBox {
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # 创建表头代理，将复选框嵌入到第一列
        self.header_proxy = QWidget()
        header_layout = QHBoxLayout(self.header_proxy)
        header_layout.addWidget(self.header_checkbox)
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.items_table)
        
        # 设置表头复选框
        try:
            # 将复选框添加到表头第一列
            self.items_table.setIndexWidget(self.items_table.model().index(0, 0), self.header_proxy)
        except Exception as e:
            print(f"设置表头复选框失败: {e}")
            # 如果设置失败，尝试在表头设置
            try:
                header = self.items_table.horizontalHeader()
                header.setSectionResizeMode(0, QHeaderView.Fixed)
                self.items_table.setColumnWidth(0, 50)
            except Exception as e2:
                print(f"设置表头列宽失败: {e2}")
    
    def load_items(self):
        """加载物料列表"""
        try:
            items = ItemService.get_all_items()
            self.populate_items_table(items)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载物料列表失败: {str(e)}")
    
    def filter_by_type(self):
        """根据物料类型筛选"""
        try:
            # 获取当前选中的物料类型
            selected_type = self.type_filter_combo.currentData()
            
            # 获取所有物料
            all_items = ItemService.get_all_items()
            
            # 根据类型筛选
            if selected_type:
                filtered_items = [item for item in all_items if item['ItemType'] == selected_type]
            else:
                filtered_items = all_items
            
            # 重新填充表格
            self.populate_items_table(filtered_items)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"筛选物料失败: {str(e)}")
    
    def search_items(self):
        """搜索物料"""
        try:
            search_text = self.search_edit.text().strip()
            selected_type = self.type_filter_combo.currentData()
            
            if search_text:
                # 多字段搜索
                items = self.search_items_by_multiple_fields(search_text)
                
                # 如果同时有类型筛选，进一步筛选
                if selected_type:
                    items = [item for item in items if item['ItemType'] == selected_type]
            else:
                # 没有搜索文本，只按类型筛选
                if selected_type:
                    all_items = ItemService.get_all_items()
                    items = [item for item in all_items if item['ItemType'] == selected_type]
                else:
                    items = ItemService.get_all_items()
            
            self.populate_items_table(items)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索物料失败: {str(e)}")
    
    def search_items_by_multiple_fields(self, search_text):
        """多字段模糊搜索物料"""
        try:
            # 获取所有物料
            all_items = ItemService.get_all_items()
            search_text_lower = search_text.lower()
            
            # 在多个字段中进行模糊搜索
            matched_items = []
            for item in all_items:
                # 检查编码 - 模糊匹配
                item_code = (item.get('ItemCode', '') or '').lower()
                if search_text_lower in item_code:
                    matched_items.append(item)
                    continue
                
                # 检查名称 - 模糊匹配
                item_name = (item.get('CnName', '') or '').lower()
                if search_text_lower in item_name:
                    matched_items.append(item)
                    continue
                
                # 检查规格 - 模糊匹配
                item_spec = (item.get('ItemSpec', '') or '').lower()
                if search_text_lower in item_spec:
                    matched_items.append(item)
                    continue
                
                # 检查商品品牌 - 模糊匹配
                item_brand = (item.get('Brand', '') or '').lower()
                if search_text_lower in item_brand:
                    matched_items.append(item)
                    continue
            
            return matched_items
            
        except Exception as e:
            print(f"多字段模糊搜索失败: {e}")
            # 如果多字段搜索失败，回退到原来的搜索方法
            return ItemService.search_items(search_text)
    
    def on_search_text_changed(self):
        """搜索文本改变时的实时搜索"""
        # 使用定时器延迟搜索，避免频繁搜索
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()
        else:
            from PySide6.QtCore import QTimer
            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self.search_items)
        
        # 300毫秒后执行搜索
        self._search_timer.start(300)
    
    def clear_search(self):
        """清空搜索"""
        self.search_edit.clear()
        self.type_filter_combo.setCurrentIndex(0)  # 重置为"全部"
        self.load_items()  # 重新加载所有物料
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu()
        
        # 复制选中单元格内容
        copy_action = menu.addAction("复制选中内容")
        copy_action.triggered.connect(self.copy_selected_cells)
        
        # 复制整行
        copy_row_action = menu.addAction("复制整行")
        copy_row_action.triggered.connect(self.copy_selected_rows)
        
        # 复制所有选中行
        copy_all_action = menu.addAction("复制所有选中行")
        copy_all_action.triggered.connect(self.copy_all_selected_rows)
        
        # 添加分隔线
        menu.addSeparator()
        
        # 测试复制功能
        test_action = menu.addAction("测试复制")
        test_action.triggered.connect(self.test_copy)
        
        # 显示菜单
        menu.exec_(self.items_table.mapToGlobal(position))
    
    def copy_selected_cells(self):
        """复制选中的单元格内容"""
        try:
            print("开始复制选中单元格...")
            selected_ranges = self.items_table.selectedRanges()
            print(f"选中的范围数量: {len(selected_ranges)}")
            
            if not selected_ranges:
                print("没有选中任何内容")
                QMessageBox.warning(self, "复制失败", "请先选中要复制的内容")
                return
            
            clipboard_text = ""
            for i, range_obj in enumerate(selected_ranges):
                print(f"处理第 {i+1} 个范围: 行 {range_obj.topRow()}-{range_obj.bottomRow()}, 列 {range_obj.leftColumn()}-{range_obj.rightColumn()}")
                
                for row in range(range_obj.topRow(), range_obj.bottomRow() + 1):
                    row_text = []
                    for col in range(range_obj.leftColumn(), range_obj.rightColumn() + 1):
                        # 跳过选择列（第0列）和操作列（第9列）
                        if col == 0 or col == 9:
                            row_text.append("")
                            print(f"  跳过列 [{row},{col}]: 选择列或操作列")
                            continue
                        
                        item = self.items_table.item(row, col)
                        if item:
                            cell_text = item.text()
                            row_text.append(cell_text)
                            print(f"  单元格 [{row},{col}]: {cell_text}")
                        else:
                            row_text.append("")
                            print(f"  空单元格 [{row},{col}]")
                    
                    row_line = "\t".join(row_text)
                    clipboard_text += row_line + "\n"
                    print(f"  行内容: {row_line}")
            
            if clipboard_text.strip():
                clipboard = QApplication.clipboard()
                clipboard.setText(clipboard_text.strip())
                print(f"已复制到剪贴板: {clipboard_text.strip()}")
                QMessageBox.information(self, "复制成功", "内容已复制到剪贴板")
            else:
                print("没有内容可复制")
                QMessageBox.warning(self, "复制失败", "没有选中任何内容")
                
        except Exception as e:
            print(f"复制单元格内容失败: {e}")
            QMessageBox.critical(self, "复制失败", f"复制过程中发生错误: {str(e)}")
    
    def copy_selected_rows(self):
        """复制选中的整行"""
        try:
            selected_rows = set()
            for range_obj in self.items_table.selectedRanges():
                for row in range(range_obj.topRow(), range_obj.bottomRow() + 1):
                    selected_rows.add(row)
            
            if not selected_rows:
                return
            
            clipboard_text = ""
            for row in sorted(selected_rows):
                row_text = []
                for col in range(self.items_table.columnCount()):
                    item = self.items_table.item(row, col)
                    if item:
                        row_text.append(item.text())
                    else:
                        # 检查是否有自定义控件
                        widget = self.items_table.cellWidget(row, col)
                        if widget:
                            checkbox = widget.findChild(QCheckBox)
                            if checkbox:
                                row_text.append("✓" if checkbox.isChecked() else "✗")
                            else:
                                row_text.append("")
                        else:
                            row_text.append("")
                clipboard_text += "\t".join(row_text) + "\n"
            
            if clipboard_text:
                clipboard = QApplication.clipboard()
                clipboard.setText(clipboard_text.strip())
                print("已复制选中行到剪贴板")
                
        except Exception as e:
            print(f"复制选中行失败: {e}")
    
    def copy_all_selected_rows(self):
        """复制所有选中的行（通过复选框）"""
        try:
            clipboard_text = ""
            for row in range(self.items_table.rowCount()):
                widget = self.items_table.cellWidget(row, 0)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        row_text = []
                        for col in range(self.items_table.columnCount()):
                            item = self.items_table.item(row, col)
                            if item:
                                row_text.append(item.text())
                            else:
                                widget = self.items_table.cellWidget(row, col)
                                if widget:
                                    checkbox = widget.findChild(QCheckBox)
                                    if checkbox:
                                        row_text.append("✓" if checkbox.isChecked() else "✗")
                                    else:
                                        row_text.append("")
                                else:
                                    row_text.append("")
                        clipboard_text += "\t".join(row_text) + "\n"
            
            if clipboard_text:
                clipboard = QApplication.clipboard()
                clipboard.setText(clipboard_text.strip())
                print("已复制所有选中行到剪贴板")
            else:
                print("没有选中的行")
                
        except Exception as e:
            print(f"复制所有选中行失败: {e}")
    
    def test_copy(self):
        """测试复制功能"""
        try:
            print("=== 测试复制功能 ===")
            
            # 获取当前选中的行
            current_row = self.items_table.currentRow()
            print(f"当前选中行: {current_row}")
            
            if current_row < 0:
                QMessageBox.warning(self, "测试失败", "请先选中一行")
                return
            
            # 获取该行的数据
            row_data = []
            for col in range(1, 9):  # 跳过选择列和操作列
                item = self.items_table.item(current_row, col)
                if item:
                    row_data.append(item.text())
                    print(f"列 {col}: {item.text()}")
                else:
                    row_data.append("")
                    print(f"列 {col}: 空")
            
            # 复制到剪贴板
            clipboard_text = "\t".join(row_data)
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)
            
            print(f"测试复制内容: {clipboard_text}")
            QMessageBox.information(self, "测试成功", f"已复制测试内容到剪贴板:\n{clipboard_text}")
            
        except Exception as e:
            print(f"测试复制失败: {e}")
            QMessageBox.critical(self, "测试失败", f"测试过程中发生错误: {str(e)}")
    
    def table_key_press_event(self, event):
        """表格键盘事件处理"""
        try:
            print(f"键盘事件: key={event.key()}, modifiers={event.modifiers()}")
            
            # 处理 Ctrl+C 复制
            if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
                print("检测到 Ctrl+C，开始复制...")
                self.copy_selected_cells()
                event.accept()
                return
            
            # 处理 Ctrl+A 全选
            elif event.key() == Qt.Key_A and event.modifiers() == Qt.ControlModifier:
                print("检测到 Ctrl+A，全选...")
                self.items_table.selectAll()
                event.accept()
                return
            
            # 处理 Delete 键删除选中项
            elif event.key() == Qt.Key_Delete:
                print("检测到 Delete 键...")
                if self.selected_items:
                    self.delete_selected_items()
                event.accept()
                return
            
            # 处理其他按键
            else:
                # 调用原始的键盘事件处理
                QTableWidget.keyPressEvent(self.items_table, event)
                
        except Exception as e:
            print(f"键盘事件处理失败: {e}")
            # 调用原始的键盘事件处理
            QTableWidget.keyPressEvent(self.items_table, event)
    
    def populate_items_table(self, items):
        """填充物料表格"""
        self.items_table.setRowCount(len(items))
        
        for row, item in enumerate(items):
            # 选择复选框
            checkbox = QCheckBox()
            # 将行号和物料ID存储在复选框的属性中
            checkbox.setProperty("row", row)
            checkbox.setProperty("item_id", item['ItemId'])
            # 连接事件到统一处理方法
            checkbox.stateChanged.connect(self.on_checkbox_state_changed)
            print(f"创建第 {row} 行复选框，物料ID: {item['ItemId']}")  # 调试信息
            
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.items_table.setCellWidget(row, 0, checkbox_widget)
            
            # 编码
            code_item = QTableWidgetItem(item['ItemCode'])
            code_item.setData(Qt.UserRole, item['ItemCode'])  # 用于排序
            self.items_table.setItem(row, 1, code_item)
            
            # 名称
            name_item = QTableWidgetItem(item['CnName'])
            name_item.setData(Qt.UserRole, item['CnName'])  # 用于排序
            self.items_table.setItem(row, 2, name_item)
            
            # 规格
            spec_item = QTableWidgetItem(item['ItemSpec'] if item['ItemSpec'] else "")
            spec_item.setData(Qt.UserRole, item['ItemSpec'] if item['ItemSpec'] else "")  # 用于排序
            self.items_table.setItem(row, 3, spec_item)
            
            # 类型
            type_item = QTableWidgetItem(item['ItemType'])
            type_item.setData(Qt.UserRole, item['ItemType'])  # 用于排序
            self.items_table.setItem(row, 4, type_item)
            
            # 单位
            unit_item = QTableWidgetItem(item['Unit'])
            unit_item.setData(Qt.UserRole, item['Unit'])  # 用于排序
            self.items_table.setItem(row, 5, unit_item)
            
            # 数量
            qty_item = QTableWidgetItem(str(item['Quantity']))
            qty_item.setData(Qt.UserRole, float(item['Quantity']))  # 用于排序
            self.items_table.setItem(row, 6, qty_item)
            
            # 安全库存
            stock_item = QTableWidgetItem(str(item['SafetyStock']))
            stock_item.setData(Qt.UserRole, float(item['SafetyStock']))  # 用于排序
            self.items_table.setItem(row, 7, stock_item)
            
            # 商品品牌
            brand_item = QTableWidgetItem(item['Brand'] if item['Brand'] else "")
            brand_item.setData(Qt.UserRole, item['Brand'] if item['Brand'] else "")  # 用于排序
            self.items_table.setItem(row, 8, brand_item)
            
            # 操作按钮
            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet("""
                QPushButton {
                    background: #1890ff;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #40a9ff;
                }
            """)
            # 使用物料ID而不是行号
            item_id = item['ItemId']
            edit_btn.clicked.connect(lambda checked, item_id=item_id: self.edit_item_by_id(item_id))
            
            view_btn = QPushButton("查看")
            view_btn.setStyleSheet("""
                QPushButton {
                    background: #52c41a;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #73d13d;
                }
            """)
            # 使用物料ID而不是行号
            view_btn.clicked.connect(lambda checked, item_id=item_id: self.view_item_by_id(item_id))
            
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(view_btn)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.items_table.setCellWidget(row, 9, btn_widget)
        
        # 更新按钮状态
        self._update_button_states()
        
        # 自动调整列宽
        self.items_table.resizeColumnsToContents()
        
        # 确保名称列有足够的空间
        name_column_width = self.items_table.columnWidth(2)
        if name_column_width < 200:  # 如果名称列太窄，设置最小宽度
            self.items_table.setColumnWidth(2, 200)
    
    def on_checkbox_state_changed(self, state):
        """复选框状态改变事件处理"""
        # 获取发送信号的复选框
        checkbox = self.sender()
        if checkbox:
            row = checkbox.property("row")
            item_id = checkbox.property("item_id")
            print(f"第 {row} 行复选框状态改变: {state}, 物料ID: {item_id}")  # 调试信息
            
            # 更新选中列表
            self.update_selection_list()
            
            # 更新按钮状态
            self._update_button_states()
    
    def on_selection_changed(self):
        """选择状态改变事件（保留兼容性）"""
        print("选择状态改变事件被触发")  # 调试信息
        self.update_selection_list()
        
        # 更新按钮状态
        self._update_button_states()
    
    def update_selection_list(self):
        """更新选中物料列表"""
        self.selected_items = []
        for row in range(self.items_table.rowCount()):
            widget = self.items_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    item_id = checkbox.property("item_id")
                    if item_id:
                        self.selected_items.append(item_id)
                        print(f"第 {row} 行被选中，物料ID: {item_id}")  # 调试信息
        
        print(f"当前选中的物料数量: {len(self.selected_items)}")  # 调试信息
    
    def add_item(self):
        """新增物料（通过对话框）"""
        dialog = ItemAddDialog(self)
        if dialog.exec() == QDialog.Accepted:
            try:
                item_data = dialog.get_item_data()
                
                # 验证必填字段
                if not item_data['ItemCode'] or not item_data['CnName']:
                    QMessageBox.warning(self, "警告", "物料编码和名称不能为空！")
                    return
                
                # 检查物料编码是否重复
                existing_items = ItemService.search_items(item_data['ItemCode'])
                if any(item['ItemCode'] == item_data['ItemCode'] for item in existing_items):
                    QMessageBox.warning(self, "警告", "物料编码已存在，请使用不同的编码！")
                    return
                
                # 通过服务层创建物料
                ItemService.create_item(item_data)
                QMessageBox.information(self, "成功", "物料创建成功！")
                self.load_items()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建物料失败: {str(e)}")
    
    def delete_selected_items(self):
        """删除选中的物料"""
        if not self.selected_items:
            QMessageBox.warning(self, "警告", "请先选择要删除的物料！")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除选中的 {len(self.selected_items)} 个物料吗？\n删除后无法恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success_count = 0
                error_count = 0
                
                for item_id in self.selected_items:
                    try:
                        ItemService.delete_item(item_id)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"删除物料 {item_id} 失败: {str(e)}")
                
                if success_count > 0:
                    QMessageBox.information(
                        self, "删除结果", 
                        f"成功删除 {success_count} 个物料" + 
                        (f"，{error_count} 个失败" if error_count > 0 else "")
                    )
                    self.load_items()
                else:
                    QMessageBox.critical(self, "错误", "删除物料失败！")
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除物料时发生错误: {str(e)}")
    

    
    def filter_items(self):
        """过滤物料列表"""
        try:
            search_text = self.search_edit.text().strip()
            if search_text:
                items = ItemService.search_items(search_text)
            else:
                items = ItemService.get_all_items()
            
            self.populate_items_table(items)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索物料失败: {str(e)}")

    def search_items(self):
        """搜索物料"""
        try:
            search_text = self.search_edit.text().strip()
            if not search_text:
                self.load_items()
                return
            
            items = ItemService.search_items(search_text)
            self.populate_items_table(items)
            
            if not items:
                QMessageBox.information(self, "搜索结果", "未找到匹配的物料")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索物料失败: {str(e)}")
    
    def clear_search(self):
        """清空搜索"""
        self.search_edit.clear()
        self.load_items()
    
    def edit_item_by_id(self, item_id):
        """通过物料ID编辑物料"""
        try:
            item = ItemService.get_item_by_id(item_id)
            if item:
                dialog = ItemEditDialog(item, self)
                if dialog.exec() == QDialog.Accepted:
                    updated_data = dialog.get_updated_item_data()
                    try:
                        # 检查是否会形成循环引用
                        parent_item_id = updated_data.get('ParentItemId')
                        if parent_item_id and ItemService.check_circular_reference(item_id, parent_item_id):
                            QMessageBox.warning(self, "警告", "不能设置该上级物资，会形成循环引用！")
                            return
                        
                        ItemService.update_item(item_id, updated_data)
                        QMessageBox.information(self, "成功", "物料更新成功！")
                        self.load_items()
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"更新物料失败: {str(e)}")
            else:
                QMessageBox.warning(self, "警告", "未找到物料信息")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑物料失败: {str(e)}")
    
    def edit_item(self, row):
        """编辑物料（通过行号，保留兼容性）"""
        try:
            # 从复选框属性中获取物料ID
            checkbox_widget = self.items_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    item_id = checkbox.property("item_id")
                    if item_id:
                        self.edit_item_by_id(item_id)
                    else:
                        QMessageBox.warning(self, "警告", "物料ID无效")
                else:
                    QMessageBox.warning(self, "警告", "未找到复选框")
            else:
                QMessageBox.warning(self, "警告", "未找到复选框组件")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑物料失败: {str(e)}")
    
    def view_item_by_id(self, item_id):
        """通过物料ID查看物料详情"""
        try:
            item = ItemService.get_item_by_id(item_id)
            if item:
                # 创建详情对话框
                detail_dialog = QDialog(self)
                detail_dialog.setWindowTitle("物料详情")
                detail_dialog.resize(700, 600)
                detail_dialog.setMinimumSize(600, 500)
                detail_dialog.setMaximumSize(1000, 900)
                detail_dialog.setModal(True)
                
                layout = QVBoxLayout(detail_dialog)
                layout.setContentsMargins(20, 20, 20, 20)
                layout.setSpacing(15)
                
                # 标题
                title_label = QLabel(f"物料详情 - {item['ItemCode'] if item['ItemCode'] else ''}")
                title_label.setStyleSheet("""
                    QLabel {
                        font-size: 18px;
                        font-weight: bold;
                        color: #1890ff;
                        padding: 10px 0;
                        border-bottom: 2px solid #1890ff;
                    }
                """)
                layout.addWidget(title_label)
                
                # 创建滚动区域
                scroll_area = QScrollArea()
                scroll_widget = QWidget()
                scroll_layout = QVBoxLayout(scroll_widget)
                scroll_layout.setSpacing(15)
                
                # 基本信息组
                basic_group = self._create_detail_group("基本信息", [
                    ("物料编码", item['ItemCode'] if item['ItemCode'] else ''),
                    ("物料名称", item['CnName'] if item['CnName'] else ''),
                    ("物料规格", item['ItemSpec'] if item['ItemSpec'] else '未设置'),
                    ("物料类型", item['ItemType'] if item['ItemType'] else ''),
                    ("单位", item['Unit'] if item['Unit'] else '个'),
                    ("组成数量", str(item['Quantity'] if item['Quantity'] else 1.0)),
                    ("安全库存", str(item['SafetyStock'] if item['SafetyStock'] else 0)),
                    ("商品品牌", item['Brand'] if item['Brand'] else '无')
                ])
                scroll_layout.addWidget(basic_group)
                
                # 层级关系组 - 显示完整的层级链
                try:
                    hierarchy = ItemService.get_item_hierarchy(item_id)
                    if len(hierarchy) > 1:  # 有上级物资
                        hierarchy_info = []
                        for i, level_item in enumerate(hierarchy):
                            prefix = "  " * i + ("└─ " if i > 0 else "")
                            hierarchy_info.append((
                                f"层级 {i+1}", 
                                f"{prefix}{level_item['ItemCode']} - {level_item['CnName']}"
                            ))
                        
                        hierarchy_group = self._create_detail_group("层级关系", hierarchy_info)
                        scroll_layout.addWidget(hierarchy_group)
                except Exception as e:
                    print(f"获取层级关系失败: {e}")
                
                # 子物资组 - 显示下级物资
                try:
                    children = ItemService.get_item_children(item_id)
                    if children:
                        children_info = []
                        for child in children:
                            children_info.append((
                                f"{child['ItemCode']}", 
                                f"{child['CnName']} ({child['ItemType']}) - 数量: {child['Quantity']}"
                            ))
                        
                        children_group = self._create_detail_group("下级物资", children_info)
                        scroll_layout.addWidget(children_group)
                except Exception as e:
                    print(f"获取子物资失败: {e}")
                
                # 备注信息组
                if item['Remark']:
                    remark_group = self._create_detail_group("备注信息", [
                        ("备注", item['Remark'])
                    ])
                    scroll_layout.addWidget(remark_group)
                
                # 设置滚动区域
                scroll_area.setWidget(scroll_widget)
                scroll_area.setWidgetResizable(True)
                scroll_area.setMaximumHeight(450)
                layout.addWidget(scroll_area)
                
                # 按钮
                button_box = QDialogButtonBox(QDialogButtonBox.Ok)
                button_box.accepted.connect(detail_dialog.accept)
                layout.addWidget(button_box)
                
                detail_dialog.exec()
            else:
                QMessageBox.warning(self, "警告", "未找到物料信息")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看物料详情失败: {str(e)}")
    
    def view_item(self, row):
        """查看物料详情（通过行号，保留兼容性）"""
        try:
            # 从复选框属性中获取物料ID
            checkbox_widget = self.items_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    item_id = checkbox.property("item_id")
                    if item_id:
                        self.view_item_by_id(item_id)
                    else:
                        QMessageBox.warning(self, "警告", "物料ID无效")
                else:
                    QMessageBox.warning(self, "警告", "未找到复选框")
            else:
                QMessageBox.warning(self, "警告", "未找到复选框组件")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看物料详情失败: {str(e)}")
    
    def _create_detail_group(self, title, items):
        """创建详情组"""
        group = QGroupBox(title)
        layout = QFormLayout(group)
        layout.setSpacing(8)
        layout.setLabelAlignment(Qt.AlignRight)
        
        for label, value in items:
            label_widget = QLabel(f"{label}:")
            value_widget = QLabel(str(value))
            value_widget.setWordWrap(True)
            value_widget.setStyleSheet("""
                QLabel {
                    color: #262626;
                    font-weight: 500;
                    padding: 4px 8px;
                    background: white;
                    border: 1px solid #f0f0f0;
                    border-radius: 3px;
                }
            """)
            layout.addRow(label_widget, value_widget)
        
        return group
    
    def select_all_items(self):
        """全选所有物料"""
        try:
            print("全选按钮被点击")  # 调试信息
            # 获取表格中的所有行
            row_count = self.items_table.rowCount()
            print(f"表格行数: {row_count}")  # 调试信息
            if row_count == 0:
                print("表格为空，无法全选")  # 调试信息
                return
            
            # 检查是否已经全选
            all_selected = True
            for row in range(row_count):
                checkbox_widget = self.items_table.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox and not checkbox.isChecked():
                        all_selected = False
                        break
            
            print(f"当前是否全选: {all_selected}")  # 调试信息
            
            # 如果已经全选，则取消全选；否则全选
            for row in range(row_count):
                checkbox_widget = self.items_table.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        if all_selected:
                            checkbox.setChecked(False)
                            print(f"取消选中第 {row} 行")  # 调试信息
                        else:
                            checkbox.setChecked(True)
                            print(f"选中第 {row} 行")  # 调试信息
            
            # 手动更新选中列表和按钮状态
            self.update_selection_list()
            self._update_button_states()
            
            # 更新按钮文本和表头复选框状态
            if all_selected:
                self.select_all_btn.setText("全选")
                if hasattr(self, 'header_checkbox'):
                    self.header_checkbox.setCheckState(Qt.Unchecked)
            else:
                self.select_all_btn.setText("取消全选")
                if hasattr(self, 'header_checkbox'):
                    self.header_checkbox.setCheckState(Qt.Checked)
            
            print("全选操作完成")  # 调试信息
                
        except Exception as e:
            print(f"全选操作异常: {e}")  # 调试信息
            QMessageBox.critical(self, "错误", f"全选操作失败: {str(e)}")
    
    def _update_button_states(self):
        """更新按钮状态"""
        try:
            # 检查是否有选中的物料
            has_selected = False
            row_count = self.items_table.rowCount()
            selected_count = 0
            
            for row in range(row_count):
                checkbox_widget = self.items_table.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        has_selected = True
                        selected_count += 1
            
            # 更新删除按钮状态
            self.delete_btn.setEnabled(has_selected)
            
            # 更新表头复选框状态 - 临时断开连接避免事件循环
            if hasattr(self, 'header_checkbox'):
                # 临时断开连接
                try:
                    self.header_checkbox.stateChanged.disconnect()
                except:
                    pass
                
                if selected_count == 0:
                    self.header_checkbox.setCheckState(Qt.Unchecked)
                elif selected_count == row_count:
                    self.header_checkbox.setCheckState(Qt.Checked)
                else:
                    self.header_checkbox.setCheckState(Qt.PartiallyChecked)
                
                # 重新连接
                self.header_checkbox.stateChanged.connect(self.toggle_all_selection)
            
        except Exception as e:
            print(f"更新按钮状态失败: {str(e)}")
    
    def toggle_all_selection(self, state):
        """表头全选/取消全选"""
        try:
            print(f"表头复选框状态改变: {state}")  # 调试信息
            row_count = self.items_table.rowCount()
            if row_count == 0:
                return
            
            check_state = (state == Qt.Checked.value)
            
            # 临时断开所有行复选框的事件连接
            for row in range(row_count):
                checkbox_widget = self.items_table.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        try:
                            checkbox.stateChanged.disconnect()
                        except:
                            pass
                        checkbox.setChecked(check_state)
            
            # 重新连接所有行复选框的事件
            for row in range(row_count):
                checkbox_widget = self.items_table.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.stateChanged.connect(self.on_checkbox_state_changed)
            
            # 手动更新选中列表和按钮状态
            self.update_selection_list()
            self._update_button_states()
            
            # 同步更新全选按钮文本
            if check_state:
                self.select_all_btn.setText("取消全选")
            else:
                self.select_all_btn.setText("全选")
            
        except Exception as e:
            print(f"表头全选操作失败: {str(e)}")
    
    def import_items(self):
        """导入物料"""
        dialog = ItemImportDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_items()  # 刷新物料列表


class ItemImportDialog(QDialog):
    """物料导入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入物料")
        self.setFixedSize(800, 650)
        self.setModal(True)
        self.import_data = []
        self.setup_ui()
        # 设置窗口尺寸策略，允许调整但限制范围
        self.resize(800, 650)
        self.setMinimumSize(700, 600)
        self.setMaximumSize(900, 700)
        # 添加调试信息
        self.move_count = 0
        self.last_pos = None
    
    def moveEvent(self, event):
        """重写移动事件，添加调试信息"""
        # 减少调试输出，只在必要时打印
        if self.move_count % 20 == 0:  # 每20次移动才打印一次
            print(f"=== 移动事件 #{self.move_count} ===")
            print(f"  窗口位置: {self.pos().x()}, {self.pos().y()}")
            print(f"  窗口尺寸: {self.width()} x {self.height()}")
        
        self.move_count += 1
        self.last_pos = event.pos()
        
        # 调用父类方法
        super().moveEvent(event)

    
    def resizeEvent(self, event):
        """重写尺寸改变事件，添加调试信息"""
        # 只在调试模式下打印
        if hasattr(self, 'debug_mode') and self.debug_mode:
            print(f"=== 尺寸改变事件 ===")
            print(f"  旧尺寸: {event.oldSize().width()} x {event.oldSize().height()}")
            print(f"  新尺寸: {event.size().width()} x {event.size().height()}")
            print(f"  事件类型: {type(event).__name__}")
            print("=" * 30)
        
        super().resizeEvent(event)

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
    
    def hideEvent(self, event):
        """隐藏事件"""
        super().hideEvent(event)
    
    def paintEvent(self, event):
        """绘制事件"""
        super().paintEvent(event)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("批量导入物料")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                padding: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # 说明文本
        desc_text = """
        导入说明：
        1. 支持Excel(.xlsx, .xls)和CSV文件格式
        2. 必需列：代码、名称、全名、规格型号
        3. 可选列：商品品牌（仅对成品有效）
        4. 全名字段前4-5个字用于判断物料类型：
           - 包含"原材料" → 原材料(RM)
           - 包含"成品" → 成品(FG)  
           - 包含"半成品" → 半成品(SFG)
           - 包含"包装材料"或"包装材" → 包装材料(PKG)
           - 其他 → 默认为原材料(RM)
        5. 商品品牌字段只有成品才会保存，其他类型物料会忽略该字段
        """
        
        desc_label = QLabel(desc_text)
        desc_label.setStyleSheet("""
            QLabel {
                background: #f6f8fa;
                border: 1px solid #e1e4e8;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
                color: #586069;
                line-height: 1.3;
            }
        """)
        desc_label.setWordWrap(True)
        splitter.addWidget(desc_label)
        
        # 文件选择区域
        file_group = QGroupBox("选择文件")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("请选择要导入的Excel或CSV文件...")
        self.file_path_edit.setReadOnly(True)
        
        self.select_file_btn = QPushButton("选择文件")
        self.select_file_btn.clicked.connect(self.select_file)
        
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.select_file_btn)
        splitter.addWidget(file_group)
        
        # 预览区域
        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout(preview_group)
        
        # 预览表格
        self.preview_table = QTableWidget()
        preview_layout.addWidget(self.preview_table)
            
        # 预览信息
        self.preview_info_label = QLabel("请先选择文件")
        self.preview_info_label.setStyleSheet("color: #666; font-size: 12px;")
        preview_layout.addWidget(self.preview_info_label)
        
        splitter.addWidget(preview_group)
        
        # 导入日志区域
        log_group = QGroupBox("导入日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background: #fafafa;
                border: 1px solid #e1e4e8;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        splitter.addWidget(log_group)
        
        # 设置分割器比例
        splitter.setSizes([120, 80, 300, 150])
        
        # 将分割器添加到主布局
        layout.addWidget(splitter)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.preview_btn = QPushButton("预览数据")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self.preview_data)
        
        self.import_btn = QPushButton("开始导入")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.start_import)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #1890ff;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 80px;
            }
            QPushButton[text="开始导入"] {
                background: #1890ff;
                color: white;
                border: none;
            }
            QPushButton[text="开始导入"]:hover {
                background: #40a9ff;
            }
            QPushButton[text="开始导入"]:disabled {
                background: #d9d9d9;
                color: #999;
            }
            QPushButton[text="预览数据"] {
                background: #52c41a;
                color: white;
                border: none;
            }
            QPushButton[text="预览数据"]:hover {
                background: #73d13d;
            }
            QPushButton[text="预览数据"]:disabled {
                background: #d9d9d9;
                color: #999;
            }
            QPushButton[text="取消"] {
                background: white;
                color: #666;
                border: 1px solid #ccc;
            }
            QPushButton[text="取消"]:hover {
                border-color: #1890ff;
                color: #1890ff;
            }
            QPushButton[text="选择文件"] {
                background: #f5f5f5;
                color: #333;
                border: 1px solid #d9d9d9;
            }
            QPushButton[text="选择文件"]:hover {
                background: #e6f7ff;
                border-color: #1890ff;
                color: #1890ff;
            }
        """)
    
    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择导入文件",
            "",
            "Excel文件 (*.xlsx *.xls);;CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.preview_btn.setEnabled(True)
            self.log_text.clear()
            self.log_text.appendPlainText(f"已选择文件: {file_path}")
    
    def preview_data(self):
        """预览数据"""
        file_path = self.file_path_edit.text()
        if not file_path:
            QMessageBox.warning(self, "警告", "请先选择文件！")
            return
        
        self.log_text.appendPlainText("正在读取文件...")
        
        try:
            # 根据文件扩展名选择读取方法
            if file_path.lower().endswith(('.xlsx', '.xls')):
                data, errors = ItemImportService.read_excel_file(file_path)
            elif file_path.lower().endswith('.csv'):
                data, errors = ItemImportService.read_csv_file(file_path)
            else:
                QMessageBox.warning(self, "警告", "不支持的文件格式！")
                return
            
            if errors:
                self.log_text.appendPlainText("读取文件出错:")
                for error in errors:
                    self.log_text.appendPlainText(f"  - {error}")
                return
            
            if not data:
                self.log_text.appendPlainText("文件中没有有效数据")
                return
            
            # 保存数据用于导入
            self.import_data = data
            
            # 更新预览表格
            self.update_preview_table(data)
            
            # 更新预览信息
            self.preview_info_label.setText(f"共读取到 {len(data)} 行数据")
            self.log_text.appendPlainText(f"成功读取 {len(data)} 行数据")
            
            # 启用导入按钮
            self.import_btn.setEnabled(True)
            
        except Exception as e:
            self.log_text.appendPlainText(f"预览数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"预览数据失败: {str(e)}")
    
    def update_preview_table(self, data):
        """更新预览表格"""
        if not data:
            return
        
        # 获取所有列名
        columns = list(data[0].keys())
        
        self.preview_table.setColumnCount(len(columns))
        self.preview_table.setHorizontalHeaderLabels(columns)
        
        # 只显示前10行数据
        preview_rows = min(10, len(data))
        self.preview_table.setRowCount(preview_rows)
        
        for row in range(preview_rows):
            for col, column_name in enumerate(columns):
                value = data[row].get(column_name, '')
                self.preview_table.setItem(row, col, QTableWidgetItem(str(value)))
        
        # 调整列宽
        self.preview_table.resizeColumnsToContents()
    
    def start_import(self):
        """开始导入"""
        if not self.import_data:
            QMessageBox.warning(self, "警告", "没有可导入的数据！")
            return
        
        # 确认导入
        reply = QMessageBox.question(
            self, "确认导入",
            f"确定要导入 {len(self.import_data)} 条物料数据吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮
        self.import_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        self.log_text.appendPlainText("开始导入数据...")
        
        try:
            # 执行导入
            success_count, errors, skipped_codes = ItemImportService.import_items(self.import_data)
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            
            # 显示导入结果
            result_messages = []
            
            if success_count > 0:
                self.log_text.appendPlainText(f"成功导入 {success_count} 条物料数据")
                result_messages.append(f"成功导入 {success_count} 条数据")
            
            if skipped_codes:
                self.log_text.appendPlainText(f"跳过已存在的编码 ({len(skipped_codes)} 个):")
                for code in skipped_codes:
                    self.log_text.appendPlainText(f"  - {code}")
                result_messages.append(f"跳过 {len(skipped_codes)} 个已存在的编码")
            
            if errors:
                self.log_text.appendPlainText("导入过程中出现以下错误:")
                for error in errors:
                    self.log_text.appendPlainText(f"  - {error}")
                result_messages.append(f"{len(errors)} 个错误")
            
            # 构建结果消息
            if success_count > 0 or skipped_codes:
                if errors:
                    # 部分成功
                    message = "\n".join(result_messages)
                    if skipped_codes:
                        message += f"\n\n跳过的编码: {', '.join(skipped_codes)}"
                    QMessageBox.warning(
                        self, "导入完成（有问题）",
                        f"{message}\n\n请查看日志了解详情。"
                    )
                else:
                    # 完全成功
                    if skipped_codes:
                        message = f"导入完成！\n成功导入 {success_count} 条数据\n跳过 {len(skipped_codes)} 个已存在的编码\n\n跳过的编码: {', '.join(skipped_codes)}"
                        QMessageBox.information(self, "导入完成", message)
                    else:
                        QMessageBox.information(self, "导入成功", f"成功导入 {success_count} 条物料数据！")
                
                # 导入有结果时关闭对话框
                self.accept()
            else:
                # 完全失败
                self.log_text.appendPlainText("导入失败:")
                for error in errors:
                    self.log_text.appendPlainText(f"  - {error}")
                
                QMessageBox.critical(
                    self, "导入失败",
                    f"导入失败，共 {len(errors)} 个错误。\n请查看日志了解详情。"
                )
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            error_msg = f"导入过程中发生异常: {str(e)}"
            self.log_text.appendPlainText(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
        
        finally:
            # 重新启用按钮
            self.import_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)


class BomEditor(QWidget):
    """BOM编辑器UI"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_boms()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)  # 减小边距
        layout.setSpacing(16)  # 减小间距
        
        # 设置主窗口尺寸策略
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # BOM列表
        list_group = QGroupBox("BOM 列表")
        list_group.setStyleSheet("""
            QGroupBox {
                font-weight: 500;
                border: 1px solid #e8e8e8;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: #262626;
            }
        """)
        
        list_layout = QVBoxLayout(list_group)
        
        # BOM表格
        self.bom_table = QTableWidget()
        self.bom_table.setColumnCount(7)
        self.bom_table.setHorizontalHeaderLabels([
            "BOM ID", "父物料编码", "父物料名称", "版本", "生效日期", "失效日期", "操作"
        ])
        
        # 设置表格样式
        self.bom_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e8e8e8;
                background-color: white;
                alternate-background-color: #fafafa;
                selection-background-color: #e6f7ff;
                selection-color: #262626;
                border: 1px solid #e8e8e8;
                border-radius: 4px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #fafafa;
                color: #262626;
                padding: 10px 6px;
                border: none;
                border-bottom: 1px solid #e8e8e8;
                font-weight: 500;
                font-size: 13px;
            }
        """)
        
        # 设置表格属性
        self.bom_table.setAlternatingRowColors(True)
        self.bom_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.bom_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # 调整列宽
        header = self.bom_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # BOM ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 父物料编码
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # 父物料名称
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 版本
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 生效日期
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 失效日期
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 操作
        
        list_layout.addWidget(self.bom_table)
        layout.addWidget(list_group)
    
    def load_boms(self):
        """加载BOM列表"""
        try:
            boms = BomService.get_bom_headers()
            self.populate_bom_table(boms)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载BOM列表失败: {str(e)}")
    
    def populate_bom_table(self, boms):
        """填充BOM表格"""
        self.bom_table.setRowCount(len(boms))
        
        for row, bom in enumerate(boms):
            # BOM ID
            self.bom_table.setItem(row, 0, QTableWidgetItem(str(bom['BomId'])))
            # 父物料编码
            self.bom_table.setItem(row, 1, QTableWidgetItem(bom['ParentItemCode']))
            # 父物料名称
            self.bom_table.setItem(row, 2, QTableWidgetItem(bom['ParentItemName']))
            # 版本
            self.bom_table.setItem(row, 3, QTableWidgetItem(bom['Rev']))
            # 生效日期
            self.bom_table.setItem(row, 4, QTableWidgetItem(str(bom['EffectiveDate'])))
            # 失效日期
            self.bom_table.setItem(row, 5, QTableWidgetItem(str(bom['ExpireDate']) if bom['ExpireDate'] else ""))
            
            # 操作按钮
            view_btn = QPushButton("查看")
            view_btn.setStyleSheet("""
                QPushButton {
                    background: #1890ff;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #40a9ff;
                }
            """)
            view_btn.clicked.connect(lambda checked, row=row: self.view_bom(row))
            
            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background: #ff4d4f;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #ff7875;
                }
            """)
            delete_btn.clicked.connect(lambda checked, row=row: self.delete_bom(row))
            
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(view_btn)
            btn_layout.addWidget(delete_btn)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            
            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.bom_table.setCellWidget(row, 6, btn_widget)
    
    def view_bom(self, row):
        """查看BOM详情"""
        try:
            bom_id = int(self.bom_table.item(row, 0).text())
            bom_lines = BomService.get_bom_lines(bom_id)
            
            # 显示BOM明细
            detail_text = "BOM 明细:\n\n"
            for line in bom_lines:
                detail_text += f"物料: {line['ChildItemCode']} - {line['ChildItemName']}\n"
                detail_text += f"用量: {line['QtyPer']}\n"
                detail_text += f"损耗率: {line['ScrapFactor']}\n"
                detail_text += "-" * 30 + "\n"
            
            msg = QMessageBox(self)
            msg.setWindowTitle("BOM 详情")
            msg.setText(detail_text)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看BOM详情失败: {str(e)}")
    
    def delete_bom(self, row):
        """删除BOM"""
        try:
            bom_id = int(self.bom_table.item(row, 0).text())
            parent_item_code = self.bom_table.item(row, 1).text()
            
            reply = QMessageBox.question(
                self, "确认删除", 
                f"确定要删除BOM '{parent_item_code}' 吗？\n删除后无法恢复！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 通过服务层删除BOM
                BomService.delete_bom_header(bom_id)
                QMessageBox.information(self, "成功", "BOM删除成功")
                self.load_boms()
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除BOM失败: {str(e)}")


class BomManagementWidget(QWidget):
    """BOM管理主界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)  # 减小边距
        layout.setSpacing(16)  # 减小间距
        
        # 设置主窗口尺寸策略
        self.setMinimumSize(600, 400)
        self.resize(800, 600)
        
        # 说明文字
        desc_label = QLabel("BOM管理功能正在开发中...")
        desc_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 14px;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        layout.addStretch()
