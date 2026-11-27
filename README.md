# PEW — 极简记事 / 待办 App

PEW 取自底部导航英文首字母：**P**ay（支付）/ **E**xecute（执行）/ **W**ork（工作）。
一个移动端优先的纯前端单文件记事应用，原生 HTML / CSS / JavaScript，无框架、无构建步骤、无常驻后端。

## 特性

- **三表独立**：执行（便签）、工作（工作表）、支付（待办）三套数据互不串扰，各自带独立分类体系。
- **分类与总览**：侧栏分类筛选；总览按分类分组、每类只取首条，单分类下展示全部记录并高亮第一条。
- **简 / 繁 / 英三语**：内置简体中文、繁体中文、英文切换，静态文案随语言回填。
- **本地存储 + 备份**：数据存浏览器 `localStorage`；设置页支持导出 / 导入 JSON 备份（纯前端，无自动云同步）。
- **极简中性 UI**：黑白灰配色，卡片式列表；导航图标为线性描边（未选中）+ 黑色实心主体配白色镂空细节（选中，微信式）双态切换。
- **单文件自包含**：CSS / JS 全部内联在一个 HTML 文件内，到手即用。

## 快速开始

直接用浏览器打开 `notes-app/index.html`，或起一个静态服务：

```bash
cd notes-app
python3 -m http.server 8011
# 浏览器访问 http://127.0.0.1:8011/index.html
```

## 下载 Android APK

调试签名包（minSdk 21 / targetSdk 34，应用名 PEW v2.61）：

- [Release 页面](https://github.com/jvxuan/ewp/releases/tag/v2.61)
- [直接下载 PEW-debug-v2.60.apk](https://github.com/jvxuan/ewp/releases/download/v2.61/PEW-debug-v2.61.apk)

> 离线壳 WebView 直接加载打进 APK 的 `assets/index.html`，无平台浮窗、断网可用；调试签名安装时可能需允许「未知来源」。

## 赞助支持

感谢你使用 PEW，若觉得有帮助，欢迎请作者喝杯咖啡 ☕。

| 微信 | 支付宝 |
| --- | --- |
| <img src="docs/sponsor/wechat-qr.png" width="160" alt="微信收款码" /> | <img src="docs/sponsor/alipay-qr.png" width="160" alt="支付宝收款码" /> |

**国际渠道**（海外或不便扫码时可用，点击直达）：

| 通道 | 链接 |
| --- | --- |
| PayPal | [paypal.me/jvxuan](https://paypal.me/jvxuan) |
| Ko-fi | [ko-fi.com/jvxuan](https://ko-fi.com/jvxuan) |

> 加密钱包通道暂未开放，App 内「国际」标签页会按配置自动显示可用的渠道。

## 目录结构

```
.
├── notes-app/
│   ├── index.html          # 线上主产品：纯前端单文件（入口，所有样式与逻辑内联）
│   ├── server.py             # 早期全栈原型（Python http.server + SQLite，参考保留，未上线）
│   ├── static/               # 原型前端静态文件
│   ├── data/                 # 原型 SQLite 数据库（运行时生成，已 gitignore）
│   └── README.md             # 早期原型说明
├── docs/sponsor/             # README 赞助展示用收款码图片
└── apk-shell/                # Android 离线壳工程（MainActivity 加载 assets/index.html）
```

## 技术说明

- 纯前端 `modern_html` 产物，数据仅保存在当前浏览器本地；更换设备或清理缓存不会自动迁移，需通过设置页导出备份再导入。
- 早期 `server.py` 全栈原型仅作历史参考，与线上单文件版的数据结构、界面逻辑不一致。
- `apk-shell/` 为离线壳工程，构建时把 `notes-app/index.html` 复制进 `assets/` 一并打进 APK；构建产物、签名密钥与 `.apk` 包均已排除出版本库。

## 版本

版本号集中在 `index.html` 内的 `APP_VERSION` 常量，关于页由 `APP_NAME` / `APP_VERSION` 渲染。
