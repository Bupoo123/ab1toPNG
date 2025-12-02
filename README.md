# ab1 转 PNG 批量工具

一个简单易用的工具，用于批量将 Sanger 测序的 `.ab1` 文件转换为 PNG 格式的色谱图。提供**命令行版本**和**图形界面版本**两种使用方式。

## 功能特点

- ✅ 支持单个文件或整个目录批量转换
- ✅ 自动识别 ab1 文件中的通道顺序（A/C/G/T）
- ✅ 生成高质量的 PNG 色谱图
- ✅ 可自定义输出 DPI
- ✅ 自动标注碱基位置（可选）
- ✅ 提供图形界面（GUI）和命令行两种使用方式

## 安装依赖

```bash
pip install -r requirements.txt
```

或者直接安装：

```bash
pip install biopython matplotlib
```

> **注意**：GUI 版本使用 tkinter，Python 3.x 通常自带，无需额外安装。

## 使用方法

### 🖥️ 图形界面版本（推荐）

最简单的方式，双击运行或使用命令：

```bash
python3 ab1_to_png_gui.py
```

或者：

```bash
cd /Users/bupoo/github/ab1toPNG
python3 ab1_to_png_gui.py
```

**GUI 功能：**
- 点击"浏览"按钮选择输入文件或目录
- 选择输出目录
- 调整 DPI 分辨率（推荐 200-300）
- 点击"开始转换"按钮
- 实时查看转换日志和进度

### 💻 命令行版本

#### 转换单个文件

```bash
python3 ab1_to_png.py sample.ab1 -o ./png_output
```

#### 批量转换整个目录

```bash
python3 ab1_to_png.py /path/to/ab1_dir -o ./png_output --dpi 300
```

#### 参数说明

- `input`: 输入的 `.ab1` 文件或包含 `.ab1` 文件的目录（必需）
- `-o, --outdir`: PNG 输出目录（默认: `png_output`）
- `--dpi`: 输出 PNG 的 DPI 分辨率（默认: 200）

## 输出说明

- 输出的 PNG 文件会保持原文件名，只是扩展名改为 `.png`
- 例如：`sample1.ab1` → `sample1.png`
- 色谱图包含 4 条曲线，分别代表 A（绿色）、C（蓝色）、G（黑色）、T（红色）

## 注意事项

- 确保输入的 `.ab1` 文件是有效的 ABIF 格式文件
- 如果某个文件解析失败，会显示错误信息但不会中断整个批量处理过程
- 输出目录如果不存在会自动创建

## 后续可扩展功能

- [ ] 只画高质量区间（根据质量值自动裁剪）
- [ ] 支持指定区间范围（如只画 100-600bp）
- [ ] 自动生成 zoom-in 图（放大中间区域）
- [ ] 打包成可安装的命令行工具

