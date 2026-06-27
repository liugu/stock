# 智能选股系统 Web 界面

Vue3 + Element Plus + ECharts + FastAPI

## 项目结构

```
web/
├── src/                    # 前端源码
│   ├── api/               # API接口
│   ├── assets/            # 静态资源
│   ├── components/        # 公共组件
│   ├── router/            # 路由配置
│   ├── stores/            # Pinia状态管理
│   ├── types/             # TypeScript类型
│   ├── views/             # 页面组件
│   ├── App.vue            # 根组件
│   └── main.ts            # 入口文件
├── server/                 # 后端服务
│   ├── api.py             # FastAPI服务
│   └── requirements.txt   # Python依赖
├── index.html             # HTML入口
├── package.json           # 前端依赖
├── vite.config.ts         # Vite配置
└── tsconfig.json          # TypeScript配置
```

## 启动方式

### 方式一：使用启动脚本

1. **启动后端**
   双击 `server/启动后端.bat`

2. **启动前端**
   双击 `启动前端.bat`

### 方式二：命令行启动

```bash
# 启动后端
cd server
python api.py

# 启动前端（新终端）
npm run dev
```

## 访问地址

- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 功能模块

### 1. 首页概览
- 市场涨跌统计
- 快捷选股策略
- 今日热门股票
- 涨跌幅分布图

### 2. 股票列表
- 全部股票浏览
- 搜索筛选
- 行业分类

### 3. 策略选股
- 均线金叉
- 放量突破
- MACD金叉
- RSI超跌
- 涨停板
- 高换手率
- 导出结果

### 4. 数据分析
- K线图
- 技术指标（MACD、RSI）
- 统计数据

### 5. 回测中心
- 策略回测
- 收益分析
- 交易记录

## 技术栈

**前端**
- Vue 3.5
- TypeScript
- Vue Router 4
- Pinia 2
- Element Plus
- ECharts 5
- Axios

**后端**
- FastAPI
- PyMySQL
- Pydantic
- Uvicorn

## 依赖安装

```bash
# 前端
npm install

# 后端
pip install fastapi uvicorn pymysql pydantic
```

## 构建生产版本

```bash
npm run build
```

构建后的文件在 `dist/` 目录。