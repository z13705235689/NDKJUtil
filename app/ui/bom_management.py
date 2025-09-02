from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QFrame, QLineEdit, QComboBox, QSpinBox,
                               QDoubleSpinBox, QMessageBox, QTabWidget,
                               QHeaderView, QAbstractItemView, QGroupBox,
                               QFormLayout, QTextEdit, QDialog, QCheckBox,
                               QDialogButtonBox, QGridLayout, QSpacerItem,
                               QSizePolicy, QScrollArea, QSplitter, QDateEdit,
                               QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from app.services.bom_service import BomService
from app.services.item_service import ItemService
import re


class BomEditorDialog(QDialog):
    """BOM编辑器对话框 - 支持无限层级嵌套的产品结构"""

    def __init__(self, parent=None, bom_data=None):
        super().__init__(parent)
        self.bom_data = bom_data
        # 修复SQLite Row对象的访问方式
        self.bom_id = bom_data['BomId'] if bom_data and 'BomId' in bom_data.keys() else None
        self.setWindowTitle("新增BOM" if not bom_data else "编辑BOM")
        self.resize(1000, 700)
        self.setMinimumSize(900, 600)
        self.setMaximumSize(1200, 800)
        self.setModal(True)
        self.setup_ui()
        if bom_data:
            self.load_bom_data()
        self.load_bom_lines()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        self.title_label = QLabel("BOM编辑器")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333;
                padding: 8px;
            }
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)

        # 上半部分：BOM基础信息
        header_widget = self.create_bom_header_widget()
        splitter.addWidget(header_widget)

        # 下半部分：产品结构树形视图
        tree_widget = self.create_product_tree_widget()
        splitter.addWidget(tree_widget)

        # 设置分割器比例 - 调整结果区域更高
        splitter.setSizes([150, 550])
        layout.addWidget(splitter)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 15, 0, 0)
        button_layout.setSpacing(20)
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #666;
                border: 1px solid #ccc;
                padding: 10px 25px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                border-color: #1890ff;
                color: #1890ff;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        save_btn.clicked.connect(self.save_bom)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                min-width: 200px;
                min-height: 15px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDoubleSpinBox:focus {
                border-color: #1890ff;
            }
        """)

    def create_bom_header_widget(self):
        """创建BOM基础信息组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # BOM基础信息组
        header_group = QGroupBox("BOM基础信息")
        header_group.setStyleSheet("""
            QGroupBox {
                font-weight: 500;
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #262626;
                font-weight: 600;
            }
        """)

        # 使用网格布局，两列显示
        header_layout = QGridLayout(header_group)
        header_layout.setSpacing(15)
        header_layout.setColumnStretch(1, 1)

        # 第一列
        # BOM名称
        self.bom_name_edit = QLineEdit()
        self.bom_name_edit.setPlaceholderText("请输入BOM名称，如：产品A的BOM结构")
        self.bom_name_edit.setMaxLength(100)
        self.bom_name_edit.setStyleSheet("QLineEdit { padding: 4px 8px; min-height: 20px; max-height: 24px; }")
        header_layout.addWidget(QLabel("BOM名称 *:"), 0, 0)
        header_layout.addWidget(self.bom_name_edit, 0, 1)

        # 版本号
        self.rev_edit = QLineEdit()
        self.rev_edit.setPlaceholderText("请输入版本号，如：A、B、1.0等")
        self.rev_edit.setMaxLength(20)
        self.rev_edit.setStyleSheet("QLineEdit { padding: 4px 8px; min-height: 20px; max-height: 24px; }")
        header_layout.addWidget(QLabel("版本号 *:"), 1, 0)
        header_layout.addWidget(self.rev_edit, 1, 1)

        # 生效日期
        self.effective_date_edit = QDateEdit()
        self.effective_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.effective_date_edit.setDate(QDate.currentDate())
        self.effective_date_edit.setCalendarPopup(True)
        self.effective_date_edit.setStyleSheet("QDateEdit { padding: 4px 8px; min-height: 20px; max-height: 24px; }")
        header_layout.addWidget(QLabel("生效日期 *:"), 2, 0)
        header_layout.addWidget(self.effective_date_edit, 2, 1)

        # 第二列
        # 失效日期
        self.expire_date_edit = QDateEdit()
        self.expire_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.expire_date_edit.setCalendarPopup(True)
        self.expire_date_edit.setDate(QDate.currentDate().addYears(10))
        self.expire_date_edit.setStyleSheet("QDateEdit { padding: 4px 8px; min-height: 20px; max-height: 24px; }")
        header_layout.addWidget(QLabel("失效日期:"), 0, 2)
        header_layout.addWidget(self.expire_date_edit, 0, 3)

        # 备注
        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(40)
        self.remark_edit.setPlaceholderText("请输入备注信息")
        self.remark_edit.setStyleSheet("QTextEdit { padding: 4px 8px; min-height: 20px; max-height: 32px; }")
        header_layout.addWidget(QLabel("备注:"), 1, 2)
        header_layout.addWidget(self.remark_edit, 1, 3, 2, 1)

        layout.addWidget(header_group)

        return widget

    def create_product_tree_widget(self):
        """创建产品结构树形视图组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # 产品结构组
        tree_group = QGroupBox("产品结构")
        tree_group.setStyleSheet("""
            QGroupBox {
                font-weight: 500;
                border: 2px solid #e8e8e8;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #262626;
                font-weight: 600;
            }
        """)

        tree_layout = QVBoxLayout(tree_group)

        # 按钮栏
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        # 添加子物料按钮
        self.add_child_btn = QPushButton("+ 添加子物料")
        self.add_child_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                min-width: 100px;
                max-height: 28px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        self.add_child_btn.clicked.connect(self.add_child_material)

        # 展开所有按钮
        expand_all_btn = QPushButton("展开所有")
        expand_all_btn.setStyleSheet("""
            QPushButton {
                background: #52c41a;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                min-width: 80px;
                max-height: 28px;
            }
            QPushButton:hover {
                background: #73d13d;
            }
        """)
        expand_all_btn.clicked.connect(self.expand_all_nodes)

        # 收起所有按钮
        collapse_all_btn = QPushButton("收起所有")
        collapse_all_btn.setStyleSheet("""
            QPushButton {
                background: #faad14;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                min-width: 80px;
                max-height: 28px;
            }
            QPushButton:hover {
                background: #ffc53d;
            }
        """)
        collapse_all_btn.clicked.connect(self.collapse_all_nodes)

        button_layout.addWidget(self.add_child_btn)
        button_layout.addWidget(expand_all_btn)
        button_layout.addWidget(collapse_all_btn)
        button_layout.addStretch()

        tree_layout.addWidget(button_frame)

        # 产品结构树形视图
        self.product_tree = QTreeWidget()
        self.product_tree.setHeaderLabels(["产品信息", "用量", "损耗率", "备注", "操作"])
        self.product_tree.setIndentation(20)
        self.product_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e8e8e8;
                border-radius: 6px;
                background-color: white;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px 0px;
                border-bottom: 1px solid #f0f0f0;
                min-height: 30px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #e6f7ff;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #262626;
                padding: 6px 8px;
                border: none;
                border-bottom: 2px solid #e8e8e8;
                font-weight: 600;
                font-size: 13px;
            }
        """)

        # 设置列宽
        header = self.product_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 产品信息
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 用量
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 损耗率
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 备注
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # 操作

        self.product_tree.setColumnWidth(4, 100)  # 操作列宽度
        
        # 设置树形视图为可编辑
        self.product_tree.setEditTriggers(QTreeWidget.DoubleClicked | QTreeWidget.EditKeyPressed)
        
        # 连接编辑完成信号
        self.product_tree.itemChanged.connect(self.on_tree_item_changed)

        tree_layout.addWidget(self.product_tree)
        layout.addWidget(tree_group)

        return widget

    def load_bom_data(self):
        """加载BOM数据到表单"""
        if not self.bom_data:
            return

        try:
            # 设置BOM名称
            bom_name = self.bom_data['BomName'] if 'BomName' in self.bom_data.keys() else ''
            self.bom_name_edit.setText(str(bom_name))

            # 设置版本号
            self.rev_edit.setText(str(self.bom_data['Rev'] if 'Rev' in self.bom_data.keys() else ''))
            
            # 设置生效日期
            effective_date = self.bom_data['EffectiveDate'] if 'EffectiveDate' in self.bom_data.keys() else None
            if effective_date:
                try:
                    date_obj = QDate.fromString(str(effective_date), "yyyy-MM-dd")
                    if date_obj.isValid():
                        self.effective_date_edit.setDate(date_obj)
                except:
                    pass
            
            # 设置失效日期
            expire_date = self.bom_data['ExpireDate'] if 'ExpireDate' in self.bom_data.keys() else None
            if expire_date:
                try:
                    date_obj = QDate.fromString(str(expire_date), "yyyy-MM-dd")
                    if date_obj.isValid():
                        self.expire_date_edit.setDate(date_obj)
                except:
                    pass
            
            self.remark_edit.setPlainText(str(self.bom_data['Remark'] if 'Remark' in self.bom_data.keys() else ''))

            # 更新标题显示父产品信息
            self.update_title_with_parent_info()

        except Exception as e:
            print(f"加载BOM数据失败: {e}")

    def update_title_with_parent_info(self):
        """更新标题显示父产品信息"""
        try:
            if not self.bom_data:
                return
                
            parent_item_code = self.bom_data.get('ParentItemCode', '')
            parent_item_name = self.bom_data.get('ParentItemName', '')
            parent_item_spec = self.bom_data.get('ParentItemSpec', '')
            parent_item_brand = self.bom_data.get('ParentItemBrand', '')
            
            # 构建标题信息
            title_parts = ["BOM编辑器"]
            if parent_item_code or parent_item_name:
                product_info_parts = []
                if parent_item_code:
                    product_info_parts.append(parent_item_code)
                if parent_item_name:
                    product_info_parts.append(parent_item_name)
                if parent_item_spec:
                    product_info_parts.append(f"规格: {parent_item_spec}")
                
                title_parts.append(f"({' - '.join(product_info_parts)})")
            
            title_text = " - ".join(title_parts)
            self.title_label.setText(title_text)
            
        except Exception as e:
            print(f"更新标题失败: {e}")

    def load_bom_lines(self):
        """加载BOM明细列表到树形视图"""
        if not self.bom_id:
            return

        try:
            bom_lines = BomService.get_bom_lines(self.bom_id)
            self.populate_product_tree(bom_lines)
        except Exception as e:
            print(f"加载BOM明细失败: {e}")

    def populate_product_tree(self, bom_lines):
        """填充产品结构树形视图"""
        self.product_tree.clear()
        
        for line in bom_lines:
            # 修复SQLite Row对象的访问方式
            child_item_code = line['ChildItemCode'] if 'ChildItemCode' in line.keys() else ''
            child_item_name = line['ChildItemName'] if 'ChildItemName' in line.keys() else ''
            child_item_spec = line['ChildItemSpec'] if 'ChildItemSpec' in line.keys() else ''
            child_item_brand = line['ChildItemBrand'] if 'ChildItemBrand' in line.keys() else ''
            qty_per = line['QtyPer'] if 'QtyPer' in line.keys() else 0
            scrap_factor = line['ScrapFactor'] if 'ScrapFactor' in line.keys() else 0
            remark = line['Remark'] if 'Remark' in line.keys() else ''
            
            # 创建产品节点
            product_item = QTreeWidgetItem(self.product_tree)
            
            # 产品信息列 - 包含编码、名称、规格
            product_info_parts = [child_item_code, child_item_name]
            if child_item_spec:
                product_info_parts.append(f"规格: {child_item_spec}")
            
            product_info = " - ".join(product_info_parts)
            product_item.setText(0, product_info)
            
            # 用量列
            product_item.setText(1, str(qty_per))
            
            # 损耗率列
            scrap_factor_display = scrap_factor * 100 if scrap_factor else 0
            product_item.setText(2, f"{scrap_factor_display:.1f}%")
            
            # 备注列
            product_item.setText(3, str(remark) if remark else "")
            
            # 操作列
            self.create_tree_operation_widget(product_item, line)

    def create_tree_operation_widget(self, tree_item, line_data):
        """为树形视图项创建操作控件"""
        operation_widget = QWidget()
        operation_layout = QHBoxLayout(operation_widget)
        operation_layout.setContentsMargins(1, 1, 1, 1)
        operation_layout.setSpacing(2)

        # 添加子物料按钮
        add_child_btn = QPushButton("+ 新增")
        add_child_btn.setStyleSheet("""
            QPushButton {
                background: #52c41a;
                color: white;
                border: none;
                padding: 5px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-width: 20px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: #73d13d;
            }
        """)
        add_child_btn.clicked.connect(lambda: self.add_child_to_node(tree_item, line_data))

        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 5px 8px;
                border-radius: 4px;
                font-size: 11px;
                min-width: 20px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        edit_btn.clicked.connect(lambda: self.edit_material_node(tree_item, line_data))

        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #ff4d4f;
                color: white;
                border: none;
                padding: 5px 8px;
                border-radius: 4px;
                font-size: 11px;
                min-width: 20px;
                min-height: 16px;
            }
            QPushButton:hover {
                background: #ff7875;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_material_node(tree_item))

        operation_layout.addWidget(add_child_btn)
        operation_layout.addWidget(edit_btn)
        operation_layout.addWidget(delete_btn)

        self.product_tree.setItemWidget(tree_item, 4, operation_widget)

    def add_child_material(self):
        """添加子物料到根节点"""
        self.add_material_dialog = MaterialSelectionDialog(self)
        if self.add_material_dialog.exec() == QDialog.Accepted:
            materials_data = self.add_material_dialog.get_selected_materials()
            for material_data in materials_data:
                self.add_material_to_tree(None, material_data)

    def add_child_to_node(self, parent_item, parent_line_data):
        """在指定节点下添加子物料"""
        self.add_material_dialog = MaterialSelectionDialog(self)
        if self.add_material_dialog.exec() == QDialog.Accepted:
            materials_data = self.add_material_dialog.get_selected_materials()
            for material_data in materials_data:
                self.add_material_to_tree(parent_item, material_data)

    def add_material_to_tree(self, parent_item, material_data):
        """添加物料到树形视图"""
        # 创建新的物料节点
        if parent_item:
            new_item = QTreeWidgetItem(parent_item)
        else:
            new_item = QTreeWidgetItem(self.product_tree)

        # 设置物料信息
        product_info = f"{material_data['ItemCode']} - {material_data['CnName']}"
        new_item.setText(0, product_info)
        new_item.setText(1, "1.0")  # 默认用量
        new_item.setText(2, "0.0%")  # 默认损耗率
        new_item.setText(3, "")  # 备注

        # 设置物料数据到节点，用于后续保存
        new_item.setData(0, Qt.UserRole, {
            'ItemId': material_data['ItemId'] if 'ItemId' in material_data.keys() else 0,
            'ItemCode': material_data['ItemCode'] if 'ItemCode' in material_data.keys() else '',
            'ItemName': material_data['CnName'] if 'CnName' in material_data.keys() else '',
            'ItemSpec': material_data['ItemSpec'] if 'ItemSpec' in material_data.keys() else '',
            'Brand': material_data['Brand'] if 'Brand' in material_data.keys() else '',
            'ItemType': material_data['ItemType'] if 'ItemType' in material_data.keys() else ''
        })

        # 设置节点为可编辑
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)

        # 创建操作控件
        self.create_tree_operation_widget(new_item, material_data)

        # 展开父节点
        if parent_item:
            parent_item.setExpanded(True)

    def edit_material_node(self, tree_item, line_data):
        """编辑物料节点"""
        try:
            # 获取当前节点的数据
            current_qty = tree_item.text(1)
            current_scrap = tree_item.text(2)
            current_remark = tree_item.text(3)
            
            # 创建编辑对话框
            dialog = MaterialEditDialog(self, current_qty, current_scrap, current_remark)
            if dialog.exec() == QDialog.Accepted:
                # 获取编辑后的数据
                new_qty, new_scrap, new_remark = dialog.get_edited_data()
                
                # 更新节点数据
                tree_item.setText(1, str(new_qty))
                tree_item.setText(2, f"{new_scrap:.1f}%")
                tree_item.setText(3, str(new_remark))
                
                QMessageBox.information(self, "成功", "物料信息更新成功！")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑物料失败: {str(e)}")

    def delete_material_node(self, tree_item):
        """删除物料节点"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除该物料吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 删除节点及其所有子节点
            parent = tree_item.parent()
            if parent:
                parent.removeChild(tree_item)
            else:
                self.product_tree.takeTopLevelItem(self.product_tree.indexOfTopLevelItem(tree_item))

    def expand_all_nodes(self):
        """展开所有节点"""
        self.product_tree.expandAll()

    def collapse_all_nodes(self):
        """收起所有节点"""
        self.product_tree.collapseAll()

    def on_tree_item_changed(self, item, column):
        """处理树形视图项编辑完成事件"""
        try:
            if column == 1:  # 用量列
                # 验证用量是否为有效数字
                qty_text = item.text(1)
                try:
                    qty = float(qty_text)
                    if qty <= 0:
                        item.setText(1, "1.0")
                        QMessageBox.warning(self, "警告", "用量必须大于0！")
                except ValueError:
                    item.setText(1, "1.0")
                    QMessageBox.warning(self, "警告", "用量必须是有效的数字！")
                    
            elif column == 2:  # 损耗率列
                # 验证损耗率是否为有效数字
                scrap_text = item.text(2)
                try:
                    # 移除百分号并转换为小数
                    if "%" in scrap_text:
                        scrap_text = scrap_text.replace("%", "")
                    scrap = float(scrap_text)
                    if scrap < 0:
                        item.setText(2, "0.0%")
                        QMessageBox.warning(self, "警告", "损耗率不能为负数！")
                    elif scrap > 100:
                        item.setText(2, "100.0%")
                        QMessageBox.warning(self, "警告", "损耗率不能超过100%！")
                    else:
                        # 重新格式化显示
                        item.setText(2, f"{scrap:.1f}%")
                except ValueError:
                    item.setText(2, "0.0%")
                    QMessageBox.warning(self, "警告", "损耗率必须是有效的数字！")
                    
        except Exception as e:
            print(f"处理树形视图项编辑失败: {e}")

    def get_bom_data(self):
        """获取BOM主表数据"""
        # 获取日期
        effective_date = self.effective_date_edit.date().toString("yyyy-MM-dd")
        expire_date = self.expire_date_edit.date().toString("yyyy-MM-dd") if self.expire_date_edit.date().isValid() else None

        return {
            'BomName': self.bom_name_edit.text().strip(),
            'Rev': self.rev_edit.text().strip(),
            'EffectiveDate': effective_date,
            'ExpireDate': expire_date,
            'Remark': self.remark_edit.toPlainText().strip()
        }

    def get_materials_data(self):
        """从树形视图获取所有物料数据"""
        materials_data = []
        self.collect_materials_from_tree(self.product_tree.invisibleRootItem(), materials_data)
        return materials_data

    def collect_materials_from_tree(self, parent_item, materials_data):
        """递归收集树形视图中的物料数据"""
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            
            # 从节点的UserRole数据中获取物料信息
            item_data = child_item.data(0, Qt.UserRole)
            
            if item_data and isinstance(item_data, dict) and item_data['ItemId'] if 'ItemId' in item_data.keys() else 0:
                try:
                    # 获取物料ID
                    child_item_id = item_data['ItemId']
                    
                    # 获取用量
                    qty_text = child_item.text(1)
                    qty_per = float(qty_text) if qty_text else 1.0
                    
                    # 获取损耗率
                    scrap_text = child_item.text(2)
                    scrap_factor = float(scrap_text.replace("%", "")) / 100 if scrap_text and "%" in scrap_text else 0.0
                    
                    # 获取备注
                    remark = child_item.text(3)
                    
                    materials_data.append({
                        'ChildItemId': child_item_id,
                        'QtyPer': qty_per,
                        'ScrapFactor': scrap_factor,
                        'Remark': remark
                    })
                    
                    # 递归处理子节点
                    self.collect_materials_from_tree(child_item, materials_data)
                    
                except Exception as e:
                    print(f"处理物料数据失败: {e}")
            else:
                # 如果没有物料ID，尝试从文本中解析物料编码
                product_info = child_item.text(0)
                item_code = product_info.split(" - ")[0] if " - " in product_info else ""
                
                if item_code:
                    try:
                        # 根据物料编码查找物料ID
                        items = ItemService.search_items(item_code)
                        if items:
                            child_item_id = items[0]['ItemId'] if 'ItemId' in items[0].keys() else 0
                            
                            if child_item_id:
                                # 获取用量
                                qty_text = child_item.text(1)
                                qty_per = float(qty_text) if qty_text else 1.0

                                # 获取损耗率
                                scrap_text = child_item.text(2)
                                scrap_factor = float(scrap_text.replace("%", "")) / 100 if scrap_text and "%" in scrap_text else 0.0

                                # 获取备注
                                remark = child_item.text(3)

                                materials_data.append({
                                    'ChildItemId': child_item_id,
                                    'QtyPer': qty_per,
                                    'ScrapFactor': scrap_factor,
                                    'Remark': remark
                                })

                                # 递归处理子节点
                                self.collect_materials_from_tree(child_item, materials_data)
                                
                    except Exception as e:
                        print(f"处理物料数据失败: {e}")

    def save_bom(self):
        """保存BOM数据"""
        try:
            # 验证必填字段
            bom_data = self.get_bom_data()
            print(f"调试 - BOM数据: {bom_data}")  # 调试信息
            
            # 验证BOM名称
            if not bom_data['BomName'] if 'BomName' in bom_data.keys() else '' or not (bom_data['BomName'] if 'BomName' in bom_data.keys() else '').strip():
                QMessageBox.warning(self, "警告", "请输入BOM名称！")
                return

            # 验证版本号
            if not bom_data['Rev'] if 'Rev' in bom_data.keys() else '' or not (bom_data['Rev'] if 'Rev' in bom_data.keys() else '').strip():
                QMessageBox.warning(self, "警告", "请输入版本号！")
                return

            # 验证版本号格式
            rev = bom_data['Rev'] if 'Rev' in bom_data.keys() else ''
            if not re.match(r'^[A-Za-z0-9._-]+$', rev):
                QMessageBox.warning(self, "警告", "版本号只能包含字母、数字、点、下划线和连字符！")
                return
                
            # 验证生效日期
            if not bom_data['EffectiveDate'] if 'EffectiveDate' in bom_data.keys() else None:
                QMessageBox.warning(self, "警告", "请选择生效日期！")
                return
                
            # 验证失效日期
            expire_date = bom_data['ExpireDate'] if 'ExpireDate' in bom_data.keys() else None
            if expire_date:
                effective_date = QDate.fromString(bom_data['EffectiveDate'] if 'EffectiveDate' in bom_data.keys() else '', "yyyy-MM-dd")
                expire_date_obj = QDate.fromString(expire_date, "yyyy-MM-dd")
                if expire_date_obj <= effective_date:
                    QMessageBox.warning(self, "警告", "失效日期必须晚于生效日期！")
                    return

            # 验证物料明细
            materials_data = self.get_materials_data()
            print(f"调试 - 物料数据: {materials_data}")  # 调试信息
            
            if not materials_data:
                QMessageBox.warning(self, "警告", "请至少添加一个物料明细！")
                return
                
            # 验证物料数据
            for i, material in enumerate(materials_data):
                print(f"调试 - 验证第{i+1}个物料: {material}")  # 调试信息
                qty_per = material.get('QtyPer', 0)
                scrap_factor = material.get('ScrapFactor', 0)
                print(f"调试 - 第{i+1}个物料用量: {qty_per}, 损耗率: {scrap_factor}")  # 调试信息
                
                if qty_per <= 0:
                    QMessageBox.warning(self, "警告", f"第{i+1}个物料的用量必须大于0！")
                    return
                if scrap_factor < 0:
                    QMessageBox.warning(self, "警告", f"第{i+1}个物料的损耗率不能为负数！")
                    return

            # 保存数据
            if self.bom_id:
                # 更新现有BOM
                print(f"调试 - 更新BOM，ID: {self.bom_id}")  # 调试信息
                BomService.update_bom_header(self.bom_id, bom_data)
                # 删除现有明细
                existing_lines = BomService.get_bom_lines(self.bom_id)
                for line in existing_lines:
                    # 修复SQLite Row对象的访问方式
                    line_id = line['LineId'] if 'LineId' in line.keys() else 0
                    if line_id:
                        BomService.delete_bom_line(line_id)
                # 添加新物料明细
                for material_data in materials_data:
                    print(f"调试 - 创建BOM明细: {material_data}")  # 调试信息
                    BomService.create_bom_line(self.bom_id, material_data)
                QMessageBox.information(self, "成功", "BOM更新成功！")
            else:
                # 创建新BOM
                print(f"调试 - 创建新BOM")  # 调试信息
                bom_id = BomService.create_bom_header(bom_data)
                print(f"调试 - 新BOM ID: {bom_id}")  # 调试信息
                
                # 添加物料明细
                for material_data in materials_data:
                    print(f"调试 - 创建BOM明细: {material_data}")  # 调试信息
                    BomService.create_bom_line(bom_id, material_data)
                QMessageBox.information(self, "成功", "BOM创建成功！")

            self.accept()

        except Exception as e:
            print(f"调试 - 保存BOM异常: {e}")  # 调试信息
            QMessageBox.critical(self, "错误", f"保存BOM失败: {str(e)}")


class MaterialSelectionDialog(QDialog):
    """物料选择对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_materials = []  # 改为支持多选
        self.setWindowTitle("选择物料")
        self.resize(750, 500)
        self.setMinimumSize(700, 450)
        self.setModal(True)
        self.setup_ui()
        self.load_materials()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 搜索区域
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)

        search_label = QLabel("搜索物料:")
        search_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入物料编码或名称搜索")
        self.search_edit.textChanged.connect(self.filter_materials)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addStretch()

        layout.addWidget(search_frame)

        # 物料列表表格
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(6)
        self.materials_table.setHorizontalHeaderLabels([
            "选择", "物料编码", "物料名称", "规格型号", "商品品牌", "物料类型"
        ])

        # 设置表格样式
        self.materials_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e8e8e8;
                background-color: white;
                alternate-background-color: #fafafa;
                selection-background-color: #e6f7ff;
                selection-color: #262626;
                border: 1px solid #e8e8e8;
                border-radius: 6px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #262626;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid #e8e8e8;
                font-weight: 600;
                font-size: 13px;
            }
        """)

        # 设置表格属性
        self.materials_table.setAlternatingRowColors(True)
        self.materials_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.materials_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.materials_table.itemDoubleClicked.connect(self.on_item_double_clicked)

        # 调整列宽
        header = self.materials_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 选择
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 物料编码
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 物料名称
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 规格型号
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 商品品牌
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 物料类型

        layout.addWidget(self.materials_table)

        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 多选操作按钮
        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background: #52c41a;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                min-width: 60px;
            }
            QPushButton:hover {
                background: #73d13d;
            }
        """)
        select_all_btn.clicked.connect(self.select_all_materials)
        
        clear_all_btn = QPushButton("清空")
        clear_all_btn.setStyleSheet("""
            QPushButton {
                background: #faad14;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                min-width: 60px;
            }
            QPushButton:hover {
                background: #ffc53d;
            }
        """)
        clear_all_btn.clicked.connect(self.clear_all_selections)
        
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(clear_all_btn)
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        select_btn = QPushButton("选择")
        select_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        select_btn.clicked.connect(self.select_material)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(select_btn)

        layout.addLayout(button_layout)

    def load_materials(self):
        """加载物料列表"""
        try:
            materials = ItemService.get_all_items()
            self.populate_materials_table(materials)
        except Exception as e:
            print(f"加载物料失败: {e}")

    def populate_materials_table(self, materials):
        """填充物料表格"""
        self.materials_table.setRowCount(len(materials))

        for row, material in enumerate(materials):
            # 添加复选框
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(lambda state, row=row: self.on_checkbox_changed(state, row))
            self.materials_table.setCellWidget(row, 0, checkbox)
            
            # 修复SQLite Row对象的访问方式
            item_code = material['ItemCode'] if 'ItemCode' in material.keys() else ''
            item_name = material['CnName'] if 'CnName' in material.keys() else ''
            item_spec = material['ItemSpec'] if 'ItemSpec' in material.keys() else ''
            item_brand = material['Brand'] if 'Brand' in material.keys() else ''
            item_type = material['ItemType'] if 'ItemType' in material.keys() else ''
            
            self.materials_table.setItem(row, 1, QTableWidgetItem(str(item_code)))
            self.materials_table.setItem(row, 2, QTableWidgetItem(str(item_name)))
            self.materials_table.setItem(row, 3, QTableWidgetItem(str(item_spec)))
            self.materials_table.setItem(row, 4, QTableWidgetItem(str(item_brand)))
            self.materials_table.setItem(row, 5, QTableWidgetItem(str(item_type)))

    def filter_materials(self, search_text):
        """过滤物料"""
        for row in range(self.materials_table.rowCount()):
            # 修复表格项为空时的错误处理
            item_code_item = self.materials_table.item(row, 1)
            item_name_item = self.materials_table.item(row, 2)
            
            if item_code_item and item_name_item:
                item_code = item_code_item.text()
                item_name = item_name_item.text()
                
                search_lower = search_text.lower()
                if not search_text or search_lower in item_code.lower() or search_lower in item_name.lower():
                    self.materials_table.setRowHidden(row, False)
                else:
                    self.materials_table.setRowHidden(row, True)
            else:
                # 如果表格项为空，隐藏该行
                self.materials_table.setRowHidden(row, True)
    
    def on_checkbox_changed(self, state, row):
        """复选框状态改变"""
        # 这里可以添加选中状态变化的处理逻辑
        pass
    
    def select_all_materials(self):
        """全选所有物料"""
        for row in range(self.materials_table.rowCount()):
            if not self.materials_table.isRowHidden(row):
                checkbox = self.materials_table.cellWidget(row, 0)
                if checkbox:
                    checkbox.setChecked(True)
    
    def clear_all_selections(self):
        """清空所有选择"""
        for row in range(self.materials_table.rowCount()):
            checkbox = self.materials_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)

    def on_item_double_clicked(self, item, column):
        """双击选择物料"""
        self.select_material()

    def select_material(self):
        """选择物料"""
        self.selected_materials = []
        
        for row in range(self.materials_table.rowCount()):
            checkbox = self.materials_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                item_code = self.materials_table.item(row, 1).text()
                item_name = self.materials_table.item(row, 2).text()
                item_spec = self.materials_table.item(row, 3).text()
                item_brand = self.materials_table.item(row, 4).text()
                item_type = self.materials_table.item(row, 5).text()
                
                # 根据物料编码查找完整的物料信息
                try:
                    items = ItemService.search_items(item_code)
                    if items and len(items) > 0:
                        item = items[0]
                        material_data = {
                            'ItemId': item['ItemId'] if 'ItemId' in item.keys() else 0,
                            'ItemCode': item_code,
                            'CnName': item_name,
                            'ItemSpec': item_spec,
                            'Brand': item_brand,
                            'ItemType': item_type
                        }
                        self.selected_materials.append(material_data)
                except Exception as e:
                    print(f"获取物料信息失败: {e}")
        
        if self.selected_materials:
            self.accept()
        else:
            QMessageBox.warning(self, "警告", "请至少选择一个物料！")

    def get_selected_materials(self):
        """获取选中的物料列表"""
        return self.selected_materials


class BomManagementWidget(QWidget):
    """BOM管理主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_boms()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 设置主窗口尺寸策略
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        # 标题
        title_label = QLabel("BOM 管理")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333;
                padding: 15px;
                text-align: center;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 搜索栏
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)

        # 搜索标签
        search_label = QLabel("搜索零部件:")
        search_label.setStyleSheet("""
            QLabel {
                color: #262626;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        search_layout.addWidget(search_label)

        # 搜索输入框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入物料编码、名称或规格，查找使用了该零部件的BOM")
        self.search_edit.setMinimumWidth(400)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #40a9ff;
                outline: none;
            }
        """)
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_edit)

        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        reset_btn.clicked.connect(self.on_reset_search)
        search_layout.addWidget(reset_btn)

        search_layout.addStretch()
        layout.addWidget(search_frame)

        # 按钮栏
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        # 新增BOM按钮
        self.add_bom_btn = QPushButton("新增BOM")
        self.add_bom_btn.setStyleSheet("""
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
        """)
        self.add_bom_btn.clicked.connect(self.add_bom)

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
                border-color: #40a9ff;
                color: #40a9ff;
            }
        """)
        self.refresh_btn.clicked.connect(lambda: self.load_boms())

        # BOM展开按钮
        self.expand_bom_btn = QPushButton("BOM展开")
        self.expand_bom_btn.setStyleSheet("""
            QPushButton {
                background: #52c41a;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #73d13d;
            }
        """)
        self.expand_bom_btn.clicked.connect(self.show_bom_expand_dialog)

        button_layout.addWidget(self.add_bom_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.expand_bom_btn)
        button_layout.addStretch()

        layout.addWidget(button_frame)

        # BOM表格
        self.bom_table = QTableWidget()
        self.bom_table.setColumnCount(11)
        self.bom_table.setHorizontalHeaderLabels([
            "BOM ID", "BOM名称", "父产品编码", "父产品名称", "父产品规格", "版本", "生效日期", "失效日期", "备注", "状态", "操作"
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
                font-size: 12px;
            }
        """)

        # 设置表格属性
        self.bom_table.setAlternatingRowColors(True)
        self.bom_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.bom_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # 调整列宽
        header = self.bom_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # BOM ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # BOM名称
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 父产品编码
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 父产品名称
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 父产品规格
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 版本
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 生效日期
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 失效日期
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # 备注
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(10, QHeaderView.Fixed)  # 操作
        header.setDefaultSectionSize(120)  # 设置默认列宽
        self.bom_table.setColumnWidth(10, 150)  # 设置操作列宽度

        layout.addWidget(self.bom_table)

    def load_boms(self, search_filter: str = None):
        """加载BOM列表"""
        try:
            boms = BomService.get_bom_headers(search_filter)
            self.populate_bom_table(boms)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载BOM列表失败: {str(e)}")

    def on_search_changed(self):
        """当搜索条件变化时，重新加载BOM列表"""
        search_text = self.search_edit.text().strip()
        self.load_boms(search_text if search_text else None)

    def on_reset_search(self):
        """重置搜索条件"""
        self.search_edit.clear()
        self.load_boms()

    def show_bom_expand_dialog(self):
        """显示BOM展开对话框"""
        try:
            # 获取有BOM结构的成品物料
            items_with_bom = []
            all_items = ItemService.get_all_items()
            
            for item in all_items:
                # 修复SQLite Row对象的访问方式
                item_type = item['ItemType'] if 'ItemType' in item.keys() else ''
                if item_type in ['FG', 'SFG']:
                    # 检查这个物料是否有BOM结构
                    try:
                        bom = BomService.get_bom_by_parent_item(item['ItemId'])
                        if bom:
                            items_with_bom.append(item)
                    except:
                        continue
            
            if not items_with_bom:
                QMessageBox.information(self, "提示", "没有找到有BOM结构的成品或半成品物料")
                return
            
            # 创建BOM展开对话框
            dialog = BomExpandDialog(self, items_with_bom)
            if dialog.exec() == QDialog.Accepted:
                pass  # 可以在这里添加后续处理逻辑
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示BOM展开对话框失败: {str(e)}")

    def populate_bom_table(self, boms):
        """填充BOM表格"""
        self.bom_table.setRowCount(len(boms))

        for row, bom in enumerate(boms):
            # 修复SQLite Row对象的访问方式
            bom_id = bom['BomId'] if 'BomId' in bom.keys() else ''
            bom_name = bom['BomName'] if 'BomName' in bom.keys() else ''
            parent_item_code = bom['ParentItemCode'] if 'ParentItemCode' in bom.keys() else ''
            parent_item_name = bom['ParentItemName'] if 'ParentItemName' in bom.keys() else ''
            parent_item_spec = bom['ParentItemSpec'] if 'ParentItemSpec' in bom.keys() else ''
            rev = bom['Rev'] if 'Rev' in bom.keys() else ''
            effective_date = bom['EffectiveDate'] if 'EffectiveDate' in bom.keys() else ''
            expire_date = bom['ExpireDate'] if 'ExpireDate' in bom.keys() else ''
            remark = bom['Remark'] if 'Remark' in bom.keys() else ''
            
            # BOM ID
            self.bom_table.setItem(row, 0, QTableWidgetItem(str(bom_id)))
            # BOM名称
            self.bom_table.setItem(row, 1, QTableWidgetItem(str(bom_name)))
            # 父产品编码
            self.bom_table.setItem(row, 2, QTableWidgetItem(str(parent_item_code)))
            # 父产品名称
            self.bom_table.setItem(row, 3, QTableWidgetItem(str(parent_item_name)))
            # 父产品规格
            self.bom_table.setItem(row, 4, QTableWidgetItem(str(parent_item_spec)))
            # 版本
            self.bom_table.setItem(row, 5, QTableWidgetItem(str(rev)))
            # 生效日期
            self.bom_table.setItem(row, 6, QTableWidgetItem(str(effective_date)))
            # 失效日期
            expire_date_display = str(expire_date) if expire_date else "未设置"
            self.bom_table.setItem(row, 7, QTableWidgetItem(expire_date_display))
            # 备注
            self.bom_table.setItem(row, 8, QTableWidgetItem(str(remark) if remark else ""))
            # 状态
            status = "有效" if not expire_date or expire_date >= QDate.currentDate().toString(
                "yyyy-MM-dd") else "已过期"
            status_item = QTableWidgetItem(status)
            if status == "已过期":
                status_item.setForeground(QColor("#ff4d4f"))
            self.bom_table.setItem(row, 9, status_item)

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

            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet("""
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
            edit_btn.clicked.connect(lambda checked, row=row: self.edit_bom(row))

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
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_layout.setContentsMargins(4, 2, 4, 2)

            btn_widget = QWidget()
            btn_widget.setLayout(btn_layout)
            self.bom_table.setCellWidget(row, 10, btn_widget)

    def add_bom(self):
        """新增BOM"""
        # 使用新的集成编辑器
        dialog = BomEditorDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_boms()

    def view_bom(self, row):
        """查看BOM详情"""
        try:
            bom_id_item = self.bom_table.item(row, 0)
            if not bom_id_item:
                QMessageBox.warning(self, "警告", "无法获取BOM ID")
                return
                
            bom_id = int(bom_id_item.text())
            bom = BomService.get_bom_by_id(bom_id)
            bom_lines = BomService.get_bom_lines(bom_id)

            if not bom:
                QMessageBox.warning(self, "警告", "未找到BOM信息")
                return

            # 创建BOM查看对话框
            dialog = BomViewDialog(self, bom, bom_lines)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看BOM详情失败: {str(e)}")

    def edit_bom(self, row):
        """编辑BOM"""
        try:
            bom_id_item = self.bom_table.item(row, 0)
            if not bom_id_item:
                QMessageBox.warning(self, "警告", "无法获取BOM ID")
                return
                
            bom_id = int(bom_id_item.text())
            bom = BomService.get_bom_by_id(bom_id)

            if bom:
                # 使用新的集成编辑器
                dialog = BomEditorDialog(self, bom)
                if dialog.exec() == QDialog.Accepted:
                    self.load_boms()
            else:
                QMessageBox.warning(self, "警告", "未找到BOM信息")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑BOM失败: {str(e)}")

    def delete_bom(self, row):
        """删除BOM"""
        try:
            bom_id_item = self.bom_table.item(row, 0)
            bom_name_item = self.bom_table.item(row, 1)
            
            if not bom_id_item or not bom_name_item:
                QMessageBox.warning(self, "警告", "无法获取BOM信息")
                return
                
            bom_id = int(bom_id_item.text())
            bom_name = bom_name_item.text()

            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除BOM '{bom_name}' 吗？\n删除后无法恢复！",
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


class BomExpandDialog(QDialog):
    """BOM展开对话框"""

    def __init__(self, parent=None, fg_items=None):
        super().__init__(parent)
        self.fg_items = fg_items or []
        self.setWindowTitle("BOM展开")
        self.resize(800, 650)
        self.setMinimumSize(700, 550)
        self.setMaximumSize(1000, 800)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title_label = QLabel("BOM展开 - 计算生产所需物料")
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

        # 选择区域 - 紧凑布局
        select_group = QGroupBox("选择产品和数量")
        select_group.setStyleSheet("""
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

        select_layout = QFormLayout(select_group)
        select_layout.setSpacing(10)

        # 产品选择
        self.product_combo = QComboBox()
        self.product_combo.setPlaceholderText("请选择要生产的产品")
        for item in self.fg_items:
            # 修复SQLite Row对象的访问方式
            item_code = item['ItemCode'] if 'ItemCode' in item.keys() else ''
            item_name = item['CnName'] if 'CnName' in item.keys() else ''
            item_spec = item['ItemSpec'] if 'ItemSpec' in item.keys() else ''
            item_brand = item['Brand'] if 'Brand' in item.keys() else ''
            item_id = item['ItemId'] if 'ItemId' in item.keys() else 0
            
            # 格式：商品品牌-物资名称-物资规格
            display_text = f"{item_brand} - {item_name} - {item_spec}"
            self.product_combo.addItem(display_text, item_id)
        select_layout.addRow("产品 *:", self.product_combo)

        # 生产数量
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(1, 999999)
        self.qty_spin.setDecimals(0)
        self.qty_spin.setValue(100)
        self.qty_spin.setSuffix(" 件")
        select_layout.addRow("生产数量 *:", self.qty_spin)

        # 展开按钮
        expand_btn = QPushButton("展开BOM")
        expand_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        expand_btn.clicked.connect(self.expand_bom)
        select_layout.addRow("", expand_btn)

        layout.addWidget(select_group)

        # 结果区域 - 占用更多空间
        result_group = QGroupBox("展开结果")
        result_group.setStyleSheet("""
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

        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(10, 10, 10, 10)

        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels([
            "物料编码", "物料名称", "物料类型", "需求数量", "单位"
        ])

        # 设置表格样式
        self.result_table.setStyleSheet("""
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
                padding: 8px 6px;
                border: none;
                border-bottom: 1px solid #e8e8e8;
                font-weight: 500;
                font-size: 12px;
            }
        """)

        # 设置表格属性
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setMinimumHeight(300)  # 设置最小高度
        self.result_table.verticalHeader().setDefaultSectionSize(30)  # 设置行高

        # 调整列宽
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 物料编码
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 物料名称
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 物料类型
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 需求数量
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 单位

        result_layout.addWidget(self.result_table)
        layout.addWidget(result_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        export_btn = QPushButton("导出结果")
        export_btn.setStyleSheet("""
                QPushButton {
                    background: #52c41a;
                    color: white;
                    border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                min-width: 100px;
                }
                QPushButton:hover {
                    background: #73d13d;
                }
            """)
        export_btn.clicked.connect(self.export_results)

        button_layout.addWidget(export_btn)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLineEdit, QComboBox, QDoubleSpinBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                min-width: 200px;
                min-height: 15px;
            }
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {
                border-color: #1890ff;
                }
            """)

    def expand_bom(self):
        """展开BOM"""
        try:
            product_id = self.product_combo.currentData()
            if not product_id:
                QMessageBox.warning(self, "警告", "请选择要生产的产品！")
                return

            qty = self.qty_spin.value()
            if qty <= 0:
                QMessageBox.warning(self, "警告", "生产数量必须大于0！")
                return

            # 使用BOM服务展开BOM
            expanded_items = BomService.expand_bom(product_id, qty)
            
            if not expanded_items:
                QMessageBox.information(self, "提示", "该产品没有BOM结构或BOM结构为空")
                return

            # 显示结果
            self.display_expanded_results(expanded_items)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"展开BOM失败: {str(e)}")

    def display_expanded_results(self, expanded_items):
        """显示展开结果"""
        try:
            # 按物料类型分组并汇总数量
            item_summary = {}
            for item in expanded_items:
                # 修复SQLite Row对象的访问方式
                item_id = item['ItemId'] if 'ItemId' in item.keys() else 0
                item_code = item['ItemCode'] if 'ItemCode' in item.keys() else ''
                item_name = item['ItemName'] if 'ItemName' in item.keys() else ''
                item_type = item['ItemType'] if 'ItemType' in item.keys() else ''
                unit = item['Unit'] if 'Unit' in item.keys() else '个'
                actual_qty = item['ActualQty'] if 'ActualQty' in item.keys() else 0
                
                item_key = (item_id, item_code, item_name, item_type, unit)
                if item_key in item_summary:
                    item_summary[item_key] += actual_qty
                else:
                    item_summary[item_key] = actual_qty

            # 填充表格
            self.result_table.setRowCount(len(item_summary))
            
            for row, ((item_id, item_code, item_name, item_type, unit), total_qty) in enumerate(item_summary.items()):
                self.result_table.setItem(row, 0, QTableWidgetItem(str(item_code)))
                self.result_table.setItem(row, 1, QTableWidgetItem(str(item_name)))
                self.result_table.setItem(row, 2, QTableWidgetItem(str(item_type)))
                self.result_table.setItem(row, 3, QTableWidgetItem(f"{total_qty:.3f}"))
                self.result_table.setItem(row, 4, QTableWidgetItem(str(unit)))

        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示展开结果失败: {str(e)}")

    def export_results(self):
        """导出结果"""
        try:
            if self.result_table.rowCount() == 0:
                QMessageBox.information(self, "提示", "没有数据可以导出")
                return

            # 这里可以添加导出到Excel或CSV的功能
            QMessageBox.information(self, "提示", "导出功能开发中...")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


class MaterialEditDialog(QDialog):
    """物料编辑对话框"""

    def __init__(self, parent=None, current_qty="1.0", current_scrap="0.0%", current_remark=""):
        super().__init__(parent)
        self.current_qty = current_qty
        self.current_scrap = current_scrap.replace("%", "") if "%" in current_scrap else current_scrap
        self.current_remark = current_remark
        
        self.setWindowTitle("编辑物料信息")
        self.resize(400, 320)
        self.setMinimumSize(380, 300)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        title_label = QLabel("编辑物料信息")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                padding: 8px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 表单区域
        form_group = QGroupBox("物料参数")
        form_group.setStyleSheet("""
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

        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(15)

        # 用量输入
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0.001, 999999)
        self.qty_spin.setDecimals(3)
        self.qty_spin.setValue(float(self.current_qty) if self.current_qty else 1.0)
        self.qty_spin.setSuffix(" 件")
        form_layout.addRow("用量 *:", self.qty_spin)

        # 损耗率输入
        self.scrap_spin = QDoubleSpinBox()
        self.scrap_spin.setRange(0, 100)
        self.scrap_spin.setDecimals(1)
        self.scrap_spin.setValue(float(self.current_scrap) if self.current_scrap else 0.0)
        self.scrap_spin.setSuffix(" %")
        form_layout.addRow("损耗率:", self.scrap_spin)

        # 备注输入
        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(60)
        self.remark_edit.setPlainText(str(self.current_remark))
        self.remark_edit.setPlaceholderText("请输入备注信息")
        form_layout.addRow("备注:", self.remark_edit)

        layout.addWidget(form_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(15)
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #666;
                border: 1px solid #ccc;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                border-color: #1890ff;
                color: #1890ff;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        save_btn.clicked.connect(self.validate_and_accept)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLineEdit, QComboBox, QTextEdit, QDoubleSpinBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                min-width: 200px;
                min-height: 15px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDoubleSpinBox:focus {
                border-color: #1890ff;
            }
        """)

    def validate_and_accept(self):
        """验证数据并接受"""
        try:
            # 验证用量
            qty = self.qty_spin.value()
            if qty <= 0:
                QMessageBox.warning(self, "警告", "用量必须大于0！")
                return

            # 验证损耗率
            scrap = self.scrap_spin.value()
            if scrap < 0 or scrap > 100:
                QMessageBox.warning(self, "警告", "损耗率必须在0-100%之间！")
                return

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"验证数据失败: {str(e)}")

    def get_edited_data(self):
        """获取编辑后的数据"""
        return (
            self.qty_spin.value(),
            self.scrap_spin.value(),
            self.remark_edit.toPlainText().strip()
        )


class BomViewDialog(QDialog):
    """BOM查看对话框"""

    def __init__(self, parent=None, bom_data=None, bom_lines=None):
        super().__init__(parent)
        self.bom_data = bom_data or {}
        self.bom_lines = bom_lines or []
        self.setWindowTitle("BOM 详情")
        self.resize(800, 600)
        self.setMinimumSize(700, 500)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        # 设置对话框背景色
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 20)  # 减少顶部边距
        layout.setSpacing(15)  # 减少间距

        # 标题
        title_label = QLabel("BOM 详情")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 4px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # BOM基本信息
        info_group = QGroupBox("BOM基本信息")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: 500;
                border: 1px solid #e8e8e8;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 13px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: #262626;
            }
        """)

        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(15)

        # BOM名称
        bom_name_label = QLabel(str(self.bom_data['BomName'] if 'BomName' in self.bom_data.keys() else ''))
        bom_name_label.setStyleSheet("font-size: 14px; color: #262626;")
        info_layout.addRow("BOM名称:", bom_name_label)

        # 版本
        rev_label = QLabel(str(self.bom_data['Rev'] if 'Rev' in self.bom_data.keys() else ''))
        rev_label.setStyleSheet("font-size: 14px; color: #262626;")
        info_layout.addRow("版本:", rev_label)

        # 生效日期
        effective_date = self.bom_data['EffectiveDate'] if 'EffectiveDate' in self.bom_data.keys() else ''
        effective_date_label = QLabel(str(effective_date))
        effective_date_label.setStyleSheet("font-size: 14px; color: #262626;")
        info_layout.addRow("生效日期:", effective_date_label)

        # 失效日期
        expire_date = self.bom_data['ExpireDate'] if 'ExpireDate' in self.bom_data.keys() else ''
        expire_date_label = QLabel(str(expire_date) if expire_date else "无")
        expire_date_label.setStyleSheet("font-size: 14px; color: #262626;")
        info_layout.addRow("失效日期:", expire_date_label)

        # 备注
        remark = self.bom_data['Remark'] if 'Remark' in self.bom_data.keys() else ''
        remark_label = QLabel(str(remark) if remark else "无")
        remark_label.setStyleSheet("font-size: 14px; color: #262626;")
        remark_label.setWordWrap(True)
        info_layout.addRow("备注:", remark_label)

        layout.addWidget(info_group)

        # BOM结构
        structure_group = QGroupBox("BOM结构")
        structure_group.setStyleSheet("""
            QGroupBox {
                font-weight: 500;
                border: 1px solid #e8e8e8;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 13px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
                color: #262626;
            }
        """)

        structure_layout = QVBoxLayout(structure_group)
        structure_layout.setContentsMargins(10, 15, 10, 10)  # 增加内边距

        # BOM结构表格
        self.structure_table = QTableWidget()
        self.structure_table.setColumnCount(6)
        self.structure_table.setHorizontalHeaderLabels([
            "物料编码", "物料名称", "规格型号", "用量", "损耗率", "备注"
        ])

        # 设置表格样式
        self.structure_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e8e8e8;
                background-color: white;
                alternate-background-color: #f8f9fa;
                selection-background-color: #e6f7ff;
                selection-color: #262626;
                border: 1px solid #e8e8e8;
                border-radius: 4px;
                font-size: 13px;
                min-height: 300px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #262626;
                padding: 8px 6px;
                border: none;
                border-bottom: 1px solid #e8e8e8;
                font-weight: 500;
                font-size: 12px;
            }
        """)

        # 设置表格属性
        self.structure_table.setAlternatingRowColors(True)
        self.structure_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.structure_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # 调整列宽
        header = self.structure_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 物料编码
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 物料名称
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 规格型号
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 用量
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 损耗率
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 备注

        structure_layout.addWidget(self.structure_table)
        layout.addWidget(structure_group)

        # 填充BOM结构数据
        self.populate_structure_table()

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #1890ff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background: #40a9ff;
            }
        """)
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def populate_structure_table(self):
        """填充BOM结构表格"""
        if not self.bom_lines:
            return

        self.structure_table.setRowCount(len(self.bom_lines))

        for row, line in enumerate(self.bom_lines):
            # 修复SQLite Row对象的访问方式
            child_item_code = line['ChildItemCode'] if 'ChildItemCode' in line.keys() else ''
            child_item_name = line['ChildItemName'] if 'ChildItemName' in line.keys() else ''
            child_item_spec = line['ChildItemSpec'] if 'ChildItemSpec' in line.keys() else ''
            qty_per = line['QtyPer'] if 'QtyPer' in line.keys() else 0
            scrap_factor = line['ScrapFactor'] if 'ScrapFactor' in line.keys() else 0
            remark = line['Remark'] if 'Remark' in line.keys() else ''

            # 物料编码
            self.structure_table.setItem(row, 0, QTableWidgetItem(str(child_item_code)))
            # 物料名称
            self.structure_table.setItem(row, 1, QTableWidgetItem(str(child_item_name)))
            # 规格型号
            self.structure_table.setItem(row, 2, QTableWidgetItem(str(child_item_spec)))
            # 用量
            self.structure_table.setItem(row, 3, QTableWidgetItem(str(qty_per)))
            # 损耗率
            scrap_factor_display = f"{scrap_factor * 100:.1f}%" if scrap_factor else "0.0%"
            self.structure_table.setItem(row, 4, QTableWidgetItem(scrap_factor_display))
            # 备注
            self.structure_table.setItem(row, 5, QTableWidgetItem(str(remark) if remark else ""))


