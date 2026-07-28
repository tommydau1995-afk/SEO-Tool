
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

APP_VERSION = "2.0.0"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"SEO AI Studio V{APP_VERSION}")
        self.geometry("1100x700")
        self.minsize(900, 600)

        header = ttk.Frame(self, padding=14)
        header.pack(fill="x")
        ttk.Label(header, text="SEO AI Studio V2", font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Label(header, text="Windows Desktop Edition").pack(side="left", padx=12)

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._add_tab(tabs, "Dashboard",
                      "Tổng quan dự án SEO, tiến độ nội dung và trạng thái website.")
        self._add_tab(tabs, "Website Audit",
                      "Crawl website, kiểm tra Title, Meta, H1, Canonical, ALT và lỗi index.")
        self._add_tab(tabs, "AI Strategy",
                      "Phân tích doanh nghiệp, content gap, topical authority và ưu tiên SEO.")
        self._add_tab(tabs, "Content Plan",
                      "Tạo kế hoạch nội dung theo từ khóa, search intent và funnel.")
        self._add_tab(tabs, "AI Writer",
                      "Viết bài SEO, FAQ, schema, meta description và đề xuất internal link.")
        self._add_tab(tabs, "WordPress",
                      "Kết nối WordPress và gửi nội dung đã duyệt dưới dạng Draft.")
        self._add_tab(tabs, "Settings",
                      "Cấu hình OpenAI API key, model và thông tin kết nối.")

        footer = ttk.Frame(self, padding=10)
        footer.pack(fill="x")
        ttk.Label(
            footer,
            text="V2 shell đã sẵn sàng. Các module backend được tích hợp theo từng bản cập nhật."
        ).pack(side="left")
        ttk.Button(
            footer, text="Hướng dẫn",
            command=lambda: webbrowser.open("https://github.com/")
        ).pack(side="right")

    def _add_tab(self, notebook, title, description):
        frame = ttk.Frame(notebook, padding=20)
        notebook.add(frame, text=title)
        ttk.Label(frame, text=title, font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(frame, text=description, wraplength=800).pack(anchor="w", pady=(8, 18))
        ttk.Button(
            frame,
            text=f"Mở module {title}",
            command=lambda t=title: messagebox.showinfo(
                t, f"Module {t} đã được đăng ký trong SEO AI Studio V2."
            )
        ).pack(anchor="w")

if __name__ == "__main__":
    App().mainloop()
