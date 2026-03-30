"""
Smart Media Categorizer — Desktop App v2.0
AI Facial Recognition | Soft/Hard Modes | Media Organizer
"""
import os, sys, json, threading
from pathlib import Path
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, END

# FIX: Prevent silent hard crashes when heavy C++ libraries load together
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    import engine
    import persons as person_mgr
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import engine
    import persons as person_mgr

from i18n import t, set_lang, get_lang

FONT = "Segoe UI"
ACCENT, ACCENT_H = "#2563EB", "#1D4ED8"
SUCCESS, WARN, DANGER = "#16A34A", "#F59E0B", "#DC2626"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ═══════════ RTL HELPERS ═══════════
def _rtl() -> bool: return get_lang() == "ar"
def _anchor(): return "e" if _rtl() else "w"
def _sticky(): return "e" if _rtl() else "w"
def _side(): return "right" if _rtl() else "left"
def _side_end(): return "left" if _rtl() else "right"
def _sidebar_col(): return 2 if _rtl() else 0
def _main_col(): return 0 if _rtl() else 1

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- Window Setup ---
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.geometry("1100x780")
        self.minsize(900, 650)
        self.title("Smart Media Categorizer")

        # --- Application State ---
        self._sources = []  
        self._dst = ctk.StringVar()
        self._mode = ctk.StringVar(value="soft") # 'soft' or 'hard'
        
        # Performance & Vision Settings
        self._workers = ctk.IntVar(value=4)
        self._tolerance = ctk.DoubleVar(value=0.6) # Face match strictness
        self._frame_skip = ctk.IntVar(value=30)    # Video processing speedup
        
        self._running = False
        self._cancel = threading.Event()
        self._results = []
        self._persons = person_mgr.load_persons()
        
        self._settings_path = Path.home() / ".smart_media_settings.json"
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
        sb.grid_propagate(False)
        sb.grid_rowconfigure(8, weight=1)
        
        ctk.CTkLabel(sb, text="📸", font=(FONT,36)).grid(row=0,column=0,padx=20,pady=(24,4))
        self._title_lbl = ctk.CTkLabel(sb, text="Smart Media", font=(FONT,16,"bold"))
        self._title_lbl.grid(row=1,column=0,padx=20,pady=(0,4))
        ctk.CTkLabel(sb, text="AI Face Recognition", font=(FONT,11), text_color="gray50").grid(row=2,column=0,padx=20,pady=(0,16))

        self._nav = {}
        icons = [("home","Home","🏠"), ("settings","Settings","⚙️"),
                 ("faces","Faces Database","👤"), ("results","Results","📊"), ("log","Log","📝")]
                 
        for i,(k,lk,ic) in enumerate(icons):
            b = ctk.CTkButton(sb, text=f" {ic}  {lk}", anchor=_anchor(), font=(FONT,13), height=38,
                              fg_color="transparent", text_color=("gray10","gray90"),
                              hover_color=("gray80","gray25"), command=lambda key=k:self._go(key))
            b.grid(row=3+i,column=0,padx=12,pady=2,sticky="ew")
            self._nav[k] = (b, lk, ic)

        # Language & Theme toggles at the bottom
        self._lang_menu = ctk.CTkOptionMenu(sb, values=["English","العربية"], font=(FONT,11),
                                            height=28, width=140, command=self._switch_lang)
        self._lang_menu.grid(row=10,column=0,padx=20,pady=(4,8))
        self._lang_menu.set("English" if get_lang()=="en" else "العربية")

        ctk.CTkOptionMenu(sb, values=["Dark","Light","System"], font=(FONT,11), height=28, width=140,
                          command=lambda v:ctk.set_appearance_mode(v)).grid(row=12,column=0,padx=20,pady=(4,20))

    def _switch_lang(self, v):
        new_lang = "ar" if "عرب" in v else "en"
        if new_lang != get_lang():
            set_lang(new_lang)
            self._save_settings()
            # A full restart of the app might be better for RTL, but we'll try to rebuild
            self.destroy()
            os.execl(sys.executable, sys.executable, *sys.argv)

    def _go(self, key):
        for k, f in self._pages.items(): f.grid_forget()
        self._pages[key].grid(row=0,column=0,sticky="nsew",padx=20,pady=16)
        for k,(btn,lk,ic) in self._nav.items():
            btn.configure(fg_color=ACCENT if k==key else "transparent",
                          text_color="white" if k==key else ("gray10","gray90"))

    # ═══════════ MAIN VIEW ═══════════
    def _build_main(self):
        self._main = ctk.CTkFrame(self, fg_color="transparent")
        self._main.grid(row=0, column=_main_col(), sticky="nsew")
        self._main.grid_columnconfigure(0,weight=1)
        self._main.grid_rowconfigure(0,weight=1)
        
        self._pages = {}
        self._pages["home"] = self._pg_home()
        self._pages["settings"] = self._pg_settings()
        self._pages["faces"] = self._pg_faces()
        self._pages["results"] = self._pg_results()
        self._pages["log"] = self._pg_log()
        self._go("home")

    # ═══════════ HOME PAGE ═══════════
    def _pg_home(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(pg, text="Organize Media by Faces", font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,4))
        ctk.CTkLabel(pg, text="Select source images/videos and choose how you want to organize them.", font=(FONT,13), text_color="gray50", anchor=_anchor()).grid(row=1,column=0,sticky=_sticky(),pady=(0,12))

        # ── Source Folders ──
        src_frame = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        src_frame.grid(row=2,column=0,sticky="ew",pady=(0,8),ipady=6)
        src_frame.grid_columnconfigure(0,weight=1)

        src_header = ctk.CTkFrame(src_frame, fg_color="transparent")
        src_header.grid(row=0,column=0,sticky="ew",padx=16,pady=(8,4))
        ctk.CTkLabel(src_header, text="📁 Source Media Folders", font=(FONT,13,"bold")).pack(side=_side())
        ctk.CTkButton(src_header, text="+ Add Folder", width=100, height=28, font=(FONT,11),
                      fg_color=SUCCESS, hover_color="#15803D", command=self._add_source).pack(side=_side_end())

        self._src_list_frame = ctk.CTkFrame(src_frame, fg_color="transparent")
        self._src_list_frame.grid(row=1,column=0,sticky="ew",padx=16,pady=(0,8))
        self._src_list_frame.grid_columnconfigure(0,weight=1)
        self._render_sources()

        # ── Destination ──
        dst_frame = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        dst_frame.grid(row=3,column=0,sticky="ew",pady=(0,8),ipady=6)
        dst_frame.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(dst_frame, text="📂 Destination Output", font=(FONT,13,"bold"), anchor=_anchor()).grid(row=0,column=0,padx=(16,8),pady=(8,0),sticky=_sticky())
        ctk.CTkEntry(dst_frame, textvariable=self._dst, font=(FONT,12), height=34, placeholder_text="Where to save results...").grid(row=1,column=0,columnspan=2,padx=16,pady=(4,8),sticky="ew")
        ctk.CTkButton(dst_frame, text="Browse", width=90, height=34, font=(FONT,12), command=lambda:self._browse("dest")).grid(row=1,column=2,padx=(0,16),pady=(4,8))

        # ── Operation Mode (Soft vs Hard) ──
        mode_frame = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10, border_width=1, border_color=ACCENT)
        mode_frame.grid(row=4, column=0, sticky="ew", pady=(2,10), ipady=6)
        mode_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(mode_frame, text="⚙️ Processing Mode", font=(FONT,13,"bold")).grid(row=0, column=0, columnspan=2, padx=16, pady=(8,4), sticky="w")
        
        rad_soft = ctk.CTkRadioButton(mode_frame, text="Soft Mode (Scan Only - Generates JSON/CSV Report, keeps files in place)", 
                                      variable=self._mode, value="soft", font=(FONT, 12))
        rad_soft.grid(row=1, column=0, padx=16, pady=4, sticky="w")
        
        rad_hard = ctk.CTkRadioButton(mode_frame, text="Hard Mode (Organize - Copies files into folders named after the detected persons)", 
                                      variable=self._mode, value="hard", font=(FONT, 12))
        rad_hard.grid(row=2, column=0, padx=16, pady=(4,8), sticky="w")

        # ── Progress ──
        pf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        pf.grid(row=8,column=0,sticky="ew",pady=(4,10),ipady=10); pf.grid_columnconfigure(0,weight=1)
        self._prog_lbl = ctk.CTkLabel(pf, text="Ready to scan", font=(FONT,12), anchor=_anchor())
        self._prog_lbl.grid(row=0,column=0,padx=16,pady=(8,4),sticky=_sticky())
        self._prog_bar = ctk.CTkProgressBar(pf, height=14, corner_radius=7)
        self._prog_bar.grid(row=1,column=0,padx=16,pady=(0,4),sticky="ew"); self._prog_bar.set(0)

        # ── Buttons ──
        bf = ctk.CTkFrame(pg, fg_color="transparent"); bf.grid(row=9,column=0,sticky="ew",pady=(4,0))
        self._btn_start = ctk.CTkButton(bf, text="▶ Start Processing", font=(FONT,15,"bold"), height=48,
                                        corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_H, command=self._start)
        self._btn_start.pack(side=_side(),expand=True,fill="x",padx=(0,8))
        self._btn_stop = ctk.CTkButton(bf, text="⏹ Stop", font=(FONT,15,"bold"), height=48, width=140,
                                        corner_radius=10, fg_color=DANGER, hover_color="#B91C1C",
                                        state="disabled", command=self._stop)
        self._btn_stop.pack(side=_side())
        return pg

    def _render_sources(self):
        for w in self._src_list_frame.winfo_children(): w.destroy()

        if not self._sources:
            ctk.CTkLabel(self._src_list_frame, text="No source folders added yet.",
                         font=(FONT,11), text_color="gray50").grid(row=0,column=0,pady=4,sticky=_sticky())
            return

        for i, src_path in enumerate(self._sources):
            row = ctk.CTkFrame(self._src_list_frame, fg_color=("gray80","gray25"), corner_radius=6)
            row.grid(row=i,column=0,sticky="ew",pady=2,ipady=2); row.grid_columnconfigure(0,weight=1)
            display = src_path if len(src_path) < 60 else "..." + src_path[-55:]
            ctk.CTkLabel(row, text=f"📁 {display}", font=(FONT,11), anchor=_anchor()).grid(row=0,column=0,padx=(8,4),pady=4,sticky=_sticky())
            ctk.CTkButton(row, text="✕", width=28, height=24, font=(FONT,11), fg_color=DANGER, hover_color="#B91C1C",
                          command=lambda idx=i: self._remove_source(idx)).grid(row=0,column=1,padx=(4,6),pady=4)

    def _add_source(self):
        folder = filedialog.askdirectory(title="Select Media Folder")
        if folder and folder not in self._sources:
            self._sources.append(folder)
            self._render_sources()
            if not self._dst.get():
                self._dst.set(os.path.join(folder, "Smart_Face_Output"))

    def _remove_source(self, idx):
        if 0 <= idx < len(self._sources):
            self._sources.pop(idx)
            self._render_sources()

    # ═══════════ FACES DATABASE PAGE ═══════════
    def _pg_faces(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(2,weight=1)
        
        ctk.CTkLabel(pg, text="👤 Faces Database", font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,4))
        ctk.CTkLabel(pg, text="Assign real names to the faces detected by the AI. These names will be used for your folders.", font=(FONT,13), text_color="gray50", anchor=_anchor()).grid(row=1,column=0,sticky=_sticky(),pady=(0,12))

        tb = ctk.CTkFrame(pg, fg_color="transparent"); tb.grid(row=1,column=0,sticky="ew",pady=(0,8))
        ctk.CTkButton(tb, text="🔄 Refresh List", font=(FONT,12), height=32, fg_color="gray40", command=self._refresh_faces).pack(side=_side())

        self._faces_scroll = ctk.CTkScrollableFrame(pg, fg_color="transparent")
        self._faces_scroll.grid(row=2,column=0,sticky="nsew"); self._faces_scroll.grid_columnconfigure(0,weight=1)
        
        self._render_faces()
        return pg

    def _refresh_faces(self):
        self._persons = person_mgr.load_persons()
        self._render_faces()

    def _render_faces(self):
        for w in self._faces_scroll.winfo_children(): w.destroy()
        
        if not self._persons:
            ctk.CTkLabel(self._faces_scroll, text="No faces detected yet. Run a scan on your media first!", font=(FONT,14), text_color="gray50").pack(pady=40)
            return

        for i, (pid, info) in enumerate(self._persons.items()):
            row = ctk.CTkFrame(self._faces_scroll, fg_color=("gray88","gray20"), corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", pady=4, ipady=4)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row, text="👤", font=(FONT,24)).grid(row=0, column=0, padx=12, pady=8)
            
            # Entry to edit the name
            name_var = ctk.StringVar(value=info["name"])
            entry = ctk.CTkEntry(row, textvariable=name_var, font=(FONT,14,"bold"), height=36)
            entry.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
            
            ctk.CTkLabel(row, text=f"ID: {pid}", font=(FONT,10), text_color="gray50").grid(row=0, column=2, padx=8)

            # Save Button for this specific person
            ctk.CTkButton(row, text="Save Name", width=90, height=36, font=(FONT,12,"bold"), fg_color=SUCCESS,
                          command=lambda p=pid, v=name_var: self._update_person_name(p, v.get())).grid(row=0, column=3, padx=12, pady=8)

    def _update_person_name(self, person_id, new_name):
        if new_name.strip():
            self._persons = person_mgr.update_person_name(self._persons, person_id, new_name.strip())
            self._log(f"Updated {person_id} to '{new_name.strip()}'")

    # ═══════════ SETTINGS PAGE ═══════════
    def _pg_settings(self):
        pg = ctk.CTkScrollableFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(pg, text="⚙️ Settings", font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,16))

        # Vision Settings
        cf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        cf.grid(row=1,column=0,sticky="ew",pady=(0,12),ipady=10); cf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(cf, text="Computer Vision & AI", font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,8),sticky=_sticky())
        
        ctk.CTkLabel(cf, text="Face Match Strictness", font=(FONT,12)).grid(row=1,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(cf, from_=0.3, to=0.8, number_of_steps=50, variable=self._tolerance).grid(row=1,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(cf, textvariable=self._tolerance, width=40, font=(FONT,12,"bold")).grid(row=1,column=2,padx=(0,16))
        ctk.CTkLabel(cf, text="Lower values are more strict (less false positives, but might miss faces).\n0.6 is the recommended default.", font=(FONT,11), text_color="gray50", justify="left").grid(row=2,column=0,columnspan=3,padx=16,pady=(2,8),sticky=_sticky())

        ctk.CTkLabel(cf, text="Video Frame Check", font=(FONT,12)).grid(row=3,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(cf, from_=1, to=100, number_of_steps=99, variable=self._frame_skip).grid(row=3,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(cf, textvariable=self._frame_skip, width=40, font=(FONT,12,"bold")).grid(row=3,column=2,padx=(0,16))
        ctk.CTkLabel(cf, text="Check 1 frame every X frames for videos. Higher = much faster processing, but might miss brief appearances.", font=(FONT,11), text_color="gray50", justify="left").grid(row=4,column=0,columnspan=3,padx=16,pady=(2,8),sticky=_sticky())

        # Performance
        pf = ctk.CTkFrame(pg, fg_color=("gray88","gray20"), corner_radius=10)
        pf.grid(row=2,column=0,sticky="ew",pady=(0,12),ipady=10); pf.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(pf, text="⚡ Performance", font=(FONT,14,"bold")).grid(row=0,column=0,columnspan=3,padx=16,pady=(10,8),sticky=_sticky())
        
        ctk.CTkLabel(pf, text="CPU Workers", font=(FONT,12)).grid(row=1,column=0,padx=(16,8),pady=4,sticky=_sticky())
        ctk.CTkSlider(pf, from_=1,to=16,number_of_steps=15, variable=self._workers).grid(row=1,column=1,padx=(0,8),pady=4,sticky="ew")
        ctk.CTkLabel(pf, textvariable=self._workers, width=40, font=(FONT,12,"bold")).grid(row=1,column=2,padx=(0,16))

        ctk.CTkButton(pg, text="💾 Save Settings", font=(FONT,14,"bold"), height=44, fg_color=SUCCESS, hover_color="#15803D", command=self._save_settings).grid(row=6,column=0,pady=(8,16),sticky="ew")
        return pg

    # ═══════════ RESULTS PAGE ═══════════
    def _pg_results(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(1,weight=1)
        ctk.CTkLabel(pg, text="📊 Scan Results", font=(FONT,22,"bold"), anchor=_anchor()).grid(row=0,column=0,sticky=_sticky(),pady=(0,12))
        self._res_scroll = ctk.CTkScrollableFrame(pg, fg_color="transparent")
        self._res_scroll.grid(row=1,column=0,sticky="nsew"); self._res_scroll.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self._res_scroll, text="No scan results yet.\nRun a scan from the Home tab.", font=(FONT,14), text_color="gray50").grid(row=0,column=0,pady=60)
        return pg

    def _refresh_results(self):
        for w in self._res_scroll.winfo_children(): w.destroy()
        
        report_path = Path(self._dst.get()) / "media_scan_report.json"
        if not report_path.exists():
            ctk.CTkLabel(self._res_scroll, text="Results report not found.", font=(FONT,14), text_color="gray50").grid(row=0,column=0,pady=60)
            return

        try:
            results = json.loads(report_path.read_text(encoding="utf-8"))
            if not results:
                ctk.CTkLabel(self._res_scroll, text="Scan finished, but no media files processed.", font=(FONT,14), text_color="gray50").grid(row=0,column=0,pady=60)
                return

            ctk.CTkLabel(self._res_scroll, text=f"Total Media Processed: {len(results)}", font=(FONT,16,"bold"), text_color=SUCCESS).grid(row=0, column=0, pady=(10,20))

            for i, item in enumerate(results):
                row = ctk.CTkFrame(self._res_scroll, fg_color=("gray88","gray20"), corner_radius=6)
                row.grid(row=i+1, column=0, sticky="ew", pady=2, ipady=4); row.grid_columnconfigure(0,weight=1)
                
                fname = Path(item.get("file", "")).name
                people = ", ".join(item.get("people", []))
                
                ctk.CTkLabel(row, text=f"📄 {fname}", font=(FONT,12,"bold")).grid(row=0,column=0,padx=12,pady=4,sticky="w")
                ctk.CTkLabel(row, text=f"Faces: {people}", font=(FONT,11), text_color=ACCENT).grid(row=1,column=0,padx=12,pady=(0,4),sticky="w")
                
        except Exception as e:
            ctk.CTkLabel(self._res_scroll, text=f"Error reading results: {e}", text_color=DANGER).pack(pady=20)

    # ═══════════ LOG PAGE ═══════════
    def _pg_log(self):
        pg = ctk.CTkFrame(self._main, fg_color="transparent")
        pg.grid_columnconfigure(0,weight=1); pg.grid_rowconfigure(1,weight=1)
        hd = ctk.CTkFrame(pg, fg_color="transparent"); hd.grid(row=0,column=0,sticky="ew",pady=(0,8))
        ctk.CTkLabel(hd, text="📝 Activity Log", font=(FONT,22,"bold"), anchor=_anchor()).pack(side=_side())
        ctk.CTkButton(hd, text="🗑 Clear", width=80, height=30, font=(FONT,11), fg_color="gray40", command=lambda:self._log_box.delete("1.0",END)).pack(side=_side_end())
        self._log_box = ctk.CTkTextbox(pg, font=("Consolas",11), wrap="word", fg_color=("gray92","gray12"))
        self._log_box.grid(row=1,column=0,sticky="nsew")
        return pg

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_box.after(0, lambda: self._log_box.insert(END, f"[{ts}] {msg}\n"))
        self._log_box.after(0, lambda: self._log_box.see(END))

    # ═══════════ ENGINE EXECUTION ═══════════
    def _browse(self, which):
        folder = filedialog.askdirectory()
        if folder: self._dst.set(folder)

    def _start(self):
        if not self._sources:
            self._log("Error: No source folders selected.")
            return
        dst = self._dst.get().strip()
        if not dst: 
            self._log("Error: No destination folder selected.")
            return

        # Prepare Engine CFG
        engine.CFG.mode = self._mode.get()
        engine.CFG.tolerance = self._tolerance.get()
        engine.CFG.frame_skip = self._frame_skip.get()
        
        self._running = True
        self._cancel.clear()
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._prog_bar.set(0)
        self._prog_lbl.configure(text="Scanning Media... Check Log for details.")
        
        self._log(f"Starting {engine.CFG.mode.upper()} mode scan...")
        
        # Start background thread
        self._worker = threading.Thread(target=self._run_engine, args=(list(self._sources), dst), daemon=True)
        self._worker.start()

    def _run_engine(self, sources, dst):
        try:
            # We will pass a simple mock progress callback here if engine.py supports it, 
            # otherwise it just runs synchronously in this thread.
            engine.run(sources, dst)
            self.after(0, self._on_complete)
        except Exception as e:
            self._log(f"Engine Error: {str(e)}")
            self.after(0, lambda: self._on_complete(error=str(e)))

    def _on_complete(self, error=None):
        self._running = False
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        
        if error:
            self._prog_lbl.configure(text=f"Stopped due to error.")
        elif self._cancel.is_set():
            self._prog_lbl.configure(text="Scan manually stopped.")
        else:
            self._prog_lbl.configure(text="Scan Complete!")
            self._prog_bar.set(1.0)
            
        self._refresh_faces() # Reload newly discovered faces
        self._refresh_results()

    def _stop(self):
        self._cancel.set()
        self._btn_stop.configure(state="disabled")
        self._prog_lbl.configure(text="Stopping...")
        self._log("Stop requested by user.")

    # ═══════════ PERSISTENCE ═══════════
    def _save_settings(self):
        data = {
            "sources": self._sources,
            "dest": self._dst.get(),
            "mode": self._mode.get(),
            "workers": self._workers.get(),
            "tolerance": self._tolerance.get(),
            "frame_skip": self._frame_skip.get(),
            "lang": get_lang()
        }
        try: 
            self._settings_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as e: 
            self._log(f"Failed to save settings: {e}")

    def _load_settings(self):
        try:
            if self._settings_path.exists():
                d = json.loads(self._settings_path.read_text(encoding="utf-8"))
                self._sources = d.get("sources", [])
                self._dst.set(d.get("dest", ""))
                self._mode.set(d.get("mode", "soft"))
                self._workers.set(d.get("workers", 4))
                self._tolerance.set(d.get("tolerance", 0.6))
                self._frame_skip.set(d.get("frame_skip", 30))
                
                lang = d.get("lang", "en")
                if lang != get_lang(): set_lang(lang)
        except Exception: 
            pass

if __name__ == "__main__":
    app = App()
    app.mainloop()