from __future__ import annotations

import asyncio
import json
import sys
import threading
from pathlib import Path
from tkinter import BOTH, END, HORIZONTAL, LEFT, RIGHT, VERTICAL, BooleanVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk
import tkinter as tk

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from constants import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, NOTEBOOK_EXTENSIONS, get_file_upload_policy
from services import gemma_analyzer
from services.notebook_loader import NotebookParseError, prepare_notebook_scan
from services.scanner import run_scan


class SafePromptGui(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SafePrompt Guard - Local Gemma")
        self.geometry("1240x760")
        self.minsize(980, 640)

        self.use_gemma = BooleanVar(value=True)
        self.status_text = StringVar(value="로컬 Gemma 상태 확인 중")
        self.file_label = StringVar(value="붙여넣기 입력")
        self.result_summary = StringVar(value="검사 결과 대기")
        self.current_file: Path | None = None
        self.last_result = None

        self._configure_theme()
        self._build_layout()
        self._refresh_gemma_status()

    def _configure_theme(self) -> None:
        self.configure(bg="#060a12")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background="#0d1424", foreground="#e8eef7", fieldbackground="#131d33")
        style.configure("TFrame", background="#060a12")
        style.configure("Panel.TFrame", background="#0d1424")
        style.configure("TLabel", background="#060a12", foreground="#e8eef7")
        style.configure("Muted.TLabel", background="#060a12", foreground="#8b9cb8")
        style.configure("Panel.TLabel", background="#0d1424", foreground="#e8eef7")
        style.configure("Title.TLabel", background="#060a12", foreground="#e8eef7", font=("TkDefaultFont", 18, "bold"))
        style.configure("Accent.TButton", background="#22d3ee", foreground="#061018", borderwidth=0, padding=(14, 8))
        style.map("Accent.TButton", background=[("active", "#67e8f9")])
        style.configure("TButton", background="#131d33", foreground="#e8eef7", borderwidth=1, padding=(12, 7))
        style.configure("TCheckbutton", background="#060a12", foreground="#e8eef7")
        style.configure("Treeview", background="#0f1729", foreground="#e8eef7", fieldbackground="#0f1729", borderwidth=0)
        style.configure("Treeview.Heading", background="#131d33", foreground="#8b9cb8")
        style.configure("TNotebook", background="#0d1424", borderwidth=0)
        style.configure("TNotebook.Tab", background="#131d33", foreground="#8b9cb8", padding=(12, 7))
        style.map("TNotebook.Tab", background=[("selected", "#0f1729")], foreground=[("selected", "#e8eef7")])

    def _build_layout(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 14))
        title_box = ttk.Frame(header)
        title_box.pack(side=LEFT, fill="x", expand=True)
        ttk.Label(title_box, text="SafePrompt Guard", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="로컬 Ollama + Gemma로 외부 AI 입력 전 민감정보를 검사합니다.",
            style="Muted.TLabel",
        ).pack(anchor="w")

        ttk.Label(header, textvariable=self.status_text, style="Muted.TLabel").pack(side=RIGHT, padx=(12, 0))
        ttk.Button(header, text="상태 새로고침", command=self._refresh_gemma_status).pack(side=RIGHT)

        body = ttk.PanedWindow(root, orient=HORIZONTAL)
        body.pack(fill=BOTH, expand=True)

        left = ttk.Frame(body, style="Panel.TFrame", padding=12)
        right = ttk.Frame(body, style="Panel.TFrame", padding=12)
        body.add(left, weight=3)
        body.add(right, weight=2)

        toolbar = ttk.Frame(left, style="Panel.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar, text="파일 열기", command=self._open_file).pack(side=LEFT)
        ttk.Button(toolbar, text="입력 지우기", command=self._clear_input).pack(side=LEFT, padx=(8, 0))
        ttk.Checkbutton(toolbar, text="Gemma 사용", variable=self.use_gemma).pack(side=LEFT, padx=(14, 0))
        ttk.Button(toolbar, text="검사 실행", style="Accent.TButton", command=self._scan_async).pack(side=RIGHT)

        ttk.Label(left, textvariable=self.file_label, style="Panel.TLabel").pack(anchor="w")
        input_frame = ttk.Frame(left, style="Panel.TFrame")
        input_frame.pack(fill=BOTH, expand=True, pady=(8, 0))
        self.input_text = tk.Text(
            input_frame,
            wrap="word",
            bg="#0f1729",
            fg="#e8eef7",
            insertbackground="#22d3ee",
            relief="flat",
            padx=12,
            pady=12,
        )
        self.input_text.pack(side=LEFT, fill=BOTH, expand=True)
        input_scroll = ttk.Scrollbar(input_frame, orient=VERTICAL, command=self.input_text.yview)
        input_scroll.pack(side=RIGHT, fill="y")
        self.input_text.configure(yscrollcommand=input_scroll.set)

        ttk.Label(right, textvariable=self.result_summary, style="Panel.TLabel").pack(anchor="w")
        self.findings = ttk.Treeview(
            right,
            columns=("severity", "line", "source"),
            show="tree headings",
            height=10,
        )
        self.findings.heading("#0", text="탐지 항목")
        self.findings.heading("severity", text="위험도")
        self.findings.heading("line", text="라인")
        self.findings.heading("source", text="소스")
        self.findings.column("#0", width=190)
        self.findings.column("severity", width=70, anchor="center")
        self.findings.column("line", width=60, anchor="center")
        self.findings.column("source", width=70, anchor="center")
        self.findings.pack(fill="x", pady=(8, 10))
        self.findings.bind("<<TreeviewSelect>>", self._show_finding_detail)

        self.detail_text = tk.Text(
            right,
            height=5,
            wrap="word",
            bg="#0f1729",
            fg="#c7d2e5",
            relief="flat",
            padx=10,
            pady=10,
        )
        self.detail_text.pack(fill="x", pady=(0, 10))
        self.detail_text.configure(state="disabled")

        tabs = ttk.Notebook(right)
        tabs.pack(fill=BOTH, expand=True)
        self.masked_text = self._tab_text(tabs, "마스킹 결과")
        self.prompt_text = self._tab_text(tabs, "안전 프롬프트")

        actions = ttk.Frame(right, style="Panel.TFrame")
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="마스킹 결과 복사", command=lambda: self._copy_widget(self.masked_text)).pack(side=LEFT)
        ttk.Button(actions, text="안전 프롬프트 복사", command=lambda: self._copy_widget(self.prompt_text)).pack(side=LEFT, padx=(8, 0))
        ttk.Button(actions, text="마스킹 노트북 저장", command=self._save_masked_notebook).pack(side=RIGHT)

    def _tab_text(self, tabs: ttk.Notebook, label: str) -> tk.Text:
        frame = ttk.Frame(tabs, style="Panel.TFrame", padding=0)
        text = tk.Text(
            frame,
            wrap="word",
            bg="#0f1729",
            fg="#e8eef7",
            insertbackground="#22d3ee",
            relief="flat",
            padx=12,
            pady=12,
        )
        text.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(frame, orient=VERTICAL, command=text.yview)
        scroll.pack(side=RIGHT, fill="y")
        text.configure(yscrollcommand=scroll.set)
        tabs.add(frame, text=label)
        return text

    def _refresh_gemma_status(self) -> None:
        self.status_text.set("로컬 Gemma 상태 확인 중")

        def worker() -> None:
            status = asyncio.run(gemma_analyzer.local_gemma_status())
            if status["gemma_available"]:
                message = f"로컬 Gemma 연결됨 ({gemma_analyzer.DEFAULT_MODEL})"
            elif status["ollama_available"]:
                message = f"Ollama 연결됨, {gemma_analyzer.DEFAULT_MODEL} 모델 없음"
            else:
                message = "Ollama 대기 중 (127.0.0.1:11434)"
            self.after(0, lambda: self.status_text.set(message))

        threading.Thread(target=worker, daemon=True).start()

    def _open_file(self) -> None:
        policy = get_file_upload_policy()
        path = filedialog.askopenfilename(
            title="검사할 파일 선택",
            filetypes=[("Allowed files", " ".join(f"*{ext}" for ext in policy["extensions"])), ("All files", "*.*")],
        )
        if not path:
            return
        file_path = Path(path)
        ext = file_path.suffix.lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            messagebox.showerror("지원하지 않는 파일", f"허용 확장자: {policy['extensions_sorted_display']}")
            return
        if file_path.stat().st_size > MAX_UPLOAD_BYTES:
            messagebox.showerror("파일 크기 초과", f"파일은 최대 {MAX_UPLOAD_BYTES // 1024 // 1024}MB까지 지원합니다.")
            return
        raw = file_path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp949", errors="replace")
        self.current_file = file_path
        self.file_label.set(str(file_path))
        self.input_text.delete("1.0", END)
        self.input_text.insert("1.0", text)

    def _clear_input(self) -> None:
        self.current_file = None
        self.file_label.set("붙여넣기 입력")
        self.input_text.delete("1.0", END)

    def _scan_async(self) -> None:
        text = self.input_text.get("1.0", END).strip()
        if not text:
            messagebox.showinfo("입력 필요", "검사할 텍스트나 파일을 입력하세요.")
            return
        self.result_summary.set("검사 중")
        self._clear_result_widgets()

        def worker() -> None:
            try:
                result = asyncio.run(self._scan_text(text))
                self.after(0, lambda: self._render_result(result))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("검사 실패", str(exc)))
                self.after(0, lambda: self.result_summary.set("검사 실패"))

        threading.Thread(target=worker, daemon=True).start()

    async def _scan_text(self, text: str):
        notebook_ctx = None
        scan_text = text
        filename = self.current_file.name if self.current_file else None
        ext = self.current_file.suffix.lower() if self.current_file else ""
        if ext in NOTEBOOK_EXTENSIONS:
            try:
                scan_text, nb, segments = prepare_notebook_scan(text)
                notebook_ctx = (nb, segments)
            except NotebookParseError as exc:
                raise ValueError(str(exc)) from exc
        return await run_scan(
            scan_text,
            use_gemma=self.use_gemma.get(),
            filename=filename,
            notebook_ctx=notebook_ctx,
        )

    def _render_result(self, result) -> None:
        self.last_result = result
        self.result_summary.set(f"{result.risk_level} · 점수 {result.risk_score} · 탐지 {len(result.findings)}건")
        for idx, finding in enumerate(result.findings):
            self.findings.insert(
                "",
                END,
                iid=str(idx),
                text=finding.type,
                values=(finding.severity, finding.line or "-", finding.source),
            )
        self._replace_text(self.masked_text, result.masked_text)
        self._replace_text(self.prompt_text, result.safe_prompt)

    def _show_finding_detail(self, _event=None) -> None:
        selection = self.findings.selection()
        if not selection or not self.last_result:
            return
        finding = self.last_result.findings[int(selection[0])]
        detail = "\n".join(
            [
                f"유형: {finding.type}",
                f"근거: {finding.reason or '-'}",
                f"조치: {finding.action or '-'}",
                f"인용: {finding.exact_quote or finding.value}",
            ]
        )
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", END)
        self.detail_text.insert("1.0", detail)
        self.detail_text.configure(state="disabled")

    def _clear_result_widgets(self) -> None:
        self.last_result = None
        for item in self.findings.get_children():
            self.findings.delete(item)
        self._replace_text(self.masked_text, "")
        self._replace_text(self.prompt_text, "")
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", END)
        self.detail_text.configure(state="disabled")

    def _replace_text(self, widget: tk.Text, content: str) -> None:
        widget.delete("1.0", END)
        widget.insert("1.0", content)

    def _copy_widget(self, widget: tk.Text) -> None:
        content = widget.get("1.0", END).strip()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.status_text.set("클립보드에 복사됨")

    def _save_masked_notebook(self) -> None:
        if not self.last_result or not self.last_result.masked_notebook_json:
            messagebox.showinfo("저장할 노트북 없음", ".ipynb 검사 결과가 있을 때 사용할 수 있습니다.")
            return
        path = filedialog.asksaveasfilename(
            title="마스킹 노트북 저장",
            defaultextension=".ipynb",
            filetypes=[("Jupyter Notebook", "*.ipynb")],
            initialfile="masked_notebook.ipynb",
        )
        if not path:
            return
        Path(path).write_text(self.last_result.masked_notebook_json, encoding="utf-8")
        self.status_text.set(f"저장 완료: {path}")


def _self_test() -> None:
    sample = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature"
    result = asyncio.run(run_scan(sample, use_gemma=False))
    assert result.findings
    assert "[MASKED" in result.masked_text
    print("desktop native gui self-test passed")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
    else:
        app = SafePromptGui()
        app.mainloop()
