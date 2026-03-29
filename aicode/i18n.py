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
