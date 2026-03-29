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
from PIL import Image

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
def _rtl() -> bool:
    return get_lang() == "ar"

def _anchor():
    return "e" if _rtl() else "w"

def _sticky():
    return "e" if _rtl() else "w"

def _sticky_full():
    return "ew"

def _side():
    return "right" if _rtl() else "left"

def _side_end():
    return "left" if _rtl() else "right"

def _padx_start(outer=0, inner=0):
    return (inner, outer) if _rtl() else (outer, inner)

def _justify():
    return "right" if _rtl() else "left"

def _sidebar_col():
    return 2 if _rtl() else 0

def _main_col():
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

        self.geometry("1100x780")
        self.minsize(900, 650)

        # State
        self._sources = []  
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
        self._timeout = ctk.IntVar(value=120)
        self._score = ctk.DoubleVar(value=3.5)
        self._llm_var = ctk.BooleanVar(value=False)  # <-- NEW: AI Toggle State
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
        self.after(2500, self._close_splash)

    # --- SPLASH SCREEN FUNCTIONS ---
    def _show_splash(self):
        self.splash = ctk.CTkToplevel(self)
        self.splash.overrideredirect(True) 
        
        w, h = 400, 250
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.splash.geometry(f"{w}x{h}+{int(x)}+{int(y)}")
        self.splash.attributes("-topmost", True)
        
        sf = ctk.CTkFrame(self.splash, fg_color=("gray90", "#111827"), corner_radius=15, border_width=2, border_color=ACCENT)
        sf.pack(fill="both", expand=True)
        
        ctk.CTkLabel(sf, text=t("app_name"), font=(FONT, 24, "bold")).pack(pady=(70, 5)) 
        ctk.CTkLabel(sf, text="Loading AI Engines...", font=(FONT, 12), text_color="gray50").pack(pady=5)
        
        self.splash.update() 

    def _close_splash(self):
        self.splash.destroy()
        self.deiconify()

    # ═══════════ SIDEBAR ═══════════
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray92","gray14"))
        sb.grid(row=0, column=_sidebar_col(), sticky="nsew")
        sb.grid_propagate(False)
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

        ctk.CTkButton(sb, text=f" ℹ️  {t('about_btn')}", anchor=_anchor(), font=(FONT,13), height=38,
                      fg_color="transparent", text_color=("gray10","gray90"),
                      hover_color=("gray80","gray25"),
                      command=self._show_about).grid(row=7,column=0,padx=12,pady=(16,2),sticky="ew")

        ctk.CTkButton(sb, text=f" ❤️  {t('support_btn')}", anchor=_anchor(), font=(FONT,13), height=38,
                      fg_color="transparent", text_color="#F472B6",
                      hover_color=("gray80","gray25"),
                      command=self._show_support).grid(row=8,column=0,padx=12,pady=(2,2),sticky="ew")

        ctk.CTkLabel(sb, text=t("lang_lbl"), font=(FONT,11), text_color="gray50").grid(row=9,column=0,padx=20,pady=(8,0))
        self._lang_menu = ctk.CTkOptionMenu(sb, values=["English","العربية"], font=(FONT,11),
                                            height=28, width=140, command=self._switch_lang)
        self._lang_menu.grid(row=10,column=0,padx=20,pady=(4,8))
        self._lang_menu.set("English" if get_lang()=="en" else "العربية")

        ctk.CTkLabel(sb, text=t("theme_lbl"), font=(FONT,11), text_color="gray50").grid(row=11,column=0,padx=20,pady=(0,0))
        ctk.CTkOptionMenu(sb, values=["Dark","Light","System"], font=(FONT,11), height=28, width=140,
                          command=lambda v:ctk.set_appearance_mode(v)).grid(row=12,column=0,padx=20,pady=(4,20))

    def _switch_lang(self, v):
        new_lang = "ar" if "عرب" in v else "en"
        if new_lang == get_lang():
            return
        set_lang(new_lang)
        self._save_settings()
        self._rebuild_ui()

    def _rebuild_ui(self):
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
        use_llm = self._llm_var.get()
        results = self._results
        dedup_res = self._dedup_results

        for w in self.winfo_children():
            w.destroy()

        self.title(t("app_name"))

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
        self._llm_var = ctk.BooleanVar(value=use_llm)
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

    # ═══════════ LLM DETECTION HELPER ═══════════
    @staticmethod
    def _detect_llm():
        """Fetch all available Qwen models from Ollama."""
        import requests
        result = {"available": False, "models": [], "display": ""}
        try:
            res = requests.get("http://localhost:11434/api/tags", timeout=1.0)
            if res.status_code == 200:
                # Filter for any model containing 'qwen'
                all_models = [m["name"] for m in res.json().get("models", [])]
                qwen_models = [m for m in all_models if "qwen" in m.lower()]
                
                if qwen_models:
                    result["available"] = True
                    result["models"] = qwen_models
                    result["display"] = f"✅ {len(qwen_models)} AI Models Found"
                else:
                    result["display"] = "⚠ No Qwen models found in Ollama"
            else:
                result["display"] = "⚠ Ollama server error"
        except Exception:
            result["display"] = "⚠ AI Core (Ollama) not running"
        return result

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

        # --- NEW: AI/LLM ENGINE CHECK & TOGGLE ---
        ai_frame = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10, border_width=1, border_color=ACCENT)
        ai_frame.grid(row=7, column=0, sticky="ew", pady=(2,10), ipady=6)
        ai_frame.grid_columnconfigure(1, weight=1)
        
        llm_info = self._detect_llm()
        
        # Switch to enable LLM
        llm_label_txt = "تفعيل محرك الذكاء الاصطناعي (AI/LLM)" if get_lang() == "ar" else "Enable AI/LLM Engine"
        self.ai_switch = ctk.CTkSwitch(ai_frame, text=llm_label_txt, font=(FONT,12,"bold"), 
                                       variable=self._llm_var,
                                       state="normal" if llm_info["available"] else "disabled")
        self.ai_switch.grid(row=0, column=0, padx=16, pady=(8,4), sticky="w")

        # Dropdown to pick the model
        self._ollama_model_var = ctk.StringVar(value=llm_info["models"][0] if llm_info["models"] else "No Models")
        self.model_dropdown = ctk.CTkOptionMenu(ai_frame, variable=self._ollama_model_var,
                                                values=llm_info["models"] if llm_info["models"] else ["None Found"],
                                                font=(FONT, 11), height=28, width=200,
                                                state="normal" if llm_info["available"] else "disabled")
        self.model_dropdown.grid(row=0, column=1, padx=16, pady=(8,4), sticky="e")
        
        # Status Label
        ctk.CTkLabel(ai_frame, text=llm_info["display"], font=(FONT,10), 
                     text_color=SUCCESS if llm_info["available"] else "gray50").grid(row=1, column=0, columnspan=2, padx=16, pady=(0,4), sticky="w")

        # Progress
        pf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        pf.grid(row=8,column=0,sticky="ew",pady=(4,10),ipady=10); pf.grid_columnconfigure(0,weight=1)
        self._prog_lbl = ctk.CTkLabel(pf, text=t("ready"), font=(FONT,12), anchor=_anchor())
        self._prog_lbl.grid(row=0,column=0,padx=16,pady=(8,4),sticky=_sticky())
        self._prog_bar = ctk.CTkProgressBar(pf, height=14, corner_radius=7)
        self._prog_bar.grid(row=1,column=0,padx=16,pady=(0,4),sticky="ew"); self._prog_bar.set(0)
        self._stats_lbl = ctk.CTkLabel(pf, text="", font=(FONT,11), text_color="gray50", anchor=_anchor())
        self._stats_lbl.grid(row=2,column=0,padx=16,pady=(0,8),sticky=_sticky())

        # Buttons
        bf = ctk.CTkFrame(pg, fg_color="transparent"); bf.grid(row=9,column=0,sticky="ew",pady=(4,0))
        self._btn_start = ctk.CTkButton(bf, text=t("btn_start"), font=(FONT,15,"bold"), height=48,
                                         corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_H, command=self._start)
        self._btn_start.pack(side=_side(),expand=True,fill="x",padx=(0,8))
        self._btn_stop = ctk.CTkButton(bf, text=t("btn_stop"), font=(FONT,15,"bold"), height=48, width=140,
                                        corner_radius=10, fg_color=DANGER, hover_color="#B91C1C",
                                        state="disabled", command=self._stop)
        self._btn_stop.pack(side=_side())
        return pg

    def _render_sources(self):
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

        # FFMPEG PATH UI
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

        ft_header = ctk.CTkFrame(ftf, fg_color="transparent")
        ft_header.grid(row=0,column=0,sticky="ew",padx=16,pady=(10,4))
        ctk.CTkLabel(ft_header, text=t("ft_title"), font=(FONT,14,"bold")).pack(side=_side())
        active_n = sum(1 for v in self._filetypes.values() if v.get("enabled"))
        total_n = len(self._filetypes)
        self._ft_count_lbl = ctk.CTkLabel(ft_header, text=t("ft_active",n=active_n,t=total_n),
                                           font=(FONT,11), text_color="gray50")
        self._ft_count_lbl.pack(side=_side(), padx=12)

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

        self._ft_scroll = ctk.CTkScrollableFrame(ftf, fg_color="transparent", height=220)
        self._ft_scroll.grid(row=2,column=0,sticky="ew",padx=8,pady=(0,8))
        self._ft_scroll.grid_columnconfigure(0,weight=1)
        self._render_filetypes()

        ctk.CTkButton(pg, text=t("btn_save"), font=(FONT,14,"bold"), height=44,
                      fg_color=SUCCESS, hover_color="#15803D",
                      command=self._save_and_confirm).grid(row=6,column=0,pady=(8,16),sticky="ew")
        return pg

    def _save_and_confirm(self):
        self._save_settings()
        try:
            from CTkMessagebox import CTkMessagebox
            CTkMessagebox(title=t("save_ok_title"), message=t("save_ok_msg"), icon="check", option_1="OK")
        except ImportError:
            self._log(t("save_ok_msg"))
        self._go("home")

    # ═══════════ CATEGORIES PAGE ═══════════
    def _pg_cats(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(2,weight=1)
        ctk.CTkLabel(pg, text=t("cats_title"), font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,4))

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

        ctk.CTkLabel(scroll, text=t("cat_name"), font=(FONT,12,"bold")).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        name_var = ctk.StringVar(value=name or "")
        ctk.CTkEntry(scroll, textvariable=name_var, font=(FONT,12), height=32).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        pers_var = ctk.BooleanVar(value=cat.get("personal",False))
        ctk.CTkSwitch(scroll, text=t("cat_personal"), variable=pers_var, font=(FONT,12)).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=4)
        r+=1
        ctk.CTkLabel(scroll, text=t("cat_potential"), font=(FONT,12,"bold")).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        pot_var = ctk.StringVar(value=cat.get("pp","MEDIUM"))
        ctk.CTkOptionMenu(scroll, variable=pot_var, values=["NONE","LOW","MEDIUM","HIGH","VERY_HIGH"],
                          font=(FONT,11), height=28).grid(row=r,column=1,sticky=_sticky(),padx=4,pady=4)
        r+=1

        ctk.CTkLabel(scroll, text=t("cat_en_kw"), font=(FONT,12,"bold")).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=(8,4))
        r+=1
        en_kw_text = ctk.CTkTextbox(scroll, height=100, font=("Consolas",11))
        en_kw_text.grid(row=r,column=0,columnspan=2,sticky="ew",padx=4,pady=2)
        for k,v in cat.get("en",{}).items(): en_kw_text.insert(END, f"{k}:{v}\n")
        r+=1

        ctk.CTkLabel(scroll, text=t("cat_ar_kw"), font=(FONT,12,"bold")).grid(row=r,column=0,columnspan=2,sticky=_sticky(),padx=4,pady=(8,4))
        r+=1
        ar_kw_text = ctk.CTkTextbox(scroll, height=100, font=("Consolas",11))
        ar_kw_text.grid(row=r,column=0,columnspan=2,sticky="ew",padx=4,pady=2)
        for k,v in cat.get("ar",{}).items(): ar_kw_text.insert(END, f"{k}:{v}\n")
        r+=1

        ctk.CTkLabel(scroll, text=t("cat_fh"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        fh_var = ctk.StringVar(value=", ".join(cat.get("fh",[])))
        ctk.CTkEntry(scroll, textvariable=fh_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        ctk.CTkLabel(scroll, text=t("cat_ph"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        ph_var = ctk.StringVar(value=", ".join(cat.get("ph",[])))
        ctk.CTkEntry(scroll, textvariable=ph_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

        ctk.CTkLabel(scroll, text=t("cat_neg"), font=(FONT,12)).grid(row=r,column=0,sticky=_sticky(),padx=4,pady=4)
        neg_en_var = ctk.StringVar(value=", ".join(cat.get("neg_en",[])))
        ctk.CTkEntry(scroll, textvariable=neg_en_var, font=(FONT,11), height=30).grid(row=r,column=1,sticky="ew",padx=4,pady=4)
        r+=1

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
        # 1. Update the Engine's LLM Flag based on User's Toggle
        engine.CFG.use_llm = self._llm_var.get()
        
        # 2. Safety Check: Only verify Ollama if the user actually requested AI Mode
        if engine.CFG.use_llm:
            # Capture the specific model chosen in the dropdown
            selected_model = self._ollama_model_var.get()
            engine.CFG.ollama_model = selected_model
            
            try:
                import requests
                # Ping Ollama server
                res = requests.get("http://localhost:11434/api/tags", timeout=3)
                if res.status_code != 200:
                    raise Exception("Server Error")
                
                # Verify the SPECIFIC selected model is still available in Ollama
                available_models = [m["name"] for m in res.json().get("models", [])]
                if selected_model not in available_models:
                    self._show_err(f"The model '{selected_model}' was not found!\n"
                                   "Please refresh or select an available model from the list.")
                    return
                    
            except Exception:
                self._show_err("AI Brain (Ollama) is not running!\n"
                               "Please start the Ollama application or install the AI Core.")
                return

        # 3. Source check
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

            active = {k:v for k,v in self._cats.items() if k not in self._disabled}
            engine.reload_categories(active)

            # Reapply config properties manually just in case
            engine.CFG.ocr_on = self._ocr.get()
            engine.CFG.gpu = self._gpu.get()
            engine.CFG.move_mode = self._move.get()
            engine.CFG.reset = self._reset.get()
            engine.CFG.max_workers = self._workers.get()
            engine.CFG.file_timeout = self._timeout.get()
            engine.CFG.ocr_timeout = self._timeout.get() * 2
            engine.CFG.score_thr = self._score.get()
            engine.CFG.dedup = self._dedup.get()
            
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

            text_exts, img_exts, media_exts = cat_mgr.get_active_extensions(self._filetypes)
            engine.TXT_EXTS = text_exts
            engine.IMG_EXT = img_exts
            engine.MEDIA_EXT = media_exts
            engine.ALL_EXTS = text_exts | img_exts | media_exts
            engine.DIA_EXT = {ext for ext, info in self._filetypes.items()
                              if info.get("group") == "diagrams" and info.get("enabled")}

            engine.set_callbacks(progress_fn=self._on_progress, log_fn=self._log, cancel_event=self._cancel)

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
        import time
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
            pass

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
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("about_title"))
        dlg.geometry("500x420")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        hdr = ctk.CTkFrame(dlg, fg_color="transparent")
        hdr.pack(pady=(20, 10))
        
        ctk.CTkLabel(hdr, text="ℹ️", font=(FONT, 40)).pack()
            
        ctk.CTkLabel(hdr, text=t("app_name"), font=(FONT, 18, "bold")).pack(pady=(5,0))
        ctk.CTkLabel(hdr, text="Version 1.0", font=(FONT, 12), text_color="gray50").pack()

        desc_frame = ctk.CTkFrame(dlg, fg_color=("gray90","gray16"), corner_radius=10)
        desc_frame.pack(padx=24, pady=10, fill="x")
        ctk.CTkLabel(desc_frame, text=t("about_desc"), font=(FONT, 12), 
                     wraplength=420, justify="center" if get_lang()=="en" else "right").pack(padx=16, pady=16)

        contact_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        contact_frame.pack(padx=24, pady=5, fill="x")
        ctk.CTkLabel(contact_frame, text=t("support_email_lbl"), font=(FONT, 13, "bold")).pack()
        
        email = "rf.ghareeb@gmail.com"
        mailto_link = f"mailto:{email}?subject=SFC-%20" 
        
        email_btn = ctk.CTkButton(contact_frame, text=f"✉️ {email}", font=(FONT, 14, "bold"), 
                                  fg_color="transparent", text_color=ACCENT, hover_color=("gray80","gray25"), 
                                  command=lambda: self._open_link(mailto_link))
        email_btn.pack(pady=4)
        
        ctk.CTkLabel(contact_frame, text=t("email_note"), font=(FONT, 11), text_color="gray50").pack()

        ctk.CTkButton(dlg, text=t("support_close"), font=(FONT, 12), width=100, height=32,
                      fg_color="gray40", hover_color="gray30", 
                      command=dlg.destroy).pack(pady=(20, 10))
        
    def _show_support(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("support_title"))
        dlg.geometry("540x620")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        header = ctk.CTkFrame(dlg, fg_color=("gray85","gray18"), corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        hdr_inner = ctk.CTkFrame(header, fg_color="transparent")
        hdr_inner.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(hdr_inner, text="❤️", font=(FONT, 32)).pack(side=_side(), padx=(0,10))
        ctk.CTkLabel(hdr_inner, text=t("support_title"), font=(FONT, 20, "bold")).pack(side=_side())

        msg_frame = ctk.CTkFrame(dlg, fg_color=("gray90","gray16"), corner_radius=12)
        msg_frame.pack(padx=24, pady=(16,12), fill="x")
        ctk.CTkLabel(msg_frame, text=t("support_msg"), font=(FONT, 12),
                     wraplength=460,
                     justify="center" if get_lang()=="en" else "right",
                     ).pack(padx=16, pady=14)

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

        self._custom_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        self._custom_var = ctk.StringVar(value="")
        ctk.CTkLabel(self._custom_frame, text="$", font=(FONT, 18, "bold")).pack(side=_side(), padx=(0,4))
        ctk.CTkEntry(self._custom_frame, textvariable=self._custom_var,
                     font=(FONT, 16), height=40, width=120,
                     placeholder_text="15").pack(side=_side())

        self._select_amount("10")

        pay_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        pay_frame.pack(padx=24, pady=(8,4), fill="x")

        ctk.CTkButton(
            pay_frame, text=t("support_paypal_btn"), font=(FONT, 15, "bold"),
            height=50, corner_radius=10,
            fg_color="#0070BA", hover_color="#005C99",
            image=None,
            command=self._donate_paypal
        ).pack(fill="x", pady=(0,6))

        ctk.CTkButton(
            pay_frame, text=t("support_patreon_btn"), font=(FONT, 13),
            height=42, corner_radius=10,
            fg_color="#FF424D", hover_color="#E03640",
            command=lambda: self._open_link(self.PATREON_LINK)
        ).pack(fill="x", pady=(0,6))

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
        self._donate_amount.set(val)
        for btn, bval in self._amt_buttons:
            if bval == val:
                btn.configure(fg_color="#F472B6", text_color="white")
            else:
                btn.configure(fg_color=("gray75","gray30"), text_color=("gray10","gray90"))
        if val == "custom":
            self._custom_frame.pack(padx=24, pady=(2,0), anchor=_anchor())
        else:
            self._custom_frame.pack_forget()

    def _donate_paypal(self):
        amt = self._donate_amount.get()
        if amt == "custom":
            amt = self._custom_var.get().strip()
            if not amt:
                amt = "10"
            amt = ''.join(c for c in amt if c.isdigit() or c == '.')
            if not amt:
                amt = "10"
        url = f"https://paypal.me/{self.PAYPAL_USER}/{amt}"
        self._open_link(url)

    @staticmethod
    def _open_link(url):
        import webbrowser
        webbrowser.open(url)

    # ═══════════ FILE TYPE MANAGEMENT ═══════════
    def _render_filetypes(self):
        for w in self._ft_scroll.winfo_children():
            w.destroy()

        lang = get_lang()
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

            grp_frame = ctk.CTkFrame(self._ft_scroll, fg_color=("gray82","gray22"), corner_radius=6)
            grp_frame.grid(row=row_idx, column=0, sticky="ew", pady=(6,2), ipady=3)
            grp_frame.grid_columnconfigure(1, weight=1)

            enabled_in_grp = sum(1 for _, info in exts if info.get("enabled"))
            ctk.CTkLabel(grp_frame, text=f"{icon} {label}",
                         font=(FONT,12,"bold")).grid(row=0,column=0,padx=(10,6),pady=4,sticky=_sticky())
            ctk.CTkLabel(grp_frame, text=f"{enabled_in_grp}/{len(exts)}",
                         font=(FONT,10), text_color="gray50").grid(row=0,column=1,padx=4,pady=4,sticky=_sticky())

            ctk.CTkButton(grp_frame, text="☑", width=28, height=24, font=(FONT,11),
                          fg_color="gray35", hover_color="gray25",
                          command=lambda g=grp_key: self._toggle_group_ft(g, True)
                          ).grid(row=0,column=2,padx=2,pady=4)
            ctk.CTkButton(grp_frame, text="☐", width=28, height=24, font=(FONT,11),
                          fg_color="gray35", hover_color="gray25",
                          command=lambda g=grp_key: self._toggle_group_ft(g, False)
                          ).grid(row=0,column=3,padx=(2,8),pady=4)

            row_idx += 1

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
        if ext in self._filetypes:
            self._filetypes[ext]["enabled"] = enabled
            cat_mgr.save_filetypes(self._filetypes)
            self._update_ft_count()

    def _toggle_group_ft(self, group, enabled):
        for ext, info in self._filetypes.items():
            if info.get("group") == group:
                info["enabled"] = enabled
        cat_mgr.save_filetypes(self._filetypes)
        self._render_filetypes()

    def _toggle_all_ft(self, enabled):
        for info in self._filetypes.values():
            info["enabled"] = enabled
        cat_mgr.save_filetypes(self._filetypes)
        self._render_filetypes()

    def _reset_ft(self):
        cat_mgr.reset_filetypes()
        self._filetypes = cat_mgr.load_filetypes()
        self._render_filetypes()

    def _remove_ext(self, ext):
        if ext in self._filetypes and self._filetypes[ext].get("custom"):
            del self._filetypes[ext]
            cat_mgr.save_filetypes(self._filetypes)
            self._render_filetypes()

    def _update_ft_count(self):
        active = sum(1 for v in self._filetypes.values() if v.get("enabled"))
        total = len(self._filetypes)
        try:
            self._ft_count_lbl.configure(text=t("ft_active", n=active, t=total))
        except Exception:
            pass

    def _add_ext_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title(t("ft_add_title"))
        dlg.geometry("420x320")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=t("ft_add_title"), font=(FONT,16,"bold")).pack(padx=20,pady=(16,12))

        ctk.CTkLabel(dlg, text=t("ft_ext_label"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        ext_var = ctk.StringVar()
        ctk.CTkEntry(dlg, textvariable=ext_var, font=(FONT,12), height=34,
                     placeholder_text=".xyz").pack(padx=20,fill="x",pady=(4,8))

        ctk.CTkLabel(dlg, text=t("ft_ext_desc"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        desc_var = ctk.StringVar()
        ctk.CTkEntry(dlg, textvariable=desc_var, font=(FONT,12), height=34,
                     placeholder_text="My Custom File").pack(padx=20,fill="x",pady=(4,8))

        ctk.CTkLabel(dlg, text=t("ft_ext_group"), font=(FONT,12)).pack(padx=20,anchor=_anchor())
        grp_var = ctk.StringVar(value="documents")
        group_names = list(cat_mgr.FILE_GROUPS.keys())
        ctk.CTkOptionMenu(dlg, variable=grp_var, values=group_names,
                          font=(FONT,11), height=30).pack(padx=20,anchor=_anchor(),pady=(4,8))

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
                "use_llm":self._llm_var.get(),
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
                if "sources" in d:
                    self._sources = [s for s in d["sources"] if isinstance(s,str)]
                elif "source" in d and d["source"]:
                    self._sources = [d["source"]]
                self._dst.set(d.get("dest",""))
                self._move.set(d.get("move",False)); self._ocr.set(d.get("ocr",True))
                self._gpu.set(d.get("gpu",False)); self._workers.set(d.get("workers",12))
                self._timeout.set(d.get("timeout",120)); self._score.set(d.get("score",3.5))
                self._llm_var.set(d.get("use_llm", False))
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