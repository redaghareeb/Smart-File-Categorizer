I've a software project as a product named "code" with this tree structure:

```text
code/
├── BUILD_GUIDE.md
├── README.md
├── SmartDocCategorizer.spec
├── USER_MANUAL.md
├── app.py
├── build.bat
├── build_installer.bat
├── categories.py
├── cleanup_dist.py
├── completecode.MD
├── engine.py
├── i18n.py
├── icon.ico
├── installer.iss
├── logo.png
├── requirements.txt
├── setup_ffmpeg.py
└── transcribe.py
```

Here are the contents of the files:

### File: `app.py`
The content of `app.py` is:
```py
"""
Smart File Categorizer — Desktop App v1.0
Bilingual (EN/AR) | Dynamic Categories | Role Presets
"""
import os, sys, json, threading

# FIX: Prevent silent hard crashes when PyTorch (OCR) and CTranslate2 (Whisper) load together
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from pathlib import Path
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, END
from PIL import Image # <--- ADD THIS

# --- ADD THIS HELPER FUNCTION ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    import engine
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import engine

from i18n import t, set_lang, get_lang
import categories as cat_mgr

FONT = "Segoe UI"
ACCENT, ACCENT_H = "#2563EB", "#1D4ED8"
SUCCESS, WARN, DANGER = "#16A34A", "#F59E0B", "#DC2626"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ═══════════ RTL HELPERS ═══════════
# These return correct alignment/direction based on current language.
# Arabic = RTL: sidebar right, text anchored east, packs reversed.

def _rtl() -> bool:
    """Is current language RTL?"""
    return get_lang() == "ar"

def _anchor():
    """Text anchor: 'e' for RTL, 'w' for LTR."""
    return "e" if _rtl() else "w"

def _sticky():
    """Grid sticky for text start: 'e' for RTL, 'w' for LTR."""
    return "e" if _rtl() else "w"

def _sticky_full():
    """Grid sticky for full-width text: 'ew' always."""
    return "ew"

def _side():
    """Pack side for start: 'right' for RTL, 'left' for LTR."""
    return "right" if _rtl() else "left"

def _side_end():
    """Pack side for end: 'left' for RTL, 'right' for LTR."""
    return "left" if _rtl() else "right"

def _padx_start(outer=0, inner=0):
    """Padx tuple for start-aligned items."""
    return (inner, outer) if _rtl() else (outer, inner)

def _justify():
    """Text justify: 'right' for RTL, 'left' for LTR."""
    return "right" if _rtl() else "left"

def _sidebar_col():
    """Column for sidebar: 2 (right) for RTL, 0 (left) for LTR."""
    return 2 if _rtl() else 0

def _main_col():
    """Column for main content: 0 (left) for RTL, 1 (right) for LTR."""
    return 0 if _rtl() else 1


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- 1. SET CUSTOM WINDOW ICON ---
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # --- 2. HIDE MAIN WINDOW & SHOW SPLASH ---
        self.withdraw()
        self._show_splash()

        self.geometry("1100x750")
        self.minsize(900, 600)

        # State
        self._sources = []  # list of source folder paths
        self._dst = ctk.StringVar()
        self._move = ctk.BooleanVar(value=False)
        self._ocr = ctk.BooleanVar(value=True)
        self._gpu = ctk.BooleanVar(value=False)
        self._reset = ctk.BooleanVar(value=False)
        self._dedup = ctk.BooleanVar(value=False)
        self._dedup_action = ctk.StringVar(value=t("dedup_move"))
        self._transcribe = ctk.BooleanVar(value=False)
        self._whisper_model = ctk.StringVar(value="medium")
        self._ffmpeg_path = ctk.StringVar(value="")
        self._workers = ctk.IntVar(value=12)
        self._timeout = ctk.IntVar(value=30)
        self._score = ctk.DoubleVar(value=5.0)
        self._running = False
        self._cancel = threading.Event()
        self._results = []
        self._dedup_results = None
        self._cats = cat_mgr.load_categories()
        self._disabled = set()
        self._filetypes = cat_mgr.load_filetypes()
        self._settings_path = Path.home() / ".smart_categorizer_settings.json"
        
        self._load_settings()

        self.title(t("app_name"))

        self.grid_columnconfigure(_sidebar_col(), weight=0, minsize=220)
        self.grid_columnconfigure(_main_col(), weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

        # --- 3. SCHEDULE SPLASH CLOSING ---
        # Wait 2.5 seconds, then destroy splash and reveal main app
        self.after(2500, self._close_splash)

    # --- SPLASH SCREEN FUNCTIONS ---
    def _show_splash(self):
        self.splash = ctk.CTkToplevel(self)
        self.splash.overrideredirect(True)  # Remove window borders/controls
        
        # Center the splash screen (400x250)
        w, h = 400, 250
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.splash.geometry(f"{w}x{h}+{int(x)}+{int(y)}")
        self.splash.attributes("-topmost", True) # Keep on top of other windows
        
        # Beautiful gradient/dark frame
        sf = ctk.CTkFrame(self.splash, fg_color=("gray90", "#111827"), corner_radius=15, border_width=2, border_color=ACCENT)
        sf.pack(fill="both", expand=True)
        
        # Optional: Render your logo.png (Uncomment these 4 lines when you have a logo.png)
        # logo_path = resource_path("logo.png")
        # if os.path.exists(logo_path):
        #     logo_img = ctk.CTkImage(Image.open(logo_path), size=(80, 80))
        #     ctk.CTkLabel(sf, image=logo_img, text="").pack(pady=(35, 5))
        
        ctk.CTkLabel(sf, text=t("app_name"), font=(FONT, 24, "bold")).pack(pady=(70, 5)) # Adjust top padding if using logo
        ctk.CTkLabel(sf, text="Loading AI Engines...", font=(FONT, 12), text_color="gray50").pack(pady=5)
        
        self.splash.update() # Force UI to draw immediately

    def _close_splash(self):
        self.splash.destroy()
        self.deiconify()  # Reveal the main window!

    # ═══════════ SIDEBAR ═══════════
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray92","gray14"))
        sb.grid(row=0, column=_sidebar_col(), sticky="nsew")
        sb.grid_propagate(False)  # keep fixed 220px width
        sb.grid_rowconfigure(8, weight=1)
        ctk.CTkLabel(sb, text="📂", font=(FONT,36)).grid(row=0,column=0,padx=20,pady=(24,4))
        self._title_lbl = ctk.CTkLabel(sb, text=t("app_name"), font=(FONT,14,"bold"), wraplength=180)
        self._title_lbl.grid(row=1,column=0,padx=20,pady=(0,4))
        ctk.CTkLabel(sb, text="v1.0", font=(FONT,11), text_color="gray50").grid(row=2,column=0,padx=20,pady=(0,16))

        self._nav = {}
        icons = [("home","nav_home","🏠"),("settings","nav_settings","⚙️"),
                 ("cats","nav_categories","📋"),("results","nav_results","📊"),("log","nav_log","📝")]
        for i,(k,lk,ic) in enumerate(icons):
            b = ctk.CTkButton(sb, text=f" {ic}  {t(lk)}", anchor=_anchor(), font=(FONT,13), height=38,
                              fg_color="transparent", text_color=("gray10","gray90"),
                              hover_color=("gray80","gray25"), command=lambda k=k:self._go(k))
            b.grid(row=3+i,column=0,padx=12,pady=2,sticky="ew")
            self._nav[k] = (b, lk, ic)

        # About button
        ctk.CTkButton(sb, text=f" ℹ️  {t('about_btn')}", anchor=_anchor(), font=(FONT,13), height=38,
                      fg_color="transparent", text_color=("gray10","gray90"),
                      hover_color=("gray80","gray25"),
                      command=self._show_about).grid(row=7,column=0,padx=12,pady=(16,2),sticky="ew")

        # Support / Donate button
        ctk.CTkButton(sb, text=f" ❤️  {t('support_btn')}", anchor=_anchor(), font=(FONT,13), height=38,
                      fg_color="transparent", text_color="#F472B6",
                      hover_color=("gray80","gray25"),
                      command=self._show_support).grid(row=8,column=0,padx=12,pady=(2,2),sticky="ew")

        # Language
        ctk.CTkLabel(sb, text=t("lang_lbl"), font=(FONT,11), text_color="gray50").grid(row=9,column=0,padx=20,pady=(8,0))
        self._lang_menu = ctk.CTkOptionMenu(sb, values=["English","العربية"], font=(FONT,11),
                                             height=28, width=140, command=self._switch_lang)
        self._lang_menu.grid(row=10,column=0,padx=20,pady=(4,8))
        self._lang_menu.set("English" if get_lang()=="en" else "العربية")

        # Theme
        ctk.CTkLabel(sb, text=t("theme_lbl"), font=(FONT,11), text_color="gray50").grid(row=11,column=0,padx=20,pady=(0,0))
        ctk.CTkOptionMenu(sb, values=["Dark","Light","System"], font=(FONT,11), height=28, width=140,
                          command=lambda v:ctk.set_appearance_mode(v)).grid(row=12,column=0,padx=20,pady=(4,20))

    def _switch_lang(self, v):
        new_lang = "ar" if "عرب" in v else "en"
        if new_lang == get_lang():
            return
        set_lang(new_lang)
        self._save_settings()
        # Rebuild UI in-place (safe for PyInstaller .exe)
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Destroy all widgets and rebuild — no process restart needed."""
        sources = list(self._sources)
        dst = self._dst.get()
        move = self._move.get()
        ocr = self._ocr.get()
        gpu = self._gpu.get()
        rst = self._reset.get()
        dedup = self._dedup.get()
        dedup_act = self._dedup_action.get()
        trans = self._transcribe.get()
        wmodel = self._whisper_model.get()
        ffmpeg_p = self._ffmpeg_path.get()
        workers = self._workers.get()
        timeout = self._timeout.get()
        score = self._score.get()
        results = self._results
        dedup_res = self._dedup_results

        for w in self.winfo_children():
            w.destroy()

        self.title(t("app_name"))

        # CRITICAL: Reset ALL column weights before reassigning
        for col in range(3):
            self.grid_columnconfigure(col, weight=0, minsize=0)

        self._sources = sources
        self._dst = ctk.StringVar(value=dst)
        self._move = ctk.BooleanVar(value=move)
        self._ocr = ctk.BooleanVar(value=ocr)
        self._gpu = ctk.BooleanVar(value=gpu)
        self._reset = ctk.BooleanVar(value=rst)
        self._dedup = ctk.BooleanVar(value=dedup)
        self._dedup_action = ctk.StringVar(value=dedup_act)
        self._transcribe = ctk.BooleanVar(value=trans)
        self._whisper_model = ctk.StringVar(value=wmodel)
        self._ffmpeg_path = ctk.StringVar(value=ffmpeg_p)
        self._workers = ctk.IntVar(value=workers)
        self._timeout = ctk.IntVar(value=timeout)
        self._score = ctk.DoubleVar(value=score)
        self._results = results
        self._dedup_results = dedup_res
        self._running = False
        self._cancel = threading.Event()

        self.grid_columnconfigure(_sidebar_col(), weight=0, minsize=220)
        self.grid_columnconfigure(_main_col(), weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    def _go(self, key):
        for k, f in self._pages.items(): f.grid_forget()
        self._pages[key].grid(row=0,column=0,sticky="nsew",padx=20,pady=16)
        for k,(btn,lk,ic) in self._nav.items():
            btn.configure(fg_color=ACCENT if k==key else "transparent",
                         text_color="white" if k==key else ("gray10","gray90"))

    # ═══════════ MAIN ═══════════
    def _build_main(self):
        self._main = ctk.CTkFrame(self, fg_color="transparent")
        self._main.grid(row=0, column=_main_col(), sticky="nsew")
        self._main.grid_columnconfigure(0,weight=1)
        self._main.grid_rowconfigure(0,weight=1)
        self._pages = {}
        self._pages["home"] = self._pg_home()
        self._pages["settings"] = self._pg_settings()
        self._pages["cats"] = self._pg_cats()
        self._pages["results"] = self._pg_results()
        self._pages["log"] = self._pg_log()
        self._go("home")

    # ═══════════ HOME PAGE ═══════════
    def _pg_home(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pg, text=t("home_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,4))
        ctk.CTkLabel(pg, text=t("home_subtitle"), font=(FONT,13), text_color="gray50", anchor=_anchor()).grid(row=1,column=0,sticky=_sticky(),pady=(0,12))

        # ── Source Folders (multi) ──
        src_frame = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        src_frame.grid(row=2,column=0,sticky="ew",pady=(0,8),ipady=6)
        src_frame.grid_columnconfigure(0,weight=1)

        src_header = ctk.CTkFrame(src_frame, fg_color="transparent")
        src_header.grid(row=0,column=0,sticky="ew",padx=16,pady=(8,4))
        ctk.CTkLabel(src_header, text=t("source_label"), font=(FONT,13,"bold")).pack(side=_side())
        ctk.CTkButton(src_header, text=t("src_add"), width=100, height=28, font=(FONT,11),
                      fg_color=SUCCESS, hover_color="#15803D",
                      command=self._add_source).pack(side=_side_end())

        self._src_list_frame = ctk.CTkFrame(src_frame, fg_color="transparent")
        self._src_list_frame.grid(row=1,column=0,sticky="ew",padx=16,pady=(0,8))
        self._src_list_frame.grid_columnconfigure(0,weight=1)
        self._render_sources()

        # ── Destination ──
        dst_frame = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        dst_frame.grid(row=3,column=0,sticky="ew",pady=(0,8),ipady=6)
        dst_frame.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(dst_frame, text=t("dest_label"), font=(FONT,13,"bold"), anchor=_anchor()).grid(row=0,column=0,padx=(16,8),pady=(8,0),sticky=_sticky())
        ctk.CTkEntry(dst_frame, textvariable=self._dst, font=(FONT,12), height=34, placeholder_text=t("dest_ph")).grid(row=1,column=0,columnspan=2,padx=16,pady=(4,8),sticky="ew")
        ctk.CTkButton(dst_frame, text=t("browse"), width=90, height=34, font=(FONT,12),
                      command=lambda:self._browse("dest")).grid(row=1,column=2,padx=(0,16),pady=(4,8))

        # Switches row 1
        q1 = ctk.CTkFrame(pg, fg_color="transparent"); q1.grid(row=4,column=0,sticky="ew",pady=(4,2))
        ctk.CTkSwitch(q1, text=t("sw_move"), font=(FONT,12), variable=self._move).pack(side=_side(),padx=(0,16))
        ctk.CTkSwitch(q1, text=t("sw_ocr"), font=(FONT,12), variable=self._ocr).pack(side=_side(),padx=(0,16))
        ctk.CTkSwitch(q1, text=t("sw_reset"), font=(FONT,12), variable=self._reset).pack(side=_side())

        # Switches row 2
        q2 = ctk.CTkFrame(pg, fg_color="transparent"); q2.grid(row=5,column=0,sticky="ew",pady=(2,2))
        ctk.CTkSwitch(q2, text=t("sw_dedup"), font=(FONT,12), variable=self._dedup).pack(side=_side(),padx=(0,12))
        ctk.CTkLabel(q2, text=t("dedup_lbl"), font=(FONT,11), text_color="gray50").pack(side=_side(),padx=(0,4))
        ctk.CTkOptionMenu(q2, variable=self._dedup_action,
                          values=[t("dedup_report"),t("dedup_move"),t("dedup_delete")],
                          font=(FONT,11), height=28, width=150).pack(side=_side())

        # Switches row 3 — Transcription
        q3 = ctk.CTkFrame(pg, fg_color="transparent"); q3.grid(row=6,column=0,sticky="ew",pady=(2,10))
        ctk.CTkSwitch(q3, text=t("sw_transcribe"), font=(FONT,12), variable=self._transcribe).pack(side=_side(),padx=(0,12))
        ctk.CTkLabel(q3, text=t("whisper_model_lbl"), font=(FONT,11), text_color="gray50").pack(side=_side(),padx=(0,4))
        ctk.CTkOptionMenu(q3, variable=self._whisper_model,
                          values=["tiny","base","small","medium","large"],
                          font=(FONT,11), height=28, width=100).pack(side=_side())

        # Progress
        pf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        pf.grid(row=7,column=0,sticky="ew",pady=(4,10),ipady=10); pf.grid_columnconfigure(0,weight=1)
        self._prog_lbl = ctk.CTkLabel(pf, text=t("ready"), font=(FONT,12), anchor=_anchor())
        self._prog_lbl.grid(row=0,column=0,padx=16,pady=(8,4),sticky=_sticky())
        self._prog_bar = ctk.CTkProgressBar(pf, height=14, corner_radius=7)
        self._prog_bar.grid(row=1,column=0,padx=16,pady=(0,4),sticky="ew"); self._prog_bar.set(0)
        self._stats_lbl = ctk.CTkLabel(pf, text="", font=(FONT,11), text_color="gray50", anchor=_anchor())
        self._stats_lbl.grid(row=2,column=0,padx=16,pady=(0,8),sticky=_sticky())

        # Buttons
        bf = ctk.CTkFrame(pg, fg_color="transparent"); bf.grid(row=8,column=0,sticky="ew",pady=(4,0))
        self._btn_start = ctk.CTkButton(bf, text=t("btn_start"), font=(FONT,15,"bold"), height=48,
                                         corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_H, command=self._start)
        self._btn_start.pack(side=_side(),expand=True,fill="x",padx=(0,8))
        self._btn_stop = ctk.CTkButton(bf, text=t("btn_stop"), font=(FONT,15,"bold"), height=48, width=140,
                                        corner_radius=10, fg_color=DANGER, hover_color="#B91C1C",
                                        state="disabled", command=self._stop)
        self._btn_stop.pack(side=_side())
        return pg

    def _render_sources(self):
        """Render the list of source folders with remove buttons."""
        for w in self._src_list_frame.winfo_children():
            w.destroy()

        if not self._sources:
            ctk.CTkLabel(self._src_list_frame, text=t("src_empty"),
                         font=(FONT,11), text_color="gray50").grid(row=0,column=0,pady=4,sticky=_sticky())
            return

        for i, src_path in enumerate(self._sources):
            row = ctk.CTkFrame(self._src_list_frame, fg_color=("gray80","gray25"), corner_radius=6)
            row.grid(row=i,column=0,sticky="ew",pady=2,ipady=2)
            row.grid_columnconfigure(0,weight=1)

            # Truncate long paths for display
            display = src_path if len(src_path) < 60 else "..." + src_path[-55:]
            ctk.CTkLabel(row, text=f"📁 {display}", font=(FONT,11),
                         anchor=_anchor()).grid(row=0,column=0,padx=(8,4),pady=4,sticky=_sticky())
            ctk.CTkButton(row, text="✕", width=28, height=24, font=(FONT,11),
                          fg_color=DANGER, hover_color="#B91C1C",
                          command=lambda idx=i: self._remove_source(idx)
                          ).grid(row=0,column=1,padx=(4,6),pady=4)

    def _add_source(self):
        folder = filedialog.askdirectory(title=t("src_add"))
        if folder and folder not in self._sources:
            self._sources.append(folder)
            self._render_sources()
            if not self._dst.get():
                self._dst.set(os.path.join(folder, "categorized_docs"))

    def _remove_source(self, idx):
        if 0 <= idx < len(self._sources):
            self._sources.pop(idx)
            self._render_sources()

    # ═══════════ SETTINGS PAGE ═══════════
    def _pg_settings(self):
        pg = ctk.CTkScrollableFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(pg, text=t("settings_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,16))

        # Role presets
        rf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        rf.grid(row=1,column=0,sticky="ew",pady=(0,12),ipady=10); rf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(rf, text=t("role_title"), font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,4),sticky=_sticky())
        ctk.CTkLabel(rf, text=t("role_hint"), font=(FONT,11), text_color="gray50").grid(row=1,column=0,columnspan=3,padx=16,pady=(0,8),sticky=_sticky())

        self._role_var = ctk.StringVar(value=cat_mgr.get_role_names()[0])
        roles_display = [cat_mgr.get_role_display(r, get_lang()) for r in cat_mgr.get_role_names()]
        ctk.CTkOptionMenu(rf, variable=self._role_var, values=roles_display,
                          font=(FONT,12), height=32, width=280).grid(row=2,column=0,columnspan=2,padx=16,pady=(0,8),sticky=_sticky())
        ctk.CTkButton(rf, text=t("btn_load"), font=(FONT,12), height=32, width=120,
                      fg_color=WARN, command=self._load_preset).grid(row=2,column=2,padx=(0,16),pady=(0,8))

        # Performance
        pf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        pf.grid(row=2,column=0,sticky="ew",pady=(0,12),ipady=10); pf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(pf, text=t("perf"), font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,8),sticky=_sticky())
        ctk.CTkLabel(pf, text=t("workers"), font=(FONT,12)).grid(row=1,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(pf, from_=1,to=32,number_of_steps=31, variable=self._workers).grid(row=1,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(pf, textvariable=self._workers, width=30, font=(FONT,12,"bold")).grid(row=1,column=2,padx=(0,16))
        ctk.CTkLabel(pf, text=t("timeout"), font=(FONT,12)).grid(row=2,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(pf, from_=10,to=120,number_of_steps=22, variable=self._timeout).grid(row=2,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(pf, textvariable=self._timeout, width=30, font=(FONT,12,"bold")).grid(row=2,column=2,padx=(0,16))

        # --- NEW FFMPEG PATH UI ---
        ctk.CTkLabel(pf, text=t("ffmpeg_path_lbl"), font=(FONT,12)).grid(row=3,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ff_frame = ctk.CTkFrame(pf, fg_color="transparent")
        ff_frame.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(0,16), pady=4)
        ff_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(ff_frame, textvariable=self._ffmpeg_path, font=(FONT,11), height=28, placeholder_text="C:\\...\\ffmpeg.exe").grid(row=0, column=0, sticky="ew", padx=(0,4))
        ctk.CTkButton(ff_frame, text=t("browse"), width=60, height=28, font=(FONT,11), command=lambda: self._browse("ffmpeg")).grid(row=0, column=1)
        ctk.CTkLabel(pf, text=t("ffmpeg_hint"), font=(FONT,10), text_color="gray50").grid(row=4,column=0,columnspan=3,padx=16,pady=(0,8),sticky=_sticky())

        # Classification
        cf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        cf.grid(row=3,column=0,sticky="ew",pady=(0,12),ipady=10); cf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(cf, text=t("cls_title"), font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,8),sticky=_sticky())
        ctk.CTkLabel(cf, text=t("score_lbl"), font=(FONT,12)).grid(row=1,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(cf, from_=2.0,to=15.0,number_of_steps=26, variable=self._score).grid(row=1,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(cf, textvariable=self._score, width=30, font=(FONT,12,"bold")).grid(row=1,column=2,padx=(0,16))
        ctk.CTkLabel(cf, text=t("score_hint"), font=(FONT,11), text_color="gray50").grid(row=2,column=0,columnspan=3,padx=16,pady=(2,8),sticky=_sticky())

        # GPU Acceleration
        gf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        gf.grid(row=4,column=0,sticky="ew",pady=(0,12),ipady=10); gf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(gf, text=t("gpu_title"), font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,4),sticky=_sticky())

        # Fast synchronous GPU check
        gpu_status = self._detect_gpu()
        status_color = SUCCESS if gpu_status["available"] else "gray50"
        ctk.CTkLabel(gf, text=gpu_status["display"], font=(FONT,11),
                     text_color=status_color).grid(row=1,column=0,columnspan=3,padx=16,pady=(0,8),sticky=_sticky())

        ctk.CTkSwitch(gf, text=t("gpu_enable"), font=(FONT,12),
                      variable=self._gpu).grid(row=2,column=0,columnspan=3,padx=16,pady=(0,4),sticky=_sticky())
        ctk.CTkLabel(gf, text=t("gpu_hint"), font=(FONT,11),
                     text_color="gray50", wraplength=500).grid(row=3,column=0,columnspan=3,padx=16,pady=(0,8),sticky=_sticky())

        # File Types
        ftf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        ftf.grid(row=5,column=0,sticky="ew",pady=(0,12),ipady=10)
        ftf.grid_columnconfigure(0,weight=1)

        # Header row
        ft_header = ctk.CTkFrame(ftf, fg_color="transparent")
        ft_header.grid(row=0,column=0,sticky="ew",padx=16,pady=(10,4))
        ctk.CTkLabel(ft_header, text=t("ft_title"), font=(FONT,14,"bold")).pack(side=_side())
        active_n = sum(1 for v in self._filetypes.values() if v.get("enabled"))
        total_n = len(self._filetypes)
        self._ft_count_lbl = ctk.CTkLabel(ft_header, text=t("ft_active",n=active_n,t=total_n),
                                           font=(FONT,11), text_color="gray50")
        self._ft_count_lbl.pack(side=_side(), padx=12)

        # Toolbar
        ft_tb = ctk.CTkFrame(ftf, fg_color="transparent")
        ft_tb.grid(row=1,column=0,sticky="ew",padx=16,pady=(0,6))
        ctk.CTkButton(ft_tb, text=t("ft_add_ext"), font=(FONT,11), width=120, height=28,
                      fg_color=SUCCESS, hover_color="#15803D",
                      command=self._add_ext_dialog).pack(side=_side(),padx=(0,6))
        ctk.CTkButton(ft_tb, text=t("ft_group_all"), font=(FONT,11), width=100, height=28,
                      fg_color="gray40", hover_color="gray30",
                      command=lambda: self._toggle_all_ft(True)).pack(side=_side(),padx=(0,6))
        ctk.CTkButton(ft_tb, text=t("ft_group_none"), font=(FONT,11), width=100, height=28,
                      fg_color="gray40", hover_color="gray30",
                      command=lambda: self._toggle_all_ft(False)).pack(side=_side(),padx=(0,6))
        ctk.CTkButton(ft_tb, text=t("ft_reset"), font=(FONT,11), width=120, height=28,
                      fg_color="gray40", hover_color="gray30",
                      command=self._reset_ft).pack(side=_side())

        # File type groups
        self._ft_scroll = ctk.CTkScrollableFrame(ftf, fg_color="transparent", height=220)
        self._ft_scroll.grid(row=2,column=0,sticky="ew",padx=8,pady=(0,8))
        self._ft_scroll.grid_columnconfigure(0,weight=1)
        self._render_filetypes()

        ctk.CTkButton(pg, text=t("btn_save"), font=(FONT,14,"bold"), height=44,
                      fg_color=SUCCESS, hover_color="#15803D",
                      command=self._save_and_confirm).grid(row=6,column=0,pady=(8,16),sticky="ew")
        return pg

    def _save_and_confirm(self):
        """Save settings, show success, navigate to home."""
        self._save_settings()
        try:
            from CTkMessagebox import CTkMessagebox
            CTkMessagebox(title=t("save_ok_title"), message=t("save_ok_msg"),
                          icon="check", option_1="OK")
        except ImportError:
            self._log(t("save_ok_msg"))
        self._go("home")

    # ═══════════ CATEGORIES PAGE ═══════════
    def _pg_cats(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(2,weight=1)
        ctk.CTkLabel(pg, text=t("cats_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,4))

        # Toolbar
        tb = ctk.CTkFrame(pg, fg_color="transparent"); tb.grid(row=1,column=0,sticky="ew",pady=(0,8))
        ctk.CTkButton(tb, text=t("btn_add"), font=(FONT,12), height=32, fg_color=SUCCESS,
                      command=self._add_cat).pack(side=_side(),padx=(0,8))
        ctk.CTkButton(tb, text=t("btn_defaults"), font=(FONT,12), height=32, fg_color="gray40",
                      command=self._reset_cats).pack(side=_side())
        ctk.CTkLabel(tb, text=f"{len(self._cats)} {t('cats_count').lower()}", font=(FONT,11),
                     text_color="gray50").pack(side=_side_end())

        self._cats_scroll = ctk.CTkScrollableFrame(pg, fg_color="transparent")
        self._cats_scroll.grid(row=2,column=0,sticky="nsew")
        self._cats_scroll.grid_columnconfigure(0,weight=1)
        self._render_cats()
        return pg

    def _render_cats(self):
        for w in self._cats_scroll.winfo_children(): w.destroy()
        for i,(cn,ci) in enumerate(self._cats.items()):
            pp = ci.get("pp","")
            is_p = ci.get("personal",False)
            rf = ctk.CTkFrame(self._cats_scroll, fg_color=("gray88","gray20"), corner_radius=8)
            rf.grid(row=i,column=0,sticky="ew",pady=2,ipady=4); rf.grid_columnconfigure(1,weight=1)

            var = ctk.BooleanVar(value=cn not in self._disabled)
            ctk.CTkSwitch(rf, text="", variable=var, width=40,
                          command=lambda n=cn,v=var:self._toggle_cat(n,v)).grid(row=0,column=0,padx=(10,4),pady=6)

            dn = cn.split("_",1)[1].replace("_"," ") if "_" in cn else cn
            bc = SUCCESS if pp in("HIGH","VERY_HIGH") else (WARN if pp=="MEDIUM" else "gray50")
            tl = t("personal") if is_p else pp
            ctk.CTkLabel(rf, text=dn, font=(FONT,12,"bold"), anchor=_anchor()).grid(row=0,column=1,padx=(4,8),pady=6,sticky=_sticky())
            ctk.CTkLabel(rf, text=tl, font=(FONT,10), text_color=bc).grid(row=0,column=2,padx=4,pady=6)

            ctk.CTkButton(rf, text=t("edit"), width=50, height=26, font=(FONT,10),
                          fg_color="gray40", command=lambda n=cn:self._edit_cat(n)).grid(row=0,column=3,padx=2,pady=6)
            ctk.CTkButton(rf, text=t("delete"), width=50, height=26, font=(FONT,10),
                          fg_color=DANGER, command=lambda n=cn:self._del_cat(n)).grid(row=0,column=4,padx=(2,10),pady=6)

            kws = list(ci.get("en",{}).keys())[:3] + list(ci.get("ar",{}).keys())[:2]
            if kws:
                ctk.CTkLabel(rf, text=", ".join(kws), font=(FONT,10), text_color="gray50",
                             wraplength=500, anchor=_anchor()).grid(row=1,column=1,columnspan=4,padx=(4,16),pady=(0,6),sticky=_sticky())

    def _toggle_cat(self, n, v):
        if v.get(): self._disabled.discard(n)
        else: self._disabled.add(n)

    def _add_cat(self):
        self._open_cat_editor(None)

    def _edit_cat(self, name):
        self._open_cat_editor(name)

    def _del_cat(self, name):
        try:
            from CTkMessagebox import CTkMessagebox
            msg = CTkMessagebox(title=t("delete"), message=t("confirm_del_cat",n=name),
                               icon="warning", option_1=t("confirm_yes"), option_2=t("cancel"))
            if msg.get() != t("confirm_yes"): return
        except ImportError: pass
        self._cats = cat_mgr.delete_category(self._cats, name)
        engine.reload_categories(self._cats)
        self._render_cats()

    def _reset_cats(self):
        try:
            from CTkMessagebox import CTkMessagebox
            msg = CTkMessagebox(title=t("btn_defaults"), message=t("confirm_reset_cats"),
                               icon="warning", option_1=t("confirm_yes"), option_2=t("cancel"))
            if msg.get() != t("confirm_yes"): return
        except ImportError: pass
        self._cats = cat_mgr.reset_to_defaults()
        engine.reload_categories(self._cats)
        self._disabled.clear()
        self._render_cats()

    def _load_preset(self):
        # Map display name back to key
        sel = self._role_var.get()
        role_key = None
        for rk in cat_mgr.get_role_names():
            if cat_mgr.get_role_display(rk, get_lang()) == sel or rk == sel:
                role_key = rk; break
        if not role_key: return

        try:
            from CTkMessagebox import CTkMessagebox
            msg = CTkMessagebox(title=t("btn_load"), message=t("preset_confirm",r=sel),
                               icon="question", option_1=t("confirm_yes"), option_2=t("cancel"))
            if msg.get() != t("confirm_yes"): return
        except ImportError: pass

        self._cats = cat_mgr.load_preset(role_key)
        engine.reload_categories(self._cats)
        self._disabled.clear()
        self._render_cats()
        self._log(t("preset_loaded", n=len(self._cats), r=sel))

    # ═══════════ CATEGORY EDITOR DIALOG ═══════════
    def _open_cat_editor(self, name):
        is_new = name is None
        cat = self._cats.get(name, cat_mgr.make_empty_category()) if not is_new else cat_mgr.make_empty_category()

        win = ctk.CTkToplevel(self)
        win.title(t("new_title") if is_new else t("edit_title"))
        win.geometry("650x700")
        win.grab_set()
        win.grid_columnconfigure(0,weight=1)

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both",expand=True,padx=16,pady=16)
        scroll.grid_columnconfigure(1,weight=1)
        r = 0

        # Name
        ctk.CTkLabel(scroll, text=t("cat_name"), font=(FONT,12,"bold")).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        name_var = ctk.StringVar(value=name or "")
        ctk.CTkEntry(scroll, textvariable=name_var, font=(FONT,12), height=32).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        # Personal + Potential
        pers_var = ctk.BooleanVar(value=cat.get("personal",False))
        ctk.CTkSwitch(scroll, text=t("cat_personal"), variable=pers_var, font=(FONT,12)).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=4)
        r+=1
        ctk.CTkLabel(scroll, text=t("cat_potential"), font=(FONT,12,"bold")).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        pot_var = ctk.StringVar(value=cat.get("pp","MEDIUM"))
        ctk.CTkOptionMenu(scroll, variable=pot_var, values=["NONE","LOW","MEDIUM","HIGH","VERY_HIGH"],
                          font=(FONT,11), height=28).grid(row=r,column=1,sticky=_sticky(),padx=4,pady=4)
        r+=1

        # English keywords
        ctk.CTkLabel(scroll, text=t("cat_en_kw"), font=(FONT,12,"bold")).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=(8,4))
        r+=1
        en_kw_text = ctk.CTkTextbox(scroll, height=100, font=("Consolas",11))
        en_kw_text.grid(row=r,column=0,columnspan=2,sticky="ew",padx=4,pady=2)
        for k,v in cat.get("en",{}).items(): en_kw_text.insert(END, f"{k}:{v}\n")
        r+=1

        # Arabic keywords
        ctk.CTkLabel(scroll, text=t("cat_ar_kw"), font=(FONT,12,"bold")).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=(8,4))
        r+=1
        ar_kw_text = ctk.CTkTextbox(scroll, height=100, font=("Consolas",11))
        ar_kw_text.grid(row=r,column=0,columnspan=2,sticky="ew",padx=4,pady=2)
        for k,v in cat.get("ar",{}).items(): ar_kw_text.insert(END, f"{k}:{v}\n")
        r+=1

        # Filename hints
        ctk.CTkLabel(scroll, text=t("cat_fh"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        fh_var = ctk.StringVar(value=", ".join(cat.get("fh",[])))
        ctk.CTkEntry(scroll, textvariable=fh_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        # Path hints
        ctk.CTkLabel(scroll, text=t("cat_ph"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        ph_var = ctk.StringVar(value=", ".join(cat.get("ph",[])))
        ctk.CTkEntry(scroll, textvariable=ph_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        # Negative keywords
        ctk.CTkLabel(scroll, text=t("cat_neg"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        neg_en_var = ctk.StringVar(value=", ".join(cat.get("neg_en",[])))
        ctk.CTkEntry(scroll, textvariable=neg_en_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent"); bf.grid(row=r,column=0,columnspan=2,pady=(12,0))
        def _save():
            new_name = name_var.get().strip().replace(" ","_")
            if not new_name: return
            data = {
                "pp": pot_var.get(),
                "personal": pers_var.get(),
                "en": self._parse_kw(en_kw_text.get("1.0",END)),
                "ar": self._parse_kw(ar_kw_text.get("1.0",END)),
                "fh": [x.strip() for x in fh_var.get().split(",") if x.strip()],
                "ph": [x.strip() for x in ph_var.get().split(",") if x.strip()],
                "neg_en": [x.strip() for x in neg_en_var.get().split(",") if x.strip()],
                "neg_ar": [],
            }
            if not is_new and new_name != name:
                self._cats.pop(name, None)
            self._cats = cat_mgr.update_category(self._cats, new_name, data)
            engine.reload_categories(self._cats)
            self._render_cats()
            win.destroy()

        ctk.CTkButton(bf, text=t("save"), font=(FONT,13), height=36, fg_color=SUCCESS, command=_save).pack(side=_side(),padx=(0,8))
        ctk.CTkButton(bf, text=t("cancel"), font=(FONT,13), height=36, fg_color="gray40", command=win.destroy).pack(side=_side())

    @staticmethod
    def _parse_kw(text):
        """Parse 'keyword:weight' per line to dict."""
        result = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if not line: continue
            if ":" in line:
                parts = line.rsplit(":",1)
                try: result[parts[0].strip()] = int(parts[1].strip())
                except: result[parts[0].strip()] = 3
            else:
                result[line] = 3
        return result

    # ═══════════ RESULTS PAGE ═══════════
    def _pg_results(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(1,weight=1)
        ctk.CTkLabel(pg, text=t("results_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,12))
        self._res_scroll = ctk.CTkScrollableFrame(pg, fg_color="transparent")
        self._res_scroll.grid(row=1,column=0,sticky="nsew"); self._res_scroll.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self._res_scroll, text=t("results_empty"), font=(FONT,14), text_color="gray50").grid(row=0,column=0,pady=60)
        return pg

    def _refresh_results(self):
        for w in self._res_scroll.winfo_children(): w.destroy()
        if not self._results:
            ctk.CTkLabel(self._res_scroll, text=t("results_empty"), font=(FONT,14), text_color="gray50").grid(row=0,column=0,pady=60)
            return
        from collections import defaultdict
        stats = defaultdict(lambda:{"c":0,"s":0,"ar":0,"en":0})
        for r in self._results:
            cat=r["category"]; stats[cat]["c"]+=1; stats[cat]["s"]+=r.get("size",0)
            l=r.get("language","")
            if l in("ar","mixed"): stats[cat]["ar"]+=1
            elif l=="en": stats[cat]["en"]+=1
        total=len(self._results)
        errors=sum(1 for r in self._results if r.get("error"))
        products=sum(1 for r in self._results if r.get("product_potential") in("HIGH","VERY_HIGH") and r.get("score",0)>=8)

        # Summary card
        sm = ctk.CTkFrame(self._res_scroll, fg_color=("gray88","gray20"), corner_radius=10)
        sm.grid(row=0,column=0,sticky="ew",pady=(0,12),ipady=10); sm.grid_columnconfigure((0,1,2,3),weight=1)
        for col,(v,l,c) in enumerate([(str(total),t("total"),ACCENT),(str(products),t("sellable"),SUCCESS),
                                       (str(errors),t("errors_lbl"),DANGER if errors else "gray50"),(str(len(stats)),t("cats_count"),WARN)]):
            f=ctk.CTkFrame(sm,fg_color="transparent"); f.grid(row=0,column=col,padx=12,pady=8)
            ctk.CTkLabel(f,text=v,font=(FONT,28,"bold"),text_color=c).pack()
            ctk.CTkLabel(f,text=l,font=(FONT,11),text_color="gray50").pack()

        for i,cat in enumerate(sorted(stats)):
            s=stats[cat]; dn=cat.split("_",1)[1].replace("_"," ") if "_" in cat else cat
            pct=(s["c"]/total*100) if total else 0
            rf=ctk.CTkFrame(self._res_scroll,fg_color=("gray88","gray20"),corner_radius=8)
            rf.grid(row=i+1,column=0,sticky="ew",pady=2,ipady=4); rf.grid_columnconfigure(1,weight=1)
            ctk.CTkLabel(rf,text=dn,font=(FONT,12,"bold"),anchor=_anchor()).grid(row=0,column=0,padx=(12,8),pady=6,sticky=_sticky())
            bar=ctk.CTkProgressBar(rf,height=10,corner_radius=5); bar.grid(row=0,column=1,padx=4,pady=6,sticky="ew"); bar.set(min(pct/100,1.0))
            ctk.CTkLabel(rf,text=f"{s['c']}  ({pct:.0f}%)",font=(FONT,10),text_color="gray50",width=120).grid(row=0,column=2,padx=(4,12),pady=6)

        # Support banner (shown after successful categorization)
        if total > 0:
            row_after = len(stats) + 2
            sup = ctk.CTkFrame(self._res_scroll, fg_color=("gray82","gray22"),
                               corner_radius=12, border_width=1, border_color="#F472B6")
            sup.grid(row=row_after, column=0, sticky="ew", pady=(16,4), ipady=8)
            sup.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(sup, text=t("support_banner_short"), font=(FONT, 12),
                         wraplength=500, justify="center" if get_lang()=="en" else "right",
                         text_color=("gray20","gray80")).grid(row=0, column=0, padx=16, pady=(10,6))
            ctk.CTkButton(sup, text=f"❤️ {t('support_btn')}", font=(FONT, 12, "bold"),
                          height=34, corner_radius=8,
                          fg_color="#F472B6", hover_color="#EC4899",
                          command=self._show_support).grid(row=1, column=0, padx=16, pady=(0,10))

    # ═══════════ LOG PAGE ═══════════
    def _pg_log(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(1,weight=1)
        hd = ctk.CTkFrame(pg, fg_color="transparent"); hd.grid(row=0,column=0,sticky="ew",pady=(0,8))
        ctk.CTkLabel(hd, text=t("log_title"), font=(FONT,22,"bold"), anchor=_anchor()).pack(side=_side())
        ctk.CTkButton(hd, text=t("btn_clear"), width=80, height=30, font=(FONT,11), fg_color="gray40",
                      command=lambda:self._log_box.delete("1.0",END)).pack(side=_side_end())
        self._log_box = ctk.CTkTextbox(pg, font=("Consolas",11), wrap="word", fg_color=("gray92","gray12"))
        self._log_box.grid(row=1,column=0,sticky="nsew")
        return pg

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_box.after(0, lambda: self._log_box.insert(END, f"[{ts}] {msg}\n"))
        self._log_box.after(0, lambda: self._log_box.see(END))

    # ═══════════ BROWSE ═══════════
    def _browse(self, which):
        if which == "ffmpeg":
            fp = filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All Files", "*.*")])
            if fp:
                self._ffmpeg_path.set(fp)
        else:
            folder = filedialog.askdirectory()
            if folder:
                self._dst.set(folder)

    # ═══════════ START / STOP ═══════════
    def _start(self):
        if not self._sources:
            self._show_err(t("err_no_src")); return
        valid = [s for s in self._sources if os.path.isdir(s)]
        if not valid:
            self._show_err(t("err_no_src")); return
        dst = self._dst.get().strip()
        if not dst: self._show_err(t("err_no_dst")); return

        if self._move.get():
            try:
                from CTkMessagebox import CTkMessagebox
                msg = CTkMessagebox(title="⚠", message=t("confirm_move"), icon="warning",
                                   option_1=t("confirm_yes"), option_2=t("cancel"))
                if msg.get() != t("confirm_yes"): return
            except ImportError: pass

        try:
            self._running = True; self._cancel.clear()
            self._btn_start.configure(state="disabled"); self._btn_stop.configure(state="normal")
            self._prog_bar.set(0); self._prog_lbl.configure(text=t("preparing")); self._stats_lbl.configure(text="")
            self._results = []; self._dedup_results = None

            # Reload categories
            active = {k:v for k,v in self._cats.items() if k not in self._disabled}
            engine.reload_categories(active)

            # Config
            engine.CFG = engine.Config()
            engine.CFG.ocr_on = self._ocr.get()
            engine.CFG.gpu = self._gpu.get()
            engine.CFG.move_mode = self._move.get()
            engine.CFG.reset = self._reset.get()
            engine.CFG.max_workers = self._workers.get()
            engine.CFG.file_timeout = self._timeout.get()
            engine.CFG.ocr_timeout = self._timeout.get() * 2
            engine.CFG.score_thr = self._score.get()
            engine.CFG.dedup = self._dedup.get()
            
            # FOOLPROOF DEDUP MAPPING (Handles all languages instantly)
            da_map = {
                t("dedup_report"): "report", 
                t("dedup_move"): "move_to_dupes", 
                t("dedup_delete"): "delete",
                "Report only": "report",
                "Move to _duplicates": "move_to_dupes",
                "Delete permanently": "delete",
                "تقرير فقط": "report",
                "نقل للمكررات": "move_to_dupes",
                "حذف نهائي": "delete"
            }
            engine.CFG.dedup_action = da_map.get(self._dedup_action.get(), "delete")
            
            engine.CFG.transcribe_on = self._transcribe.get()
            engine.CFG.whisper_model = self._whisper_model.get()
            engine.CFG.ffmpeg_path = self._ffmpeg_path.get().strip()

            # File types
            text_exts, img_exts, media_exts = cat_mgr.get_active_extensions(self._filetypes)
            engine.TXT_EXTS = text_exts
            engine.IMG_EXT = img_exts
            engine.MEDIA_EXT = media_exts
            engine.ALL_EXTS = text_exts | img_exts | media_exts
            engine.DIA_EXT = {ext for ext, info in self._filetypes.items()
                              if info.get("group") == "diagrams" and info.get("enabled")}

            engine.set_callbacks(progress_fn=self._on_progress, log_fn=self._log, cancel_event=self._cancel)

            # Start background thread
            self._worker = threading.Thread(target=self._run_engine, args=(list(valid), dst), daemon=True)
            self._worker.start()

        except Exception as e:
            self._running = False
            self._btn_start.configure(state="normal"); self._btn_stop.configure(state="disabled")
            self._prog_lbl.configure(text=t("error", e=str(e)))
            self._log(f"Start error: {e}")

    def _run_engine(self, sources, dst):
        try:
            self._log(f"Start: {len(sources)} sources → {dst}")
            engine.run(sources, dst)
            rp = Path(dst) / "_categorization_report.json"
            if rp.exists():
                self._results = json.loads(rp.read_text(encoding="utf-8")).get("files",[])
            dp = Path(dst) / "_DUPLICATES_REPORT.json"
            if dp.exists(): self._dedup_results = json.loads(dp.read_text(encoding="utf-8"))
            self.after(0, self._on_complete)
        except Exception as e:
            err_msg = str(e)
            self._log(f"Engine error: {err_msg}")
            self.after(0, lambda: self._on_complete(error=err_msg))

    def _on_progress(self, cur, total, fn, cat):
        """Called from engine thread — schedule GUI updates safely."""
        import time
        # Throttle UI updates to 10 frames per second to prevent freezing
        now = time.time()
        if now - getattr(self, '_last_ui_update', 0) < 0.1 and cur < total:
            return
        self._last_ui_update = now

        _pct = cur / total if total else 0
        _fn = fn[:60] if fn else ""
        _cd = cat.split("_",1)[1].replace("_"," ") if "_" in cat else (cat or "")
        _txt = f"{cur:,}/{total:,} ({_pct*100:.1f}%) → {_cd}"

        try:
            self.after(0, lambda p=_pct: self._prog_bar.set(p))
            self.after(0, lambda f=_fn: self._prog_lbl.configure(text=f"📄 {f}"))
            self.after(0, lambda s=_txt: self._stats_lbl.configure(text=s))
        except Exception:
            pass

    def _on_complete(self, error=None):
        self._running = False
        try:
            self._btn_start.configure(state="normal"); self._btn_stop.configure(state="disabled")
            if error: self._prog_lbl.configure(text=t("error", e=error))
            elif self._cancel.is_set(): self._prog_lbl.configure(text=t("stopped"))
            else:
                self._prog_lbl.configure(text=t("done", n=f"{len(self._results):,}"))
                self._prog_bar.set(1.0)
            self._refresh_results(); self._save_settings()
        except Exception:
            pass  # widgets might not exist if app was closed during processing

    def _stop(self):
        self._cancel.set()
        try:
            self._btn_stop.configure(state="disabled")
            self._prog_lbl.configure(text=t("stopping"))
        except Exception:
            pass
        self._log("Stop requested")

    @staticmethod
    def _detect_gpu():
        """Detect NVIDIA GPU using lightning-fast subprocess command."""
        import subprocess, sys
        result = {"available": False, "display": "⚠ No NVIDIA GPU detected — CPU mode active", "name": ""}
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=2,
                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split('\n')[0].split(",")
                name = parts[0].strip()
                vram = f"{int(parts[1].strip())/1024:.1f}" if len(parts) > 1 else "?"
                result.update({"available": True, "name": name, "display": f"✅ GPU: {name} ({vram} GB VRAM)"})
        except Exception: 
            pass
        return result

    def _show_err(self, msg):
        try:
            from CTkMessagebox import CTkMessagebox
            CTkMessagebox(title="Error", message=msg, icon="cancel")
        except ImportError: self._log(f"❌ {msg}")

    # ═══════════ SUPPORT / DONATE ═══════════
    PAYPAL_USER  = "redaghareeb"
    PATREON_LINK = "https://patreon.com/redaghareeb"
    GITHUB_LINK  = "https://github.com/redaghareeb"

    def _show_about(self):
        """Show the About product dialog with contact info."""
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("about_title"))
        dlg.geometry("500x420")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        # Logo/Header Area
        hdr = ctk.CTkFrame(dlg, fg_color="transparent")
        hdr.pack(pady=(20, 10))
        
        # NOTE: If you have logo.png working, you can uncomment the next 3 lines to show it here too!
        # logo_path = resource_path("logo.png")
        # if os.path.exists(logo_path):
        #     logo_img = ctk.CTkImage(Image.open(logo_path), size=(64, 64))
        #     ctk.CTkLabel(hdr, image=logo_img, text="").pack(pady=(0, 5))
        # else:
        ctk.CTkLabel(hdr, text="ℹ️", font=(FONT, 40)).pack()
            
        ctk.CTkLabel(hdr, text=t("app_name"), font=(FONT, 18, "bold")).pack(pady=(5,0))
        ctk.CTkLabel(hdr, text="Version 1.0", font=(FONT, 12), text_color="gray50").pack()

        # App Description
        desc_frame = ctk.CTkFrame(dlg, fg_color=("gray90","gray16"), corner_radius=10)
        desc_frame.pack(padx=24, pady=10, fill="x")
        ctk.CTkLabel(desc_frame, text=t("about_desc"), font=(FONT, 12), 
                     wraplength=420, justify="center" if get_lang()=="en" else "right").pack(padx=16, pady=16)

        # Contact & Email Area
        contact_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        contact_frame.pack(padx=24, pady=5, fill="x")
        ctk.CTkLabel(contact_frame, text=t("support_email_lbl"), font=(FONT, 13, "bold")).pack()
        
        email = "rf.ghareeb@gmail.com"
        # The %20 acts as a space in the URL, creating the subject "SFC- " automatically!
        mailto_link = f"mailto:{email}?subject=SFC-%20" 
        
        email_btn = ctk.CTkButton(contact_frame, text=f"✉️ {email}", font=(FONT, 14, "bold"), 
                                  fg_color="transparent", text_color=ACCENT, hover_color=("gray80","gray25"), 
                                  command=lambda: self._open_link(mailto_link))
        email_btn.pack(pady=4)
        
        ctk.CTkLabel(contact_frame, text=t("email_note"), font=(FONT, 11), text_color="gray50").pack()

        # Close button
        ctk.CTkButton(dlg, text=t("support_close"), font=(FONT, 12), width=100, height=32,
                      fg_color="gray40", hover_color="gray30", 
                      command=dlg.destroy).pack(pady=(20, 10))
        
    def _show_support(self):
        """Show professional donation dialog with preset amounts."""
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("support_title"))
        dlg.geometry("540x620")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        # ── Header ──
        header = ctk.CTkFrame(dlg, fg_color=("gray85","gray18"), corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        hdr_inner = ctk.CTkFrame(header, fg_color="transparent")
        hdr_inner.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(hdr_inner, text="❤️", font=(FONT, 32)).pack(side=_side(), padx=(0,10))
        ctk.CTkLabel(hdr_inner, text=t("support_title"), font=(FONT, 20, "bold")).pack(side=_side())

        # ── Message ──
        msg_frame = ctk.CTkFrame(dlg, fg_color=("gray90","gray16"), corner_radius=12)
        msg_frame.pack(padx=24, pady=(16,12), fill="x")
        ctk.CTkLabel(msg_frame, text=t("support_msg"), font=(FONT, 12),
                     wraplength=460,
                     justify="center" if get_lang()=="en" else "right",
                     ).pack(padx=16, pady=14)

        # ── Amount Selection ──
        amt_label = ctk.CTkLabel(dlg, text=t("support_choose_amount"), font=(FONT, 13, "bold"))
        amt_label.pack(padx=24, pady=(4,6), anchor=_anchor())

        self._donate_amount = ctk.StringVar(value="10")

        amt_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        amt_frame.pack(padx=24, fill="x", pady=(0,6))
        amt_frame.grid_columnconfigure((0,1,2,3), weight=1)

        amounts = [("$5", "5"), ("$10", "10"), ("$25", "25"), (t("support_custom"), "custom")]
        self._amt_buttons = []
        for i, (label, val) in enumerate(amounts):
            btn = ctk.CTkButton(
                amt_frame, text=label, font=(FONT, 14, "bold"),
                height=48, corner_radius=10,
                fg_color=("gray75","gray30"), hover_color=("gray65","gray35"),
                text_color=("gray10","gray90"),
                command=lambda v=val: self._select_amount(v)
            )
            btn.grid(row=0, column=i, padx=3, sticky="ew")
            self._amt_buttons.append((btn, val))

        # Custom amount entry (hidden by default)
        self._custom_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        self._custom_var = ctk.StringVar(value="")
        ctk.CTkLabel(self._custom_frame, text="$", font=(FONT, 18, "bold")).pack(side=_side(), padx=(0,4))
        ctk.CTkEntry(self._custom_frame, textvariable=self._custom_var,
                     font=(FONT, 16), height=40, width=120,
                     placeholder_text="15").pack(side=_side())

        # Select $10 by default
        self._select_amount("10")

        # ── Donate Buttons ──
        pay_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        pay_frame.pack(padx=24, pady=(8,4), fill="x")

        # PayPal — direct with amount
        ctk.CTkButton(
            pay_frame, text=t("support_paypal_btn"), font=(FONT, 15, "bold"),
            height=50, corner_radius=10,
            fg_color="#0070BA", hover_color="#005C99",
            image=None,
            command=self._donate_paypal
        ).pack(fill="x", pady=(0,6))

        # Patreon — monthly support
        ctk.CTkButton(
            pay_frame, text=t("support_patreon_btn"), font=(FONT, 13),
            height=42, corner_radius=10,
            fg_color="#FF424D", hover_color="#E03640",
            command=lambda: self._open_link(self.PATREON_LINK)
        ).pack(fill="x", pady=(0,6))

        # Bottom row: GitHub + Close
        bottom = ctk.CTkFrame(dlg, fg_color="transparent")
        bottom.pack(padx=24, pady=(4,16), fill="x")

        ctk.CTkButton(
            bottom, text=t("support_github_btn"), font=(FONT, 11),
            height=34, corner_radius=8,
            fg_color="#333333", hover_color="#222222",
            command=lambda: self._open_link(self.GITHUB_LINK)
        ).pack(side=_side())

        ctk.CTkButton(
            bottom, text=t("support_close"), font=(FONT, 11),
            height=34, width=100, corner_radius=8,
            fg_color="gray40", hover_color="gray30",
            command=dlg.destroy
        ).pack(side=_side_end())

    def _select_amount(self, val):
        """Highlight selected amount button."""
        self._donate_amount.set(val)
        for btn, bval in self._amt_buttons:
            if bval == val:
                btn.configure(fg_color="#F472B6", text_color="white")
            else:
                btn.configure(fg_color=("gray75","gray30"), text_color=("gray10","gray90"))
        # Show/hide custom field
        if val == "custom":
            self._custom_frame.pack(padx=24, pady=(2,0), anchor=_anchor())
        else:
            self._custom_frame.pack_forget()

    def _donate_paypal(self):
        """Open PayPal.me with pre-filled amount."""
        amt = self._donate_amount.get()
        if amt == "custom":
            amt = self._custom_var.get().strip()
            if not amt:
                amt = "10"
            # Clean: remove $ and non-numeric
            amt = ''.join(c for c in amt if c.isdigit() or c == '.')
            if not amt:
                amt = "10"
        # PayPal.me format: paypal.me/username/AMOUNT
        url = f"https://paypal.me/{self.PAYPAL_USER}/{amt}"
        self._open_link(url)

    @staticmethod
    def _open_link(url):
        """Open URL in default browser."""
        import webbrowser
        webbrowser.open(url)

    # ═══════════ FILE TYPE MANAGEMENT ═══════════
    def _render_filetypes(self):
        """Render file type toggles grouped by category."""
        for w in self._ft_scroll.winfo_children():
            w.destroy()

        lang = get_lang()
        # Group extensions
        from collections import defaultdict
        groups = defaultdict(list)
        for ext, info in sorted(self._filetypes.items()):
            groups[info.get("group","other")].append((ext, info))

        row_idx = 0
        for grp_key in ["documents","pdf","spreadsheets","presentations","diagrams",
                         "images","code","ebooks","archives","cad","media","other"]:
            exts = groups.get(grp_key, [])
            if not exts:
                continue

            grp_info = cat_mgr.FILE_GROUPS.get(grp_key, {})
            icon = grp_info.get("icon", "📎")
            label = grp_info.get(f"label_{lang}", grp_info.get("label_en", grp_key.title()))

            # Group header
            grp_frame = ctk.CTkFrame(self._ft_scroll, fg_color=("gray82","gray22"), corner_radius=6)
            grp_frame.grid(row=row_idx, column=0, sticky="ew", pady=(6,2), ipady=3)
            grp_frame.grid_columnconfigure(1, weight=1)

            enabled_in_grp = sum(1 for _, info in exts if info.get("enabled"))
            ctk.CTkLabel(grp_frame, text=f"{icon} {label}",
                         font=(FONT,12,"bold")).grid(row=0,column=0,padx=(10,6),pady=4,sticky=_sticky())
            ctk.CTkLabel(grp_frame, text=f"{enabled_in_grp}/{len(exts)}",
                         font=(FONT,10), text_color="gray50").grid(row=0,column=1,padx=4,pady=4,sticky=_sticky())

            # Group-level toggle all
            ctk.CTkButton(grp_frame, text="☑", width=28, height=24, font=(FONT,11),
                          fg_color="gray35", hover_color="gray25",
                          command=lambda g=grp_key: self._toggle_group_ft(g, True)
                          ).grid(row=0,column=2,padx=2,pady=4)
            ctk.CTkButton(grp_frame, text="☐", width=28, height=24, font=(FONT,11),
                          fg_color="gray35", hover_color="gray25",
                          command=lambda g=grp_key: self._toggle_group_ft(g, False)
                          ).grid(row=0,column=3,padx=(2,8),pady=4)

            row_idx += 1

            # Extensions in this group (flow layout in a single frame)
            ext_frame = ctk.CTkFrame(self._ft_scroll, fg_color="transparent")
            ext_frame.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=(0,4))

            for ext, info in exts:
                lbl = info.get(f"label_{lang}", info.get("label_en", ext))
                short = f"{ext}"
                is_custom = info.get("custom", False)
                var = ctk.BooleanVar(value=info.get("enabled", False))

                item = ctk.CTkFrame(ext_frame, fg_color="transparent")
                item.pack(side=_side(), padx=(0,4), pady=1)

                ctk.CTkCheckBox(item, text=short, variable=var,
                                font=(FONT,11), width=20, height=20,
                                checkbox_width=18, checkbox_height=18,
                                command=lambda e=ext, v=var: self._toggle_ft(e, v.get())
                                ).pack(side=_side())

                if is_custom:
                    ctk.CTkButton(item, text="✕", width=18, height=18, font=(FONT,9),
                                  fg_color=DANGER, hover_color="#B91C1C",
                                  command=lambda e=ext: self._remove_ext(e)
                                  ).pack(side=_side(), padx=(2,0))

            row_idx += 1

        self._update_ft_count()

    def _toggle_ft(self, ext, enabled):
        """Toggle a single extension."""
        if ext in self._filetypes:
            self._filetypes[ext]["enabled"] = enabled
            cat_mgr.save_filetypes(self._filetypes)
            self._update_ft_count()

    def _toggle_group_ft(self, group, enabled):
        """Toggle all extensions in a group."""
        for ext, info in self._filetypes.items():
            if info.get("group") == group:
                info["enabled"] = enabled
        cat_mgr.save_filetypes(self._filetypes)
        self._render_filetypes()

    def _toggle_all_ft(self, enabled):
        """Toggle all file types."""
        for info in self._filetypes.values():
            info["enabled"] = enabled
        cat_mgr.save_filetypes(self._filetypes)
        self._render_filetypes()

    def _reset_ft(self):
        """Reset file types to defaults."""
        cat_mgr.reset_filetypes()
        self._filetypes = cat_mgr.load_filetypes()
        self._render_filetypes()

    def _remove_ext(self, ext):
        """Remove a custom extension."""
        if ext in self._filetypes and self._filetypes[ext].get("custom"):
            del self._filetypes[ext]
            cat_mgr.save_filetypes(self._filetypes)
            self._render_filetypes()

    def _update_ft_count(self):
        """Update the active/total count label."""
        active = sum(1 for v in self._filetypes.values() if v.get("enabled"))
        total = len(self._filetypes)
        try:
            self._ft_count_lbl.configure(text=t("ft_active", n=active, t=total))
        except Exception:
            pass

    def _add_ext_dialog(self):
        """Dialog to add a custom file extension."""
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("ft_add_title"))
        dlg.geometry("420x320")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=t("ft_add_title"), font=(FONT,16,"bold")).pack(padx=20,pady=(16,12))

        # Extension
        ctk.CTkLabel(dlg, text=t("ft_ext_label"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        ext_var = ctk.StringVar()
        ctk.CTkEntry(dlg, textvariable=ext_var, font=(FONT,12), height=34,
                     placeholder_text=".xyz").pack(padx=20,fill="x",pady=(4,8))

        # Description
        ctk.CTkLabel(dlg, text=t("ft_ext_desc"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        desc_var = ctk.StringVar()
        ctk.CTkEntry(dlg, textvariable=desc_var, font=(FONT,12), height=34,
                     placeholder_text="My Custom File").pack(padx=20,fill="x",pady=(4,8))

        # Group
        ctk.CTkLabel(dlg, text=t("ft_ext_group"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        grp_var = ctk.StringVar(value="documents")
        group_names = list(cat_mgr.FILE_GROUPS.keys())
        ctk.CTkOptionMenu(dlg, variable=grp_var, values=group_names,
                          font=(FONT,11), height=30).pack(padx=20,anchor=_anchor(),pady=(4,8))

        # Needs OCR
        ocr_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(dlg, text=t("ft_ext_ocr"), font=(FONT,12), variable=ocr_var).pack(padx=20,anchor=_anchor(),pady=(0,12))

        def save():
            ext = ext_var.get().strip().lower()
            if not ext:
                return
            if not ext.startswith("."):
                ext = "." + ext
            desc = desc_var.get().strip() or ext
            self._filetypes[ext] = {
                "group": grp_var.get(),
                "label_en": desc,
                "label_ar": desc,
                "needs_ocr": ocr_var.get(),
                "enabled": True,
                "custom": True,
            }
            cat_mgr.save_filetypes(self._filetypes)
            dlg.destroy()
            self._render_filetypes()

        ctk.CTkButton(dlg, text=t("btn_save"), font=(FONT,13,"bold"), height=40,
                      fg_color=SUCCESS, hover_color="#15803D", command=save).pack(padx=20,fill="x",pady=(4,16))

    # ═══════════ SETTINGS PERSISTENCE ═══════════
    def _save_settings(self):
        data = {"sources":self._sources,"dest":self._dst.get(),"move":self._move.get(),
                "ocr":self._ocr.get(),"gpu":self._gpu.get(),"workers":self._workers.get(),
                "timeout":self._timeout.get(),"score":self._score.get(),
                "dedup":self._dedup.get(),"dedup_action":self._dedup_action.get(),
                "transcribe":self._transcribe.get(),"whisper_model":self._whisper_model.get(),
                "ffmpeg_path":self._ffmpeg_path.get(),
                "lang":get_lang(),"disabled":list(self._disabled)}
        try: self._settings_path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        except: pass

    def _load_settings(self):
        try:
            if self._settings_path.exists():
                d = json.loads(self._settings_path.read_text(encoding="utf-8"))
                # Multi-source (backward compat with old "source" key)
                if "sources" in d:
                    self._sources = [s for s in d["sources"] if isinstance(s,str)]
                elif "source" in d and d["source"]:
                    self._sources = [d["source"]]
                self._dst.set(d.get("dest",""))
                self._move.set(d.get("move",False)); self._ocr.set(d.get("ocr",True))
                self._gpu.set(d.get("gpu",False)); self._workers.set(d.get("workers",12))
                self._timeout.set(d.get("timeout",30)); self._score.set(d.get("score",5.0))
                self._dedup.set(d.get("dedup",False))
                self._dedup_action.set(d.get("dedup_action",t("dedup_move")))
                self._transcribe.set(d.get("transcribe",False))
                self._whisper_model.set(d.get("whisper_model","medium"))
                self._ffmpeg_path.set(d.get("ffmpeg_path",""))
                self._disabled = set(d.get("disabled",[]))
                lang = d.get("lang","en")
                if lang != get_lang(): set_lang(lang)
        except: pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
```

### File: `build.bat`
The content of `build.bat` is:
```bat
@echo off
setlocal enabledelayedexpansion
echo.
echo ════════════════════════════════════════════════
echo   Smart Document Categorizer — Portable Build
echo ════════════════════════════════════════════════
echo.
echo   For a proper setup.exe: run build_installer.bat
echo.

pip install -r requirements.txt >nul 2>&1
pip install pyinstaller >nul 2>&1

REM ffmpeg
if not exist "ffmpeg_bin\ffmpeg.exe" (
    echo Downloading ffmpeg...
    python setup_ffmpeg.py
)

set "FFMPEG_DATA="
if exist "ffmpeg_bin\ffmpeg.exe" set "FFMPEG_DATA=--add-data ffmpeg_bin\ffmpeg.exe;."

echo Building...
python -m PyInstaller --onedir ^
    --windowed ^
    --name "SmartDocCategorizer" ^
    --add-data "engine.py;." ^
    --add-data "i18n.py;." ^
    --add-data "categories.py;." ^
    --add-data "transcribe.py;." ^
    %FFMPEG_DATA% ^
    --hidden-import customtkinter ^
    --hidden-import CTkMessagebox ^
    --hidden-import docx ^
    --hidden-import pdfplumber ^
    --hidden-import openpyxl ^
    --hidden-import pptx ^
    --hidden-import PIL ^
    --hidden-import hashlib ^
    --collect-all customtkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --exclude-module pip ^
    --exclude-module setuptools ^
    --noupx ^
    app.py

if exist "dist\SmartDocCategorizer\SmartDocCategorizer.exe" (
    python cleanup_dist.py 2>nul
    echo.
    echo ═══════════════════════════════════════════
    echo   ✅ Portable build ready!
    echo   📂 dist\SmartDocCategorizer\
    echo ═══════════════════════════════════════════
) else (
    echo   ❌ BUILD FAILED
)
pause
```

### File: `BUILD_GUIDE.md`
The content of `BUILD_GUIDE.md` is:
```md
# BUILD GUIDE — Smart Document Categorizer

Complete instructions for building the Windows installer (.exe).

## Prerequisites

### 1. Python 3.12 (Recommended)

Python 3.14 has compatibility issues with PyInstaller. Use Python 3.12:

- Download: https://www.python.org/downloads/release/python-31211/
- Choose: "Windows installer (64-bit)"
- During install, check:
  - ✅ Add Python to PATH
  - ✅ Install for all users

If you have multiple Python versions, use `py -3.12` to target 3.12 specifically.

### 2. Inno Setup 6 (For installer — free)

- Download: https://jrsoftware.org/isinfo.php
- Install with default settings
- This creates the professional setup.exe installer

### 3. ffmpeg (For audio/video transcription)

Either:
- Run `python setup_ffmpeg.py` (auto-downloads ~90MB)
- Or download manually from https://www.gyan.dev/ffmpeg/builds/

## Build Options

### Option A: Full Installer (Recommended)

Creates a professional setup.exe with Start Menu shortcuts and uninstaller.

```cmd
cd SmartDocCategorizer
build_installer.bat
```

This automatically:
1. Installs Python dependencies
2. Downloads ffmpeg (if not present)
3. Cleans previous builds
4. Builds with PyInstaller (--onedir)
5. Removes unnecessary files (saves ~30-50%)
6. Creates installer with Inno Setup

Output: `installer_output/SmartDocCategorizer_Setup_v4.0.exe` (~80-120 MB)

### Option B: Portable Build

Creates a folder you can copy to any PC — no installation needed.

```cmd
cd SmartDocCategorizer
build.bat
```

Output: `dist/SmartDocCategorizer/SmartDocCategorizer.exe`

### Option C: Manual Build

If the batch files don't work:

```cmd
cd SmartDocCategorizer

REM 1. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

REM 2. Download ffmpeg
python setup_ffmpeg.py

REM 3. Build
python -m PyInstaller --onedir --windowed --name "SmartDocCategorizer" ^
    --add-data "engine.py;." ^
    --add-data "i18n.py;." ^
    --add-data "categories.py;." ^
    --add-data "transcribe.py;." ^
    --add-data "ffmpeg_bin\ffmpeg.exe;." ^
    --hidden-import customtkinter ^
    --hidden-import CTkMessagebox ^
    --hidden-import docx ^
    --hidden-import pdfplumber ^
    --hidden-import openpyxl ^
    --hidden-import pptx ^
    --hidden-import PIL ^
    --hidden-import hashlib ^
    --collect-all customtkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pytest ^
    --noupx ^
    app.py

REM 4. Clean (optional)
python cleanup_dist.py

REM 5. Create installer (optional — requires Inno Setup)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## Custom App Icon

To add your own icon:
1. Create a 256x256 PNG image
2. Convert to .ico format (use https://convertio.co/png-ico/)
3. Save as `icon.ico` in the project folder
4. Rebuild — the installer will use it automatically

## Expected File Sizes

| Build Type | Size | Startup Time |
|---|---|---|
| PyInstaller --onefile (old) | ~432 MB | 15-30 seconds |
| PyInstaller --onedir (portable) | ~200 MB folder | 2-3 seconds |
| Inno Setup installer | ~80-120 MB | 2-3 seconds (after install) |

## Troubleshooting

### "failed to start embedded python interpreter"
- Cause: Python 3.14 incompatibility with PyInstaller
- Fix: Install and use Python 3.12

### "pyinstaller is not recognized"
- Fix: Use `python -m PyInstaller` instead of `pyinstaller`

### "NoneType object has no attribute write"
- Cause: PyInstaller --windowed sets sys.stderr=None
- Fix: Already handled in engine.py (_suppress_stderr)

### Blank screen when changing language
- Fix: Already handled in app.py (_rebuild_ui with column reset)

### Build is too large
- Run `python cleanup_dist.py` after PyInstaller
- Use `--exclude-module` for unused packages
- The cleanup script removes test files, docs, and type stubs

### ffmpeg not working
- Run `python setup_ffmpeg.py` to download
- Or manually place ffmpeg.exe in the `ffmpeg_bin/` folder
- The app auto-detects ffmpeg from bundled path, then system PATH

## GPU Support

For GPU acceleration (OCR + Whisper 5-10x faster):

```cmd
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

The app auto-detects GPU. If GPU fails, it falls back to CPU automatically.
```

### File: `build_installer.bat`
The content of `build_installer.bat` is:
```bat
@echo off
setlocal enabledelayedexpansion
echo.
echo ========================================================
echo   Smart Document Categorizer - Installer Builder
echo ========================================================
echo.

REM -- Check Python version --
python --version 2>nul | findstr "3.14" >nul
if %errorlevel% equ 0 (
    echo [WARNING] Python 3.14 detected - may have PyInstaller issues.
    echo Recommended: use Python 3.12 for building.
    echo.
    set /p "CONT=Continue with 3.14 anyway? (y/n): "
    if /i not "!CONT!"=="y" exit /b 1
)

REM -- Step 1: Install dependencies --
echo [1/5] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller
echo        Done.
echo.

REM -- Step 2: Setup ffmpeg --
echo [2/5] Checking ffmpeg...
if exist "ffmpeg_bin\ffmpeg.exe" (
    echo        ffmpeg already present.
) else (
    echo        Downloading ffmpeg...
    python setup_ffmpeg.py
)
echo.

REM -- Step 3: Clean previous builds --
echo [3/5] Cleaning previous builds...
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist\SmartDocCategorizer" rmdir /s /q "dist\SmartDocCategorizer" >nul 2>&1
echo        Done.
echo.

REM -- Step 4: Build with PyInstaller --
echo [4/5] Building application (this may take a few minutes)...
echo.

set "FFMPEG_DATA="
if exist "ffmpeg_bin\ffmpeg.exe" (
    set "FFMPEG_DATA=--add-data ffmpeg_bin\ffmpeg.exe;."
)

REM The PyInstaller command must be on one single line (distutils removed!)
python -m PyInstaller --onedir --windowed --name "SmartDocCategorizer" --icon="icon.ico" --add-data "icon.ico;." --add-data "engine.py;." --add-data "i18n.py;." --add-data "categories.py;." --add-data "transcribe.py;." %FFMPEG_DATA% --hidden-import customtkinter --hidden-import CTkMessagebox --hidden-import docx --hidden-import pdfplumber --hidden-import openpyxl --hidden-import pptx --hidden-import PIL --hidden-import hashlib --collect-all customtkinter --exclude-module matplotlib --exclude-module scipy --exclude-module numpy.tests --exclude-module setuptools --exclude-module pip --exclude-module pytest --exclude-module unittest --exclude-module tkinter.test --noupx app.py

if not exist "dist\SmartDocCategorizer\SmartDocCategorizer.exe" (
    echo.
    echo ===================================
    echo   BUILD FAILED - check errors above
    echo ===================================
    pause
    exit /b 1
)

echo.
echo        PyInstaller build complete.
echo        Cleaning dist folder...
python cleanup_dist.py 2>nul
echo.

REM -- Step 5: Create installer with Inno Setup --
echo [5/5] Creating installer...
echo.

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "!ISCC!"=="" (
    echo    Inno Setup not found.
    echo    Your app is ready as portable in: dist\SmartDocCategorizer\
    pause
    exit /b 0
)

if not exist "installer_output" mkdir "installer_output"

if not exist "icon.ico" (
    powershell -Command "(Get-Content installer.iss) -replace 'SetupIconFile=icon.ico', '; SetupIconFile=icon.ico' | Set-Content installer_temp.iss"
    "!ISCC!" installer_temp.iss
    del installer_temp.iss >nul 2>&1
) else (
    "!ISCC!" installer.iss
)

echo.
echo ========================================================
if exist "installer_output\SmartDocCategorizer_Setup_v1.0.exe" (
    echo   SUCCESS: INSTALLER CREATED!
    echo   Location: installer_output\SmartDocCategorizer_Setup_v1.0.exe
) else (
    echo   Installer creation failed. Portable build is in: dist\SmartDocCategorizer\
)
echo ========================================================
pause
```

### File: `categories.py`
The content of `categories.py` is:
```py
"""
categories.py — Dynamic category management with job role presets
"""

import json
from pathlib import Path
from copy import deepcopy

CATS_FILE = Path.home() / ".smart_categorizer_categories.json"

# ═══════════════════════════════════════════════
#  DEFAULT CATEGORIES (same as engine.py v3.2)
# ═══════════════════════════════════════════════

_DEFAULTS = {
"01_Enterprise_Architecture": {
    "pp":"HIGH", "personal": False,
    "en":{"enterprise architecture":5,"togaf":5,"archimate":5,"togaf adm":5,"architecture framework":4,"capability map":4,"capability model":4,"business architecture":4,"data architecture":4,"technology architecture":4,"application architecture":4,"architecture vision":4,"target architecture":4,"reference architecture":4,"solution architecture":4,"architecture governance":4,"zachman framework":5},
    "ar":{"بنية مؤسسية":5,"البنية المؤسسية":5,"معمارية الحلول":4,"معمارية تقنية":4,"معمارية البيانات":4,"معمارية التطبيقات":4,"خارطة القدرات":4,"المعمارية المرجعية":4,"حوكمة المعمارية":4},
    "fh":["togaf","archimate","enterprise_arch","capability_map"],"ph":["architecture","togaf","enterprise_architecture"],
    "neg_en":["story","novel","children","kids","fairy","coloring","senses","ears","tales","isbn"],"neg_ar":["قصة","رواية","اطفال","تلوين","حكاية"],
},
"02_Digital_Transformation": {
    "pp":"HIGH","personal":False,
    "en":{"digital transformation":5,"digital strategy":5,"digital maturity":4,"maturity model":3,"maturity assessment":4,"digital roadmap":4,"e-government":4,"smart government":4,"digital governance":4,"dga standards":5,"legacy modernization":4,"cloud migration":3},
    "ar":{"التحول الرقمي":5,"تحول رقمي":5,"الحكومة الرقمية":4,"الخدمات الرقمية":4,"النضج الرقمي":4,"الاستراتيجية الرقمية":5,"الحكومة الالكترونية":4,"هيئة الحكومة الرقمية":5,"الرقمنة":4,"المنصات الرقمية":4},
    "fh":["digital_transform","digitalization","dga_standards"],"ph":["digital_transformation","digitalization"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"03_Project_Management_PMO": {
    "pp":"HIGH","personal":False,
    "en":{"project management":4,"project charter":5,"project plan":4,"pmo":4,"pmbok":5,"prince2":5,"work breakdown structure":5,"wbs":3,"gantt chart":5,"critical path":4,"risk register":5,"risk management plan":5,"change request":4,"lessons learned":4,"project closure":4,"stakeholder register":4,"agile methodology":4,"scrum master":4,"sprint planning":4},
    "ar":{"ادارة مشاريع":5,"ادارة المشاريع":5,"مكتب ادارة المشاريع":5,"ميثاق المشروع":5,"خطة المشروع":4,"سجل المخاطر":5,"ادارة المخاطر":4,"هيكل تجزئة العمل":5,"الدروس المستفادة":4},
    "fh":["project_plan","project_charter","pmo_","gantt","wbs_","risk_register","pmbok"],"ph":["project_management","pmo","projects"],
    "neg_en":["story","novel","children","kids","hero","fairy","senses","coloring","reading","book","isbn"],"neg_ar":["قصة","رواية","اطفال","تلوين","بطل","حكاية","ابطال"],
},
"04_Business_Analysis": {
    "pp":"HIGH","personal":False,
    "en":{"business analysis":4,"business requirements document":5,"functional requirements":4,"non-functional requirements":4,"use case diagram":5,"user story":3,"acceptance criteria":4,"brd":3,"frd":3,"gap analysis":4,"business process":3,"bpmn":4,"process mapping":4,"feasibility study":4,"cost-benefit analysis":4},
    "ar":{"تحليل اعمال":5,"تحليل الاعمال":5,"المتطلبات الوظيفية":4,"تحليل الفجوات":4,"دراسة جدوى":4,"حالات الاستخدام":4,"متطلبات العمل":4},
    "fh":["brd_","frd_","requirements_","gap_analysis","use_case"],"ph":["business_analysis","requirements"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"05_Consulting_Deliverables": {
    "pp":"HIGH","personal":False,
    "en":{"consulting engagement":4,"consulting deliverable":4,"advisory report":4,"assessment report":4,"current state assessment":5,"strategic assessment":4,"implementation roadmap":5,"transformation roadmap":5,"workshop facilitation":4,"benchmarking study":4,"best practices":2,"recommendations":2},
    "ar":{"استشارات":3,"تقييم استراتيجي":4,"تقييم الوضع الحالي":5,"ورشة عمل":3,"خارطة طريق التنفيذ":5,"افضل الممارسات":3,"توصيات":2,"مخرجات استشارية":5},
    "fh":["consulting_","advisory_","deliverable_","assessment_"],"ph":["consulting","advisory","engagements"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"06_Strategy_Planning": {
    "pp":"HIGH","personal":False,
    "en":{"strategic plan":4,"strategic planning":4,"swot analysis":5,"pestle analysis":5,"balanced scorecard":5,"okr framework":4,"competitive analysis":4,"market analysis":3,"value chain":4,"business model canvas":5,"it strategy":4,"technology strategy":4,"strategic initiative":4},
    "ar":{"خطة استراتيجية":5,"التخطيط الاستراتيجي":5,"تحليل سوات":5,"مؤشرات الاداء الرئيسية":5,"بطاقة الاداء المتوازن":5,"تحليل تنافسي":4,"الاهداف الاستراتيجية":4},
    "fh":["strategy_","strategic_","swot","pestle"],"ph":["strategy","strategic_planning"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"07_Product_Development": {
    "pp":"HIGH","personal":False,
    "en":{"product development":4,"product roadmap":5,"product strategy":4,"product requirements document":5,"minimum viable product":5,"mvp":3,"go-to-market":4,"product-market fit":4,"product launch plan":5,"product lifecycle":4,"customer journey map":4,"user persona":4},
    "ar":{"تطوير المنتج":4,"خارطة طريق المنتج":5,"استراتيجية المنتج":4,"اطلاق المنتج":4,"دورة حياة المنتج":4,"رحلة العميل":4},
    "fh":["product_roadmap","prd_","product_strategy","mvp_"],"ph":["product_development","product_management"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"08_IT_Governance_Compliance": {
    "pp":"MEDIUM","personal":False,
    "en":{"it governance":4,"cobit":5,"itil":4,"iso 27001":5,"iso 20000":4,"information security":4,"cybersecurity":3,"data governance":4,"business continuity plan":5,"disaster recovery plan":5,"isms":4},
    "ar":{"حوكمة تقنية المعلومات":5,"حوكمة تقنية":4,"امن المعلومات":4,"الامن السيبراني":4,"استمرارية الاعمال":4,"التعافي من الكوارث":4},
    "fh":["governance_","cobit","itil","iso27","isms"],"ph":["governance","compliance","information_security"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"09_Proposals_Tenders_RFPs": {
    "pp":"HIGH","personal":False,
    "en":{"request for proposal":5,"rfp":3,"rfq":3,"tender document":5,"bid submission":4,"technical proposal":5,"financial proposal":5,"scope of work":4,"evaluation criteria":4},
    "ar":{"كراسة الشروط":5,"كراسة شروط":5,"عرض فني":5,"عرض مالي":5,"مناقصة":4,"عطاء":3,"نطاق العمل":4,"المواصفات الفنية":4,"جدول الكميات":4},
    "fh":["proposal_","rfp_","rfq_","tender_","bid_"],"ph":["proposals","tenders","rfp","bids"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"10_Finance_Budgets": {
    "pp":"MEDIUM","personal":False,
    "en":{"budget plan":4,"financial statement":4,"invoice":3,"cost estimate":4,"revenue forecast":4,"profit and loss":4,"balance sheet":4,"cash flow":3},
    "ar":{"ميزانية":3,"موازنة تقديرية":4,"فاتورة":3,"قائمة الدخل":4,"التدفق النقدي":4,"البيانات المالية":4},
    "fh":["budget_","financial_","invoice_","cost_estimate"],"ph":["finance","budget","accounting"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"11_Contracts_Legal": {
    "pp":"LOW","personal":False,
    "en":{"contract agreement":4,"non-disclosure agreement":5,"terms and conditions":4,"indemnification":4,"governing law":4,"confidentiality agreement":5,"service level agreement":5},
    "ar":{"عقد اتفاقية":4,"اتفاقية عدم افشاء":5,"الشروط والاحكام":4,"اتفاقية سرية":4},
    "fh":["contract_","agreement_","nda_","sla_"],"ph":["legal","contracts"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"12_HR_People": {
    "pp":"LOW","personal":False,
    "en":{"human resources":4,"job description":4,"performance review":4,"onboarding":3,"payroll":3,"salary structure":4,"recruitment":3},
    "ar":{"موارد بشرية":4,"الوصف الوظيفي":4,"تقييم الاداء":4,"الهيكل التنظيمي":4,"سلم الرواتب":4},
    "fh":["hr_","employee_","job_desc","payroll_"],"ph":["human_resources","hr"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"13_Reports_Presentations": {
    "pp":"MEDIUM","personal":False,
    "en":{"executive summary":4,"annual report":4,"quarterly report":4,"status report":3,"progress report":3,"dashboard":3},
    "ar":{"تقرير سنوي":4,"تقرير ربع سنوي":4,"الملخص التنفيذي":4,"عرض تقديمي":3,"لوحة متابعة":3},
    "fh":["report_","presentation_","dashboard_"],"ph":["reports","presentations"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"14_Training_Knowledge": {
    "pp":"HIGH","personal":False,
    "en":{"training material":4,"training course":4,"curriculum":3,"e-learning":4,"lms":3,"knowledge transfer":4,"instructional design":4},
    "ar":{"حقيبة تدريبية":5,"مادة تدريبية":5,"دورة تدريبية":4,"نقل المعرفة":4,"محتوى تعليمي":4},
    "fh":["training_","course_","workshop_material"],"ph":["training","courses","learning"],
    "neg_en":["story","novel","children","kids","fairy","coloring"],"neg_ar":["قصة","رواية","اطفال","تلوين"],
},
"15_Meeting_Communications": {
    "pp":"LOW","personal":False,
    "en":{"meeting minutes":5,"meeting agenda":4,"action items":4,"memorandum":4,"memo":2,"attendees":3},
    "ar":{"محضر اجتماع":5,"جدول الاعمال":4,"مذكرة":3,"توصيات الاجتماع":4},
    "fh":["minutes_","meeting_","memo_","agenda_"],"ph":["meetings","minutes"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"16_LMS_ELearning": {
    "pp":"HIGH","personal":False,
    "en":{"learning management system":5,"scorm":5,"xapi":4,"tin can":4,"moodle":4,"instructional design":4},
    "ar":{"نظام ادارة التعلم":5,"التعلم الالكتروني":4,"تصميم تعليمي":4},
    "fh":["lms_","scorm_","elearning_"],"ph":["lms","elearning"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"17_Infrastructure_Technical": {
    "pp":"MEDIUM","personal":False,
    "en":{"server infrastructure":4,"network architecture":4,"cloud computing":4,"aws":2,"azure":2,"kubernetes":3,"docker":3,"devops":3,"database design":4,"ci/cd pipeline":4},
    "ar":{"البنية التحتية":4,"الحوسبة السحابية":4,"قواعد البيانات":3,"مركز البيانات":4},
    "fh":["infrastructure_","server_","network_","cloud_"],"ph":["infrastructure","technical","devops"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"18_Policies_Procedures": {
    "pp":"MEDIUM","personal":False,
    "en":{"standard operating procedure":5,"sop":3,"policy document":4,"code of conduct":4,"quality management":4,"guideline":2},
    "ar":{"اجراءات التشغيل":4,"سياسة":2,"دليل ارشادي":4,"دليل العمل":4,"لائحة تنظيمية":4},
    "fh":["policy_","procedure_","sop_","guideline_"],"ph":["policies","procedures"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"19_Personal_Books": {
    "pp":"NONE","personal":True,
    "en":{"once upon a time":5,"fairy tale":5,"bedtime story":5,"chapter one":4,"chapter two":4,"novel":3,"fiction":3,"isbn":5,"published by":4,"oxford read":5,"read and discover":5,"graded reader":5,"penguin readers":5,"story":2,"stories":2,"tale":2,"the end":2,"happily ever after":5},
    "ar":{"رواية":4,"قصة قصيرة":4,"كان يا مكان":5,"كان ياما كان":5,"كتاب":2,"ادب":3,"شعر":3,"ديوان":4,"دار النشر":5,"المؤلف":3,"الطبعة":4},
    "fh":["book","novel","story","ebook","reader","tales","كتاب","رواية","قصة"],"ph":["books","novels","ebooks","stories","reading","كتب","روايات","قصص"],
    "neg_en":[],"neg_ar":[],
},
"20_Kids_Activities": {
    "pp":"NONE","personal":True,
    "en":{"for kids":5,"for children":5,"coloring":4,"colouring":4,"worksheet":3,"homework":3,"kindergarten":4,"preschool":4,"activity book":5,"phonics":4,"alphabet":3,"counting":3,"read and discover":4,"talking ears":4,"five senses":3},
    "ar":{"اطفال":4,"للاطفال":5,"قصص اطفال":5,"انشطة":3,"تلوين":4,"مدرسة":3,"حضانة":4,"روضة":4,"الابن":3,"بطل":2,"مغامرات":3,"تعليم اطفال":5},
    "fh":["kids","children","child","activity","coloring","worksheet","school","اطفال","انشطة","تلوين"],"ph":["kids","children","school","activities","nursery","اطفال","مدرسة"],
    "neg_en":[],"neg_ar":[],
},
"21_Personal_Documents": {
    "pp":"NONE","personal":True,
    "en":{"curriculum vitae":5,"resume":3,"passport":4,"birth certificate":5,"marriage certificate":5,"insurance policy":4,"medical record":4,"visa application":4,"driving license":4},
    "ar":{"سيرة ذاتية":5,"جواز سفر":4,"جواز":3,"شهادة ميلاد":5,"شهادة زواج":5,"تأمين":3,"تأشيرة":3,"هوية":3,"اقامة":3,"رخصة قيادة":4},
    "fh":["cv","resume","personal","passport","certificate","سيرة","جواز","شخصي"],"ph":["personal","private","family","شخصي","عائلي","وثائق"],
    "neg_en":[],"neg_ar":[],
},
"22_Templates_Reusable": {
    "pp":"VERY_HIGH","personal":False,
    "en":{"template":3,"boilerplate":4,"toolkit":3,"checklist":3,"reusable":3,"framework template":5},
    "ar":{"قالب":4,"نموذج جاهز":5,"قوالب":4,"حقيبة ادوات":4,"قائمة مراجعة":4},
    "fh":["template_","tmpl_","toolkit_","checklist_"],"ph":["templates","toolkits"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"23_Diagrams_Visuals": {
    "pp":"MEDIUM","personal":False,
    "en":{"diagram":2,"flowchart":3,"uml diagram":4,"sequence diagram":4,"network diagram":4},
    "ar":{"رسم توضيحي":3,"مخطط انسيابي":4},
    "fh":["diagram_","flowchart_","uml_"],"ph":["diagrams","visuals"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
}


# ═══════════════════════════════════════════════
#  JOB ROLE PRESETS
# ═══════════════════════════════════════════════
#  Each preset is a list of category keys from _DEFAULTS
#  + any extra role-specific categories

_COMMON_PERSONAL = ["19_Personal_Books","20_Kids_Activities","21_Personal_Documents"]
_COMMON_BUSINESS = ["06_Strategy_Planning","10_Finance_Budgets","11_Contracts_Legal",
                    "12_HR_People","13_Reports_Presentations","15_Meeting_Communications",
                    "18_Policies_Procedures","22_Templates_Reusable"]

ROLE_PRESETS = {
    "CTO / VP Engineering": {
        "en": "CTO / VP Engineering",
        "ar": "مدير تقنية / نائب رئيس هندسة",
        "cats": list(_DEFAULTS.keys()),  # all categories
    },
    "Project Manager / PMO": {
        "en": "Project Manager / PMO",
        "ar": "مدير مشاريع / مكتب إدارة المشاريع",
        "cats": ["03_Project_Management_PMO","04_Business_Analysis","05_Consulting_Deliverables",
                 "09_Proposals_Tenders_RFPs"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
    },
    "Enterprise Architect": {
        "en": "Enterprise Architect",
        "ar": "مهندس بنية مؤسسية",
        "cats": ["01_Enterprise_Architecture","02_Digital_Transformation","04_Business_Analysis",
                 "08_IT_Governance_Compliance","17_Infrastructure_Technical","23_Diagrams_Visuals"
                 ] + _COMMON_BUSINESS + _COMMON_PERSONAL,
    },
    "Business Analyst": {
        "en": "Business Analyst",
        "ar": "محلل أعمال",
        "cats": ["04_Business_Analysis","03_Project_Management_PMO","05_Consulting_Deliverables",
                 "09_Proposals_Tenders_RFPs","23_Diagrams_Visuals"
                 ] + _COMMON_BUSINESS + _COMMON_PERSONAL,
    },
    "Digital Transformation Lead": {
        "en": "Digital Transformation Lead",
        "ar": "قائد التحول الرقمي",
        "cats": ["02_Digital_Transformation","01_Enterprise_Architecture","06_Strategy_Planning",
                 "08_IT_Governance_Compliance","05_Consulting_Deliverables"
                 ] + _COMMON_BUSINESS + _COMMON_PERSONAL,
    },
    "Software Developer / Engineer": {
        "en": "Software Developer / Engineer",
        "ar": "مطور / مهندس برمجيات",
        "cats": ["17_Infrastructure_Technical","07_Product_Development","23_Diagrams_Visuals",
                 "14_Training_Knowledge","22_Templates_Reusable"
                 ] + _COMMON_PERSONAL,
        "extra": {
            "Dev_Code_Repositories": {
                "pp":"MEDIUM","personal":False,
                "en":{"source code":4,"repository":3,"git":3,"github":3,"pull request":4,"code review":4,"api documentation":4,"readme":3,"changelog":3},
                "ar":{"كود مصدري":4,"مستودع":3},
                "fh":["readme","changelog","api_doc"],"ph":["src","code","repos"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Marketing Manager": {
        "en": "Marketing Manager",
        "ar": "مدير تسويق",
        "cats": ["07_Product_Development","13_Reports_Presentations"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
        "extra": {
            "Marketing_Campaigns": {
                "pp":"HIGH","personal":False,
                "en":{"marketing campaign":5,"brand guidelines":5,"social media":4,"content calendar":4,"seo":3,"google analytics":4,"email marketing":4,"press release":4,"media kit":4,"target audience":4,"brand identity":4,"advertising":3,"conversion rate":4,"marketing funnel":4},
                "ar":{"حملة تسويقية":5,"هوية بصرية":4,"وسائل التواصل":4,"تسويق رقمي":4,"اعلان":3,"جمهور مستهدف":4},
                "fh":["campaign_","marketing_","brand_","social_"],"ph":["marketing","campaigns","brand"],
                "neg_en":[],"neg_ar":[],
            },
            "Design_Creative": {
                "pp":"MEDIUM","personal":False,
                "en":{"design brief":4,"creative brief":4,"mockup":3,"wireframe":3,"brand book":4,"style guide":4,"logo":3,"typography":3,"color palette":3},
                "ar":{"تصميم":2,"هوية بصرية":4,"شعار":3,"دليل الهوية":4},
                "fh":["design_","creative_","brand_","logo_"],"ph":["design","creative","branding"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Accountant / Finance": {
        "en": "Accountant / Finance",
        "ar": "محاسب / مالية",
        "cats": ["10_Finance_Budgets","11_Contracts_Legal"] + _COMMON_PERSONAL,
        "extra": {
            "Accounting_Records": {
                "pp":"LOW","personal":False,
                "en":{"general ledger":5,"journal entry":5,"accounts payable":5,"accounts receivable":5,"trial balance":5,"chart of accounts":5,"depreciation":4,"tax return":5,"vat":3,"audit report":5,"reconciliation":4,"fiscal year":3},
                "ar":{"دفتر الاستاذ":5,"قيد يومية":5,"ذمم دائنة":5,"ذمم مدينة":5,"ميزان المراجعة":5,"شجرة الحسابات":5,"اهلاك":4,"ضريبة":3,"تقرير مراجعة":5},
                "fh":["ledger_","journal_","tax_","audit_","vat_"],"ph":["accounting","ledger","tax","audit"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "HR Manager": {
        "en": "HR Manager",
        "ar": "مدير موارد بشرية",
        "cats": ["12_HR_People","11_Contracts_Legal","14_Training_Knowledge",
                 "18_Policies_Procedures"] + _COMMON_PERSONAL,
        "extra": {
            "HR_Recruitment": {
                "pp":"MEDIUM","personal":False,
                "en":{"job posting":4,"candidate screening":4,"interview scorecard":5,"offer letter":5,"employment contract":5,"background check":4,"talent pipeline":4,"succession plan":4,"competency framework":5,"organizational chart":4},
                "ar":{"اعلان وظيفي":4,"مقابلة":3,"عرض وظيفي":5,"عقد عمل":5,"تقييم مرشح":4,"الهيكل التنظيمي":4,"خطة التعاقب":4,"اطار الكفاءات":5},
                "fh":["recruitment_","candidate_","offer_","interview_"],"ph":["recruitment","hiring","talent"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Teacher / Educator": {
        "en": "Teacher / Educator",
        "ar": "معلم / مدرس",
        "cats": ["14_Training_Knowledge","16_LMS_ELearning"] + _COMMON_PERSONAL,
        "extra": {
            "Lesson_Plans": {
                "pp":"HIGH","personal":False,
                "en":{"lesson plan":5,"unit plan":4,"learning objectives":4,"assessment rubric":5,"curriculum map":5,"differentiation":3,"classroom management":4,"student assessment":4,"grading":3,"syllabus":4,"semester plan":4},
                "ar":{"خطة درس":5,"خطة وحدة":4,"اهداف تعليمية":4,"معايير تقييم":5,"المنهج":3,"تقييم الطلاب":4,"فصل دراسي":3},
                "fh":["lesson_","syllabus_","rubric_","curriculum_"],"ph":["lessons","curriculum","teaching"],
                "neg_en":[],"neg_ar":[],
            },
            "Student_Records": {
                "pp":"NONE","personal":False,
                "en":{"student record":4,"transcript":4,"grade report":4,"attendance":3,"parent communication":4,"iep":4,"report card":4},
                "ar":{"سجل طالب":4,"كشف درجات":4,"حضور وغياب":4,"تقرير اداء":3,"ولي امر":3},
                "fh":["student_","grades_","attendance_","transcript_"],"ph":["students","grades","records"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Lawyer / Legal": {
        "en": "Lawyer / Legal",
        "ar": "محامي / قانوني",
        "cats": ["11_Contracts_Legal","18_Policies_Procedures"] + _COMMON_PERSONAL,
        "extra": {
            "Legal_Cases": {
                "pp":"LOW","personal":False,
                "en":{"case file":5,"legal brief":5,"court filing":5,"litigation":4,"deposition":4,"affidavit":5,"judgment":4,"settlement":4,"plaintiff":4,"defendant":4,"statute":4,"precedent":4,"legal opinion":5},
                "ar":{"ملف قضية":5,"مذكرة قانونية":5,"دعوى":4,"حكم":3,"تسوية":4,"شهادة":3,"رأي قانوني":5,"نظام":3,"لائحة":3},
                "fh":["case_","legal_","court_","litigation_"],"ph":["cases","litigation","court","legal"],
                "neg_en":[],"neg_ar":[],
            },
            "Legal_Research": {
                "pp":"MEDIUM","personal":False,
                "en":{"legal research":4,"case law":4,"regulatory analysis":4,"compliance review":4,"legal memorandum":5,"due diligence":5,"intellectual property":4},
                "ar":{"بحث قانوني":4,"تحليل تنظيمي":4,"العناية الواجبة":5,"ملكية فكرية":4},
                "fh":["research_","memo_","due_diligence"],"ph":["research","compliance"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "General / Personal Use": {
        "en": "General / Personal Use",
        "ar": "استخدام عام / شخصي",
        "cats": _COMMON_PERSONAL + ["13_Reports_Presentations","22_Templates_Reusable"],
        "extra": {
            "Photos_Media": {
                "pp":"NONE","personal":True,
                "en":{"photo":2,"picture":2,"image":2,"video":2,"screenshot":3,"wallpaper":2},
                "ar":{"صورة":2,"صور":2,"فيديو":2,"لقطة شاشة":3},
                "fh":["photo","img_","screenshot","pic_"],"ph":["photos","pictures","media","صور"],
                "neg_en":[],"neg_ar":[],
            },
            "Recipes_Home": {
                "pp":"NONE","personal":True,
                "en":{"recipe":4,"ingredients":3,"cooking":3,"baking":3,"tablespoon":3,"teaspoon":3,"preheat":4,"servings":3},
                "ar":{"وصفة":4,"مقادير":3,"طبخ":3,"خبز":3,"ملعقة":2},
                "fh":["recipe_","cooking_"],"ph":["recipes","cooking","kitchen","وصفات","طبخ"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    # ── NEW ROLES ──
    "PhD / Researcher": {
        "en": "PhD / Researcher / Academic",
        "ar": "باحث / أكاديمي / دكتوراه",
        "cats": ["13_Reports_Presentations","14_Training_Knowledge","06_Strategy_Planning"] + _COMMON_PERSONAL,
        "extra": {
            "Research_Papers": {
                "pp":"HIGH","personal":False,
                "en":{"abstract":4,"literature review":5,"methodology":4,"hypothesis":4,"findings":3,"peer review":5,"journal":3,"publication":4,"citation":4,"references":3,"doi":4,"research paper":5,"thesis":5,"dissertation":5,"conference paper":5,"systematic review":5,"meta-analysis":5,"research proposal":5,"bibliography":4,"appendix":2,"acknowledgments":2},
                "ar":{"ملخص البحث":5,"مراجعة الادبيات":5,"منهجية البحث":5,"فرضية":4,"نتائج البحث":4,"مجلة علمية":4,"رسالة ماجستير":5,"رسالة دكتوراه":5,"اطروحة":5,"بحث علمي":5,"مؤتمر":3,"مرجع":3,"اقتباس":3,"خطة بحثية":5},
                "fh":["paper_","thesis_","research_","dissertation_","journal_"],"ph":["research","papers","thesis","academic","بحث","رسالة","اطروحة"],
                "neg_en":["story","novel","kids","coloring"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Academic_Teaching": {
                "pp":"HIGH","personal":False,
                "en":{"lecture notes":5,"course syllabus":5,"exam paper":5,"quiz":3,"assignment":3,"grading rubric":4,"academic calendar":4,"office hours":3,"tutorial":3,"seminar":4,"lab report":4,"field study":4},
                "ar":{"محاضرة":4,"منهج دراسي":5,"امتحان":4,"اختبار":3,"واجب":3,"معايير التصحيح":4,"تقويم اكاديمي":4,"تقرير مختبر":4,"دراسة ميدانية":4,"حلقة بحث":4},
                "fh":["lecture_","exam_","syllabus_","course_","lab_"],"ph":["lectures","exams","courses","academic","محاضرات","امتحانات"],
                "neg_en":[],"neg_ar":[],
            },
            "Grants_Funding": {
                "pp":"HIGH","personal":False,
                "en":{"grant proposal":5,"funding application":5,"research grant":5,"budget justification":4,"principal investigator":4,"co-investigator":4,"grant report":4,"progress report":3,"impact factor":4,"h-index":3},
                "ar":{"منحة بحثية":5,"طلب تمويل":5,"ميزانية بحث":4,"باحث رئيسي":4,"تقرير منحة":4},
                "fh":["grant_","funding_","proposal_"],"ph":["grants","funding"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "AV Manager / Audiovisual": {
        "en": "AV Manager / Audiovisual",
        "ar": "مدير سمعي بصري / AV",
        "cats": ["17_Infrastructure_Technical","09_Proposals_Tenders_RFPs","23_Diagrams_Visuals"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
        "extra": {
            "AV_Systems_Design": {
                "pp":"HIGH","personal":False,
                "en":{"audiovisual":5,"av system":5,"av design":5,"display system":4,"projector":4,"sound system":5,"audio system":5,"video conferencing":5,"digital signage":5,"control system":5,"crestron":5,"extron":5,"biamp":4,"qsc":4,"shure":4,"dante":4,"hdmi":3,"av matrix":4,"av rack":4,"signal flow":4,"av integration":5},
                "ar":{"نظام سمعي بصري":5,"تصميم صوتي":4,"نظام عرض":4,"مؤتمرات فيديو":5,"لافتات رقمية":4,"نظام تحكم":4,"تكامل سمعي بصري":5,"نظام صوت":4},
                "fh":["av_","audiovisual_","sound_","display_","projector_"],"ph":["av","audiovisual","av_systems","سمعي_بصري"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "AV_Specs_BOQ": {
                "pp":"HIGH","personal":False,
                "en":{"bill of quantities":5,"boq":4,"av specification":5,"technical specification":4,"equipment list":4,"rack elevation":4,"cable schedule":4,"commissioning":4,"as-built":4,"riser diagram":4,"av tender":4},
                "ar":{"جدول كميات":5,"مواصفات فنية":5,"قائمة معدات":4,"جدول كابلات":4,"تشغيل وتسليم":4,"مخطط رايزر":4},
                "fh":["boq_","spec_","equipment_","cable_","commissioning_"],"ph":["specifications","boq","equipment"],
                "neg_en":[],"neg_ar":[],
            },
            "Events_Venues": {
                "pp":"MEDIUM","personal":False,
                "en":{"event setup":4,"venue":3,"stage design":4,"lighting design":4,"live streaming":4,"broadcast":3,"led wall":4,"rigging":4,"stage plot":4,"event production":4,"technical rider":5},
                "ar":{"تجهيز فعالية":4,"تصميم مسرح":4,"اضاءة":3,"بث مباشر":4,"انتاج فعاليات":4,"متطلبات فنية":4},
                "fh":["event_","venue_","stage_","lighting_"],"ph":["events","venues","production","فعاليات"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Content Creator / Influencer": {
        "en": "Content Creator / Influencer",
        "ar": "صانع محتوى / مؤثر",
        "cats": ["07_Product_Development","13_Reports_Presentations","23_Diagrams_Visuals"] + _COMMON_PERSONAL,
        "extra": {
            "Content_Planning": {
                "pp":"HIGH","personal":False,
                "en":{"content calendar":5,"editorial calendar":5,"content strategy":5,"content plan":4,"content pillar":4,"posting schedule":4,"social media plan":4,"content brief":4,"content audit":4,"evergreen content":4,"content repurposing":4},
                "ar":{"تقويم محتوى":5,"خطة محتوى":5,"استراتيجية محتوى":5,"جدول نشر":4,"اعمدة المحتوى":4,"محتوى دائم":4},
                "fh":["content_","editorial_","calendar_","posting_"],"ph":["content","editorial","planning","محتوى"],
                "neg_en":["story","novel","isbn"],"neg_ar":["رواية","قصة"],
            },
            "Scripts_Storyboards": {
                "pp":"HIGH","personal":False,
                "en":{"script":3,"storyboard":5,"shot list":4,"video script":5,"podcast script":4,"voiceover":4,"thumbnail":3,"intro":2,"outro":2,"call to action":3,"hook":3,"b-roll":4,"talking head":3},
                "ar":{"سكربت":4,"نص فيديو":5,"لوحة قصة":5,"قائمة لقطات":4,"تعليق صوتي":4,"صورة مصغرة":3,"مقدمة":2},
                "fh":["script_","storyboard_","video_","podcast_"],"ph":["scripts","storyboards","videos","podcasts"],
                "neg_en":[],"neg_ar":[],
            },
            "Analytics_Growth": {
                "pp":"MEDIUM","personal":False,
                "en":{"analytics report":4,"engagement rate":4,"subscriber":3,"follower":3,"impressions":3,"reach":3,"click-through rate":4,"ctr":3,"monetization":4,"sponsorship":4,"brand deal":4,"media kit":5,"rate card":4},
                "ar":{"تقرير تحليلات":4,"معدل تفاعل":4,"مشتركين":3,"متابعين":3,"رعاية":3,"شراكة":3,"بطاقة اسعار":4},
                "fh":["analytics_","sponsor_","media_kit"],"ph":["analytics","sponsorship"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Sales / Business Development": {
        "en": "Sales / Business Development",
        "ar": "مبيعات / تطوير أعمال",
        "cats": ["09_Proposals_Tenders_RFPs","07_Product_Development"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
        "extra": {
            "Sales_Pipeline": {
                "pp":"HIGH","personal":False,
                "en":{"sales pipeline":5,"crm":3,"lead generation":4,"prospecting":4,"sales funnel":5,"qualified lead":4,"opportunity":3,"deal":3,"close rate":4,"win rate":4,"cold call":4,"follow up":3,"sales forecast":4,"quota":3,"territory":3,"account management":4},
                "ar":{"خط مبيعات":5,"توليد عملاء":4,"فرصة بيع":4,"معدل اغلاق":4,"ادارة حسابات":4,"عميل محتمل":4,"متابعة":3,"حصة مبيعات":4},
                "fh":["sales_","pipeline_","lead_","crm_","deal_"],"ph":["sales","pipeline","leads","crm","مبيعات"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Client_Presentations": {
                "pp":"HIGH","personal":False,
                "en":{"client presentation":5,"pitch deck":5,"demo":3,"product demo":4,"case study":4,"testimonial":3,"reference":2,"competitive positioning":4,"value proposition":5,"pricing proposal":4},
                "ar":{"عرض للعميل":5,"عرض تقديمي":3,"دراسة حالة":4,"شهادة عميل":3,"عرض قيمة":5,"عرض تسعير":4},
                "fh":["pitch_","demo_","case_study_","client_"],"ph":["pitches","demos","clients"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "UX / UI Designer": {
        "en": "UX / UI Designer",
        "ar": "مصمم تجربة / واجهة مستخدم",
        "cats": ["07_Product_Development","23_Diagrams_Visuals","14_Training_Knowledge"] + _COMMON_PERSONAL,
        "extra": {
            "UX_Research": {
                "pp":"HIGH","personal":False,
                "en":{"user research":5,"usability test":5,"user interview":4,"persona":4,"user journey":5,"empathy map":5,"affinity diagram":4,"card sorting":4,"heuristic evaluation":5,"accessibility audit":4,"ux audit":5,"competitive analysis":3,"user flow":4,"information architecture":4},
                "ar":{"بحث المستخدم":5,"اختبار قابلية الاستخدام":5,"مقابلة مستخدم":4,"شخصية المستخدم":4,"رحلة المستخدم":5,"خريطة التعاطف":5,"تدقيق تجربة المستخدم":5},
                "fh":["ux_","usability_","persona_","journey_"],"ph":["ux","research","usability","تجربة_مستخدم"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "UI_Design_Assets": {
                "pp":"HIGH","personal":False,
                "en":{"design system":5,"component library":5,"style guide":4,"wireframe":4,"mockup":4,"prototype":3,"ui kit":4,"icon set":3,"figma":3,"sketch":3,"design token":4,"responsive design":4,"mobile design":4},
                "ar":{"نظام تصميم":5,"مكتبة مكونات":5,"دليل التصميم":4,"تصميم اولي":4,"نموذج تفاعلي":4,"تصميم متجاوب":4},
                "fh":["design_system_","wireframe_","mockup_","prototype_","ui_"],"ph":["design","wireframes","mockups","ui_kit"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Data Analyst / Scientist": {
        "en": "Data Analyst / Data Scientist",
        "ar": "محلل بيانات / عالم بيانات",
        "cats": ["17_Infrastructure_Technical","04_Business_Analysis","13_Reports_Presentations","23_Diagrams_Visuals"] + _COMMON_PERSONAL,
        "extra": {
            "Data_Analysis": {
                "pp":"HIGH","personal":False,
                "en":{"data analysis":5,"exploratory data":4,"statistical analysis":5,"regression":4,"correlation":4,"data visualization":5,"dashboard":3,"data cleaning":4,"etl":4,"data pipeline":4,"sql query":4,"python notebook":4,"jupyter":3,"pandas":3,"data model":4,"data dictionary":4,"data catalog":4},
                "ar":{"تحليل بيانات":5,"تحليل احصائي":5,"تصور البيانات":5,"لوحة بيانات":4,"تنظيف بيانات":4,"نموذج بيانات":4,"قاموس بيانات":4},
                "fh":["data_","analysis_","dashboard_","query_","notebook_"],"ph":["data","analysis","notebooks","analytics","بيانات","تحليل"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "ML_AI_Models": {
                "pp":"HIGH","personal":False,
                "en":{"machine learning":5,"deep learning":5,"neural network":4,"model training":4,"model evaluation":4,"feature engineering":4,"hyperparameter":4,"classification":3,"clustering":3,"natural language processing":5,"nlp":3,"computer vision":4,"reinforcement learning":4,"transfer learning":4,"mlops":4},
                "ar":{"تعلم آلي":5,"تعلم عميق":5,"شبكة عصبية":4,"تدريب نموذج":4,"معالجة لغة طبيعية":5,"رؤية حاسوب":4},
                "fh":["model_","ml_","ai_","training_","nlp_"],"ph":["models","ml","ai","machine_learning"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Medical / Healthcare": {
        "en": "Medical Doctor / Healthcare",
        "ar": "طبيب / رعاية صحية",
        "cats": ["13_Reports_Presentations","14_Training_Knowledge","18_Policies_Procedures"] + _COMMON_PERSONAL,
        "extra": {
            "Medical_Records_Research": {
                "pp":"MEDIUM","personal":False,
                "en":{"patient":3,"diagnosis":4,"treatment plan":5,"clinical trial":5,"medical report":5,"lab results":4,"radiology":4,"pathology":4,"prescription":4,"medical history":4,"discharge summary":4,"referral":3,"ehr":3,"icd":3,"cpt":3,"medical protocol":4},
                "ar":{"مريض":3,"تشخيص":4,"خطة علاج":5,"تقرير طبي":5,"نتائج مختبر":4,"اشعة":4,"وصفة طبية":4,"تاريخ مرضي":4,"ملخص خروج":4,"تحويل":3,"بروتوكول طبي":4},
                "fh":["patient_","clinical_","medical_","lab_","diagnosis_"],"ph":["medical","clinical","patients","hospital","طبي","عيادة"],
                "neg_en":["story","novel","kids","coloring"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Healthcare_Admin": {
                "pp":"MEDIUM","personal":False,
                "en":{"hospital policy":4,"accreditation":4,"jci":4,"cbahi":4,"quality improvement":4,"patient safety":4,"infection control":4,"clinical pathway":4,"formulary":3,"credentialing":4},
                "ar":{"سياسة المستشفى":4,"اعتماد":4,"تحسين الجودة":4,"سلامة المرضى":4,"مكافحة العدوى":4,"مسار سريري":4,"اعتماد طبي":4},
                "fh":["hospital_","accreditation_","jci_","quality_"],"ph":["hospital","accreditation","quality","مستشفى"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Real Estate / Property": {
        "en": "Real Estate / Property Manager",
        "ar": "عقارات / إدارة أملاك",
        "cats": ["11_Contracts_Legal","10_Finance_Budgets","09_Proposals_Tenders_RFPs"] + _COMMON_PERSONAL,
        "extra": {
            "Property_Management": {
                "pp":"MEDIUM","personal":False,
                "en":{"lease agreement":5,"tenancy contract":5,"property valuation":5,"rent":3,"landlord":3,"tenant":3,"property inspection":4,"maintenance request":4,"occupancy rate":4,"property listing":4,"real estate":3,"title deed":5,"mortgage":4,"escrow":4},
                "ar":{"عقد ايجار":5,"تقييم عقاري":5,"مالك":3,"مستأجر":3,"فحص عقار":4,"طلب صيانة":4,"صك ملكية":5,"رهن عقاري":4,"عقارات":3},
                "fh":["lease_","property_","tenant_","rent_"],"ph":["property","real_estate","leases","عقارات","ايجار"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
        },
    },
    "Operations Manager": {
        "en": "Operations Manager",
        "ar": "مدير عمليات",
        "cats": ["03_Project_Management_PMO","08_IT_Governance_Compliance","17_Infrastructure_Technical"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
        "extra": {
            "Operations_Processes": {
                "pp":"HIGH","personal":False,
                "en":{"standard operating procedure":5,"sop":3,"process improvement":4,"lean":3,"six sigma":4,"kaizen":4,"supply chain":4,"inventory":3,"logistics":4,"warehouse":3,"procurement":4,"vendor management":4,"kpi dashboard":4,"operational excellence":4},
                "ar":{"اجراءات تشغيل":5,"تحسين العمليات":4,"سلسلة الامداد":4,"مخزون":3,"لوجستيات":4,"مشتريات":4,"ادارة الموردين":4,"التميز التشغيلي":4},
                "fh":["sop_","process_","operations_","supply_","vendor_"],"ph":["operations","processes","supply_chain","procurement","عمليات"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
        },
    },
}


# ═══════════════════════════════════════════════
#  LOAD / SAVE / CRUD
# ═══════════════════════════════════════════════

def get_defaults():
    return deepcopy(_DEFAULTS)

def load_categories():
    """Load categories from user file, or return defaults."""
    if CATS_FILE.exists():
        try:
            data = json.loads(CATS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and len(data) > 0:
                return data
        except Exception:
            pass
    return get_defaults()

def save_categories(cats):
    """Save categories to user file."""
    try:
        CATS_FILE.write_text(json.dumps(cats, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def reset_to_defaults():
    """Reset to default categories."""
    cats = get_defaults()
    save_categories(cats)
    return cats

def get_role_names():
    """Return list of role preset names."""
    return list(ROLE_PRESETS.keys())

def get_role_display(role_key, lang="en"):
    """Get display name for a role."""
    preset = ROLE_PRESETS.get(role_key, {})
    return preset.get(lang, preset.get("en", role_key))

def load_preset(role_key):
    """Load a role preset — returns new categories dict."""
    preset = ROLE_PRESETS.get(role_key)
    if not preset:
        return get_defaults()

    cats = {}
    for cat_key in preset.get("cats", []):
        if cat_key in _DEFAULTS:
            cats[cat_key] = deepcopy(_DEFAULTS[cat_key])

    # Add role-specific extra categories
    for extra_key, extra_val in preset.get("extra", {}).items():
        cats[extra_key] = deepcopy(extra_val)

    save_categories(cats)
    return cats

def add_category(cats, name, cat_data):
    """Add a new category."""
    safe_name = name.replace(" ", "_")
    cats[safe_name] = cat_data
    save_categories(cats)
    return cats

def update_category(cats, name, cat_data):
    """Update an existing category."""
    cats[name] = cat_data
    save_categories(cats)
    return cats

def delete_category(cats, name):
    """Delete a category."""
    cats.pop(name, None)
    save_categories(cats)
    return cats

def make_empty_category():
    """Return a blank category template."""
    return {
        "pp": "MEDIUM",
        "personal": False,
        "en": {},
        "ar": {},
        "fh": [],
        "ph": [],
        "neg_en": [],
        "neg_ar": [],
    }


# ═══════════════════════════════════════════════════════
#  FILE TYPE MANAGER
# ═══════════════════════════════════════════════════════

FILETYPES_FILE = Path.home() / ".smart_categorizer_filetypes.json"

# Default file types grouped by category
# Each: { ext: { "group": str, "label_en": str, "label_ar": str, "needs_ocr": bool } }
_DEFAULT_FILETYPES = {
    # ── Documents ──
    ".docx":  {"group":"documents",  "label_en":"Word Document",         "label_ar":"مستند وورد",          "needs_ocr":False},
    ".doc":   {"group":"documents",  "label_en":"Word 97-2003",          "label_ar":"وورد قديم",            "needs_ocr":False},
    ".rtf":   {"group":"documents",  "label_en":"Rich Text Format",      "label_ar":"نص منسق RTF",         "needs_ocr":False},
    ".odt":   {"group":"documents",  "label_en":"OpenDocument Text",     "label_ar":"مستند OpenDocument",   "needs_ocr":False},
    ".txt":   {"group":"documents",  "label_en":"Plain Text",            "label_ar":"نص عادي",              "needs_ocr":False},
    ".md":    {"group":"documents",  "label_en":"Markdown",              "label_ar":"ماركداون",              "needs_ocr":False},
    ".html":  {"group":"documents",  "label_en":"HTML Page",             "label_ar":"صفحة HTML",            "needs_ocr":False},
    ".htm":   {"group":"documents",  "label_en":"HTML Page",             "label_ar":"صفحة HTML",            "needs_ocr":False},
    ".xml":   {"group":"documents",  "label_en":"XML File",              "label_ar":"ملف XML",              "needs_ocr":False},
    ".json":  {"group":"documents",  "label_en":"JSON File",             "label_ar":"ملف JSON",             "needs_ocr":False},
    ".tex":   {"group":"documents",  "label_en":"LaTeX Document",        "label_ar":"مستند LaTeX",          "needs_ocr":False, "default_off":True},
    ".log":   {"group":"documents",  "label_en":"Log File",              "label_ar":"ملف سجل",              "needs_ocr":False, "default_off":True},
    ".ini":   {"group":"documents",  "label_en":"Config File",           "label_ar":"ملف إعدادات",          "needs_ocr":False, "default_off":True},
    ".yaml":  {"group":"documents",  "label_en":"YAML Config",           "label_ar":"ملف YAML",             "needs_ocr":False, "default_off":True},
    ".yml":   {"group":"documents",  "label_en":"YAML Config",           "label_ar":"ملف YAML",             "needs_ocr":False, "default_off":True},

    # ── PDFs ──
    ".pdf":   {"group":"pdf",        "label_en":"PDF Document",          "label_ar":"مستند PDF",            "needs_ocr":False},

    # ── Spreadsheets ──
    ".xlsx":  {"group":"spreadsheets","label_en":"Excel Workbook",       "label_ar":"ملف إكسل",             "needs_ocr":False},
    ".xls":   {"group":"spreadsheets","label_en":"Excel 97-2003",        "label_ar":"إكسل قديم",            "needs_ocr":False},
    ".xlsm":  {"group":"spreadsheets","label_en":"Excel with Macros",    "label_ar":"إكسل بماكرو",          "needs_ocr":False},
    ".csv":   {"group":"spreadsheets","label_en":"CSV File",             "label_ar":"ملف CSV",              "needs_ocr":False},
    ".tsv":   {"group":"spreadsheets","label_en":"TSV File",             "label_ar":"ملف TSV",              "needs_ocr":False},
    ".ods":   {"group":"spreadsheets","label_en":"OpenDocument Sheet",   "label_ar":"جدول OpenDocument",    "needs_ocr":False},
    ".numbers":{"group":"spreadsheets","label_en":"Apple Numbers",       "label_ar":"Apple Numbers",        "needs_ocr":False, "default_off":True},

    # ── Presentations ──
    ".pptx":  {"group":"presentations","label_en":"PowerPoint",          "label_ar":"عرض باوربوينت",        "needs_ocr":False},
    ".ppt":   {"group":"presentations","label_en":"PowerPoint 97-2003",  "label_ar":"باوربوينت قديم",       "needs_ocr":False},
    ".odp":   {"group":"presentations","label_en":"OpenDocument Present","label_ar":"عرض OpenDocument",     "needs_ocr":False},
    ".key":   {"group":"presentations","label_en":"Apple Keynote",       "label_ar":"Apple Keynote",        "needs_ocr":False, "default_off":True},

    # ── Diagrams ──
    ".vsd":   {"group":"diagrams",   "label_en":"Visio Diagram",         "label_ar":"رسم فيزيو",            "needs_ocr":False},
    ".vsdx":  {"group":"diagrams",   "label_en":"Visio Diagram (XML)",   "label_ar":"فيزيو XML",            "needs_ocr":False},
    ".vsdm":  {"group":"diagrams",   "label_en":"Visio with Macros",     "label_ar":"فيزيو بماكرو",         "needs_ocr":False},
    ".drawio":{"group":"diagrams",   "label_en":"Draw.io Diagram",       "label_ar":"رسم Draw.io",          "needs_ocr":False},
    ".svg":   {"group":"diagrams",   "label_en":"SVG Vector",            "label_ar":"رسم SVG",              "needs_ocr":False, "default_off":True},

    # ── Images (OCR) ──
    ".png":   {"group":"images",     "label_en":"PNG Image",             "label_ar":"صورة PNG",             "needs_ocr":True},
    ".jpg":   {"group":"images",     "label_en":"JPEG Image",            "label_ar":"صورة JPEG",            "needs_ocr":True},
    ".jpeg":  {"group":"images",     "label_en":"JPEG Image",            "label_ar":"صورة JPEG",            "needs_ocr":True},
    ".tiff":  {"group":"images",     "label_en":"TIFF Image",            "label_ar":"صورة TIFF",            "needs_ocr":True},
    ".tif":   {"group":"images",     "label_en":"TIFF Image",            "label_ar":"صورة TIFF",            "needs_ocr":True},
    ".bmp":   {"group":"images",     "label_en":"BMP Image",             "label_ar":"صورة BMP",             "needs_ocr":True},
    ".webp":  {"group":"images",     "label_en":"WebP Image",            "label_ar":"صورة WebP",            "needs_ocr":True},
    ".gif":   {"group":"images",     "label_en":"GIF Image",             "label_ar":"صورة GIF",             "needs_ocr":True,  "default_off":True},
    ".heic":  {"group":"images",     "label_en":"HEIC Image (iPhone)",   "label_ar":"صورة HEIC (آيفون)",    "needs_ocr":True,  "default_off":True},
    ".raw":   {"group":"images",     "label_en":"RAW Photo",             "label_ar":"صورة RAW",             "needs_ocr":True,  "default_off":True},

    # ── Code Files ──
    ".py":    {"group":"code",       "label_en":"Python Script",         "label_ar":"سكربت بايثون",         "needs_ocr":False, "default_off":True},
    ".js":    {"group":"code",       "label_en":"JavaScript",            "label_ar":"جافاسكربت",            "needs_ocr":False, "default_off":True},
    ".ts":    {"group":"code",       "label_en":"TypeScript",            "label_ar":"تايبسكربت",            "needs_ocr":False, "default_off":True},
    ".java":  {"group":"code",       "label_en":"Java Source",           "label_ar":"ملف جافا",             "needs_ocr":False, "default_off":True},
    ".cs":    {"group":"code",       "label_en":"C# Source",             "label_ar":"ملف سي شارب",          "needs_ocr":False, "default_off":True},
    ".cpp":   {"group":"code",       "label_en":"C++ Source",            "label_ar":"ملف C++",              "needs_ocr":False, "default_off":True},
    ".sql":   {"group":"code",       "label_en":"SQL Script",            "label_ar":"سكربت SQL",            "needs_ocr":False, "default_off":True},
    ".sh":    {"group":"code",       "label_en":"Shell Script",          "label_ar":"سكربت شل",             "needs_ocr":False, "default_off":True},
    ".ps1":   {"group":"code",       "label_en":"PowerShell Script",     "label_ar":"سكربت باورشل",         "needs_ocr":False, "default_off":True},
    ".bat":   {"group":"code",       "label_en":"Batch Script",          "label_ar":"سكربت BAT",            "needs_ocr":False, "default_off":True},
    ".r":     {"group":"code",       "label_en":"R Script",              "label_ar":"سكربت R",              "needs_ocr":False, "default_off":True},
    ".ipynb": {"group":"code",       "label_en":"Jupyter Notebook",      "label_ar":"دفتر جوبيتر",          "needs_ocr":False, "default_off":True},

    # ── eBooks ──
    ".epub":  {"group":"ebooks",     "label_en":"EPUB eBook",            "label_ar":"كتاب EPUB",            "needs_ocr":False, "default_off":True},
    ".mobi":  {"group":"ebooks",     "label_en":"Kindle eBook",          "label_ar":"كتاب كيندل",           "needs_ocr":False, "default_off":True},
    ".azw3":  {"group":"ebooks",     "label_en":"Kindle eBook",          "label_ar":"كتاب كيندل",           "needs_ocr":False, "default_off":True},
    ".djvu":  {"group":"ebooks",     "label_en":"DjVu Document",         "label_ar":"مستند DjVu",           "needs_ocr":False, "default_off":True},

    # ── Archives ──
    ".zip":   {"group":"archives",   "label_en":"ZIP Archive",           "label_ar":"أرشيف ZIP",            "needs_ocr":False, "default_off":True},
    ".rar":   {"group":"archives",   "label_en":"RAR Archive",           "label_ar":"أرشيف RAR",            "needs_ocr":False, "default_off":True},
    ".7z":    {"group":"archives",   "label_en":"7-Zip Archive",         "label_ar":"أرشيف 7Z",             "needs_ocr":False, "default_off":True},

    # ── CAD / 3D ──
    ".dwg":   {"group":"cad",        "label_en":"AutoCAD Drawing",       "label_ar":"رسم أوتوكاد",          "needs_ocr":False, "default_off":True},
    ".dxf":   {"group":"cad",        "label_en":"DXF Exchange",          "label_ar":"ملف DXF",              "needs_ocr":False, "default_off":True},
    ".step":  {"group":"cad",        "label_en":"STEP 3D Model",         "label_ar":"نموذج STEP",           "needs_ocr":False, "default_off":True},
    ".stl":   {"group":"cad",        "label_en":"STL 3D Print",          "label_ar":"ملف طباعة ثلاثية",     "needs_ocr":False, "default_off":True},

    # ── Audio / Video ──
    ".mp3":   {"group":"media",      "label_en":"MP3 Audio",             "label_ar":"صوت MP3",              "needs_ocr":False, "default_off":True},
    ".wav":   {"group":"media",      "label_en":"WAV Audio",             "label_ar":"صوت WAV",              "needs_ocr":False, "default_off":True},
    ".mp4":   {"group":"media",      "label_en":"MP4 Video",             "label_ar":"فيديو MP4",            "needs_ocr":False, "default_off":True},
    ".mkv":   {"group":"media",      "label_en":"MKV Video",             "label_ar":"فيديو MKV",            "needs_ocr":False, "default_off":True},
    ".avi":   {"group":"media",      "label_en":"AVI Video",             "label_ar":"فيديو AVI",            "needs_ocr":False, "default_off":True},
    ".mov":   {"group":"media",      "label_en":"QuickTime Video",       "label_ar":"فيديو QuickTime",      "needs_ocr":False, "default_off":True},
    ".m4a":   {"group":"media",      "label_en":"M4A Audio",             "label_ar":"صوت M4A",              "needs_ocr":False, "default_off":True},
}

# Group display info
FILE_GROUPS = {
    "documents":     {"icon":"📄","label_en":"Documents",     "label_ar":"مستندات"},
    "pdf":           {"icon":"📕","label_en":"PDFs",           "label_ar":"ملفات PDF"},
    "spreadsheets":  {"icon":"📊","label_en":"Spreadsheets",   "label_ar":"جداول بيانات"},
    "presentations": {"icon":"📽️","label_en":"Presentations",  "label_ar":"عروض تقديمية"},
    "diagrams":      {"icon":"📐","label_en":"Diagrams",       "label_ar":"مخططات ورسوم"},
    "images":        {"icon":"🖼️","label_en":"Images (OCR)",   "label_ar":"صور (OCR)"},
    "code":          {"icon":"💻","label_en":"Code Files",     "label_ar":"ملفات برمجية"},
    "ebooks":        {"icon":"📚","label_en":"eBooks",         "label_ar":"كتب إلكترونية"},
    "archives":      {"icon":"📦","label_en":"Archives",       "label_ar":"أرشيفات مضغوطة"},
    "cad":           {"icon":"🏗️","label_en":"CAD / 3D",       "label_ar":"تصميم هندسي / ثلاثي"},
    "media":         {"icon":"🎬","label_en":"Audio / Video",  "label_ar":"صوت / فيديو"},
}


def load_filetypes() -> dict:
    """Load file type settings. Returns {ext: {enabled:bool, ...}}."""
    # Start with defaults
    ft = {}
    for ext, info in _DEFAULT_FILETYPES.items():
        ft[ext] = {**info, "enabled": not info.get("default_off", False), "custom": False}

    # Override with saved settings
    try:
        if FILETYPES_FILE.exists():
            saved = json.loads(FILETYPES_FILE.read_text(encoding="utf-8"))
            for ext, sdata in saved.items():
                if ext in ft:
                    ft[ext]["enabled"] = sdata.get("enabled", ft[ext]["enabled"])
                else:
                    # Custom extension added by user
                    ft[ext] = {
                        "group": sdata.get("group", "documents"),
                        "label_en": sdata.get("label_en", ext),
                        "label_ar": sdata.get("label_ar", ext),
                        "needs_ocr": sdata.get("needs_ocr", False),
                        "enabled": sdata.get("enabled", True),
                        "custom": True,
                    }
    except Exception:
        pass
    return ft


def save_filetypes(ft: dict):
    """Save only non-default settings (overrides + custom extensions)."""
    to_save = {}
    for ext, info in ft.items():
        is_default = ext in _DEFAULT_FILETYPES
        if is_default:
            default_enabled = not _DEFAULT_FILETYPES[ext].get("default_off", False)
            if info["enabled"] != default_enabled:
                to_save[ext] = {"enabled": info["enabled"]}
        else:
            # Custom extension — save fully
            to_save[ext] = {
                "group": info.get("group", "documents"),
                "label_en": info.get("label_en", ext),
                "label_ar": info.get("label_ar", ext),
                "needs_ocr": info.get("needs_ocr", False),
                "enabled": info["enabled"],
            }
    try:
        FILETYPES_FILE.write_text(json.dumps(to_save, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_active_extensions(ft: dict) -> tuple:
    """Return (text_extensions: set, image_extensions: set, media_extensions: set)."""
    text_exts = set()
    img_exts = set()
    media_exts = set()
    MEDIA_GROUPS = {"media"}  # groups that are audio/video
    for ext, info in ft.items():
        if not info.get("enabled", False):
            continue
        grp = info.get("group", "")
        if grp in MEDIA_GROUPS:
            media_exts.add(ext)
        elif info.get("needs_ocr", False):
            img_exts.add(ext)
        else:
            text_exts.add(ext)
    return text_exts, img_exts, media_exts


def reset_filetypes():
    """Delete saved file type settings."""
    try:
        if FILETYPES_FILE.exists():
            FILETYPES_FILE.unlink()
    except Exception:
        pass

```

### File: `cleanup_dist.py`
The content of `cleanup_dist.py` is:
```py
"""
cleanup_dist.py — Reduce PyInstaller dist size by removing unnecessary files
Run after PyInstaller build: python cleanup_dist.py

Typically saves 30-50% of the dist folder size.
"""

import os
import shutil
from pathlib import Path

DIST_DIR = Path("dist/SmartDocCategorizer")

# Patterns to delete (case-insensitive)
DELETE_PATTERNS = [
    # Test files
    "**/test_*", "**/tests/**", "**/*_test.py",
    # Documentation
    "**/*.md", "**/*.txt", "**/*.rst",
    # Unnecessary locales (keep English + Arabic)
    "**/locales/**",
    # Debug symbols
    "**/*.pdb",
    # Duplicate DLLs / large unnecessary libs
    "**/msvcp140_1.dll",  # already in system
    "**/ucrtbase.dll",     # already in system
]

# Folders to delete entirely
DELETE_FOLDERS = [
    "tcl/tzdata",          # timezone data (not needed)
    "tcl/msgs",            # tcl messages (not needed)
    "tk/msgs",             # tk messages
    "numpy/tests",
    "numpy/f2py",
    "numpy/distutils",
    "PIL/tests",
    "docx/tests",
    "pptx/tests",
    "openpyxl/tests",
    "pdfminer/tests",
    "share/jupyter",
    "share/man",
    "include",
    "Scripts",
]

# File extensions to delete
DELETE_EXTENSIONS = {
    ".pyc",   # compiled python (already bundled)
    ".pyo",
    ".pyi",   # type stubs
    ".c",     # C source files
    ".h",     # C headers
    ".html",  # documentation
    ".map",   # source maps
}

def cleanup():
    if not DIST_DIR.exists():
        print(f"Dist directory not found: {DIST_DIR}")
        return

    before_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())
    deleted_count = 0
    freed = 0

    # Delete folders
    for folder_pattern in DELETE_FOLDERS:
        for folder in DIST_DIR.glob(f"**/{folder_pattern}"):
            if folder.is_dir():
                size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                shutil.rmtree(folder, ignore_errors=True)
                freed += size
                deleted_count += 1
                print(f"  🗑️ {folder.relative_to(DIST_DIR)} ({size//1024:,} KB)")

    # Delete by extension
    for f in list(DIST_DIR.rglob("*")):
        if f.is_file() and f.suffix.lower() in DELETE_EXTENSIONS:
            size = f.stat().st_size
            f.unlink()
            freed += size
            deleted_count += 1

    after_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())

    print(f"\n{'═'*50}")
    print(f"  Before: {before_size // (1024*1024):,} MB")
    print(f"  After:  {after_size // (1024*1024):,} MB")
    print(f"  Saved:  {freed // (1024*1024):,} MB ({deleted_count} items)")
    print(f"{'═'*50}")


if __name__ == "__main__":
    cleanup()
```

### File: `completecode.MD`
The content of `completecode.MD` is:
```MD
I've a redmine plugin named "code" with this tree structure:

```text
code/
├── BUILD_GUIDE.md
├── README.md
├── USER_MANUAL.md
├── app.py
├── build.bat
├── build_installer.bat
├── categories.py
├── cleanup_dist.py
├── engine.py
├── i18n.py
├── installer.iss
├── requirements.txt
├── setup_ffmpeg.py
└── transcribe.py
```

Here are the contents of the files:

### File: `app.py`
The content of `app.py` is:
```py
"""
Smart File Categorizer — Desktop App v4.0
Bilingual (EN/AR) | Dynamic Categories | Role Presets
"""
import os, sys, json, threading
from pathlib import Path
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, END

try:
    import engine
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import engine

from i18n import t, set_lang, get_lang
import categories as cat_mgr

FONT = "Segoe UI"
ACCENT, ACCENT_H = "#2563EB", "#1D4ED8"
SUCCESS, WARN, DANGER = "#16A34A", "#F59E0B", "#DC2626"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ═══════════ RTL HELPERS ═══════════
# These return correct alignment/direction based on current language.
# Arabic = RTL: sidebar right, text anchored east, packs reversed.

def _rtl() -> bool:
    """Is current language RTL?"""
    return get_lang() == "ar"

def _anchor():
    """Text anchor: 'e' for RTL, 'w' for LTR."""
    return "e" if _rtl() else "w"

def _sticky():
    """Grid sticky for text start: 'e' for RTL, 'w' for LTR."""
    return "e" if _rtl() else "w"

def _sticky_full():
    """Grid sticky for full-width text: 'ew' always."""
    return "ew"

def _side():
    """Pack side for start: 'right' for RTL, 'left' for LTR."""
    return "right" if _rtl() else "left"

def _side_end():
    """Pack side for end: 'left' for RTL, 'right' for LTR."""
    return "left" if _rtl() else "right"

def _padx_start(outer=0, inner=0):
    """Padx tuple for start-aligned items."""
    return (inner, outer) if _rtl() else (outer, inner)

def _justify():
    """Text justify: 'right' for RTL, 'left' for LTR."""
    return "right" if _rtl() else "left"

def _sidebar_col():
    """Column for sidebar: 2 (right) for RTL, 0 (left) for LTR."""
    return 2 if _rtl() else 0

def _main_col():
    """Column for main content: 0 (left) for RTL, 1 (right) for LTR."""
    return 0 if _rtl() else 1


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(t("app_name"))
        self.geometry("1100x750")
        self.minsize(900, 600)

        # State
        self._sources = []  # list of source folder paths
        self._dst = ctk.StringVar()
        self._move = ctk.BooleanVar(value=False)
        self._ocr = ctk.BooleanVar(value=True)
        self._gpu = ctk.BooleanVar(value=False)
        self._reset = ctk.BooleanVar(value=False)
        self._dedup = ctk.BooleanVar(value=False)
        self._dedup_action = ctk.StringVar(value=t("dedup_move"))
        self._transcribe = ctk.BooleanVar(value=False)
        self._whisper_model = ctk.StringVar(value="medium")
        self._workers = ctk.IntVar(value=12)
        self._timeout = ctk.IntVar(value=30)
        self._score = ctk.DoubleVar(value=5.0)
        self._running = False
        self._cancel = threading.Event()
        self._results = []
        self._dedup_results = None
        self._cats = cat_mgr.load_categories()
        self._disabled = set()
        self._filetypes = cat_mgr.load_filetypes()
        self._settings_path = Path.home() / ".smart_categorizer_settings.json"
        self._load_settings()

        self.grid_columnconfigure(_sidebar_col(), weight=0, minsize=220)
        self.grid_columnconfigure(_main_col(), weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ═══════════ SIDEBAR ═══════════
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray92","gray14"))
        sb.grid(row=0, column=_sidebar_col(), sticky="nsew")
        sb.grid_propagate(False)  # keep fixed 220px width
        sb.grid_rowconfigure(8, weight=1)
        ctk.CTkLabel(sb, text="📂", font=(FONT,36)).grid(row=0,column=0,padx=20,pady=(24,4))
        self._title_lbl = ctk.CTkLabel(sb, text=t("app_name"), font=(FONT,14,"bold"), wraplength=180)
        self._title_lbl.grid(row=1,column=0,padx=20,pady=(0,4))
        ctk.CTkLabel(sb, text="v4.0", font=(FONT,11), text_color="gray50").grid(row=2,column=0,padx=20,pady=(0,16))

        self._nav = {}
        icons = [("home","nav_home","🏠"),("settings","nav_settings","⚙️"),
                 ("cats","nav_categories","📋"),("results","nav_results","📊"),("log","nav_log","📝")]
        for i,(k,lk,ic) in enumerate(icons):
            b = ctk.CTkButton(sb, text=f" {ic}  {t(lk)}", anchor=_anchor(), font=(FONT,13), height=38,
                              fg_color="transparent", text_color=("gray10","gray90"),
                              hover_color=("gray80","gray25"), command=lambda k=k:self._go(k))
            b.grid(row=3+i,column=0,padx=12,pady=2,sticky="ew")
            self._nav[k] = (b, lk, ic)

        # Support / Donate button
        ctk.CTkButton(sb, text=f" ❤️  {t('support_btn')}", anchor=_anchor(), font=(FONT,13), height=38,
                      fg_color="transparent", text_color="#F472B6",
                      hover_color=("gray80","gray25"),
                      command=self._show_support).grid(row=8,column=0,padx=12,pady=(8,2),sticky="ew")

        # Language
        ctk.CTkLabel(sb, text=t("lang_lbl"), font=(FONT,11), text_color="gray50").grid(row=9,column=0,padx=20,pady=(8,0))
        self._lang_menu = ctk.CTkOptionMenu(sb, values=["English","العربية"], font=(FONT,11),
                                             height=28, width=140, command=self._switch_lang)
        self._lang_menu.grid(row=10,column=0,padx=20,pady=(4,8))
        self._lang_menu.set("English" if get_lang()=="en" else "العربية")

        # Theme
        ctk.CTkLabel(sb, text=t("theme_lbl"), font=(FONT,11), text_color="gray50").grid(row=11,column=0,padx=20,pady=(0,0))
        ctk.CTkOptionMenu(sb, values=["Dark","Light","System"], font=(FONT,11), height=28, width=140,
                          command=lambda v:ctk.set_appearance_mode(v)).grid(row=12,column=0,padx=20,pady=(4,20))

    def _switch_lang(self, v):
        new_lang = "ar" if "عرب" in v else "en"
        if new_lang == get_lang():
            return
        set_lang(new_lang)
        self._save_settings()
        # Rebuild UI in-place (safe for PyInstaller .exe)
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Destroy all widgets and rebuild — no process restart needed."""
        sources = list(self._sources)
        dst = self._dst.get()
        move = self._move.get()
        ocr = self._ocr.get()
        gpu = self._gpu.get()
        rst = self._reset.get()
        dedup = self._dedup.get()
        dedup_act = self._dedup_action.get()
        trans = self._transcribe.get()
        wmodel = self._whisper_model.get()
        workers = self._workers.get()
        timeout = self._timeout.get()
        score = self._score.get()
        results = self._results
        dedup_res = self._dedup_results

        for w in self.winfo_children():
            w.destroy()

        self.title(t("app_name"))

        # CRITICAL: Reset ALL column weights before reassigning
        # Without this, old column config persists when LTR↔RTL switch
        for col in range(3):
            self.grid_columnconfigure(col, weight=0, minsize=0)

        self._sources = sources
        self._dst = ctk.StringVar(value=dst)
        self._move = ctk.BooleanVar(value=move)
        self._ocr = ctk.BooleanVar(value=ocr)
        self._gpu = ctk.BooleanVar(value=gpu)
        self._reset = ctk.BooleanVar(value=rst)
        self._dedup = ctk.BooleanVar(value=dedup)
        self._dedup_action = ctk.StringVar(value=dedup_act)
        self._transcribe = ctk.BooleanVar(value=trans)
        self._whisper_model = ctk.StringVar(value=wmodel)
        self._workers = ctk.IntVar(value=workers)
        self._timeout = ctk.IntVar(value=timeout)
        self._score = ctk.DoubleVar(value=score)
        self._results = results
        self._dedup_results = dedup_res
        self._running = False
        self._cancel = threading.Event()

        self.grid_columnconfigure(_sidebar_col(), weight=0, minsize=220)
        self.grid_columnconfigure(_main_col(), weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    def _go(self, key):
        for k, f in self._pages.items(): f.grid_forget()
        self._pages[key].grid(row=0,column=0,sticky="nsew",padx=20,pady=16)
        for k,(btn,lk,ic) in self._nav.items():
            btn.configure(fg_color=ACCENT if k==key else "transparent",
                         text_color="white" if k==key else ("gray10","gray90"))

    # ═══════════ MAIN ═══════════
    def _build_main(self):
        self._main = ctk.CTkFrame(self, fg_color="transparent")
        self._main.grid(row=0, column=_main_col(), sticky="nsew")
        self._main.grid_columnconfigure(0,weight=1)
        self._main.grid_rowconfigure(0,weight=1)
        self._pages = {}
        self._pages["home"] = self._pg_home()
        self._pages["settings"] = self._pg_settings()
        self._pages["cats"] = self._pg_cats()
        self._pages["results"] = self._pg_results()
        self._pages["log"] = self._pg_log()
        self._go("home")

    # ═══════════ HOME PAGE ═══════════
    def _pg_home(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pg, text=t("home_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,4))
        ctk.CTkLabel(pg, text=t("home_subtitle"), font=(FONT,13), text_color="gray50", anchor=_anchor()).grid(row=1,column=0,sticky=_sticky(),pady=(0,12))

        # ── Source Folders (multi) ──
        src_frame = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        src_frame.grid(row=2,column=0,sticky="ew",pady=(0,8),ipady=6)
        src_frame.grid_columnconfigure(0,weight=1)

        src_header = ctk.CTkFrame(src_frame, fg_color="transparent")
        src_header.grid(row=0,column=0,sticky="ew",padx=16,pady=(8,4))
        ctk.CTkLabel(src_header, text=t("source_label"), font=(FONT,13,"bold")).pack(side=_side())
        ctk.CTkButton(src_header, text=t("src_add"), width=100, height=28, font=(FONT,11),
                      fg_color=SUCCESS, hover_color="#15803D",
                      command=self._add_source).pack(side=_side_end())

        self._src_list_frame = ctk.CTkFrame(src_frame, fg_color="transparent")
        self._src_list_frame.grid(row=1,column=0,sticky="ew",padx=16,pady=(0,8))
        self._src_list_frame.grid_columnconfigure(0,weight=1)
        self._render_sources()

        # ── Destination ──
        dst_frame = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        dst_frame.grid(row=3,column=0,sticky="ew",pady=(0,8),ipady=6)
        dst_frame.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(dst_frame, text=t("dest_label"), font=(FONT,13,"bold"), anchor=_anchor()).grid(row=0,column=0,padx=(16,8),pady=(8,0),sticky=_sticky())
        ctk.CTkEntry(dst_frame, textvariable=self._dst, font=(FONT,12), height=34, placeholder_text=t("dest_ph")).grid(row=1,column=0,columnspan=2,padx=16,pady=(4,8),sticky="ew")
        ctk.CTkButton(dst_frame, text=t("browse"), width=90, height=34, font=(FONT,12),
                      command=lambda:self._browse("dest")).grid(row=1,column=2,padx=(0,16),pady=(4,8))

        # Switches row 1
        q1 = ctk.CTkFrame(pg, fg_color="transparent"); q1.grid(row=4,column=0,sticky="ew",pady=(4,2))
        ctk.CTkSwitch(q1, text=t("sw_move"), font=(FONT,12), variable=self._move).pack(side=_side(),padx=(0,16))
        ctk.CTkSwitch(q1, text=t("sw_ocr"), font=(FONT,12), variable=self._ocr).pack(side=_side(),padx=(0,16))
        ctk.CTkSwitch(q1, text=t("sw_reset"), font=(FONT,12), variable=self._reset).pack(side=_side())

        # Switches row 2
        q2 = ctk.CTkFrame(pg, fg_color="transparent"); q2.grid(row=5,column=0,sticky="ew",pady=(2,2))
        ctk.CTkSwitch(q2, text=t("sw_dedup"), font=(FONT,12), variable=self._dedup).pack(side=_side(),padx=(0,12))
        ctk.CTkLabel(q2, text=t("dedup_lbl"), font=(FONT,11), text_color="gray50").pack(side=_side(),padx=(0,4))
        ctk.CTkOptionMenu(q2, variable=self._dedup_action,
                          values=[t("dedup_report"),t("dedup_move"),t("dedup_delete")],
                          font=(FONT,11), height=28, width=150).pack(side=_side())

        # Switches row 3 — Transcription
        q3 = ctk.CTkFrame(pg, fg_color="transparent"); q3.grid(row=6,column=0,sticky="ew",pady=(2,10))
        ctk.CTkSwitch(q3, text=t("sw_transcribe"), font=(FONT,12), variable=self._transcribe).pack(side=_side(),padx=(0,12))
        ctk.CTkLabel(q3, text=t("whisper_model_lbl"), font=(FONT,11), text_color="gray50").pack(side=_side(),padx=(0,4))
        ctk.CTkOptionMenu(q3, variable=self._whisper_model,
                          values=["tiny","base","small","medium","large"],
                          font=(FONT,11), height=28, width=100).pack(side=_side())

        # Progress
        pf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        pf.grid(row=7,column=0,sticky="ew",pady=(4,10),ipady=10); pf.grid_columnconfigure(0,weight=1)
        self._prog_lbl = ctk.CTkLabel(pf, text=t("ready"), font=(FONT,12), anchor=_anchor())
        self._prog_lbl.grid(row=0,column=0,padx=16,pady=(8,4),sticky=_sticky())
        self._prog_bar = ctk.CTkProgressBar(pf, height=14, corner_radius=7)
        self._prog_bar.grid(row=1,column=0,padx=16,pady=(0,4),sticky="ew"); self._prog_bar.set(0)
        self._stats_lbl = ctk.CTkLabel(pf, text="", font=(FONT,11), text_color="gray50", anchor=_anchor())
        self._stats_lbl.grid(row=2,column=0,padx=16,pady=(0,8),sticky=_sticky())

        # Buttons
        bf = ctk.CTkFrame(pg, fg_color="transparent"); bf.grid(row=8,column=0,sticky="ew",pady=(4,0))
        self._btn_start = ctk.CTkButton(bf, text=t("btn_start"), font=(FONT,15,"bold"), height=48,
                                         corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_H, command=self._start)
        self._btn_start.pack(side=_side(),expand=True,fill="x",padx=(0,8))
        self._btn_stop = ctk.CTkButton(bf, text=t("btn_stop"), font=(FONT,15,"bold"), height=48, width=140,
                                        corner_radius=10, fg_color=DANGER, hover_color="#B91C1C",
                                        state="disabled", command=self._stop)
        self._btn_stop.pack(side=_side())
        return pg

    def _render_sources(self):
        """Render the list of source folders with remove buttons."""
        for w in self._src_list_frame.winfo_children():
            w.destroy()

        if not self._sources:
            ctk.CTkLabel(self._src_list_frame, text=t("src_empty"),
                         font=(FONT,11), text_color="gray50").grid(row=0,column=0,pady=4,sticky=_sticky())
            return

        for i, src_path in enumerate(self._sources):
            row = ctk.CTkFrame(self._src_list_frame, fg_color=("gray80","gray25"), corner_radius=6)
            row.grid(row=i,column=0,sticky="ew",pady=2,ipady=2)
            row.grid_columnconfigure(0,weight=1)

            # Truncate long paths for display
            display = src_path if len(src_path) < 60 else "..." + src_path[-55:]
            ctk.CTkLabel(row, text=f"📁 {display}", font=(FONT,11),
                         anchor=_anchor()).grid(row=0,column=0,padx=(8,4),pady=4,sticky=_sticky())
            ctk.CTkButton(row, text="✕", width=28, height=24, font=(FONT,11),
                          fg_color=DANGER, hover_color="#B91C1C",
                          command=lambda idx=i: self._remove_source(idx)
                          ).grid(row=0,column=1,padx=(4,6),pady=4)

    def _add_source(self):
        folder = filedialog.askdirectory(title=t("src_add"))
        if folder and folder not in self._sources:
            self._sources.append(folder)
            self._render_sources()
            if not self._dst.get():
                self._dst.set(os.path.join(folder, "categorized_docs"))

    def _remove_source(self, idx):
        if 0 <= idx < len(self._sources):
            self._sources.pop(idx)
            self._render_sources()

    # ═══════════ SETTINGS PAGE ═══════════
    def _pg_settings(self):
        pg = ctk.CTkScrollableFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(pg, text=t("settings_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,16))

        # Role presets
        rf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        rf.grid(row=1,column=0,sticky="ew",pady=(0,12),ipady=10); rf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(rf, text=t("role_title"), font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,4),sticky=_sticky())
        ctk.CTkLabel(rf, text=t("role_hint"), font=(FONT,11), text_color="gray50").grid(row=1,column=0,columnspan=3,padx=16,pady=(0,8),sticky=_sticky())

        self._role_var = ctk.StringVar(value=cat_mgr.get_role_names()[0])
        roles_display = [cat_mgr.get_role_display(r, get_lang()) for r in cat_mgr.get_role_names()]
        ctk.CTkOptionMenu(rf, variable=self._role_var, values=roles_display,
                          font=(FONT,12), height=32, width=280).grid(row=2,column=0,columnspan=2,padx=16,pady=(0,8),sticky=_sticky())
        ctk.CTkButton(rf, text=t("btn_load"), font=(FONT,12), height=32, width=120,
                      fg_color=WARN, command=self._load_preset).grid(row=2,column=2,padx=(0,16),pady=(0,8))

        # Performance
        pf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        pf.grid(row=2,column=0,sticky="ew",pady=(0,12),ipady=10); pf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(pf, text=t("perf"), font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,8),sticky=_sticky())
        ctk.CTkLabel(pf, text=t("workers"), font=(FONT,12)).grid(row=1,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(pf, from_=1,to=32,number_of_steps=31, variable=self._workers).grid(row=1,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(pf, textvariable=self._workers, width=30, font=(FONT,12,"bold")).grid(row=1,column=2,padx=(0,16))
        ctk.CTkLabel(pf, text=t("timeout"), font=(FONT,12)).grid(row=2,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(pf, from_=10,to=120,number_of_steps=22, variable=self._timeout).grid(row=2,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(pf, textvariable=self._timeout, width=30, font=(FONT,12,"bold")).grid(row=2,column=2,padx=(0,16))

        # Classification
        cf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        cf.grid(row=3,column=0,sticky="ew",pady=(0,12),ipady=10); cf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(cf, text=t("cls_title"), font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,8),sticky=_sticky())
        ctk.CTkLabel(cf, text=t("score_lbl"), font=(FONT,12)).grid(row=1,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(cf, from_=2.0,to=15.0,number_of_steps=26, variable=self._score).grid(row=1,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(cf, textvariable=self._score, width=30, font=(FONT,12,"bold")).grid(row=1,column=2,padx=(0,16))
        ctk.CTkLabel(cf, text=t("score_hint"), font=(FONT,11), text_color="gray50").grid(row=2,column=0,columnspan=3,padx=16,pady=(2,8),sticky=_sticky())

        # GPU Acceleration
        gf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        gf.grid(row=4,column=0,sticky="ew",pady=(0,12),ipady=10); gf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(gf, text=t("gpu_title"), font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,4),sticky=_sticky())

        # Detect GPU
        gpu_status = self._detect_gpu()
        status_color = SUCCESS if gpu_status["available"] else "gray50"
        ctk.CTkLabel(gf, text=gpu_status["display"], font=(FONT,11),
                     text_color=status_color).grid(row=1,column=0,columnspan=3,padx=16,pady=(0,8),sticky=_sticky())

        ctk.CTkSwitch(gf, text=t("gpu_enable"), font=(FONT,12),
                      variable=self._gpu).grid(row=2,column=0,columnspan=3,padx=16,pady=(0,4),sticky=_sticky())
        ctk.CTkLabel(gf, text=t("gpu_hint"), font=(FONT,11),
                     text_color="gray50", wraplength=500).grid(row=3,column=0,columnspan=3,padx=16,pady=(0,8),sticky=_sticky())

        # File Types
        ftf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        ftf.grid(row=5,column=0,sticky="ew",pady=(0,12),ipady=10)
        ftf.grid_columnconfigure(0,weight=1)

        # Header row
        ft_header = ctk.CTkFrame(ftf, fg_color="transparent")
        ft_header.grid(row=0,column=0,sticky="ew",padx=16,pady=(10,4))
        ctk.CTkLabel(ft_header, text=t("ft_title"), font=(FONT,14,"bold")).pack(side=_side())
        active_n = sum(1 for v in self._filetypes.values() if v.get("enabled"))
        total_n = len(self._filetypes)
        self._ft_count_lbl = ctk.CTkLabel(ft_header, text=t("ft_active",n=active_n,t=total_n),
                                           font=(FONT,11), text_color="gray50")
        self._ft_count_lbl.pack(side=_side(), padx=12)

        # Toolbar
        ft_tb = ctk.CTkFrame(ftf, fg_color="transparent")
        ft_tb.grid(row=1,column=0,sticky="ew",padx=16,pady=(0,6))
        ctk.CTkButton(ft_tb, text=t("ft_add_ext"), font=(FONT,11), width=120, height=28,
                      fg_color=SUCCESS, hover_color="#15803D",
                      command=self._add_ext_dialog).pack(side=_side(),padx=(0,6))
        ctk.CTkButton(ft_tb, text=t("ft_group_all"), font=(FONT,11), width=100, height=28,
                      fg_color="gray40", hover_color="gray30",
                      command=lambda: self._toggle_all_ft(True)).pack(side=_side(),padx=(0,6))
        ctk.CTkButton(ft_tb, text=t("ft_group_none"), font=(FONT,11), width=100, height=28,
                      fg_color="gray40", hover_color="gray30",
                      command=lambda: self._toggle_all_ft(False)).pack(side=_side(),padx=(0,6))
        ctk.CTkButton(ft_tb, text=t("ft_reset"), font=(FONT,11), width=120, height=28,
                      fg_color="gray40", hover_color="gray30",
                      command=self._reset_ft).pack(side=_side())

        # File type groups
        self._ft_scroll = ctk.CTkScrollableFrame(ftf, fg_color="transparent", height=220)
        self._ft_scroll.grid(row=2,column=0,sticky="ew",padx=8,pady=(0,8))
        self._ft_scroll.grid_columnconfigure(0,weight=1)
        self._render_filetypes()

        ctk.CTkButton(pg, text=t("btn_save"), font=(FONT,14,"bold"), height=44,
                      fg_color=SUCCESS, hover_color="#15803D",
                      command=self._save_and_confirm).grid(row=6,column=0,pady=(8,16),sticky="ew")
        return pg

    def _save_and_confirm(self):
        """Save settings, show success, navigate to home."""
        self._save_settings()
        try:
            from CTkMessagebox import CTkMessagebox
            CTkMessagebox(title=t("save_ok_title"), message=t("save_ok_msg"),
                          icon="check", option_1="OK")
        except ImportError:
            self._log(t("save_ok_msg"))
        self._go("home")

    # ═══════════ CATEGORIES PAGE ═══════════
    def _pg_cats(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(2,weight=1)
        ctk.CTkLabel(pg, text=t("cats_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,4))

        # Toolbar
        tb = ctk.CTkFrame(pg, fg_color="transparent"); tb.grid(row=1,column=0,sticky="ew",pady=(0,8))
        ctk.CTkButton(tb, text=t("btn_add"), font=(FONT,12), height=32, fg_color=SUCCESS,
                      command=self._add_cat).pack(side=_side(),padx=(0,8))
        ctk.CTkButton(tb, text=t("btn_defaults"), font=(FONT,12), height=32, fg_color="gray40",
                      command=self._reset_cats).pack(side=_side())
        ctk.CTkLabel(tb, text=f"{len(self._cats)} {t('cats_count').lower()}", font=(FONT,11),
                     text_color="gray50").pack(side=_side_end())

        self._cats_scroll = ctk.CTkScrollableFrame(pg, fg_color="transparent")
        self._cats_scroll.grid(row=2,column=0,sticky="nsew")
        self._cats_scroll.grid_columnconfigure(0,weight=1)
        self._render_cats()
        return pg

    def _render_cats(self):
        for w in self._cats_scroll.winfo_children(): w.destroy()
        for i,(cn,ci) in enumerate(self._cats.items()):
            pp = ci.get("pp","")
            is_p = ci.get("personal",False)
            rf = ctk.CTkFrame(self._cats_scroll, fg_color=("gray88","gray20"), corner_radius=8)
            rf.grid(row=i,column=0,sticky="ew",pady=2,ipady=4); rf.grid_columnconfigure(1,weight=1)

            var = ctk.BooleanVar(value=cn not in self._disabled)
            ctk.CTkSwitch(rf, text="", variable=var, width=40,
                          command=lambda n=cn,v=var:self._toggle_cat(n,v)).grid(row=0,column=0,padx=(10,4),pady=6)

            dn = cn.split("_",1)[1].replace("_"," ") if "_" in cn else cn
            bc = SUCCESS if pp in("HIGH","VERY_HIGH") else (WARN if pp=="MEDIUM" else "gray50")
            tl = t("personal") if is_p else pp
            ctk.CTkLabel(rf, text=dn, font=(FONT,12,"bold"), anchor=_anchor()).grid(row=0,column=1,padx=(4,8),pady=6,sticky=_sticky())
            ctk.CTkLabel(rf, text=tl, font=(FONT,10), text_color=bc).grid(row=0,column=2,padx=4,pady=6)

            ctk.CTkButton(rf, text=t("edit"), width=50, height=26, font=(FONT,10),
                          fg_color="gray40", command=lambda n=cn:self._edit_cat(n)).grid(row=0,column=3,padx=2,pady=6)
            ctk.CTkButton(rf, text=t("delete"), width=50, height=26, font=(FONT,10),
                          fg_color=DANGER, command=lambda n=cn:self._del_cat(n)).grid(row=0,column=4,padx=(2,10),pady=6)

            kws = list(ci.get("en",{}).keys())[:3] + list(ci.get("ar",{}).keys())[:2]
            if kws:
                ctk.CTkLabel(rf, text=", ".join(kws), font=(FONT,10), text_color="gray50",
                             wraplength=500, anchor=_anchor()).grid(row=1,column=1,columnspan=4,padx=(4,16),pady=(0,6),sticky=_sticky())

    def _toggle_cat(self, n, v):
        if v.get(): self._disabled.discard(n)
        else: self._disabled.add(n)

    def _add_cat(self):
        self._open_cat_editor(None)

    def _edit_cat(self, name):
        self._open_cat_editor(name)

    def _del_cat(self, name):
        try:
            from CTkMessagebox import CTkMessagebox
            msg = CTkMessagebox(title=t("delete"), message=t("confirm_del_cat",n=name),
                               icon="warning", option_1=t("confirm_yes"), option_2=t("cancel"))
            if msg.get() != t("confirm_yes"): return
        except ImportError: pass
        self._cats = cat_mgr.delete_category(self._cats, name)
        engine.reload_categories(self._cats)
        self._render_cats()

    def _reset_cats(self):
        try:
            from CTkMessagebox import CTkMessagebox
            msg = CTkMessagebox(title=t("btn_defaults"), message=t("confirm_reset_cats"),
                               icon="warning", option_1=t("confirm_yes"), option_2=t("cancel"))
            if msg.get() != t("confirm_yes"): return
        except ImportError: pass
        self._cats = cat_mgr.reset_to_defaults()
        engine.reload_categories(self._cats)
        self._disabled.clear()
        self._render_cats()

    def _load_preset(self):
        # Map display name back to key
        sel = self._role_var.get()
        role_key = None
        for rk in cat_mgr.get_role_names():
            if cat_mgr.get_role_display(rk, get_lang()) == sel or rk == sel:
                role_key = rk; break
        if not role_key: return

        try:
            from CTkMessagebox import CTkMessagebox
            msg = CTkMessagebox(title=t("btn_load"), message=t("preset_confirm",r=sel),
                               icon="question", option_1=t("confirm_yes"), option_2=t("cancel"))
            if msg.get() != t("confirm_yes"): return
        except ImportError: pass

        self._cats = cat_mgr.load_preset(role_key)
        engine.reload_categories(self._cats)
        self._disabled.clear()
        self._render_cats()
        self._log(t("preset_loaded", n=len(self._cats), r=sel))

    # ═══════════ CATEGORY EDITOR DIALOG ═══════════
    def _open_cat_editor(self, name):
        is_new = name is None
        cat = self._cats.get(name, cat_mgr.make_empty_category()) if not is_new else cat_mgr.make_empty_category()

        win = ctk.CTkToplevel(self)
        win.title(t("new_title") if is_new else t("edit_title"))
        win.geometry("650x700")
        win.grab_set()
        win.grid_columnconfigure(0,weight=1)

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both",expand=True,padx=16,pady=16)
        scroll.grid_columnconfigure(1,weight=1)
        r = 0

        # Name
        ctk.CTkLabel(scroll, text=t("cat_name"), font=(FONT,12,"bold")).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        name_var = ctk.StringVar(value=name or "")
        ctk.CTkEntry(scroll, textvariable=name_var, font=(FONT,12), height=32).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        # Personal + Potential
        pers_var = ctk.BooleanVar(value=cat.get("personal",False))
        ctk.CTkSwitch(scroll, text=t("cat_personal"), variable=pers_var, font=(FONT,12)).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=4)
        r+=1
        ctk.CTkLabel(scroll, text=t("cat_potential"), font=(FONT,12,"bold")).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        pot_var = ctk.StringVar(value=cat.get("pp","MEDIUM"))
        ctk.CTkOptionMenu(scroll, variable=pot_var, values=["NONE","LOW","MEDIUM","HIGH","VERY_HIGH"],
                          font=(FONT,11), height=28).grid(row=r,column=1,sticky=_sticky(),padx=4,pady=4)
        r+=1

        # English keywords
        ctk.CTkLabel(scroll, text=t("cat_en_kw"), font=(FONT,12,"bold")).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=(8,4))
        r+=1
        en_kw_text = ctk.CTkTextbox(scroll, height=100, font=("Consolas",11))
        en_kw_text.grid(row=r,column=0,columnspan=2,sticky="ew",padx=4,pady=2)
        for k,v in cat.get("en",{}).items(): en_kw_text.insert(END, f"{k}:{v}\n")
        r+=1

        # Arabic keywords
        ctk.CTkLabel(scroll, text=t("cat_ar_kw"), font=(FONT,12,"bold")).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=(8,4))
        r+=1
        ar_kw_text = ctk.CTkTextbox(scroll, height=100, font=("Consolas",11))
        ar_kw_text.grid(row=r,column=0,columnspan=2,sticky="ew",padx=4,pady=2)
        for k,v in cat.get("ar",{}).items(): ar_kw_text.insert(END, f"{k}:{v}\n")
        r+=1

        # Filename hints
        ctk.CTkLabel(scroll, text=t("cat_fh"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        fh_var = ctk.StringVar(value=", ".join(cat.get("fh",[])))
        ctk.CTkEntry(scroll, textvariable=fh_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        # Path hints
        ctk.CTkLabel(scroll, text=t("cat_ph"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        ph_var = ctk.StringVar(value=", ".join(cat.get("ph",[])))
        ctk.CTkEntry(scroll, textvariable=ph_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        # Negative keywords
        ctk.CTkLabel(scroll, text=t("cat_neg"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        neg_en_var = ctk.StringVar(value=", ".join(cat.get("neg_en",[])))
        ctk.CTkEntry(scroll, textvariable=neg_en_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        # Buttons
        bf = ctk.CTkFrame(scroll, fg_color="transparent"); bf.grid(row=r,column=0,columnspan=2,pady=(12,0))
        def _save():
            new_name = name_var.get().strip().replace(" ","_")
            if not new_name: return
            data = {
                "pp": pot_var.get(),
                "personal": pers_var.get(),
                "en": self._parse_kw(en_kw_text.get("1.0",END)),
                "ar": self._parse_kw(ar_kw_text.get("1.0",END)),
                "fh": [x.strip() for x in fh_var.get().split(",") if x.strip()],
                "ph": [x.strip() for x in ph_var.get().split(",") if x.strip()],
                "neg_en": [x.strip() for x in neg_en_var.get().split(",") if x.strip()],
                "neg_ar": [],
            }
            if not is_new and new_name != name:
                self._cats.pop(name, None)
            self._cats = cat_mgr.update_category(self._cats, new_name, data)
            engine.reload_categories(self._cats)
            self._render_cats()
            win.destroy()

        ctk.CTkButton(bf, text=t("save"), font=(FONT,13), height=36, fg_color=SUCCESS, command=_save).pack(side=_side(),padx=(0,8))
        ctk.CTkButton(bf, text=t("cancel"), font=(FONT,13), height=36, fg_color="gray40", command=win.destroy).pack(side=_side())

    @staticmethod
    def _parse_kw(text):
        """Parse 'keyword:weight' per line to dict."""
        result = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if not line: continue
            if ":" in line:
                parts = line.rsplit(":",1)
                try: result[parts[0].strip()] = int(parts[1].strip())
                except: result[parts[0].strip()] = 3
            else:
                result[line] = 3
        return result

    # ═══════════ RESULTS PAGE ═══════════
    def _pg_results(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(1,weight=1)
        ctk.CTkLabel(pg, text=t("results_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,12))
        self._res_scroll = ctk.CTkScrollableFrame(pg, fg_color="transparent")
        self._res_scroll.grid(row=1,column=0,sticky="nsew"); self._res_scroll.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self._res_scroll, text=t("results_empty"), font=(FONT,14), text_color="gray50").grid(row=0,column=0,pady=60)
        return pg

    def _refresh_results(self):
        for w in self._res_scroll.winfo_children(): w.destroy()
        if not self._results:
            ctk.CTkLabel(self._res_scroll, text=t("results_empty"), font=(FONT,14), text_color="gray50").grid(row=0,column=0,pady=60)
            return
        from collections import defaultdict
        stats = defaultdict(lambda:{"c":0,"s":0,"ar":0,"en":0})
        for r in self._results:
            cat=r["category"]; stats[cat]["c"]+=1; stats[cat]["s"]+=r.get("size",0)
            l=r.get("language","")
            if l in("ar","mixed"): stats[cat]["ar"]+=1
            elif l=="en": stats[cat]["en"]+=1
        total=len(self._results)
        errors=sum(1 for r in self._results if r.get("error"))
        products=sum(1 for r in self._results if r.get("product_potential") in("HIGH","VERY_HIGH") and r.get("score",0)>=8)

        # Summary card
        sm = ctk.CTkFrame(self._res_scroll, fg_color=("gray88","gray20"), corner_radius=10)
        sm.grid(row=0,column=0,sticky="ew",pady=(0,12),ipady=10); sm.grid_columnconfigure((0,1,2,3),weight=1)
        for col,(v,l,c) in enumerate([(str(total),t("total"),ACCENT),(str(products),t("sellable"),SUCCESS),
                                       (str(errors),t("errors_lbl"),DANGER if errors else "gray50"),(str(len(stats)),t("cats_count"),WARN)]):
            f=ctk.CTkFrame(sm,fg_color="transparent"); f.grid(row=0,column=col,padx=12,pady=8)
            ctk.CTkLabel(f,text=v,font=(FONT,28,"bold"),text_color=c).pack()
            ctk.CTkLabel(f,text=l,font=(FONT,11),text_color="gray50").pack()

        for i,cat in enumerate(sorted(stats)):
            s=stats[cat]; dn=cat.split("_",1)[1].replace("_"," ") if "_" in cat else cat
            pct=(s["c"]/total*100) if total else 0
            rf=ctk.CTkFrame(self._res_scroll,fg_color=("gray88","gray20"),corner_radius=8)
            rf.grid(row=i+1,column=0,sticky="ew",pady=2,ipady=4); rf.grid_columnconfigure(1,weight=1)
            ctk.CTkLabel(rf,text=dn,font=(FONT,12,"bold"),anchor=_anchor()).grid(row=0,column=0,padx=(12,8),pady=6,sticky=_sticky())
            bar=ctk.CTkProgressBar(rf,height=10,corner_radius=5); bar.grid(row=0,column=1,padx=4,pady=6,sticky="ew"); bar.set(min(pct/100,1.0))
            ctk.CTkLabel(rf,text=f"{s['c']}  ({pct:.0f}%)",font=(FONT,10),text_color="gray50",width=120).grid(row=0,column=2,padx=(4,12),pady=6)

        # Support banner (shown after successful categorization)
        if total > 0:
            row_after = len(stats) + 2
            sup = ctk.CTkFrame(self._res_scroll, fg_color=("gray82","gray22"),
                               corner_radius=12, border_width=1, border_color="#F472B6")
            sup.grid(row=row_after, column=0, sticky="ew", pady=(16,4), ipady=8)
            sup.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(sup, text=t("support_banner_short"), font=(FONT, 12),
                         wraplength=500, justify="center" if get_lang()=="en" else "right",
                         text_color=("gray20","gray80")).grid(row=0, column=0, padx=16, pady=(10,6))
            ctk.CTkButton(sup, text=f"❤️ {t('support_btn')}", font=(FONT, 12, "bold"),
                          height=34, corner_radius=8,
                          fg_color="#F472B6", hover_color="#EC4899",
                          command=self._show_support).grid(row=1, column=0, padx=16, pady=(0,10))

    # ═══════════ LOG PAGE ═══════════
    def _pg_log(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(1,weight=1)
        hd = ctk.CTkFrame(pg, fg_color="transparent"); hd.grid(row=0,column=0,sticky="ew",pady=(0,8))
        ctk.CTkLabel(hd, text=t("log_title"), font=(FONT,22,"bold"), anchor=_anchor()).pack(side=_side())
        ctk.CTkButton(hd, text=t("btn_clear"), width=80, height=30, font=(FONT,11), fg_color="gray40",
                      command=lambda:self._log_box.delete("1.0",END)).pack(side=_side_end())
        self._log_box = ctk.CTkTextbox(pg, font=("Consolas",11), wrap="word", fg_color=("gray92","gray12"))
        self._log_box.grid(row=1,column=0,sticky="nsew")
        return pg

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_box.after(0, lambda: self._log_box.insert(END, f"[{ts}] {msg}\n"))
        self._log_box.after(0, lambda: self._log_box.see(END))

    # ═══════════ BROWSE ═══════════
    def _browse(self, which):
        folder = filedialog.askdirectory()
        if folder:
            self._dst.set(folder)

    # ═══════════ START / STOP ═══════════
    def _start(self):
        if not self._sources:
            self._show_err(t("err_no_src")); return
        valid = [s for s in self._sources if os.path.isdir(s)]
        if not valid:
            self._show_err(t("err_no_src")); return
        dst = self._dst.get().strip()
        if not dst: self._show_err(t("err_no_dst")); return

        if self._move.get():
            try:
                from CTkMessagebox import CTkMessagebox
                msg = CTkMessagebox(title="⚠", message=t("confirm_move"), icon="warning",
                                   option_1=t("confirm_yes"), option_2=t("cancel"))
                if msg.get() != t("confirm_yes"): return
            except ImportError: pass

        try:
            self._running = True; self._cancel.clear()
            self._btn_start.configure(state="disabled"); self._btn_stop.configure(state="normal")
            self._prog_bar.set(0); self._prog_lbl.configure(text=t("preparing")); self._stats_lbl.configure(text="")
            self._results = []; self._dedup_results = None

            # Reload categories
            active = {k:v for k,v in self._cats.items() if k not in self._disabled}
            engine.reload_categories(active)

            # Config
            engine.CFG = engine.Config()
            engine.CFG.ocr_on = self._ocr.get()
            engine.CFG.gpu = self._gpu.get()
            engine.CFG.move_mode = self._move.get()
            engine.CFG.reset = self._reset.get()
            engine.CFG.max_workers = self._workers.get()
            engine.CFG.file_timeout = self._timeout.get()
            engine.CFG.ocr_timeout = self._timeout.get() * 2
            engine.CFG.score_thr = self._score.get()
            engine.CFG.dedup = self._dedup.get()
            da_map = {t("dedup_report"):"report", t("dedup_move"):"move_to_dupes", t("dedup_delete"):"delete"}
            engine.CFG.dedup_action = da_map.get(self._dedup_action.get(), "move_to_dupes")
            engine.CFG.transcribe_on = self._transcribe.get()
            engine.CFG.whisper_model = self._whisper_model.get()

            # File types
            text_exts, img_exts, media_exts = cat_mgr.get_active_extensions(self._filetypes)
            engine.TXT_EXTS = text_exts
            engine.IMG_EXT = img_exts
            engine.MEDIA_EXT = media_exts
            engine.ALL_EXTS = text_exts | img_exts | media_exts
            engine.DIA_EXT = {ext for ext, info in self._filetypes.items()
                              if info.get("group") == "diagrams" and info.get("enabled")}

            engine.set_callbacks(progress_fn=self._on_progress, log_fn=self._log, cancel_event=self._cancel)

            # Start background thread
            self._worker = threading.Thread(target=self._run_engine, args=(list(valid), dst), daemon=True)
            self._worker.start()

        except Exception as e:
            self._running = False
            self._btn_start.configure(state="normal"); self._btn_stop.configure(state="disabled")
            self._prog_lbl.configure(text=t("error", e=str(e)))
            self._log(f"Start error: {e}")

    def _run_engine(self, sources, dst):
        try:
            self._log(f"Start: {len(sources)} sources → {dst}")
            engine.run(sources, dst)
            rp = Path(dst) / "_categorization_report.json"
            if rp.exists():
                self._results = json.loads(rp.read_text(encoding="utf-8")).get("files",[])
            dp = Path(dst) / "_DUPLICATES_REPORT.json"
            if dp.exists(): self._dedup_results = json.loads(dp.read_text(encoding="utf-8"))
            self.after(0, self._on_complete)
        except Exception as e:
            err_msg = str(e)
            self._log(f"Engine error: {err_msg}")
            self.after(0, lambda: self._on_complete(error=err_msg))

    def _on_progress(self, cur, total, fn, cat):
        """Called from engine thread — schedule GUI updates on main thread."""
        # Capture values now (not by reference) to avoid stale data
        _pct = cur / total if total else 0
        _fn = fn[:60] if fn else ""
        _cd = cat.split("_",1)[1].replace("_"," ") if "_" in cat else (cat or "")
        _txt = f"{cur:,}/{total:,} ({_pct*100:.1f}%) → {_cd}"

        try:
            self.after(0, lambda p=_pct: self._prog_bar.set(p))
            self.after(0, lambda f=_fn: self._prog_lbl.configure(text=f"📄 {f}"))
            self.after(0, lambda s=_txt: self._stats_lbl.configure(text=s))
        except Exception:
            pass  # widget might be destroyed during language switch

    def _on_complete(self, error=None):
        self._running = False
        try:
            self._btn_start.configure(state="normal"); self._btn_stop.configure(state="disabled")
            if error: self._prog_lbl.configure(text=t("error", e=error))
            elif self._cancel.is_set(): self._prog_lbl.configure(text=t("stopped"))
            else:
                self._prog_lbl.configure(text=t("done", n=f"{len(self._results):,}"))
                self._prog_bar.set(1.0)
            self._refresh_results(); self._save_settings()
        except Exception:
            pass  # widgets might not exist if app was closed during processing

    def _stop(self):
        self._cancel.set()
        try:
            self._btn_stop.configure(state="disabled")
            self._prog_lbl.configure(text=t("stopping"))
        except Exception:
            pass
        self._log("Stop requested")

    @staticmethod
    def _detect_gpu():
        """Detect NVIDIA GPU availability for CUDA acceleration."""
        result = {"available": False, "display": "", "name": ""}
        # Check PyTorch CUDA
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                vram = torch.cuda.get_device_properties(0).total_mem / (1024**3)
                result["available"] = True
                result["name"] = name
                result["display"] = f"✅ GPU: {name} ({vram:.1f} GB VRAM)"
                return result
        except ImportError:
            pass
        # Check via subprocess (nvidia-smi)
        try:
            import subprocess
            r = subprocess.run(["nvidia-smi","--query-gpu=name,memory.total",
                                "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=5,
                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split(",")
                name = parts[0].strip()
                vram = f"{int(parts[1].strip())/1024:.1f}" if len(parts)>1 else "?"
                result["available"] = True
                result["name"] = name
                result["display"] = f"✅ GPU: {name} ({vram} GB) — install torch for CUDA"
                return result
        except Exception:
            pass
        result["display"] = "⚠ No NVIDIA GPU detected — will use CPU (slower but works fine)"
        return result

    def _show_err(self, msg):
        try:
            from CTkMessagebox import CTkMessagebox
            CTkMessagebox(title="Error", message=msg, icon="cancel")
        except ImportError: self._log(f"❌ {msg}")

    # ═══════════ SUPPORT / DONATE ═══════════
    PAYPAL_USER  = "redaghareeb"
    PATREON_LINK = "https://patreon.com/redaghareeb"
    GITHUB_LINK  = "https://github.com/redaghareeb"

    def _show_support(self):
        """Show professional donation dialog with preset amounts."""
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("support_title"))
        dlg.geometry("540x620")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        # ── Header ──
        header = ctk.CTkFrame(dlg, fg_color=("gray85","gray18"), corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        hdr_inner = ctk.CTkFrame(header, fg_color="transparent")
        hdr_inner.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(hdr_inner, text="❤️", font=(FONT, 32)).pack(side=_side(), padx=(0,10))
        ctk.CTkLabel(hdr_inner, text=t("support_title"), font=(FONT, 20, "bold")).pack(side=_side())

        # ── Message ──
        msg_frame = ctk.CTkFrame(dlg, fg_color=("gray90","gray16"), corner_radius=12)
        msg_frame.pack(padx=24, pady=(16,12), fill="x")
        ctk.CTkLabel(msg_frame, text=t("support_msg"), font=(FONT, 12),
                     wraplength=460,
                     justify="center" if get_lang()=="en" else "right",
                     ).pack(padx=16, pady=14)

        # ── Amount Selection ──
        amt_label = ctk.CTkLabel(dlg, text=t("support_choose_amount"), font=(FONT, 13, "bold"))
        amt_label.pack(padx=24, pady=(4,6), anchor=_anchor())

        self._donate_amount = ctk.StringVar(value="10")

        amt_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        amt_frame.pack(padx=24, fill="x", pady=(0,6))
        amt_frame.grid_columnconfigure((0,1,2,3), weight=1)

        amounts = [("$5", "5"), ("$10", "10"), ("$25", "25"), (t("support_custom"), "custom")]
        self._amt_buttons = []
        for i, (label, val) in enumerate(amounts):
            btn = ctk.CTkButton(
                amt_frame, text=label, font=(FONT, 14, "bold"),
                height=48, corner_radius=10,
                fg_color=("gray75","gray30"), hover_color=("gray65","gray35"),
                text_color=("gray10","gray90"),
                command=lambda v=val: self._select_amount(v)
            )
            btn.grid(row=0, column=i, padx=3, sticky="ew")
            self._amt_buttons.append((btn, val))

        # Custom amount entry (hidden by default)
        self._custom_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        self._custom_var = ctk.StringVar(value="")
        ctk.CTkLabel(self._custom_frame, text="$", font=(FONT, 18, "bold")).pack(side=_side(), padx=(0,4))
        ctk.CTkEntry(self._custom_frame, textvariable=self._custom_var,
                     font=(FONT, 16), height=40, width=120,
                     placeholder_text="15").pack(side=_side())

        # Select $10 by default
        self._select_amount("10")

        # ── Donate Buttons ──
        pay_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        pay_frame.pack(padx=24, pady=(8,4), fill="x")

        # PayPal — direct with amount
        ctk.CTkButton(
            pay_frame, text=t("support_paypal_btn"), font=(FONT, 15, "bold"),
            height=50, corner_radius=10,
            fg_color="#0070BA", hover_color="#005C99",
            image=None,
            command=self._donate_paypal
        ).pack(fill="x", pady=(0,6))

        # Patreon — monthly support
        ctk.CTkButton(
            pay_frame, text=t("support_patreon_btn"), font=(FONT, 13),
            height=42, corner_radius=10,
            fg_color="#FF424D", hover_color="#E03640",
            command=lambda: self._open_link(self.PATREON_LINK)
        ).pack(fill="x", pady=(0,6))

        # Bottom row: GitHub + Close
        bottom = ctk.CTkFrame(dlg, fg_color="transparent")
        bottom.pack(padx=24, pady=(4,16), fill="x")

        ctk.CTkButton(
            bottom, text=t("support_github_btn"), font=(FONT, 11),
            height=34, corner_radius=8,
            fg_color="#333333", hover_color="#222222",
            command=lambda: self._open_link(self.GITHUB_LINK)
        ).pack(side=_side())

        ctk.CTkButton(
            bottom, text=t("support_close"), font=(FONT, 11),
            height=34, width=100, corner_radius=8,
            fg_color="gray40", hover_color="gray30",
            command=dlg.destroy
        ).pack(side=_side_end())

    def _select_amount(self, val):
        """Highlight selected amount button."""
        self._donate_amount.set(val)
        for btn, bval in self._amt_buttons:
            if bval == val:
                btn.configure(fg_color="#F472B6", text_color="white")
            else:
                btn.configure(fg_color=("gray75","gray30"), text_color=("gray10","gray90"))
        # Show/hide custom field
        if val == "custom":
            self._custom_frame.pack(padx=24, pady=(2,0), anchor=_anchor())
        else:
            self._custom_frame.pack_forget()

    def _donate_paypal(self):
        """Open PayPal.me with pre-filled amount."""
        amt = self._donate_amount.get()
        if amt == "custom":
            amt = self._custom_var.get().strip()
            if not amt:
                amt = "10"
            # Clean: remove $ and non-numeric
            amt = ''.join(c for c in amt if c.isdigit() or c == '.')
            if not amt:
                amt = "10"
        # PayPal.me format: paypal.me/username/AMOUNT
        url = f"https://paypal.me/{self.PAYPAL_USER}/{amt}"
        self._open_link(url)

    @staticmethod
    def _open_link(url):
        """Open URL in default browser."""
        import webbrowser
        webbrowser.open(url)

    # ═══════════ FILE TYPE MANAGEMENT ═══════════
    def _render_filetypes(self):
        """Render file type toggles grouped by category."""
        for w in self._ft_scroll.winfo_children():
            w.destroy()

        lang = get_lang()
        # Group extensions
        from collections import defaultdict
        groups = defaultdict(list)
        for ext, info in sorted(self._filetypes.items()):
            groups[info.get("group","other")].append((ext, info))

        row_idx = 0
        for grp_key in ["documents","pdf","spreadsheets","presentations","diagrams",
                         "images","code","ebooks","archives","cad","media","other"]:
            exts = groups.get(grp_key, [])
            if not exts:
                continue

            grp_info = cat_mgr.FILE_GROUPS.get(grp_key, {})
            icon = grp_info.get("icon", "📎")
            label = grp_info.get(f"label_{lang}", grp_info.get("label_en", grp_key.title()))

            # Group header
            grp_frame = ctk.CTkFrame(self._ft_scroll, fg_color=("gray82","gray22"), corner_radius=6)
            grp_frame.grid(row=row_idx, column=0, sticky="ew", pady=(6,2), ipady=3)
            grp_frame.grid_columnconfigure(1, weight=1)

            enabled_in_grp = sum(1 for _, info in exts if info.get("enabled"))
            ctk.CTkLabel(grp_frame, text=f"{icon} {label}",
                         font=(FONT,12,"bold")).grid(row=0,column=0,padx=(10,6),pady=4,sticky=_sticky())
            ctk.CTkLabel(grp_frame, text=f"{enabled_in_grp}/{len(exts)}",
                         font=(FONT,10), text_color="gray50").grid(row=0,column=1,padx=4,pady=4,sticky=_sticky())

            # Group-level toggle all
            ctk.CTkButton(grp_frame, text="☑", width=28, height=24, font=(FONT,11),
                          fg_color="gray35", hover_color="gray25",
                          command=lambda g=grp_key: self._toggle_group_ft(g, True)
                          ).grid(row=0,column=2,padx=2,pady=4)
            ctk.CTkButton(grp_frame, text="☐", width=28, height=24, font=(FONT,11),
                          fg_color="gray35", hover_color="gray25",
                          command=lambda g=grp_key: self._toggle_group_ft(g, False)
                          ).grid(row=0,column=3,padx=(2,8),pady=4)

            row_idx += 1

            # Extensions in this group (flow layout in a single frame)
            ext_frame = ctk.CTkFrame(self._ft_scroll, fg_color="transparent")
            ext_frame.grid(row=row_idx, column=0, sticky="ew", padx=8, pady=(0,4))

            for ext, info in exts:
                lbl = info.get(f"label_{lang}", info.get("label_en", ext))
                short = f"{ext}"
                is_custom = info.get("custom", False)
                var = ctk.BooleanVar(value=info.get("enabled", False))

                item = ctk.CTkFrame(ext_frame, fg_color="transparent")
                item.pack(side=_side(), padx=(0,4), pady=1)

                ctk.CTkCheckBox(item, text=short, variable=var,
                                font=(FONT,11), width=20, height=20,
                                checkbox_width=18, checkbox_height=18,
                                command=lambda e=ext, v=var: self._toggle_ft(e, v.get())
                                ).pack(side=_side())

                if is_custom:
                    ctk.CTkButton(item, text="✕", width=18, height=18, font=(FONT,9),
                                  fg_color=DANGER, hover_color="#B91C1C",
                                  command=lambda e=ext: self._remove_ext(e)
                                  ).pack(side=_side(), padx=(2,0))

            row_idx += 1

        self._update_ft_count()

    def _toggle_ft(self, ext, enabled):
        """Toggle a single extension."""
        if ext in self._filetypes:
            self._filetypes[ext]["enabled"] = enabled
            cat_mgr.save_filetypes(self._filetypes)
            self._update_ft_count()

    def _toggle_group_ft(self, group, enabled):
        """Toggle all extensions in a group."""
        for ext, info in self._filetypes.items():
            if info.get("group") == group:
                info["enabled"] = enabled
        cat_mgr.save_filetypes(self._filetypes)
        self._render_filetypes()

    def _toggle_all_ft(self, enabled):
        """Toggle all file types."""
        for info in self._filetypes.values():
            info["enabled"] = enabled
        cat_mgr.save_filetypes(self._filetypes)
        self._render_filetypes()

    def _reset_ft(self):
        """Reset file types to defaults."""
        cat_mgr.reset_filetypes()
        self._filetypes = cat_mgr.load_filetypes()
        self._render_filetypes()

    def _remove_ext(self, ext):
        """Remove a custom extension."""
        if ext in self._filetypes and self._filetypes[ext].get("custom"):
            del self._filetypes[ext]
            cat_mgr.save_filetypes(self._filetypes)
            self._render_filetypes()

    def _update_ft_count(self):
        """Update the active/total count label."""
        active = sum(1 for v in self._filetypes.values() if v.get("enabled"))
        total = len(self._filetypes)
        try:
            self._ft_count_lbl.configure(text=t("ft_active", n=active, t=total))
        except Exception:
            pass

    def _add_ext_dialog(self):
        """Dialog to add a custom file extension."""
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("ft_add_title"))
        dlg.geometry("420x320")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=t("ft_add_title"), font=(FONT,16,"bold")).pack(padx=20,pady=(16,12))

        # Extension
        ctk.CTkLabel(dlg, text=t("ft_ext_label"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        ext_var = ctk.StringVar()
        ctk.CTkEntry(dlg, textvariable=ext_var, font=(FONT,12), height=34,
                     placeholder_text=".xyz").pack(padx=20,fill="x",pady=(4,8))

        # Description
        ctk.CTkLabel(dlg, text=t("ft_ext_desc"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        desc_var = ctk.StringVar()
        ctk.CTkEntry(dlg, textvariable=desc_var, font=(FONT,12), height=34,
                     placeholder_text="My Custom File").pack(padx=20,fill="x",pady=(4,8))

        # Group
        ctk.CTkLabel(dlg, text=t("ft_ext_group"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        grp_var = ctk.StringVar(value="documents")
        group_names = list(cat_mgr.FILE_GROUPS.keys())
        ctk.CTkOptionMenu(dlg, variable=grp_var, values=group_names,
                          font=(FONT,11), height=30).pack(padx=20,anchor=_anchor(),pady=(4,8))

        # Needs OCR
        ocr_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(dlg, text=t("ft_ext_ocr"), font=(FONT,12), variable=ocr_var).pack(padx=20,anchor=_anchor(),pady=(0,12))

        def save():
            ext = ext_var.get().strip().lower()
            if not ext:
                return
            if not ext.startswith("."):
                ext = "." + ext
            desc = desc_var.get().strip() or ext
            self._filetypes[ext] = {
                "group": grp_var.get(),
                "label_en": desc,
                "label_ar": desc,
                "needs_ocr": ocr_var.get(),
                "enabled": True,
                "custom": True,
            }
            cat_mgr.save_filetypes(self._filetypes)
            dlg.destroy()
            self._render_filetypes()

        ctk.CTkButton(dlg, text=t("btn_save"), font=(FONT,13,"bold"), height=40,
                      fg_color=SUCCESS, hover_color="#15803D", command=save).pack(padx=20,fill="x",pady=(4,16))

    # ═══════════ SETTINGS PERSISTENCE ═══════════
    def _save_settings(self):
        data = {"sources":self._sources,"dest":self._dst.get(),"move":self._move.get(),
                "ocr":self._ocr.get(),"gpu":self._gpu.get(),"workers":self._workers.get(),
                "timeout":self._timeout.get(),"score":self._score.get(),
                "dedup":self._dedup.get(),"dedup_action":self._dedup_action.get(),
                "transcribe":self._transcribe.get(),"whisper_model":self._whisper_model.get(),
                "lang":get_lang(),"disabled":list(self._disabled)}
        try: self._settings_path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        except: pass

    def _load_settings(self):
        try:
            if self._settings_path.exists():
                d = json.loads(self._settings_path.read_text(encoding="utf-8"))
                # Multi-source (backward compat with old "source" key)
                if "sources" in d:
                    self._sources = [s for s in d["sources"] if isinstance(s,str)]
                elif "source" in d and d["source"]:
                    self._sources = [d["source"]]
                self._dst.set(d.get("dest",""))
                self._move.set(d.get("move",False)); self._ocr.set(d.get("ocr",True))
                self._gpu.set(d.get("gpu",False)); self._workers.set(d.get("workers",12))
                self._timeout.set(d.get("timeout",30)); self._score.set(d.get("score",5.0))
                self._dedup.set(d.get("dedup",False))
                self._dedup_action.set(d.get("dedup_action",t("dedup_move")))
                self._transcribe.set(d.get("transcribe",False))
                self._whisper_model.set(d.get("whisper_model","medium"))
                self._disabled = set(d.get("disabled",[]))
                lang = d.get("lang","ar")
                if lang != get_lang(): set_lang(lang)
        except: pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
```

### File: `build.bat`
The content of `build.bat` is:
```bat
@echo off
setlocal enabledelayedexpansion
echo.
echo ════════════════════════════════════════════════
echo   Smart Document Categorizer — Portable Build
echo ════════════════════════════════════════════════
echo.
echo   For a proper setup.exe: run build_installer.bat
echo.

pip install -r requirements.txt >nul 2>&1
pip install pyinstaller >nul 2>&1

REM ffmpeg
if not exist "ffmpeg_bin\ffmpeg.exe" (
    echo Downloading ffmpeg...
    python setup_ffmpeg.py
)

set "FFMPEG_DATA="
if exist "ffmpeg_bin\ffmpeg.exe" set "FFMPEG_DATA=--add-data ffmpeg_bin\ffmpeg.exe;."

echo Building...
python -m PyInstaller --onedir ^
    --windowed ^
    --name "SmartDocCategorizer" ^
    --add-data "engine.py;." ^
    --add-data "i18n.py;." ^
    --add-data "categories.py;." ^
    --add-data "transcribe.py;." ^
    %FFMPEG_DATA% ^
    --hidden-import customtkinter ^
    --hidden-import CTkMessagebox ^
    --hidden-import docx ^
    --hidden-import pdfplumber ^
    --hidden-import openpyxl ^
    --hidden-import pptx ^
    --hidden-import PIL ^
    --hidden-import hashlib ^
    --collect-all customtkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --exclude-module pip ^
    --exclude-module setuptools ^
    --noupx ^
    app.py

if exist "dist\SmartDocCategorizer\SmartDocCategorizer.exe" (
    python cleanup_dist.py 2>nul
    echo.
    echo ═══════════════════════════════════════════
    echo   ✅ Portable build ready!
    echo   📂 dist\SmartDocCategorizer\
    echo ═══════════════════════════════════════════
) else (
    echo   ❌ BUILD FAILED
)
pause
```

### File: `BUILD_GUIDE.md`
The content of `BUILD_GUIDE.md` is:
```md
# BUILD GUIDE — Smart Document Categorizer

Complete instructions for building the Windows installer (.exe).

## Prerequisites

### 1. Python 3.12 (Recommended)

Python 3.14 has compatibility issues with PyInstaller. Use Python 3.12:

- Download: https://www.python.org/downloads/release/python-31211/
- Choose: "Windows installer (64-bit)"
- During install, check:
  - ✅ Add Python to PATH
  - ✅ Install for all users

If you have multiple Python versions, use `py -3.12` to target 3.12 specifically.

### 2. Inno Setup 6 (For installer — free)

- Download: https://jrsoftware.org/isinfo.php
- Install with default settings
- This creates the professional setup.exe installer

### 3. ffmpeg (For audio/video transcription)

Either:
- Run `python setup_ffmpeg.py` (auto-downloads ~90MB)
- Or download manually from https://www.gyan.dev/ffmpeg/builds/

## Build Options

### Option A: Full Installer (Recommended)

Creates a professional setup.exe with Start Menu shortcuts and uninstaller.

```cmd
cd SmartDocCategorizer
build_installer.bat
```

This automatically:
1. Installs Python dependencies
2. Downloads ffmpeg (if not present)
3. Cleans previous builds
4. Builds with PyInstaller (--onedir)
5. Removes unnecessary files (saves ~30-50%)
6. Creates installer with Inno Setup

Output: `installer_output/SmartDocCategorizer_Setup_v4.0.exe` (~80-120 MB)

### Option B: Portable Build

Creates a folder you can copy to any PC — no installation needed.

```cmd
cd SmartDocCategorizer
build.bat
```

Output: `dist/SmartDocCategorizer/SmartDocCategorizer.exe`

### Option C: Manual Build

If the batch files don't work:

```cmd
cd SmartDocCategorizer

REM 1. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

REM 2. Download ffmpeg
python setup_ffmpeg.py

REM 3. Build
python -m PyInstaller --onedir --windowed --name "SmartDocCategorizer" ^
    --add-data "engine.py;." ^
    --add-data "i18n.py;." ^
    --add-data "categories.py;." ^
    --add-data "transcribe.py;." ^
    --add-data "ffmpeg_bin\ffmpeg.exe;." ^
    --hidden-import customtkinter ^
    --hidden-import CTkMessagebox ^
    --hidden-import docx ^
    --hidden-import pdfplumber ^
    --hidden-import openpyxl ^
    --hidden-import pptx ^
    --hidden-import PIL ^
    --hidden-import hashlib ^
    --collect-all customtkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pytest ^
    --noupx ^
    app.py

REM 4. Clean (optional)
python cleanup_dist.py

REM 5. Create installer (optional — requires Inno Setup)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## Custom App Icon

To add your own icon:
1. Create a 256x256 PNG image
2. Convert to .ico format (use https://convertio.co/png-ico/)
3. Save as `icon.ico` in the project folder
4. Rebuild — the installer will use it automatically

## Expected File Sizes

| Build Type | Size | Startup Time |
|---|---|---|
| PyInstaller --onefile (old) | ~432 MB | 15-30 seconds |
| PyInstaller --onedir (portable) | ~200 MB folder | 2-3 seconds |
| Inno Setup installer | ~80-120 MB | 2-3 seconds (after install) |

## Troubleshooting

### "failed to start embedded python interpreter"
- Cause: Python 3.14 incompatibility with PyInstaller
- Fix: Install and use Python 3.12

### "pyinstaller is not recognized"
- Fix: Use `python -m PyInstaller` instead of `pyinstaller`

### "NoneType object has no attribute write"
- Cause: PyInstaller --windowed sets sys.stderr=None
- Fix: Already handled in engine.py (_suppress_stderr)

### Blank screen when changing language
- Fix: Already handled in app.py (_rebuild_ui with column reset)

### Build is too large
- Run `python cleanup_dist.py` after PyInstaller
- Use `--exclude-module` for unused packages
- The cleanup script removes test files, docs, and type stubs

### ffmpeg not working
- Run `python setup_ffmpeg.py` to download
- Or manually place ffmpeg.exe in the `ffmpeg_bin/` folder
- The app auto-detects ffmpeg from bundled path, then system PATH

## GPU Support

For GPU acceleration (OCR + Whisper 5-10x faster):

```cmd
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

The app auto-detects GPU. If GPU fails, it falls back to CPU automatically.
```

### File: `build_installer.bat`
The content of `build_installer.bat` is:
```bat
@echo off
setlocal enabledelayedexpansion
echo.
echo ════════════════════════════════════════════════════════
echo   Smart Document Categorizer — Installer Builder
echo ════════════════════════════════════════════════════════
echo.

REM ── Check Python version ──
python --version 2>nul | findstr "3.14" >nul
if %errorlevel% equ 0 (
    echo ⚠  Python 3.14 detected — may have PyInstaller issues.
    echo    Recommended: use Python 3.12 for building.
    echo    You can install 3.12 alongside: https://python.org/downloads/
    echo    Then build with: py -3.12 -m PyInstaller ...
    echo.
    set /p "CONT=Continue with 3.14 anyway? (y/n): "
    if /i not "!CONT!"=="y" exit /b 1
)

REM ── Step 1: Install dependencies ──
echo [1/5] Installing dependencies...
pip install -r requirements.txt >nul 2>&1
pip install pyinstaller >nul 2>&1
echo       Done.
echo.

REM ── Step 2: Setup ffmpeg ──
echo [2/5] Checking ffmpeg...
if exist "ffmpeg_bin\ffmpeg.exe" (
    echo       ffmpeg already present.
) else (
    echo       Downloading ffmpeg...
    python setup_ffmpeg.py
    if not exist "ffmpeg_bin\ffmpeg.exe" (
        echo       ⚠ ffmpeg download failed — video transcription will be unavailable
        echo         You can download manually later from: https://www.gyan.dev/ffmpeg/builds/
    )
)
echo.

REM ── Step 3: Clean previous builds ──
echo [3/5] Cleaning previous builds...
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist\SmartDocCategorizer" rmdir /s /q "dist\SmartDocCategorizer" >nul 2>&1
echo       Done.
echo.

REM ── Step 4: Build with PyInstaller ──
echo [4/5] Building application (this may take a few minutes)...
echo.

set "FFMPEG_DATA="
if exist "ffmpeg_bin\ffmpeg.exe" (
    set "FFMPEG_DATA=--add-data ffmpeg_bin\ffmpeg.exe;."
)

python -m PyInstaller --onedir ^
    --windowed ^
    --name "SmartDocCategorizer" ^
    --add-data "engine.py;." ^
    --add-data "i18n.py;." ^
    --add-data "categories.py;." ^
    --add-data "transcribe.py;." ^
    %FFMPEG_DATA% ^
    --hidden-import customtkinter ^
    --hidden-import CTkMessagebox ^
    --hidden-import docx ^
    --hidden-import pdfplumber ^
    --hidden-import openpyxl ^
    --hidden-import pptx ^
    --hidden-import PIL ^
    --hidden-import hashlib ^
    --collect-all customtkinter ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module numpy.tests ^
    --exclude-module setuptools ^
    --exclude-module pip ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --exclude-module tkinter.test ^
    --exclude-module distutils ^
    --noupx ^
    app.py

if not exist "dist\SmartDocCategorizer\SmartDocCategorizer.exe" (
    echo.
    echo ═══════════════════════════════════
    echo   BUILD FAILED — check errors above
    echo ═══════════════════════════════════
    pause
    exit /b 1
)

echo.
echo       PyInstaller build complete.

REM Cleanup unnecessary files from dist
echo       Cleaning dist folder...
python cleanup_dist.py 2>nul
echo.

REM ── Step 5: Create installer with Inno Setup ──
echo [5/5] Creating installer...
echo.

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if "!ISCC!"=="" (
    echo   Inno Setup not found — download from: https://jrsoftware.org/isinfo.php
    echo   Your app is ready as portable in: dist\SmartDocCategorizer\
    pause
    exit /b 0
)

if not exist "installer_output" mkdir "installer_output"

if not exist "icon.ico" (
    powershell -Command "(Get-Content installer.iss) -replace 'SetupIconFile=icon.ico', '; SetupIconFile=icon.ico' | Set-Content installer_temp.iss"
    "!ISCC!" installer_temp.iss
    del installer_temp.iss >nul 2>&1
) else (
    "!ISCC!" installer.iss
)

echo.
echo ════════════════════════════════════════════════════════════
if exist "installer_output\SmartDocCategorizer_Setup_v4.0.exe" (
    echo   ✅ INSTALLER CREATED!
    echo.
    echo   📦 installer_output\SmartDocCategorizer_Setup_v4.0.exe
    for %%A in ("installer_output\SmartDocCategorizer_Setup_v4.0.exe") do (
        set "size=%%~zA"
        set /a "sizeMB=!size! / 1048576"
        echo   📏 Size: !sizeMB! MB
    )
) else (
    echo   ⚠ Installer creation failed — portable build in: dist\SmartDocCategorizer\
)
echo ════════════════════════════════════════════════════════════
pause
```

### File: `categories.py`
The content of `categories.py` is:
```py
"""
categories.py — Dynamic category management with job role presets
"""

import json
from pathlib import Path
from copy import deepcopy

CATS_FILE = Path.home() / ".smart_categorizer_categories.json"

# ═══════════════════════════════════════════════
#  DEFAULT CATEGORIES (same as engine.py v3.2)
# ═══════════════════════════════════════════════

_DEFAULTS = {
"01_Enterprise_Architecture": {
    "pp":"HIGH", "personal": False,
    "en":{"enterprise architecture":5,"togaf":5,"archimate":5,"togaf adm":5,"architecture framework":4,"capability map":4,"capability model":4,"business architecture":4,"data architecture":4,"technology architecture":4,"application architecture":4,"architecture vision":4,"target architecture":4,"reference architecture":4,"solution architecture":4,"architecture governance":4,"zachman framework":5},
    "ar":{"بنية مؤسسية":5,"البنية المؤسسية":5,"معمارية الحلول":4,"معمارية تقنية":4,"معمارية البيانات":4,"معمارية التطبيقات":4,"خارطة القدرات":4,"المعمارية المرجعية":4,"حوكمة المعمارية":4},
    "fh":["togaf","archimate","enterprise_arch","capability_map"],"ph":["architecture","togaf","enterprise_architecture"],
    "neg_en":["story","novel","children","kids","fairy","coloring","senses","ears","tales","isbn"],"neg_ar":["قصة","رواية","اطفال","تلوين","حكاية"],
},
"02_Digital_Transformation": {
    "pp":"HIGH","personal":False,
    "en":{"digital transformation":5,"digital strategy":5,"digital maturity":4,"maturity model":3,"maturity assessment":4,"digital roadmap":4,"e-government":4,"smart government":4,"digital governance":4,"dga standards":5,"legacy modernization":4,"cloud migration":3},
    "ar":{"التحول الرقمي":5,"تحول رقمي":5,"الحكومة الرقمية":4,"الخدمات الرقمية":4,"النضج الرقمي":4,"الاستراتيجية الرقمية":5,"الحكومة الالكترونية":4,"هيئة الحكومة الرقمية":5,"الرقمنة":4,"المنصات الرقمية":4},
    "fh":["digital_transform","digitalization","dga_standards"],"ph":["digital_transformation","digitalization"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"03_Project_Management_PMO": {
    "pp":"HIGH","personal":False,
    "en":{"project management":4,"project charter":5,"project plan":4,"pmo":4,"pmbok":5,"prince2":5,"work breakdown structure":5,"wbs":3,"gantt chart":5,"critical path":4,"risk register":5,"risk management plan":5,"change request":4,"lessons learned":4,"project closure":4,"stakeholder register":4,"agile methodology":4,"scrum master":4,"sprint planning":4},
    "ar":{"ادارة مشاريع":5,"ادارة المشاريع":5,"مكتب ادارة المشاريع":5,"ميثاق المشروع":5,"خطة المشروع":4,"سجل المخاطر":5,"ادارة المخاطر":4,"هيكل تجزئة العمل":5,"الدروس المستفادة":4},
    "fh":["project_plan","project_charter","pmo_","gantt","wbs_","risk_register","pmbok"],"ph":["project_management","pmo","projects"],
    "neg_en":["story","novel","children","kids","hero","fairy","senses","coloring","reading","book","isbn"],"neg_ar":["قصة","رواية","اطفال","تلوين","بطل","حكاية","ابطال"],
},
"04_Business_Analysis": {
    "pp":"HIGH","personal":False,
    "en":{"business analysis":4,"business requirements document":5,"functional requirements":4,"non-functional requirements":4,"use case diagram":5,"user story":3,"acceptance criteria":4,"brd":3,"frd":3,"gap analysis":4,"business process":3,"bpmn":4,"process mapping":4,"feasibility study":4,"cost-benefit analysis":4},
    "ar":{"تحليل اعمال":5,"تحليل الاعمال":5,"المتطلبات الوظيفية":4,"تحليل الفجوات":4,"دراسة جدوى":4,"حالات الاستخدام":4,"متطلبات العمل":4},
    "fh":["brd_","frd_","requirements_","gap_analysis","use_case"],"ph":["business_analysis","requirements"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"05_Consulting_Deliverables": {
    "pp":"HIGH","personal":False,
    "en":{"consulting engagement":4,"consulting deliverable":4,"advisory report":4,"assessment report":4,"current state assessment":5,"strategic assessment":4,"implementation roadmap":5,"transformation roadmap":5,"workshop facilitation":4,"benchmarking study":4,"best practices":2,"recommendations":2},
    "ar":{"استشارات":3,"تقييم استراتيجي":4,"تقييم الوضع الحالي":5,"ورشة عمل":3,"خارطة طريق التنفيذ":5,"افضل الممارسات":3,"توصيات":2,"مخرجات استشارية":5},
    "fh":["consulting_","advisory_","deliverable_","assessment_"],"ph":["consulting","advisory","engagements"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"06_Strategy_Planning": {
    "pp":"HIGH","personal":False,
    "en":{"strategic plan":4,"strategic planning":4,"swot analysis":5,"pestle analysis":5,"balanced scorecard":5,"okr framework":4,"competitive analysis":4,"market analysis":3,"value chain":4,"business model canvas":5,"it strategy":4,"technology strategy":4,"strategic initiative":4},
    "ar":{"خطة استراتيجية":5,"التخطيط الاستراتيجي":5,"تحليل سوات":5,"مؤشرات الاداء الرئيسية":5,"بطاقة الاداء المتوازن":5,"تحليل تنافسي":4,"الاهداف الاستراتيجية":4},
    "fh":["strategy_","strategic_","swot","pestle"],"ph":["strategy","strategic_planning"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"07_Product_Development": {
    "pp":"HIGH","personal":False,
    "en":{"product development":4,"product roadmap":5,"product strategy":4,"product requirements document":5,"minimum viable product":5,"mvp":3,"go-to-market":4,"product-market fit":4,"product launch plan":5,"product lifecycle":4,"customer journey map":4,"user persona":4},
    "ar":{"تطوير المنتج":4,"خارطة طريق المنتج":5,"استراتيجية المنتج":4,"اطلاق المنتج":4,"دورة حياة المنتج":4,"رحلة العميل":4},
    "fh":["product_roadmap","prd_","product_strategy","mvp_"],"ph":["product_development","product_management"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"08_IT_Governance_Compliance": {
    "pp":"MEDIUM","personal":False,
    "en":{"it governance":4,"cobit":5,"itil":4,"iso 27001":5,"iso 20000":4,"information security":4,"cybersecurity":3,"data governance":4,"business continuity plan":5,"disaster recovery plan":5,"isms":4},
    "ar":{"حوكمة تقنية المعلومات":5,"حوكمة تقنية":4,"امن المعلومات":4,"الامن السيبراني":4,"استمرارية الاعمال":4,"التعافي من الكوارث":4},
    "fh":["governance_","cobit","itil","iso27","isms"],"ph":["governance","compliance","information_security"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"09_Proposals_Tenders_RFPs": {
    "pp":"HIGH","personal":False,
    "en":{"request for proposal":5,"rfp":3,"rfq":3,"tender document":5,"bid submission":4,"technical proposal":5,"financial proposal":5,"scope of work":4,"evaluation criteria":4},
    "ar":{"كراسة الشروط":5,"كراسة شروط":5,"عرض فني":5,"عرض مالي":5,"مناقصة":4,"عطاء":3,"نطاق العمل":4,"المواصفات الفنية":4,"جدول الكميات":4},
    "fh":["proposal_","rfp_","rfq_","tender_","bid_"],"ph":["proposals","tenders","rfp","bids"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"10_Finance_Budgets": {
    "pp":"MEDIUM","personal":False,
    "en":{"budget plan":4,"financial statement":4,"invoice":3,"cost estimate":4,"revenue forecast":4,"profit and loss":4,"balance sheet":4,"cash flow":3},
    "ar":{"ميزانية":3,"موازنة تقديرية":4,"فاتورة":3,"قائمة الدخل":4,"التدفق النقدي":4,"البيانات المالية":4},
    "fh":["budget_","financial_","invoice_","cost_estimate"],"ph":["finance","budget","accounting"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"11_Contracts_Legal": {
    "pp":"LOW","personal":False,
    "en":{"contract agreement":4,"non-disclosure agreement":5,"terms and conditions":4,"indemnification":4,"governing law":4,"confidentiality agreement":5,"service level agreement":5},
    "ar":{"عقد اتفاقية":4,"اتفاقية عدم افشاء":5,"الشروط والاحكام":4,"اتفاقية سرية":4},
    "fh":["contract_","agreement_","nda_","sla_"],"ph":["legal","contracts"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"12_HR_People": {
    "pp":"LOW","personal":False,
    "en":{"human resources":4,"job description":4,"performance review":4,"onboarding":3,"payroll":3,"salary structure":4,"recruitment":3},
    "ar":{"موارد بشرية":4,"الوصف الوظيفي":4,"تقييم الاداء":4,"الهيكل التنظيمي":4,"سلم الرواتب":4},
    "fh":["hr_","employee_","job_desc","payroll_"],"ph":["human_resources","hr"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"13_Reports_Presentations": {
    "pp":"MEDIUM","personal":False,
    "en":{"executive summary":4,"annual report":4,"quarterly report":4,"status report":3,"progress report":3,"dashboard":3},
    "ar":{"تقرير سنوي":4,"تقرير ربع سنوي":4,"الملخص التنفيذي":4,"عرض تقديمي":3,"لوحة متابعة":3},
    "fh":["report_","presentation_","dashboard_"],"ph":["reports","presentations"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"14_Training_Knowledge": {
    "pp":"HIGH","personal":False,
    "en":{"training material":4,"training course":4,"curriculum":3,"e-learning":4,"lms":3,"knowledge transfer":4,"instructional design":4},
    "ar":{"حقيبة تدريبية":5,"مادة تدريبية":5,"دورة تدريبية":4,"نقل المعرفة":4,"محتوى تعليمي":4},
    "fh":["training_","course_","workshop_material"],"ph":["training","courses","learning"],
    "neg_en":["story","novel","children","kids","fairy","coloring"],"neg_ar":["قصة","رواية","اطفال","تلوين"],
},
"15_Meeting_Communications": {
    "pp":"LOW","personal":False,
    "en":{"meeting minutes":5,"meeting agenda":4,"action items":4,"memorandum":4,"memo":2,"attendees":3},
    "ar":{"محضر اجتماع":5,"جدول الاعمال":4,"مذكرة":3,"توصيات الاجتماع":4},
    "fh":["minutes_","meeting_","memo_","agenda_"],"ph":["meetings","minutes"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"16_LMS_ELearning": {
    "pp":"HIGH","personal":False,
    "en":{"learning management system":5,"scorm":5,"xapi":4,"tin can":4,"moodle":4,"instructional design":4},
    "ar":{"نظام ادارة التعلم":5,"التعلم الالكتروني":4,"تصميم تعليمي":4},
    "fh":["lms_","scorm_","elearning_"],"ph":["lms","elearning"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"17_Infrastructure_Technical": {
    "pp":"MEDIUM","personal":False,
    "en":{"server infrastructure":4,"network architecture":4,"cloud computing":4,"aws":2,"azure":2,"kubernetes":3,"docker":3,"devops":3,"database design":4,"ci/cd pipeline":4},
    "ar":{"البنية التحتية":4,"الحوسبة السحابية":4,"قواعد البيانات":3,"مركز البيانات":4},
    "fh":["infrastructure_","server_","network_","cloud_"],"ph":["infrastructure","technical","devops"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"18_Policies_Procedures": {
    "pp":"MEDIUM","personal":False,
    "en":{"standard operating procedure":5,"sop":3,"policy document":4,"code of conduct":4,"quality management":4,"guideline":2},
    "ar":{"اجراءات التشغيل":4,"سياسة":2,"دليل ارشادي":4,"دليل العمل":4,"لائحة تنظيمية":4},
    "fh":["policy_","procedure_","sop_","guideline_"],"ph":["policies","procedures"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"19_Personal_Books": {
    "pp":"NONE","personal":True,
    "en":{"once upon a time":5,"fairy tale":5,"bedtime story":5,"chapter one":4,"chapter two":4,"novel":3,"fiction":3,"isbn":5,"published by":4,"oxford read":5,"read and discover":5,"graded reader":5,"penguin readers":5,"story":2,"stories":2,"tale":2,"the end":2,"happily ever after":5},
    "ar":{"رواية":4,"قصة قصيرة":4,"كان يا مكان":5,"كان ياما كان":5,"كتاب":2,"ادب":3,"شعر":3,"ديوان":4,"دار النشر":5,"المؤلف":3,"الطبعة":4},
    "fh":["book","novel","story","ebook","reader","tales","كتاب","رواية","قصة"],"ph":["books","novels","ebooks","stories","reading","كتب","روايات","قصص"],
    "neg_en":[],"neg_ar":[],
},
"20_Kids_Activities": {
    "pp":"NONE","personal":True,
    "en":{"for kids":5,"for children":5,"coloring":4,"colouring":4,"worksheet":3,"homework":3,"kindergarten":4,"preschool":4,"activity book":5,"phonics":4,"alphabet":3,"counting":3,"read and discover":4,"talking ears":4,"five senses":3},
    "ar":{"اطفال":4,"للاطفال":5,"قصص اطفال":5,"انشطة":3,"تلوين":4,"مدرسة":3,"حضانة":4,"روضة":4,"الابن":3,"بطل":2,"مغامرات":3,"تعليم اطفال":5},
    "fh":["kids","children","child","activity","coloring","worksheet","school","اطفال","انشطة","تلوين"],"ph":["kids","children","school","activities","nursery","اطفال","مدرسة"],
    "neg_en":[],"neg_ar":[],
},
"21_Personal_Documents": {
    "pp":"NONE","personal":True,
    "en":{"curriculum vitae":5,"resume":3,"passport":4,"birth certificate":5,"marriage certificate":5,"insurance policy":4,"medical record":4,"visa application":4,"driving license":4},
    "ar":{"سيرة ذاتية":5,"جواز سفر":4,"جواز":3,"شهادة ميلاد":5,"شهادة زواج":5,"تأمين":3,"تأشيرة":3,"هوية":3,"اقامة":3,"رخصة قيادة":4},
    "fh":["cv","resume","personal","passport","certificate","سيرة","جواز","شخصي"],"ph":["personal","private","family","شخصي","عائلي","وثائق"],
    "neg_en":[],"neg_ar":[],
},
"22_Templates_Reusable": {
    "pp":"VERY_HIGH","personal":False,
    "en":{"template":3,"boilerplate":4,"toolkit":3,"checklist":3,"reusable":3,"framework template":5},
    "ar":{"قالب":4,"نموذج جاهز":5,"قوالب":4,"حقيبة ادوات":4,"قائمة مراجعة":4},
    "fh":["template_","tmpl_","toolkit_","checklist_"],"ph":["templates","toolkits"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"23_Diagrams_Visuals": {
    "pp":"MEDIUM","personal":False,
    "en":{"diagram":2,"flowchart":3,"uml diagram":4,"sequence diagram":4,"network diagram":4},
    "ar":{"رسم توضيحي":3,"مخطط انسيابي":4},
    "fh":["diagram_","flowchart_","uml_"],"ph":["diagrams","visuals"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
}


# ═══════════════════════════════════════════════
#  JOB ROLE PRESETS
# ═══════════════════════════════════════════════
#  Each preset is a list of category keys from _DEFAULTS
#  + any extra role-specific categories

_COMMON_PERSONAL = ["19_Personal_Books","20_Kids_Activities","21_Personal_Documents"]
_COMMON_BUSINESS = ["06_Strategy_Planning","10_Finance_Budgets","11_Contracts_Legal",
                    "12_HR_People","13_Reports_Presentations","15_Meeting_Communications",
                    "18_Policies_Procedures","22_Templates_Reusable"]

ROLE_PRESETS = {
    "CTO / VP Engineering": {
        "en": "CTO / VP Engineering",
        "ar": "مدير تقنية / نائب رئيس هندسة",
        "cats": list(_DEFAULTS.keys()),  # all categories
    },
    "Project Manager / PMO": {
        "en": "Project Manager / PMO",
        "ar": "مدير مشاريع / مكتب إدارة المشاريع",
        "cats": ["03_Project_Management_PMO","04_Business_Analysis","05_Consulting_Deliverables",
                 "09_Proposals_Tenders_RFPs"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
    },
    "Enterprise Architect": {
        "en": "Enterprise Architect",
        "ar": "مهندس بنية مؤسسية",
        "cats": ["01_Enterprise_Architecture","02_Digital_Transformation","04_Business_Analysis",
                 "08_IT_Governance_Compliance","17_Infrastructure_Technical","23_Diagrams_Visuals"
                 ] + _COMMON_BUSINESS + _COMMON_PERSONAL,
    },
    "Business Analyst": {
        "en": "Business Analyst",
        "ar": "محلل أعمال",
        "cats": ["04_Business_Analysis","03_Project_Management_PMO","05_Consulting_Deliverables",
                 "09_Proposals_Tenders_RFPs","23_Diagrams_Visuals"
                 ] + _COMMON_BUSINESS + _COMMON_PERSONAL,
    },
    "Digital Transformation Lead": {
        "en": "Digital Transformation Lead",
        "ar": "قائد التحول الرقمي",
        "cats": ["02_Digital_Transformation","01_Enterprise_Architecture","06_Strategy_Planning",
                 "08_IT_Governance_Compliance","05_Consulting_Deliverables"
                 ] + _COMMON_BUSINESS + _COMMON_PERSONAL,
    },
    "Software Developer / Engineer": {
        "en": "Software Developer / Engineer",
        "ar": "مطور / مهندس برمجيات",
        "cats": ["17_Infrastructure_Technical","07_Product_Development","23_Diagrams_Visuals",
                 "14_Training_Knowledge","22_Templates_Reusable"
                 ] + _COMMON_PERSONAL,
        "extra": {
            "Dev_Code_Repositories": {
                "pp":"MEDIUM","personal":False,
                "en":{"source code":4,"repository":3,"git":3,"github":3,"pull request":4,"code review":4,"api documentation":4,"readme":3,"changelog":3},
                "ar":{"كود مصدري":4,"مستودع":3},
                "fh":["readme","changelog","api_doc"],"ph":["src","code","repos"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Marketing Manager": {
        "en": "Marketing Manager",
        "ar": "مدير تسويق",
        "cats": ["07_Product_Development","13_Reports_Presentations"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
        "extra": {
            "Marketing_Campaigns": {
                "pp":"HIGH","personal":False,
                "en":{"marketing campaign":5,"brand guidelines":5,"social media":4,"content calendar":4,"seo":3,"google analytics":4,"email marketing":4,"press release":4,"media kit":4,"target audience":4,"brand identity":4,"advertising":3,"conversion rate":4,"marketing funnel":4},
                "ar":{"حملة تسويقية":5,"هوية بصرية":4,"وسائل التواصل":4,"تسويق رقمي":4,"اعلان":3,"جمهور مستهدف":4},
                "fh":["campaign_","marketing_","brand_","social_"],"ph":["marketing","campaigns","brand"],
                "neg_en":[],"neg_ar":[],
            },
            "Design_Creative": {
                "pp":"MEDIUM","personal":False,
                "en":{"design brief":4,"creative brief":4,"mockup":3,"wireframe":3,"brand book":4,"style guide":4,"logo":3,"typography":3,"color palette":3},
                "ar":{"تصميم":2,"هوية بصرية":4,"شعار":3,"دليل الهوية":4},
                "fh":["design_","creative_","brand_","logo_"],"ph":["design","creative","branding"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Accountant / Finance": {
        "en": "Accountant / Finance",
        "ar": "محاسب / مالية",
        "cats": ["10_Finance_Budgets","11_Contracts_Legal"] + _COMMON_PERSONAL,
        "extra": {
            "Accounting_Records": {
                "pp":"LOW","personal":False,
                "en":{"general ledger":5,"journal entry":5,"accounts payable":5,"accounts receivable":5,"trial balance":5,"chart of accounts":5,"depreciation":4,"tax return":5,"vat":3,"audit report":5,"reconciliation":4,"fiscal year":3},
                "ar":{"دفتر الاستاذ":5,"قيد يومية":5,"ذمم دائنة":5,"ذمم مدينة":5,"ميزان المراجعة":5,"شجرة الحسابات":5,"اهلاك":4,"ضريبة":3,"تقرير مراجعة":5},
                "fh":["ledger_","journal_","tax_","audit_","vat_"],"ph":["accounting","ledger","tax","audit"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "HR Manager": {
        "en": "HR Manager",
        "ar": "مدير موارد بشرية",
        "cats": ["12_HR_People","11_Contracts_Legal","14_Training_Knowledge",
                 "18_Policies_Procedures"] + _COMMON_PERSONAL,
        "extra": {
            "HR_Recruitment": {
                "pp":"MEDIUM","personal":False,
                "en":{"job posting":4,"candidate screening":4,"interview scorecard":5,"offer letter":5,"employment contract":5,"background check":4,"talent pipeline":4,"succession plan":4,"competency framework":5,"organizational chart":4},
                "ar":{"اعلان وظيفي":4,"مقابلة":3,"عرض وظيفي":5,"عقد عمل":5,"تقييم مرشح":4,"الهيكل التنظيمي":4,"خطة التعاقب":4,"اطار الكفاءات":5},
                "fh":["recruitment_","candidate_","offer_","interview_"],"ph":["recruitment","hiring","talent"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Teacher / Educator": {
        "en": "Teacher / Educator",
        "ar": "معلم / مدرس",
        "cats": ["14_Training_Knowledge","16_LMS_ELearning"] + _COMMON_PERSONAL,
        "extra": {
            "Lesson_Plans": {
                "pp":"HIGH","personal":False,
                "en":{"lesson plan":5,"unit plan":4,"learning objectives":4,"assessment rubric":5,"curriculum map":5,"differentiation":3,"classroom management":4,"student assessment":4,"grading":3,"syllabus":4,"semester plan":4},
                "ar":{"خطة درس":5,"خطة وحدة":4,"اهداف تعليمية":4,"معايير تقييم":5,"المنهج":3,"تقييم الطلاب":4,"فصل دراسي":3},
                "fh":["lesson_","syllabus_","rubric_","curriculum_"],"ph":["lessons","curriculum","teaching"],
                "neg_en":[],"neg_ar":[],
            },
            "Student_Records": {
                "pp":"NONE","personal":False,
                "en":{"student record":4,"transcript":4,"grade report":4,"attendance":3,"parent communication":4,"iep":4,"report card":4},
                "ar":{"سجل طالب":4,"كشف درجات":4,"حضور وغياب":4,"تقرير اداء":3,"ولي امر":3},
                "fh":["student_","grades_","attendance_","transcript_"],"ph":["students","grades","records"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Lawyer / Legal": {
        "en": "Lawyer / Legal",
        "ar": "محامي / قانوني",
        "cats": ["11_Contracts_Legal","18_Policies_Procedures"] + _COMMON_PERSONAL,
        "extra": {
            "Legal_Cases": {
                "pp":"LOW","personal":False,
                "en":{"case file":5,"legal brief":5,"court filing":5,"litigation":4,"deposition":4,"affidavit":5,"judgment":4,"settlement":4,"plaintiff":4,"defendant":4,"statute":4,"precedent":4,"legal opinion":5},
                "ar":{"ملف قضية":5,"مذكرة قانونية":5,"دعوى":4,"حكم":3,"تسوية":4,"شهادة":3,"رأي قانوني":5,"نظام":3,"لائحة":3},
                "fh":["case_","legal_","court_","litigation_"],"ph":["cases","litigation","court","legal"],
                "neg_en":[],"neg_ar":[],
            },
            "Legal_Research": {
                "pp":"MEDIUM","personal":False,
                "en":{"legal research":4,"case law":4,"regulatory analysis":4,"compliance review":4,"legal memorandum":5,"due diligence":5,"intellectual property":4},
                "ar":{"بحث قانوني":4,"تحليل تنظيمي":4,"العناية الواجبة":5,"ملكية فكرية":4},
                "fh":["research_","memo_","due_diligence"],"ph":["research","compliance"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "General / Personal Use": {
        "en": "General / Personal Use",
        "ar": "استخدام عام / شخصي",
        "cats": _COMMON_PERSONAL + ["13_Reports_Presentations","22_Templates_Reusable"],
        "extra": {
            "Photos_Media": {
                "pp":"NONE","personal":True,
                "en":{"photo":2,"picture":2,"image":2,"video":2,"screenshot":3,"wallpaper":2},
                "ar":{"صورة":2,"صور":2,"فيديو":2,"لقطة شاشة":3},
                "fh":["photo","img_","screenshot","pic_"],"ph":["photos","pictures","media","صور"],
                "neg_en":[],"neg_ar":[],
            },
            "Recipes_Home": {
                "pp":"NONE","personal":True,
                "en":{"recipe":4,"ingredients":3,"cooking":3,"baking":3,"tablespoon":3,"teaspoon":3,"preheat":4,"servings":3},
                "ar":{"وصفة":4,"مقادير":3,"طبخ":3,"خبز":3,"ملعقة":2},
                "fh":["recipe_","cooking_"],"ph":["recipes","cooking","kitchen","وصفات","طبخ"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    # ── NEW ROLES ──
    "PhD / Researcher": {
        "en": "PhD / Researcher / Academic",
        "ar": "باحث / أكاديمي / دكتوراه",
        "cats": ["13_Reports_Presentations","14_Training_Knowledge","06_Strategy_Planning"] + _COMMON_PERSONAL,
        "extra": {
            "Research_Papers": {
                "pp":"HIGH","personal":False,
                "en":{"abstract":4,"literature review":5,"methodology":4,"hypothesis":4,"findings":3,"peer review":5,"journal":3,"publication":4,"citation":4,"references":3,"doi":4,"research paper":5,"thesis":5,"dissertation":5,"conference paper":5,"systematic review":5,"meta-analysis":5,"research proposal":5,"bibliography":4,"appendix":2,"acknowledgments":2},
                "ar":{"ملخص البحث":5,"مراجعة الادبيات":5,"منهجية البحث":5,"فرضية":4,"نتائج البحث":4,"مجلة علمية":4,"رسالة ماجستير":5,"رسالة دكتوراه":5,"اطروحة":5,"بحث علمي":5,"مؤتمر":3,"مرجع":3,"اقتباس":3,"خطة بحثية":5},
                "fh":["paper_","thesis_","research_","dissertation_","journal_"],"ph":["research","papers","thesis","academic","بحث","رسالة","اطروحة"],
                "neg_en":["story","novel","kids","coloring"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Academic_Teaching": {
                "pp":"HIGH","personal":False,
                "en":{"lecture notes":5,"course syllabus":5,"exam paper":5,"quiz":3,"assignment":3,"grading rubric":4,"academic calendar":4,"office hours":3,"tutorial":3,"seminar":4,"lab report":4,"field study":4},
                "ar":{"محاضرة":4,"منهج دراسي":5,"امتحان":4,"اختبار":3,"واجب":3,"معايير التصحيح":4,"تقويم اكاديمي":4,"تقرير مختبر":4,"دراسة ميدانية":4,"حلقة بحث":4},
                "fh":["lecture_","exam_","syllabus_","course_","lab_"],"ph":["lectures","exams","courses","academic","محاضرات","امتحانات"],
                "neg_en":[],"neg_ar":[],
            },
            "Grants_Funding": {
                "pp":"HIGH","personal":False,
                "en":{"grant proposal":5,"funding application":5,"research grant":5,"budget justification":4,"principal investigator":4,"co-investigator":4,"grant report":4,"progress report":3,"impact factor":4,"h-index":3},
                "ar":{"منحة بحثية":5,"طلب تمويل":5,"ميزانية بحث":4,"باحث رئيسي":4,"تقرير منحة":4},
                "fh":["grant_","funding_","proposal_"],"ph":["grants","funding"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "AV Manager / Audiovisual": {
        "en": "AV Manager / Audiovisual",
        "ar": "مدير سمعي بصري / AV",
        "cats": ["17_Infrastructure_Technical","09_Proposals_Tenders_RFPs","23_Diagrams_Visuals"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
        "extra": {
            "AV_Systems_Design": {
                "pp":"HIGH","personal":False,
                "en":{"audiovisual":5,"av system":5,"av design":5,"display system":4,"projector":4,"sound system":5,"audio system":5,"video conferencing":5,"digital signage":5,"control system":5,"crestron":5,"extron":5,"biamp":4,"qsc":4,"shure":4,"dante":4,"hdmi":3,"av matrix":4,"av rack":4,"signal flow":4,"av integration":5},
                "ar":{"نظام سمعي بصري":5,"تصميم صوتي":4,"نظام عرض":4,"مؤتمرات فيديو":5,"لافتات رقمية":4,"نظام تحكم":4,"تكامل سمعي بصري":5,"نظام صوت":4},
                "fh":["av_","audiovisual_","sound_","display_","projector_"],"ph":["av","audiovisual","av_systems","سمعي_بصري"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "AV_Specs_BOQ": {
                "pp":"HIGH","personal":False,
                "en":{"bill of quantities":5,"boq":4,"av specification":5,"technical specification":4,"equipment list":4,"rack elevation":4,"cable schedule":4,"commissioning":4,"as-built":4,"riser diagram":4,"av tender":4},
                "ar":{"جدول كميات":5,"مواصفات فنية":5,"قائمة معدات":4,"جدول كابلات":4,"تشغيل وتسليم":4,"مخطط رايزر":4},
                "fh":["boq_","spec_","equipment_","cable_","commissioning_"],"ph":["specifications","boq","equipment"],
                "neg_en":[],"neg_ar":[],
            },
            "Events_Venues": {
                "pp":"MEDIUM","personal":False,
                "en":{"event setup":4,"venue":3,"stage design":4,"lighting design":4,"live streaming":4,"broadcast":3,"led wall":4,"rigging":4,"stage plot":4,"event production":4,"technical rider":5},
                "ar":{"تجهيز فعالية":4,"تصميم مسرح":4,"اضاءة":3,"بث مباشر":4,"انتاج فعاليات":4,"متطلبات فنية":4},
                "fh":["event_","venue_","stage_","lighting_"],"ph":["events","venues","production","فعاليات"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Content Creator / Influencer": {
        "en": "Content Creator / Influencer",
        "ar": "صانع محتوى / مؤثر",
        "cats": ["07_Product_Development","13_Reports_Presentations","23_Diagrams_Visuals"] + _COMMON_PERSONAL,
        "extra": {
            "Content_Planning": {
                "pp":"HIGH","personal":False,
                "en":{"content calendar":5,"editorial calendar":5,"content strategy":5,"content plan":4,"content pillar":4,"posting schedule":4,"social media plan":4,"content brief":4,"content audit":4,"evergreen content":4,"content repurposing":4},
                "ar":{"تقويم محتوى":5,"خطة محتوى":5,"استراتيجية محتوى":5,"جدول نشر":4,"اعمدة المحتوى":4,"محتوى دائم":4},
                "fh":["content_","editorial_","calendar_","posting_"],"ph":["content","editorial","planning","محتوى"],
                "neg_en":["story","novel","isbn"],"neg_ar":["رواية","قصة"],
            },
            "Scripts_Storyboards": {
                "pp":"HIGH","personal":False,
                "en":{"script":3,"storyboard":5,"shot list":4,"video script":5,"podcast script":4,"voiceover":4,"thumbnail":3,"intro":2,"outro":2,"call to action":3,"hook":3,"b-roll":4,"talking head":3},
                "ar":{"سكربت":4,"نص فيديو":5,"لوحة قصة":5,"قائمة لقطات":4,"تعليق صوتي":4,"صورة مصغرة":3,"مقدمة":2},
                "fh":["script_","storyboard_","video_","podcast_"],"ph":["scripts","storyboards","videos","podcasts"],
                "neg_en":[],"neg_ar":[],
            },
            "Analytics_Growth": {
                "pp":"MEDIUM","personal":False,
                "en":{"analytics report":4,"engagement rate":4,"subscriber":3,"follower":3,"impressions":3,"reach":3,"click-through rate":4,"ctr":3,"monetization":4,"sponsorship":4,"brand deal":4,"media kit":5,"rate card":4},
                "ar":{"تقرير تحليلات":4,"معدل تفاعل":4,"مشتركين":3,"متابعين":3,"رعاية":3,"شراكة":3,"بطاقة اسعار":4},
                "fh":["analytics_","sponsor_","media_kit"],"ph":["analytics","sponsorship"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Sales / Business Development": {
        "en": "Sales / Business Development",
        "ar": "مبيعات / تطوير أعمال",
        "cats": ["09_Proposals_Tenders_RFPs","07_Product_Development"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
        "extra": {
            "Sales_Pipeline": {
                "pp":"HIGH","personal":False,
                "en":{"sales pipeline":5,"crm":3,"lead generation":4,"prospecting":4,"sales funnel":5,"qualified lead":4,"opportunity":3,"deal":3,"close rate":4,"win rate":4,"cold call":4,"follow up":3,"sales forecast":4,"quota":3,"territory":3,"account management":4},
                "ar":{"خط مبيعات":5,"توليد عملاء":4,"فرصة بيع":4,"معدل اغلاق":4,"ادارة حسابات":4,"عميل محتمل":4,"متابعة":3,"حصة مبيعات":4},
                "fh":["sales_","pipeline_","lead_","crm_","deal_"],"ph":["sales","pipeline","leads","crm","مبيعات"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Client_Presentations": {
                "pp":"HIGH","personal":False,
                "en":{"client presentation":5,"pitch deck":5,"demo":3,"product demo":4,"case study":4,"testimonial":3,"reference":2,"competitive positioning":4,"value proposition":5,"pricing proposal":4},
                "ar":{"عرض للعميل":5,"عرض تقديمي":3,"دراسة حالة":4,"شهادة عميل":3,"عرض قيمة":5,"عرض تسعير":4},
                "fh":["pitch_","demo_","case_study_","client_"],"ph":["pitches","demos","clients"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "UX / UI Designer": {
        "en": "UX / UI Designer",
        "ar": "مصمم تجربة / واجهة مستخدم",
        "cats": ["07_Product_Development","23_Diagrams_Visuals","14_Training_Knowledge"] + _COMMON_PERSONAL,
        "extra": {
            "UX_Research": {
                "pp":"HIGH","personal":False,
                "en":{"user research":5,"usability test":5,"user interview":4,"persona":4,"user journey":5,"empathy map":5,"affinity diagram":4,"card sorting":4,"heuristic evaluation":5,"accessibility audit":4,"ux audit":5,"competitive analysis":3,"user flow":4,"information architecture":4},
                "ar":{"بحث المستخدم":5,"اختبار قابلية الاستخدام":5,"مقابلة مستخدم":4,"شخصية المستخدم":4,"رحلة المستخدم":5,"خريطة التعاطف":5,"تدقيق تجربة المستخدم":5},
                "fh":["ux_","usability_","persona_","journey_"],"ph":["ux","research","usability","تجربة_مستخدم"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "UI_Design_Assets": {
                "pp":"HIGH","personal":False,
                "en":{"design system":5,"component library":5,"style guide":4,"wireframe":4,"mockup":4,"prototype":3,"ui kit":4,"icon set":3,"figma":3,"sketch":3,"design token":4,"responsive design":4,"mobile design":4},
                "ar":{"نظام تصميم":5,"مكتبة مكونات":5,"دليل التصميم":4,"تصميم اولي":4,"نموذج تفاعلي":4,"تصميم متجاوب":4},
                "fh":["design_system_","wireframe_","mockup_","prototype_","ui_"],"ph":["design","wireframes","mockups","ui_kit"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Data Analyst / Scientist": {
        "en": "Data Analyst / Data Scientist",
        "ar": "محلل بيانات / عالم بيانات",
        "cats": ["17_Infrastructure_Technical","04_Business_Analysis","13_Reports_Presentations","23_Diagrams_Visuals"] + _COMMON_PERSONAL,
        "extra": {
            "Data_Analysis": {
                "pp":"HIGH","personal":False,
                "en":{"data analysis":5,"exploratory data":4,"statistical analysis":5,"regression":4,"correlation":4,"data visualization":5,"dashboard":3,"data cleaning":4,"etl":4,"data pipeline":4,"sql query":4,"python notebook":4,"jupyter":3,"pandas":3,"data model":4,"data dictionary":4,"data catalog":4},
                "ar":{"تحليل بيانات":5,"تحليل احصائي":5,"تصور البيانات":5,"لوحة بيانات":4,"تنظيف بيانات":4,"نموذج بيانات":4,"قاموس بيانات":4},
                "fh":["data_","analysis_","dashboard_","query_","notebook_"],"ph":["data","analysis","notebooks","analytics","بيانات","تحليل"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "ML_AI_Models": {
                "pp":"HIGH","personal":False,
                "en":{"machine learning":5,"deep learning":5,"neural network":4,"model training":4,"model evaluation":4,"feature engineering":4,"hyperparameter":4,"classification":3,"clustering":3,"natural language processing":5,"nlp":3,"computer vision":4,"reinforcement learning":4,"transfer learning":4,"mlops":4},
                "ar":{"تعلم آلي":5,"تعلم عميق":5,"شبكة عصبية":4,"تدريب نموذج":4,"معالجة لغة طبيعية":5,"رؤية حاسوب":4},
                "fh":["model_","ml_","ai_","training_","nlp_"],"ph":["models","ml","ai","machine_learning"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Medical / Healthcare": {
        "en": "Medical Doctor / Healthcare",
        "ar": "طبيب / رعاية صحية",
        "cats": ["13_Reports_Presentations","14_Training_Knowledge","18_Policies_Procedures"] + _COMMON_PERSONAL,
        "extra": {
            "Medical_Records_Research": {
                "pp":"MEDIUM","personal":False,
                "en":{"patient":3,"diagnosis":4,"treatment plan":5,"clinical trial":5,"medical report":5,"lab results":4,"radiology":4,"pathology":4,"prescription":4,"medical history":4,"discharge summary":4,"referral":3,"ehr":3,"icd":3,"cpt":3,"medical protocol":4},
                "ar":{"مريض":3,"تشخيص":4,"خطة علاج":5,"تقرير طبي":5,"نتائج مختبر":4,"اشعة":4,"وصفة طبية":4,"تاريخ مرضي":4,"ملخص خروج":4,"تحويل":3,"بروتوكول طبي":4},
                "fh":["patient_","clinical_","medical_","lab_","diagnosis_"],"ph":["medical","clinical","patients","hospital","طبي","عيادة"],
                "neg_en":["story","novel","kids","coloring"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Healthcare_Admin": {
                "pp":"MEDIUM","personal":False,
                "en":{"hospital policy":4,"accreditation":4,"jci":4,"cbahi":4,"quality improvement":4,"patient safety":4,"infection control":4,"clinical pathway":4,"formulary":3,"credentialing":4},
                "ar":{"سياسة المستشفى":4,"اعتماد":4,"تحسين الجودة":4,"سلامة المرضى":4,"مكافحة العدوى":4,"مسار سريري":4,"اعتماد طبي":4},
                "fh":["hospital_","accreditation_","jci_","quality_"],"ph":["hospital","accreditation","quality","مستشفى"],
                "neg_en":[],"neg_ar":[],
            },
        },
    },
    "Real Estate / Property": {
        "en": "Real Estate / Property Manager",
        "ar": "عقارات / إدارة أملاك",
        "cats": ["11_Contracts_Legal","10_Finance_Budgets","09_Proposals_Tenders_RFPs"] + _COMMON_PERSONAL,
        "extra": {
            "Property_Management": {
                "pp":"MEDIUM","personal":False,
                "en":{"lease agreement":5,"tenancy contract":5,"property valuation":5,"rent":3,"landlord":3,"tenant":3,"property inspection":4,"maintenance request":4,"occupancy rate":4,"property listing":4,"real estate":3,"title deed":5,"mortgage":4,"escrow":4},
                "ar":{"عقد ايجار":5,"تقييم عقاري":5,"مالك":3,"مستأجر":3,"فحص عقار":4,"طلب صيانة":4,"صك ملكية":5,"رهن عقاري":4,"عقارات":3},
                "fh":["lease_","property_","tenant_","rent_"],"ph":["property","real_estate","leases","عقارات","ايجار"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
        },
    },
    "Operations Manager": {
        "en": "Operations Manager",
        "ar": "مدير عمليات",
        "cats": ["03_Project_Management_PMO","08_IT_Governance_Compliance","17_Infrastructure_Technical"] + _COMMON_BUSINESS + _COMMON_PERSONAL,
        "extra": {
            "Operations_Processes": {
                "pp":"HIGH","personal":False,
                "en":{"standard operating procedure":5,"sop":3,"process improvement":4,"lean":3,"six sigma":4,"kaizen":4,"supply chain":4,"inventory":3,"logistics":4,"warehouse":3,"procurement":4,"vendor management":4,"kpi dashboard":4,"operational excellence":4},
                "ar":{"اجراءات تشغيل":5,"تحسين العمليات":4,"سلسلة الامداد":4,"مخزون":3,"لوجستيات":4,"مشتريات":4,"ادارة الموردين":4,"التميز التشغيلي":4},
                "fh":["sop_","process_","operations_","supply_","vendor_"],"ph":["operations","processes","supply_chain","procurement","عمليات"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
        },
    },
}


# ═══════════════════════════════════════════════
#  LOAD / SAVE / CRUD
# ═══════════════════════════════════════════════

def get_defaults():
    return deepcopy(_DEFAULTS)

def load_categories():
    """Load categories from user file, or return defaults."""
    if CATS_FILE.exists():
        try:
            data = json.loads(CATS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and len(data) > 0:
                return data
        except Exception:
            pass
    return get_defaults()

def save_categories(cats):
    """Save categories to user file."""
    try:
        CATS_FILE.write_text(json.dumps(cats, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def reset_to_defaults():
    """Reset to default categories."""
    cats = get_defaults()
    save_categories(cats)
    return cats

def get_role_names():
    """Return list of role preset names."""
    return list(ROLE_PRESETS.keys())

def get_role_display(role_key, lang="en"):
    """Get display name for a role."""
    preset = ROLE_PRESETS.get(role_key, {})
    return preset.get(lang, preset.get("en", role_key))

def load_preset(role_key):
    """Load a role preset — returns new categories dict."""
    preset = ROLE_PRESETS.get(role_key)
    if not preset:
        return get_defaults()

    cats = {}
    for cat_key in preset.get("cats", []):
        if cat_key in _DEFAULTS:
            cats[cat_key] = deepcopy(_DEFAULTS[cat_key])

    # Add role-specific extra categories
    for extra_key, extra_val in preset.get("extra", {}).items():
        cats[extra_key] = deepcopy(extra_val)

    save_categories(cats)
    return cats

def add_category(cats, name, cat_data):
    """Add a new category."""
    safe_name = name.replace(" ", "_")
    cats[safe_name] = cat_data
    save_categories(cats)
    return cats

def update_category(cats, name, cat_data):
    """Update an existing category."""
    cats[name] = cat_data
    save_categories(cats)
    return cats

def delete_category(cats, name):
    """Delete a category."""
    cats.pop(name, None)
    save_categories(cats)
    return cats

def make_empty_category():
    """Return a blank category template."""
    return {
        "pp": "MEDIUM",
        "personal": False,
        "en": {},
        "ar": {},
        "fh": [],
        "ph": [],
        "neg_en": [],
        "neg_ar": [],
    }


# ═══════════════════════════════════════════════════════
#  FILE TYPE MANAGER
# ═══════════════════════════════════════════════════════

FILETYPES_FILE = Path.home() / ".smart_categorizer_filetypes.json"

# Default file types grouped by category
# Each: { ext: { "group": str, "label_en": str, "label_ar": str, "needs_ocr": bool } }
_DEFAULT_FILETYPES = {
    # ── Documents ──
    ".docx":  {"group":"documents",  "label_en":"Word Document",         "label_ar":"مستند وورد",          "needs_ocr":False},
    ".doc":   {"group":"documents",  "label_en":"Word 97-2003",          "label_ar":"وورد قديم",            "needs_ocr":False},
    ".rtf":   {"group":"documents",  "label_en":"Rich Text Format",      "label_ar":"نص منسق RTF",         "needs_ocr":False},
    ".odt":   {"group":"documents",  "label_en":"OpenDocument Text",     "label_ar":"مستند OpenDocument",   "needs_ocr":False},
    ".txt":   {"group":"documents",  "label_en":"Plain Text",            "label_ar":"نص عادي",              "needs_ocr":False},
    ".md":    {"group":"documents",  "label_en":"Markdown",              "label_ar":"ماركداون",              "needs_ocr":False},
    ".html":  {"group":"documents",  "label_en":"HTML Page",             "label_ar":"صفحة HTML",            "needs_ocr":False},
    ".htm":   {"group":"documents",  "label_en":"HTML Page",             "label_ar":"صفحة HTML",            "needs_ocr":False},
    ".xml":   {"group":"documents",  "label_en":"XML File",              "label_ar":"ملف XML",              "needs_ocr":False},
    ".json":  {"group":"documents",  "label_en":"JSON File",             "label_ar":"ملف JSON",             "needs_ocr":False},
    ".tex":   {"group":"documents",  "label_en":"LaTeX Document",        "label_ar":"مستند LaTeX",          "needs_ocr":False, "default_off":True},
    ".log":   {"group":"documents",  "label_en":"Log File",              "label_ar":"ملف سجل",              "needs_ocr":False, "default_off":True},
    ".ini":   {"group":"documents",  "label_en":"Config File",           "label_ar":"ملف إعدادات",          "needs_ocr":False, "default_off":True},
    ".yaml":  {"group":"documents",  "label_en":"YAML Config",           "label_ar":"ملف YAML",             "needs_ocr":False, "default_off":True},
    ".yml":   {"group":"documents",  "label_en":"YAML Config",           "label_ar":"ملف YAML",             "needs_ocr":False, "default_off":True},

    # ── PDFs ──
    ".pdf":   {"group":"pdf",        "label_en":"PDF Document",          "label_ar":"مستند PDF",            "needs_ocr":False},

    # ── Spreadsheets ──
    ".xlsx":  {"group":"spreadsheets","label_en":"Excel Workbook",       "label_ar":"ملف إكسل",             "needs_ocr":False},
    ".xls":   {"group":"spreadsheets","label_en":"Excel 97-2003",        "label_ar":"إكسل قديم",            "needs_ocr":False},
    ".xlsm":  {"group":"spreadsheets","label_en":"Excel with Macros",    "label_ar":"إكسل بماكرو",          "needs_ocr":False},
    ".csv":   {"group":"spreadsheets","label_en":"CSV File",             "label_ar":"ملف CSV",              "needs_ocr":False},
    ".tsv":   {"group":"spreadsheets","label_en":"TSV File",             "label_ar":"ملف TSV",              "needs_ocr":False},
    ".ods":   {"group":"spreadsheets","label_en":"OpenDocument Sheet",   "label_ar":"جدول OpenDocument",    "needs_ocr":False},
    ".numbers":{"group":"spreadsheets","label_en":"Apple Numbers",       "label_ar":"Apple Numbers",        "needs_ocr":False, "default_off":True},

    # ── Presentations ──
    ".pptx":  {"group":"presentations","label_en":"PowerPoint",          "label_ar":"عرض باوربوينت",        "needs_ocr":False},
    ".ppt":   {"group":"presentations","label_en":"PowerPoint 97-2003",  "label_ar":"باوربوينت قديم",       "needs_ocr":False},
    ".odp":   {"group":"presentations","label_en":"OpenDocument Present","label_ar":"عرض OpenDocument",     "needs_ocr":False},
    ".key":   {"group":"presentations","label_en":"Apple Keynote",       "label_ar":"Apple Keynote",        "needs_ocr":False, "default_off":True},

    # ── Diagrams ──
    ".vsd":   {"group":"diagrams",   "label_en":"Visio Diagram",         "label_ar":"رسم فيزيو",            "needs_ocr":False},
    ".vsdx":  {"group":"diagrams",   "label_en":"Visio Diagram (XML)",   "label_ar":"فيزيو XML",            "needs_ocr":False},
    ".vsdm":  {"group":"diagrams",   "label_en":"Visio with Macros",     "label_ar":"فيزيو بماكرو",         "needs_ocr":False},
    ".drawio":{"group":"diagrams",   "label_en":"Draw.io Diagram",       "label_ar":"رسم Draw.io",          "needs_ocr":False},
    ".svg":   {"group":"diagrams",   "label_en":"SVG Vector",            "label_ar":"رسم SVG",              "needs_ocr":False, "default_off":True},

    # ── Images (OCR) ──
    ".png":   {"group":"images",     "label_en":"PNG Image",             "label_ar":"صورة PNG",             "needs_ocr":True},
    ".jpg":   {"group":"images",     "label_en":"JPEG Image",            "label_ar":"صورة JPEG",            "needs_ocr":True},
    ".jpeg":  {"group":"images",     "label_en":"JPEG Image",            "label_ar":"صورة JPEG",            "needs_ocr":True},
    ".tiff":  {"group":"images",     "label_en":"TIFF Image",            "label_ar":"صورة TIFF",            "needs_ocr":True},
    ".tif":   {"group":"images",     "label_en":"TIFF Image",            "label_ar":"صورة TIFF",            "needs_ocr":True},
    ".bmp":   {"group":"images",     "label_en":"BMP Image",             "label_ar":"صورة BMP",             "needs_ocr":True},
    ".webp":  {"group":"images",     "label_en":"WebP Image",            "label_ar":"صورة WebP",            "needs_ocr":True},
    ".gif":   {"group":"images",     "label_en":"GIF Image",             "label_ar":"صورة GIF",             "needs_ocr":True,  "default_off":True},
    ".heic":  {"group":"images",     "label_en":"HEIC Image (iPhone)",   "label_ar":"صورة HEIC (آيفون)",    "needs_ocr":True,  "default_off":True},
    ".raw":   {"group":"images",     "label_en":"RAW Photo",             "label_ar":"صورة RAW",             "needs_ocr":True,  "default_off":True},

    # ── Code Files ──
    ".py":    {"group":"code",       "label_en":"Python Script",         "label_ar":"سكربت بايثون",         "needs_ocr":False, "default_off":True},
    ".js":    {"group":"code",       "label_en":"JavaScript",            "label_ar":"جافاسكربت",            "needs_ocr":False, "default_off":True},
    ".ts":    {"group":"code",       "label_en":"TypeScript",            "label_ar":"تايبسكربت",            "needs_ocr":False, "default_off":True},
    ".java":  {"group":"code",       "label_en":"Java Source",           "label_ar":"ملف جافا",             "needs_ocr":False, "default_off":True},
    ".cs":    {"group":"code",       "label_en":"C# Source",             "label_ar":"ملف سي شارب",          "needs_ocr":False, "default_off":True},
    ".cpp":   {"group":"code",       "label_en":"C++ Source",            "label_ar":"ملف C++",              "needs_ocr":False, "default_off":True},
    ".sql":   {"group":"code",       "label_en":"SQL Script",            "label_ar":"سكربت SQL",            "needs_ocr":False, "default_off":True},
    ".sh":    {"group":"code",       "label_en":"Shell Script",          "label_ar":"سكربت شل",             "needs_ocr":False, "default_off":True},
    ".ps1":   {"group":"code",       "label_en":"PowerShell Script",     "label_ar":"سكربت باورشل",         "needs_ocr":False, "default_off":True},
    ".bat":   {"group":"code",       "label_en":"Batch Script",          "label_ar":"سكربت BAT",            "needs_ocr":False, "default_off":True},
    ".r":     {"group":"code",       "label_en":"R Script",              "label_ar":"سكربت R",              "needs_ocr":False, "default_off":True},
    ".ipynb": {"group":"code",       "label_en":"Jupyter Notebook",      "label_ar":"دفتر جوبيتر",          "needs_ocr":False, "default_off":True},

    # ── eBooks ──
    ".epub":  {"group":"ebooks",     "label_en":"EPUB eBook",            "label_ar":"كتاب EPUB",            "needs_ocr":False, "default_off":True},
    ".mobi":  {"group":"ebooks",     "label_en":"Kindle eBook",          "label_ar":"كتاب كيندل",           "needs_ocr":False, "default_off":True},
    ".azw3":  {"group":"ebooks",     "label_en":"Kindle eBook",          "label_ar":"كتاب كيندل",           "needs_ocr":False, "default_off":True},
    ".djvu":  {"group":"ebooks",     "label_en":"DjVu Document",         "label_ar":"مستند DjVu",           "needs_ocr":False, "default_off":True},

    # ── Archives ──
    ".zip":   {"group":"archives",   "label_en":"ZIP Archive",           "label_ar":"أرشيف ZIP",            "needs_ocr":False, "default_off":True},
    ".rar":   {"group":"archives",   "label_en":"RAR Archive",           "label_ar":"أرشيف RAR",            "needs_ocr":False, "default_off":True},
    ".7z":    {"group":"archives",   "label_en":"7-Zip Archive",         "label_ar":"أرشيف 7Z",             "needs_ocr":False, "default_off":True},

    # ── CAD / 3D ──
    ".dwg":   {"group":"cad",        "label_en":"AutoCAD Drawing",       "label_ar":"رسم أوتوكاد",          "needs_ocr":False, "default_off":True},
    ".dxf":   {"group":"cad",        "label_en":"DXF Exchange",          "label_ar":"ملف DXF",              "needs_ocr":False, "default_off":True},
    ".step":  {"group":"cad",        "label_en":"STEP 3D Model",         "label_ar":"نموذج STEP",           "needs_ocr":False, "default_off":True},
    ".stl":   {"group":"cad",        "label_en":"STL 3D Print",          "label_ar":"ملف طباعة ثلاثية",     "needs_ocr":False, "default_off":True},

    # ── Audio / Video ──
    ".mp3":   {"group":"media",      "label_en":"MP3 Audio",             "label_ar":"صوت MP3",              "needs_ocr":False, "default_off":True},
    ".wav":   {"group":"media",      "label_en":"WAV Audio",             "label_ar":"صوت WAV",              "needs_ocr":False, "default_off":True},
    ".mp4":   {"group":"media",      "label_en":"MP4 Video",             "label_ar":"فيديو MP4",            "needs_ocr":False, "default_off":True},
    ".mkv":   {"group":"media",      "label_en":"MKV Video",             "label_ar":"فيديو MKV",            "needs_ocr":False, "default_off":True},
    ".avi":   {"group":"media",      "label_en":"AVI Video",             "label_ar":"فيديو AVI",            "needs_ocr":False, "default_off":True},
    ".mov":   {"group":"media",      "label_en":"QuickTime Video",       "label_ar":"فيديو QuickTime",      "needs_ocr":False, "default_off":True},
    ".m4a":   {"group":"media",      "label_en":"M4A Audio",             "label_ar":"صوت M4A",              "needs_ocr":False, "default_off":True},
}

# Group display info
FILE_GROUPS = {
    "documents":     {"icon":"📄","label_en":"Documents",     "label_ar":"مستندات"},
    "pdf":           {"icon":"📕","label_en":"PDFs",           "label_ar":"ملفات PDF"},
    "spreadsheets":  {"icon":"📊","label_en":"Spreadsheets",   "label_ar":"جداول بيانات"},
    "presentations": {"icon":"📽️","label_en":"Presentations",  "label_ar":"عروض تقديمية"},
    "diagrams":      {"icon":"📐","label_en":"Diagrams",       "label_ar":"مخططات ورسوم"},
    "images":        {"icon":"🖼️","label_en":"Images (OCR)",   "label_ar":"صور (OCR)"},
    "code":          {"icon":"💻","label_en":"Code Files",     "label_ar":"ملفات برمجية"},
    "ebooks":        {"icon":"📚","label_en":"eBooks",         "label_ar":"كتب إلكترونية"},
    "archives":      {"icon":"📦","label_en":"Archives",       "label_ar":"أرشيفات مضغوطة"},
    "cad":           {"icon":"🏗️","label_en":"CAD / 3D",       "label_ar":"تصميم هندسي / ثلاثي"},
    "media":         {"icon":"🎬","label_en":"Audio / Video",  "label_ar":"صوت / فيديو"},
}


def load_filetypes() -> dict:
    """Load file type settings. Returns {ext: {enabled:bool, ...}}."""
    # Start with defaults
    ft = {}
    for ext, info in _DEFAULT_FILETYPES.items():
        ft[ext] = {**info, "enabled": not info.get("default_off", False), "custom": False}

    # Override with saved settings
    try:
        if FILETYPES_FILE.exists():
            saved = json.loads(FILETYPES_FILE.read_text(encoding="utf-8"))
            for ext, sdata in saved.items():
                if ext in ft:
                    ft[ext]["enabled"] = sdata.get("enabled", ft[ext]["enabled"])
                else:
                    # Custom extension added by user
                    ft[ext] = {
                        "group": sdata.get("group", "documents"),
                        "label_en": sdata.get("label_en", ext),
                        "label_ar": sdata.get("label_ar", ext),
                        "needs_ocr": sdata.get("needs_ocr", False),
                        "enabled": sdata.get("enabled", True),
                        "custom": True,
                    }
    except Exception:
        pass
    return ft


def save_filetypes(ft: dict):
    """Save only non-default settings (overrides + custom extensions)."""
    to_save = {}
    for ext, info in ft.items():
        is_default = ext in _DEFAULT_FILETYPES
        if is_default:
            default_enabled = not _DEFAULT_FILETYPES[ext].get("default_off", False)
            if info["enabled"] != default_enabled:
                to_save[ext] = {"enabled": info["enabled"]}
        else:
            # Custom extension — save fully
            to_save[ext] = {
                "group": info.get("group", "documents"),
                "label_en": info.get("label_en", ext),
                "label_ar": info.get("label_ar", ext),
                "needs_ocr": info.get("needs_ocr", False),
                "enabled": info["enabled"],
            }
    try:
        FILETYPES_FILE.write_text(json.dumps(to_save, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_active_extensions(ft: dict) -> tuple:
    """Return (text_extensions: set, image_extensions: set, media_extensions: set)."""
    text_exts = set()
    img_exts = set()
    media_exts = set()
    MEDIA_GROUPS = {"media"}  # groups that are audio/video
    for ext, info in ft.items():
        if not info.get("enabled", False):
            continue
        grp = info.get("group", "")
        if grp in MEDIA_GROUPS:
            media_exts.add(ext)
        elif info.get("needs_ocr", False):
            img_exts.add(ext)
        else:
            text_exts.add(ext)
    return text_exts, img_exts, media_exts


def reset_filetypes():
    """Delete saved file type settings."""
    try:
        if FILETYPES_FILE.exists():
            FILETYPES_FILE.unlink()
    except Exception:
        pass

```

### File: `cleanup_dist.py`
The content of `cleanup_dist.py` is:
```py
"""
cleanup_dist.py — Reduce PyInstaller dist size by removing unnecessary files
Run after PyInstaller build: python cleanup_dist.py

Typically saves 30-50% of the dist folder size.
"""

import os
import shutil
from pathlib import Path

DIST_DIR = Path("dist/SmartDocCategorizer")

# Patterns to delete (case-insensitive)
DELETE_PATTERNS = [
    # Test files
    "**/test_*", "**/tests/**", "**/*_test.py",
    # Documentation
    "**/*.md", "**/*.txt", "**/*.rst",
    # Unnecessary locales (keep English + Arabic)
    "**/locales/**",
    # Debug symbols
    "**/*.pdb",
    # Duplicate DLLs / large unnecessary libs
    "**/msvcp140_1.dll",  # already in system
    "**/ucrtbase.dll",     # already in system
]

# Folders to delete entirely
DELETE_FOLDERS = [
    "tcl/tzdata",          # timezone data (not needed)
    "tcl/msgs",            # tcl messages (not needed)
    "tk/msgs",             # tk messages
    "numpy/tests",
    "numpy/f2py",
    "numpy/distutils",
    "PIL/tests",
    "docx/tests",
    "pptx/tests",
    "openpyxl/tests",
    "pdfminer/tests",
    "share/jupyter",
    "share/man",
    "include",
    "Scripts",
]

# File extensions to delete
DELETE_EXTENSIONS = {
    ".pyc",   # compiled python (already bundled)
    ".pyo",
    ".pyi",   # type stubs
    ".c",     # C source files
    ".h",     # C headers
    ".html",  # documentation
    ".map",   # source maps
}

def cleanup():
    if not DIST_DIR.exists():
        print(f"Dist directory not found: {DIST_DIR}")
        return

    before_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())
    deleted_count = 0
    freed = 0

    # Delete folders
    for folder_pattern in DELETE_FOLDERS:
        for folder in DIST_DIR.glob(f"**/{folder_pattern}"):
            if folder.is_dir():
                size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
                shutil.rmtree(folder, ignore_errors=True)
                freed += size
                deleted_count += 1
                print(f"  🗑️ {folder.relative_to(DIST_DIR)} ({size//1024:,} KB)")

    # Delete by extension
    for f in list(DIST_DIR.rglob("*")):
        if f.is_file() and f.suffix.lower() in DELETE_EXTENSIONS:
            size = f.stat().st_size
            f.unlink()
            freed += size
            deleted_count += 1

    after_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())

    print(f"\n{'═'*50}")
    print(f"  Before: {before_size // (1024*1024):,} MB")
    print(f"  After:  {after_size // (1024*1024):,} MB")
    print(f"  Saved:  {freed // (1024*1024):,} MB ({deleted_count} items)")
    print(f"{'═'*50}")


if __name__ == "__main__":
    cleanup()
```

### File: `engine.py`
The content of `engine.py` is:
```py
"""
CTO Knowledge Asset Categorizer v3.2 — Fixed Classification Engine
===================================================================
FIXES from v3.1:
  ✔ Word-boundary matching (no more "ears" matching "ea_")
  ✔ Minimum 2 distinct keywords required to classify
  ✔ Multi-word phrases weighted higher (more specific)
  ✔ Personal categories get priority (books/kids never go to PM)
  ✔ Negative keywords block false positives
  ✔ Short docs need stronger signals
  ✔ Arabic single-word traps fixed (مشروع ≠ project management)

Install:
    pip install python-docx pdfplumber openpyxl python-pptx tqdm Pillow
    pip install easyocr  # optional, for OCR

Usage:
    python cto_categorize_v3.py <source> [dest] [--ocr] [--gpu]
    python cto_categorize_v3.py "D:\\AllMyFiles"
    python cto_categorize_v3.py "D:\\AllMyFiles" --ocr --gpu
"""

import os, sys, re, csv, json, math, shutil, logging, io
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

try:
    from tqdm import tqdm; HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

import warnings
warnings.filterwarnings("ignore", message=".*Cannot set.*color.*")
warnings.filterwarnings("ignore", message=".*components specified.*")
for _ln in ("pdfminer","pdfminer.pdfpage","pdfminer.converter","pdfminer.cmapdb",
            "pdfminer.psparser","pdfminer.pdfdocument","pdfminer.pdfinterp"):
    logging.getLogger(_ln).setLevel(logging.CRITICAL)

log_fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("cto_v3"); log.setLevel(logging.INFO)
# In PyInstaller --windowed mode, sys.stderr is None — use NullHandler as fallback
if sys.stderr is not None:
    _ch = logging.StreamHandler(); _ch.setFormatter(log_fmt); log.addHandler(_ch)
else:
    log.addHandler(logging.NullHandler())

# ═══════════ CONFIG ═══════════
class Config:
    max_workers=12; max_pages_pdf=20; max_rows_excel=300
    text_sample=15000; score_thr=5.0; prod_thr=8  # raised thresholds
    min_distinct_kw=2   # minimum distinct keywords to classify
    ocr_on=True; gpu=False; file_timeout=30; ocr_timeout=60
    min_img_kb=20; max_img_mb=50; min_img_px=200; reset=False
    move_mode=False  # --move: move files instead of copy (safe: copy→verify→delete)
    dedup=False      # --dedup: detect and remove duplicate files
    dedup_action="report"  # report | delete | move_to_dupes
    transcribe_on=False  # --transcribe: transcribe audio/video files
    whisper_model="medium" # tiny|base|small|medium|large — medium is optimal for Arabic
    max_media_duration=300  # max seconds to transcribe per file
    @classmethod
    def from_args(cls, args):
        c=cls()
        for a in args:
            if a=="--ocr": c.ocr_on=True
            elif a=="--gpu": c.gpu=True; c.ocr_on=True
            elif a.startswith("--timeout="): c.file_timeout=int(a.split("=")[1]); c.ocr_timeout=c.file_timeout*2
            elif a.startswith("--workers="): c.max_workers=int(a.split("=")[1])
            elif a=="--reset": c.reset=True
            elif a=="--move": c.move_mode=True
            elif a=="--dedup": c.dedup=True
            elif a=="--transcribe": c.transcribe_on=True
        c.max_workers=int(os.environ.get("MAX_WORKERS",c.max_workers))
        if os.environ.get("OCR_ENABLED")=="1": c.ocr_on=True
        if os.environ.get("GPU","").lower()=="true": c.gpu=True; c.ocr_on=True
        return c
CFG=Config()

# ═══════════ FILE TYPES ═══════════
DOC_EXT={".docx",".doc",".rtf",".odt",".txt",".md",".html",".htm",".xml",".json"}
PDF_EXT={".pdf"}
SHT_EXT={".xlsx",".xls",".xlsm",".csv",".tsv",".ods"}
PRS_EXT={".pptx",".ppt",".odp",".key"}
DIA_EXT={".vsd",".vsdx",".vsdm",".drawio"}
IMG_EXT={".png",".jpg",".jpeg",".tiff",".tif",".bmp",".webp"}
MEDIA_EXT=set()  # populated dynamically from categories.py file types
TXT_EXTS=DOC_EXT|PDF_EXT|SHT_EXT|PRS_EXT|DIA_EXT
ALL_EXTS=TXT_EXTS|IMG_EXT|MEDIA_EXT

# ═══════════ OCR ENGINE (lazy) ═══════════
class SmartOCR:
    def __init__(self,gpu=False): self.name=None; self._r=None; self._gpu=gpu
    def _load(self):
        if self._r is not None or self.name=="__fail__": return
        try:
            import easyocr
            log.info("تحميل EasyOCR ...")
            self._r=easyocr.Reader(['ar','en'],gpu=self._gpu,verbose=False)
            self.name="easyocr"; log.info("  ✅ EasyOCR (GPU:%s)",self._gpu); return
        except: pass
        try:
            from paddleocr import PaddleOCR
            self._r=PaddleOCR(lang='ar',use_angle_cls=True,use_gpu=self._gpu,show_log=False)
            self.name="paddleocr"; log.info("  ✅ PaddleOCR"); return
        except: pass
        try:
            import pytesseract; pytesseract.get_tesseract_version()
            self.name="tesseract"; log.info("  ✅ Tesseract"); return
        except: pass
        self.name="__fail__"; log.warning("⚠ لا يوجد OCR — pip install easyocr")
    def ocr(self,img):
        self._load()
        if not self.name or self.name=="__fail__": return ""
        try:
            from PIL import ImageOps,ImageFilter,Image as PILImage
            import numpy as np
            if img.mode=="RGBA":
                bg=PILImage.new("RGB",img.size,(255,255,255)); bg.paste(img,mask=img.split()[3]); img=bg
            elif img.mode not in("L","RGB"): img=img.convert("RGB")
            w,h=img.size
            if min(w,h)<800:
                s=max(2,1000//min(w,h)); img=img.resize((w*s,h*s),PILImage.LANCZOS)
            g=img.convert("L"); g=ImageOps.autocontrast(g,cutoff=1); g=g.filter(ImageFilter.SHARPEN)
            na=np.array(g)
            if self.name=="easyocr":
                res=self._r.readtext(na,paragraph=True,min_size=10,text_threshold=0.6)
                return "\n".join(r[1] for r in res if len(r)>=2 and (len(r)<3 or r[2]>0.2))
            elif self.name=="paddleocr":
                res=self._r.ocr(na,cls=True); lines=[]
                if res and res[0]:
                    for l in res[0]:
                        if l and len(l)>=2:
                            t=l[1][0] if isinstance(l[1],(list,tuple)) else str(l[1]); lines.append(t)
                return "\n".join(lines)
            elif self.name=="tesseract":
                import pytesseract; return pytesseract.image_to_string(g,lang="ara+eng").strip()
        except Exception as e: log.debug("OCR err: %s",e)
        return ""
    def ocr_file(self,fp):
        try:
            from PIL import Image; return self.ocr(Image.open(fp))
        except: return ""

_ocr=None
def get_ocr():
    global _ocr
    if _ocr is None: _ocr=SmartOCR(gpu=CFG.gpu)
    return _ocr

# ═══════════ ARABIC NORM ═══════════
_AD=re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]')
_HM=str.maketrans({'\u0622':'\u0627','\u0623':'\u0627','\u0625':'\u0627','\u0671':'\u0627','\u0624':'\u0648','\u0626':'\u064A'})
_TM=str.maketrans({'\u0629':'\u0647'}); _AM=str.maketrans({'\u0649':'\u064A'})
def norm(t):
    t=_AD.sub('',t); t=t.translate(_HM).translate(_TM).translate(_AM)
    return re.sub(r'\s+',' ',t.lower())

# ═══════════ TEXT EXTRACTION ═══════════
def _rd(fp):
    for e in("utf-8","utf-8-sig","utf-16","cp1256","iso-8859-6","cp1252","latin-1"):
        try:
            t=Path(fp).read_text(encoding=e,errors="ignore")
            if len(t.strip())>10: return t
        except: continue
    return ""

def ex_docx(fp):
    try:
        from docx import Document; d=Document(fp)
        p=[p.text for p in d.paragraphs if p.text.strip()]
        for t in d.tables:
            for row in t.rows:
                c=[c.text.strip() for c in row.cells if c.text.strip()]
                if c: p.append(" | ".join(c))
        return "\n".join(p)
    except: return _rd(fp)

# Safe stderr suppressor — handles PyInstaller --windowed where sys.stderr is None
from contextlib import contextmanager
@contextmanager
def _suppress_stderr():
    """Temporarily suppress stderr (safe when sys.stderr is None in windowed mode)."""
    old = sys.stderr
    try:
        sys.stderr = io.StringIO()
        yield
    finally:
        sys.stderr = old if old is not None else io.StringIO()

def ex_pdf(fp):
    parts=[]
    try:
        import pdfplumber
        with _suppress_stderr():
            with pdfplumber.open(fp) as pdf:
                for pg in pdf.pages[:CFG.max_pages_pdf]:
                    t=pg.extract_text()
                    if t: parts.append(t)
    except: pass
    c="\n".join(parts)
    if len(c.strip())<50: c=f"__NEEDS_OCR__ {c}"
    return c

def ex_xlsx(fp):
    try:
        from openpyxl import load_workbook; wb=load_workbook(fp,read_only=True,data_only=True)
        p=[]
        for ws in wb.worksheets:
            p.append(f"[{ws.title}]")
            for r in ws.iter_rows(max_row=CFG.max_rows_excel,values_only=True):
                v=[str(c) for c in r if c is not None]
                if v: p.append(" ".join(v))
        wb.close(); return "\n".join(p)
    except: return _rd(fp)

def ex_csv(fp):
    import csv as _c
    try:
        t=_rd(fp)
        if not t: return ""
        d="\t" if Path(fp).suffix.lower()==".tsv" else ","
        return "\n".join(" ".join(r) for i,r in enumerate(_c.reader(t.splitlines(),delimiter=d)) if i<800)
    except: return ""

def ex_pptx(fp):
    try:
        from pptx import Presentation; pr=Presentation(fp); p=[]
        for sl in pr.slides:
            for sh in sl.shapes:
                if sh.has_text_frame:
                    for pa in sh.text_frame.paragraphs:
                        if pa.text.strip(): p.append(pa.text)
                if sh.has_table:
                    for r in sh.table.rows:
                        c=[c.text.strip() for c in r.cells if c.text.strip()]
                        if c: p.append(" | ".join(c))
            if sl.has_notes_slide and sl.notes_slide.notes_text_frame:
                n=sl.notes_slide.notes_text_frame.text.strip()
                if n: p.append(n)
        return "\n".join(p)
    except: return _rd(fp)

EX={".docx":ex_docx,".doc":_rd,".rtf":_rd,".odt":_rd,".txt":_rd,".md":_rd,
    ".html":_rd,".htm":_rd,".xml":_rd,".json":_rd,".pdf":ex_pdf,
    ".xlsx":ex_xlsx,".xls":_rd,".xlsm":ex_xlsx,".csv":ex_csv,".tsv":ex_csv,
    ".ods":_rd,".pptx":ex_pptx,".ppt":_rd,".odp":_rd,".key":_rd,
    ".vsd":_rd,".vsdx":_rd,".vsdm":_rd,".drawio":_rd,
    ".png":lambda f:"__IMG__",".jpg":lambda f:"__IMG__",".jpeg":lambda f:"__IMG__",
    ".tiff":lambda f:"__IMG__",".tif":lambda f:"__IMG__",".bmp":lambda f:"__IMG__",".webp":lambda f:"__IMG__"}

def extract(fp):
    ext = Path(fp).suffix.lower()
    # Known extractor
    if ext in EX:
        return EX[ext](fp)[:CFG.text_sample]
    # Dynamic image extension (needs OCR) — mark for OCR phase
    if ext in IMG_EXT:
        return "__IMG__"
    # Audio/Video — mark for transcription phase
    if ext in MEDIA_EXT:
        return "__MEDIA__"
    # Fallback: try reading as text
    return _rd(fp)[:CFG.text_sample]

def transcribe_media(fp):
    """Transcribe audio/video file using Whisper."""
    try:
        import transcribe as tr
        if not tr.is_available():
            return ""
        return tr.transcribe_text_only(
            fp, gpu=CFG.gpu,
            max_duration=CFG.max_media_duration,
            model_size=CFG.whisper_model
        )
    except ImportError:
        return ""
    except Exception as e:
        log.debug("Transcription error for %s: %s", fp, e)
        return ""

def ocr_image(fp):
    try:
        sz=Path(fp).stat().st_size/1024
        if sz<CFG.min_img_kb or sz>CFG.max_img_mb*1024: return ""
        from PIL import Image; im=Image.open(fp); w,h=im.size
        if min(w,h)<CFG.min_img_px: im.close(); return ""
        im.close()
    except: return ""
    return get_ocr().ocr_file(fp)

def ocr_pdf(fp):
    try:
        import pdfplumber; ocr=get_ocr()
        if not ocr.name or ocr.name=="__fail__": return ""
        texts=[]
        with _suppress_stderr():
            with pdfplumber.open(fp) as pdf:
                for pg in pdf.pages[:10]:
                    t=ocr.ocr(pg.to_image(resolution=200).original)
                    if t and t.strip(): texts.append(t)
        return "\n".join(texts)
    except: return ""


# ═══════════════════════════════════════════════════════════
#  COMPLETELY REWRITTEN CLASSIFICATION ENGINE v3.2
# ═══════════════════════════════════════════════════════════
#
#  Key fixes:
#  1. Word-boundary matching (regex \b for English, spaces for Arabic)
#  2. Minimum 2 distinct keywords to assign professional category
#  3. Multi-word phrases count as stronger signals
#  4. Personal categories ALWAYS checked first and take priority
#  5. Negative keywords block false positives
#  6. Short documents need more evidence
# ═══════════════════════════════════════════════════════════

# ── Build regex patterns for word-boundary matching ──

def _build_en_pattern(phrase):
    """Build regex for English phrase with word boundaries."""
    escaped = re.escape(phrase.lower())
    return re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)

def _build_ar_pattern(phrase):
    """Build regex for Arabic phrase with word boundaries.
    Arabic doesn't use \\b well, so we use space/start/end boundaries."""
    normalized = norm(phrase)
    escaped = re.escape(normalized)
    return re.compile(r'(?:^|[\s\.,;:!?\-/|()\"\'{}])'
                      + escaped +
                      r'(?:$|[\s\.,;:!?\-/|()\"\'{}])')

def _build_fn_pattern(hint):
    """Build regex for filename hint — must match as whole word/segment.
    Matches: ea_report, EA-doc, project_plan
    Does NOT match: ears, learning, bears"""
    escaped = re.escape(hint.lower())
    # Match at word boundary or separated by _ - . /
    return re.compile(r'(?:^|[_\-./\\\ ])'
                      + escaped +
                      r'(?:$|[_\-./\\\ ])', re.IGNORECASE)


# ═══════════ CATEGORY DEFINITIONS ═══════════
# Structure per category:
#   "en": {phrase: weight}     — English keywords (word-boundary matched)
#   "ar": {phrase: weight}     — Arabic keywords (normalized + boundary matched)
#   "fh": [hints]              — Filename hints (whole-word matched)
#   "ph": [hints]              — Path hints
#   "neg_en": [words]          — Negative signals (English) — if found, reduce score
#   "neg_ar": [words]          — Negative signals (Arabic)
#   "pp": str                  — Product potential
#   "personal": bool           — Is this a personal category?

# ═══════════ DYNAMIC CATEGORIES ═══════════
# Categories are loaded from categories.py (user-editable, role presets)
# Fallback to hardcoded defaults if categories.py not available

try:
    from categories import load_categories
    CATEGORIES = load_categories()
except ImportError:
    CATEGORIES = {}  # will be populated by engine's own defaults if needed

_COMPILED = {}

def compile_categories():
    """Compile regex patterns for all categories. Call after loading/changing categories."""
    global _COMPILED
    _COMPILED = {}
    for cat_name, cat_info in CATEGORIES.items():
        c = {"en": [], "ar": [], "fh": [], "ph": [], "neg": []}
        for phrase, weight in cat_info.get("en", {}).items():
            wc = len(phrase.split())
            c["en"].append((_build_en_pattern(phrase), weight, wc, phrase))
        for phrase, weight in cat_info.get("ar", {}).items():
            wc = len(phrase.split())
            c["ar"].append((_build_ar_pattern(phrase), weight, wc, phrase))
        for hint in cat_info.get("fh", []):
            c["fh"].append(_build_fn_pattern(hint))
        for hint in cat_info.get("ph", []):
            c["ph"].append(_build_fn_pattern(hint))
        for neg in cat_info.get("neg_en", []):
            c["neg"].append(_build_en_pattern(neg))
        for neg in cat_info.get("neg_ar", []):
            c["neg"].append(_build_ar_pattern(neg))
        _COMPILED[cat_name] = c

def reload_categories(new_cats=None):
    """Reload categories (called from GUI when user edits categories)."""
    global CATEGORIES
    if new_cats:
        CATEGORIES = new_cats
    else:
        try:
            from categories import load_categories
            CATEGORIES = load_categories()
        except ImportError:
            pass
    compile_categories()

# Initial compile
compile_categories()


# ═══════════ CLASSIFICATION ENGINE ═══════════

def build_ctx(fp, fn):
    return norm(" ".join(Path(fp).parts[-5:]) + " " + fn)

def classify(text, filepath, filename):
    """
    Classify a document. Returns (category, score, product_potential, matches).

    Rules:
    1. Personal categories are scored first — if ANY personal category
       scores above threshold, it wins over ALL professional categories.
    2. Professional categories need at least 2 distinct keyword matches.
    3. Negative keywords reduce score by 50%.
    4. Multi-word phrases get a 1.5x bonus (more reliable signals).
    5. Filename/path hints only add to score, they can't be the sole signal.
    """
    text_norm = norm(text)
    fn_lower = filename.lower().replace(" ", "_")
    ctx = build_ctx(filepath, filename)

    personal_best = None     # (cat, score, pp, matches)
    professional_best = None

    for cat_name, cat_info in CATEGORIES.items():
        compiled = _COMPILED[cat_name]
        is_personal = cat_info.get("personal", False)

        score = 0.0
        matched = []
        distinct_kw = set()  # track unique keywords
        hint_score = 0.0     # score from hints only

        # ── English keywords (word-boundary regex) ──
        for pattern, weight, word_count, phrase in compiled["en"]:
            matches = pattern.findall(text_norm)
            count = len(matches)
            if count > 0:
                # Multi-word bonus: 2+ word phrases are 1.5x
                multiplier = 1.5 if word_count >= 2 else 1.0
                s = weight * multiplier * (1 + math.log(count))
                score += s
                distinct_kw.add(phrase)
                matched.append((phrase, round(s, 1)))

        # ── Arabic keywords (normalized + boundary regex) ──
        for pattern, weight, word_count, phrase in compiled["ar"]:
            matches = pattern.findall(text_norm)
            count = len(matches)
            if count > 0:
                multiplier = 1.5 if word_count >= 2 else 1.0
                s = weight * multiplier * (1 + math.log(count))
                score += s
                distinct_kw.add(phrase)
                matched.append((phrase, round(s, 1)))

        # ── Filename hints (whole-word boundary) ──
        for pattern in compiled["fh"]:
            if pattern.search(fn_lower):
                hint_score += 4
                matched.append(("📄 filename", 4))

        # ── Path hints ──
        for pattern in compiled["ph"]:
            if pattern.search(ctx):
                hint_score += 3
                matched.append(("📁 path", 3))

        # ── Extension bonus for diagrams ──
        ext = Path(filename).suffix.lower()
        if cat_name == "23_Diagrams_Visuals" and ext in DIA_EXT:
            score += 6
            distinct_kw.add("__ext__")
            matched.append(("🔧 " + ext, 6))

        # ── Negative keyword penalty ──
        neg_count = 0
        for neg_pat in compiled["neg"]:
            if neg_pat.search(text_norm):
                neg_count += 1
        if neg_count > 0:
            score *= max(0.2, 1.0 - 0.3 * neg_count)  # reduce 30% per neg, min 20%

        # Add hint score (but hints alone can't classify)
        total_score = score + hint_score

        # ── Minimum diversity check for professional categories ──
        if not is_personal and len(distinct_kw) < CFG.min_distinct_kw:
            # If only hints but no content keywords, skip
            if score < CFG.score_thr:
                total_score = min(total_score, CFG.score_thr - 0.1)

        total_score = round(total_score, 2)
        matched_sorted = sorted(matched, key=lambda x: -x[1])[:6]

        entry = (cat_name, total_score, cat_info["pp"], matched_sorted)

        if is_personal:
            if personal_best is None or total_score > personal_best[1]:
                personal_best = entry
        else:
            if professional_best is None or total_score > professional_best[1]:
                professional_best = entry

    # ── Decision logic ──

    # Rule 1: If personal category scores above threshold, it ALWAYS wins
    if personal_best and personal_best[1] >= CFG.score_thr:
        return personal_best

    # Rule 2: Otherwise use professional
    if professional_best and professional_best[1] >= CFG.score_thr:
        return professional_best

    # Rule 3: Below threshold → Uncategorized
    best = max([e for e in [personal_best, professional_best] if e],
               key=lambda x: x[1], default=None)
    if best:
        return ("99_Uncategorized", best[1], "UNKNOWN", best[3])
    return ("99_Uncategorized", 0.0, "UNKNOWN", [])


# ═══════════ HELPERS ═══════════
def hsz(n):
    for u in("B","KB","MB","GB"):
        if abs(n)<1024: return f"{n:.1f} {u}"
        n/=1024
    return f"{n:.1f} TB"

def uniq(d,fn):
    t=d/fn
    if not t.exists(): return t
    s,x=Path(fn).stem,Path(fn).suffix; c=1
    while True:
        t=d/f"{s}({c}){x}"
        if not t.exists(): return t
        c+=1

def dlang(t):
    if not t: return "unknown"
    ar=len(re.findall(r'[\u0600-\u06FF]',t[:5000]))
    en=len(re.findall(r'[a-zA-Z]',t[:5000]))
    tot=ar+en
    if tot==0: return "unknown"
    r=ar/tot
    return "ar" if r>0.7 else("mixed" if r>0.2 else "en")

def mkrow(src,fn,ext,sz,cat,sc,pp,kws,dst=None,dup=False,lang="unknown",ocr=False,err=None):
    return {"source":str(src),"destination":dst,"filename":fn,"extension":ext,"size":sz,
            "category":cat,"score":sc,"product_potential":pp,"top_keywords":kws,
            "duplicate":dup,"language":lang,"ocr_used":ocr,"error":err}

# ═══════════ PROCESS FILE ═══════════
def proc(src,dest,do_ocr=False,do_transcribe=False):
    fn=src.name; ext=src.suffix.lower()
    if ext not in ALL_EXTS: return None

    # Resume safety: if file was already moved, skip gracefully
    if not src.exists():
        return None

    try:
        sz=src.stat().st_size
        if sz>200*1024*1024: return mkrow(src,fn,ext,sz,"99_Uncategorized",0,"NONE",[],err="Skipped >200MB")

        is_img=ext in IMG_EXT; is_scan=False; is_media=ext in MEDIA_EXT
        transcribed=False

        if is_img and not do_ocr: text=""
        elif is_media and not do_transcribe: text=""
        else: text=extract(str(src))

        if isinstance(text,str) and text.startswith("__NEEDS_OCR__"):
            is_scan=True; text=text.replace("__NEEDS_OCR__","").strip()
            if do_ocr:
                ot=ocr_pdf(str(src))
                if ot: text=ot
        if is_img and do_ocr and (not text or text=="__IMG__"):
            text=ocr_image(str(src))
        if text=="__IMG__": text=""

        # Media transcription
        if is_media and do_transcribe and (not text or text=="__MEDIA__"):
            text=transcribe_media(str(src))
            if text: transcribed=True
        if text=="__MEDIA__": text=""

        lang=dlang(text)
        cat,sc,pp,matches=classify(text,str(src),fn)
        cf=dest/cat; cf.mkdir(parents=True,exist_ok=True)
        df=uniq(cf,fn); dup=df.name!=fn

        # Safe transfer: copy → verify → delete source (if --move)
        shutil.copy2(src,df)

        if CFG.move_mode:
            # Verify destination exists and matches size before deleting source
            if df.exists() and df.stat().st_size == sz:
                try:
                    src.unlink()
                except Exception as e:
                    log.debug("Could not delete source %s: %s", src, e)

        return mkrow(src,fn,ext,sz,cat,sc,pp,[m[0] for m in matches],
                    dst=str(df),dup=dup,lang=lang,
                    ocr=(is_img and do_ocr)or(is_scan and do_ocr) or transcribed)
    except Exception as e:
        return mkrow(src,fn,ext,0,"ERROR",0,"NONE",[],err=str(e))

# ═══════════ BATCH PROCESSOR ═══════════
# GUI callbacks (set by app.py before calling run)
_progress_cb = None    # fn(current, total, filename, category)
_log_cb = None         # fn(message)
_cancel = None         # threading.Event — set to stop

def set_callbacks(progress_fn=None, log_fn=None, cancel_event=None):
    global _progress_cb, _log_cb, _cancel
    _progress_cb = progress_fn
    _log_cb = log_fn
    _cancel = cancel_event

def batch(files,dest,done,rpath,do_ocr,timeout,desc,workers=None):
    results=[]; errs=0; tos=0; w=workers or CFG.max_workers
    prog=tqdm(total=len(files),desc=desc,unit="ملف") if (HAS_TQDM and sys.stderr is not None) else None
    save_n=max(200,len(files)//10)
    total=len(files)
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs={ex.submit(proc,f,dest,do_ocr):f for f in files}
        dc=0
        for fut in as_completed(futs):
            # Check cancellation
            if _cancel and _cancel.is_set():
                ex.shutdown(wait=False,cancel_futures=True)
                if _log_cb: _log_cb("⚠ تم الإيقاف بواسطة المستخدم")
                break
            try:
                r=fut.result(timeout=timeout)
                if r:
                    results.append(r)
                    if r["error"]: errs+=1
                    done.add(r["source"])
                    if _progress_cb: _progress_cb(dc+1,total,r.get("filename",""),r.get("category",""))
            except TimeoutError:
                fp=futs[fut]; tos+=1
                results.append(mkrow(fp,fp.name,fp.suffix.lower(),0,"99_Uncategorized",0,"NONE",[],err=f"Timeout({timeout}s)"))
                done.add(str(fp))
            except Exception as e:
                fp=futs[fut]
                results.append(mkrow(fp,fp.name,fp.suffix.lower(),0,"ERROR",0,"NONE",[],err=str(e)))
                done.add(str(fp))
            dc+=1
            if prog: prog.update(1)
            elif dc%1000==0: log.info("  ... %d / %d",dc,total)
            if dc%save_n==0:
                try: rpath.write_text(json.dumps(list(done),ensure_ascii=False),encoding="utf-8")
                except: pass
    if prog: prog.close()
    try: rpath.write_text(json.dumps(list(done),ensure_ascii=False),encoding="utf-8")
    except: pass
    log.info("  ✅ %d معالج | %d خطأ | %d timeout",len(results),errs,tos)
    return results

# ═══════════════════════════════════════════════════════════
#  DUPLICATE DETECTION ENGINE
# ═══════════════════════════════════════════════════════════
#
#  Detection layers (fast → accurate):
#    1. Group by file size (instant filter — different size = not duplicate)
#    2. Partial hash: first 8KB + last 8KB (catches 99% of dupes fast)
#    3. Full content hash (MD5 — confirms true duplicates)
#    4. Metadata comparison (author, title, dates from doc headers)
#
#  For each duplicate group, keeps the "best" copy based on:
#    - Highest classification score
#    - Most recent modification date
#    - Shortest path (less deeply nested)
# ═══════════════════════════════════════════════════════════

import hashlib

def _file_hash_partial(filepath, chunk_size=8192):
    """Fast partial hash: first 8KB + last 8KB + size."""
    try:
        p = Path(filepath)
        sz = p.stat().st_size
        h = hashlib.md5()
        h.update(str(sz).encode())
        with open(filepath, 'rb') as f:
            h.update(f.read(chunk_size))
            if sz > chunk_size * 2:
                f.seek(-chunk_size, 2)
                h.update(f.read(chunk_size))
        return h.hexdigest()
    except Exception:
        return None

def _file_hash_full(filepath):
    """Full MD5 hash of entire file content."""
    try:
        h = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def _extract_metadata(filepath):
    """Extract document metadata (author, title, created, modified)."""
    meta = {}
    ext = Path(filepath).suffix.lower()
    try:
        if ext == '.docx':
            from docx import Document
            d = Document(filepath)
            cp = d.core_properties
            meta['title'] = cp.title or ''
            meta['author'] = cp.author or ''
            meta['created'] = str(cp.created) if cp.created else ''
            meta['modified'] = str(cp.modified) if cp.modified else ''
            meta['revision'] = str(cp.revision) if cp.revision else ''
        elif ext == '.pptx':
            from pptx import Presentation
            p = Presentation(filepath)
            cp = p.core_properties
            meta['title'] = cp.title or ''
            meta['author'] = cp.author or ''
            meta['created'] = str(cp.created) if cp.created else ''
            meta['modified'] = str(cp.modified) if cp.modified else ''
        elif ext == '.xlsx':
            from openpyxl import load_workbook
            wb = load_workbook(filepath, read_only=True)
            props = wb.properties
            meta['title'] = props.title or ''
            meta['author'] = props.creator or ''
            meta['created'] = str(props.created) if props.created else ''
            meta['modified'] = str(props.modified) if props.modified else ''
            wb.close()
        elif ext == '.pdf':
            import pdfplumber
            with _suppress_stderr():
                with pdfplumber.open(filepath) as pdf:
                    info = pdf.metadata or {}
                    meta['title'] = info.get('Title', '')
                    meta['author'] = info.get('Author', '')
                    meta['created'] = info.get('CreationDate', '')
                    meta['modified'] = info.get('ModDate', '')
                    meta['producer'] = info.get('Producer', '')
                    meta['pages'] = len(pdf.pages)
    except Exception:
        pass

    # File system metadata
    try:
        st = Path(filepath).stat()
        meta['fs_size'] = st.st_size
        meta['fs_modified'] = datetime.fromtimestamp(st.st_mtime).isoformat()
        meta['fs_created'] = datetime.fromtimestamp(st.st_ctime).isoformat()
    except Exception:
        pass

    return meta


def _pick_best_copy(group):
    """
    From a list of duplicate file dicts, pick the 'best' one to keep.
    Priority: highest classification score → most recent → shortest path.
    """
    def sort_key(item):
        score = item.get('score', 0)
        # Parse modification time
        try:
            mtime = Path(item['destination']).stat().st_mtime if item.get('destination') else 0
        except Exception:
            mtime = 0
        # Shorter path = probably less deeply nested = more accessible
        path_len = len(item.get('destination', '')) if item.get('destination') else 9999
        return (-score, -mtime, path_len)

    sorted_group = sorted(group, key=sort_key)
    return sorted_group[0]  # best


def find_duplicates(results, dest_path):
    """
    Detect duplicates among categorized files.
    Returns: (duplicates_groups, dedup_report)

    Each group: {
        'hash': str,
        'keep': dict (file row to keep),
        'remove': [dict] (file rows to remove),
        'match_type': 'exact_content' | 'same_content_diff_name' | 'metadata_match',
        'size': int,
    }
    """
    if _log_cb:
        _log_cb("🔍 بدء فحص التكرارات ...")

    # Only check successfully categorized files with valid destinations
    valid = [r for r in results if r.get('destination') and not r.get('error')
             and Path(r['destination']).exists()]

    if not valid:
        return [], {}

    # ── Phase 1: Group by size (instant filter) ──
    size_groups = defaultdict(list)
    for r in valid:
        try:
            sz = Path(r['destination']).stat().st_size
            if sz > 0:  # skip empty files
                size_groups[sz].append(r)
        except Exception:
            pass

    # Only keep groups with 2+ same-size files
    candidates = {sz: items for sz, items in size_groups.items() if len(items) >= 2}

    if _log_cb:
        total_candidates = sum(len(v) for v in candidates.values())
        _log_cb(f"  المرحلة 1: {total_candidates} ملف بأحجام متطابقة ({len(candidates)} مجموعة)")

    if not candidates:
        if _log_cb:
            _log_cb("  ✅ لم يتم العثور على ملفات مكررة")
        return [], {"total_checked": len(valid), "duplicates_found": 0}

    # ── Phase 2: Partial hash (fast — first+last 8KB) ──
    partial_groups = defaultdict(list)
    for sz, items in candidates.items():
        for r in items:
            ph = _file_hash_partial(r['destination'])
            if ph:
                partial_groups[ph].append(r)

    partial_dupes = {h: items for h, items in partial_groups.items() if len(items) >= 2}

    if _log_cb:
        _log_cb(f"  المرحلة 2: {len(partial_dupes)} مجموعة بـ partial hash متطابق")

    if not partial_dupes:
        if _log_cb:
            _log_cb("  ✅ لم يتم العثور على ملفات مكررة")
        return [], {"total_checked": len(valid), "duplicates_found": 0}

    # ── Phase 3: Full hash (confirms true duplicates) ──
    duplicate_groups = []
    total_dupes = 0

    for ph, items in partial_dupes.items():
        # Full hash each file
        full_hash_groups = defaultdict(list)
        for r in items:
            fh = _file_hash_full(r['destination'])
            if fh:
                full_hash_groups[fh].append(r)

        for fh, group in full_hash_groups.items():
            if len(group) >= 2:
                best = _pick_best_copy(group)
                removes = [r for r in group if r is not best]
                total_dupes += len(removes)

                # Determine match type
                names = set(r['filename'] for r in group)
                match_type = 'exact_content' if len(names) == 1 else 'same_content_diff_name'

                duplicate_groups.append({
                    'hash': fh,
                    'keep': best,
                    'remove': removes,
                    'match_type': match_type,
                    'size': group[0].get('size', 0),
                    'count': len(group),
                })

    # ── Phase 4: Metadata-based near-duplicates ──
    # Check files with same metadata (title+author) but different content
    # These might be different versions of the same document
    meta_groups = defaultdict(list)
    for r in valid:
        dest = r.get('destination')
        if not dest:
            continue
        ext = Path(dest).suffix.lower()
        if ext in ('.docx', '.pptx', '.xlsx', '.pdf'):
            meta = _extract_metadata(dest)
            title = (meta.get('title', '') or '').strip().lower()
            author = (meta.get('author', '') or '').strip().lower()
            if title and len(title) > 3:  # meaningful title
                key = f"{title}|{author}|{ext}"
                meta_groups[key].append({**r, '_meta': meta})

    near_dupes = []
    for key, group in meta_groups.items():
        if len(group) >= 2:
            # Check they're not already in exact duplicates
            dests = set(r['destination'] for r in group)
            already_found = False
            for dg in duplicate_groups:
                existing_dests = {dg['keep']['destination']} | {r['destination'] for r in dg['remove']}
                if dests & existing_dests:
                    already_found = True
                    break
            if not already_found:
                best = _pick_best_copy(group)
                removes = [r for r in group if r is not best]
                near_dupes.append({
                    'hash': f"meta:{key[:50]}",
                    'keep': best,
                    'remove': removes,
                    'match_type': 'metadata_match',
                    'size': group[0].get('size', 0),
                    'count': len(group),
                    'meta_key': key,
                })

    all_groups = duplicate_groups + near_dupes
    total_removable = sum(len(g['remove']) for g in all_groups)
    total_space = sum(
        sum(Path(r['destination']).stat().st_size for r in g['remove']
            if r.get('destination') and Path(r['destination']).exists())
        for g in all_groups
    )

    if _log_cb:
        _log_cb(f"  المرحلة 3: {len(duplicate_groups)} مجموعة تكرار حقيقي (content match)")
        _log_cb(f"  المرحلة 4: {len(near_dupes)} مجموعة تكرار محتمل (metadata match)")
        _log_cb(f"  📊 إجمالي: {total_removable} ملف مكرر | {hsz(total_space)} مساحة قابلة للتحرير")

    report = {
        "total_checked": len(valid),
        "exact_duplicate_groups": len(duplicate_groups),
        "near_duplicate_groups": len(near_dupes),
        "duplicates_found": total_removable,
        "space_recoverable": total_space,
        "space_recoverable_human": hsz(total_space),
    }

    return all_groups, report


def apply_dedup(duplicate_groups, dest_path, action="move_to_dupes"):
    """
    Apply dedup action to duplicate files.
    action: 'report' (do nothing), 'delete', 'move_to_dupes'
    Returns count of files acted on.
    """
    if action == "report":
        return 0

    dupes_folder = dest_path / "_duplicates"
    acted = 0

    for group in duplicate_groups:
        for r in group['remove']:
            fp = Path(r['destination'])
            if not fp.exists():
                continue
            try:
                if action == "delete":
                    fp.unlink()
                    acted += 1
                elif action == "move_to_dupes":
                    dupes_folder.mkdir(parents=True, exist_ok=True)
                    match_type = group.get('match_type', 'unknown')
                    sub = dupes_folder / match_type
                    sub.mkdir(exist_ok=True)
                    target = sub / fp.name
                    # Handle name collision in dupes folder
                    if target.exists():
                        stem, suffix = fp.stem, fp.suffix
                        c = 1
                        while target.exists():
                            target = sub / f"{stem}({c}){suffix}"
                            c += 1
                    shutil.move(str(fp), str(target))
                    acted += 1
            except Exception as e:
                log.debug("Dedup action failed for %s: %s", fp, e)

    if _log_cb:
        _log_cb(f"  {'🗑️ حذف' if action=='delete' else '📦 نقل'} {acted} ملف مكرر")

    return acted


def save_dedup_report(duplicate_groups, dedup_stats, dest_path):
    """Save detailed duplicate report as CSV + JSON."""
    # CSV Report
    csv_path = dest_path / "_DUPLICATES_REPORT.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[
            "group_id", "match_type", "action", "filename",
            "category", "score", "size", "path",
            "title", "author", "modified",
        ])
        w.writeheader()
        for i, group in enumerate(duplicate_groups, 1):
            # Write the kept file
            keep = group['keep']
            meta = _extract_metadata(keep['destination']) if keep.get('destination') and Path(keep['destination']).exists() else {}
            w.writerow({
                "group_id": i,
                "match_type": group['match_type'],
                "action": "✅ KEEP",
                "filename": keep.get('filename', ''),
                "category": keep.get('category', ''),
                "score": keep.get('score', 0),
                "size": keep.get('size', 0),
                "path": keep.get('destination', ''),
                "title": meta.get('title', ''),
                "author": meta.get('author', ''),
                "modified": meta.get('fs_modified', ''),
            })
            # Write duplicates
            for r in group['remove']:
                meta_r = _extract_metadata(r['destination']) if r.get('destination') and Path(r['destination']).exists() else {}
                w.writerow({
                    "group_id": i,
                    "match_type": group['match_type'],
                    "action": "❌ DUPLICATE",
                    "filename": r.get('filename', ''),
                    "category": r.get('category', ''),
                    "score": r.get('score', 0),
                    "size": r.get('size', 0),
                    "path": r.get('destination', r.get('source', '')),
                    "title": meta_r.get('title', ''),
                    "author": meta_r.get('author', ''),
                    "modified": meta_r.get('fs_modified', ''),
                })

    # JSON Report
    json_path = dest_path / "_DUPLICATES_REPORT.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "stats": dedup_stats,
            "groups": [
                {
                    "match_type": g['match_type'],
                    "hash": g['hash'],
                    "file_count": g['count'],
                    "keep": g['keep']['destination'],
                    "remove": [r['destination'] for r in g['remove']],
                }
                for g in duplicate_groups
            ],
        }, f, indent=2, ensure_ascii=False)

    log.info("تقرير التكرارات CSV → %s", csv_path)
    log.info("تقرير التكرارات JSON → %s", json_path)


# ═══════════ REPORTS ═══════════
def reports(results,dest,src):
    stats=defaultdict(lambda:{"c":0,"s":0,"pp":"","l":defaultdict(int),"o":0})
    prods=[]
    for r in results:
        cat=r["category"]; stats[cat]["c"]+=1; stats[cat]["s"]+=r.get("size",0)
        stats[cat]["pp"]=r.get("product_potential","")
        stats[cat]["l"][r.get("language","unknown")]+=1
        if r.get("ocr_used"): stats[cat]["o"]+=1
        if r.get("product_potential") in("HIGH","VERY_HIGH") and r.get("score",0)>=CFG.prod_thr:
            prods.append(r)
    log.info(""); log.info("═"*80); log.info("  النتائج"); log.info("═"*80)
    log.info("  إجمالي: %d",len(results))
    log.info("─"*80)
    log.info("  %-38s %5s %9s %4s %4s %4s  %s","التصنيف","عدد","حجم","عر","إنج","OCR","منتج؟")
    log.info("─"*80)
    for cat in sorted(stats):
        s=stats[cat]; ar=s["l"].get("ar",0)+s["l"].get("mixed",0); en=s["l"].get("en",0)
        log.info("  %-38s %5d %9s %4d %4d %4d  %s",cat,s["c"],hsz(s["s"]),ar,en,s["o"],s.get("pp",""))
    log.info("═"*80); log.info("  ★ ملفات منتجات: %d",len(prods)); log.info("═"*80)

    rj=dest/"_categorization_report.json"
    with open(rj,"w",encoding="utf-8") as f:
        json.dump({"timestamp":datetime.now().isoformat(),"source":str(src),"total":len(results),
                   "category_summary":{c:{"count":s["c"],"size":hsz(s["s"]),"product_potential":s.get("pp","")} for c,s in sorted(stats.items())},
                   "product_candidates":len(prods),"files":results},f,indent=2,ensure_ascii=False)
    log.info("JSON → %s",rj)

    rc=dest/"_categorization_report.csv"
    with open(rc,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["filename","extension","language","ocr_used","category","score","product_potential","top_keywords","duplicate","size","source","destination","error"])
        w.writeheader()
        for r in results:
            row=dict(r); row["top_keywords"]=" | ".join(str(x) for x in row.get("top_keywords",[])); w.writerow(row)
    log.info("CSV  → %s",rc)

    if prods:
        pc=dest/"_PRODUCT_CANDIDATES.csv"
        with open(pc,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=["filename","language","category","score","product_potential","top_keywords","source"])
            w.writeheader()
            for r in sorted(prods,key=lambda x:-x["score"]):
                w.writerow({"filename":r["filename"],"language":r.get("language",""),"category":r["category"],
                           "score":r["score"],"product_potential":r["product_potential"],
                           "top_keywords":" | ".join(str(x) for x in r.get("top_keywords",[])),"source":r["source"]})
        log.info("★ منتجات → %s",pc)
    log.info(""); log.info("✅ انتهى!")
    if CFG.move_mode:
        moved = sum(1 for r in results if not r.get("error") and r.get("destination"))
        log.info("  📦 تم نقل %d ملف (المصدر تم حذفه)", moved)

# ═══════════ MAIN ═══════════
def run(source,destination):
    """
    Main pipeline. source can be a single path (str) or list of paths.
    """
    # Multi-source support
    if isinstance(source, (list, tuple)):
        sources = [Path(s).resolve() for s in source if s and Path(s).is_dir()]
    else:
        sp = Path(source).resolve()
        if not sp.is_dir():
            log.error("غير موجود: %s", sp)
            if not _progress_cb: sys.exit(1)
            return
        sources = [sp]

    if not sources:
        log.error("No valid source folders")
        return

    dp=Path(destination).resolve()
    dp.mkdir(parents=True,exist_ok=True)

    # Add file handler (avoid duplicates on repeated runs)
    log_path = dp / "_categorization.log"
    existing = [h for h in log.handlers if isinstance(h, logging.FileHandler)
                and hasattr(h, 'baseFilename') and Path(h.baseFilename).name == "_categorization.log"]
    if not existing:
        fh=logging.FileHandler(log_path, encoding="utf-8"); fh.setFormatter(log_fmt); log.addHandler(fh)

    log.info("═"*65)
    log.info("  Smart Document Categorizer v4.0")
    log.info("═"*65)
    for i, sp in enumerate(sources):
        log.info("  المصدر %d : %s", i+1, sp)
    log.info("  الوجهة   : %s",dp)
    log.info("  OCR      : %s","ON" if CFG.ocr_on else "OFF")
    log.info("  Transcribe: %s","ON (%s)" % CFG.whisper_model if CFG.transcribe_on else "OFF")
    log.info("  Mode     : %s","MOVE" if CFG.move_mode else "COPY")
    log.info("  Workers  : %d | Timeout: %ds",CFG.max_workers,CFG.file_timeout)
    log.info("═"*65)

    # Safety confirmation for --move (CLI only, skip in GUI)
    if CFG.move_mode and not _progress_cb:
        log.info("  ⚠  وضع النقل (MOVE) مفعّل!")
        try:
            confirm = input("     هل تريد المتابعة؟ (y/n): ").strip().lower()
            if confirm not in ("y", "yes", "نعم"):
                log.info("  تم الإلغاء."); return
        except (EOFError, KeyboardInterrupt):
            log.info("  تم الإلغاء."); return

    # ── Discover files from all sources ──
    log.info("جاري البحث ...")
    all_f=[]
    for sp in sources:
        for root,_,fnames in os.walk(sp):
            for fn in fnames:
                if Path(fn).suffix.lower() in ALL_EXTS:
                    all_f.append(Path(root)/fn)

    txt_f=[f for f in all_f if f.suffix.lower() in TXT_EXTS]
    img_f=[f for f in all_f if f.suffix.lower() in IMG_EXT]
    media_f=[f for f in all_f if f.suffix.lower() in MEDIA_EXT]
    log.info("  إجمالي: %d | نصية: %d | صور: %d | صوت/فيديو: %d",
             len(all_f),len(txt_f),len(img_f),len(media_f))

    rp=dp/"_processed_files.json"; done=set()
    if not CFG.reset and rp.exists():
        try: done=set(json.loads(rp.read_text(encoding="utf-8"))); log.info("  سابق: %d",len(done))
        except: pass

    tp=[f for f in txt_f if str(f) not in done and f.exists()]
    ip=[f for f in img_f if str(f) not in done and f.exists()]
    mp=[f for f in media_f if str(f) not in done and f.exists()]
    log.info("  نصية: %d | صور: %d | صوت/فيديو: %d",len(tp),len(ip),len(mp))

    if not tp and not ip and not mp: log.info("✅ تم!"); return
    results=[]

    # ── Phase 1: Text files (fast) ──
    if tp:
        log.info(""); log.info("━━━ المرحلة 1: ملفات نصية (%d) ━━━",len(tp))
        results+=batch(tp,dp,done,rp,False,CFG.file_timeout,"📄 نصية")

    # ── Phase 2: Images ──
    if ip:
        log.info(""); log.info("━━━ المرحلة 2: صور (%d) %s ━━━",len(ip),"+ OCR" if CFG.ocr_on else "(اسم فقط)")
        if CFG.ocr_on:
            o=get_ocr(); o._load()
            if o.name and o.name!="__fail__": log.info("  OCR: %s",o.name)
            else: log.info("  ⚠ لا OCR"); CFG.ocr_on=False
        w=max(2,CFG.max_workers//4) if CFG.ocr_on else CFG.max_workers
        t=CFG.ocr_timeout if CFG.ocr_on else CFG.file_timeout
        results+=batch(ip,dp,done,rp,CFG.ocr_on,t,"🖼️ صور",workers=w)

    # ── Phase 3: Audio / Video (transcription) ──
    if mp:
        log.info(""); log.info("━━━ المرحلة 3: صوت وفيديو (%d) %s ━━━",len(mp),
                 "+ Whisper" if CFG.transcribe_on else "(اسم فقط)")
        if CFG.transcribe_on:
            try:
                import transcribe as tr
                if tr.is_available():
                    log.info("  Whisper: %s", CFG.whisper_model)
                else:
                    log.info("  ⚠ faster-whisper غير مثبت — pip install faster-whisper")
                    CFG.transcribe_on=False
            except ImportError:
                log.info("  ⚠ transcribe module not found"); CFG.transcribe_on=False
        # For media: use do_transcribe flag via a wrapper
        media_results = batch_media(mp,dp,done,rp,CFG.transcribe_on,
                                     CFG.file_timeout*3 if CFG.transcribe_on else CFG.file_timeout,
                                     "🎵 صوت/فيديو",
                                     workers=max(1,CFG.max_workers//8) if CFG.transcribe_on else CFG.max_workers)
        results += media_results

    reports(results,dp,sources[0] if len(sources)==1 else Path(destination))

    # ── Dedup phase ──
    if CFG.dedup and results:
        log.info("")
        log.info("━━━ فحص التكرارات ━━━")
        dup_groups, dup_stats = find_duplicates(results, dp)
        if dup_groups:
            save_dedup_report(dup_groups, dup_stats, dp)
            if CFG.dedup_action != "report":
                acted = apply_dedup(dup_groups, dp, CFG.dedup_action)
                log.info("  ✅ تم معالجة %d ملف مكرر", acted)
            else:
                log.info("  📋 تقرير فقط")
        else:
            log.info("  ✅ لم يتم العثور على ملفات مكررة")


def batch_media(files,dest,done,rpath,do_transcribe,timeout,desc,workers=None):
    """Batch process media files — wraps proc() with do_transcribe flag."""
    results=[]; errs=0; tos=0; w=workers or CFG.max_workers
    prog=tqdm(total=len(files),desc=desc,unit="ملف") if (HAS_TQDM and sys.stderr is not None) else None
    save_n=max(50,len(files)//10)
    total=len(files)
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs={ex.submit(proc,f,dest,False,do_transcribe):f for f in files}
        dc=0
        for fut in as_completed(futs):
            if _cancel and _cancel.is_set():
                ex.shutdown(wait=False,cancel_futures=True)
                break
            try:
                r=fut.result(timeout=timeout)
                if r:
                    results.append(r)
                    if r["error"]: errs+=1
                    done.add(r["source"])
                    if _progress_cb: _progress_cb(dc+1,total,r.get("filename",""),r.get("category",""))
            except TimeoutError:
                fp=futs[fut]; tos+=1
                results.append(mkrow(fp,fp.name,fp.suffix.lower(),0,"99_Uncategorized",0,"NONE",[],err=f"Timeout({timeout}s)"))
                done.add(str(fp))
            except Exception as e:
                fp=futs[fut]
                results.append(mkrow(fp,fp.name,fp.suffix.lower(),0,"ERROR",0,"NONE",[],err=str(e)))
                done.add(str(fp))
            dc+=1
            if prog: prog.update(1)
            elif dc%100==0: log.info("  ... %d / %d",dc,total)
            if dc%save_n==0:
                try: rpath.write_text(json.dumps(list(done),ensure_ascii=False),encoding="utf-8")
                except: pass
    if prog: prog.close()
    try: rpath.write_text(json.dumps(list(done),ensure_ascii=False),encoding="utf-8")
    except: pass
    log.info("  ✅ %d معالج | %d خطأ | %d timeout",len(results),errs,tos)
    return results

def main():
    args=sys.argv[1:]
    if not args or args[0] in("-h","--help"):
        print("""
╔════════════════════════════════════════════════════════════════╗
║  CTO Knowledge Asset Categorizer v3.2 — Fixed Classification  ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  python cto_categorize_v3.py <source> [dest] [options]        ║
║                                                                ║
║  خيارات:                                                       ║
║    --move         نقل الملفات بدل النسخ (يوفر مساحة)          ║
║    --dedup        كشف وإزالة الملفات المكررة                    ║
║    --ocr          تفعيل OCR للصور                              ║
║    --gpu          استخدام GPU (يفعّل OCR)                      ║
║    --timeout=30   حد أقصى لكل ملف (ثواني)                     ║
║    --workers=12   عمليات متوازية                                ║
║    --reset        بداية جديدة (مسح التقدم السابق)              ║
║                                                                ║
║  أمثلة:                                                        ║
║    python cto_categorize_v3.py "D:\\Files" --reset              ║
║    python cto_categorize_v3.py "D:\\Files" --move               ║
║    python cto_categorize_v3.py "D:\\Files" --move --ocr --gpu   ║
║                                                                ║
║  --move آمن: ينسخ أولاً → يتحقق → ثم يحذف المصدر              ║
║  لو توقف وأعدت التشغيل، يكمل من حيث وقف تلقائياً             ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝""")
        sys.exit(0)
    pos=[a for a in args if not a.startswith("--")]
    flags=[a for a in args if a.startswith("--")]
    global CFG; CFG=Config.from_args(flags)
    run(pos[0],pos[1] if len(pos)>1 else "./categorized_docs")

if __name__=="__main__": main()
```

### File: `i18n.py`
The content of `i18n.py` is:
```py
"""
i18n — Bilingual UI strings (English / Arabic)
"""

STRINGS = {
    "app_name":           {"en": "Smart File Categorizer", "ar": "المصنف الذكي للملفات"},
    "app_subtitle":       {"en": "Organize, categorize & discover your files", "ar": "نظّم وصنّف واكتشف ملفاتك"},
    "nav_home":           {"en": "Home",        "ar": "الرئيسية"},
    "nav_settings":       {"en": "Settings",    "ar": "الإعدادات"},
    "nav_categories":     {"en": "Categories",  "ar": "التصنيفات"},
    "nav_results":        {"en": "Results",     "ar": "النتائج"},
    "nav_log":            {"en": "Log",         "ar": "السجل"},
    "home_title":         {"en": "Categorize & Organize Your Files", "ar": "صنّف ونظّم ملفاتك"},
    "home_subtitle":      {"en": "Select source and destination, then click Start", "ar": "اختر المصدر والوجهة ثم اضغط ابدأ"},
    "source_label":       {"en": "📁 Source Folder",  "ar": "📁 المصدر"},
    "dest_label":         {"en": "📂 Destination",    "ar": "📂 الوجهة"},
    "source_ph":          {"en": "Select folder with your files...", "ar": "اختر مجلد الملفات..."},
    "dest_ph":            {"en": "Categorized output folder...", "ar": "مجلد الملفات المصنفة..."},
    "browse":             {"en": "Browse",      "ar": "استعراض"},
    "sw_move":            {"en": "Move (not copy)", "ar": "نقل (بدل النسخ)"},
    "sw_ocr":             {"en": "OCR images",  "ar": "OCR للصور"},
    "sw_reset":           {"en": "Fresh start", "ar": "بداية جديدة"},
    "sw_dedup":           {"en": "Detect duplicates", "ar": "كشف التكرارات"},
    "dedup_lbl":          {"en": "On detect:",  "ar": "عند الكشف:"},
    "dedup_report":       {"en": "Report only", "ar": "تقرير فقط"},
    "dedup_move":         {"en": "Move to _duplicates", "ar": "نقل للمكررات"},
    "dedup_delete":       {"en": "Delete permanently", "ar": "حذف نهائي"},
    "btn_start":          {"en": "▶  Start", "ar": "▶  ابدأ"},
    "btn_stop":           {"en": "⏹  Stop",  "ar": "⏹  إيقاف"},
    "ready":              {"en": "Ready to start", "ar": "جاهز للبدء"},
    "preparing":          {"en": "Preparing...", "ar": "جاري التحضير..."},
    "stopping":           {"en": "Stopping...", "ar": "جاري الإيقاف..."},
    "stopped":            {"en": "Stopped — resume later", "ar": "تم الإيقاف — يمكنك الاستكمال"},
    "done":               {"en": "Done — {n} files categorized", "ar": "انتهى — تم تصنيف {n} ملف"},
    "error":              {"en": "Error: {e}", "ar": "خطأ: {e}"},
    "settings_title":     {"en": "Settings", "ar": "الإعدادات"},
    "perf":               {"en": "⚡ Performance", "ar": "⚡ الأداء"},
    "workers":            {"en": "Parallel workers", "ar": "عمليات متوازية"},
    "timeout":            {"en": "Timeout per file (sec)", "ar": "حد أقصى لكل ملف (ثواني)"},
    "ocr_title":          {"en": "🔍 OCR", "ar": "🔍 قراءة الصور"},
    "ocr_sw":             {"en": "Enable OCR for images & scanned PDFs", "ar": "تفعيل OCR للصور والـ PDF الممسوح"},
    "gpu_sw":             {"en": "Use GPU (10x faster)", "ar": "استخدام GPU (أسرع 10x)"},
    "ocr_engines":        {"en": "Engines: EasyOCR → PaddleOCR → Tesseract", "ar": "المحركات: EasyOCR → PaddleOCR → Tesseract"},
    "cls_title":          {"en": "🎯 Classification", "ar": "🎯 التصنيف"},
    "score_lbl":          {"en": "Min classification score", "ar": "حد أدنى لدرجة التصنيف"},
    "score_hint":         {"en": "Higher = more precise, more Uncategorized", "ar": "أعلى = أدق، لكن أكثر Uncategorized"},
    "btn_save":           {"en": "💾 Save Settings", "ar": "💾 حفظ الإعدادات"},
    "role_title":         {"en": "👤 Job Role Presets", "ar": "👤 قوالب حسب الوظيفة"},
    "role_hint":          {"en": "Load categories matching your role", "ar": "حمّل تصنيفات تناسب وظيفتك"},
    "btn_load":           {"en": "Load Preset", "ar": "تحميل القالب"},
    "lang_lbl":           {"en": "Language", "ar": "اللغة"},
    "theme_lbl":          {"en": "Theme", "ar": "المظهر"},
    "cats_title":         {"en": "Categories", "ar": "التصنيفات"},
    "cats_sub":           {"en": "Enable, disable, edit or add categories", "ar": "فعّل أو عطّل أو عدّل أو أضف تصنيفات"},
    "btn_add":            {"en": "➕ Add Category", "ar": "➕ إضافة تصنيف"},
    "btn_defaults":       {"en": "🔄 Reset Defaults", "ar": "🔄 استعادة الافتراضي"},
    "personal":           {"en": "Personal", "ar": "شخصي"},
    "edit":               {"en": "Edit", "ar": "تعديل"},
    "delete":             {"en": "Delete", "ar": "حذف"},
    "edit_title":         {"en": "Edit Category", "ar": "تعديل التصنيف"},
    "new_title":          {"en": "New Category", "ar": "تصنيف جديد"},
    "cat_name":           {"en": "Category Name", "ar": "اسم التصنيف"},
    "cat_personal":       {"en": "Personal category", "ar": "تصنيف شخصي"},
    "cat_potential":      {"en": "Product Potential", "ar": "إمكانية التحويل لمنتج"},
    "cat_en_kw":          {"en": "English Keywords (keyword:weight per line)", "ar": "كلمات إنجليزية (keyword:weight لكل سطر)"},
    "cat_ar_kw":          {"en": "Arabic Keywords (كلمة:وزن per line)", "ar": "كلمات عربية (كلمة:وزن لكل سطر)"},
    "cat_fh":             {"en": "Filename Hints (comma-separated)", "ar": "تلميحات اسم الملف (بفاصلة)"},
    "cat_ph":             {"en": "Path Hints (comma-separated)", "ar": "تلميحات المسار (بفاصلة)"},
    "cat_neg":            {"en": "Negative Keywords (comma-separated)", "ar": "كلمات سلبية (بفاصلة)"},
    "save":               {"en": "Save", "ar": "حفظ"},
    "cancel":             {"en": "Cancel", "ar": "إلغاء"},
    "results_title":      {"en": "Results", "ar": "النتائج"},
    "results_empty":      {"en": "No results yet.\nClick Start on Home page.", "ar": "لم يتم تشغيل التصنيف بعد\nاضغط ابدأ في الرئيسية."},
    "total":              {"en": "Total", "ar": "إجمالي"},
    "sellable":           {"en": "Sellable ★", "ar": "قابل للبيع ★"},
    "errors_lbl":         {"en": "Errors", "ar": "أخطاء"},
    "cats_count":         {"en": "Categories", "ar": "تصنيفات"},
    "log_title":          {"en": "Activity Log", "ar": "سجل العمليات"},
    "btn_clear":          {"en": "🗑 Clear", "ar": "🗑 مسح"},
    "confirm_move":       {"en": "MOVE mode enabled!\nFiles will be moved from source.\nCannot undo. Continue?",
                           "ar": "وضع النقل مفعّل!\nالملفات ستُنقل من المصدر.\nلا يمكن التراجع. متابعة؟"},
    "confirm_yes":        {"en": "Yes — Start", "ar": "نعم — ابدأ"},
    "err_no_src":         {"en": "Select a valid source folder", "ar": "اختر مجلد مصدر صحيح"},
    "err_no_dst":         {"en": "Select a destination folder", "ar": "اختر مجلد وجهة"},
    "preset_confirm":     {"en": "Load '{r}' preset?\nReplaces current categories.", "ar": "تحميل قالب '{r}'؟\nسيستبدل التصنيفات الحالية."},
    "preset_loaded":      {"en": "Loaded {n} categories for '{r}'", "ar": "تم تحميل {n} تصنيف لـ '{r}'"},
    "confirm_del_cat":    {"en": "Delete '{n}'?", "ar": "حذف '{n}'؟"},
    "confirm_reset_cats": {"en": "Reset to defaults?\nCustom categories will be lost.", "ar": "استعادة الافتراضي؟\nالتصنيفات المخصصة ستُفقد."},
    "dup_files":          {"en": "duplicates", "ar": "ملف مكرر"},
    "dup_exact":          {"en": "exact match", "ar": "تطابق تام"},
    "dup_meta":           {"en": "metadata match", "ar": "تطابق بيانات"},
    "dup_space":          {"en": "recoverable space", "ar": "مساحة قابلة للتحرير"},
    # File types
    "ft_title":           {"en": "📎 File Types", "ar": "📎 أنواع الملفات"},
    "ft_subtitle":        {"en": "Enable or disable file types to process. Add custom extensions.", "ar": "فعّل أو عطّل أنواع الملفات. أضف امتدادات مخصصة."},
    "ft_group_all":       {"en": "Select All", "ar": "تحديد الكل"},
    "ft_group_none":      {"en": "Deselect All", "ar": "إلغاء الكل"},
    "ft_add_ext":         {"en": "+ Add Extension", "ar": "+ إضافة امتداد"},
    "ft_reset":           {"en": "↺ Reset Defaults", "ar": "↺ استعادة الافتراضي"},
    "ft_ext_label":       {"en": "Extension (e.g. .xyz)", "ar": "الامتداد (مثال: xyz.)"},
    "ft_ext_group":       {"en": "Group", "ar": "المجموعة"},
    "ft_ext_desc":        {"en": "Description", "ar": "الوصف"},
    "ft_ext_ocr":         {"en": "Needs OCR", "ar": "يحتاج OCR"},
    "ft_active":          {"en": "{n} active of {t} total", "ar": "{n} مفعّل من {t} إجمالي"},
    "ft_add_title":       {"en": "Add Custom Extension", "ar": "إضافة امتداد مخصص"},
    # Multi-source
    "src_add":            {"en": "+ Add Folder", "ar": "+ إضافة مجلد"},
    "src_empty":          {"en": "No source folders added — click '+ Add Folder'", "ar": "لم تتم إضافة مجلدات — اضغط '+ إضافة مجلد'"},
    # Transcription
    "sw_transcribe":      {"en": "Transcribe Audio/Video", "ar": "تفريغ صوت/فيديو"},
    "whisper_model_lbl":  {"en": "Model:", "ar": "النموذج:"},
    # GPU
    "gpu_title":          {"en": "🚀 GPU Acceleration", "ar": "🚀 تسريع GPU"},
    "gpu_enable":         {"en": "Enable GPU (NVIDIA CUDA)", "ar": "تفعيل GPU (NVIDIA CUDA)"},
    "gpu_hint": {
        "en": "Speeds up OCR and Audio/Video transcription 5-10x. Falls back to CPU automatically if GPU is unavailable.",
        "ar": "يسرّع OCR وتفريغ الصوت/الفيديو 5-10 أضعاف. يعمل على CPU تلقائياً في حال عدم توفر GPU."
    },
    # Save confirmation
    "save_ok_title":      {"en": "Settings Saved", "ar": "تم الحفظ"},
    "save_ok_msg":        {"en": "Settings saved successfully! ✅", "ar": "تم حفظ الإعدادات بنجاح! ✅"},
    # Support / Donate
    "support_btn":        {"en": "Support This Project", "ar": "ادعم هذا المشروع"},
    "support_title":      {"en": "Support This Project", "ar": "ادعم هذا المشروع"},
    "support_msg": {
        "en": "I put continuous effort into building this tool to organize my own files, "
              "and I decided to share it with you.\n\n"
              "If this software helped you save time and organize your work, "
              "please consider supporting its development.\n\n"
              "Your support helps me keep improving it and adding new features. 🙏",
        "ar": "قمت بعمل مجهود متواصل للخروج بهذا المنتج لتنظيم ملفاتي، "
              "وفكرت في مشاركته معك.\n\n"
              "إذا قام هذا المنتج بمساعدتك في توفير وقتك وتنظيم عملك، "
              "فلا تبخل عليّ في تقديم الدعم.\n\n"
              "دعمك يساعدني على الاستمرار في التطوير وإضافة مميزات جديدة. 🙏"
    },
    "support_choose_amount": {"en": "Choose an amount:", "ar": "اختر المبلغ:"},
    "support_custom":     {"en": "Custom", "ar": "مبلغ آخر"},
    "support_paypal_btn": {"en": "💳  Donate with PayPal", "ar": "💳  تبرع عبر PayPal"},
    "support_patreon_btn":{"en": "🎨  Monthly Support on Patreon", "ar": "🎨  دعم شهري عبر Patreon"},
    "support_github_btn": {"en": "⭐ Star on GitHub", "ar": "⭐ نجمة على GitHub"},
    "support_close":      {"en": "Maybe Later", "ar": "لاحقاً"},
    "support_banner_short": {
        "en": "Enjoying this tool? Your support keeps it free and improving!",
        "ar": "هل أعجبك البرنامج؟ دعمك يساعدني على الاستمرار في التطوير وتوفيره مجاناً!"
    },
}

_lang = "ar"
def set_lang(l): global _lang; _lang = l
def get_lang(): return _lang
def t(key, **kw):
    e = STRINGS.get(key, {})
    s = e.get(_lang, e.get("en", f"[{key}]"))
    if kw:
        try: s = s.format(**kw)
        except: pass
    return s
```

### File: `installer.iss`
The content of `installer.iss` is:
```iss
; ═══════════════════════════════════════════════════
;  Smart Document Categorizer — Inno Setup Script
;  Creates a professional setup.exe installer
; ═══════════════════════════════════════════════════

#define MyAppName "Smart Document Categorizer"
#define MyAppNameShort "SmartDocCategorizer"
#define MyAppVersion "4.0"
#define MyAppPublisher "Reda Ghareeb"
#define MyAppURL "https://github.com/redaghareeb"
#define MyAppExeName "SmartDocCategorizer.exe"

[Setup]
AppId={{B8F3A1D2-7C4E-4A9B-8D6F-2E5C1B3A4D7E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppNameShort}
DefaultGroupName={#MyAppName}
; Output setup.exe location and name
OutputDir=installer_output
OutputBaseFilename=SmartDocCategorizer_Setup_v{#MyAppVersion}
; Installer appearance
SetupIconFile=icon.ico
WizardStyle=modern
WizardSizePercent=120
; Compression — LZMA2 ultra gives best ratio
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4
; Permissions
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; Misc
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
; Size estimate (shown to user)
ExtraDiskSpaceRequired=0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; Arabic support (if Inno Setup has Arabic translation installed)
; Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startmenu"; Description: "Create Start Menu shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checked

[Files]
; Copy entire PyInstaller output directory
Source: "dist\SmartDocCategorizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; Tasks: startmenu
; Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Option to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Show installed size in Add/Remove Programs
procedure CurStepChanged(CurStep: TSetupStep);
var
  Size: Int64;
begin
  if CurStep = ssPostInstall then
  begin
    Size := 0;
    // Estimate ~200MB installed
    RegWriteDWordValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1',
      'EstimatedSize', 200000);
  end;
end;
```

### File: `README.md`
The content of `README.md` is:
```md
# Smart Document Categorizer v4.0

**Organize, classify, and discover your files — powered by AI**

Arabic-first desktop application that automatically categorizes documents, images, audio, and video files into organized folders using keyword-based content analysis with OCR and speech-to-text.

## Project Files

```
SmartDocCategorizer/
├── app.py              ← Main GUI application (CustomTkinter)
├── engine.py           ← Classification engine (keyword matching, NLP)
├── categories.py       ← Category definitions, 21 role presets, 72 file types
├── i18n.py             ← Bilingual strings (Arabic / English)
├── transcribe.py       ← Audio/Video transcription (Whisper)
├── setup_ffmpeg.py     ← Auto-download ffmpeg for Windows
├── cleanup_dist.py     ← Post-build size optimizer
├── build.bat           ← Portable build (PyInstaller --onedir)
├── build_installer.bat ← Full installer build (PyInstaller + Inno Setup)
├── installer.iss       ← Inno Setup script
├── requirements.txt    ← Python dependencies
├── BUILD_GUIDE.md      ← Developer build instructions
└── USER_MANUAL.md      ← End-user guide
```

## Quick Start (Development)

```bash
pip install -r requirements.txt
python app.py
```

## Build Windows Installer

See BUILD_GUIDE.md for complete instructions.

## Features

- 23 default categories with Arabic + English keywords
- 21 job role presets (CTO, PM, BA, Developer, PhD, AV Manager, etc.)
- 72 file types across 11 groups (dynamically configurable)
- Multi-source folders — scan multiple locations at once
- OCR for images and scanned PDFs (EasyOCR)
- Audio/Video transcription via Whisper (Arabic optimized)
- 4-layer duplicate detection (size → partial hash → full hash → metadata)
- Bilingual UI (Arabic default, English available)
- RTL support for Arabic interface
- GPU acceleration for OCR and transcription
- Move or Copy mode with resume support
- Professional Windows installer with Inno Setup

## Author

Reda Ghareeb
- PayPal: paypal.me/redaghareeb
- Patreon: patreon.com/redaghareeb
- GitHub: github.com/redaghareeb
```

### File: `requirements.txt`
The content of `requirements.txt` is:
```txt
customtkinter>=5.2.0
CTkMessagebox>=2.5
python-docx>=1.1.0
pdfplumber>=0.10.0
openpyxl>=3.1.0
python-pptx>=0.6.23
Pillow>=10.0.0
tqdm>=4.66.0

# OCR
easyocr>=1.7.0

# Alternative OCR (optional)
# paddlepaddle>=2.5.0
# paddleocr>=2.7.0

# Audio/Video transcription
faster-whisper>=1.0.0
# Also requires: ffmpeg (https://www.gyan.dev/ffmpeg/builds/)
```

### File: `setup_ffmpeg.py`
The content of `setup_ffmpeg.py` is:
```py
"""
setup_ffmpeg.py — Download and setup ffmpeg for Windows
Run once before building: python setup_ffmpeg.py

Downloads ffmpeg essentials build and extracts ffmpeg.exe
to be bundled with the application.
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_DIR = Path("ffmpeg_bin")


def download_ffmpeg():
    """Download and extract ffmpeg.exe for Windows."""

    if FFMPEG_DIR.exists() and (FFMPEG_DIR / "ffmpeg.exe").exists():
        print(f"✅ ffmpeg already exists at {FFMPEG_DIR / 'ffmpeg.exe'}")
        return True

    FFMPEG_DIR.mkdir(exist_ok=True)
    zip_path = FFMPEG_DIR / "ffmpeg.zip"

    print("📥 Downloading ffmpeg (~90MB)...")
    print(f"   URL: {FFMPEG_URL}")
    print("   This is a one-time download.")
    print()

    try:
        # Download with progress
        def _progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(downloaded / total_size * 100, 100)
                mb = downloaded / (1024*1024)
                total_mb = total_size / (1024*1024)
                sys.stdout.write(f"\r   {mb:.0f}/{total_mb:.0f} MB ({pct:.0f}%)")
                sys.stdout.flush()

        urllib.request.urlretrieve(FFMPEG_URL, str(zip_path), reporthook=_progress)
        print("\n   ✅ Download complete")

    except Exception as e:
        print(f"\n   ❌ Download failed: {e}")
        print()
        print("   Manual download:")
        print(f"   1. Go to: {FFMPEG_URL}")
        print(f"   2. Extract ffmpeg.exe to: {FFMPEG_DIR.absolute()}")
        return False

    # Extract only ffmpeg.exe (not the full package)
    print("📦 Extracting ffmpeg.exe...")
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            for member in zf.namelist():
                basename = os.path.basename(member)
                if basename in ("ffmpeg.exe", "ffprobe.exe"):
                    # Extract to ffmpeg_bin/
                    target = FFMPEG_DIR / basename
                    with zf.open(member) as src, open(str(target), 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    print(f"   ✅ {basename}")

        # Cleanup zip
        zip_path.unlink()

        if (FFMPEG_DIR / "ffmpeg.exe").exists():
            print()
            print(f"✅ ffmpeg ready at: {FFMPEG_DIR.absolute()}")
            print(f"   Size: {(FFMPEG_DIR / 'ffmpeg.exe').stat().st_size // (1024*1024)} MB")
            return True
        else:
            print("   ❌ ffmpeg.exe not found in archive")
            return False

    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        return False


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This script is for Windows only.")
        print("On Linux/Mac: sudo apt install ffmpeg  /  brew install ffmpeg")
        sys.exit(1)

    success = download_ffmpeg()
    if success:
        print()
        print("Next steps:")
        print("  1. Run: build_installer.bat")
        print("  2. ffmpeg will be bundled automatically with the app")
    else:
        print()
        print("ffmpeg download failed. You can:")
        print("  1. Download manually from https://www.gyan.dev/ffmpeg/builds/")
        print("  2. Extract ffmpeg.exe to the ffmpeg_bin/ folder")
        print("  3. Then run build_installer.bat")
```

### File: `transcribe.py`
The content of `transcribe.py` is:
```py
"""
transcribe.py — Audio/Video transcription for document categorization
Uses faster-whisper (CTranslate2) for speech-to-text with Arabic support.

Install:
    pip install faster-whisper
    # ffmpeg must be installed for video audio extraction
    # Windows: https://www.gyan.dev/ffmpeg/builds/ (add to PATH)
    # Ubuntu:  sudo apt install ffmpeg
"""

import os, sys, io, logging, subprocess, tempfile
from pathlib import Path

log = logging.getLogger("cto_v3")

# Audio/Video extensions
AUDIO_EXT = {".mp3",".wav",".m4a",".aac",".ogg",".flac",".wma",".opus"}
VIDEO_EXT = {".mp4",".mkv",".avi",".mov",".wmv",".flv",".webm",".mpg",".mpeg",".m4v",".3gp"}
MEDIA_EXT = AUDIO_EXT | VIDEO_EXT

_whisper_model = None
_whisper_available = None  # None = not checked, True/False = checked


def is_available() -> bool:
    """Check if faster-whisper is installed."""
    global _whisper_available
    if _whisper_available is None:
        try:
            import faster_whisper
            _whisper_available = True
        except ImportError:
            _whisper_available = False
    return _whisper_available


_ffmpeg_path = None  # cached path to ffmpeg executable

def _find_ffmpeg() -> str | None:
    """Find ffmpeg: bundled first, then system PATH."""
    global _ffmpeg_path
    if _ffmpeg_path is not None:
        return _ffmpeg_path

    # 1. Check bundled with app (PyInstaller or dev)
    candidates = []
    if getattr(sys, 'frozen', False):
        # PyInstaller .exe — ffmpeg in same dir or ffmpeg_bin subdir
        app_dir = Path(sys.executable).parent
        candidates.append(app_dir / "ffmpeg.exe")
        candidates.append(app_dir / "ffmpeg_bin" / "ffmpeg.exe")
    # Dev mode — look relative to script
    script_dir = Path(__file__).parent
    candidates.append(script_dir / "ffmpeg_bin" / "ffmpeg.exe")
    candidates.append(script_dir / "ffmpeg.exe")

    for c in candidates:
        if c.exists():
            _ffmpeg_path = str(c)
            log.info("  ffmpeg: %s (bundled)", _ffmpeg_path)
            return _ffmpeg_path

    # 2. Check system PATH
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        if result.returncode == 0:
            _ffmpeg_path = "ffmpeg"
            return _ffmpeg_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    log.warning("  ⚠ ffmpeg not found — video transcription disabled")
    log.warning("    Run: python setup_ffmpeg.py  (downloads automatically)")
    return None


def _check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    return _find_ffmpeg() is not None


def _get_model(model_size="medium", gpu=False):
    """Lazy-load Whisper model. Auto-falls back to CPU if GPU fails."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    try:
        from faster_whisper import WhisperModel

        device = "cuda" if gpu else "cpu"
        compute_type = "float16" if gpu else "int8"

        log.info("تحميل نموذج Whisper (%s) على %s ...", model_size, device)
        log.info("  ⏳ أول تشغيل يحمّل النموذج (قد يستغرق دقائق)")

        try:
            _whisper_model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
            log.info("  ✅ Whisper جاهز (%s, %s)", model_size, device)
        except Exception as gpu_err:
            if gpu:
                log.warning("  ⚠ GPU failed (%s) — falling back to CPU", gpu_err)
                _whisper_model = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8",
                )
                log.info("  ✅ Whisper جاهز (%s, CPU — fallback)", model_size)
            else:
                raise

        return _whisper_model

    except Exception as e:
        log.warning("فشل تحميل Whisper: %s", e)
        return None


def _extract_audio(video_path: str, max_duration: int = 300) -> str | None:
    """
    Extract audio from video using ffmpeg.
    Returns path to temporary WAV file, or None on failure.
    max_duration: limit extraction to first N seconds (default 5 min).
    """
    if not _check_ffmpeg():
        log.debug("ffmpeg not found, skipping video: %s", video_path)
        return None

    ffmpeg = _find_ffmpeg()
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()

        cmd = [
            ffmpeg, "-i", video_path,
            "-t", str(max_duration),     # limit duration
            "-vn",                        # no video
            "-acodec", "pcm_s16le",      # WAV format
            "-ar", "16000",              # 16kHz (Whisper optimal)
            "-ac", "1",                  # mono
            "-y",                        # overwrite
            tmp.name,
        ]

        result = subprocess.run(
            cmd, capture_output=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        if result.returncode == 0 and Path(tmp.name).stat().st_size > 1000:
            return tmp.name
        else:
            os.unlink(tmp.name)
            return None

    except Exception as e:
        log.debug("Audio extraction failed for %s: %s", video_path, e)
        try:
            os.unlink(tmp.name)
        except:
            pass
        return None


def transcribe_file(filepath: str, gpu=False, max_duration=300,
                    model_size="medium") -> dict:
    """
    Transcribe an audio or video file.
    Optimized for Arabic + English with auto-detection.

    Model recommendations for Arabic:
        tiny   — fastest, ~70% accuracy, good for quick scan
        base   — fast, ~80% accuracy
        small  — balanced, ~88% accuracy
        medium — recommended, ~92% accuracy (best quality/speed balance)
        large  — best quality ~96%, but slow on CPU

    Returns:
        {
            "text": str,           # full transcription
            "language": str,       # detected language code (ar, en, ...)
            "duration": float,     # audio duration in seconds
            "segments": int,       # number of segments
        }
    """
    empty = {"text": "", "language": "unknown", "duration": 0, "segments": 0}

    if not is_available():
        return empty

    ext = Path(filepath).suffix.lower()
    audio_path = filepath

    # For video files, extract audio first
    is_video = ext in VIDEO_EXT
    if is_video:
        audio_path = _extract_audio(filepath, max_duration)
        if not audio_path:
            return empty

    try:
        model = _get_model(model_size, gpu)
        if model is None:
            return empty

        # Optimal settings for Arabic transcription:
        # - beam_size=5: good balance of speed and accuracy
        # - language=None: auto-detect (handles mixed Arabic/English)
        # - vad_filter=True: skip silence (huge speedup on long files)
        # - condition_on_previous_text=True: better context for Arabic diacritics
        # - word_timestamps=False: faster, we only need full text for classification
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            language=None,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,    # Arabic speech has shorter pauses
                speech_pad_ms=200,              # pad speech segments slightly
                threshold=0.4,                  # sensitivity (lower = catches more speech)
            ),
            condition_on_previous_text=True,    # helps with Arabic context
            word_timestamps=False,              # speed: we only need text for classification
            no_speech_threshold=0.5,            # skip segments that are likely not speech
            initial_prompt="هذا ملف صوتي يحتوي على محتوى باللغة العربية أو الإنجليزية",
        )

        texts = []
        seg_count = 0
        for segment in segments:
            text = segment.text.strip()
            if text:  # skip empty segments
                texts.append(text)
            seg_count += 1
            # Safety limit: enough text for keyword classification
            if seg_count >= 300 or len(" ".join(texts)) > 15000:
                break

        full_text = " ".join(texts)

        # Detected language
        detected_lang = "unknown"
        if info:
            detected_lang = info.language
            log.debug("Whisper detected: %s (prob: %.2f) for %s",
                      info.language, info.language_probability, filepath)

        result = {
            "text": full_text,
            "language": detected_lang,
            "duration": info.duration if info else 0,
            "segments": seg_count,
        }
        return result

    except Exception as e:
        log.debug("Transcription failed for %s: %s", filepath, e)
        return empty

    finally:
        # Clean up temp audio file from video extraction
        if is_video and audio_path and audio_path != filepath:
            try:
                os.unlink(audio_path)
            except:
                pass


def transcribe_text_only(filepath: str, gpu=False, max_duration=300,
                         model_size="medium") -> str:
    """Convenience: just return the text, or empty string."""
    result = transcribe_file(filepath, gpu, max_duration, model_size)
    return result.get("text", "")
```

### File: `USER_MANUAL.md`
The content of `USER_MANUAL.md` is:
```md
# دليل المستخدم — المُصنِّف الذكي للمستندات
# User Manual — Smart Document Categorizer

الإصدار 4.0 | Version 4.0

---

## التثبيت | Installation

### الطريقة 1: المُثبِّت (مُوصى به)
1. شغّل ملف `SmartDocCategorizer_Setup_v4.0.exe`
2. اتبع خطوات التثبيت
3. شغّل التطبيق من قائمة Start أو سطح المكتب

### Method 1: Installer (Recommended)
1. Run `SmartDocCategorizer_Setup_v4.0.exe`
2. Follow the setup wizard
3. Launch from Start Menu or Desktop shortcut

### الطريقة 2: النسخة المحمولة
1. انسخ مجلد `SmartDocCategorizer` إلى أي مكان
2. شغّل `SmartDocCategorizer.exe` مباشرة

---

## الصفحة الرئيسية | Home Page

### إضافة مجلدات المصدر
- اضغط **"+ إضافة مجلد"** لإضافة مجلد أو أكثر
- يمكن إضافة مجلدات من أقراص مختلفة (مثال: D:\Work + E:\Archive)
- اضغط **✕** لحذف أي مجلد من القائمة

### اختيار مجلد الوجهة
- اضغط **"استعراض"** لاختيار مجلد النتائج
- الملفات المصنفة ستُنسخ (أو تُنقل) إلى هذا المجلد

### الخيارات السريعة

| الخيار | الوظيفة |
|---|---|
| **نقل (بدل النسخ)** | ينقل الملفات بدل نسخها — يوفر مساحة لكن لا يمكن التراجع |
| **OCR للصور** | يقرأ النص من الصور والملفات الممسوحة ضوئياً |
| **بداية جديدة** | يتجاهل التقدم السابق ويبدأ من الصفر |
| **كشف التكرارات** | يبحث عن ملفات مكررة ويعرض تقريراً |
| **تفريغ صوت/فيديو** | يحوّل الكلام في الملفات الصوتية والمرئية إلى نص |

### نموذج Whisper (للصوت والفيديو)

| النموذج | الدقة للعربي | السرعة | الاستخدام |
|---|---|---|---|
| tiny | ~70% | أسرع | فحص سريع |
| base | ~80% | سريع | ملفات كثيرة |
| **medium** | **~92%** | **متوسط** | **مُوصى به** |
| large | ~96% | بطيء | أعلى دقة |

### بدء التصنيف
1. أضف مجلد مصدر واحد على الأقل
2. اختر مجلد الوجهة
3. اضبط الخيارات حسب حاجتك
4. اضغط **▶ ابدأ**

يمكنك إيقاف التصنيف في أي وقت بالضغط على **⏹ إيقاف**
عند إعادة التشغيل، يكمل من حيث توقف (ما لم تختر "بداية جديدة").

---

## الإعدادات | Settings

### القوالب الوظيفية (21 قالب)
اختر مسماك الوظيفي لتفعيل التصنيفات المناسبة تلقائياً:

| القالب | التصنيفات |
|---|---|
| مدير تقنية (CTO) | جميع التصنيفات (23) |
| مدير مشاريع (PM) | إدارة مشاريع، تحليل أعمال، عقود... |
| مهندس بنية مؤسسية | بنية مؤسسية، تحول رقمي، حوكمة... |
| محلل أعمال | تحليل أعمال، مشاريع، استشارات... |
| مطور برمجيات | بنية تحتية، منتجات، + مستودعات كود |
| مدير تسويق | منتجات، + حملات تسويقية، تصميم |
| محاسب / مالية | مالية، عقود، + سجلات محاسبية |
| مدير موارد بشرية | موارد بشرية، عقود، + توظيف |
| معلم / مدرس | تدريب، + خطط دروس، سجلات طلاب |
| محامي / قانوني | عقود، سياسات، + قضايا قانونية |
| باحث / دكتوراه | + أبحاث علمية، تدريس أكاديمي، منح |
| مدير سمعي بصري | + أنظمة AV، مواصفات، فعاليات |
| صانع محتوى | + تخطيط محتوى، سكربتات، تحليلات |
| مبيعات / تطوير أعمال | + خط مبيعات، عروض عملاء |
| مصمم UX/UI | + أبحاث مستخدم، أصول تصميم |
| محلل / عالم بيانات | + تحليل بيانات، نماذج ذكاء اصطناعي |
| طبيب / رعاية صحية | + سجلات طبية، إدارة مستشفى |
| عقارات / إدارة أملاك | + إدارة عقارات |
| مدير عمليات | + عمليات، إجراءات تشغيل |
| استخدام عام | كتب، أطفال، وثائق شخصية |

### الأداء
- **عدد العمليات المتوازية**: 1-32 (الافتراضي 12)
- **حد أقصى لكل ملف**: 10-120 ثانية (الافتراضي 30)

### حد التصنيف
- **حد أدنى لدرجة التصنيف**: 2.0-15.0 (الافتراضي 5.0)
- رقم أعلى = دقة أكبر لكن ملفات أكثر في "غير مصنف"
- رقم أقل = تصنيف أكثر لكن احتمال أخطاء أعلى

### تسريع GPU
- التطبيق يكتشف كرت الشاشة NVIDIA تلقائياً
- فعّل GPU لتسريع OCR وتفريغ الصوت 5-10 أضعاف
- لو GPU مش موجود، يعمل على CPU تلقائياً

### أنواع الملفات (72 نوع)
فعّل أو عطّل أنواع الملفات حسب حاجتك:

| المجموعة | الأنواع | افتراضي |
|---|---|---|
| 📄 مستندات | docx, doc, rtf, txt, md, html, xml, json... | ✅ مفعّل |
| 📕 PDF | pdf | ✅ |
| 📊 جداول بيانات | xlsx, xls, csv, tsv, ods... | ✅ |
| 📽️ عروض تقديمية | pptx, ppt, odp... | ✅ |
| 📐 مخططات | vsd, vsdx, drawio, svg... | ✅ |
| 🖼️ صور (OCR) | png, jpg, tiff, bmp, webp... | ✅ |
| 💻 ملفات برمجية | py, js, java, sql, sh... | ⬜ معطّل |
| 📚 كتب إلكترونية | epub, mobi, azw3... | ⬜ |
| 📦 أرشيفات | zip, rar, 7z | ⬜ |
| 🏗️ CAD / 3D | dwg, dxf, step, stl | ⬜ |
| 🎬 صوت / فيديو | mp3, wav, mp4, mkv... | ⬜ |

يمكنك أيضاً **إضافة امتدادات مخصصة** بالضغط على "+ إضافة امتداد".

### حفظ الإعدادات
بعد تعديل الإعدادات، اضغط **💾 حفظ** — ستظهر رسالة تأكيد وسيعود للصفحة الرئيسية.

---

## صفحة التصنيفات | Categories

### التصنيفات الافتراضية (23 تصنيف)

1. البنية المؤسسية (Enterprise Architecture)
2. التحول الرقمي (Digital Transformation)
3. إدارة المشاريع (Project Management / PMO)
4. تحليل الأعمال (Business Analysis)
5. المخرجات الاستشارية (Consulting Deliverables)
6. التخطيط الاستراتيجي (Strategy & Planning)
7. تطوير المنتجات (Product Development)
8. حوكمة تقنية المعلومات (IT Governance)
9. العروض والمناقصات (Proposals & Tenders)
10. المالية والميزانيات (Finance & Budgets)
11. العقود والقانونية (Contracts & Legal)
12. الموارد البشرية (HR & People)
13. التقارير والعروض (Reports & Presentations)
14. التدريب ونقل المعرفة (Training & Knowledge)
15. محاضر الاجتماعات (Meeting Communications)
16. أنظمة التعلم (LMS / E-Learning)
17. البنية التحتية (Infrastructure & Technical)
18. السياسات والإجراءات (Policies & Procedures)
19. الكتب الشخصية (Personal Books)
20. أنشطة الأطفال (Kids Activities)
21. الوثائق الشخصية (Personal Documents)
22. القوالب القابلة لإعادة الاستخدام (Templates)
23. المخططات والرسوم (Diagrams & Visuals)

### تعديل التصنيفات
- **فعّل/عطّل** أي تصنيف بالمفتاح الجانبي
- **عدّل** أي تصنيف بالضغط على ✏️ (كلمات مفتاحية، أوزان، تلميحات)
- **أضف** تصنيف جديد بالضغط على "+ إضافة تصنيف"
- **استعد** التصنيفات الافتراضية بالضغط على "↺ استعادة"

### كيف يعمل التصنيف
1. يقرأ محتوى كل ملف (نص، OCR للصور، Whisper للصوت)
2. يبحث عن كلمات مفتاحية عربية وإنجليزية
3. يحسب درجة لكل تصنيف بناءً على عدد ووزن الكلمات المطابقة
4. ينسخ/ينقل الملف للتصنيف الأعلى درجة

### أولوية التصنيف
- التصنيفات **الشخصية** (كتب، أطفال) لها أولوية على المهنية
- يحتاج **كلمتين مفتاحيتين مختلفتين على الأقل** للتصنيف المهني
- **الكلمات السلبية** تمنع التصنيف الخاطئ (مثال: "قصة أطفال" لا تذهب لإدارة المشاريع)

---

## صفحة النتائج | Results

بعد انتهاء التصنيف، تعرض:

### ملخص
- **إجمالي**: عدد الملفات المعالجة
- **قابل للبيع ★**: ملفات ذات إمكانية تحويل لمنتج (score ≥ 8)
- **أخطاء**: ملفات لم يتم معالجتها
- **تصنيفات**: عدد التصنيفات المستخدمة

### توزيع التصنيفات
شريط تقدم لكل تصنيف يوضح عدد الملفات والنسبة المئوية.

### تقرير التكرارات (إذا مفعّل)
- عدد الملفات المكررة
- المساحة القابلة للتحرير
- تفاصيل كل مجموعة تكرار

---

## كشف التكرارات | Duplicate Detection

### مراحل الكشف (4 طبقات)

| المرحلة | الطريقة | الدقة |
|---|---|---|
| 1 | تطابق حجم الملف | فلتر أولي سريع |
| 2 | Hash جزئي (أول 8KB + آخر 8KB) | 99% |
| 3 | Hash كامل MD5 | 100% — تطابق محتوى |
| 4 | تطابق البيانات الوصفية (العنوان + المؤلف) | يكشف نُسخ مختلفة |

### خيارات عند اكتشاف التكرار

| الخيار | الوظيفة |
|---|---|
| **تقرير فقط** | يعرض تقرير CSV بدون حذف أي ملف |
| **نقل للمكررات** | ينقل النسخ المكررة لمجلد `_duplicates` (آمن) |
| **حذف نهائي** | يحذف النسخ المكررة (يوفر مساحة) |

### ملفات التقرير

بعد التصنيف، ستجد في مجلد الوجهة:
- `_categorization_report.json` — تقرير التصنيف الكامل
- `_categorization.log` — سجل العمليات
- `_PRODUCT_CANDIDATES.csv` — الملفات القابلة للتحويل لمنتج
- `_DUPLICATES_REPORT.csv` — تقرير التكرارات (إذا مفعّل)
- `_processed_files.json` — قائمة الملفات المعالجة (للاستكمال)

---

## تبديل اللغة | Language Switch

- من الشريط الجانبي، اختر **English** أو **العربية**
- التطبيق يُعيد بناء الواجهة تلقائياً باللغة الجديدة
- عند اختيار العربية، الواجهة تصبح من اليمين لليسار (RTL)
- عند اختيار الإنجليزية، الواجهة من اليسار لليمين (LTR)
- الإعداد يُحفظ تلقائياً

---

## الدعم | Support

إذا أعجبك البرنامج وساعدك في تنظيم ملفاتك، يمكنك دعم المشروع:

- **PayPal**: paypal.me/redaghareeb (تبرع مباشر بمبلغ محدد)
- **Patreon**: patreon.com/redaghareeb (دعم شهري)
- **GitHub**: github.com/redaghareeb (نجمة ومشاركة)

اضغط على ❤️ في الشريط الجانبي لتفاصيل الدعم.

---

## الأسئلة الشائعة | FAQ

### س: هل يحذف الملفات الأصلية؟
لا — الوضع الافتراضي هو **النسخ**. الملفات الأصلية تبقى في مكانها. فقط إذا فعّلت "نقل" يتم حذف الأصل بعد التأكد من نجاح النسخ.

### س: ماذا لو توقف التطبيق أثناء التصنيف؟
التطبيق يحفظ تقدمه تلقائياً. عند إعادة التشغيل، يكمل من حيث توقف.

### س: هل يدعم الملفات العربية؟
نعم — التصنيف يدعم الكلمات المفتاحية بالعربية والإنجليزية. OCR يقرأ النص العربي من الصور. Whisper يفرّغ الكلام العربي من الصوت والفيديو.

### س: كم حجم التطبيق؟
المثبّت ~80-120 MB. بعد التثبيت ~200 MB على القرص.

### س: هل يحتاج إنترنت؟
لا — يعمل بالكامل دون اتصال. فقط أول تشغيل لـ Whisper يحمّل النموذج (~1.5 GB لنموذج medium).

### س: هل يدعم GPU؟
نعم — يدعم بطاقات NVIDIA مع CUDA. فعّله من الإعدادات. لو مش موجود، يعمل على CPU تلقائياً.

---

© 2024-2025 Reda Ghareeb. All rights reserved.
```

---

Now I need to do the following:
1. 
2. 
3. 

Can you help me improve the plugin based on these requirements?
```

### File: `engine.py`
The content of `engine.py` is:
```py
"""
CTO Knowledge Asset Categorizer v3.2 — Fixed Classification Engine
===================================================================
FIXES from v3.1:
  ✔ Word-boundary matching (no more "ears" matching "ea_")
  ✔ Minimum 2 distinct keywords required to classify
  ✔ Multi-word phrases weighted higher (more specific)
  ✔ Personal categories get priority (books/kids never go to PM)
  ✔ Negative keywords block false positives
  ✔ Short docs need stronger signals
  ✔ Arabic single-word traps fixed (مشروع ≠ project management)
  ✔ Optimized 90k+ massive file discovery without UI freezing

Install:
    pip install python-docx pdfplumber openpyxl python-pptx tqdm Pillow
    pip install easyocr  # optional, for OCR

Usage:
    python cto_categorize_v3.py <source> [dest] [--ocr] [--gpu]
    python cto_categorize_v3.py "D:\\AllMyFiles"
    python cto_categorize_v3.py "D:\\AllMyFiles" --ocr --gpu
"""

import os, sys, re, csv, json, math, shutil, logging, io
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

try:
    from tqdm import tqdm; HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

import warnings
warnings.filterwarnings("ignore", message=".*Cannot set.*color.*")
warnings.filterwarnings("ignore", message=".*components specified.*")
for _ln in ("pdfminer","pdfminer.pdfpage","pdfminer.converter","pdfminer.cmapdb",
            "pdfminer.psparser","pdfminer.pdfdocument","pdfminer.pdfinterp"):
    logging.getLogger(_ln).setLevel(logging.CRITICAL)

log_fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("cto_v3"); log.setLevel(logging.INFO)
# In PyInstaller --windowed mode, sys.stderr is None — use NullHandler as fallback
if sys.stderr is not None:
    _ch = logging.StreamHandler(); _ch.setFormatter(log_fmt); log.addHandler(_ch)
else:
    log.addHandler(logging.NullHandler())

# ═══════════ CONFIG ═══════════
class Config:
    max_workers=12; max_pages_pdf=20; max_rows_excel=300
    text_sample=15000; score_thr=5.0; prod_thr=8  # raised thresholds
    min_distinct_kw=2   # minimum distinct keywords to classify
    ocr_on=True; gpu=False; file_timeout=30; ocr_timeout=60
    min_img_kb=20; max_img_mb=50; min_img_px=200; reset=False
    move_mode=False  # --move: move files instead of copy (safe: copy→verify→delete)
    dedup=False      # --dedup: detect and remove duplicate files
    dedup_action="report"  # report | delete | move_to_dupes
    transcribe_on=False  # --transcribe: transcribe audio/video files
    whisper_model="medium" # tiny|base|small|medium|large — medium is optimal for Arabic
    max_media_duration=300  # max seconds to transcribe per file
    @classmethod
    def from_args(cls, args):
        c=cls()
        for a in args:
            if a=="--ocr": c.ocr_on=True
            elif a=="--gpu": c.gpu=True; c.ocr_on=True
            elif a.startswith("--timeout="): c.file_timeout=int(a.split("=")[1]); c.ocr_timeout=c.file_timeout*2
            elif a.startswith("--workers="): c.max_workers=int(a.split("=")[1])
            elif a=="--reset": c.reset=True
            elif a=="--move": c.move_mode=True
            elif a=="--dedup": c.dedup=True
            elif a=="--transcribe": c.transcribe_on=True
        c.max_workers=int(os.environ.get("MAX_WORKERS",c.max_workers))
        if os.environ.get("OCR_ENABLED")=="1": c.ocr_on=True
        if os.environ.get("GPU","").lower()=="true": c.gpu=True; c.ocr_on=True
        return c
CFG=Config()

# ═══════════ FILE TYPES ═══════════
DOC_EXT={".docx",".doc",".rtf",".odt",".txt",".md",".html",".htm",".xml",".json"}
PDF_EXT={".pdf"}
SHT_EXT={".xlsx",".xls",".xlsm",".csv",".tsv",".ods"}
PRS_EXT={".pptx",".ppt",".odp",".key"}
DIA_EXT={".vsd",".vsdx",".vsdm",".drawio"}
IMG_EXT={".png",".jpg",".jpeg",".tiff",".tif",".bmp",".webp"}
MEDIA_EXT=set()  # populated dynamically from categories.py file types
TXT_EXTS=DOC_EXT|PDF_EXT|SHT_EXT|PRS_EXT|DIA_EXT
ALL_EXTS=TXT_EXTS|IMG_EXT|MEDIA_EXT

# ═══════════ OCR ENGINE (lazy) ═══════════
class SmartOCR:
    def __init__(self,gpu=False): self.name=None; self._r=None; self._gpu=gpu
    def _load(self):
        if self._r is not None or self.name=="__fail__": return
        try:
            import easyocr
            log.info("تحميل EasyOCR ...")
            self._r=easyocr.Reader(['ar','en'],gpu=self._gpu,verbose=False)
            self.name="easyocr"; log.info("  ✅ EasyOCR (GPU:%s)",self._gpu); return
        except: pass
        try:
            from paddleocr import PaddleOCR
            self._r=PaddleOCR(lang='ar',use_angle_cls=True,use_gpu=self._gpu,show_log=False)
            self.name="paddleocr"; log.info("  ✅ PaddleOCR"); return
        except: pass
        try:
            import pytesseract; pytesseract.get_tesseract_version()
            self.name="tesseract"; log.info("  ✅ Tesseract"); return
        except: pass
        self.name="__fail__"; log.warning("⚠ لا يوجد OCR — pip install easyocr")
    def ocr(self,img):
        self._load()
        if not self.name or self.name=="__fail__": return ""
        try:
            from PIL import ImageOps,ImageFilter,Image as PILImage
            import numpy as np
            if img.mode=="RGBA":
                bg=PILImage.new("RGB",img.size,(255,255,255)); bg.paste(img,mask=img.split()[3]); img=bg
            elif img.mode not in("L","RGB"): img=img.convert("RGB")
            w,h=img.size
            if min(w,h)<800:
                s=max(2,1000//min(w,h)); img=img.resize((w*s,h*s),PILImage.LANCZOS)
            g=img.convert("L"); g=ImageOps.autocontrast(g,cutoff=1); g=g.filter(ImageFilter.SHARPEN)
            na=np.array(g)
            if self.name=="easyocr":
                res=self._r.readtext(na,paragraph=True,min_size=10,text_threshold=0.6)
                return "\n".join(r[1] for r in res if len(r)>=2 and (len(r)<3 or r[2]>0.2))
            elif self.name=="paddleocr":
                res=self._r.ocr(na,cls=True); lines=[]
                if res and res[0]:
                    for l in res[0]:
                        if l and len(l)>=2:
                            t=l[1][0] if isinstance(l[1],(list,tuple)) else str(l[1]); lines.append(t)
                return "\n".join(lines)
            elif self.name=="tesseract":
                import pytesseract; return pytesseract.image_to_string(g,lang="ara+eng").strip()
        except Exception as e: log.debug("OCR err: %s",e)
        return ""
    def ocr_file(self,fp):
        try:
            from PIL import Image; return self.ocr(Image.open(fp))
        except: return ""

_ocr=None
def get_ocr():
    global _ocr
    if _ocr is None: _ocr=SmartOCR(gpu=CFG.gpu)
    return _ocr

# ═══════════ ARABIC NORM ═══════════
_AD=re.compile(r'[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]')
_HM=str.maketrans({'\u0622':'\u0627','\u0623':'\u0627','\u0625':'\u0627','\u0671':'\u0627','\u0624':'\u0648','\u0626':'\u064A'})
_TM=str.maketrans({'\u0629':'\u0647'}); _AM=str.maketrans({'\u0649':'\u064A'})
def norm(t):
    t=_AD.sub('',t); t=t.translate(_HM).translate(_TM).translate(_AM)
    return re.sub(r'\s+',' ',t.lower())

# ═══════════ TEXT EXTRACTION ═══════════
def _rd(fp):
    for e in("utf-8","utf-8-sig","utf-16","cp1256","iso-8859-6","cp1252","latin-1"):
        try:
            t=Path(fp).read_text(encoding=e,errors="ignore")
            if len(t.strip())>10: return t
        except: continue
    return ""

def ex_docx(fp):
    try:
        from docx import Document; d=Document(fp)
        p=[p.text for p in d.paragraphs if p.text.strip()]
        for t in d.tables:
            for row in t.rows:
                c=[c.text.strip() for c in row.cells if c.text.strip()]
                if c: p.append(" | ".join(c))
        return "\n".join(p)
    except: return _rd(fp)

# Safe stderr suppressor — handles PyInstaller --windowed where sys.stderr is None
from contextlib import contextmanager
@contextmanager
def _suppress_stderr():
    """Temporarily suppress stderr (safe when sys.stderr is None in windowed mode)."""
    old = sys.stderr
    try:
        sys.stderr = io.StringIO()
        yield
    finally:
        sys.stderr = old if old is not None else io.StringIO()

def ex_pdf(fp):
    parts=[]
    try:
        import pdfplumber
        with _suppress_stderr():
            with pdfplumber.open(fp) as pdf:
                for pg in pdf.pages[:CFG.max_pages_pdf]:
                    t=pg.extract_text()
                    if t: parts.append(t)
    except: pass
    c="\n".join(parts)
    if len(c.strip())<50: c=f"__NEEDS_OCR__ {c}"
    return c

def ex_xlsx(fp):
    try:
        from openpyxl import load_workbook; wb=load_workbook(fp,read_only=True,data_only=True)
        p=[]
        for ws in wb.worksheets:
            p.append(f"[{ws.title}]")
            for r in ws.iter_rows(max_row=CFG.max_rows_excel,values_only=True):
                v=[str(c) for c in r if c is not None]
                if v: p.append(" ".join(v))
        wb.close(); return "\n".join(p)
    except: return _rd(fp)

def ex_csv(fp):
    import csv as _c
    try:
        t=_rd(fp)
        if not t: return ""
        d="\t" if Path(fp).suffix.lower()==".tsv" else ","
        return "\n".join(" ".join(r) for i,r in enumerate(_c.reader(t.splitlines(),delimiter=d)) if i<800)
    except: return ""

def ex_pptx(fp):
    try:
        from pptx import Presentation; pr=Presentation(fp); p=[]
        for sl in pr.slides:
            for sh in sl.shapes:
                if sh.has_text_frame:
                    for pa in sh.text_frame.paragraphs:
                        if pa.text.strip(): p.append(pa.text)
                if sh.has_table:
                    for r in sh.table.rows:
                        c=[c.text.strip() for c in r.cells if c.text.strip()]
                        if c: p.append(" | ".join(c))
            if sl.has_notes_slide and sl.notes_slide.notes_text_frame:
                n=sl.notes_slide.notes_text_frame.text.strip()
                if n: p.append(n)
        return "\n".join(p)
    except: return _rd(fp)

EX={".docx":ex_docx,".doc":_rd,".rtf":_rd,".odt":_rd,".txt":_rd,".md":_rd,
    ".html":_rd,".htm":_rd,".xml":_rd,".json":_rd,".pdf":ex_pdf,
    ".xlsx":ex_xlsx,".xls":_rd,".xlsm":ex_xlsx,".csv":ex_csv,".tsv":ex_csv,
    ".ods":_rd,".pptx":ex_pptx,".ppt":_rd,".odp":_rd,".key":_rd,
    ".vsd":_rd,".vsdx":_rd,".vsdm":_rd,".drawio":_rd,
    ".png":lambda f:"__IMG__",".jpg":lambda f:"__IMG__",".jpeg":lambda f:"__IMG__",
    ".tiff":lambda f:"__IMG__",".tif":lambda f:"__IMG__",".bmp":lambda f:"__IMG__",".webp":lambda f:"__IMG__"}

def extract(fp):
    ext = Path(fp).suffix.lower()
    # Known extractor
    if ext in EX:
        return EX[ext](fp)[:CFG.text_sample]
    # Dynamic image extension (needs OCR) — mark for OCR phase
    if ext in IMG_EXT:
        return "__IMG__"
    # Audio/Video — mark for transcription phase
    if ext in MEDIA_EXT:
        return "__MEDIA__"
    # Fallback: try reading as text
    return _rd(fp)[:CFG.text_sample]

def transcribe_media(fp):
    """Transcribe audio/video file using Whisper."""
    try:
        import transcribe as tr
        if not tr.is_available():
            return ""
        return tr.transcribe_text_only(
            fp, gpu=CFG.gpu,
            max_duration=CFG.max_media_duration,
            model_size=CFG.whisper_model
        )
    except ImportError:
        return ""
    except Exception as e:
        log.debug("Transcription error for %s: %s", fp, e)
        return ""

def ocr_image(fp):
    try:
        sz=Path(fp).stat().st_size/1024
        if sz<CFG.min_img_kb or sz>CFG.max_img_mb*1024: return ""
        from PIL import Image; im=Image.open(fp); w,h=im.size
        if min(w,h)<CFG.min_img_px: im.close(); return ""
        im.close()
    except: return ""
    return get_ocr().ocr_file(fp)

def ocr_pdf(fp):
    try:
        import pdfplumber; ocr=get_ocr()
        if not ocr.name or ocr.name=="__fail__": return ""
        texts=[]
        with _suppress_stderr():
            with pdfplumber.open(fp) as pdf:
                for pg in pdf.pages[:10]:
                    t=ocr.ocr(pg.to_image(resolution=200).original)
                    if t and t.strip(): texts.append(t)
        return "\n".join(texts)
    except: return ""


# ═══════════════════════════════════════════════════════════
#  COMPLETELY REWRITTEN CLASSIFICATION ENGINE v3.2
# ═══════════════════════════════════════════════════════════
#
#  Key fixes:
#  1. Word-boundary matching (regex \b for English, spaces for Arabic)
#  2. Minimum 2 distinct keywords to assign professional category
#  3. Multi-word phrases count as stronger signals
#  4. Personal categories ALWAYS checked first and take priority
#  5. Negative keywords block false positives
#  6. Short documents need more evidence
# ═══════════════════════════════════════════════════════════

# ── Build regex patterns for word-boundary matching ──

def _build_en_pattern(phrase):
    """Build regex for English phrase with word boundaries."""
    escaped = re.escape(phrase.lower())
    return re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)

def _build_ar_pattern(phrase):
    """Build regex for Arabic phrase with word boundaries.
    Arabic doesn't use \b well, so we use space/start/end boundaries."""
    normalized = norm(phrase)
    escaped = re.escape(normalized)
    return re.compile(r'(?:^|[\s\.,;:!?\-/|()\"\'{}])'
                      + escaped +
                      r'(?:$|[\s\.,;:!?\-/|()\"\'{}])')

def _build_fn_pattern(hint):
    """Build regex for filename hint — must match as whole word/segment.
    Matches: ea_report, EA-doc, project_plan
    Does NOT match: ears, learning, bears"""
    escaped = re.escape(hint.lower())
    # Match at word boundary or separated by _ - . /
    return re.compile(r'(?:^|[_\-./\\\ ])'
                      + escaped +
                      r'(?:$|[_\-./\\\ ])', re.IGNORECASE)


# ═══════════ CATEGORY DEFINITIONS ═══════════
# Structure per category:
#   "en": {phrase: weight}     — English keywords (word-boundary matched)
#   "ar": {phrase: weight}     — Arabic keywords (normalized + boundary matched)
#   "fh": [hints]              — Filename hints (whole-word matched)
#   "ph": [hints]              — Path hints
#   "neg_en": [words]          — Negative signals (English) — if found, reduce score
#   "neg_ar": [words]          — Negative signals (Arabic)
#   "pp": str                  — Product potential
#   "personal": bool           — Is this a personal category?

# ═══════════ DYNAMIC CATEGORIES ═══════════
# Categories are loaded from categories.py (user-editable, role presets)
# Fallback to hardcoded defaults if categories.py not available

try:
    from categories import load_categories
    CATEGORIES = load_categories()
except ImportError:
    CATEGORIES = {}  # will be populated by engine's own defaults if needed

_COMPILED = {}

def compile_categories():
    """Compile regex patterns for all categories. Call after loading/changing categories."""
    global _COMPILED
    _COMPILED = {}
    for cat_name, cat_info in CATEGORIES.items():
        c = {"en": [], "ar": [], "fh": [], "ph": [], "neg": []}
        for phrase, weight in cat_info.get("en", {}).items():
            wc = len(phrase.split())
            c["en"].append((_build_en_pattern(phrase), weight, wc, phrase))
        for phrase, weight in cat_info.get("ar", {}).items():
            wc = len(phrase.split())
            c["ar"].append((_build_ar_pattern(phrase), weight, wc, phrase))
        for hint in cat_info.get("fh", []):
            c["fh"].append(_build_fn_pattern(hint))
        for hint in cat_info.get("ph", []):
            c["ph"].append(_build_fn_pattern(hint))
        for neg in cat_info.get("neg_en", []):
            c["neg"].append(_build_en_pattern(neg))
        for neg in cat_info.get("neg_ar", []):
            c["neg"].append(_build_ar_pattern(neg))
        _COMPILED[cat_name] = c

def reload_categories(new_cats=None):
    """Reload categories (called from GUI when user edits categories)."""
    global CATEGORIES
    if new_cats:
        CATEGORIES = new_cats
    else:
        try:
            from categories import load_categories
            CATEGORIES = load_categories()
        except ImportError:
            pass
    compile_categories()

# Initial compile
compile_categories()


# ═══════════ CLASSIFICATION ENGINE ═══════════

def build_ctx(fp, fn):
    return norm(" ".join(Path(fp).parts[-5:]) + " " + fn)

def classify(text, filepath, filename):
    """
    Classify a document. Returns (category, score, product_potential, matches).

    Rules:
    1. Personal categories are scored first — if ANY personal category
       scores above threshold, it wins over ALL professional categories.
    2. Professional categories need at least 2 distinct keyword matches.
    3. Negative keywords reduce score by 50%.
    4. Multi-word phrases get a 1.5x bonus (more reliable signals).
    5. Filename/path hints only add to score, they can't be the sole signal.
    """
    text_norm = norm(text)
    fn_lower = filename.lower().replace(" ", "_")
    ctx = build_ctx(filepath, filename)

    personal_best = None     # (cat, score, pp, matches)
    professional_best = None

    for cat_name, cat_info in CATEGORIES.items():
        compiled = _COMPILED[cat_name]
        is_personal = cat_info.get("personal", False)

        score = 0.0
        matched = []
        distinct_kw = set()  # track unique keywords
        hint_score = 0.0     # score from hints only

        # ── English keywords (word-boundary regex) ──
        for pattern, weight, word_count, phrase in compiled["en"]:
            matches = pattern.findall(text_norm)
            count = len(matches)
            if count > 0:
                # Multi-word bonus: 2+ word phrases are 1.5x
                multiplier = 1.5 if word_count >= 2 else 1.0
                s = weight * multiplier * (1 + math.log(count))
                score += s
                distinct_kw.add(phrase)
                matched.append((phrase, round(s, 1)))

        # ── Arabic keywords (normalized + boundary regex) ──
        for pattern, weight, word_count, phrase in compiled["ar"]:
            matches = pattern.findall(text_norm)
            count = len(matches)
            if count > 0:
                multiplier = 1.5 if word_count >= 2 else 1.0
                s = weight * multiplier * (1 + math.log(count))
                score += s
                distinct_kw.add(phrase)
                matched.append((phrase, round(s, 1)))

        # ── Filename hints (whole-word boundary) ──
        for pattern in compiled["fh"]:
            if pattern.search(fn_lower):
                hint_score += 4
                matched.append(("📄 filename", 4))

        # ── Path hints ──
        for pattern in compiled["ph"]:
            if pattern.search(ctx):
                hint_score += 3
                matched.append(("📁 path", 3))

        # ── Extension bonus for diagrams ──
        ext = Path(filename).suffix.lower()
        if cat_name == "23_Diagrams_Visuals" and ext in DIA_EXT:
            score += 6
            distinct_kw.add("__ext__")
            matched.append(("🔧 " + ext, 6))

        # ── Negative keyword penalty ──
        neg_count = 0
        for neg_pat in compiled["neg"]:
            if neg_pat.search(text_norm):
                neg_count += 1
        if neg_count > 0:
            score *= max(0.2, 1.0 - 0.3 * neg_count)  # reduce 30% per neg, min 20%

        # Add hint score (but hints alone can't classify)
        total_score = score + hint_score

        # ── Minimum diversity check for professional categories ──
        if not is_personal and len(distinct_kw) < CFG.min_distinct_kw:
            # If only hints but no content keywords, skip
            if score < CFG.score_thr:
                total_score = min(total_score, CFG.score_thr - 0.1)

        total_score = round(total_score, 2)
        matched_sorted = sorted(matched, key=lambda x: -x[1])[:6]

        entry = (cat_name, total_score, cat_info["pp"], matched_sorted)

        if is_personal:
            if personal_best is None or total_score > personal_best[1]:
                personal_best = entry
        else:
            if professional_best is None or total_score > professional_best[1]:
                professional_best = entry

    # ── Decision logic ──

    # Rule 1: If personal category scores above threshold, it ALWAYS wins
    if personal_best and personal_best[1] >= CFG.score_thr:
        return personal_best

    # Rule 2: Otherwise use professional
    if professional_best and professional_best[1] >= CFG.score_thr:
        return professional_best

    # Rule 3: Below threshold → Uncategorized
    best = max([e for e in [personal_best, professional_best] if e],
               key=lambda x: x[1], default=None)
    if best:
        return ("99_Uncategorized", best[1], "UNKNOWN", best[3])
    return ("99_Uncategorized", 0.0, "UNKNOWN", [])


# ═══════════ HELPERS ═══════════
def hsz(n):
    for u in("B","KB","MB","GB"):
        if abs(n)<1024: return f"{n:.1f} {u}"
        n/=1024
    return f"{n:.1f} TB"

def uniq(d,fn):
    t=d/fn
    if not t.exists(): return t
    s,x=Path(fn).stem,Path(fn).suffix; c=1
    while True:
        t=d/f"{s}({c}){x}"
        if not t.exists(): return t
        c+=1

def dlang(t):
    if not t: return "unknown"
    ar=len(re.findall(r'[\u0600-\u06FF]',t[:5000]))
    en=len(re.findall(r'[a-zA-Z]',t[:5000]))
    tot=ar+en
    if tot==0: return "unknown"
    r=ar/tot
    return "ar" if r>0.7 else("mixed" if r>0.2 else "en")

def mkrow(src,fn,ext,sz,cat,sc,pp,kws,dst=None,dup=False,lang="unknown",ocr=False,err=None):
    return {"source":str(src),"destination":dst,"filename":fn,"extension":ext,"size":sz,
            "category":cat,"score":sc,"product_potential":pp,"top_keywords":kws,
            "duplicate":dup,"language":lang,"ocr_used":ocr,"error":err}

# ═══════════ PROCESS FILE ═══════════
def proc(src,dest,do_ocr=False,do_transcribe=False):
    fn=src.name; ext=src.suffix.lower()
    if ext not in ALL_EXTS: return None

    # Resume safety: if file was already moved, skip gracefully
    if not src.exists():
        return None

    try:
        sz=src.stat().st_size
        if sz>200*1024*1024: return mkrow(src,fn,ext,sz,"99_Uncategorized",0,"NONE",[],err="Skipped >200MB")

        is_img=ext in IMG_EXT; is_scan=False; is_media=ext in MEDIA_EXT
        transcribed=False

        if is_img and not do_ocr: text=""
        elif is_media and not do_transcribe: text=""
        else: text=extract(str(src))

        if isinstance(text,str) and text.startswith("__NEEDS_OCR__"):
            is_scan=True; text=text.replace("__NEEDS_OCR__","").strip()
            if do_ocr:
                ot=ocr_pdf(str(src))
                if ot: text=ot
        if is_img and do_ocr and (not text or text=="__IMG__"):
            text=ocr_image(str(src))
        if text=="__IMG__": text=""

        # Media transcription
        if is_media and do_transcribe and (not text or text=="__MEDIA__"):
            text=transcribe_media(str(src))
            if text: transcribed=True
        if text=="__MEDIA__": text=""

        lang=dlang(text)
        cat,sc,pp,matches=classify(text,str(src),fn)
        cf=dest/cat; cf.mkdir(parents=True,exist_ok=True)
        df=uniq(cf,fn); dup=df.name!=fn

        # Safe transfer: copy → verify → delete source (if --move)
        shutil.copy2(src,df)

        if CFG.move_mode:
            # Verify destination exists and matches size before deleting source
            if df.exists() and df.stat().st_size == sz:
                try:
                    src.unlink()
                except Exception as e:
                    log.debug("Could not delete source %s: %s", src, e)

        return mkrow(src,fn,ext,sz,cat,sc,pp,[m[0] for m in matches],
                    dst=str(df),dup=dup,lang=lang,
                    ocr=(is_img and do_ocr)or(is_scan and do_ocr) or transcribed)
    except Exception as e:
        return mkrow(src,fn,ext,0,"ERROR",0,"NONE",[],err=str(e))

# ═══════════ BATCH PROCESSOR ═══════════
# GUI callbacks (set by app.py before calling run)
_progress_cb = None    # fn(current, total, filename, category)
_log_cb = None         # fn(message)
_cancel = None         # threading.Event — set to stop

def set_callbacks(progress_fn=None, log_fn=None, cancel_event=None):
    global _progress_cb, _log_cb, _cancel
    _progress_cb = progress_fn
    _log_cb = log_fn
    _cancel = cancel_event

def batch(files,dest,done,rpath,do_ocr,timeout,desc,workers=None):
    results=[]; errs=0; tos=0; w=workers or CFG.max_workers
    prog=tqdm(total=len(files),desc=desc,unit="ملف") if (HAS_TQDM and sys.stderr is not None) else None
    save_n=max(200,len(files)//10)
    total=len(files)
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs={ex.submit(proc,f,dest,do_ocr):f for f in files}
        dc=0
        for fut in as_completed(futs):
            # Check cancellation
            if _cancel and _cancel.is_set():
                ex.shutdown(wait=False,cancel_futures=True)
                if _log_cb: _log_cb("⚠ تم الإيقاف بواسطة المستخدم")
                break
            try:
                r=fut.result(timeout=timeout)
                if r:
                    results.append(r)
                    if r["error"]: errs+=1
                    done.add(r["source"])
                    if _progress_cb: _progress_cb(dc+1,total,r.get("filename",""),r.get("category",""))
            except TimeoutError:
                fp=futs[fut]; tos+=1
                results.append(mkrow(fp,fp.name,fp.suffix.lower(),0,"99_Uncategorized",0,"NONE",[],err=f"Timeout({timeout}s)"))
                done.add(str(fp))
            except Exception as e:
                fp=futs[fut]
                results.append(mkrow(fp,fp.name,fp.suffix.lower(),0,"ERROR",0,"NONE",[],err=str(e)))
                done.add(str(fp))
            dc+=1
            if prog: prog.update(1)
            elif dc%1000==0: log.info("  ... %d / %d",dc,total)
            if dc%save_n==0:
                try: rpath.write_text(json.dumps(list(done),ensure_ascii=False),encoding="utf-8")
                except: pass
    if prog: prog.close()
    try: rpath.write_text(json.dumps(list(done),ensure_ascii=False),encoding="utf-8")
    except: pass
    log.info("  ✅ %d معالج | %d خطأ | %d timeout",len(results),errs,tos)
    return results

# ═══════════════════════════════════════════════════════════
#  DUPLICATE DETECTION ENGINE
# ═══════════════════════════════════════════════════════════
#
#  Detection layers (fast → accurate):
#    1. Group by file size (instant filter — different size = not duplicate)
#    2. Partial hash: first 8KB + last 8KB (catches 99% of dupes fast)
#    3. Full content hash (MD5 — confirms true duplicates)
#    4. Metadata comparison (author, title, dates from doc headers)
#
#  For each duplicate group, keeps the "best" copy based on:
#    - Highest classification score
#    - Most recent modification date
#    - Shortest path (less deeply nested)
# ═══════════════════════════════════════════════════════════

import hashlib

def _file_hash_partial(filepath, chunk_size=8192):
    """Fast partial hash: first 8KB + last 8KB + size."""
    try:
        p = Path(filepath)
        sz = p.stat().st_size
        h = hashlib.md5()
        h.update(str(sz).encode())
        with open(filepath, 'rb') as f:
            h.update(f.read(chunk_size))
            if sz > chunk_size * 2:
                f.seek(-chunk_size, 2)
                h.update(f.read(chunk_size))
        return h.hexdigest()
    except Exception:
        return None

def _file_hash_full(filepath):
    """Full MD5 hash of entire file content."""
    try:
        h = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def _extract_metadata(filepath):
    """Extract document metadata (author, title, created, modified)."""
    meta = {}
    ext = Path(filepath).suffix.lower()
    try:
        if ext == '.docx':
            from docx import Document
            d = Document(filepath)
            cp = d.core_properties
            meta['title'] = cp.title or ''
            meta['author'] = cp.author or ''
            meta['created'] = str(cp.created) if cp.created else ''
            meta['modified'] = str(cp.modified) if cp.modified else ''
            meta['revision'] = str(cp.revision) if cp.revision else ''
        elif ext == '.pptx':
            from pptx import Presentation
            p = Presentation(filepath)
            cp = p.core_properties
            meta['title'] = cp.title or ''
            meta['author'] = cp.author or ''
            meta['created'] = str(cp.created) if cp.created else ''
            meta['modified'] = str(cp.modified) if cp.modified else ''
        elif ext == '.xlsx':
            from openpyxl import load_workbook
            wb = load_workbook(filepath, read_only=True)
            props = wb.properties
            meta['title'] = props.title or ''
            meta['author'] = props.creator or ''
            meta['created'] = str(props.created) if props.created else ''
            meta['modified'] = str(props.modified) if props.modified else ''
            wb.close()
        elif ext == '.pdf':
            import pdfplumber
            with _suppress_stderr():
                with pdfplumber.open(filepath) as pdf:
                    info = pdf.metadata or {}
                    meta['title'] = info.get('Title', '')
                    meta['author'] = info.get('Author', '')
                    meta['created'] = info.get('CreationDate', '')
                    meta['modified'] = info.get('ModDate', '')
                    meta['producer'] = info.get('Producer', '')
                    meta['pages'] = len(pdf.pages)
    except Exception:
        pass

    # File system metadata
    try:
        st = Path(filepath).stat()
        meta['fs_size'] = st.st_size
        meta['fs_modified'] = datetime.fromtimestamp(st.st_mtime).isoformat()
        meta['fs_created'] = datetime.fromtimestamp(st.st_ctime).isoformat()
    except Exception:
        pass

    return meta


def _pick_best_copy(group):
    """
    From a list of duplicate file dicts, pick the 'best' one to keep.
    Priority: highest classification score → most recent → shortest path.
    """
    def sort_key(item):
        score = item.get('score', 0)
        # Parse modification time
        try:
            mtime = Path(item['destination']).stat().st_mtime if item.get('destination') else 0
        except Exception:
            mtime = 0
        # Shorter path = probably less deeply nested = more accessible
        path_len = len(item.get('destination', '')) if item.get('destination') else 9999
        return (-score, -mtime, path_len)

    sorted_group = sorted(group, key=sort_key)
    return sorted_group[0]  # best


def find_duplicates(results, dest_path):
    """
    Detect duplicates among categorized files.
    Returns: (duplicates_groups, dedup_report)

    Each group: {
        'hash': str,
        'keep': dict (file row to keep),
        'remove': [dict] (file rows to remove),
        'match_type': 'exact_content' | 'same_content_diff_name' | 'metadata_match',
        'size': int,
    }
    """
    if _log_cb:
        _log_cb("🔍 بدء فحص التكرارات ...")

    # Only check successfully categorized files with valid destinations
    valid = [r for r in results if r.get('destination') and not r.get('error')
             and Path(r['destination']).exists()]

    if not valid:
        return [], {}

    # ── Phase 1: Group by size (instant filter) ──
    size_groups = defaultdict(list)
    for r in valid:
        try:
            sz = Path(r['destination']).stat().st_size
            if sz > 0:  # skip empty files
                size_groups[sz].append(r)
        except Exception:
            pass

    # Only keep groups with 2+ same-size files
    candidates = {sz: items for sz, items in size_groups.items() if len(items) >= 2}

    if _log_cb:
        total_candidates = sum(len(v) for v in candidates.values())
        _log_cb(f"  المرحلة 1: {total_candidates} ملف بأحجام متطابقة ({len(candidates)} مجموعة)")

    if not candidates:
        if _log_cb:
            _log_cb("  ✅ لم يتم العثور على ملفات مكررة")
        return [], {"total_checked": len(valid), "duplicates_found": 0}

    # ── Phase 2: Partial hash (fast — first+last 8KB) ──
    partial_groups = defaultdict(list)
    for sz, items in candidates.items():
        for r in items:
            ph = _file_hash_partial(r['destination'])
            if ph:
                partial_groups[ph].append(r)

    partial_dupes = {h: items for h, items in partial_groups.items() if len(items) >= 2}

    if _log_cb:
        _log_cb(f"  المرحلة 2: {len(partial_dupes)} مجموعة بـ partial hash متطابق")

    if not partial_dupes:
        if _log_cb:
            _log_cb("  ✅ لم يتم العثور على ملفات مكررة")
        return [], {"total_checked": len(valid), "duplicates_found": 0}

    # ── Phase 3: Full hash (confirms true duplicates) ──
    duplicate_groups = []
    total_dupes = 0

    for ph, items in partial_dupes.items():
        # Full hash each file
        full_hash_groups = defaultdict(list)
        for r in items:
            fh = _file_hash_full(r['destination'])
            if fh:
                full_hash_groups[fh].append(r)

        for fh, group in full_hash_groups.items():
            if len(group) >= 2:
                best = _pick_best_copy(group)
                removes = [r for r in group if r is not best]
                total_dupes += len(removes)

                # Determine match type
                names = set(r['filename'] for r in group)
                match_type = 'exact_content' if len(names) == 1 else 'same_content_diff_name'

                duplicate_groups.append({
                    'hash': fh,
                    'keep': best,
                    'remove': removes,
                    'match_type': match_type,
                    'size': group[0].get('size', 0),
                    'count': len(group),
                })

    # ── Phase 4: Metadata-based near-duplicates ──
    # Check files with same metadata (title+author) but different content
    # These might be different versions of the same document
    meta_groups = defaultdict(list)
    for r in valid:
        dest = r.get('destination')
        if not dest:
            continue
        ext = Path(dest).suffix.lower()
        if ext in ('.docx', '.pptx', '.xlsx', '.pdf'):
            meta = _extract_metadata(dest)
            title = (meta.get('title', '') or '').strip().lower()
            author = (meta.get('author', '') or '').strip().lower()
            if title and len(title) > 3:  # meaningful title
                key = f"{title}|{author}|{ext}"
                meta_groups[key].append({**r, '_meta': meta})

    near_dupes = []
    for key, group in meta_groups.items():
        if len(group) >= 2:
            # Check they're not already in exact duplicates
            dests = set(r['destination'] for r in group)
            already_found = False
            for dg in duplicate_groups:
                existing_dests = {dg['keep']['destination']} | {r['destination'] for r in dg['remove']}
                if dests & existing_dests:
                    already_found = True
                    break
            if not already_found:
                best = _pick_best_copy(group)
                removes = [r for r in group if r is not best]
                near_dupes.append({
                    'hash': f"meta:{key[:50]}",
                    'keep': best,
                    'remove': removes,
                    'match_type': 'metadata_match',
                    'size': group[0].get('size', 0),
                    'count': len(group),
                    'meta_key': key,
                })

    all_groups = duplicate_groups + near_dupes
    total_removable = sum(len(g['remove']) for g in all_groups)
    total_space = sum(
        sum(Path(r['destination']).stat().st_size for r in g['remove']
            if r.get('destination') and Path(r['destination']).exists())
        for g in all_groups
    )

    if _log_cb:
        _log_cb(f"  المرحلة 3: {len(duplicate_groups)} مجموعة تكرار حقيقي (content match)")
        _log_cb(f"  المرحلة 4: {len(near_dupes)} مجموعة تكرار محتمل (metadata match)")
        _log_cb(f"  📊 إجمالي: {total_removable} ملف مكرر | {hsz(total_space)} مساحة قابلة للتحرير")

    report = {
        "total_checked": len(valid),
        "exact_duplicate_groups": len(duplicate_groups),
        "near_duplicate_groups": len(near_dupes),
        "duplicates_found": total_removable,
        "space_recoverable": total_space,
        "space_recoverable_human": hsz(total_space),
    }

    return all_groups, report


def apply_dedup(duplicate_groups, dest_path, action="move_to_dupes"):
    """
    Apply dedup action to duplicate files.
    action: 'report' (do nothing), 'delete', 'move_to_dupes'
    Returns count of files acted on.
    """
    if action == "report":
        return 0

    import stat
    dupes_folder = dest_path / "_duplicates"
    acted = 0
    log.info(f"  تنفيذ إجراء التكرارات: {action}")

    for group in duplicate_groups:
        for r in group['remove']:
            fp = Path(r['destination'])
            if not fp.exists():
                continue
            try:
                if action == "delete":
                    fp.chmod(stat.S_IWRITE)  # FORCE UNLOCK Windows Read-Only
                    fp.unlink()
                    acted += 1
                elif action == "move_to_dupes":
                    dupes_folder.mkdir(parents=True, exist_ok=True)
                    match_type = group.get('match_type', 'unknown')
                    sub = dupes_folder / match_type
                    sub.mkdir(exist_ok=True)
                    target = sub / fp.name
                    if target.exists():
                        stem, suffix = fp.stem, fp.suffix
                        c = 1
                        while target.exists():
                            target = sub / f"{stem}({c}){suffix}"
                            c += 1
                    shutil.move(str(fp), str(target))
                    acted += 1
            except Exception as e:
                log.debug("Dedup action failed for %s: %s", fp, e)

    if _log_cb:
        _log_cb(f"  {'🗑️ حذف' if action=='delete' else '📦 نقل'} {acted} ملف مكرر")

    return acted


def save_dedup_report(duplicate_groups, dedup_stats, dest_path):
    """Save detailed duplicate report as CSV + JSON."""
    # CSV Report
    csv_path = dest_path / "_DUPLICATES_REPORT.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[
            "group_id", "match_type", "action", "filename",
            "category", "score", "size", "path",
            "title", "author", "modified",
        ])
        w.writeheader()
        for i, group in enumerate(duplicate_groups, 1):
            # Write the kept file
            keep = group['keep']
            meta = _extract_metadata(keep['destination']) if keep.get('destination') and Path(keep['destination']).exists() else {}
            w.writerow({
                "group_id": i,
                "match_type": group['match_type'],
                "action": "✅ KEEP",
                "filename": keep.get('filename', ''),
                "category": keep.get('category', ''),
                "score": keep.get('score', 0),
                "size": keep.get('size', 0),
                "path": keep.get('destination', ''),
                "title": meta.get('title', ''),
                "author": meta.get('author', ''),
                "modified": meta.get('fs_modified', ''),
            })
            # Write duplicates
            for r in group['remove']:
                meta_r = _extract_metadata(r['destination']) if r.get('destination') and Path(r['destination']).exists() else {}
                w.writerow({
                    "group_id": i,
                    "match_type": group['match_type'],
                    "action": "❌ DUPLICATE",
                    "filename": r.get('filename', ''),
                    "category": r.get('category', ''),
                    "score": r.get('score', 0),
                    "size": r.get('size', 0),
                    "path": r.get('destination', r.get('source', '')),
                    "title": meta_r.get('title', ''),
                    "author": meta_r.get('author', ''),
                    "modified": meta_r.get('fs_modified', ''),
                })

    # JSON Report
    json_path = dest_path / "_DUPLICATES_REPORT.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "stats": dedup_stats,
            "groups": [
                {
                    "match_type": g['match_type'],
                    "hash": g['hash'],
                    "file_count": g['count'],
                    "keep": g['keep']['destination'],
                    "remove": [r['destination'] for r in g['remove']],
                }
                for g in duplicate_groups
            ],
        }, f, indent=2, ensure_ascii=False)

    log.info("تقرير التكرارات CSV → %s", csv_path)
    log.info("تقرير التكرارات JSON → %s", json_path)


# ═══════════ REPORTS ═══════════
def reports(results,dest,src):
    stats=defaultdict(lambda:{"c":0,"s":0,"pp":"","l":defaultdict(int),"o":0})
    prods=[]
    for r in results:
        cat=r["category"]; stats[cat]["c"]+=1; stats[cat]["s"]+=r.get("size",0)
        stats[cat]["pp"]=r.get("product_potential","")
        stats[cat]["l"][r.get("language","unknown")]+=1
        if r.get("ocr_used"): stats[cat]["o"]+=1
        if r.get("product_potential") in("HIGH","VERY_HIGH") and r.get("score",0)>=CFG.prod_thr:
            prods.append(r)
    log.info(""); log.info("═"*80); log.info("  النتائج"); log.info("═"*80)
    log.info("  إجمالي: %d",len(results))
    log.info("─"*80)
    log.info("  %-38s %5s %9s %4s %4s %4s  %s","التصنيف","عدد","حجم","عر","إنج","OCR","منتج؟")
    log.info("─"*80)
    for cat in sorted(stats):
        s=stats[cat]; ar=s["l"].get("ar",0)+s["l"].get("mixed",0); en=s["l"].get("en",0)
        log.info("  %-38s %5d %9s %4d %4d %4d  %s",cat,s["c"],hsz(s["s"]),ar,en,s["o"],s.get("pp",""))
    log.info("═"*80); log.info("  ★ ملفات منتجات: %d",len(prods)); log.info("═"*80)

    rj=dest/"_categorization_report.json"
    with open(rj,"w",encoding="utf-8") as f:
        json.dump({"timestamp":datetime.now().isoformat(),"source":str(src),"total":len(results),
                   "category_summary":{c:{"count":s["c"],"size":hsz(s["s"]),"product_potential":s.get("pp","")} for c,s in sorted(stats.items())},
                   "product_candidates":len(prods),"files":results},f,indent=2,ensure_ascii=False)
    log.info("JSON → %s",rj)

    rc=dest/"_categorization_report.csv"
    with open(rc,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["filename","extension","language","ocr_used","category","score","product_potential","top_keywords","duplicate","size","source","destination","error"])
        w.writeheader()
        for r in results:
            row=dict(r); row["top_keywords"]=" | ".join(str(x) for x in row.get("top_keywords",[])); w.writerow(row)
    log.info("CSV  → %s",rc)

    if prods:
        pc=dest/"_PRODUCT_CANDIDATES.csv"
        with open(pc,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=["filename","language","category","score","product_potential","top_keywords","source"])
            w.writeheader()
            for r in sorted(prods,key=lambda x:-x["score"]):
                w.writerow({"filename":r["filename"],"language":r.get("language",""),"category":r["category"],
                           "score":r["score"],"product_potential":r["product_potential"],
                           "top_keywords":" | ".join(str(x) for x in r.get("top_keywords",[])),"source":r["source"]})
        log.info("★ منتجات → %s",pc)
    log.info(""); log.info("✅ انتهى!")
    if CFG.move_mode:
        moved = sum(1 for r in results if not r.get("error") and r.get("destination"))
        log.info("  📦 تم نقل %d ملف (المصدر تم حذفه)", moved)

# ═══════════ MAIN ═══════════
def run(source,destination):
    """
    Main pipeline. source can be a single path (str) or list of paths.
    """
    # Multi-source support
    if isinstance(source, (list, tuple)):
        sources = [Path(s).resolve() for s in source if s and Path(s).is_dir()]
    else:
        sp = Path(source).resolve()
        if not sp.is_dir():
            log.error("غير موجود: %s", sp)
            if not _progress_cb: sys.exit(1)
            return
        sources = [sp]

    if not sources:
        log.error("No valid source folders")
        return

    dp=Path(destination).resolve()
    dp.mkdir(parents=True,exist_ok=True)

    # Add file handler (avoid duplicates on repeated runs)
    log_path = dp / "_categorization.log"
    existing = [h for h in log.handlers if isinstance(h, logging.FileHandler)
                and hasattr(h, 'baseFilename') and Path(h.baseFilename).name == "_categorization.log"]
    if not existing:
        fh=logging.FileHandler(log_path, encoding="utf-8"); fh.setFormatter(log_fmt); log.addHandler(fh)

    log.info("═"*65)
    log.info("  Smart Document Categorizer v4.0")
    log.info("═"*65)
    for i, sp in enumerate(sources):
        log.info("  المصدر %d : %s", i+1, sp)
    log.info("  الوجهة   : %s",dp)
    log.info("  OCR      : %s","ON" if CFG.ocr_on else "OFF")
    log.info("  Transcribe: %s","ON (%s)" % CFG.whisper_model if CFG.transcribe_on else "OFF")
    log.info("  Mode     : %s","MOVE" if CFG.move_mode else "COPY")
    log.info("  Workers  : %d | Timeout: %ds",CFG.max_workers,CFG.file_timeout)
    log.info("═"*65)

    # Safety confirmation for --move (CLI only, skip in GUI)
    if CFG.move_mode and not _progress_cb:
        log.info("  ⚠  وضع النقل (MOVE) مفعّل!")
        try:
            confirm = input("     هل تريد المتابعة؟ (y/n): ").strip().lower()
            if confirm not in ("y", "yes", "نعم"):
                log.info("  تم الإلغاء."); return
        except (EOFError, KeyboardInterrupt):
            log.info("  تم الإلغاء."); return

    # ── Discover files from all sources ──
    log.info("جاري البحث ...")
    if _progress_cb: _progress_cb(0, 0, "جاري استكشاف الملفات المتاحة...", "")

    rp=dp/"_processed_files.json"; done=set()
    if not CFG.reset and rp.exists():
        try: done=set(json.loads(rp.read_text(encoding="utf-8"))); log.info("  سابق: %d",len(done))
        except: pass

    tp = []
    ip = []
    mp = []
    discovered_count = 0

    for sp in sources:
        for root, _, fnames in os.walk(sp):
            if _cancel and _cancel.is_set():
                log.info("تم الإلغاء أثناء البحث")
                return

            root_path = Path(root)
            for fn in fnames:
                ext = fn[fn.rfind('.'):].lower() if '.' in fn else ""
                
                if ext in ALL_EXTS:
                    full_path_str = str(root_path / fn)
                    
                    if full_path_str not in done:
                        p = root_path / fn
                        if ext in TXT_EXTS: tp.append(p)
                        elif ext in IMG_EXT: ip.append(p)
                        elif ext in MEDIA_EXT: mp.append(p)
                        
                        discovered_count += 1
                        
                        if discovered_count % 1000 == 0 and _progress_cb:
                            _progress_cb(0, 0, f"جاري البحث... ({discovered_count:,} ملف جديد)", "")

    log.info("  نصية: %d | صور: %d | صوت/فيديو: %d", len(tp), len(ip), len(mp))

    if not tp and not ip and not mp: log.info("✅ تم!"); return
    results=[]

    # ── Phase 1: Text files (fast) ──
    if tp:
        log.info(""); log.info("━━━ المرحلة 1: ملفات نصية (%d) ━━━",len(tp))
        # Cap text workers to 6 to prevent pdfplumber from crashing your PC's RAM
        w_txt = min(6, CFG.max_workers)
        results+=batch(tp,dp,done,rp,False,CFG.file_timeout,"📄 نصية", workers=w_txt)
        # Force stop if user clicked Stop
        if _cancel and _cancel.is_set(): return

    # ── Phase 2: Images ──
    if ip:
        log.info(""); log.info("━━━ المرحلة 2: صور (%d) %s ━━━",len(ip),"+ OCR" if CFG.ocr_on else "(اسم فقط)")
        if CFG.ocr_on:
            o=get_ocr(); o._load()
            if o.name and o.name!="__fail__": log.info("  OCR: %s",o.name)
            else: log.info("  ⚠ لا OCR"); CFG.ocr_on=False
        
        w = min(2, CFG.max_workers) if CFG.ocr_on else CFG.max_workers
        t=CFG.ocr_timeout if CFG.ocr_on else CFG.file_timeout
        results+=batch(ip,dp,done,rp,CFG.ocr_on,t,"🖼️ صور",workers=w)
        if _cancel and _cancel.is_set(): return

    # ── Phase 3: Audio / Video (transcription) ──
    if mp:
        log.info(""); log.info("━━━ المرحلة 3: صوت وفيديو (%d) %s ━━━",len(mp),
                 "+ Whisper" if CFG.transcribe_on else "(اسم فقط)")
        if CFG.transcribe_on:
            try:
                import transcribe as tr
                if tr.is_available():
                    log.info("  Whisper: %s", CFG.whisper_model)
                else:
                    log.info("  ⚠ faster-whisper غير مثبت — pip install faster-whisper")
                    CFG.transcribe_on=False
            except ImportError:
                log.info("  ⚠ transcribe module not found"); CFG.transcribe_on=False
        
        media_workers = 1 if CFG.transcribe_on else CFG.max_workers
        media_results = batch_media(mp,dp,done,rp,CFG.transcribe_on,
                                     CFG.file_timeout*3 if CFG.transcribe_on else CFG.file_timeout,
                                     "🎵 صوت/فيديو",
                                     workers=media_workers)
        results += media_results
        if _cancel and _cancel.is_set(): return

    reports(results,dp,sources[0] if len(sources)==1 else Path(destination))

    # ── Dedup phase ──
    if CFG.dedup and results:
        log.info("")
        log.info("━━━ فحص التكرارات ━━━")
        dup_groups, dup_stats = find_duplicates(results, dp)
        if dup_groups:
            save_dedup_report(dup_groups, dup_stats, dp)
            if CFG.dedup_action != "report":
                acted = apply_dedup(dup_groups, dp, CFG.dedup_action)
                log.info("  ✅ تم معالجة %d ملف مكرر", acted)
            else:
                log.info("  📋 تقرير فقط")
        else:
            log.info("  ✅ لم يتم العثور على ملفات مكررة")


def batch_media(files,dest,done,rpath,do_transcribe,timeout,desc,workers=None):
    """Batch process media files — wraps proc() with do_transcribe flag."""
    results=[]; errs=0; tos=0; w=workers or CFG.max_workers
    prog=tqdm(total=len(files),desc=desc,unit="ملف") if (HAS_TQDM and sys.stderr is not None) else None
    save_n=max(50,len(files)//10)
    total=len(files)
    with ThreadPoolExecutor(max_workers=w) as ex:
        futs={ex.submit(proc,f,dest,False,do_transcribe):f for f in files}
        dc=0
        for fut in as_completed(futs):
            if _cancel and _cancel.is_set():
                ex.shutdown(wait=False,cancel_futures=True)
                break
            try:
                r=fut.result(timeout=timeout)
                if r:
                    results.append(r)
                    if r["error"]: errs+=1
                    done.add(r["source"])
                    if _progress_cb: _progress_cb(dc+1,total,r.get("filename",""),r.get("category",""))
            except TimeoutError:
                fp=futs[fut]; tos+=1
                results.append(mkrow(fp,fp.name,fp.suffix.lower(),0,"99_Uncategorized",0,"NONE",[],err=f"Timeout({timeout}s)"))
                done.add(str(fp))
            except Exception as e:
                fp=futs[fut]
                results.append(mkrow(fp,fp.name,fp.suffix.lower(),0,"ERROR",0,"NONE",[],err=str(e)))
                done.add(str(fp))
            dc+=1
            if prog: prog.update(1)
            elif dc%100==0: log.info("  ... %d / %d",dc,total)
            if dc%save_n==0:
                try: rpath.write_text(json.dumps(list(done),ensure_ascii=False),encoding="utf-8")
                except: pass
    if prog: prog.close()
    try: rpath.write_text(json.dumps(list(done),ensure_ascii=False),encoding="utf-8")
    except: pass
    log.info("  ✅ %d معالج | %d خطأ | %d timeout",len(results),errs,tos)
    return results

def main():
    args=sys.argv[1:]
    if not args or args[0] in("-h","--help"):
        print("""
╔════════════════════════════════════════════════════════════════╗
║  CTO Knowledge Asset Categorizer v3.2 — Fixed Classification  ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  python cto_categorize_v3.py <source> [dest] [options]        ║
║                                                                ║
║  خيارات:                                                      ║
║    --move         نقل الملفات بدل النسخ (يوفر مساحة)          ║
║    --dedup        كشف وإزالة الملفات المكررة                    ║
║    --ocr          تفعيل OCR للصور                              ║
║    --gpu          استخدام GPU (يفعّل OCR)                      ║
║    --timeout=30   حد أقصى لكل ملف (ثواني)                     ║
║    --workers=12   عمليات متوازية                               ║
║    --reset        بداية جديدة (مسح التقدم السابق)              ║
║                                                                ║
║  أمثلة:                                                       ║
║    python cto_categorize_v3.py "D:\\Files" --reset             ║
║    python cto_categorize_v3.py "D:\\Files" --move              ║
║    python cto_categorize_v3.py "D:\\Files" --move --ocr --gpu  ║
║                                                                ║
║  --move آمن: ينسخ أولاً → يتحقق → ثم يحذف المصدر              ║
║  لو توقف وأعدت التشغيل، يكمل من حيث وقف تلقائياً             ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝""")
        sys.exit(0)
    pos=[a for a in args if not a.startswith("--")]
    flags=[a for a in args if a.startswith("--")]
    global CFG; CFG=Config.from_args(flags)
    run(pos[0],pos[1] if len(pos)>1 else "./categorized_docs")

if __name__=="__main__": main()
```

### File: `i18n.py`
The content of `i18n.py` is:
```py
"""
i18n — Bilingual UI strings (English / Arabic)
"""

STRINGS = {
    "app_name":           {"en": "Smart File Categorizer", "ar": "المصنف الذكي للملفات"},
    "app_subtitle":       {"en": "Organize, categorize & discover your files", "ar": "نظّم وصنّف واكتشف ملفاتك"},
    "nav_home":           {"en": "Home",        "ar": "الرئيسية"},
    "nav_settings":       {"en": "Settings",    "ar": "الإعدادات"},
    "nav_categories":     {"en": "Categories",  "ar": "التصنيفات"},
    "nav_results":        {"en": "Results",     "ar": "النتائج"},
    "nav_log":            {"en": "Log",         "ar": "السجل"},
    "home_title":         {"en": "Categorize & Organize Your Files", "ar": "صنّف ونظّم ملفاتك"},
    "home_subtitle":      {"en": "Select source and destination, then click Start", "ar": "اختر المصدر والوجهة ثم اضغط ابدأ"},
    "source_label":       {"en": "📁 Source Folder",  "ar": "📁 المصدر"},
    "dest_label":         {"en": "📂 Destination",    "ar": "📂 الوجهة"},
    "source_ph":          {"en": "Select folder with your files...", "ar": "اختر مجلد الملفات..."},
    "dest_ph":            {"en": "Categorized output folder...", "ar": "مجلد الملفات المصنفة..."},
    "browse":             {"en": "Browse",      "ar": "استعراض"},
    "sw_move":            {"en": "Move (not copy)", "ar": "نقل (بدل النسخ)"},
    "sw_ocr":             {"en": "OCR images",  "ar": "OCR للصور"},
    "sw_reset":           {"en": "Fresh start", "ar": "بداية جديدة"},
    "sw_dedup":           {"en": "Detect duplicates", "ar": "كشف التكرارات"},
    "dedup_lbl":          {"en": "On detect:",  "ar": "عند الكشف:"},
    "dedup_report":       {"en": "Report only", "ar": "تقرير فقط"},
    "dedup_move":         {"en": "Move to _duplicates", "ar": "نقل للمكررات"},
    "dedup_delete":       {"en": "Delete permanently", "ar": "حذف نهائي"},
    "btn_start":          {"en": "▶  Start", "ar": "▶  ابدأ"},
    "btn_stop":           {"en": "⏹  Stop",  "ar": "⏹  إيقاف"},
    "ready":              {"en": "Ready to start", "ar": "جاهز للبدء"},
    "preparing":          {"en": "Preparing...", "ar": "جاري التحضير..."},
    "stopping":           {"en": "Stopping...", "ar": "جاري الإيقاف..."},
    "stopped":            {"en": "Stopped — resume later", "ar": "تم الإيقاف — يمكنك الاستكمال"},
    "done":               {"en": "Done — {n} files categorized", "ar": "انتهى — تم تصنيف {n} ملف"},
    "error":              {"en": "Error: {e}", "ar": "خطأ: {e}"},
    "settings_title":     {"en": "Settings", "ar": "الإعدادات"},
    "perf":               {"en": "⚡ Performance", "ar": "⚡ الأداء"},
    "workers":            {"en": "Parallel workers", "ar": "عمليات متوازية"},
    "timeout":            {"en": "Timeout per file (sec)", "ar": "حد أقصى لكل ملف (ثواني)"},
    "ocr_title":          {"en": "🔍 OCR", "ar": "🔍 قراءة الصور"},
    "ocr_sw":             {"en": "Enable OCR for images & scanned PDFs", "ar": "تفعيل OCR للصور والـ PDF الممسوح"},
    "gpu_sw":             {"en": "Use GPU (10x faster)", "ar": "استخدام GPU (أسرع 10x)"},
    "ocr_engines":        {"en": "Engines: EasyOCR → PaddleOCR → Tesseract", "ar": "المحركات: EasyOCR → PaddleOCR → Tesseract"},
    "cls_title":          {"en": "🎯 Classification", "ar": "🎯 التصنيف"},
    "score_lbl":          {"en": "Min classification score", "ar": "حد أدنى لدرجة التصنيف"},
    "score_hint":         {"en": "Higher = more precise, more Uncategorized", "ar": "أعلى = أدق، لكن أكثر Uncategorized"},
    "btn_save":           {"en": "💾 Save Settings", "ar": "💾 حفظ الإعدادات"},
    "role_title":         {"en": "👤 Job Role Presets", "ar": "👤 قوالب حسب الوظيفة"},
    "role_hint":          {"en": "Load categories matching your role", "ar": "حمّل تصنيفات تناسب وظيفتك"},
    "btn_load":           {"en": "Load Preset", "ar": "تحميل القالب"},
    "lang_lbl":           {"en": "Language", "ar": "اللغة"},
    "theme_lbl":          {"en": "Theme", "ar": "المظهر"},
    "cats_title":         {"en": "Categories", "ar": "التصنيفات"},
    "cats_sub":           {"en": "Enable, disable, edit or add categories", "ar": "فعّل أو عطّل أو عدّل أو أضف تصنيفات"},
    "btn_add":            {"en": "➕ Add Category", "ar": "➕ إضافة تصنيف"},
    "btn_defaults":       {"en": "🔄 Reset Defaults", "ar": "🔄 استعادة الافتراضي"},
    "personal":           {"en": "Personal", "ar": "شخصي"},
    "edit":               {"en": "Edit", "ar": "تعديل"},
    "delete":             {"en": "Delete", "ar": "حذف"},
    "edit_title":         {"en": "Edit Category", "ar": "تعديل التصنيف"},
    "new_title":          {"en": "New Category", "ar": "تصنيف جديد"},
    "cat_name":           {"en": "Category Name", "ar": "اسم التصنيف"},
    "cat_personal":       {"en": "Personal category", "ar": "تصنيف شخصي"},
    "cat_potential":      {"en": "Product Potential", "ar": "إمكانية التحويل لمنتج"},
    "cat_en_kw":          {"en": "English Keywords (keyword:weight per line)", "ar": "كلمات إنجليزية (keyword:weight لكل سطر)"},
    "cat_ar_kw":          {"en": "Arabic Keywords (كلمة:وزن per line)", "ar": "كلمات عربية (كلمة:وزن لكل سطر)"},
    "cat_fh":             {"en": "Filename Hints (comma-separated)", "ar": "تلميحات اسم الملف (بفاصلة)"},
    "cat_ph":             {"en": "Path Hints (comma-separated)", "ar": "تلميحات المسار (بفاصلة)"},
    "cat_neg":            {"en": "Negative Keywords (comma-separated)", "ar": "كلمات سلبية (بفاصلة)"},
    "save":               {"en": "Save", "ar": "حفظ"},
    "cancel":             {"en": "Cancel", "ar": "إلغاء"},
    "results_title":      {"en": "Results", "ar": "النتائج"},
    "results_empty":      {"en": "No results yet.\nClick Start on Home page.", "ar": "لم يتم تشغيل التصنيف بعد\nاضغط ابدأ في الرئيسية."},
    "total":              {"en": "Total", "ar": "إجمالي"},
    "sellable":           {"en": "Sellable ★", "ar": "قابل للبيع ★"},
    "errors_lbl":         {"en": "Errors", "ar": "أخطاء"},
    "cats_count":         {"en": "Categories", "ar": "تصنيفات"},
    "log_title":          {"en": "Activity Log", "ar": "سجل العمليات"},
    "btn_clear":          {"en": "🗑 Clear", "ar": "🗑 مسح"},
    "confirm_move":       {"en": "MOVE mode enabled!\nFiles will be moved from source.\nCannot undo. Continue?",
                           "ar": "وضع النقل مفعّل!\nالملفات ستُنقل من المصدر.\nلا يمكن التراجع. متابعة؟"},
    "confirm_yes":        {"en": "Yes — Start", "ar": "نعم — ابدأ"},
    "err_no_src":         {"en": "Select a valid source folder", "ar": "اختر مجلد مصدر صحيح"},
    "err_no_dst":         {"en": "Select a destination folder", "ar": "اختر مجلد وجهة"},
    "preset_confirm":     {"en": "Load '{r}' preset?\nReplaces current categories.", "ar": "تحميل قالب '{r}'؟\nسيستبدل التصنيفات الحالية."},
    "preset_loaded":      {"en": "Loaded {n} categories for '{r}'", "ar": "تم تحميل {n} تصنيف لـ '{r}'"},
    "confirm_del_cat":    {"en": "Delete '{n}'?", "ar": "حذف '{n}'؟"},
    "confirm_reset_cats": {"en": "Reset to defaults?\nCustom categories will be lost.", "ar": "استعادة الافتراضي؟\nالتصنيفات المخصصة ستُفقد."},
    "dup_files":          {"en": "duplicates", "ar": "ملف مكرر"},
    "dup_exact":          {"en": "exact match", "ar": "تطابق تام"},
    "dup_meta":           {"en": "metadata match", "ar": "تطابق بيانات"},
    "dup_space":          {"en": "recoverable space", "ar": "مساحة قابلة للتحرير"},
    # File types
    "ft_title":           {"en": "📎 File Types", "ar": "📎 أنواع الملفات"},
    "ft_subtitle":        {"en": "Enable or disable file types to process. Add custom extensions.", "ar": "فعّل أو عطّل أنواع الملفات. أضف امتدادات مخصصة."},
    "ft_group_all":       {"en": "Select All", "ar": "تحديد الكل"},
    "ft_group_none":      {"en": "Deselect All", "ar": "إلغاء الكل"},
    "ft_add_ext":         {"en": "+ Add Extension", "ar": "+ إضافة امتداد"},
    "ft_reset":           {"en": "↺ Reset Defaults", "ar": "↺ استعادة الافتراضي"},
    "ft_ext_label":       {"en": "Extension (e.g. .xyz)", "ar": "الامتداد (مثال: xyz.)"},
    "ft_ext_group":       {"en": "Group", "ar": "المجموعة"},
    "ft_ext_desc":        {"en": "Description", "ar": "الوصف"},
    "ft_ext_ocr":         {"en": "Needs OCR", "ar": "يحتاج OCR"},
    "ft_active":          {"en": "{n} active of {t} total", "ar": "{n} مفعّل من {t} إجمالي"},
    "ft_add_title":       {"en": "Add Custom Extension", "ar": "إضافة امتداد مخصص"},
    # Multi-source
    "src_add":            {"en": "+ Add Folder", "ar": "+ إضافة مجلد"},
    "src_empty":          {"en": "No source folders added — click '+ Add Folder'", "ar": "لم تتم إضافة مجلدات — اضغط '+ إضافة مجلد'"},
    # Transcription
    "sw_transcribe":      {"en": "Transcribe Audio/Video", "ar": "تفريغ صوت/فيديو"},
    "whisper_model_lbl":  {"en": "Model:", "ar": "النموذج:"},
    # GPU
    "gpu_title":          {"en": "🚀 GPU Acceleration", "ar": "🚀 تسريع GPU"},
    "gpu_enable":         {"en": "Enable GPU (NVIDIA CUDA)", "ar": "تفعيل GPU (NVIDIA CUDA)"},
    "gpu_hint": {
        "en": "Speeds up OCR and Audio/Video transcription 5-10x. Falls back to CPU automatically if GPU is unavailable.",
        "ar": "يسرّع OCR وتفريغ الصوت/الفيديو 5-10 أضعاف. يعمل على CPU تلقائياً في حال عدم توفر GPU."
    },
    # Save confirmation
    "save_ok_title":      {"en": "Settings Saved", "ar": "تم الحفظ"},
    "save_ok_msg":        {"en": "Settings saved successfully! ✅", "ar": "تم حفظ الإعدادات بنجاح! ✅"},
    # Support / Donate
    "support_btn":        {"en": "Support This Project", "ar": "ادعم هذا المشروع"},
    "support_title":      {"en": "Support This Project", "ar": "ادعم هذا المشروع"},
    "support_msg": {
        "en": "I put continuous effort into building this tool to organize my own files, "
              "and I decided to share it with you.\n\n"
              "If this software helped you save time and organize your work, "
              "please consider supporting its development.\n\n"
              "Your support helps me keep improving it and adding new features. 🙏",
        "ar": "قمت بعمل مجهود متواصل للخروج بهذا المنتج لتنظيم ملفاتي، "
              "وفكرت في مشاركته معك.\n\n"
              "إذا قام هذا المنتج بمساعدتك في توفير وقتك وتنظيم عملك، "
              "فلا تبخل عليّ في تقديم الدعم.\n\n"
              "دعمك يساعدني على الاستمرار في التطوير وإضافة مميزات جديدة. 🙏"
    },
    "support_choose_amount": {"en": "Choose an amount:", "ar": "اختر المبلغ:"},
    "support_custom":     {"en": "Custom", "ar": "مبلغ آخر"},
    "support_paypal_btn": {"en": "💳  Donate with PayPal", "ar": "💳  تبرع عبر PayPal"},
    "support_patreon_btn":{"en": "🎨  Monthly Support on Patreon", "ar": "🎨  دعم شهري عبر Patreon"},
    "support_github_btn": {"en": "⭐ Star on GitHub", "ar": "⭐ نجمة على GitHub"},
    "support_close":      {"en": "Maybe Later", "ar": "لاحقاً"},
    "support_banner_short": {
        "en": "Enjoying this tool? Your support keeps it free and improving!",
        "ar": "هل أعجبك البرنامج؟ دعمك يساعدني على الاستمرار في التطوير وتوفيره مجاناً!"
    },
    "ffmpeg_path_lbl":  {"en": "FFmpeg Path", "ar": "مسار FFmpeg"},
    "ffmpeg_hint":      {"en": "Optional: Path to ffmpeg.exe. Leave empty to auto-detect.", "ar": "اختياري: مسار ffmpeg.exe. اتركه فارغاً للاكتشاف التلقائي."},
    "about_btn":        {"en": "About", "ar": "عن البرنامج"},
    "about_title":      {"en": "About Smart File Categorizer", "ar": "عن المصنف الذكي للملفات"},
    "about_desc":       {"en": "Smart File Categorizer (SFC) is an AI-powered desktop application designed to organize your digital workspace by automatically analyzing and categorizing documents, images, and media files.", 
                         "ar": "المصنف الذكي للملفات (SFC) هو تطبيق مكتبي مدعوم بالذكاء الاصطناعي مصمم لتنظيم مساحة عملك الرقمية من خلال تحليل وتصنيف المستندات والصور وملفات الوسائط تلقائياً."},
    "support_email_lbl":{"en": "For support or suggestions, please email:", "ar": "للدعم الفني أو الاقتراحات، يرجى المراسلة على:"},
    "email_note":       {"en": "(Please ensure the subject line starts with SFC-)", "ar": "(يرجى التأكد من أن عنوان الرسالة يبدأ بـ SFC-)"},
}

_lang = "en"
def set_lang(l): global _lang; _lang = l
def get_lang(): return _lang
def t(key, **kw):
    e = STRINGS.get(key, {})
    s = e.get(_lang, e.get("en", f"[{key}]"))
    if kw:
        try: s = s.format(**kw)
        except: pass
    return s
```

### File: `installer.iss`
The content of `installer.iss` is:
```iss
; ===================================================
;  Smart Document Categorizer - Inno Setup Script
;  Creates a professional setup.exe installer
; ===================================================

#define MyAppName "Smart Document Categorizer"
#define MyAppNameShort "SmartDocCategorizer"
#define MyAppVersion "1.0"
#define MyAppPublisher "Reda Ghareeb"
#define MyAppURL "https://github.com/redaghareeb"
#define MyAppExeName "SmartDocCategorizer.exe"

[Setup]
AppId={{B8F3A1D2-7C4E-4A9B-8D6F-2E5C1B3A4D7E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppNameShort}
DefaultGroupName={#MyAppName}
; Output setup.exe location and name
OutputDir=installer_output
OutputBaseFilename=SmartDocCategorizer_Setup_v{#MyAppVersion}
; Installer appearance
SetupIconFile=icon.ico
WizardStyle=modern
WizardSizePercent=120

; FIX: Reduced compression level to prevent 32-bit Out of Memory crashes
Compression=lzma2/normal
SolidCompression=yes
LZMANumBlockThreads=2

; Permissions
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; Misc
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
; Size estimate
ExtraDiskSpaceRequired=0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startmenu"; Description: "Create Start Menu shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\SmartDocCategorizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  Size: Int64;
begin
  if CurStep = ssPostInstall then
  begin
    Size := 0;
    RegWriteDWordValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1',
      'EstimatedSize', 3000000);
  end;
end;
```

### File: `README.md`
The content of `README.md` is:
```md
# Smart Document Categorizer v4.0

**Organize, classify, and discover your files — powered by AI**

Arabic-first desktop application that automatically categorizes documents, images, audio, and video files into organized folders using keyword-based content analysis with OCR and speech-to-text.

## Project Files

```
SmartDocCategorizer/
├── app.py              ← Main GUI application (CustomTkinter)
├── engine.py           ← Classification engine (keyword matching, NLP)
├── categories.py       ← Category definitions, 21 role presets, 72 file types
├── i18n.py             ← Bilingual strings (Arabic / English)
├── transcribe.py       ← Audio/Video transcription (Whisper)
├── setup_ffmpeg.py     ← Auto-download ffmpeg for Windows
├── cleanup_dist.py     ← Post-build size optimizer
├── build.bat           ← Portable build (PyInstaller --onedir)
├── build_installer.bat ← Full installer build (PyInstaller + Inno Setup)
├── installer.iss       ← Inno Setup script
├── requirements.txt    ← Python dependencies
├── BUILD_GUIDE.md      ← Developer build instructions
└── USER_MANUAL.md      ← End-user guide
```

## Quick Start (Development)

```bash
pip install -r requirements.txt
python app.py
```

## Build Windows Installer

See BUILD_GUIDE.md for complete instructions.

## Features

- 23 default categories with Arabic + English keywords
- 21 job role presets (CTO, PM, BA, Developer, PhD, AV Manager, etc.)
- 72 file types across 11 groups (dynamically configurable)
- Multi-source folders — scan multiple locations at once
- OCR for images and scanned PDFs (EasyOCR)
- Audio/Video transcription via Whisper (Arabic optimized)
- 4-layer duplicate detection (size → partial hash → full hash → metadata)
- Bilingual UI (Arabic default, English available)
- RTL support for Arabic interface
- GPU acceleration for OCR and transcription
- Move or Copy mode with resume support
- Professional Windows installer with Inno Setup

## Author

Reda Ghareeb
- PayPal: paypal.me/redaghareeb
- Patreon: patreon.com/redaghareeb
- GitHub: github.com/redaghareeb
```

### File: `requirements.txt`
The content of `requirements.txt` is:
```txt
customtkinter>=5.2.0
CTkMessagebox>=2.5
python-docx>=1.1.0
pdfplumber>=0.10.0
openpyxl>=3.1.0
python-pptx>=0.6.23
Pillow>=10.0.0
tqdm>=4.66.0

# OCR
easyocr>=1.7.0

# Alternative OCR (optional)
# paddlepaddle>=2.5.0
# paddleocr>=2.7.0

# Audio/Video transcription
openai-whisper>=20231117
# Also requires: ffmpeg (https://www.gyan.dev/ffmpeg/builds/)
```

### File: `setup_ffmpeg.py`
The content of `setup_ffmpeg.py` is:
```py
"""
setup_ffmpeg.py — Download and setup ffmpeg for Windows
Run once before building: python setup_ffmpeg.py

Downloads ffmpeg essentials build and extracts ffmpeg.exe
to be bundled with the application.
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_DIR = Path("ffmpeg_bin")


def download_ffmpeg():
    """Download and extract ffmpeg.exe for Windows."""

    if FFMPEG_DIR.exists() and (FFMPEG_DIR / "ffmpeg.exe").exists():
        print(f"✅ ffmpeg already exists at {FFMPEG_DIR / 'ffmpeg.exe'}")
        return True

    FFMPEG_DIR.mkdir(exist_ok=True)
    zip_path = FFMPEG_DIR / "ffmpeg.zip"

    print("📥 Downloading ffmpeg (~90MB)...")
    print(f"   URL: {FFMPEG_URL}")
    print("   This is a one-time download.")
    print()

    try:
        # Download with progress
        def _progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(downloaded / total_size * 100, 100)
                mb = downloaded / (1024*1024)
                total_mb = total_size / (1024*1024)
                sys.stdout.write(f"\r   {mb:.0f}/{total_mb:.0f} MB ({pct:.0f}%)")
                sys.stdout.flush()

        urllib.request.urlretrieve(FFMPEG_URL, str(zip_path), reporthook=_progress)
        print("\n   ✅ Download complete")

    except Exception as e:
        print(f"\n   ❌ Download failed: {e}")
        print()
        print("   Manual download:")
        print(f"   1. Go to: {FFMPEG_URL}")
        print(f"   2. Extract ffmpeg.exe to: {FFMPEG_DIR.absolute()}")
        return False

    # Extract only ffmpeg.exe (not the full package)
    print("📦 Extracting ffmpeg.exe...")
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            for member in zf.namelist():
                basename = os.path.basename(member)
                if basename in ("ffmpeg.exe", "ffprobe.exe"):
                    # Extract to ffmpeg_bin/
                    target = FFMPEG_DIR / basename
                    with zf.open(member) as src, open(str(target), 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    print(f"   ✅ {basename}")

        # Cleanup zip
        zip_path.unlink()

        if (FFMPEG_DIR / "ffmpeg.exe").exists():
            print()
            print(f"✅ ffmpeg ready at: {FFMPEG_DIR.absolute()}")
            print(f"   Size: {(FFMPEG_DIR / 'ffmpeg.exe').stat().st_size // (1024*1024)} MB")
            return True
        else:
            print("   ❌ ffmpeg.exe not found in archive")
            return False

    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        return False


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This script is for Windows only.")
        print("On Linux/Mac: sudo apt install ffmpeg  /  brew install ffmpeg")
        sys.exit(1)

    success = download_ffmpeg()
    if success:
        print()
        print("Next steps:")
        print("  1. Run: build_installer.bat")
        print("  2. ffmpeg will be bundled automatically with the app")
    else:
        print()
        print("ffmpeg download failed. You can:")
        print("  1. Download manually from https://www.gyan.dev/ffmpeg/builds/")
        print("  2. Extract ffmpeg.exe to the ffmpeg_bin/ folder")
        print("  3. Then run build_installer.bat")
```

### File: `SmartDocCategorizer.spec`
The content of `SmartDocCategorizer.spec` is:
```spec
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('icon.ico', '.'), ('engine.py', '.'), ('i18n.py', '.'), ('categories.py', '.'), ('transcribe.py', '.'), ('ffmpeg_bin\\ffmpeg.exe', '.')]
binaries = []
hiddenimports = ['customtkinter', 'CTkMessagebox', 'docx', 'pdfplumber', 'openpyxl', 'pptx', 'PIL', 'hashlib']
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'numpy.tests', 'setuptools', 'pip', 'pytest', 'unittest', 'tkinter.test'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmartDocCategorizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SmartDocCategorizer',
)
```

### File: `transcribe.py`
The content of `transcribe.py` is:
```py
"""
transcribe.py — Audio/Video transcription for document categorization
Uses official OpenAI Whisper (PyTorch) for ultimate stability.
"""

import os, sys, io, logging, subprocess, tempfile
from pathlib import Path

log = logging.getLogger("cto_v3")

# Audio/Video extensions
AUDIO_EXT = {".mp3",".wav",".m4a",".aac",".ogg",".flac",".wma",".opus"}
VIDEO_EXT = {".mp4",".mkv",".avi",".mov",".wmv",".flv",".webm",".mpg",".mpeg",".m4v",".3gp"}
MEDIA_EXT = AUDIO_EXT | VIDEO_EXT

_whisper_model = None
_whisper_available = None  # None = not checked, True/False = checked
_custom_ffmpeg_path = None # Store the user's custom path

def set_ffmpeg_path(path: str):
    """Allow the engine to inject a custom ffmpeg.exe path."""
    global _custom_ffmpeg_path
    if path and Path(path).is_file():
        _custom_ffmpeg_path = path

def is_available() -> bool:
    """Check if official openai-whisper is installed."""
    global _whisper_available
    if _whisper_available is None:
        try:
            import whisper
            _whisper_available = True
        except ImportError:
            _whisper_available = False
    return _whisper_available

_ffmpeg_path = None  # cached path to ffmpeg executable

def _find_ffmpeg() -> str | None:
    """Find ffmpeg: custom path first, then bundled, then system PATH."""
    global _ffmpeg_path, _custom_ffmpeg_path
    
    if _custom_ffmpeg_path and Path(_custom_ffmpeg_path).exists():
        return _custom_ffmpeg_path

    if _ffmpeg_path is not None:
        return _ffmpeg_path

    candidates = []
    if getattr(sys, 'frozen', False):
        app_dir = Path(sys.executable).parent
        candidates.append(app_dir / "ffmpeg.exe")
        candidates.append(app_dir / "ffmpeg_bin" / "ffmpeg.exe")
        candidates.append(app_dir / "_internal" / "ffmpeg.exe")
    
    script_dir = Path(__file__).parent
    candidates.append(script_dir / "ffmpeg_bin" / "ffmpeg.exe")
    candidates.append(script_dir / "ffmpeg.exe")

    for c in candidates:
        if c.exists():
            _ffmpeg_path = str(c)
            log.info("  ffmpeg: %s (bundled)", _ffmpeg_path)
            return _ffmpeg_path

    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        if result.returncode == 0:
            _ffmpeg_path = "ffmpeg"
            return _ffmpeg_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    log.warning("  ⚠ ffmpeg not found — video transcription disabled")
    return None

def _check_ffmpeg() -> bool:
    return _find_ffmpeg() is not None

def _get_model(model_size="medium", gpu=False):
    """Lazy-load Official Whisper model."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    try:
        import whisper
        import torch

        # Use PyTorch device logic (same as your OCR, guaranteeing stability)
        device = "cuda" if gpu and torch.cuda.is_available() else "cpu"

        log.info("تحميل نموذج Whisper الرسمي (%s) على %s ...", model_size, device)
        log.info("  ⏳ يرجى الانتظار، جاري إعداد النموذج...")

        # Load the official model
        _whisper_model = whisper.load_model(model_size, device=device)
        
        log.info("  ✅ Whisper جاهز (%s, %s)", model_size, device)
        return _whisper_model

    except Exception as e:
        log.warning("فشل تحميل Whisper: %s", e)
        return None

def _extract_audio(video_path: str, max_duration: int = 300) -> str | None:
    """Extract audio from video using ffmpeg."""
    if not _check_ffmpeg():
        return None

    ffmpeg = _find_ffmpeg()
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()

        cmd = [
            ffmpeg, "-i", video_path,
            "-t", str(max_duration),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            tmp.name,
        ]

        result = subprocess.run(
            cmd, capture_output=True, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        if result.returncode == 0 and Path(tmp.name).stat().st_size > 1000:
            return tmp.name
        else:
            os.unlink(tmp.name)
            return None
    except Exception as e:
        try: os.unlink(tmp.name)
        except: pass
        return None

def transcribe_file(filepath: str, gpu=False, max_duration=300, model_size="medium") -> dict:
    """Transcribe using Official OpenAI Whisper."""
    empty = {"text": "", "language": "unknown", "duration": 0, "segments": 0}

    if not is_available():
        return empty

    ext = Path(filepath).suffix.lower()
    audio_path = filepath
    is_video = ext in VIDEO_EXT
    
    if is_video:
        audio_path = _extract_audio(filepath, max_duration)
        if not audio_path:
            return empty

    try:
        model = _get_model(model_size, gpu)
        if model is None:
            return empty

        # Official Whisper transcription call
        # FP16 is disabled on CPU to prevent PyTorch warnings/errors
        import torch
        fp16_enabled = True if gpu and torch.cuda.is_available() else False

        result = model.transcribe(
            audio_path,
            fp16=fp16_enabled,
            condition_on_previous_text=True,
            initial_prompt="هذا ملف صوتي يحتوي على محتوى باللغة العربية أو الإنجليزية"
        )

        # The official library returns the full text directly!
        full_text = result.get("text", "").strip()
        detected_lang = result.get("language", "unknown")
        
        # Simple safety cutoff for massive texts
        if len(full_text) > 15000:
            full_text = full_text[:15000]

        return {
            "text": full_text,
            "language": detected_lang,
            "duration": 0, # Official simple transcribe doesn't return easy duration
            "segments": len(result.get("segments", [])),
        }

    except Exception as e:
        log.debug("Transcription failed for %s: %s", filepath, e)
        return empty

    finally:
        if is_video and audio_path and audio_path != filepath:
            try: os.unlink(audio_path)
            except: pass

def transcribe_text_only(filepath: str, gpu=False, max_duration=300, model_size="medium") -> str:
    """Convenience: just return the text, or empty string."""
    result = transcribe_file(filepath, gpu, max_duration, model_size)
    return result.get("text", "")
```

### File: `USER_MANUAL.md`
The content of `USER_MANUAL.md` is:
```md
# دليل المستخدم — المُصنِّف الذكي للمستندات
# User Manual — Smart Document Categorizer

الإصدار 4.0 | Version 4.0

---

## التثبيت | Installation

### الطريقة 1: المُثبِّت (مُوصى به)
1. شغّل ملف `SmartDocCategorizer_Setup_v4.0.exe`
2. اتبع خطوات التثبيت
3. شغّل التطبيق من قائمة Start أو سطح المكتب

### Method 1: Installer (Recommended)
1. Run `SmartDocCategorizer_Setup_v4.0.exe`
2. Follow the setup wizard
3. Launch from Start Menu or Desktop shortcut

### الطريقة 2: النسخة المحمولة
1. انسخ مجلد `SmartDocCategorizer` إلى أي مكان
2. شغّل `SmartDocCategorizer.exe` مباشرة

---

## الصفحة الرئيسية | Home Page

### إضافة مجلدات المصدر
- اضغط **"+ إضافة مجلد"** لإضافة مجلد أو أكثر
- يمكن إضافة مجلدات من أقراص مختلفة (مثال: D:\Work + E:\Archive)
- اضغط **✕** لحذف أي مجلد من القائمة

### اختيار مجلد الوجهة
- اضغط **"استعراض"** لاختيار مجلد النتائج
- الملفات المصنفة ستُنسخ (أو تُنقل) إلى هذا المجلد

### الخيارات السريعة

| الخيار | الوظيفة |
|---|---|
| **نقل (بدل النسخ)** | ينقل الملفات بدل نسخها — يوفر مساحة لكن لا يمكن التراجع |
| **OCR للصور** | يقرأ النص من الصور والملفات الممسوحة ضوئياً |
| **بداية جديدة** | يتجاهل التقدم السابق ويبدأ من الصفر |
| **كشف التكرارات** | يبحث عن ملفات مكررة ويعرض تقريراً |
| **تفريغ صوت/فيديو** | يحوّل الكلام في الملفات الصوتية والمرئية إلى نص |

### نموذج Whisper (للصوت والفيديو)

| النموذج | الدقة للعربي | السرعة | الاستخدام |
|---|---|---|---|
| tiny | ~70% | أسرع | فحص سريع |
| base | ~80% | سريع | ملفات كثيرة |
| **medium** | **~92%** | **متوسط** | **مُوصى به** |
| large | ~96% | بطيء | أعلى دقة |

### بدء التصنيف
1. أضف مجلد مصدر واحد على الأقل
2. اختر مجلد الوجهة
3. اضبط الخيارات حسب حاجتك
4. اضغط **▶ ابدأ**

يمكنك إيقاف التصنيف في أي وقت بالضغط على **⏹ إيقاف**
عند إعادة التشغيل، يكمل من حيث توقف (ما لم تختر "بداية جديدة").

---

## الإعدادات | Settings

### القوالب الوظيفية (21 قالب)
اختر مسماك الوظيفي لتفعيل التصنيفات المناسبة تلقائياً:

| القالب | التصنيفات |
|---|---|
| مدير تقنية (CTO) | جميع التصنيفات (23) |
| مدير مشاريع (PM) | إدارة مشاريع، تحليل أعمال، عقود... |
| مهندس بنية مؤسسية | بنية مؤسسية، تحول رقمي، حوكمة... |
| محلل أعمال | تحليل أعمال، مشاريع، استشارات... |
| مطور برمجيات | بنية تحتية، منتجات، + مستودعات كود |
| مدير تسويق | منتجات، + حملات تسويقية، تصميم |
| محاسب / مالية | مالية، عقود، + سجلات محاسبية |
| مدير موارد بشرية | موارد بشرية، عقود، + توظيف |
| معلم / مدرس | تدريب، + خطط دروس، سجلات طلاب |
| محامي / قانوني | عقود، سياسات، + قضايا قانونية |
| باحث / دكتوراه | + أبحاث علمية، تدريس أكاديمي، منح |
| مدير سمعي بصري | + أنظمة AV، مواصفات، فعاليات |
| صانع محتوى | + تخطيط محتوى، سكربتات، تحليلات |
| مبيعات / تطوير أعمال | + خط مبيعات، عروض عملاء |
| مصمم UX/UI | + أبحاث مستخدم، أصول تصميم |
| محلل / عالم بيانات | + تحليل بيانات، نماذج ذكاء اصطناعي |
| طبيب / رعاية صحية | + سجلات طبية، إدارة مستشفى |
| عقارات / إدارة أملاك | + إدارة عقارات |
| مدير عمليات | + عمليات، إجراءات تشغيل |
| استخدام عام | كتب، أطفال، وثائق شخصية |

### الأداء
- **عدد العمليات المتوازية**: 1-32 (الافتراضي 12)
- **حد أقصى لكل ملف**: 10-120 ثانية (الافتراضي 30)

### حد التصنيف
- **حد أدنى لدرجة التصنيف**: 2.0-15.0 (الافتراضي 5.0)
- رقم أعلى = دقة أكبر لكن ملفات أكثر في "غير مصنف"
- رقم أقل = تصنيف أكثر لكن احتمال أخطاء أعلى

### تسريع GPU
- التطبيق يكتشف كرت الشاشة NVIDIA تلقائياً
- فعّل GPU لتسريع OCR وتفريغ الصوت 5-10 أضعاف
- لو GPU مش موجود، يعمل على CPU تلقائياً

### أنواع الملفات (72 نوع)
فعّل أو عطّل أنواع الملفات حسب حاجتك:

| المجموعة | الأنواع | افتراضي |
|---|---|---|
| 📄 مستندات | docx, doc, rtf, txt, md, html, xml, json... | ✅ مفعّل |
| 📕 PDF | pdf | ✅ |
| 📊 جداول بيانات | xlsx, xls, csv, tsv, ods... | ✅ |
| 📽️ عروض تقديمية | pptx, ppt, odp... | ✅ |
| 📐 مخططات | vsd, vsdx, drawio, svg... | ✅ |
| 🖼️ صور (OCR) | png, jpg, tiff, bmp, webp... | ✅ |
| 💻 ملفات برمجية | py, js, java, sql, sh... | ⬜ معطّل |
| 📚 كتب إلكترونية | epub, mobi, azw3... | ⬜ |
| 📦 أرشيفات | zip, rar, 7z | ⬜ |
| 🏗️ CAD / 3D | dwg, dxf, step, stl | ⬜ |
| 🎬 صوت / فيديو | mp3, wav, mp4, mkv... | ⬜ |

يمكنك أيضاً **إضافة امتدادات مخصصة** بالضغط على "+ إضافة امتداد".

### حفظ الإعدادات
بعد تعديل الإعدادات، اضغط **💾 حفظ** — ستظهر رسالة تأكيد وسيعود للصفحة الرئيسية.

---

## صفحة التصنيفات | Categories

### التصنيفات الافتراضية (23 تصنيف)

1. البنية المؤسسية (Enterprise Architecture)
2. التحول الرقمي (Digital Transformation)
3. إدارة المشاريع (Project Management / PMO)
4. تحليل الأعمال (Business Analysis)
5. المخرجات الاستشارية (Consulting Deliverables)
6. التخطيط الاستراتيجي (Strategy & Planning)
7. تطوير المنتجات (Product Development)
8. حوكمة تقنية المعلومات (IT Governance)
9. العروض والمناقصات (Proposals & Tenders)
10. المالية والميزانيات (Finance & Budgets)
11. العقود والقانونية (Contracts & Legal)
12. الموارد البشرية (HR & People)
13. التقارير والعروض (Reports & Presentations)
14. التدريب ونقل المعرفة (Training & Knowledge)
15. محاضر الاجتماعات (Meeting Communications)
16. أنظمة التعلم (LMS / E-Learning)
17. البنية التحتية (Infrastructure & Technical)
18. السياسات والإجراءات (Policies & Procedures)
19. الكتب الشخصية (Personal Books)
20. أنشطة الأطفال (Kids Activities)
21. الوثائق الشخصية (Personal Documents)
22. القوالب القابلة لإعادة الاستخدام (Templates)
23. المخططات والرسوم (Diagrams & Visuals)

### تعديل التصنيفات
- **فعّل/عطّل** أي تصنيف بالمفتاح الجانبي
- **عدّل** أي تصنيف بالضغط على ✏️ (كلمات مفتاحية، أوزان، تلميحات)
- **أضف** تصنيف جديد بالضغط على "+ إضافة تصنيف"
- **استعد** التصنيفات الافتراضية بالضغط على "↺ استعادة"

### كيف يعمل التصنيف
1. يقرأ محتوى كل ملف (نص، OCR للصور، Whisper للصوت)
2. يبحث عن كلمات مفتاحية عربية وإنجليزية
3. يحسب درجة لكل تصنيف بناءً على عدد ووزن الكلمات المطابقة
4. ينسخ/ينقل الملف للتصنيف الأعلى درجة

### أولوية التصنيف
- التصنيفات **الشخصية** (كتب، أطفال) لها أولوية على المهنية
- يحتاج **كلمتين مفتاحيتين مختلفتين على الأقل** للتصنيف المهني
- **الكلمات السلبية** تمنع التصنيف الخاطئ (مثال: "قصة أطفال" لا تذهب لإدارة المشاريع)

---

## صفحة النتائج | Results

بعد انتهاء التصنيف، تعرض:

### ملخص
- **إجمالي**: عدد الملفات المعالجة
- **قابل للبيع ★**: ملفات ذات إمكانية تحويل لمنتج (score ≥ 8)
- **أخطاء**: ملفات لم يتم معالجتها
- **تصنيفات**: عدد التصنيفات المستخدمة

### توزيع التصنيفات
شريط تقدم لكل تصنيف يوضح عدد الملفات والنسبة المئوية.

### تقرير التكرارات (إذا مفعّل)
- عدد الملفات المكررة
- المساحة القابلة للتحرير
- تفاصيل كل مجموعة تكرار

---

## كشف التكرارات | Duplicate Detection

### مراحل الكشف (4 طبقات)

| المرحلة | الطريقة | الدقة |
|---|---|---|
| 1 | تطابق حجم الملف | فلتر أولي سريع |
| 2 | Hash جزئي (أول 8KB + آخر 8KB) | 99% |
| 3 | Hash كامل MD5 | 100% — تطابق محتوى |
| 4 | تطابق البيانات الوصفية (العنوان + المؤلف) | يكشف نُسخ مختلفة |

### خيارات عند اكتشاف التكرار

| الخيار | الوظيفة |
|---|---|
| **تقرير فقط** | يعرض تقرير CSV بدون حذف أي ملف |
| **نقل للمكررات** | ينقل النسخ المكررة لمجلد `_duplicates` (آمن) |
| **حذف نهائي** | يحذف النسخ المكررة (يوفر مساحة) |

### ملفات التقرير

بعد التصنيف، ستجد في مجلد الوجهة:
- `_categorization_report.json` — تقرير التصنيف الكامل
- `_categorization.log` — سجل العمليات
- `_PRODUCT_CANDIDATES.csv` — الملفات القابلة للتحويل لمنتج
- `_DUPLICATES_REPORT.csv` — تقرير التكرارات (إذا مفعّل)
- `_processed_files.json` — قائمة الملفات المعالجة (للاستكمال)

---

## تبديل اللغة | Language Switch

- من الشريط الجانبي، اختر **English** أو **العربية**
- التطبيق يُعيد بناء الواجهة تلقائياً باللغة الجديدة
- عند اختيار العربية، الواجهة تصبح من اليمين لليسار (RTL)
- عند اختيار الإنجليزية، الواجهة من اليسار لليمين (LTR)
- الإعداد يُحفظ تلقائياً

---

## الدعم | Support

إذا أعجبك البرنامج وساعدك في تنظيم ملفاتك، يمكنك دعم المشروع:

- **PayPal**: paypal.me/redaghareeb (تبرع مباشر بمبلغ محدد)
- **Patreon**: patreon.com/redaghareeb (دعم شهري)
- **GitHub**: github.com/redaghareeb (نجمة ومشاركة)

اضغط على ❤️ في الشريط الجانبي لتفاصيل الدعم.

---

## الأسئلة الشائعة | FAQ

### س: هل يحذف الملفات الأصلية؟
لا — الوضع الافتراضي هو **النسخ**. الملفات الأصلية تبقى في مكانها. فقط إذا فعّلت "نقل" يتم حذف الأصل بعد التأكد من نجاح النسخ.

### س: ماذا لو توقف التطبيق أثناء التصنيف؟
التطبيق يحفظ تقدمه تلقائياً. عند إعادة التشغيل، يكمل من حيث توقف.

### س: هل يدعم الملفات العربية؟
نعم — التصنيف يدعم الكلمات المفتاحية بالعربية والإنجليزية. OCR يقرأ النص العربي من الصور. Whisper يفرّغ الكلام العربي من الصوت والفيديو.

### س: كم حجم التطبيق؟
المثبّت ~80-120 MB. بعد التثبيت ~200 MB على القرص.

### س: هل يحتاج إنترنت؟
لا — يعمل بالكامل دون اتصال. فقط أول تشغيل لـ Whisper يحمّل النموذج (~1.5 GB لنموذج medium).

### س: هل يدعم GPU؟
نعم — يدعم بطاقات NVIDIA مع CUDA. فعّله من الإعدادات. لو مش موجود، يعمل على CPU تلقائياً.

---

© 2024-2025 Reda Ghareeb. All rights reserved.
```

---

Now I need to do the following:
1. 
2. 
3. 

Can you help me implementing these requirements?
