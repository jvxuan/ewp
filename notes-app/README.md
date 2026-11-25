# 记事 APP（可运行原型）

一个带服务端持久化的轻量记事应用原型：网页界面 + 后端 API + SQLite 数据库，
零第三方依赖，Python 标准库即可运行。

## 功能清单

- **笔记增删改查**：新建、编辑、删除、查看笔记，正文为富文本
- **分类 / 标签 / 搜索**：侧边栏分类筛选、标签云筛选、标题与正文关键词搜索
- **待办事项**：每条笔记下可添加待办条目，勾选完成、双击编辑、删除，可带提醒时间
- **提醒**：笔记级提醒时间；到点后页面内 toast 提醒，已授权时弹浏览器通知
- **富文本编辑**：加粗 / 斜体 / 下划线 / 有序无序列表 / 撤销重做 / 插入图片
- **图片上传**：图片以 base64 上传后落盘到 `uploads/`，正文内引用
- **导出**：单条笔记导出 Markdown（.md）或纯文本（.txt）
- **服务端持久化**：数据存 SQLite，页面操作实时写回服务端，定时自动同步刷新

## 技术栈

- 后端：Python 3 标准库（`http.server` + `sqlite3`），无需 pip 安装任何包
- 前端：原生 HTML / CSS / JavaScript，无框架、无构建步骤
- 数据库：SQLite（`data/notes.db`，首次运行自动创建）

## 目录结构

```
notes-app/
├── server.py            # 后端服务：REST API + 静态托管
├── data/
│   └── notes.db         # SQLite 数据库（运行时自动生成）
├── uploads/             # 上传的图片文件
├── static/
│   ├── index.html       # 页面入口
│   ├── style.css        # 样式
│   └── app.js           # 前端逻辑
└── README.md
```

## 启动方式

```bash
cd notes-app
python3 server.py
```

启动后浏览器打开：<http://127.0.0.1:8000>

如需更换端口：

```bash
PORT=9000 python3 server.py
```

局域网内其他设备访问时，把地址换成本机 IP（如 `http://192.168.x.x:8000`），
同一服务端下的所有访问共享同一份数据。

## API 一览

| 方法   | 路径                          | 说明                     |
|--------|-------------------------------|--------------------------|
| GET    | `/api/notes`                  | 笔记列表，支持 `q`/`category`/`tag` 查询参数 |
| GET    | `/api/notes/<id>`             | 单条笔记详情             |
| POST   | `/api/notes`                  | 新建笔记                 |
| PUT    | `/api/notes/<id>`             | 更新笔记                 |
| DELETE | `/api/notes/<id>`             | 删除笔记                 |
| GET    | `/api/meta`                   | 全部分类与标签汇总       |
| POST   | `/api/images`                 | 上传图片（body: `data_url`） |
| GET    | `/api/notes/<id>/export`       | 导出，`format=md` 或 `txt` |

笔记字段：`title`、`content`(HTML)、`category`、`tags`(数组)、
`todos`(`[{id,text,done,reminder}]`)、`reminder_at`、`created_at`、`updated_at`。

## 关于“云端同步”的说明

当前原型的持久化落在本机 SQLite：只要多个浏览器 / 设备访问同一个后端服务，
看到的就是同一份数据，具备基础的服务端集中存储能力。

若要做成真正的多账号跨产品云端同步，后续可扩展：

- 用户注册 / 登录（账号体系 + 密码哈希 + Token 会话）
- 笔记按用户隔离，数据库迁移到 PostgreSQL / MySQL
- 后端部署到公网服务器，配置 HTTPS 与域名
- 离线草稿缓存、冲突合并、回收站、笔记历史版本

## 可继续迭代的方向

- 待办提醒的本地通知 / 邮件推送
- Markdown 实时预览、夜间模式、笔记列表排序
- 全文检索优化、附件管理、笔记分享链接
- 打包为桌面应用（Electron）或手机 Web App（PWA）
