#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
from pathlib import Path
from Bio import SeqIO
import matplotlib.pyplot as plt

def parse_ab1_traces(ab1_path):
    """
    解析 ab1 文件，返回：
    - traces: dict[base] -> intensity array（例如 {"A": [...], "C": [...]}）
    - seq:    碱基序列（str）
    - base_calls: 碱基序列字符串
    - base_positions: 每个碱基在色谱上的位置（list[int]），可能为 None
    """
    record = SeqIO.read(str(ab1_path), "abi")
    abif = record.annotations["abif_raw"]
    
    # 序列
    seq = str(record.seq)
    
    # base calls （PBAS2 优先，没有就退回 PBAS1）
    base_calls = abif.get("PBAS2") or abif.get("PBAS1")
    if isinstance(base_calls, bytes):
        base_calls = base_calls.decode(errors="ignore")
    
    # 每个 base 在 trace 上的位置（可选）
    base_positions = abif.get("PLOC2")
    # 有些机器可能没有 PLOC2，这种情况就留 None
    if base_positions is not None:
        base_positions = list(base_positions)
    
    # 通道顺序 FWO_（比如 b"GATC"）
    fwo = abif.get("FWO_")  # forward order
    if fwo is None:
        # 极少数情况下没有 FWO_，这里可以设一个默认顺序
        channel_order = ["G", "A", "T", "C"]
    else:
        if isinstance(fwo, bytes):
            fwo = fwo.decode(errors="ignore")
        channel_order = [b for b in fwo if b in "ACGT"]
    
    # 找出所有 DATA 通道并按编号排序（DATA9, DATA10, DATA11, DATA12）
    data_keys = sorted(
        [k for k in abif.keys() if k.startswith("DATA")],
        key=lambda x: int(x[4:])
    )
    
    # 取前四个通道映射到 A/C/G/T（通常就是 4 条峰图）
    traces = {}
    for base, key in zip(channel_order, data_keys[:4]):
        traces[base] = abif[key]
    
    return traces, seq, base_calls, base_positions

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
    
    plt.xlabel("Trace index")
    plt.ylabel("Signal intensity")
    plt.title(title)
    plt.legend(loc="upper right")
    
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
        return True
    except Exception as e:
        log(f"[ERROR] 处理 {ab1_path} 时出错: {e}")
        return False

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

