-- MES/MRP 系统数据库表结构
-- 支持外键约束和唯一索引

-- 物料主数据表
CREATE TABLE IF NOT EXISTS Items (
    ItemId INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemCode TEXT UNIQUE NOT NULL,           -- 物资编码
    CnName TEXT NOT NULL,                   -- 物资名称
    ItemSpec TEXT,                          -- 物资规格
    ItemType TEXT NOT NULL,                 -- 物资类型
    Unit TEXT NOT NULL DEFAULT '个',        -- 单位
    Quantity REAL NOT NULL DEFAULT 1.0,     -- 组成数量
    SafetyStock REAL NOT NULL DEFAULT 0,    -- 安全库存
    Remark TEXT,                            -- 备注
    Brand TEXT,                            -- 商品品牌
    ParentItemId INTEGER,                   -- 归属物资ID（上级物资）
    IsActive BOOLEAN NOT NULL DEFAULT 1,    -- 是否启用
    CreatedDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ParentItemId) REFERENCES Items(ItemId)
);

-- 供应商信息表
CREATE TABLE IF NOT EXISTS Suppliers (
    SupplierId INTEGER PRIMARY KEY AUTOINCREMENT,
    SupplierCode TEXT UNIQUE NOT NULL,
    SupplierName TEXT NOT NULL,
    ContactPerson TEXT,
    Phone TEXT,
    Email TEXT,
    Address TEXT,
    TaxNo TEXT,  -- 税号
    BankAccount TEXT,  -- 银行账户
    PaymentTerms TEXT,  -- 付款条件
    CreditLimit REAL,  -- 信用额度
    IsActive BOOLEAN DEFAULT 1,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 物料供应商关系表
CREATE TABLE IF NOT EXISTS ItemSuppliers (
    ItemSupplierId INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemId INTEGER NOT NULL,
    SupplierId INTEGER NOT NULL,
    Priority INTEGER DEFAULT 1,  -- 优先级
    UnitPrice REAL,  -- 单价
    Currency TEXT DEFAULT 'CNY',  -- 币种
    MinOrderQty REAL,  -- 最小订购量
    LeadTimeDays INTEGER,  -- 供应商提前期
    IsPreferred BOOLEAN DEFAULT 0,  -- 是否首选供应商
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ItemId) REFERENCES Items(ItemId) ON DELETE CASCADE,
    FOREIGN KEY (SupplierId) REFERENCES Suppliers(SupplierId) ON DELETE CASCADE,
    UNIQUE(ItemId, SupplierId)
);

-- 工作中心表
CREATE TABLE IF NOT EXISTS WorkCenters (
    WorkCenterId INTEGER PRIMARY KEY AUTOINCREMENT,
    WorkCenterCode TEXT UNIQUE NOT NULL,
    WorkCenterName TEXT NOT NULL,
    WorkCenterType TEXT,  -- 工作中心类型
    Capacity REAL,  -- 产能(小时/天)
    Efficiency REAL DEFAULT 1.0,  -- 效率系数
    SetupTime REAL DEFAULT 0,  -- 换型时间(小时)
    IsActive BOOLEAN DEFAULT 1,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 工艺路线主表
CREATE TABLE IF NOT EXISTS RoutingHeaders (
    RoutingId INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemId INTEGER NOT NULL,
    RoutingCode TEXT UNIQUE NOT NULL,
    RoutingName TEXT NOT NULL,
    Rev TEXT NOT NULL,
    EffectiveDate DATE NOT NULL,
    ExpireDate DATE,
    IsDefault BOOLEAN DEFAULT 0,  -- 是否默认工艺路线
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ItemId) REFERENCES Items(ItemId) ON DELETE CASCADE,
    UNIQUE(ItemId, Rev)
);

-- 工艺路线明细表
CREATE TABLE IF NOT EXISTS RoutingLines (
    RoutingLineId INTEGER PRIMARY KEY AUTOINCREMENT,
    RoutingId INTEGER NOT NULL,
    OperationNo INTEGER NOT NULL,  -- 工序号
    OperationName TEXT NOT NULL,  -- 工序名称
    WorkCenterId INTEGER NOT NULL,
    SetupTime REAL DEFAULT 0,  -- 换型时间(小时)
    ProcessTime REAL NOT NULL,  -- 加工时间(小时/件)
    MoveTime REAL DEFAULT 0,  -- 移动时间(小时)
    QueueTime REAL DEFAULT 0,  -- 排队时间(小时)
    WaitTime REAL DEFAULT 0,  -- 等待时间(小时)
    YieldRate REAL DEFAULT 1.0,  -- 合格率
    IsCritical BOOLEAN DEFAULT 0,  -- 是否关键工序
    Remark TEXT,  -- 备注
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (RoutingId) REFERENCES RoutingHeaders(RoutingId) ON DELETE CASCADE,
    FOREIGN KEY (WorkCenterId) REFERENCES WorkCenters(WorkCenterId) ON DELETE CASCADE,
    UNIQUE(RoutingId, OperationNo)
);

-- BOM 主表
CREATE TABLE IF NOT EXISTS BomHeaders (
    BomId INTEGER PRIMARY KEY AUTOINCREMENT,
    BomName TEXT NOT NULL,  -- BOM名称
    ParentItemId INTEGER,   -- 父物料ID（可选）
    Rev TEXT NOT NULL,
    EffectiveDate DATE NOT NULL,
    ExpireDate DATE,
    BomType TEXT DEFAULT 'Production',  -- BOM类型：Production/Engineering/Spare
    IsActive BOOLEAN DEFAULT 1,
    Remark TEXT,  -- 备注
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ParentItemId) REFERENCES Items(ItemId) ON DELETE CASCADE,
    UNIQUE(BomName, Rev)  -- BOM名称和版本的组合必须唯一
);

-- BOM 明细表
CREATE TABLE IF NOT EXISTS BomLines (
    LineId INTEGER PRIMARY KEY AUTOINCREMENT,
    BomId INTEGER NOT NULL,
    ChildItemId INTEGER NOT NULL,
    Position TEXT,  -- 位置标识
    QtyPer REAL NOT NULL,
    ScrapFactor REAL DEFAULT 0,
    Unit TEXT,  -- 单位
    IsPhantom BOOLEAN DEFAULT 0,  -- 是否虚拟件
    IsCoProduct BOOLEAN DEFAULT 0,  -- 是否联产品
    IsByProduct BOOLEAN DEFAULT 0,  -- 是否副产品
    Remark TEXT,  -- 备注
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (BomId) REFERENCES BomHeaders(BomId) ON DELETE CASCADE,
    FOREIGN KEY (ChildItemId) REFERENCES Items(ItemId) ON DELETE CASCADE,
    UNIQUE(BomId, ChildItemId)
);

-- 客户信息表
CREATE TABLE IF NOT EXISTS Customers (
    CustomerId INTEGER PRIMARY KEY AUTOINCREMENT,
    CustomerCode TEXT UNIQUE NOT NULL,
    CustomerName TEXT NOT NULL,
    ContactPerson TEXT,
    Phone TEXT,
    Email TEXT,
    Address TEXT,
    TaxNo TEXT,
    CreditLimit REAL,
    PaymentTerms TEXT,
    IsActive BOOLEAN DEFAULT 1,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 客户订单主表
CREATE TABLE IF NOT EXISTS SalesOrders (
    OrderId INTEGER PRIMARY KEY AUTOINCREMENT,
    CustomerId INTEGER NOT NULL,
    OrderNo TEXT UNIQUE NOT NULL,
    Project TEXT,
    OrderType TEXT DEFAULT 'Standard',  -- 订单类型：Standard/Urgent/Stock
    Priority INTEGER DEFAULT 5,  -- 优先级(1-10)
    StartDate DATE NOT NULL,
    DueDate DATE NOT NULL,
    Weeks INTEGER NOT NULL,
    QtyPerWeek REAL NOT NULL,
    TotalQty REAL NOT NULL,
    UnitPrice REAL,
    Currency TEXT DEFAULT 'CNY',
    DemandType TEXT CHECK(DemandType IN ('F', 'P')) NOT NULL,  -- F:固定 P:预测
    Status TEXT DEFAULT 'Active',  -- Active/Completed/Cancelled
    Remark TEXT,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerId) REFERENCES Customers(CustomerId) ON DELETE CASCADE
);

-- 客户订单明细表（展开后的日/周需求）
CREATE TABLE IF NOT EXISTS SalesOrderLines (
    LineId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrderId INTEGER NOT NULL,
    ItemId INTEGER NOT NULL,
    DeliveryDate DATE NOT NULL,
    Qty REAL NOT NULL,
    DemandType TEXT CHECK(DemandType IN ('F', 'P')) NOT NULL,
    Project TEXT,
    Priority INTEGER DEFAULT 5,
    Status TEXT DEFAULT 'Open',  -- Open/Planned/InProduction/Completed
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (OrderId) REFERENCES SalesOrders(OrderId) ON DELETE CASCADE,
    FOREIGN KEY (ItemId) REFERENCES Items(ItemId) ON DELETE CASCADE,
    UNIQUE(OrderId, ItemId, DeliveryDate)
);

-- 库存流水账
CREATE TABLE IF NOT EXISTS InventoryTx (
    TxId INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemId INTEGER NOT NULL,
    TxDate DATE NOT NULL,
    TxType TEXT CHECK(TxType IN ('IN', 'OUT', 'ADJ', 'TRANSFER')) NOT NULL,
    Qty REAL NOT NULL,
    UnitCost REAL,  -- 单位成本
    TotalCost REAL,  -- 总成本
    Warehouse TEXT,  -- 仓库
    Location TEXT,  -- 库位
    BatchNo TEXT,  -- 批次号
    RefType TEXT,  -- 关联类型
    RefId INTEGER,  -- 关联ID
    Remark TEXT,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ItemId) REFERENCES Items(ItemId) ON DELETE CASCADE
);

-- 库存余额表
CREATE TABLE IF NOT EXISTS InventoryBalance (
    BalanceId INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemId INTEGER NOT NULL,
    Warehouse TEXT NOT NULL,
    Location TEXT,
    BatchNo TEXT,
    QtyOnHand REAL DEFAULT 0,  -- 在手数量
    QtyReserved REAL DEFAULT 0,  -- 预留数量
    QtyInTransit REAL DEFAULT 0,  -- 在途数量
    QtyOnOrder REAL DEFAULT 0,  -- 在订数量
    UnitCost REAL,  -- 单位成本
    LastUpdated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ItemId) REFERENCES Items(ItemId) ON DELETE CASCADE,
    UNIQUE(ItemId, Warehouse, Location, BatchNo)
);

-- MRP 计划事件表
CREATE TABLE IF NOT EXISTS PlannedEvents (
    PlannedId INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemId INTEGER NOT NULL,
    EventDate DATE NOT NULL,
    EventType TEXT CHECK(EventType IN ('PlanReceipt', 'PlanRelease', 'PlanOrder')) NOT NULL,
    Qty REAL NOT NULL,
    Source TEXT,  -- 来源
    RefType TEXT,  -- 关联类型
    RefId INTEGER,  -- 关联ID
    Priority INTEGER DEFAULT 5,
    Status TEXT DEFAULT 'Planned',  -- Planned/Released/Completed/Cancelled
    Remark TEXT,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ItemId) REFERENCES Items(ItemId) ON DELETE CASCADE
);

-- 排产计划表
CREATE TABLE IF NOT EXISTS SchedulePlans (
    PlanId INTEGER PRIMARY KEY AUTOINCREMENT,
    ItemId INTEGER NOT NULL,
    WorkCenterId INTEGER NOT NULL,
    StartDate DATE NOT NULL,
    EndDate DATE NOT NULL,
    Qty REAL NOT NULL,
    SetupTime REAL DEFAULT 0,
    ProcessTime REAL NOT NULL,
    Priority INTEGER DEFAULT 5,
    Status TEXT DEFAULT 'Scheduled',  -- Scheduled/InProgress/Completed/Cancelled
    Remark TEXT,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ItemId) REFERENCES Items(ItemId) ON DELETE CASCADE,
    FOREIGN KEY (WorkCenterId) REFERENCES WorkCenters(WorkCenterId) ON DELETE CASCADE
);

-- 生产订单表
CREATE TABLE IF NOT EXISTS ProductionOrders (
    OrderId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrderNo TEXT UNIQUE NOT NULL,
    ItemId INTEGER NOT NULL,
    RoutingId INTEGER,
    BomId INTEGER,
    OrderQty REAL NOT NULL,
    CompletedQty REAL DEFAULT 0,
    ScrappedQty REAL DEFAULT 0,
    StartDate DATE,
    DueDate DATE,
    Priority INTEGER DEFAULT 5,
    Status TEXT DEFAULT 'Planned',  -- Planned/Released/InProgress/Completed/Cancelled
    Remark TEXT,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ItemId) REFERENCES Items(ItemId) ON DELETE CASCADE,
    FOREIGN KEY (RoutingId) REFERENCES RoutingHeaders(RoutingId) ON DELETE SET NULL,
    FOREIGN KEY (BomId) REFERENCES BomHeaders(BomId) ON DELETE SET NULL
);

-- 生产订单工序表
CREATE TABLE IF NOT EXISTS ProductionOrderOperations (
    OperationId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrderId INTEGER NOT NULL,
    OperationNo INTEGER NOT NULL,
    WorkCenterId INTEGER NOT NULL,
    PlannedStartDate DATE,
    PlannedEndDate DATE,
    ActualStartDate DATE,
    ActualEndDate DATE,
    PlannedQty REAL NOT NULL,
    CompletedQty REAL DEFAULT 0,
    ScrappedQty REAL DEFAULT 0,
    SetupTime REAL DEFAULT 0,
    ProcessTime REAL DEFAULT 0,
    Status TEXT DEFAULT 'Planned',  -- Planned/InProgress/Completed
    Remark TEXT,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (OrderId) REFERENCES ProductionOrders(OrderId) ON DELETE CASCADE,
    FOREIGN KEY (WorkCenterId) REFERENCES WorkCenters(WorkCenterId) ON DELETE CASCADE,
    UNIQUE(OrderId, OperationNo)
);

-- 客户订单主表
CREATE TABLE IF NOT EXISTS CustomerOrders (
    OrderId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrderNumber TEXT NOT NULL,                 -- 订单号，如CW33_2024
    ImportId INTEGER,                          -- 导入版本ID
    CalendarWeek TEXT NOT NULL,                -- 日历周，如CW33
    OrderYear INTEGER NOT NULL,                -- 订单年份
    SupplierCode TEXT,                         -- 供应商代码
    SupplierName TEXT,                         -- 供应商名称
    CustomerCode TEXT,                         -- 客户代码
    CustomerName TEXT,                         -- 客户名称
    ReleaseDate TEXT,                          -- 发布日期
    ReleaseId TEXT,                            -- 发布ID
    Buyer TEXT,                                -- 采购员
    ShipToAddress TEXT,                        -- 收货地址
    ReceiptQuantity REAL DEFAULT 0,            -- 收货数量
    CumReceived REAL DEFAULT 0,                -- 累计收货数量
    Project TEXT,                              -- 项目名称
    OrderStatus TEXT DEFAULT 'Active',         -- 订单状态
    CreatedDate TEXT DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TEXT DEFAULT CURRENT_TIMESTAMP,
    Remark TEXT,
    FOREIGN KEY (ImportId) REFERENCES OrderImportHistory(ImportId),
    UNIQUE(ImportId, CalendarWeek, OrderYear)  -- 唯一索引：导入版本ID + CW几和年份
);

-- 客户订单明细表
CREATE TABLE IF NOT EXISTS CustomerOrderLines (
    LineId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrderId INTEGER NOT NULL,                  -- 关联订单ID
    ImportId INTEGER,                          -- 导入版本ID
    ItemNumber TEXT NOT NULL,                  -- 产品型号，如R001H368E
    ItemDescription TEXT,                      -- 产品描述
    UnitOfMeasure TEXT DEFAULT 'EA',          -- 单位
    DeliveryDate TEXT NOT NULL,               -- 交货日期
    CalendarWeek TEXT,                         -- 日历周，如CW33
    OrderType TEXT NOT NULL,                  -- 订单类型：F(正式订单)/P(预测订单)
    RequiredQty REAL NOT NULL,                -- 需求数量
    CumulativeQty REAL,                       -- 累计需求数量
    NetRequiredQty REAL,                      -- 净需求数量
    InTransitQty REAL DEFAULT 0,              -- 在途数量
    ReceivedQty REAL DEFAULT 0,               -- 已收货数量
    LineStatus TEXT DEFAULT 'Active',          -- 行状态
    CreatedDate TEXT DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate TEXT DEFAULT CURRENT_TIMESTAMP,
    Remark TEXT,
    FOREIGN KEY (OrderId) REFERENCES CustomerOrders(OrderId),
    FOREIGN KEY (ImportId) REFERENCES OrderImportHistory(ImportId),
    UNIQUE(OrderId, ItemNumber, DeliveryDate)
);

-- 订单导入历史表
CREATE TABLE IF NOT EXISTS OrderImportHistory (
    ImportId INTEGER PRIMARY KEY AUTOINCREMENT,
    FileName TEXT NOT NULL,                    -- 导入文件名
    ImportDate TEXT DEFAULT CURRENT_TIMESTAMP, -- 导入日期
    OrderCount INTEGER DEFAULT 0,              -- 导入订单数量
    LineCount INTEGER DEFAULT 0,               -- 导入明细数量
    ImportStatus TEXT DEFAULT 'Success',       -- 导入状态
    ErrorMessage TEXT,                         -- 错误信息
    ImportedBy TEXT                            -- 导入用户
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_items_itemcode ON Items(ItemCode);
CREATE INDEX IF NOT EXISTS idx_items_itemtype ON Items(ItemType);
CREATE INDEX IF NOT EXISTS idx_suppliers_code ON Suppliers(SupplierCode);
CREATE INDEX IF NOT EXISTS idx_workcenters_code ON WorkCenters(WorkCenterCode);
CREATE INDEX IF NOT EXISTS idx_routing_headers_item ON RoutingHeaders(ItemId);
CREATE INDEX IF NOT EXISTS idx_routing_lines_routing ON RoutingLines(RoutingId);
CREATE INDEX IF NOT EXISTS idx_bomheaders_parentitem ON BomHeaders(ParentItemId);
CREATE INDEX IF NOT EXISTS idx_bomlines_bomid ON BomLines(BomId);
CREATE INDEX IF NOT EXISTS idx_bomlines_childitem ON BomLines(ChildItemId);
CREATE INDEX IF NOT EXISTS idx_customers_code ON Customers(CustomerCode);
CREATE INDEX IF NOT EXISTS idx_salesorders_customer ON SalesOrders(CustomerId);
CREATE INDEX IF NOT EXISTS idx_salesorders_startdate ON SalesOrders(StartDate);
CREATE INDEX IF NOT EXISTS idx_salesorderlines_itemdate ON SalesOrderLines(ItemId, DeliveryDate);
CREATE INDEX IF NOT EXISTS idx_inventorytx_itemdate ON InventoryTx(ItemId, TxDate);
CREATE INDEX IF NOT EXISTS idx_inventorybalance_itemwarehouse ON InventoryBalance(ItemId, Warehouse);
CREATE INDEX IF NOT EXISTS idx_plannedevents_itemdate ON PlannedEvents(ItemId, EventDate);
CREATE INDEX IF NOT EXISTS idx_scheduleplans_itemdate ON SchedulePlans(ItemId, StartDate);
CREATE INDEX IF NOT EXISTS idx_productionorders_item ON ProductionOrders(ItemId);
CREATE INDEX IF NOT EXISTS idx_productionorders_status ON ProductionOrders(Status);
CREATE INDEX IF NOT EXISTS idx_customer_orders_cw_year ON CustomerOrders(CalendarWeek, OrderYear);
CREATE INDEX IF NOT EXISTS idx_customer_orders_number ON CustomerOrders(OrderNumber);
CREATE INDEX IF NOT EXISTS idx_customer_order_lines_order ON CustomerOrderLines(OrderId);
CREATE INDEX IF NOT EXISTS idx_customer_order_lines_item ON CustomerOrderLines(ItemNumber);
CREATE INDEX IF NOT EXISTS idx_customer_order_lines_date ON CustomerOrderLines(DeliveryDate);
CREATE INDEX IF NOT EXISTS idx_customer_order_lines_cw ON CustomerOrderLines(CalendarWeek);

-- 创建触发器更新时间戳
CREATE TRIGGER IF NOT EXISTS update_items_timestamp 
    AFTER UPDATE ON Items
    FOR EACH ROW
BEGIN
    UPDATE Items SET UpdatedDate = CURRENT_TIMESTAMP WHERE ItemId = NEW.ItemId;
END;

CREATE TRIGGER IF NOT EXISTS update_suppliers_timestamp 
    AFTER UPDATE ON Suppliers
    FOR EACH ROW
BEGIN
    UPDATE Suppliers SET UpdatedDate = CURRENT_TIMESTAMP WHERE SupplierId = NEW.SupplierId;
END;

CREATE TRIGGER IF NOT EXISTS update_workcenters_timestamp 
    AFTER UPDATE ON WorkCenters
    FOR EACH ROW
BEGIN
    UPDATE WorkCenters SET UpdatedDate = CURRENT_TIMESTAMP WHERE WorkCenterId = NEW.WorkCenterId;
END;

CREATE TRIGGER IF NOT EXISTS update_routing_headers_timestamp 
    AFTER UPDATE ON RoutingHeaders
    FOR EACH ROW
BEGIN
    UPDATE RoutingHeaders SET UpdatedDate = CURRENT_TIMESTAMP WHERE RoutingId = NEW.RoutingId;
END;

CREATE TRIGGER IF NOT EXISTS update_bom_headers_timestamp 
    AFTER UPDATE ON BomHeaders
    FOR EACH ROW
BEGIN
    UPDATE BomHeaders SET UpdatedDate = CURRENT_TIMESTAMP WHERE BomId = NEW.BomId;
END;

CREATE TRIGGER IF NOT EXISTS update_customers_timestamp 
    AFTER UPDATE ON Customers
    FOR EACH ROW
BEGIN
    UPDATE Customers SET UpdatedDate = CURRENT_TIMESTAMP WHERE CustomerId = NEW.CustomerId;
END;

CREATE TRIGGER IF NOT EXISTS update_salesorders_timestamp 
    AFTER UPDATE ON SalesOrders
    FOR EACH ROW
BEGIN
    UPDATE SalesOrders SET UpdatedDate = CURRENT_TIMESTAMP WHERE OrderId = NEW.OrderId;
END;

CREATE TRIGGER IF NOT EXISTS update_production_orders_timestamp 
    AFTER UPDATE ON ProductionOrders
    FOR EACH ROW
BEGIN
    UPDATE ProductionOrders SET UpdatedDate = CURRENT_TIMESTAMP WHERE OrderId = NEW.OrderId;
END;


-- ============ 仓库主数据/关系表 ============
CREATE TABLE IF NOT EXISTS Warehouses (
  WarehouseId   INTEGER PRIMARY KEY AUTOINCREMENT,
  Code          TEXT NOT NULL UNIQUE,
  Name          TEXT NOT NULL,
  IsActive      INTEGER NOT NULL DEFAULT 1,
  Remark        TEXT,
  CreatedDate   TEXT DEFAULT CURRENT_TIMESTAMP,
  UpdatedDate   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS WarehouseItems (
  Id           INTEGER PRIMARY KEY AUTOINCREMENT,
  WarehouseId  INTEGER NOT NULL,
  ItemId       INTEGER NOT NULL,
  MinQty       REAL DEFAULT 0,
  MaxQty       REAL DEFAULT 0,
  ReorderPoint REAL DEFAULT 0,
  CreatedDate   TEXT DEFAULT CURRENT_TIMESTAMP,
  UpdatedDate   TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (WarehouseId, ItemId),
  FOREIGN KEY (WarehouseId) REFERENCES Warehouses(WarehouseId),
  FOREIGN KEY (ItemId) REFERENCES Items(ItemId)
);

-- 迁移历史仓库字符串到主数据
INSERT OR IGNORE INTO Warehouses(Code, Name)
SELECT w, w FROM (
  SELECT DISTINCT Warehouse AS w FROM InventoryBalance WHERE IFNULL(Warehouse,'')<>''
  UNION
  SELECT DISTINCT Warehouse AS w FROM InventoryTx      WHERE IFNULL(Warehouse,'')<>''
);

-- 没有任何仓库时，建一个默认仓库
INSERT OR IGNORE INTO Warehouses(Code, Name)
SELECT '默认仓库','默认仓库'
WHERE NOT EXISTS(SELECT 1 FROM Warehouses);


