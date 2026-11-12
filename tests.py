"""Bộ kiểm thử: dữ liệu nhỏ có đáp án biết trước và các trường hợp cận biên."""
import random

from graph_generator import random_graph
from social_graph import SocialGraph

_pass = 0
_fail = 0


def _check(name, ok):
    global _pass, _fail
    if ok:
        _pass += 1
    else:
        _fail += 1
    print(f"  [{'ĐẠT' if ok else 'LỖI'}] {name}")


def _make(n, *edges):
    g = SocialGraph()
    for i in range(n):
        g.add_user(f"U{i}")
    for a, b in edges:
        g.add_friend(a, b)
    return g


def run_all():
    """Chạy toàn bộ test, in kết quả ra màn hình, trả về (số đạt, số lỗi)."""
    global _pass, _fail
    _pass = _fail = 0

    print("== Thao tác cơ bản ==")
    g = _make(3)
    _check("add_user cấp id liên tục", g.add_user("X") == 3 and g.user_count == 4)
    _check("add_friend hợp lệ", g.add_friend(0, 1) and g.are_friends(1, 0) and g.edge_count == 1)
    _check("add_friend trùng bị từ chối", not g.add_friend(1, 0) and g.edge_count == 1)
    _check("Tự kết bạn bị từ chối", not g.add_friend(2, 2))
    _check("Kết bạn với id không tồn tại bị từ chối", not g.add_friend(0, 99) and not g.add_friend(-1, 0))
    _check("remove_friend chưa là bạn trả về False", not g.remove_friend(0, 2))
    _check("remove_friend hợp lệ", g.remove_friend(0, 1) and not g.are_friends(0, 1) and g.edge_count == 0)

    print("== Bạn chung ==")
    m = _make(5, (0, 2), (0, 3), (1, 2), (1, 3), (1, 4))
    mf = m.mutual_friends(0, 1)
    _check("0 và 1 có đúng 2 bạn chung {2,3}", sorted(mf) == [2, 3])
    _check("Không có bạn chung -> rỗng", m.mutual_friends(0, 4) == [])
    _check("Người không tồn tại -> rỗng", m.mutual_friends(0, 42) == [])

    print("== Gợi ý kết bạn ==")
    # 0 có bạn {2,3}; 1 là bạn của cả 2 và 3; 4 chỉ là bạn của 2
    rg = _make(5, (0, 2), (0, 3), (1, 2), (1, 3), (2, 4))
    r = rg.recommend(0, 5)
    _check("Gợi ý cho 0: người đầu là 1 (2 bạn chung)", len(r) >= 1 and r[0].user_id == 1 and r[0].mutual_count == 2)
    _check("Gợi ý cho 0: người thứ hai là 4 (1 bạn chung)", len(r) == 2 and r[1].user_id == 4 and r[1].mutual_count == 1)
    _check("Không gợi ý người đã là bạn hoặc chính mình", all(x.user_id != 0 and not rg.are_friends(0, x.user_id) for x in r))
    _check("Người không có bạn -> không có gợi ý", _make(3).recommend(0) == [])
    _check("Giới hạn top-k", len(rg.recommend(0, 1)) == 1)
    k5 = _make(5, (0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4))
    _check("Đồ thị đầy đủ K5 -> không còn ai để gợi ý", k5.recommend(0) == [])

    print("== Khoảng cách (BFS) ==")
    chain = _make(6, (0, 1), (1, 2), (2, 3))
    _check("Cùng một người -> 0", chain.distance(2, 2) == 0)
    _check("Bạn trực tiếp -> 1", chain.distance(0, 1) == 1)
    _check("Chuỗi 0-1-2-3 -> 3", chain.distance(0, 3) == 3)
    _check("Không liên thông -> -1", chain.distance(0, 5) == -1)
    _check("Id không tồn tại -> -1", chain.distance(0, 99) == -1)
    _check("Đường đi đúng thứ tự", chain.shortest_path(0, 3) == [0, 1, 2, 3])
    tri = _make(4, (0, 1), (1, 2), (0, 2), (2, 3))
    _check("BFS chọn đường ngắn nhất (0->3 = 2)", tri.distance(0, 3) == 2)

    print("== So sánh BFS và DFS trên đồ thị ngẫu nhiên ==")
    big = random_graph(2000, 6, 7)
    rnd = random.Random(1)
    dfs_never_shorter, same_reach = True, True
    for _ in range(100):
        a, b = rnd.randrange(2000), rnd.randrange(2000)
        d1, d2 = big.distance(a, b), big.dfs_path_length(a, b)
        if (d1 == -1) != (d2 == -1):
            same_reach = False
        if d1 != -1 and d2 < d1:
            dfs_never_shorter = False
    _check("BFS và DFS thống nhất về khả năng đến được", same_reach)
    _check("Đường DFS không bao giờ ngắn hơn BFS", dfs_never_shorter)

    print(f"\nKết quả: {_pass} đạt, {_fail} lỗi.")
    return _pass, _fail


if __name__ == "__main__":
    run_all()
