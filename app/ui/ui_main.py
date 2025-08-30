import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QStackedWidget,
                               QFrame, QScrollArea, QSizePolicy, QTabWidget)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QLinearGradient
from app.ui.materia_management import ItemEditor
from app.ui.bom_management import BomManagementWidget
from app.ui.customer_order_management import CustomerOrderManagement
from app.ui.inventory_management import InventoryManagement
from app.ui.mrp_viewer import MRPViewer
from app.ui.database_management import DatabaseManagement


class ModernButton(QPushButton):
    """现代化按钮样式"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)  # 减小按钮高度
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2c3e50, stop:1 #34495e);
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: 500;
                text-align: left;
                padding-left: 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #3498db, stop:1 #2980b9);
            }
        """)


class SidebarButton(QPushButton):
    """侧边栏按钮"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)  # 减小按钮高度
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #595959;
                font-size: 13px;
                font-weight: 400;
                text-align: left;
                padding-left: 20px;
                padding-right: 20px;
                border-radius: 6px;
                margin: 0px 6px;
            }
            QPushButton:hover {
                background: rgba(24, 144, 255, 0.1);
                color: #1890ff;
            }
            QPushButton:checked {
                background: rgba(24, 144, 255, 0.1);
                color: #1890ff;
                font-weight: 500;
                border-left: 3px solid #1890ff;
                padding-left: 17px;
            }
        """)


class Sidebar(QFrame):
    """侧边栏导航"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window  # 保存主窗口引用
        self.setFixedWidth(260)  # 减小侧边栏宽度
        self.setStyleSheet("""
            QFrame {
                background: #fafafa;
                border: none;
                border-right: 1px solid #e8e8e8;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo区域
        logo_frame = QFrame()
        logo_frame.setFixedHeight(70)  # 减小Logo区域高度
        logo_frame.setStyleSheet("""
            QFrame {
                background: #1890ff;
                border-bottom: 1px solid rgba(24, 144, 255, 0.2);
            }
        """)
        
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(20, 15, 20, 15)
        logo_layout.setSpacing(3)
        
        # 系统标题
        title_label = QLabel("MES 生产管理系统")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: 500;
                text-align: center;
                letter-spacing: 1px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        subtitle_label = QLabel("Manufacturing Execution System")
        subtitle_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 10px;
                text-align: center;
                font-weight: 400;
                letter-spacing: 0.5px;
            }
        """)
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        logo_layout.addWidget(title_label)
        logo_layout.addWidget(subtitle_label)
        
        layout.addWidget(logo_frame)
        
        # 导航按钮
        nav_frame = QFrame()
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 20, 0, 20)
        nav_layout.setSpacing(2)
        
        # 创建导航按钮
        self.nav_buttons = []
        
        # 物料管理（主菜单项）
        material_btn = SidebarButton("物料管理")
        material_btn.setCheckable(True)
        material_btn.clicked.connect(lambda: self.on_nav_clicked("物料管理"))
        nav_layout.addWidget(material_btn)
        self.nav_buttons.append(material_btn)
        
        # 其他主菜单项
        other_nav_items = [
            "BOM 管理", 
            "客户订单",
            "库存管理",
            "MRP 计算",
            "数据库管理",
            "自动排产",
            "库存监控",
            "系统设置"
        ]
        
        for text in other_nav_items:
            btn = SidebarButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=text: self.on_nav_clicked(t))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        # 默认选中第一个
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)
        
        # 添加弹性空间
        nav_layout.addStretch()
        
        # 底部信息
        bottom_frame = QFrame()
        bottom_frame.setFixedHeight(60)  # 减小底部区域高度
        bottom_frame.setStyleSheet("""
            QFrame {
                background: rgba(24, 144, 255, 0.05);
                border-top: 1px solid rgba(24, 144, 255, 0.1);
            }
        """)
        
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        
        version_label = QLabel("Version 1.0.0")
        version_label.setStyleSheet("""
            QLabel {
                color: #8c8c8c;
                font-size: 11px;
                text-align: center;
            }
        """)
        version_label.setAlignment(Qt.AlignCenter)
        
        bottom_layout.addWidget(version_label)
        
        layout.addWidget(nav_frame)
        layout.addWidget(bottom_frame)
    
    def on_nav_clicked(self, text):
        """主导航按钮点击事件"""
        # 取消所有主导航按钮的选中状态
        for btn in self.nav_buttons:
            btn.setChecked(False)
        
        # 选中当前点击的按钮
        for btn in self.nav_buttons:
            if btn.text() == text:
                btn.setChecked(True)
                break
        
        # 直接调用主窗口的方法
        if self.main_window and hasattr(self.main_window, 'on_page_changed'):
            self.main_window.on_page_changed(text)


class ContentArea(QFrame):
    """内容区域"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: none;
            }
        """)
        
        # 设置大小策略，允许内容区域拉伸
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)  # 减小边距
        
        # 欢迎页面
        welcome_frame = QFrame()
        welcome_frame.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 8px;
                border: 1px solid #f0f0f0;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
            }
        """)
        
        welcome_layout = QVBoxLayout(welcome_frame)
        welcome_layout.setContentsMargins(32, 32, 32, 32)  # 减小内边距
        welcome_layout.setSpacing(20)  # 减小间距
        
        # 欢迎标题 - 减小字体
        welcome_title = QLabel("MES/MRP 制造执行系统")
        welcome_title.setStyleSheet("""
            QLabel {
                color: #262626;
                font-size: 22px;
                font-weight: 600;
                text-align: center;
                letter-spacing: 0.5px;
            }
        """)
        welcome_title.setAlignment(Qt.AlignCenter)
        
        # 副标题 - 减小字体
        welcome_subtitle = QLabel("Manufacturing Execution System & Material Requirements Planning")
        welcome_subtitle.setStyleSheet("""
            QLabel {
                color: #8c8c8c;
                font-size: 12px;
                text-align: center;
                font-weight: 400;
                letter-spacing: 0.3px;
            }
        """)
        welcome_subtitle.setAlignment(Qt.AlignCenter)
        
        # 功能特性
        features_frame = QFrame()
        features_layout = QHBoxLayout(features_frame)
        features_layout.setSpacing(20)  # 减小间距
        features_layout.setContentsMargins(0, 12, 0, 0)
        
        feature_items = [
            ("BOM", "BOM管理", "支持多层级BOM结构，版本控制"),
            ("ORDER", "订单管理", "智能订单展开，需求预测"),
            ("MRP", "MRP计算", "自动计算物料需求计划"),
            ("SCHEDULE", "智能排产", "基于约束的自动排产算法"),
            ("STOCK", "库存管理", "实时库存监控，安全库存预警"),
            ("REPORT", "数据分析", "多维度报表分析，决策支持")
        ]
        
        for icon, title, desc in feature_items:
            feature_card = self.create_feature_card(icon, title, desc)
            features_layout.addWidget(feature_card)
        
        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(welcome_subtitle)
        welcome_layout.addWidget(features_frame)
        welcome_layout.addStretch()
        
        layout.addWidget(welcome_frame)
        
        # 创建堆叠窗口部件用于页面切换
        self.stacked_widget = QStackedWidget()
        
        # 欢迎页面
        self.welcome_page = welcome_frame
        self.stacked_widget.addWidget(self.welcome_page)
        
        # 物料管理页面
        self.material_page = self.create_material_management_page()
        self.stacked_widget.addWidget(self.material_page)
        
        # BOM管理页面
        self.bom_page = self.create_bom_management_page()
        self.stacked_widget.addWidget(self.bom_page)
        
        # 客户订单管理页面
        self.customer_order_page = self.create_customer_order_page()
        self.stacked_widget.addWidget(self.customer_order_page)

        # 库存管理页面
        self.inventory_page = self.create_inventory_page()
        self.stacked_widget.addWidget(self.inventory_page)

        # MRP计算页面
        self.mrp_page = self.create_mrp_page()
        self.stacked_widget.addWidget(self.mrp_page)

        # 数据库管理页面
        self.database_page = self.create_database_page()
        self.stacked_widget.addWidget(self.database_page)

        # 其他页面占位符
        self.placeholder_page = self.create_placeholder_page("功能开发中...")
        self.stacked_widget.addWidget(self.placeholder_page)
        
        # 替换为堆叠窗口
        layout.removeWidget(welcome_frame)
        layout.addWidget(self.stacked_widget)
    
    def create_feature_card(self, icon, title, desc):
        """创建功能特性卡片"""
        card = QFrame()
        card.setFixedSize(160, 100)  # 减小卡片尺寸
        card.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 6px;
                border: 1px solid #f0f0f0;
            }
            QFrame:hover {
                border: 1px solid #1890ff;
                box-shadow: 0 1px 4px rgba(24, 144, 255, 0.1);
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)  # 减小内边距
        layout.setSpacing(6)  # 减小间距
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("""
            QLabel {
                color: #1890ff;
                font-size: 11px;
                font-weight: 500;
                text-align: center;
                background: rgba(24, 144, 255, 0.08);
                padding: 3px 6px;
                border-radius: 10px;
            }
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #262626;
                font-size: 12px;
                font-weight: 500;
                text-align: center;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        
        # 描述
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("""
            QLabel {
                color: #8c8c8c;
                font-size: 10px;
                text-align: center;
                line-height: 1.3;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        
        return card
    
    def create_placeholder_page(self, message):
        """创建占位页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)  # 减小边距
        
        placeholder_frame = QFrame()
        placeholder_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-radius: 12px;
                border: 1px solid #e9ecef;
            }
        """)
        
        placeholder_layout = QVBoxLayout(placeholder_frame)
        placeholder_layout.setContentsMargins(32, 32, 32, 32)  # 减小内边距
        
        # 占位标题 - 减小字体
        placeholder_title = QLabel(message)
        placeholder_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 24px;
                font-weight: bold;
                text-align: center;
            }
        """)
        placeholder_title.setAlignment(Qt.AlignCenter)
        
        placeholder_layout.addWidget(placeholder_title)
        placeholder_layout.addStretch()
        
        layout.addWidget(placeholder_frame)
        return page
    
    def switch_to_page(self, page_index):
        """切换到指定页面"""
        self.stacked_widget.setCurrentIndex(page_index)
    
    def create_material_management_page(self):
        """创建物料管理页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)  # 减小边距
        layout.setSpacing(16)  # 减小间距
        
        # 物料管理
        self.item_editor = ItemEditor()
        layout.addWidget(self.item_editor)
        
        return page
    
    def create_bom_management_page(self):
        """创建BOM管理页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)  # 减小边距
        layout.setSpacing(16)  # 减小间距
        
        # BOM管理
        self.bom_editor = BomManagementWidget()
        layout.addWidget(self.bom_editor)
        
        return page
    
    def create_customer_order_page(self):
        """创建客户订单管理页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)  # 减小边距
        layout.setSpacing(16)  # 减小间距

        # 客户订单管理
        self.customer_order_editor = CustomerOrderManagement()
        layout.addWidget(self.customer_order_editor)
        return page

    def create_inventory_page(self):
        """创建库存管理页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        self.inventory_widget = InventoryManagement()
        layout.addWidget(self.inventory_widget)
        return page

    def create_mrp_page(self):
        """创建MRP计算页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        self.mrp_widget = MRPViewer()
        layout.addWidget(self.mrp_widget)
        return page

    def create_database_page(self):
        """创建数据库管理页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        self.database_widget = DatabaseManagement()
        layout.addWidget(self.database_widget)
        return page


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MES 生产管理系统")
        self.setMinimumSize(1000, 700)  # 调整最小尺寸
        self.resize(1200, 800)  # 调整默认窗口大小
        self.setStyleSheet("""
            QMainWindow {
                background: white;
                font-family: "Microsoft YaHei UI", "Segoe UI", system-ui, sans-serif;
            }
        """)
        
        # 设置窗口大小策略
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.setup_ui()
    
    def setup_ui(self):
        # 中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 侧边栏
        self.sidebar = Sidebar(self, self)  # 传递主窗口引用
        main_layout.addWidget(self.sidebar)
        
        # 内容区域
        self.content_area = ContentArea(self)
        main_layout.addWidget(self.content_area)
        
        # 设置布局的拉伸因子，使内容区域可以调整大小
        main_layout.setStretch(0, 0)  # 侧边栏固定宽度
        main_layout.setStretch(1, 1)  # 内容区域可拉伸
        
        # 设置窗口图标 - 移除不存在的图标
        # self.setWindowIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
    
    def on_page_changed(self, page_name):
        """页面切换事件"""
        # 根据页面名称切换到对应页面
        if "物料管理" in page_name:
            self.content_area.switch_to_page(1)  # 物料管理页面
        elif "BOM 管理" in page_name:
            self.content_area.switch_to_page(2)  # BOM管理页面
        elif "客户订单" in page_name:
            self.content_area.switch_to_page(3)  # 客户订单管理页面
        elif "库存管理" in page_name:
            self.content_area.switch_to_page(4)  # 库存管理页面
        elif "MRP 计算" in page_name:
            self.content_area.switch_to_page(5)  # MRP页面
        elif "数据库管理" in page_name:
            self.content_area.switch_to_page(6)  # 数据库管理页面
        elif "自动排产" in page_name:
            self.content_area.switch_to_page(7)  # 占位页面
        elif "库存监控" in page_name:
            self.content_area.switch_to_page(7)  # 占位页面
        elif "系统设置" in page_name:
            self.content_area.switch_to_page(7)  # 占位页面
        else:
            self.content_area.switch_to_page(0)  # 默认欢迎页面
    



def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("牛大MES生产管理")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Niuda Technology")
    
    # 初始化数据库
    try:
        from app.db import DatabaseManager
        db_manager = DatabaseManager()
        print("数据库初始化成功")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        return
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
