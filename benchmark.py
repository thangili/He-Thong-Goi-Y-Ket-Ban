"""Đo thời gian (time.perf_counter) và bộ nhớ (tracemalloc) của các chức năng chính."""
import csv
import gc
import random
import time
import tracemalloc
from dataclasses import dataclass

from graph_generator import random_graph, scale_free_graph


@dataclass
class BenchResult:
    type: str            # "Random" hoặc "ScaleFree"
    n: int
    e: int
    build_ms: float
    mem_mb: float
    rec_ms: float
    rec_aa_ms: float
    bfs_ms: float
    dfs_ms: float
    bfs_len: float
    dfs_len: float
    mutual_us: float


CSV_HEADER = ["Type", "N", "E", "BuildMs", "MemMB", "RecommendMs", "RecommendAdamicAdarMs",
              "BfsMs", "DfsMs", "AvgBfsLen", "AvgDfsLen", "MutualUs"]


def _build(kind, n, avg_deg, seed):
    if kind == "Random":
        return random_graph(n, avg_deg, seed)
    return scale_free_graph(n, max(1, avg_deg // 2), seed)


def run(kind, n, avg_deg=10, seed=42):
    # 1) Thời gian dựng đồ thị (không bật tracemalloc để không làm chậm)
    gc.collect()
    t = time.perf_counter()
    g = _build(kind, n, avg_deg, seed)
    build_ms = (time.perf_counter() - t) * 1000

    # 2) Bộ nhớ: dựng lại một đồ thị giống hệt dưới tracemalloc
    tracemalloc.start()
    tmp = _build(kind, n, avg_deg, seed)
    mem_mb = tracemalloc.get_traced_memory()[0] / 1048576
    tracemalloc.stop()
    del tmp
    gc.collect()

    rnd = random.Random(seed + 1)

    # 3) Gợi ý kết bạn: 200 người dùng ngẫu nhiên, top-5
    users = [rnd.randrange(n) for _ in range(200)]
    t = time.perf_counter()
    for u in users:
        g.recommend(u, 5)
    rec_ms = (time.perf_counter() - t) * 1000 / len(users)
    t = time.perf_counter()
    for u in users:
        g.recommend(u, 5, use_adamic_adar=True)
    rec_aa_ms = (time.perf_counter() - t) * 1000 / len(users)

    # 4) BFS và DFS trên cùng 50 cặp ngẫu nhiên
    pairs = [(rnd.randrange(n), rnd.randrange(n)) for _ in range(50)]
    t = time.perf_counter()
    bfs_lens = [g.distance(a, b) for a, b in pairs]
    bfs_ms = (time.perf_counter() - t) * 1000 / len(pairs)
    t = time.perf_counter()
    dfs_lens = [g.dfs_path_length(a, b) for a, b in pairs]
    dfs_ms = (time.perf_counter() - t) * 1000 / len(pairs)
    ok_b = [x for x in bfs_lens if x >= 0]
    ok_d = [x for x in dfs_lens if x >= 0]
    bfs_len = sum(ok_b) / len(ok_b) if ok_b else 0.0
    dfs_len = sum(ok_d) / len(ok_d) if ok_d else 0.0

    # 5) Bạn chung: 2000 cặp (người, một người bạn của họ)
    mp = []
    while len(mp) < 2000:
        a = rnd.randrange(n)
        if g.degree(a) == 0:
            continue
        mp.append((a, next(iter(g.friends_of(a)))))
    t = time.perf_counter()
    for a, b in mp:
        g.mutual_friends(a, b)
    mutual_us = (time.perf_counter() - t) * 1e6 / len(mp)

    return BenchResult(kind, n, g.edge_count, build_ms, mem_mb, rec_ms, rec_aa_ms,
                       bfs_ms, dfs_ms, bfs_len, dfs_len, mutual_us)


def to_csv(results):
    rows = [CSV_HEADER]
    for r in results:
        rows.append([r.type, r.n, r.e, f"{r.build_ms:.1f}", f"{r.mem_mb:.2f}", f"{r.rec_ms:.4f}",
                     f"{r.rec_aa_ms:.4f}", f"{r.bfs_ms:.4f}", f"{r.dfs_ms:.4f}",
                     f"{r.bfs_len:.2f}", f"{r.dfs_len:.2f}", f"{r.mutual_us:.3f}"])
    return rows


def save_csv(results, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: Excel mở không lỗi
        csv.writer(f).writerows(to_csv(results))


def run_all(sizes, avg_deg=10, csv_path="ket_qua_thuc_nghiem.csv"):
    """Chạy cả hai loại đồ thị, in bảng ra màn hình và lưu CSV."""
    head = (f"{'Loại':<10}{'Đỉnh':>9}{'Cạnh':>10}{'Dựng(ms)':>10}{'RAM(MB)':>9}{'Gợi ý(ms)':>11}"
            f"{'GợiýAA(ms)':>12}{'BFS(ms)':>9}{'DFS(ms)':>9}{'Dài BFS':>9}{'Dài DFS':>9}{'Chung(µs)':>11}")
    print(head)
    results = []
    for kind in ("Random", "ScaleFree"):
        for n in sizes:
            r = run(kind, n, avg_deg)
            results.append(r)
            print(f"{r.type:<10}{r.n:>9}{r.e:>10}{r.build_ms:>10.0f}{r.mem_mb:>9.1f}{r.rec_ms:>11.3f}"
                  f"{r.rec_aa_ms:>12.3f}{r.bfs_ms:>9.3f}{r.dfs_ms:>9.3f}{r.bfs_len:>9.2f}{r.dfs_len:>9.1f}{r.mutual_us:>11.2f}")
    save_csv(results, csv_path)
    print(f"\nĐã lưu kết quả vào: {csv_path} (mở bằng Excel để vẽ biểu đồ)")
    return results
