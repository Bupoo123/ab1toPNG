#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
from pathlib import Path

from abifpy import Trace
# 设置 matplotlib 使用非交互式后端（避免在服务器环境中崩溃）
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt

def parse_ab1_traces(ab1_path):
    """
    解析 ab1 文件，返回：
    - traces: dict[base] -> intensity array（例如 {"A": [...], "C": [...]}）
    - seq:    碱基序列（str）
    - base_calls: 碱基序列字符串
    - base_positions: 每个碱基在色谱上的位置（list[int]），可能为 None

    使用 abifpy 库解析 ab1 文件，如果解析失败会直接抛出异常。
    """
    # 使用 abifpy 解析 ab1 文件
    try:
        reader = Trace(str(ab1_path))
    except Exception as e:
        raise ValueError(f"无法打开 ab1 文件: {str(e)}")
    
    try:
        # 检查 reader 是否有 tags 属性
        if not hasattr(reader, 'tags'):
            raise ValueError("ab1 文件格式不正确：缺少 tags 数据")
        
        # 获取序列（PBAS2 优先，没有就退回 PBAS1）
        seq_bytes = None
        try:
            if "PBAS2" in reader.tags:
                seq_bytes = reader.get_data("PBAS2")
        except (KeyError, AttributeError, TypeError, NameError):
            pass
        
        if seq_bytes is None:
            try:
                if "PBAS1" in reader.tags:
                    seq_bytes = reader.get_data("PBAS1")
            except (KeyError, AttributeError, TypeError, NameError):
                pass
        
        if seq_bytes is None:
            raise ValueError("无法从 ab1 文件中获取序列数据（PBAS2 和 PBAS1 都不存在）")
        
        if isinstance(seq_bytes, bytes):
            seq = seq_bytes.decode(errors="ignore")
        else:
            seq = str(seq_bytes)
        
        base_calls = seq
        
        # 获取碱基位置（PLOC2）
        base_positions = None
        try:
            if "PLOC2" in reader.tags:
                base_positions = reader.get_data("PLOC2")
                if base_positions is not None:
                    base_positions = list(base_positions)
        except (KeyError, AttributeError, TypeError, NameError):
            base_positions = None
        
        # 获取通道顺序 FWO_（比如 b"GATC"）
        fwo = None
        try:
            if "FWO_" in reader.tags:
                fwo = reader.get_data("FWO_")
        except (KeyError, AttributeError, TypeError, NameError):
            fwo = None
        
        if fwo is None:
            # 极少数情况下没有 FWO_，使用默认顺序
            channel_order = ["G", "A", "T", "C"]
        else:
            if isinstance(fwo, bytes):
                fwo = fwo.decode(errors="ignore")
            channel_order = [b for b in fwo if b in "ACGT"]
            if not channel_order:
                channel_order = ["G", "A", "T", "C"]
        
        # 获取 DATA 通道数据（DATA9, DATA10, DATA11, DATA12）
        # 根据通道顺序映射到对应的碱基
        data_channels = {
            "DATA9": None,
            "DATA10": None,
            "DATA11": None,
            "DATA12": None
        }
        
        for key in data_channels.keys():
            try:
                if key in reader.tags:
                    data_channels[key] = reader.get_data(key)
                    if data_channels[key] is None:
                        raise ValueError(f"无法从 ab1 文件中获取 {key} 数据")
                else:
                    raise ValueError(f"ab1 文件中不存在 {key} 标签")
            except (KeyError, AttributeError, TypeError, NameError) as e:
                raise ValueError(f"无法从 ab1 文件中获取 {key} 数据: {str(e)}")
        
        # 将 DATA 通道映射到对应的碱基
        traces = {}
        data_keys = ["DATA9", "DATA10", "DATA11", "DATA12"]
        for base, key in zip(channel_order, data_keys[:4]):
            traces[base] = data_channels[key]
        
        return traces, seq, base_calls, base_positions
    finally:
        # 确保关闭 reader
        try:
            reader.close()
        except:
            pass
    
    # 将 DATA 通道映射到对应的碱基
    traces = {}
    data_keys = ["DATA9", "DATA10", "DATA11", "DATA12"]
    for base, key in zip(channel_order, data_keys[:4]):
        traces[base] = data_channels[key]
    
    reader.close()
    return traces, seq, base_calls, base_positions

def _guess_window_from_signal(traces, threshold_ratio=0.01, padding=100):
    """
    根据信号强度估计应该展示的区间。

    - 将四个通道求和，找到信号占比超过 threshold_ratio * max_intensity 的位置
    - 返回 (start, end) 供 x 轴范围使用，如果无法判断则返回 (0, length-1)
    """
    import numpy as np
    example_base = next(iter(traces))
    length = len(traces[example_base])

    # 合并四条曲线，避免某一通道过低导致误判
    merged = None
    for trace in traces.values():
        if merged is None:
            merged = np.array(trace, dtype=float)
        else:
            merged = merged + np.array(trace, dtype=float)

    max_intensity = merged.max() if merged is not None else 0
    if max_intensity <= 0:
        return 0, length - 1

    mask = merged >= max_intensity * threshold_ratio
    if not mask.any():
        return 0, length - 1

    indices = np.nonzero(mask)[0]
    start = max(int(indices.min()) - padding, 0)
    end = min(int(indices.max()) + padding, length - 1)
    return start, end

def plot_chromatogram(traces, seq, base_calls, base_positions,
                      title, out_path, dpi=200, width=16, height=4):
    """
    画色谱图并保存为 PNG
    """
    plt.figure(figsize=(width, height))
    
    # X 轴长度以任意一个通道的长度为准
    example_base = next(iter(traces))
    length = len(traces[example_base])
    x = range(length)
    
    # 为四种碱基预设颜色（可按自己习惯改）
    base_colors = {
        "A": "green",
        "C": "blue",
        "G": "black",
        "T": "red"
    }
    
    for base, trace in traces.items():
        color = base_colors.get(base, None)
        plt.plot(x, trace, label=base, color=color, linewidth=0.5)
    
    # 计算可视化范围，避免色谱尾部长串 0 造成横轴过长
    if base_positions:
        start = max(min(base_positions) - 100, 0)
        end = min(max(base_positions) + 100, length - 1)
    else:
        start, end = _guess_window_from_signal(traces)
    
    plt.xlabel("Trace index")
    plt.ylabel("Signal intensity")
    plt.title(title)
    plt.legend(loc="upper right")
    plt.xlim(start, end)
    
    # 可选：在碱基位置上画竖线，并标注 base_calls
    # 如果你觉得太乱，可以把这一段注释掉
    if base_positions is not None and base_calls:
        ymin, ymax = plt.ylim()
        for i, (pos, base) in enumerate(zip(base_positions, base_calls)):
            if 0 <= pos < length:
                plt.vlines(pos, ymin, ymax * 0.9, alpha=0.1, linewidth=0.3)
                # 只在较少间隔处标注文字，否则会太密
                # 这里简单按步长取一部分
                if i % 50 == 0:  # 每50个碱基标注一次
                    plt.text(pos, ymax * 0.95, base, ha="center", fontsize=6, alpha=0.6)
    
    plt.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(out_path), dpi=dpi, bbox_inches="tight")
    plt.close()

def process_single_file(ab1_path, out_dir, dpi=200, log_callback=None):
    """
    处理单个 ab1 文件
    log_callback: 可选的日志回调函数，接受一个字符串参数
    返回: (success: bool, error_message: str)
    """
    ab1_path = Path(ab1_path)
    out_dir = Path(out_dir)
    
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)
    
    try:
        title = ab1_path.name
        traces, seq, base_calls, base_positions = parse_ab1_traces(ab1_path)
        
        out_name = ab1_path.with_suffix(".png").name
        out_path = out_dir / out_name
        
        plot_chromatogram(
            traces=traces,
            seq=seq,
            base_calls=base_calls,
            base_positions=base_positions,
            title=title,
            out_path=out_path,
            dpi=dpi
        )
        log(f"[OK] {ab1_path} -> {out_path}")
        return True, None
    except Exception as e:
        import traceback
        error_detail = str(e)
        error_trace = traceback.format_exc()
        log(f"[ERROR] 处理 {ab1_path} 时出错: {error_detail}")
        log(f"[ERROR] 详细错误: {error_trace}")
        return False, error_detail

def process_path(input_path, out_dir, dpi=200):
    input_path = Path(input_path)
    
    if input_path.is_file():
        process_single_file(input_path, out_dir, dpi=dpi)
    elif input_path.is_dir():
        # 遍历目录中的 .ab1 / .abi 文件
        ab1_files = []
        for root, dirs, files in os.walk(input_path):
            for name in files:
                if name.lower().endswith((".ab1", ".abi")):
                    fpath = Path(root) / name
                    ab1_files.append(fpath)
        
        if not ab1_files:
            print(f"[WARNING] 在 {input_path} 中未找到 .ab1 或 .abi 文件")
            return
        
        print(f"[INFO] 找到 {len(ab1_files)} 个 ab1 文件，开始转换...")
        success_count = 0
        for fpath in ab1_files:
            if process_single_file(fpath, out_dir, dpi=dpi):
                success_count += 1
        
        print(f"\n[完成] 成功转换 {success_count}/{len(ab1_files)} 个文件")
    else:
        raise FileNotFoundError(f"输入路径不存在: {input_path}")

def main():
    parser = argparse.ArgumentParser(
        description="批量将 Sanger .ab1 色谱图转换为 PNG 图片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 转换单个文件
  python ab1_to_png.py sample.ab1 -o ./png_output
  
  # 转换整个目录
  python ab1_to_png.py /path/to/ab1_dir -o ./png_output --dpi 300
        """
    )
    parser.add_argument(
        "input",
        help="输入的 .ab1 文件或包含 .ab1 文件的目录"
    )
    parser.add_argument(
        "-o", "--outdir",
        default="png_output",
        help="PNG 输出目录（默认: png_output）"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="输出 PNG 的 DPI（默认: 200）"
    )
    
    args = parser.parse_args()
    process_path(args.input, args.outdir, dpi=args.dpi)

if __name__ == "__main__":
    main()

