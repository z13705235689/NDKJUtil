#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库查看和编辑工具
支持查看数据库结构、数据，以及Excel导入导出
"""

import sqlite3
import pandas as pd
import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
                               QPushButton, QLabel, QFileDialog, QMessageBox, QTextEdit,
                               QHeaderView, QSplitter, QFrame, QComboBox)
from PySide6.QtCore import Qt

class DatabaseViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_path = None
        self.setup_ui()
        self.load_database()
    
    def setup_ui(self):
        self.setWindowTitle("数据库查看和编辑工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 数据库路径显示
        path_frame = QFrame()
        path_layout = QHBoxLayout(path_frame)
        path_layout.addWidget(QLabel("数据库路径:"))
        self.path_label = QLabel("未选择数据库")
        self.path_label.setStyleSheet("color: #666; font-style: italic;")
        path_layout.addWidget(self.path_label)
        path_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新数据库")
        refresh_btn.clicked.connect(self.load_database)
        path_layout.addWidget(refresh_btn)
        
        main_layout.addWidget(path_frame)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 数据库结构标签页
        self.create_structure_tab()
        
        # 数据查看标签页
        self.create_data_tab()
        
        # Excel导入导出标签页
        self.create_excel_tab()
        
        main_layout.addWidget(self.tab_widget)
    
    def create_structure_tab(self):
        """创建数据库结构标签页"""
        structure_widget = QWidget()
        structure_layout = QVBoxLayout(structure_widget)
        
        # 表列表
        structure_layout.addWidget(QLabel("数据库表结构:"))
        
        self.structure_table = QTableWidget()
        self.structure_table.setColumnCount(5)
        self.structure_table.setHorizontalHeaderLabels([
            "表名", "列名", "数据类型", "是否非空", "默认值"
        ])
        
        # 设置表格样式
        self.structure_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e9ecef;
                background-color: white;
                alternate-background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: 600;
            }
        """)
        
        # 设置列宽
        header = self.structure_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        structure_layout.addWidget(self.structure_table)
        
        self.tab_widget.addTab(structure_widget, "数据库结构")
    
    def create_data_tab(self):
        """创建数据查看标签页"""
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        
        # 表选择
        table_frame = QFrame()
        table_layout = QHBoxLayout(table_frame)
        table_layout.addWidget(QLabel("选择表:"))
        
        self.table_combo = QComboBox()
        self.table_combo.currentTextChanged.connect(self.load_table_data)
        table_layout.addWidget(self.table_combo)
        
        table_layout.addStretch()
        
        # 导出按钮
        export_btn = QPushButton("导出到Excel")
        export_btn.clicked.connect(self.export_table_to_excel)
        table_layout.addWidget(export_btn)
        
        data_layout.addWidget(table_frame)
        
        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e9ecef;
                background-color: white;
                alternate-background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: 600;
            }
        """)
        
        data_layout.addWidget(self.data_table)
        
        self.tab_widget.addTab(data_widget, "数据查看")
    
    def create_excel_tab(self):
        """创建Excel导入导出标签页"""
        excel_widget = QWidget()
        excel_layout = QVBoxLayout(excel_widget)
        
        # 导入区域
        import_frame = QFrame()
        import_frame.setFrameStyle(QFrame.StyledPanel)
        import_layout = QVBoxLayout(import_frame)
        
        import_layout.addWidget(QLabel("从Excel导入数据:"))
        
        # 选择Excel文件
        file_frame = QFrame()
        file_layout = QHBoxLayout(file_frame)
        file_layout.addWidget(QLabel("Excel文件:"))
        
        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setStyleSheet("color: #666; font-style: italic;")
        file_layout.addWidget(self.file_path_label)
        
        select_file_btn = QPushButton("选择文件")
        select_file_btn.clicked.connect(self.select_excel_file)
        file_layout.addWidget(select_file_btn)
        
        import_layout.addWidget(file_frame)
        
        # 表选择
        table_select_frame = QFrame()
        table_select_layout = QHBoxLayout(table_select_frame)
        table_select_layout.addWidget(QLabel("目标表:"))
        
        self.import_table_combo = QComboBox()
        table_select_layout.addWidget(self.import_table_combo)
        
        import_layout.addWidget(table_select_frame)
        
        # 导入按钮
        import_btn = QPushButton("导入数据")
        import_btn.clicked.connect(self.import_from_excel)
        import_layout.addWidget(import_btn)
        
        excel_layout.addWidget(import_frame)
        
        # 导出区域
        export_frame = QFrame()
        export_frame.setFrameStyle(QFrame.StyledPanel)
        export_layout = QVBoxLayout(export_frame)
        
        export_layout.addWidget(QLabel("导出数据到Excel:"))
        
        # 导出按钮
        export_all_btn = QPushButton("导出所有表到Excel")
        export_all_btn.clicked.connect(self.export_all_tables)
        export_layout.addWidget(export_all_btn)
        
        excel_layout.addWidget(export_frame)
        
        # 日志区域
        log_frame = QFrame()
        log_frame.setFrameStyle(QFrame.StyledPanel)
        log_layout = QVBoxLayout(log_frame)
        
        log_layout.addWidget(QLabel("操作日志:"))
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: #f8f9fa;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        excel_layout.addWidget(log_frame)
        
        self.tab_widget.addTab(excel_widget, "Excel导入导出")
    
    def load_database(self):
        """加载数据库"""
        try:
            # 尝试多个可能的数据库路径
            possible_paths = [
                "mes.db",
                Path(__file__).parent / "mes.db",
                Path.home() / "AppData" / "Local" / "MES_MRP_PY" / "mes.db"
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    self.db_path = str(path)
                    break
            
            if not self.db_path:
                self.log_message("未找到数据库文件，请确保数据库已创建")
                return
            
            self.path_label.setText(self.db_path)
            self.log_message(f"成功加载数据库: {self.db_path}")
            
            # 加载数据库结构
            self.load_database_structure()
            
            # 加载表列表
            self.load_table_list()
            
        except Exception as e:
            self.log_message(f"加载数据库失败: {e}")
    
    def load_database_structure(self):
        """加载数据库结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            structure_data = []
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                for col in columns:
                    structure_data.append([
                        table_name,
                        col[1],  # 列名
                        col[2],  # 数据类型
                        "是" if col[3] else "否",  # 是否非空
                        col[4] if col[4] else ""   # 默认值
                    ])
            
            # 填充表格
            self.structure_table.setRowCount(len(structure_data))
            for row, data in enumerate(structure_data):
                for col, value in enumerate(data):
                    self.structure_table.setItem(row, col, QTableWidgetItem(str(value)))
            
            conn.close()
            self.log_message(f"加载了 {len(structure_data)} 个字段的结构信息")
            
        except Exception as e:
            self.log_message(f"加载数据库结构失败: {e}")
    
    def load_table_list(self):
        """加载表列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            table_names = [table[0] for table in tables]
            
            # 更新下拉框
            self.table_combo.clear()
            self.table_combo.addItems(table_names)
            
            self.import_table_combo.clear()
            self.import_table_combo.addItems(table_names)
            
            conn.close()
            
        except Exception as e:
            self.log_message(f"加载表列表失败: {e}")
    
    def load_table_data(self, table_name):
        """加载表数据"""
        if not table_name:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 使用pandas读取数据
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            
            # 设置表格行列数
            self.data_table.setRowCount(len(df))
            self.data_table.setColumnCount(len(df.columns))
            
            # 设置表头
            self.data_table.setHorizontalHeaderLabels(df.columns)
            
            # 填充数据
            for row in range(len(df)):
                for col in range(len(df.columns)):
                    value = str(df.iloc[row, col]) if pd.notna(df.iloc[row, col]) else ""
                    self.data_table.setItem(row, col, QTableWidgetItem(value))
            
            # 调整列宽
            header = self.data_table.horizontalHeader()
            for i in range(len(df.columns)):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
            conn.close()
            self.log_message(f"成功加载表 {table_name} 的数据，共 {len(df)} 行")
            
        except Exception as e:
            self.log_message(f"加载表数据失败: {e}")
    
    def select_excel_file(self):
        """选择Excel文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.file_path_label.setText(file_path)
            self.log_message(f"选择文件: {file_path}")
    
    def import_from_excel(self):
        """从Excel导入数据"""
        if not self.file_path_label.text() or self.file_path_label.text() == "未选择文件":
            QMessageBox.warning(self, "警告", "请先选择Excel文件")
            return
        
        table_name = self.import_table_combo.currentText()
        if not table_name:
            QMessageBox.warning(self, "警告", "请选择目标表")
            return
        
        try:
            # 读取Excel文件
            df = pd.read_excel(self.file_path_label.text())
            
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            
            # 导入数据
            df.to_sql(table_name, conn, if_exists='append', index=False)
            
            conn.close()
            
            self.log_message(f"成功导入 {len(df)} 行数据到表 {table_name}")
            QMessageBox.information(self, "成功", f"成功导入 {len(df)} 行数据")
            
            # 刷新数据
            if table_name == self.table_combo.currentText():
                self.load_table_data(table_name)
            
        except Exception as e:
            self.log_message(f"导入失败: {e}")
            QMessageBox.critical(self, "错误", f"导入失败: {e}")
    
    def export_table_to_excel(self):
        """导出表数据到Excel"""
        table_name = self.table_combo.currentText()
        if not table_name:
            QMessageBox.warning(self, "警告", "请先选择要导出的表")
            return
        
        try:
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存Excel文件", f"{table_name}.xlsx", "Excel Files (*.xlsx)"
            )
            
            if file_path:
                # 读取表数据
                conn = sqlite3.connect(self.db_path)
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                conn.close()
                
                # 导出到Excel
                df.to_excel(file_path, index=False)
                
                self.log_message(f"成功导出表 {table_name} 到 {file_path}")
                QMessageBox.information(self, "成功", f"成功导出到 {file_path}")
                
        except Exception as e:
            self.log_message(f"导出失败: {e}")
            QMessageBox.critical(self, "错误", f"导出失败: {e}")
    
    def export_all_tables(self):
        """导出所有表到Excel"""
        try:
            # 选择保存目录
            save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
            if not save_dir:
                return
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            exported_count = 0
            
            for table in tables:
                table_name = table[0]
                try:
                    # 读取表数据
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    
                    # 保存到Excel
                    file_path = os.path.join(save_dir, f"{table_name}.xlsx")
                    df.to_excel(file_path, index=False)
                    
                    exported_count += 1
                    self.log_message(f"导出表 {table_name} 到 {file_path}")
                    
                except Exception as e:
                    self.log_message(f"导出表 {table_name} 失败: {e}")
            
            conn.close()
            
            self.log_message(f"成功导出 {exported_count} 个表")
            QMessageBox.information(self, "成功", f"成功导出 {exported_count} 个表到 {save_dir}")
            
        except Exception as e:
            self.log_message(f"批量导出失败: {e}")
            QMessageBox.critical(self, "错误", f"批量导出失败: {e}")
    
    def log_message(self, message):
        """记录日志消息"""
        self.log_text.append(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] {message}")

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    window = DatabaseViewer()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
