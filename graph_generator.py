"""Sinh đồ thị lớn để thực nghiệm."""
import random

from social_graph import SocialGraph


def random_graph(n, avg_deg, seed=42):
    """Đồ thị ngẫu nhiên: n đỉnh, khoảng n*avg_deg/2 cạnh chọn ngẫu nhiên đều."""
    g = SocialGraph()
    for i in range(n):
        g.add_user(f"U{i}")
    rnd = random.Random(seed)
    target = min(n * avg_deg // 2, n * (n - 1) // 2)
    while g.edge_count < target:
        g.add_friend(rnd.randrange(n), rnd.randrange(n))
    return g


def scale_free_graph(n, m, seed=42):
    """Đồ thị "phi tỷ lệ" (Barabási–Albert): mỗi người mới kết bạn với m người cũ,
    xác suất chọn tỷ lệ với số bạn hiện có. Gần với mạng xã hội thật (có vài "hub" rất đông bạn)."""
    g = SocialGraph()
    for i in range(n):
        g.add_user(f"U{i}")
    rnd = random.Random(seed)
    ends = []   # mỗi cạnh đóng góp 2 đầu mút => chọn đều trong list = chọn tỷ lệ theo bậc
    m0 = min(m + 1, n)
    for i in range(m0):
        for j in range(i):
            if g.add_friend(i, j):
                ends.extend((i, j))
    for v in range(m0, n):
        added = 0
        while added < m:
            t = ends[rnd.randrange(len(ends))]
            if g.add_friend(v, t):
                ends.extend((v, t))
                added += 1
    return g
