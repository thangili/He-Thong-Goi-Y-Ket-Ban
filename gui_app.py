"""Giao diện đồ họa bằng tkinter (có sẵn trong Python, không cần cài thêm)."""
import contextlib
import io
import math
import queue
import random
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import benchmark
import tests
from graph_generator import scale_free_graph
from sample_data import make_sample_graph

INK, BG = "#17313B", "#F2F5F1"
COL_A, COL_B, GOLD, GREEN = "#2B6CB0", "#7B2D5B", "#D99A00", "#2E9E5B"
NODE, EDGE = "#2F6F73", "#C4D0CB"
FONT = "Segoe UI"

METRICS = [
    ("Thời gian dựng đồ thị (ms)", lambda r: r.build_ms),
    ("Bộ nhớ sử dụng (MB)", lambda r: r.mem_mb),
    ("Gợi ý kết bạn, trung bình mỗi người (ms)", lambda r: r.rec_ms),
    ("Gợi ý có trọng số Adamic-Adar (ms)", lambda r: r.rec_aa_ms),
    ("BFS, trung bình mỗi cặp (ms)", lambda r: r.bfs_ms),
    ("DFS, trung bình mỗi cặp (ms)", lambda r: r.dfs_ms),
    ("Tìm bạn chung (µs)", lambda r: r.mutual_us),
    ("Độ dài đường đi trung bình do BFS tìm được", lambda r: r.bfs_len),
    ("Độ dài đường đi trung bình do DFS tìm được", lambda r: r.dfs_len),
]


# =====================================================================
#  Vẽ đồ thị (mô phỏng lực, kéo thả, bấm chọn)
# =====================================================================
class GraphCanvas(tk.Canvas):
    MAX_DRAW = 200

    def __init__(self, master, on_pick):
        super().__init__(master, bg="#F7FAF8", highlightthickness=0)
        self.graph = None
        self.a = self.b = -1
        self.mutual = set()
        self.recs = {}
        self.path = []
        self.on_pick = on_pick
        self.pos, self.vel = {}, {}
        self._drag, self._down, self._moved = None, (0, 0), False
        self._rnd = random.Random(1)
        self.bind("<Button-1>", self._on_down)
        self.bind("<B1-Motion>", self._on_move)
        self.bind("<ButtonRelease-1>", self._on_up)
        self.bind("<Motion>", self._on_hover)
        self.after(30, self._tick)

    def reset_layout(self):
        self.pos.clear()
        self.vel.clear()
        self._drag = None

    # ---- mô phỏng lực: các đỉnh đẩy nhau, các cạnh như lò xo ----
    def _tick(self):
        self._step()
        self._draw()
        self.after(30, self._tick)

    def _step(self):
        g = self.graph
        w, h = self.winfo_width(), self.winfo_height()
        if g is None or w < 60 or h < 60:
            return
        n = g.user_count
        if n == 0 or n > self.MAX_DRAW:
            return
        for i in range(n):
            if i not in self.pos:
                self.pos[i] = [w / 2 + (self._rnd.random() - .5) * 200, h / 2 + (self._rnd.random() - .5) * 200]
                self.vel[i] = [0.0, 0.0]
        fx, fy = [0.0] * n, [0.0] * n
        for i in range(n):
            px, py = self.pos[i]
            fx[i] += (w / 2 - px) * .0015
            fy[i] += (h / 2 - py) * .0015
            for j in range(i + 1, n):
                qx, qy = self.pos[j]
                dx, dy = px - qx, py - qy
                d2 = dx * dx + dy * dy + 40.0
                d = math.sqrt(d2)
                f = 2600.0 / d2
                fx[i] += dx / d * f
                fy[i] += dy / d * f
                fx[j] -= dx / d * f
                fy[j] -= dy / d * f
            for j in g.friends_of(i):
                if j <= i:
                    continue
                qx, qy = self.pos[j]
                dx, dy = qx - px, qy - py
                d = math.hypot(dx, dy) or 1.0
                f = (d - 85.0) * .012
                fx[i] += dx / d * f
                fy[i] += dy / d * f
                fx[j] -= dx / d * f
                fy[j] -= dy / d * f
        for i in range(n):
            if i == self._drag and self._moved:
                continue
            vx = (self.vel[i][0] + fx[i]) * .82
            vy = (self.vel[i][1] + fy[i]) * .82
            self.vel[i] = [vx, vy]
            p = self.pos[i]
            p[0] = min(max(p[0] + vx, 26), w - 26)
            p[1] = min(max(p[1] + vy, 48), h - 26)

    # ---- vẽ ----
    def _draw(self):
        self.delete("all")
        g = self.graph
        if g is None:
            return
        n = g.user_count
        if n > self.MAX_DRAW:
            self.create_text(self.winfo_width() / 2, self.winfo_height() / 2, fill="gray", font=(FONT, 11),
                             text=f"Đồ thị có {n:,} người, quá lớn để vẽ (tối đa {self.MAX_DRAW}).")
            return
        on_path = set()
        for i in range(len(self.path) - 1):
            on_path.add((self.path[i], self.path[i + 1]))
            on_path.add((self.path[i + 1], self.path[i]))
        for u in range(n):
            if u not in self.pos:
                continue
            for v in g.friends_of(u):
                if v <= u or v not in self.pos:
                    continue
                hot = (u, v) in on_path
                self.create_line(*self.pos[u], *self.pos[v], fill=COL_B if hot else EDGE, width=4 if hot else 2)
        for i in range(n):
            if i not in self.pos:
                continue
            x, y = self.pos[i]
            is_a, is_b = i == self.a, i == self.b
            r = 15 if (is_a or is_b) else 12
            rec = i in self.recs
            if rec or i in self.mutual:
                self.create_oval(x - 17, y - 17, x + 17, y + 17, outline=GOLD if rec else GREEN, width=4)
            self.create_oval(x - r, y - r, x + r, y + r, fill=COL_A if is_a else COL_B if is_b else NODE, outline="")
            label = g.name_of(i) + (f" ({self.recs[i]})" if rec else "")
            self.create_text(x, y - 24, text=label, fill=INK, anchor="s",
                             font=(FONT, 9, "bold" if (is_a or is_b) else "normal"))

    # ---- chuột ----
    def _hit(self, x, y):
        for i in reversed(list(self.pos)):
            px, py = self.pos[i]
            if (px - x) ** 2 + (py - y) ** 2 < 18 ** 2:
                return i
        return None

    def _on_down(self, e):
        self._drag, self._down, self._moved = self._hit(e.x, e.y), (e.x, e.y), False

    def _on_move(self, e):
        if self._drag is None:
            return
        if abs(e.x - self._down[0]) + abs(e.y - self._down[1]) > 4:
            self._moved = True
        if self._moved:
            self.pos[self._drag] = [min(max(e.x, 26), self.winfo_width() - 26), min(max(e.y, 48), self.winfo_height() - 26)]
            self.vel[self._drag] = [0.0, 0.0]

    def _on_up(self, _e):
        if self._drag is not None and not self._moved:
            self.on_pick(self._drag)
        self._drag, self._moved = None, False

    def _on_hover(self, e):
        self.config(cursor="hand2" if self._hit(e.x, e.y) is not None else "")


# =====================================================================
#  Biểu đồ cột nhóm tự vẽ
# =====================================================================
class BarChart(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, bg="white", highlightthickness=1, highlightbackground="#D5DEEE")
        self.title, self.cats, self.series = "", [], []
        self.bind("<Configure>", lambda _e: self._redraw())

    def set_data(self, title, cats, series):
        """series: danh sách (tên, màu, [giá trị theo từng nhóm]); giá trị None = không có dữ liệu."""
        self.title, self.cats, self.series = title, cats, series
        self._redraw()

    @staticmethod
    def _nice_max(v):
        p = 10 ** math.floor(math.log10(v))
        m = v / p
        return (1 if m <= 1 else 2 if m <= 2 else 5 if m <= 5 else 10) * p

    @staticmethod
    def _fmt(v):
        return f"{v:.0f}" if v >= 100 else f"{v:.1f}" if v >= 10 else f"{v:.2f}" if v >= 1 else f"{v:.3f}"

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        self.create_text(8, 8, anchor="nw", text=self.title, font=(FONT, 10, "bold"))
        if not self.cats or not self.series:
            self.create_text(12, 40, anchor="nw", fill="gray", font=(FONT, 9),
                             text='Chưa có dữ liệu. Bấm "Chạy thực nghiệm" để tạo biểu đồ.')
            return
        left, top, right, bottom = 58, 44, 12, 30
        pw, ph = w - left - right, h - top - bottom
        if pw < 60 or ph < 50:
            return
        vals = [v for s in self.series for v in s[2] if v is not None]
        mx = self._nice_max(max(vals) if vals and max(vals) > 0 else 1)
        for i in range(5):
            y = top + ph - ph * i / 4
            self.create_line(left, y, left + pw, y, fill="#E2E2E2")
            self.create_text(left - 4, y, anchor="e", text=self._fmt(mx * i / 4), fill="#555", font=(FONT, 8))
        gw = pw / len(self.cats)
        bw = gw * 0.74 / len(self.series)
        for c, cat in enumerate(self.cats):
            gx = left + gw * c + gw * 0.13
            for s, (_name, color, data) in enumerate(self.series):
                v = data[c]
                if v is None:
                    continue
                bh = v / mx * ph
                x0 = gx + s * bw
                self.create_rectangle(x0, top + ph - bh, x0 + bw - 3, top + ph, fill=color, outline="")
                self.create_text(x0 + (bw - 3) / 2, top + ph - bh - 2, anchor="s", text=self._fmt(v), font=(FONT, 8))
            self.create_text(left + gw * c + gw / 2, top + ph + 6, anchor="n", text=cat, font=(FONT, 9))
        x = w - 12
        for name, color, _ in reversed(self.series):
            tw = len(name) * 7
            x -= tw
            self.create_text(x, 8, anchor="nw", text=name, font=(FONT, 9))
            x -= 16
            self.create_rectangle(x, 12, x + 11, 23, fill=color, outline="")
            x -= 14


# =====================================================================
#  Cửa sổ chính
# =====================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gợi ý kết bạn trên mạng xã hội - Cấu trúc dữ liệu và giải thuật")
        self.geometry("1320x780")
        self.minsize(1040, 660)
        self.configure(bg=BG)

        self.g = make_sample_graph()
        self.results = []
        self.next_is_b = True
        self._bench_queue = None

        tk.Label(self, text="  Gợi ý kết bạn trên mạng xã hội", bg=INK, fg="white", anchor="w",
                 font=(FONT, 15, "bold"), height=2).pack(fill="x")
        self.status = tk.Label(self, anchor="w", bd=1, relief="sunken", bg=BG, font=(FONT, 9))
        self.status.pack(side="bottom", fill="x")

        paned = tk.PanedWindow(self, orient="horizontal", sashwidth=6, bg=BG)
        paned.pack(fill="both", expand=True)
        left = tk.Frame(paned, bg=BG)
        self.canvas = GraphCanvas(left, self.on_node_picked)
        legend = tk.Frame(left, bg=BG)
        legend.pack(side="bottom", fill="x", pady=4)
        self.canvas.pack(fill="both", expand=True)
        for text, color in (("● Người A", COL_A), ("● Người B", COL_B), ("● Gợi ý (số bạn chung)", GOLD), ("● Bạn chung", GREEN)):
            tk.Label(legend, text=text, fg=color, bg=BG, font=(FONT, 9, "bold")).pack(side="left", padx=6)
        tk.Label(legend, text="Bấm để chọn, kéo để di chuyển", fg="gray", bg=BG, font=(FONT, 9)).pack(side="left", padx=6)

        tabs = ttk.Notebook(paned)
        paned.add(left, width=580, minsize=300)
        paned.add(tabs, minsize=480)
        self.tab_ops, self.tab_bench, self.tab_test = ttk.Frame(tabs), ttk.Frame(tabs), ttk.Frame(tabs)
        tabs.add(self.tab_ops, text="Thao tác")
        tabs.add(self.tab_bench, text="Thực nghiệm hiệu năng")
        tabs.add(self.tab_test, text="Kiểm thử")
        self._build_ops()
        self._build_bench()
        self._build_tests()

        self.load_sample()
        self.refresh_chart()

    # ---------------- Tab Thao tác ----------------
    def _build_ops(self):
        t = self.tab_ops
        f1 = ttk.LabelFrame(t, text="Thêm người dùng", padding=8)
        f1.pack(fill="x", padx=8, pady=(8, 4))
        self.var_name = tk.StringVar()
        e = ttk.Entry(f1, textvariable=self.var_name)
        e.pack(side="left", fill="x", expand=True, padx=(0, 8))
        e.bind("<Return>", lambda _e: self.add_user())
        ttk.Button(f1, text="Thêm người", command=self.add_user).pack(side="left")

        f2 = ttk.LabelFrame(t, text="Chọn hai người (hoặc bấm vào đồ thị)", padding=8)
        f2.pack(fill="x", padx=8, pady=4)
        f2.columnconfigure(0, weight=1)
        f2.columnconfigure(1, weight=1)
        tk.Label(f2, text="Người A", fg=COL_A, font=(FONT, 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(f2, text="Người B", fg=COL_B, font=(FONT, 9, "bold")).grid(row=0, column=1, sticky="w")
        self.cb_a = ttk.Combobox(f2, state="readonly")
        self.cb_b = ttk.Combobox(f2, state="readonly")
        self.cb_a.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.cb_b.grid(row=1, column=1, sticky="ew")
        self.cb_a.bind("<<ComboboxSelected>>", lambda _e: self.on_selection_changed())
        self.cb_b.bind("<<ComboboxSelected>>", lambda _e: self.on_selection_changed())

        f3 = ttk.LabelFrame(t, text="Chức năng", padding=8)
        f3.pack(fill="x", padx=8, pady=4)
        for c in range(3):
            f3.columnconfigure(c, weight=1)
        buttons = [("Kết bạn", lambda: self.do_friend(True)), ("Hủy bạn", lambda: self.do_friend(False)),
                   ("Tìm bạn chung", self.do_mutual), ("Gợi ý cho A", self.do_recommend),
                   ("Khoảng cách A → B", self.do_distance)]
        for i, (text, cmd) in enumerate(buttons):
            ttk.Button(f3, text=text, command=cmd).grid(row=i // 3, column=i % 3, sticky="ew", padx=3, pady=3)
        self.var_aa = tk.BooleanVar()
        ttk.Checkbutton(f3, text="Dùng trọng số Adamic-Adar", variable=self.var_aa).grid(row=1, column=2, sticky="w", padx=6)
        ttk.Button(f3, text="Nạp dữ liệu mẫu", command=self.load_sample).grid(row=2, column=0, sticky="ew", padx=3, pady=3)
        ttk.Button(f3, text="Sinh ngẫu nhiên 30 người", command=self.random_small).grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=3, pady=3)

        f4 = ttk.LabelFrame(t, text="Kết quả", padding=6)
        f4.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.txt_out = tk.Text(f4, wrap="word", height=8, font=(FONT, 10), state="disabled", bg="white")
        sb = ttk.Scrollbar(f4, command=self.txt_out.yview)
        self.txt_out.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt_out.pack(fill="both", expand=True)

    # ---------------- Tab Thực nghiệm ----------------
    def _build_bench(self):
        t = self.tab_bench
        top = ttk.Frame(t, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Số đỉnh (cách nhau bởi dấu phẩy):").grid(row=0, column=0, sticky="w")
        self.var_sizes = tk.StringVar(value="1000, 10000, 50000, 100000")
        ttk.Entry(top, textvariable=self.var_sizes, width=30).grid(row=0, column=1, padx=6, sticky="w")
        ttk.Label(top, text="Bậc trung bình:").grid(row=0, column=2, padx=(10, 0))
        self.var_deg = tk.StringVar(value="10")
        ttk.Entry(top, textvariable=self.var_deg, width=5).grid(row=0, column=3, padx=6)
        self.var_random, self.var_scale = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Đồ thị ngẫu nhiên", variable=self.var_random).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Checkbutton(top, text="Đồ thị phi tỷ lệ", variable=self.var_scale).grid(row=1, column=1, sticky="w")
        self.btn_run = ttk.Button(top, text="Chạy thực nghiệm", command=self.run_bench)
        self.btn_run.grid(row=1, column=2, columnspan=2, padx=6, sticky="ew")
        self.btn_csv = ttk.Button(top, text="Xuất CSV", command=self.export_csv, state="disabled")
        self.btn_csv.grid(row=1, column=4, padx=6)
        self.lbl_progress = ttk.Label(top, text="", foreground="gray")
        self.lbl_progress.grid(row=2, column=0, columnspan=5, sticky="w")

        cols = ("Loại đồ thị", "Số đỉnh", "Số cạnh", "Dựng (ms)", "RAM (MB)", "Gợi ý (ms)", "Gợi ý AA (ms)",
                "BFS (ms)", "DFS (ms)", "Dài BFS", "Dài DFS", "Bạn chung (µs)")
        frame = ttk.Frame(t)
        frame.pack(fill="x", padx=8)
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", height=8)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100 if c == "Loại đồ thị" else 78, anchor="e" if c != "Loại đồ thị" else "w")
        xs = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=xs.set)
        self.tree.pack(fill="x")
        xs.pack(fill="x")

        mrow = ttk.Frame(t, padding=(8, 6))
        mrow.pack(fill="x")
        ttk.Label(mrow, text="Biểu đồ:").pack(side="left")
        self.cb_metric = ttk.Combobox(mrow, state="readonly", width=44, values=[m[0] for m in METRICS])
        self.cb_metric.current(4)
        self.cb_metric.pack(side="left", padx=6)
        self.cb_metric.bind("<<ComboboxSelected>>", lambda _e: self.refresh_chart())
        self.chart = BarChart(t)
        self.chart.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ---------------- Tab Kiểm thử ----------------
    def _build_tests(self):
        t = self.tab_test
        row = ttk.Frame(t, padding=8)
        row.pack(fill="x")
        ttk.Button(row, text="Chạy bộ kiểm thử", command=self.run_tests).pack(side="left")
        ttk.Label(row, text="  Kiểm tra thao tác cơ bản, bạn chung, gợi ý, BFS/DFS và các trường hợp cận biên.",
                  foreground="gray").pack(side="left")
        frame = ttk.Frame(t)
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.txt_tests = tk.Text(frame, font=("Consolas", 10), state="disabled", bg="white", wrap="none")
        sb = ttk.Scrollbar(frame, command=self.txt_tests.yview)
        self.txt_tests.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt_tests.pack(fill="both", expand=True)

    # =====================================================================
    #  Trạng thái và tiện ích
    # =====================================================================
    @property
    def A(self):
        return self.cb_a.current()

    @property
    def B(self):
        return self.cb_b.current()

    def who(self, uid):
        return f"{self.g.name_of(uid)} (#{uid})"

    def say(self, *lines):
        self.txt_out.config(state="normal")
        self.txt_out.delete("1.0", "end")
        self.txt_out.insert("1.0", "\n".join(lines))
        self.txt_out.config(state="disabled")

    def update_status(self):
        self.status.config(text=f"  {self.g.user_count:,} người dùng, {self.g.edge_count:,} quan hệ bạn bè.   "
                                f"Bấm vào hai người trên đồ thị để chọn A và B.")

    def fill_combos(self, sel_a, sel_b):
        values = [self.who(i) for i in range(self.g.user_count)]
        for cb in (self.cb_a, self.cb_b):
            cb["values"] = values
            cb.set("")
        if 0 <= sel_a < len(values):
            self.cb_a.current(sel_a)
        if 0 <= sel_b < len(values):
            self.cb_b.current(sel_b)
        self.on_selection_changed()

    def clear_highlights(self):
        self.canvas.mutual, self.canvas.recs, self.canvas.path = set(), {}, []

    def on_selection_changed(self):
        self.canvas.a, self.canvas.b = self.A, self.B
        self.clear_highlights()

    def on_node_picked(self, uid):
        if self.next_is_b and uid != self.A:
            self.cb_b.current(uid)
            self.next_is_b = False
        else:
            self.cb_a.current(uid)
            self.cb_b.set("")
            self.next_is_b = True
        self.on_selection_changed()

    def need_one(self):
        if self.A >= 0:
            return True
        self.say("Hãy chọn Người A trước (bấm vào đồ thị hoặc chọn trong danh sách).")
        return False

    def need_two(self, allow_same=False):
        if self.A < 0 or self.B < 0:
            self.say("Hãy chọn cả Người A và Người B.")
            return False
        if not allow_same and self.A == self.B:
            self.say("Hãy chọn hai người khác nhau.")
            return False
        return True

    def set_graph(self, g, message):
        self.g = g
        self.canvas.graph = g
        self.canvas.reset_layout()
        self.fill_combos(0, -1)
        self.next_is_b = True
        self.update_status()
        self.say(message)

    # =====================================================================
    #  Thao tác trên đồ thị
    # =====================================================================
    def load_sample(self):
        self.set_graph(make_sample_graph(),
                       "Đã nạp dữ liệu mẫu gồm 14 người. Bấm vào hai người trên đồ thị hoặc chọn trong danh sách rồi dùng các chức năng.")

    def random_small(self):
        self.set_graph(scale_free_graph(30, 2, random.randrange(1_000_000)),
                       "Đã sinh đồ thị ngẫu nhiên 30 người (mô hình phi tỷ lệ).")

    def add_user(self):
        name = self.var_name.get().strip()
        if not name:
            self.say("Hãy nhập tên người dùng.")
            return
        keep_a, keep_b = self.A, self.B
        uid = self.g.add_user(name)
        self.var_name.set("")
        self.fill_combos(keep_a, keep_b)
        self.update_status()
        self.say(f"Đã thêm {self.who(uid)}.")

    def do_friend(self, add):
        if not self.need_two():
            return
        a, b = self.A, self.B
        ok = self.g.add_friend(a, b) if add else self.g.remove_friend(a, b)
        self.clear_highlights()
        self.update_status()
        if add:
            self.say(f"{self.who(a)} và {self.who(b)} đã trở thành bạn bè." if ok
                     else "Không thực hiện được: hai người đã là bạn bè.")
        else:
            self.say(f"Đã hủy kết bạn giữa {self.who(a)} và {self.who(b)}." if ok else "Hai người này chưa là bạn bè.")

    def do_mutual(self):
        if not self.need_two():
            return
        self.clear_highlights()
        a, b = self.A, self.B
        m = self.g.mutual_friends(a, b)
        self.canvas.mutual = set(m)
        if m:
            self.say(f"{self.who(a)} và {self.who(b)} có {len(m)} bạn chung: " + ", ".join(self.who(x) for x in m))
        else:
            self.say(f"{self.who(a)} và {self.who(b)} không có bạn chung.")

    def do_recommend(self):
        if not self.need_one():
            return
        self.clear_highlights()
        a, aa = self.A, self.var_aa.get()
        recs = self.g.recommend(a, 5, aa)
        self.canvas.recs = {r.user_id: r.mutual_count for r in recs}
        if not recs:
            self.say(f"Chưa có gợi ý nào cho {self.who(a)} (chưa có bạn, hoặc đã kết bạn với mọi người trong vòng bạn của bạn).")
            return
        lines = [f"Gợi ý kết bạn cho {self.who(a)}" + (" (xếp hạng Adamic-Adar):" if aa else " (xếp hạng theo số bạn chung):")]
        for r in recs:
            via = ", ".join(self.g.name_of(x) for x in self.g.mutual_friends(a, r.user_id))
            lines.append(f"  • {self.who(r.user_id)}: {r.mutual_count} bạn chung"
                         + (f", điểm {r.score:.2f}" if aa else "") + f" (qua {via})")
        self.say(*lines)

    def do_distance(self):
        if not self.need_two(allow_same=True):
            return
        self.clear_highlights()
        a, b = self.A, self.B
        path = self.g.shortest_path(a, b)
        if path is None:
            self.say(f"{self.who(a)} và {self.who(b)} không có đường nối (không liên thông).")
            return
        self.canvas.path = path
        dfs = self.g.dfs_path_length(a, b)
        self.say(f"Khoảng cách {self.who(a)} → {self.who(b)}: {len(path) - 1} bậc quan hệ (BFS).",
                 "Đường đi: " + " → ".join(self.g.name_of(x) for x in path),
                 f"Để so sánh: DFS tìm được đường dài {dfs} bậc, không đảm bảo ngắn nhất.")

    # =====================================================================
    #  Thực nghiệm hiệu năng (chạy ở luồng nền để cửa sổ không bị đơ)
    # =====================================================================
    @staticmethod
    def parse_sizes(text):
        sizes = set()
        for part in re.split(r"[,; ]+", text.strip()):
            part = part.replace(".", "")
            if part.isdigit() and int(part) >= 10:
                sizes.add(min(int(part), 300_000))
        return sorted(sizes)

    def run_bench(self):
        sizes = self.parse_sizes(self.var_sizes.get())
        if not sizes:
            messagebox.showwarning("Thiếu dữ liệu", "Hãy nhập ít nhất một số đỉnh hợp lệ (từ 10 trở lên).")
            return
        try:
            deg = min(max(int(self.var_deg.get()), 2), 100)
        except ValueError:
            deg = 10
        kinds = (["Random"] if self.var_random.get() else []) + (["ScaleFree"] if self.var_scale.get() else [])
        if not kinds:
            messagebox.showwarning("Thiếu dữ liệu", "Hãy chọn ít nhất một loại đồ thị.")
            return

        self.btn_run.config(state="disabled")
        self.btn_csv.config(state="disabled")
        self.results.clear()
        self.tree.delete(*self.tree.get_children())
        self.refresh_chart()
        self._bench_queue = q = queue.Queue()

        def worker():
            try:
                for kind in kinds:
                    for n in sizes:
                        q.put(("progress", f"Đang chạy: {'ngẫu nhiên' if kind == 'Random' else 'phi tỷ lệ'}, {n:,} đỉnh..."))
                        q.put(("result", benchmark.run(kind, n, deg)))
                q.put(("done", None))
            except Exception as ex:  # noqa: BLE001 - hiển thị lỗi cho người dùng
                q.put(("error", str(ex)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self.poll_bench)

    def poll_bench(self):
        finished = False
        try:
            while True:
                kind, val = self._bench_queue.get_nowait()
                if kind == "progress":
                    self.lbl_progress.config(text=val)
                elif kind == "result":
                    self.results.append(val)
                    self.add_row(val)
                    self.refresh_chart()
                elif kind == "done":
                    self.lbl_progress.config(text="Hoàn tất.")
                    finished = True
                elif kind == "error":
                    messagebox.showerror("Lỗi khi chạy thực nghiệm", val)
                    self.lbl_progress.config(text="")
                    finished = True
        except queue.Empty:
            pass
        if finished:
            self.btn_run.config(state="normal")
            self.btn_csv.config(state="normal" if self.results else "disabled")
        else:
            self.after(100, self.poll_bench)

    def add_row(self, r):
        self.tree.insert("", "end", values=(
            "Ngẫu nhiên" if r.type == "Random" else "Phi tỷ lệ", f"{r.n:,}", f"{r.e:,}", f"{r.build_ms:.0f}",
            f"{r.mem_mb:.1f}", f"{r.rec_ms:.3f}", f"{r.rec_aa_ms:.3f}", f"{r.bfs_ms:.3f}", f"{r.dfs_ms:.3f}",
            f"{r.bfs_len:.2f}", f"{r.dfs_len:.1f}", f"{r.mutual_us:.2f}"))

    def refresh_chart(self):
        cats = sorted({r.n for r in self.results})
        name, getter = METRICS[max(0, self.cb_metric.current())]
        series = []
        for kind, label, color in (("Random", "Đồ thị ngẫu nhiên", NODE), ("ScaleFree", "Đồ thị phi tỷ lệ", COL_B)):
            if not any(r.type == kind for r in self.results):
                continue
            vals = []
            for n in cats:
                r = next((x for x in self.results if x.type == kind and x.n == n), None)
                vals.append(getter(r) if r else None)
            series.append((label, color, vals))
        self.chart.set_data(name, [f"{n:,}" for n in cats], series)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="ket_qua_thuc_nghiem.csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            benchmark.save_csv(self.results, path)
            self.lbl_progress.config(text="Đã xuất CSV.")

    # =====================================================================
    #  Kiểm thử
    # =====================================================================
    def run_tests(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tests.run_all()
        self.txt_tests.config(state="normal")
        self.txt_tests.delete("1.0", "end")
        self.txt_tests.insert("1.0", buf.getvalue())
        self.txt_tests.config(state="disabled")
