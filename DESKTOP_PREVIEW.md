# dv365-music-downloader Windows 技术预发布版使用说明

版本：0.1.0-preview。此版本用于评估桌面操作与下载稳定性。项目作者与音乐来源的商业授权尚未核实，因此当前交付包不作为销售版本。

## 一键启动

在项目根目录双击 `start.bat` 即可启动，无需手动输入命令。脚本会自动切换到自身所在目录，路径包含空格也可使用。

启动顺序为：项目的 `.venv` 虚拟环境 → 同目录的便携版 EXE → `dist\dv365-music-downloader` 下的 EXE。脚本不会自动安装依赖；首次使用源码请先按下方说明配置环境。启动报错时窗口会保留错误信息，按任意键关闭。

## 启动和使用

1. 解压整个 `dv365-music-downloader-0.1.0-preview-windows-x64.zip`，保留目录结构。
2. 双击 `dv365-music-downloader.exe`。无需安装 Python；不要单独移动 EXE，旁边的 `_internal` 是运行依赖。
3. 输入歌名或歌手，选择音乐源，点击“搜索音乐”。默认选择网易云，其余原有来源保留为实验选项。
4. 选中结果后点击“下载选中歌曲”。按 Ctrl / Shift 多选，“全选”可选择所有结果。
5. 成功文件可在保存目录中找到，也可双击成功记录，用系统默认播放器打开。

查询类型还支持网易云单曲链接，以及网易云、酷狗歌单链接。第三方接口随时可能变化；搜索成功不代表提供下载权限。来源拒绝、付费权限不足或返回空链接时，程序显示失败，不绕过平台的访问限制。

## 下载状态

下载在后台进行，界面可响应。失败原因显示在底部提示和“下载记录”中。选中失败项再点击下载即可重试；不会自动无限重试。

“取消任务”在当前网络请求返回或超时后生效。下载中断、取消或内容不完整时，临时文件会被清理，不会把它当作成功文件。已完成文件保留；同名音频保存为带序号的新文件。歌词和封面为可选附加文件，来源可能不支持。

过滤条件示例：`size>3,length<300`，表示大于 3 MB 且短于 300 秒。`size` 单位为 MB，`length` 单位为秒。未知大小或时长的结果保留。

## 配置和支持信息

默认音频目录为用户主目录下的 `Music\dv365-music-downloader`，可以在界面中更改。旧版设置会自动读取，已有的自定义下载目录保持不变。设置和诊断日志位于 `%LOCALAPPDATA%\dv365-music-downloader`。下载记录仅在本次会话中保留；关闭程序不会删除音频。

本软件不要求账号，不包含支付、激活或自动更新功能，不主动上传下载记录。联网发生在用户查询或下载第三方内容时；相应来源会接收到查询、网络地址等请求信息。

已在当前 Windows x64 主机验证。尚未进行多台干净机器的兼容性验证，交付包未做代码签名。若系统显示未知发布者，请先核对交付包来源与校验文件。

交付目录中的 `SHA256SUMS.txt` 记录文件校验值，`STARTUP_CHECK.json` 记录打包后启动检查结果。`LICENSE`、`ORIGINAL_README.md` 和 `THIRD_PARTY_NOTICES.txt` 保留原项目及运行依赖许可；`授权与接口核对.md` 说明未解决事项。

## 从源码运行和构建

本机已配置 uv。建议使用已验证的 Python 3.11 x64，在新开发环境中安装 uv 后，于项目目录执行：

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.lock
uv pip install --python .venv/Scripts/python.exe --no-deps -e .
.\.venv\Scripts\python.exe -m music_dl.desktop
```

运行默认测试和生成交付包：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\build_desktop.py
```

默认测试通过本地 HTTP 服务与模拟来源验证实际程序，不下载第三方音乐。历史音乐源测试只有显式执行 `pytest --live` 时才运行，结果依赖平台当时的接口状态。构建脚本先运行默认测试，再打包和检查冻结后的 Tk 界面及加密依赖，最后输出 ZIP 和校验清单。
