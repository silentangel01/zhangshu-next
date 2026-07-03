# macOS Apple Silicon 打包说明

本文档说明如何在 macOS M 系列机器上构建章枢桌面版安装包。业务代码仍与 Windows 共用，macOS 只新增独立自动化打包流水线。

## 输出产物

默认目标架构为 Apple Silicon：

```bash
scripts/package_macos.sh
```

成功后会生成：

```text
frontend/src-tauri/target/aarch64-apple-darwin/release/bundle/macos/*.app
release/macos-aarch64-apple-darwin/Zhangshu_<version>_macos_arm64.dmg
```

## 环境要求

- macOS Apple Silicon
- Xcode Command Line Tools
- Node.js，满足 `frontend/package.json` 的 engines
- Rust stable
- Python 3，建议 3.12
- npm 依赖已安装，或允许脚本自行安装后端 Python 依赖

首次准备：

```bash
xcode-select --install
rustup target add aarch64-apple-darwin
cd frontend
npm ci
cd ..
```

## 一键构建

在仓库根目录运行：

```bash
scripts/package_macos.sh
```

也可以从前端目录运行：

```bash
cd frontend
npm run tauri:build:macos
```

脚本会执行：

1. 校验 `package.json`、`Cargo.toml`、`tauri.conf.json` 版本一致。
2. 创建或复用 `backend/.venv`。
3. 安装后端依赖和 PyInstaller。
4. 构建 Vue 前端。
5. 使用 PyInstaller 构建 macOS arm64 后端 sidecar。
6. 运行后端 sidecar 冒烟测试。
7. 构建 Tauri `.app`。
8. 将 `zhangshu-backend` 和 `frontend-dist` 安装到 `.app/Contents/Resources/`。
9. 默认执行 ad-hoc codesign。
10. 使用 `hdiutil` 生成 `.dmg`。

## 常用参数

```bash
scripts/package_macos.sh --skip-deps
scripts/package_macos.sh --skip-smoke
scripts/package_macos.sh --skip-sign
scripts/package_macos.sh --skip-dmg
scripts/package_macos.sh --target aarch64-apple-darwin
scripts/package_macos.sh --codesign "Developer ID Application: Your Name (TEAMID)"
```

环境变量也可以覆盖默认值：

```bash
ZHANGSHU_MACOS_TARGET=aarch64-apple-darwin scripts/package_macos.sh
ZHANGSHU_MACOS_CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" scripts/package_macos.sh
```

## 单独冒烟后端

如果只想验证 PyInstaller 后端：

```bash
scripts/smoke_packaged_backend_macos.sh
```

或指定后端路径：

```bash
scripts/smoke_packaged_backend_macos.sh \
  --backend-exe frontend/src-tauri/binaries/macos-aarch64-apple-darwin/zhangshu-backend/zhangshu-backend
```

## 签名与公证

默认脚本使用 ad-hoc 签名，适合本机测试和内部验证。对外分发时需要：

1. 使用 Developer ID Application 证书签名。
2. 对 `.dmg` 或 `.app` 执行 Apple notarization。
3. stapler 固定公证票据。

公证需要 Apple 开发者账号和专用密码，当前脚本暂不自动执行公证流程。

## 已知边界

- macOS 产物必须在 macOS 上构建，不能复用 Windows PyInstaller 产物。
- 当前自动更新通道仍是 Windows-first；macOS 首版建议先手动分发 `.dmg`。
- 如果首次运行被 Gatekeeper 拦截，内部测试可右键打开，或移除下载隔离属性：

```bash
xattr -dr com.apple.quarantine /Applications/章枢.app
```
