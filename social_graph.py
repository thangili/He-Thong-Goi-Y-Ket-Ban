"""Mạng xã hội biểu diễn bằng đồ thị vô hướng, lưu bằng DANH SÁCH KỀ.

Mỗi người dùng có id nguyên liên tục 0..n-1 nên tra cứu đỉnh là O(1).
Danh sách bạn của mỗi người là một set để kiểm tra "đã là bạn" trong O(1).
Bộ nhớ: O(V + E).
"""
import heapq
import math
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    """Một gợi ý kết bạn: người được gợi ý, số bạn chung và điểm xếp hạng."""
    user_id: int
    mutual_count: int
    score: float


class SocialGraph:
    def __init__(self):
        self._adj = []      # _adj[u] là set các bạn của u
        self._names = []
        self.edge_count = 0

    # ---------- Thông tin ----------
    @property
    def user_count(self):
        return len(self._adj)

    def exists(self, uid):
        return isinstance(uid, int) and 0 <= uid < len(self._adj)

    def name_of(self, uid):
        return self._names[uid] if self.exists(uid) else "?"

    def degree(self, uid):
        return len(self._adj[uid]) if self.exists(uid) else 0

    def friends_of(self, uid):
        return self._adj[uid] if self.exists(uid) else frozenset()

    # ---------- Thao tác cơ bản ----------
    def add_user(self, name=""):
        """Thêm người dùng mới, trả về id. O(1)."""
        self._adj.append(set())
        uid = len(self._adj) - 1
        self._names.append(name.strip() if name and name.strip() else f"User{uid}")
        return uid

    def add_friend(self, a, b):
        """Kết bạn a - b. False nếu id sai, tự kết bạn hoặc đã là bạn. O(1)."""
        if not self.exists(a) or not self.exists(b) or a == b:
            return False
        if b in self._adj[a]:
            return False
        self._adj[a].add(b)
        self._adj[b].add(a)
        self.edge_count += 1
        return True

    def remove_friend(self, a, b):
        """Hủy kết bạn. False nếu hai người chưa là bạn. O(1)."""
        if not self.exists(a) or not self.exists(b) or b not in self._adj[a]:
            return False
        self._adj[a].remove(b)
        self._adj[b].remove(a)
        self.edge_count -= 1
        return True

    def are_friends(self, a, b):
        return self.exists(a) and self.exists(b) and b in self._adj[a]

    def mutual_friends(self, a, b):
        """Bạn chung = giao của hai tập bạn.
        Duyệt tập nhỏ hơn, tra trong tập lớn hơn nên mất O(min(deg a, deg b))."""
        if not self.exists(a) or not self.exists(b) or a == b:
            return []
        small, large = (self._adj[a], self._adj[b])
        if len(small) > len(large):
            small, large = large, small
        return [x for x in small if x in large]

    # ---------- Gợi ý kết bạn ----------
    def recommend(self, u, k=5, use_adamic_adar=False):
        """Gợi ý top-k người cho u.

        Ứng viên là "bạn của bạn" (khoảng cách đúng bằng 2): với mỗi bạn f của u,
        mỗi bạn x của f (x khác u, chưa là bạn của u) được cộng 1 bạn chung.
        Xếp hạng: số bạn chung giảm dần; hòa thì ưu tiên người nhiều bạn hơn.
        Nếu use_adamic_adar = True, mỗi bạn chung f có trọng số 1/ln(deg f):
        bạn chung "ít bạn" (thân thiết hơn) có giá trị cao hơn bạn chung "đông bạn".
        Độ phức tạp: O(tổng deg của bạn bè + C log k), C là số ứng viên (heap kích thước k).
        """
        if not self.exists(u) or k <= 0:
            return []
        adj = self._adj
        friends = adj[u]
        count, weight = {}, {}
        for f in friends:
            neighbors = adj[f]
            w = 1.0 / math.log(len(neighbors)) if use_adamic_adar and len(neighbors) > 1 else 1.0
            for x in neighbors:
                if x == u or x in friends:
                    continue
                count[x] = count.get(x, 0) + 1
                weight[x] = weight.get(x, 0.0) + w

        def key(x):
            return (weight[x] if use_adamic_adar else count[x], len(adj[x]), -x)

        best = heapq.nlargest(k, count, key=key)      # min-heap kích thước k bên trong
        return [Recommendation(x, count[x], weight[x] if use_adamic_adar else float(count[x])) for x in best]

    # ---------- Khoảng cách (BFS / DFS) ----------
    def shortest_path(self, s, t):
        """BFS tìm đường đi NGẮN NHẤT từ s đến t.
        Trả về danh sách đỉnh (số bậc quan hệ = len - 1) hoặc None nếu không có đường. O(V + E)."""
        if not self.exists(s) or not self.exists(t):
            return None
        if s == t:
            return [s]
        parent = {s: -1}
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for v in self._adj[u]:
                if v in parent:
                    continue
                parent[v] = u
                if v == t:
                    path = []
                    x = t
                    while x != -1:
                        path.append(x)
                        x = parent[x]
                    path.reverse()
                    return path
                queue.append(v)
        return None

    def distance(self, a, b):
        """Số bậc quan hệ ngắn nhất giữa a và b; -1 nếu không liên thông."""
        p = self.shortest_path(a, b)
        return -1 if p is None else len(p) - 1

    def dfs_path_length(self, s, t):
        """DFS (lặp, dùng stack) trả về độ dài đường đi MÀ DFS TÌM ĐƯỢC từ s đến t.
        Chỉ dùng để so sánh với BFS: DFS không đảm bảo ngắn nhất. -1 nếu không có đường."""
        if not self.exists(s) or not self.exists(t):
            return -1
        if s == t:
            return 0
        parent = {}
        stack = [(s, -1)]
        while stack:
            v, p = stack.pop()
            if v in parent:
                continue
            parent[v] = p
            if v == t:
                break
            for w in self._adj[v]:
                if w not in parent:
                    stack.append((w, v))
        if t not in parent:
            return -1
        length, x = 0, t
        while x != s:
            x = parent[x]
            length += 1
        return length
