# Gợi ý kết bạn trên mạng xã hội (Python 3)

Chạy giao diện đồ họa (tkinter, có sẵn trong Python trên Windows và macOS):

    python main.py

Chạy giao diện dòng lệnh:

    python main.py --cli

Chạy riêng bộ kiểm thử (25 test case):

    python tests.py

Chạy riêng thực nghiệm hiệu năng (kết quả lưu vào ket_qua_thuc_nghiem.csv):

    python -c "import benchmark; benchmark.run_all([1000, 10000, 50000, 100000])"

Cấu trúc:
- social_graph.py     Đồ thị danh sách kề: thêm người, kết bạn, hủy bạn, bạn chung, gợi ý, BFS, DFS
- graph_generator.py  Sinh đồ thị ngẫu nhiên và đồ thị phi tỷ lệ (Barabási–Albert)
- benchmark.py        Đo thời gian (perf_counter) và bộ nhớ (tracemalloc), xuất CSV
- tests.py            Kiểm thử dữ liệu nhỏ và trường hợp cận biên
- sample_data.py      Dữ liệu mẫu 14 người
- gui_app.py          Giao diện đồ họa (3 tab: Thao tác, Thực nghiệm hiệu năng, Kiểm thử)
- cli_app.py          Giao diện dòng lệnh
- main.py             Điểm vào chương trình
