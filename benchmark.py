"""FastFileOp Benchmark - Generate speed comparison chart

Benchmarks multi-file copy performance: FastFileOp (parallel)
vs Windows sequential copy (shutil.copy2 with metadata).
"""

import os
import shutil
import sys
import time
import ctypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from fastfileop.engine import FileEngine


def flush_os_cache():
    """Minimize OS file cache effects between runs."""
    try:
        ctypes.windll.kernel32.SetProcessWorkingSetSize(
            ctypes.windll.kernel32.GetCurrentProcess(), -1, -1
        )
    except Exception:
        pass
    time.sleep(0.5)


def benchmark_fastfileop(src_list: list, dst_dir: str, workers: int = 4) -> dict:
    """Benchmark FastFileOp parallel copy."""
    total_size = sum(os.path.getsize(f) for f in src_list)
    engine = FileEngine(max_workers=workers)

    flush_os_cache()
    start = time.time()
    engine.copy(src_list, dst_dir)
    elapsed = time.time() - start

    speed = total_size / elapsed if elapsed > 0 else 0

    # Cleanup
    for f in src_list:
        dst_file = os.path.join(dst_dir, os.path.basename(f))
        if os.path.exists(dst_file):
            try:
                os.remove(dst_file)
            except Exception:
                pass

    return {"speed": speed, "elapsed": elapsed, "size": total_size}


def benchmark_sequential(src_list: list, dst_dir: str) -> dict:
    """Benchmark sequential copy (simulates Windows Explorer behavior).

    Uses shutil.copy2 which preserves metadata (timestamps, permissions),
    closer to what Windows Explorer actually does.
    """
    total_size = sum(os.path.getsize(f) for f in src_list)

    flush_os_cache()
    start = time.time()
    for f in src_list:
        dst_file = os.path.join(dst_dir, f"seq_{os.path.basename(f)}")
        shutil.copy2(f, dst_file)
    elapsed = time.time() - start

    speed = total_size / elapsed if elapsed > 0 else 0

    # Cleanup
    for f in src_list:
        dst_file = os.path.join(dst_dir, f"seq_{os.path.basename(f)}")
        if os.path.exists(dst_file):
            try:
                os.remove(dst_file)
            except Exception:
                pass

    return {"speed": speed, "elapsed": elapsed, "size": total_size}


def format_speed(bps: float) -> str:
    if bps >= 1024 ** 3:
        return f"{bps / 1024**3:.1f} GB/s"
    elif bps >= 1024 ** 2:
        return f"{bps / 1024**2:.0f} MB/s"
    elif bps >= 1024:
        return f"{bps / 1024:.0f} KB/s"
    return f"{bps:.0f} B/s"


def format_size(b: float) -> str:
    if b >= 1024 ** 3:
        return f"{b / 1024**3:.0f} GB"
    elif b >= 1024 ** 2:
        return f"{b / 1024**2:.0f} MB"
    elif b >= 1024:
        return f"{b / 1024:.0f} KB"
    return f"{b:.0f} B"


def generate_chart(results: dict, output_path: str):
    """Generate comparison bar chart."""
    if not HAS_PIL:
        print("PIL not available, skipping chart generation")
        return

    W, H = 640, 400
    img = Image.new("RGB", (W, H), "#1e1e2e")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 22)
        font_label = ImageFont.truetype("arial.ttf", 15)
        font_speed = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 13)
        font_ratio = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font_title = ImageFont.load_default()
        font_label = font_title
        font_speed = font_title
        font_small = font_title
        font_ratio = font_title

    # Title
    title = "FastFileOp vs Windows Default"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 15), title, fill="#cdd6f4", font=font_title)

    # Subtitle
    sub = results.get("subtitle", "Multi-File Copy Benchmark")
    bbox_sub = draw.textbbox((0, 0), sub, font=font_small)
    sw = bbox_sub[2] - bbox_sub[0]
    draw.text(((W - sw) // 2, 45), sub, fill="#6c7086", font=font_small)

    # Bar settings
    ffo_speed = results.get("fastfileop_speed", 0)
    win_speed = results.get("windows_speed", 0)
    bar_w = 160
    bar_h_max = 180
    base_y = 295
    max_speed = max(ffo_speed, win_speed) * 1.15

    def draw_bar(x_center, label, speed, color, accent_color):
        h = int((speed / max_speed) * bar_h_max) if max_speed > 0 else 0
        x0 = x_center - bar_w // 2
        y0 = base_y - h
        x1 = x_center + bar_w // 2

        # Shadow
        draw.rectangle([x0 + 3, y0 + 3, x1 + 3, base_y], fill="#11111b")
        # Main bar
        draw.rectangle([x0, y0, x1, base_y], fill=color)
        # Top highlight
        draw.rectangle([x0, y0, x1, y0 + 4], fill=accent_color)

        # Speed text
        speed_text = format_speed(speed)
        bbox_s = draw.textbbox((0, 0), speed_text, font=font_speed)
        stw = bbox_s[2] - bbox_s[0]
        draw.text((x_center - stw // 2, y0 - 28), speed_text, fill=accent_color, font=font_speed)

        # Label
        bbox_l = draw.textbbox((0, 0), label, font=font_label)
        lw = bbox_l[2] - bbox_l[0]
        draw.text((x_center - lw // 2, base_y + 10), label, fill="#a6adc8", font=font_label)

    # Draw bars
    gap = 100
    cx1 = W // 2 - gap
    cx2 = W // 2 + gap

    draw_bar(cx1, "Windows Default", win_speed, "#45475a", "#9399b8")
    draw_bar(cx2, "FastFileOp", ffo_speed, "#89b4fa", "#89dceb")

    # Speedup ratio
    if win_speed > 0:
        ratio = ffo_speed / win_speed
        ratio_text = f"{ratio:.1f}x faster"
        bbox_r = draw.textbbox((0, 0), ratio_text, font=font_ratio)
        rw = bbox_r[2] - bbox_r[0]
        draw.text(((W - rw) // 2, base_y + 38), ratio_text, fill="#a6e3a1", font=font_ratio)

    # Footer
    footer = "4 worker threads | 64MB buffer | NVMe SSD"
    bbox_f = draw.textbbox((0, 0), footer, font=font_small)
    fw = bbox_f[2] - bbox_f[0]
    draw.text(((W - fw) // 2, H - 25), footer, "#585b70", font=font_small)

    img.save(output_path)
    print(f"Chart saved to: {output_path}")


def main():
    print("=" * 50)
    print("FastFileOp Benchmark")
    print("=" * 50)

    base_tmp = os.path.join(os.environ.get("TEMP", "."), f"ffo_bench_{os.getpid()}")
    src_dir = os.path.join(base_tmp, "source")
    dst_dir = os.path.join(base_tmp, "destination")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(dst_dir, exist_ok=True)

    # --- Test: 500 files x 1MB = 500MB total ---
    # Many small files is where parallel copy shines:
    # per-file overhead (open/close/metadata) is distributed across threads
    num_files = 500
    file_size = 1 * 1024 * 1024  # 1 MB each
    total_size = num_files * file_size
    test_files = []

    print(f"\nGenerating {num_files} x {format_size(file_size)} test files ({format_size(total_size)} total)...")
    for i in range(num_files):
        fpath = os.path.join(src_dir, f"data_{i:04d}.bin")
        with open(fpath, "wb") as f:
            f.write(os.urandom(file_size))
        test_files.append(fpath)

    print("\n--- Sequential Copy (Windows Default Simulation) ---")
    seq_results = []
    for i in range(5):
        r = benchmark_sequential(test_files, dst_dir)
        seq_results.append(r["speed"])
        print(f"  Run {i+1}: {format_speed(r['speed'])} ({r['elapsed']:.2f}s)")
    seq_results.sort()
    windows_speed = seq_results[len(seq_results) // 2]  # median

    print("\n--- FastFileOp (4 Worker Threads) ---")
    ffo_results = []
    for i in range(5):
        r = benchmark_fastfileop(test_files, dst_dir, workers=4)
        ffo_results.append(r["speed"])
        print(f"  Run {i+1}: {format_speed(r['speed'])} ({r['elapsed']:.2f}s)")
    ffo_results.sort()
    ffo_speed = ffo_results[len(ffo_results) // 2]  # median

    # --- Summary ---
    ratio = ffo_speed / windows_speed if windows_speed > 0 else 0

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"  Test: {num_files} files x {format_size(file_size)} = {format_size(total_size)}")
    print(f"  FastFileOp (4 threads): {format_speed(ffo_speed):>12}  avg {ffo_speed/1024**2:.0f} MB/s")
    print(f"  Windows (sequential):   {format_speed(windows_speed):>12}  avg {windows_speed/1024**2:.0f} MB/s")
    print(f"  Speedup:                {ratio:.2f}x")
    print("=" * 50)

    # Generate chart
    results = {
        "fastfileop_speed": ffo_speed,
        "windows_speed": windows_speed,
        "subtitle": f"{num_files} files x {format_size(file_size)} = {format_size(total_size)}",
    }
    chart_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark.png")
    generate_chart(results, chart_path)

    # Cleanup
    try:
        shutil.rmtree(base_tmp, ignore_errors=True)
    except Exception:
        pass

    return {"ffo_speed": ffo_speed, "windows_speed": windows_speed, "ratio": ratio}


if __name__ == "__main__":
    result = main()
