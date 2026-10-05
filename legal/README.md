# 发行许可与源码

Organize 是基于 [Thomas Feldmann 的 organize](https://github.com/tfeldmann/organize)
开发的独立桌面衍生项目，不是上游的官方桌面发行版。
上游代码继续适用根目录 `LICENSE.txt` 的 MIT 许可证；保留原版权声明。
本仓库新增的桌面代码、文档和原创矢量图标也按 MIT 分发。第三方组件仍适用各自许可证，
不能用本项目的 MIT 声明替代它们。许可证不授予第三方商标权。

## 安装包内的文件

macOS：右键应用 → 显示包内容 → `Contents/Resources/legal/`。
应用内也可通过「关于与诊断 → 开源许可证与源码」查看全文和打开该目录。

- `LICENSE.txt`：上游 MIT 许可及原版权声明。
- `DESKTOP-LICENSE.txt`：新增桌面贡献与原创图标的 MIT 许可，不替换上游声明。
- `THIRD_PARTY_NOTICES.txt`：组件版本、许可全文、版权及 NOTICE 原文。
- `manifest.json`：构建目标、组件来源、许可文件 SHA-256、锁文件及源码归档 SHA-256。
- `MPL-SOURCES.md`、`MPL-SOURCES.zip`：对应版本 MPL 组件的源码，无需联网获取。
- `BRAND.md`：独立项目和品牌说明。
- `Cargo.lock`、`similar-photos-Cargo.lock`、`package-lock.json`、`python-packages.json`：本次构建的依赖依据。
  `similar-photos` 只链接 MIT 的 `czkawka_core`，不包含 GPL-3.0-only 的 krokiet。
  `czkawka_core` 的依赖图包含 MPL-2.0 的 symphonia 音频库。本功能不调用音频工具，
  生成许可包时仍附带这些未修改的对应源码。

## 可重复生成

在安装好 npm / Cargo 依赖和引擎打包环境后执行：

```sh
cd apps/desktop
npm run build:licenses
```

`build:bundle` 会先构建引擎和 similar-photos sidecar，再生成许可材料，最后构建前端。
生成器读取当前 npm 锁文件、桌面和 similar-photos 的 Cargo 依赖图，以及打包 Python 环境中所有已安装的
distribution（保守覆盖运行与构建依赖，不代表每个组件都链接进应用）。
不得把所有构建工具的许可证解释为应用整体的许可证。
Python 标准库的许可证来自本次打包的解释器，而不是任意最新版网页。
cryptography wheel 内嵌的 OpenSSL 单独按实际库版本提供许可。此清单不是所有原生 wheel
内部依赖的完整 SBOM；升级或更换二进制 wheel 时仍须核查其内嵌组件与版权声明。

个别上游包未携带独立许可证文件：从指定提交获取的许可说明缓存于
`legal/upstream/`，来源和哈希在 `legal/upstream.json` 中保存。更换依赖版本后必须重新审核；
发现缺少许可原文或对应 MPL 源码时构建失败，不会静默漏过。

## 发版检查

1. 按实际发行平台重新构建并检查包内 legal 文件；不能直接沿用另一个平台的清单。
2. 保留全部版权和 NOTICE；修改 MPL 文件时，同步提供修改后的对应源码和修改说明。
3. MPL 文件仍按 MPL-2.0 提供；未覆盖的独立代码可保持 MIT。参见
   [MPL 2.0 第 3 节](https://www.mozilla.org/en-US/MPL/2.0/)。
4. 更换图标或素材时核实来源，不把历史设计草图当作可直接商用的授权资产。
5. 确认发行主体、商标检索、开发者签名、公证及下载页说明。当前补充许可材料不代表
   已完成商标清查或法律意见。objc2 上游许可说明也保留了 Apple SDK 衍生绑定的解释风险，
   商业发布前应结合 Xcode 协议确认；不要把补齐文件理解为消除全部法律风险。

PyInstaller 的输出例外允许生成的应用使用自己的许可证，见其随附许可原文。
安装包的最终分发者应保留本目录全部材料；若单独抽出二进制分发，也必须提供这些说明和源码。
