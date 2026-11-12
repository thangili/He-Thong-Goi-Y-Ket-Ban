"""Điểm vào chương trình.

    python main.py          mở giao diện đồ họa (tkinter)
    python main.py --cli    chạy giao diện dòng lệnh
"""
import sys


def main():
    if "--cli" in sys.argv:
        import cli_app
        cli_app.run()
        return
    try:
        from gui_app import App
    except ImportError as ex:
        print("Không mở được giao diện đồ họa:", ex)
        print("Trên Linux hãy cài tkinter (sudo apt install python3-tk) hoặc chạy: python main.py --cli")
        return
    App().mainloop()


if __name__ == "__main__":
    main()
