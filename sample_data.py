"""Dữ liệu mẫu 14 người dùng cho giao diện."""
from social_graph import SocialGraph

SAMPLE_NAMES = ["An", "Bình", "Chi", "Dũng", "Hà", "Khoa", "Lan", "Minh", "Nga", "Phúc", "Quân", "Thảo", "Uyên", "Vy"]
SAMPLE_EDGES = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 4), (2, 4), (3, 5), (4, 6), (5, 6), (5, 7), (6, 8),
                (7, 8), (8, 9), (9, 10), (10, 11), (10, 12), (11, 12), (12, 13), (9, 13)]


def make_sample_graph():
    g = SocialGraph()
    for name in SAMPLE_NAMES:
        g.add_user(name)
    for a, b in SAMPLE_EDGES:
        g.add_friend(a, b)
    return g
