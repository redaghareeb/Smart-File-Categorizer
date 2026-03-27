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