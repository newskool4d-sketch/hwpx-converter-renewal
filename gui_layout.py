from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui_theme import (
    ACCENT,
    ACCENT_DARK,
    ACCENT_DIM,
    BG,
    BORDER,
    CARD,
    EDITABLE_FORMATTING_NOTICE,
    FONT,
    FONT_BOLD,
    FONT_SMALL,
    FONT_TITLE,
    GREEN,
    LOG_BG,
    MUTED,
    RED,
    TEXT,
    TROUGH,
    YELLOW,
)


def configure_styles(app) -> None:
    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=FONT)
    style.configure("Card.TFrame", background=CARD)
    style.configure("Bg.TFrame", background=BG)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
    style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=FONT_SMALL)
    style.configure("CardHead.TLabel", background=CARD, foreground=TEXT, font=FONT_BOLD)
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=FONT_SMALL)
    style.configure("Status.TLabel", background=BG, foreground=MUTED, font=FONT)
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground="white",
        font=FONT_BOLD,
        padding=(20, 9),
        borderwidth=0,
        focuscolor=ACCENT,
    )
    style.map(
        "Primary.TButton",
        background=[("disabled", ACCENT_DIM), ("active", ACCENT_DARK), ("pressed", ACCENT_DARK)],
    )
    style.configure(
        "Secondary.TButton",
        background=CARD,
        foreground=TEXT,
        font=FONT,
        padding=(12, 6),
        borderwidth=1,
        bordercolor=BORDER,
        focuscolor=CARD,
        relief="solid",
    )
    style.map(
        "Secondary.TButton",
        background=[("active", "gray95"), ("pressed", "gray90")],
        bordercolor=[("active", ACCENT)],
    )
    style.configure("TCheckbutton", background=CARD, foreground=TEXT, font=FONT, focuscolor=CARD)
    style.map("TCheckbutton", background=[("active", CARD)])
    style.configure(
        "Accent.Horizontal.TProgressbar",
        background=ACCENT,
        troughcolor=TROUGH,
        borderwidth=0,
        thickness=8,
    )
    style.configure(
        "Vertical.TScrollbar",
        background=BORDER,
        troughcolor=CARD,
        borderwidth=0,
        arrowsize=12,
    )


def make_card(parent):
    return tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1, bd=0)


def build_ui(app) -> None:
    root = ttk.Frame(app, style="Bg.TFrame", padding=(18, 14, 18, 12))
    root.pack(fill=tk.BOTH, expand=True)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(2, weight=3)
    root.rowconfigure(6, weight=2)
    header = ttk.Frame(root, style="Bg.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    ttk.Label(header, text="HWPX 변환기", style="Title.TLabel").pack(anchor="w")
    ttk.Label(
        header,
        text="md · txt · docx · html · csv · xlsx · pdf  →  한글 HWPX",
        style="Sub.TLabel",
    ).pack(anchor="w", pady=(2, 0))
    file_card = make_card(root)
    file_card.grid(row=1, column=0, rowspan=2, sticky="nsew")
    file_card.columnconfigure(0, weight=1)
    file_card.rowconfigure(1, weight=1)
    file_head = tk.Frame(file_card, bg=CARD)
    file_head.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))
    ttk.Label(file_head, text="변환할 파일", style="CardHead.TLabel").pack(side=tk.LEFT)
    ttk.Label(file_head, textvariable=app.count_text, style="CardMuted.TLabel").pack(side=tk.LEFT, padx=(8, 0))
    app.clear_button = ttk.Button(file_head, text="목록 비우기", style="Secondary.TButton", command=app.clear_files)
    app.clear_button.pack(side=tk.RIGHT)
    app.remove_button = ttk.Button(file_head, text="선택 삭제", style="Secondary.TButton", command=app._remove_selected)
    app.remove_button.pack(side=tk.RIGHT, padx=(0, 6))
    app.add_button = ttk.Button(file_head, text="파일 추가", style="Secondary.TButton", command=app.select_files)
    app.add_button.pack(side=tk.RIGHT, padx=(0, 6))
    app.list_wrap = tk.Frame(file_card, bg=CARD)
    app.list_wrap.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
    app.list_wrap.columnconfigure(0, weight=1)
    app.list_wrap.rowconfigure(0, weight=1)
    app.file_list = tk.Listbox(
        app.list_wrap,
        height=9,
        activestyle="none",
        selectmode=tk.EXTENDED,
        bg=LOG_BG,
        fg=TEXT,
        font=FONT,
        selectbackground=ACCENT,
        selectforeground="white",
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
    )
    app.file_list.grid(row=0, column=0, sticky="nsew")
    app.file_list.bind("<Delete>", lambda e: app._remove_selected())
    app.file_list.bind("<BackSpace>", lambda e: app._remove_selected())
    list_scroll = ttk.Scrollbar(app.list_wrap, orient="vertical", command=app.file_list.yview)
    list_scroll.grid(row=0, column=1, sticky="ns", padx=(4, 0))
    app.file_list.configure(yscrollcommand=list_scroll.set)
    out_card = make_card(root)
    out_card.grid(row=3, column=0, sticky="ew", pady=(12, 0))
    out_card.columnconfigure(1, weight=1)
    ttk.Label(out_card, text="저장 설정", style="CardHead.TLabel").grid(
        row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 8)
    )
    tk.Label(out_card, text="저장 폴더", bg=CARD, fg=MUTED, font=FONT).grid(
        row=1, column=0, sticky="w", padx=(14, 8)
    )
    app.out_entry = tk.Entry(
        out_card,
        textvariable=app.output_dir,
        bg=LOG_BG,
        fg=TEXT,
        font=FONT,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
    )
    app.out_entry.grid(row=1, column=1, sticky="ew", ipady=5)
    app.output_browse_button = ttk.Button(
        out_card, text="찾기", style="Secondary.TButton", command=app.select_output_dir
    )
    app.output_browse_button.grid(row=1, column=2, padx=(8, 14))
    opts = tk.Frame(out_card, bg=CARD)
    opts.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(10, 12))
    app.empty_output_check = ttk.Checkbutton(
        opts, text="저장 폴더 비우기(앱 관리 파일만)", variable=app.empty_output_folder
    )
    app.empty_output_check.pack(side=tk.LEFT, padx=(0, 18))
    app.insert_end_check = ttk.Checkbutton(
        opts, text="문서 끝에 '끝' 자동 삽입 (공문서)", variable=app.insert_end_mark
    )
    app.insert_end_check.pack(side=tk.LEFT)
    pdf_frame = tk.Frame(out_card, bg=CARD)
    pdf_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 12))
    tk.Label(pdf_frame, text="PDF 방식", bg=CARD, fg=MUTED, font=FONT_SMALL).pack(side=tk.LEFT)
    app.pdf_layout_radio = ttk.Radiobutton(
        pdf_frame, text="레이아웃 보존(기본)", value="layout", variable=app.pdf_mode
    )
    app.pdf_layout_radio.pack(side=tk.LEFT, padx=(12, 8))
    app.pdf_editable_radio = ttk.Radiobutton(
        pdf_frame, text="편집 가능", value="editable", variable=app.pdf_mode
    )
    app.pdf_editable_radio.pack(side=tk.LEFT)
    ttk.Label(pdf_frame, text=EDITABLE_FORMATTING_NOTICE, style="CardMuted.TLabel").pack(
        side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True
    )
    if not app.capabilities.pdf_enabled:
        app.pdf_mode.set("layout")
        app.pdf_layout_radio.configure(state="disabled")
        app.pdf_editable_radio.configure(state="disabled")
    action = ttk.Frame(root, style="Bg.TFrame")
    action.grid(row=4, column=0, sticky="ew", pady=(14, 0))
    action.columnconfigure(0, weight=1)
    app.progress = ttk.Progressbar(action, mode="determinate", style="Accent.Horizontal.TProgressbar")
    app.progress.grid(row=0, column=0, sticky="ew", padx=(0, 14))
    app.convert_button = ttk.Button(action, text="변환 시작", style="Primary.TButton", command=app.start_conversion)
    app.convert_button.grid(row=0, column=1)
    ttk.Label(root, textvariable=app.status, style="Status.TLabel").grid(
        row=5, column=0, sticky="w", pady=(8, 6)
    )
    log_card = make_card(root)
    log_card.grid(row=6, column=0, sticky="nsew")
    log_card.columnconfigure(0, weight=1)
    log_card.rowconfigure(1, weight=1)
    ttk.Label(log_card, text="진행 로그", style="CardHead.TLabel").grid(
        row=0, column=0, sticky="w", padx=14, pady=(10, 6)
    )
    log_wrap = tk.Frame(log_card, bg=CARD)
    log_wrap.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
    log_wrap.columnconfigure(0, weight=1)
    log_wrap.rowconfigure(0, weight=1)
    app.log = tk.Text(
        log_wrap,
        height=7,
        wrap="word",
        state="disabled",
        bg=LOG_BG,
        fg=TEXT,
        font=FONT_SMALL,
        relief="flat",
        highlightthickness=1,
        highlightbackground=BORDER,
        padx=8,
        pady=6,
        spacing1=2,
    )
    app.log.grid(row=0, column=0, sticky="nsew")
    app.log.tag_configure("ok", foreground=GREEN)
    app.log.tag_configure("info", foreground=ACCENT)
    app.log.tag_configure("warn", background=YELLOW, foreground=TEXT)
    app.log.tag_configure("err", foreground=RED)
    app.log.tag_configure("muted", foreground=MUTED)
    log_scroll = ttk.Scrollbar(log_wrap, orient="vertical", command=app.log.yview)
    log_scroll.grid(row=0, column=1, sticky="ns", padx=(4, 0))
    app.log.configure(yscrollcommand=log_scroll.set)
