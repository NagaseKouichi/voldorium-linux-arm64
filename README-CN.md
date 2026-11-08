# Voldorium — Linux ARM64

[English](README.md) · [构建说明](docs/BUILD-ARM64.md) · [上游原始 README](docs/README.upstream.md)

基于 [enrique363/voldorium](https://github.com/enrique363/voldorium) 的 Dreamcast《灵魂能力》Linux AArch64 静态重编译移植。支持 **USA，T-1401N，V1.000**。SH-4 指令翻译为 C 后编译成原生 ARM64 模块，不通过 x86 模拟器运行游戏。

## 当前状态

- 已用固定版本 Zig 0.14.1 构建 ARM64 主程序与私人 `sc_game.so`。
- 保留 x86 SSE 浮点控制，加入 ARM64 FPCR/FPSR 控制及独立语义测试。
- 构建主机与目标架构分离，支持目标 SDL/OpenGL sysroot、受限并行及防止混用不同架构缓存。
- 已在 QEMU 下运行 AArch64 游戏、执行协程切换，并通过 Mesa llvmpipe 实际绘图及读回截图。**这不是掌机原生性能、真实 GPU、声音或实体手柄验收。**
- 需要桌面 **OpenGL 3.3 Core**；不是 GLES 或 Android 版本。
- 用户已反馈游戏可在 Armada 掌机运行；声音、实体手柄、帧时间与温度尚未独立验收。
- 详细证据与剩余验收项见 [VALIDATION-ARM64.md](docs/VALIDATION-ARM64.md)。尚未认证跨架构联机确定性。

## 游戏镜像与私人数据

公开包不含镜像、提取文件、翻译生成的 C、游戏派生模块、BIOS 字体或个人存档。请用自己合法持有的受支持镜像生成 `sc_game.so`，并与兼容版本的运行时配套使用。

`tools/cue_to_gdi.py` 可把指定三轨 Redump CUE+BIN 布局转换为 GDI 描述及相对符号链接，不复制或修改原 BIN。仅复制 GDI 不等于迁移镜像；移动后须保持链接及源文件有效。

## 构建与运行

完整的 x86 主机 Docker 交叉构建及 ARM64 本地模块生成命令见 [构建文档](docs/BUILD-ARM64.md)。ARM64 主机下载 ARM64 Zig，x86 交叉构建主机下载 x86 Zig，二者均可生成 AArch64 模块。

运行依赖目标系统的 SDL2、libGL、glibc 及图形/音频驱动。编译目标为 glibc 2.28，但目标系统的 SDL/Mesa 可能要求更新版本。没有捆绑 x86 库、替换系统 libc 或写死 CPU 核号；大小核默认交给系统调度。

包结构：
- **build/setup ZIP**：ARM64 主程序、首次启动模块构建器及对应源码。
- **runtime ZIP**：仅运行时，需自行提供私人构建的兼容模块。

两个包都不含游戏派生数据。若解压软件丢失执行权限，执行 `chmod +x voldorium builder/first_run.sh`（运行包无 builder 时省略第二个路径）。

## 致谢与许可

保留上游项目作者 enrique363、原始翻译器和运行时的贡献说明，见上游 README。上游第一方代码限合法持有游戏者**个人、非商业使用**，本移植不另行改授许可证；GGPO、SDL、Zig、Flycast 继续适用各自许可。分发前须阅读上游许可说明。
