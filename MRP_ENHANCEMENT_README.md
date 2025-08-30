# MRP功能增强说明

## 概述

本次更新对MRP（物料需求计划）功能进行了重大增强，增加了客户订单选择、成品筛选和成品MRP计算等核心功能，使MRP系统更加实用和灵活。

## 新增功能

### 1. 客户订单版本选择 🎯

**功能描述**：
- 支持选择特定的客户订单版本进行MRP计算
- 不同版本的客户订单可能有不同的周需求量
- 可以针对特定订单版本进行精确的物料需求计算

**使用方法**：
- 在MRP界面选择"客户订单版本"下拉框
- 选择"全部订单汇总"或具体的订单版本ID
- 系统会根据选择的订单版本计算对应的MRP

**技术实现**：
```python
# 获取可用的客户订单版本
versions = MRPService.get_available_import_versions()

# 按指定版本计算MRP
result = MRPService.calculate_mrp_kanban(
    start_date, end_date, 
    import_id=selected_version_id
)
```

### 2. 成品筛选功能 🔍

**功能描述**：
- 支持按成品编码或名称进行模糊筛选
- 可以只计算特定成品的MRP需求
- 提高计算效率，减少不必要的数据处理

**使用方法**：
- 在"成品筛选"输入框中输入筛选条件
- 支持部分匹配，如输入"R001"可筛选所有以R001开头的成品
- 留空表示计算所有成品的MRP

**技术实现**：
```python
# 按筛选条件计算MRP
result = MRPService.calculate_mrp_kanban(
    start_date, end_date, 
    import_id=import_id,
    parent_item_filter="R001"  # 筛选条件
)
```

### 3. 成品MRP计算模式 📊

**功能描述**：
- 新增"成品MRP"计算模式
- 直接显示成品的需求计划，不展开BOM
- 提供两种计算模式：零部件MRP和成品MRP

**计算模式对比**：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 零部件MRP | 展开BOM计算原材料需求 | 采购计划、库存管理 |
| 成品MRP | 直接显示成品需求 | 生产计划、订单管理 |

**技术实现**：
```python
# 零部件MRP计算
child_result = MRPService.calculate_mrp_kanban(
    start_date, end_date, 
    import_id=import_id
)

# 成品MRP计算
parent_result = MRPService.calculate_parent_mrp_kanban(
    start_date, end_date, 
    import_id=import_id
)
```

## 界面更新

### 控制面板优化

**新增控件**：
1. **客户订单版本选择**：下拉框，显示所有可用的订单版本
2. **成品筛选输入框**：支持模糊搜索的文本输入框
3. **计算类型选择**：下拉框，选择零部件MRP或成品MRP
4. **功能说明标签**：解释两种计算模式的区别

**布局优化**：
- 采用分组布局，逻辑更清晰
- 控件大小适中，用户体验更好
- 响应式设计，支持不同屏幕尺寸

### 表格展示增强

**颜色区分**：
- **零部件MRP**：
  - 生产计划行：默认背景
  - 即时库存行：绿色背景
  - 负库存单元格：红色背景（预警）
- **成品MRP**：
  - 所有行：蓝色背景
  - 需求数量>0：绿色高亮

**列标题优化**：
- 根据计算类型动态调整列标题
- 零部件MRP：物料编码、物料名称、物料类型...
- 成品MRP：成品编码、成品名称、成品类型...

## 技术架构

### 服务层增强

**MRPService类新增方法**：
```python
class MRPService:
    @staticmethod
    def calculate_mrp_kanban(start_date, end_date, import_id=None, 
                            parent_item_filter=None, include_types=("RM", "PKG"))
    
    @staticmethod
    def calculate_parent_mrp_kanban(start_date, end_date, import_id=None, 
                                   parent_item_filter=None)
    
    @staticmethod
    def get_available_import_versions()
    
    @staticmethod
    def get_available_parent_items()
```

**核心算法优化**：
- 支持按订单版本筛选需求数据
- 支持按成品条件筛选
- 保持原有的BOM展开逻辑
- 新增成品级别的需求汇总

### 数据查询优化

**SQL查询增强**：
```sql
-- 支持订单版本筛选
SELECT i.ItemId, col.CalendarWeek, SUM(col.RequiredQty) AS Qty
FROM CustomerOrderLines col
JOIN CustomerOrders co ON col.OrderId = co.OrderId
JOIN Items i ON i.ItemCode = col.ItemNumber
WHERE col.LineStatus='Active' 
  AND col.DeliveryDate BETWEEN ? AND ?
  AND co.ImportId = ?  -- 新增：订单版本筛选
  AND (i.ItemCode LIKE ? OR i.CnName LIKE ?)  -- 新增：成品筛选
GROUP BY i.ItemId, col.CalendarWeek
```

### 多线程处理

**计算线程优化**：
- 支持两种计算模式
- 参数传递更灵活
- 错误处理更完善
- 避免界面卡顿

## 使用场景

### 1. 按订单版本计算MRP

**适用情况**：
- 需要针对特定客户订单进行物料计划
- 不同订单版本的需求量差异较大
- 需要精确控制物料需求来源

**操作步骤**：
1. 选择具体的客户订单版本
2. 设置日期范围
3. 选择"零部件MRP"计算模式
4. 点击"生成看板"

### 2. 按成品筛选计算MRP

**适用情况**：
- 只关心特定产品系列的物料需求
- 需要减少计算复杂度
- 重点关注某些核心产品

**操作步骤**：
1. 在成品筛选框中输入筛选条件
2. 选择计算模式
3. 设置其他参数
4. 生成MRP看板

### 3. 成品需求计划

**适用情况**：
- 需要了解成品的直接需求计划
- 不关心原材料的详细需求
- 用于生产计划和产能规划

**操作步骤**：
1. 选择"成品MRP"计算模式
2. 设置订单版本和筛选条件
3. 生成成品需求看板

## 测试验证

### 运行测试脚本

```bash
python test_mrp_enhanced.py
```

**测试内容**：
1. 客户订单版本获取
2. 成品列表获取
3. 零部件MRP计算
4. 成品MRP计算
5. 成品筛选功能
6. 界面组件导入

### 功能验证要点

**基本功能**：
- ✅ 客户订单版本选择正常
- ✅ 成品筛选输入正常
- ✅ 计算类型切换正常
- ✅ 日期范围设置正常

**计算功能**：
- ✅ 零部件MRP计算正确
- ✅ 成品MRP计算正确
- ✅ 筛选条件生效
- ✅ 结果展示正确

**界面体验**：
- ✅ 控件布局合理
- ✅ 颜色区分清晰
- ✅ 响应速度良好
- ✅ 错误提示友好

## 注意事项

### 1. 数据依赖

**前提条件**：
- 必须有客户订单数据
- 必须有BOM结构数据
- 必须有库存余额数据

**数据完整性**：
- 确保订单数据与物料主数据关联正确
- 确保BOM结构完整且无循环引用
- 确保库存数据及时更新

### 2. 性能考虑

**计算复杂度**：
- 零部件MRP计算复杂度较高（需要展开BOM）
- 成品MRP计算复杂度较低（直接汇总需求）
- 筛选条件可以减少计算量

**优化建议**：
- 合理设置日期范围，避免计算过多周次
- 使用成品筛选减少不必要的计算
- 考虑数据缓存机制

### 3. 使用建议

**最佳实践**：
- 优先使用成品筛选功能减少计算量
- 根据实际需要选择计算模式
- 定期验证计算结果的准确性

**常见问题**：
- 如果计算结果为空，检查筛选条件和数据完整性
- 如果计算速度慢，考虑缩小日期范围或增加筛选条件
- 如果库存显示异常，检查库存数据的准确性

## 总结

本次MRP功能增强显著提升了系统的实用性和灵活性：

1. **功能完整性**：支持按订单版本和成品筛选的精确MRP计算
2. **用户体验**：界面更友好，操作更直观
3. **技术架构**：代码结构清晰，易于维护和扩展
4. **业务价值**：更好地满足实际制造管理的需求

这些增强功能使MRP系统能够更精确地支持生产计划、采购计划和库存管理，为制造企业提供更有价值的决策支持。
