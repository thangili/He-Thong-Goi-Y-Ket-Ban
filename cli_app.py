"""Giao diện dòng lệnh (CLI)."""
import benchmark
import tests
from sample_data import make_sample_graph


def run(input_fn=input):
    g = make_sample_graph()

    def label(uid):
        return f"{g.name_of(uid)} (#{uid})"

    def read_id(prompt):
        try:
            uid = int(input_fn(prompt))
        except ValueError:
            return -1
        return uid if g.exists(uid) else -1

    def two_users():
        a = read_id("Nhập id người thứ nhất: ")
        b = read_id("Nhập id người thứ hai: ")
        if a < 0 or b < 0:
            print("Id không tồn tại.")
            return None
        return a, b

    while True:
        print("\n===== MẠNG XÃ HỘI - GỢI Ý KẾT BẠN =====")
        print(f"({g.user_count} người dùng, {g.edge_count} quan hệ bạn bè)")
        print("1. Thêm người dùng        6. Khoảng cách (BFS)")
        print("2. Kết bạn                7. Hiển thị danh sách kề")
        print("3. Hủy bạn                8. Chạy bộ kiểm thử")
        print("4. Tìm bạn chung          9. Thực nghiệm hiệu năng")
        print("5. Gợi ý kết bạn          0. Thoát")
        choice = input_fn("Chọn: ").strip()

        if choice == "1":
            uid = g.add_user(input_fn("Tên người dùng: "))
            print(f"Đã thêm {label(uid)}.")
        elif choice == "2":
            p = two_users()
            if p:
                print("Đã kết bạn." if g.add_friend(*p) else "Không thực hiện được (đã là bạn hoặc chọn trùng).")
        elif choice == "3":
            p = two_users()
            if p:
                print("Đã hủy kết bạn." if g.remove_friend(*p) else "Hai người chưa là bạn.")
        elif choice == "4":
            p = two_users()
            if p:
                m = g.mutual_friends(*p)
                print("Không có bạn chung." if not m else f"{len(m)} bạn chung: " + ", ".join(label(x) for x in m))
        elif choice == "5":
            u = read_id("Nhập id người dùng: ")
            if u < 0:
                print("Id không tồn tại.")
                continue
            aa = input_fn("Dùng trọng số Adamic-Adar? (y/N): ").strip().lower() == "y"
            recs = g.recommend(u, 5, aa)
            if not recs:
                print("Chưa có gợi ý (người này chưa có bạn hoặc đã kết bạn với mọi bạn của bạn).")
            for r in recs:
                print(f"- {label(r.user_id)}: {r.mutual_count} bạn chung" + (f", điểm {r.score:.2f}" if aa else ""))
        elif choice == "6":
            p = two_users()
            if p:
                path = g.shortest_path(*p)
                if path is None:
                    print("Hai người không liên thông.")
                else:
                    print(f"Khoảng cách: {len(path) - 1} bậc")
                    print(" -> ".join(label(x) for x in path))
        elif choice == "7":
            for i in range(g.user_count):
                print(f"{label(i)}: " + ", ".join(g.name_of(f) for f in sorted(g.friends_of(i))))
        elif choice == "8":
            tests.run_all()
        elif choice == "9":
            print("Bậc trung bình = 10. Đang chạy, vui lòng đợi...\n")
            benchmark.run_all([1000, 10000, 50000, 100000], 10, "ket_qua_thuc_nghiem.csv")
        elif choice == "0":
            return
        else:
            print("Lựa chọn không hợp lệ.")
