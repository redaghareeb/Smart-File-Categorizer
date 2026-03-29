"""
categories.py — Dynamic category management with job role presets (Enhanced Smart Regex Edition)
"""

import json
from pathlib import Path
from copy import deepcopy

CATS_FILE = Path.home() / ".smart_categorizer_categories.json"

# ═══════════════════════════════════════════════
#  DEFAULT CATEGORIES (Optimized for Morphological Engine v3.2+)
# ═══════════════════════════════════════════════

_DEFAULTS = {
"00_General_Administration": {
    "pp":"LOW","personal":False,
    "en":{"memo":4,"circular":5,"general administration":4,"leave request":4,"vacation":3,"attendance":3,"official letter":4},
    "ar":{"تعميم":5,"تعاميم":5,"قرار اداري":5,"ادارة عامة":4,"طلب اجازة":5,"اجازات":4,"دوام":3,"خطاب رسمي":5,"مذكرة داخلية":5,"شؤون ادارية":4,"صادر":5,"وارد":5,"مشفوعات":3},
    "fh":["memo","circular","admin","تعميم","خطاب","اجازة","ادارة","صادر","وارد","قرار"],
    "ph":["admin","general","ادارة","عامة","تعاميم","صادر","وارد"],
    "neg_en":[],"neg_ar":[],
},    
"01_Enterprise_Architecture": {
    "pp":"HIGH", "personal": False,
    "en":{"enterprise architecture":5,"togaf":5,"archimate":5,"togaf adm":5,"architecture framework":4,"capability map":4,"business architecture":4,"data architecture":4,"technology architecture":4,"application architecture":4,"target architecture":4,"reference architecture":4,"solution architecture":4,"zachman":5,"eamm":4,"it landscape":4},
    "ar":{"بنية مؤسسية":5,"بنى مؤسسية":5,"معمارية الحلول":4,"معمارية تقنية":4,"معمارية البيانات":4,"معمارية التطبيقات":4,"خارطة القدرات":4,"المعمارية المرجعية":4,"حوكمة المعمارية":4,"توغاف":5},
    "fh":["togaf","archimate","enterprise_arch","capability_map"],"ph":["architecture","togaf","enterprise_architecture"],
    "neg_en":["story","novel","children","kids","fairy","coloring","tales","isbn"],"neg_ar":["قصة","رواية","اطفال","تلوين","حكاية"],
},
"02_Digital_Transformation": {
    "pp":"HIGH","personal":False,
    "en":{"digital transformation":5,"digital strategy":5,"digital maturity":4,"maturity assessment":4,"digital roadmap":4,"e-government":4,"smart government":4,"digital governance":4,"dga standard":5,"legacy modernization":4,"cloud migration":3,"digitalization":4,"smart city":4,"yesser":5,"gsb":4},
    "ar":{"تحول رقمي":5,"الحكومة الرقمية":4,"الخدمات الرقمية":4,"خدمة الكترونية":4,"النضج الرقمي":4,"الاستراتيجية الرقمية":5,"الحكومة الالكترونية":4,"هيئة الحكومة الرقمية":5,"الرقمنة":4,"المنصات الرقمية":4,"مدينة ذكية":4,"قناة التكامل":4,"يسر":5},
    "fh":["digital_transform","digitalization","dga_standards"],"ph":["digital_transformation","digitalization"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"03_Project_Management_PMO": {
    "pp":"HIGH","personal":False,
    "en":{"project management":5,"project charter":5,"project plan":4,"pmo":5,"pmbok":5,"prince2":5,"work breakdown structure":5,"wbs":4,"gantt chart":5,"critical path":4,"risk register":5,"risk management":5,"change request":4,"lesson learned":4,"project closure":4,"stakeholder":4,"agile":4,"scrum":4,"sprint":3,"kanban":3,"milestone":4,"status report":4},
    "ar":{"ادارة مشاريع":5,"مكتب ادارة مشاريع":5,"ميثاق مشروع":5,"خطة مشروع":4,"سجل مخاطر":5,"ادارة مخاطر":4,"هيكل تجزئة العمل":5,"دروس مستفادة":4,"مدير مشروع":4,"جدول زمني":4,"تقرير حالة":4,"مشروع":3,"مشاريع":3},
    "fh":["project_plan","project_charter","pmo_","gantt","wbs_","risk_register","pmbok"],"ph":["project_management","pmo","projects"],
    "neg_en":["story","novel","children","kids","hero","fairy","coloring","book","isbn"],"neg_ar":["قصة","رواية","اطفال","تلوين","بطل","حكاية","ابطال"],
},
"04_Business_Analysis": {
    "pp":"HIGH","personal":False,
    "en":{"business analysis":5,"business process":5,"functional requirement":4,"non-functional requirement":4,"use case":5,"user story":3,"acceptance criteria":4,"brd":4,"frd":4,"gap analysis":5,"bpmn":5,"process map":4,"feasibility study":4,"cost-benefit analysis":4,"as-is":5,"to-be":5,"bpr":5,"process reengineering":5,"current state":4,"future state":4,"process flow":4},
    "ar":{"تحليل اعمال":5,"متطلبات وظيفية":4,"تحليل فجوات":5,"دراسة جدوى":4,"حالات استخدام":4,"متطلبات عمل":4,"إجراءات عمل":5,"إعادة هندسة":5,"هندسة عمليات":4,"سير عمل":5,"سير اعمال":4,"وضع حالي":5,"وضع مستقبلي":5,"وثيقة تحليل":5,"نموذج عمل":4,"عمليات":3},
    "fh":["brd_","frd_","requirements_","gap_analysis","use_case","process","to-be","as-is","bpr"],"ph":["business_analysis","requirements","bpr","process"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"05_Consulting_Deliverables": {
    "pp":"HIGH","personal":False,
    "en":{"consulting engagement":4,"consulting deliverable":5,"advisory report":4,"assessment report":4,"current state assessment":5,"strategic assessment":4,"implementation roadmap":5,"transformation roadmap":5,"workshop facilitation":4,"benchmarking study":4,"best practice":4,"recommendation":3,"pwc":5,"deloitte":5,"kpmg":5,"mckinsey":5,"ey":5,"booz allen":5,"consulting study":4},
    "ar":{"استشارات":3,"استشارية":4,"تقييم استراتيجي":4,"تقييم وضع حالي":5,"ورشة عمل":3,"خارطة طريق":5,"افضل ممارسات":4,"توصيات":3,"مخرجات استشارية":5,"دراسة فنية":4,"شركة استشارية":4,"مستشار":3,"برايس وترهاوس":5,"ديلويت":5,"كي بي ام جي":5,"ماكينزي":5},
    "fh":["consulting_","advisory_","deliverable_","assessment_","pwc","deloitte","kpmg","mckinsey"],"ph":["consulting","advisory","engagements"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"06_Strategy_Planning": {
    "pp":"HIGH","personal":False,
    "en":{
        "strategic plan":5,"strategic planning":4,"swot analysis":5,"pestle":5,"balanced scorecard":5,
        "okr":5,"kpi":5,"competitive analysis":4,"market analysis":3,"value chain":4,
        "business model canvas":5,"it strategy":4,"technology strategy":4,"strategic initiative":4,
        "vision 2030":5,"strategic objective":4,
        "performance management":5, "performance measurement":4, "corporate performance":5,
        "performance improvement":4
    },
    "ar":{
        "خطة استراتيجية":5,"تخطيط استراتيجي":5,"تحليل سوات":5,"مؤشرات اداء":5,"مؤشر اداء":4,
        "بطاقة اداء متوازن":5,"تحليل تنافسي":4,"اهداف استراتيجية":4,"رؤية 2030":5,
        "هدف استراتيجي":4,"مبادرة":4,"مبادرات":4,"خطط":3,
        "خطط استراتيجية":5, "ادارة اداء":5, "قياس اداء":4, "تحسين اداء":4, "متابعة اداء":4,
        "اداء مالي":4, "اداء مؤسسي":5
    },
    "fh":["strategy_","strategic_","swot","pestle","vision2030", "performance", "kpi", "okr"],
    "ph":["strategy","strategic_planning", "performance"],
    "neg_en":["story","novel","children","kids", "employee performance", "appraisal"],
    "neg_ar":["قصة","رواية","اطفال", "تقييم موظف", "تقييم الموظفين"],
},
"07_Product_Development": {
    "pp":"HIGH","personal":False,
    "en":{"product development":4,"product roadmap":5,"product strategy":4,"product requirement":5,"minimum viable product":5,"mvp":4,"go-to-market":4,"product-market fit":4,"product launch":5,"product lifecycle":4,"customer journey":4,"user persona":4,"product backlog":4,"ux/ui":3},
    "ar":{"تطوير منتج":4,"خارطة طريق منتج":5,"استراتيجية منتج":4,"اطلاق منتج":4,"دورة حياة منتج":4,"رحلة عميل":4,"منتجات":3,"منتج":3},
    "fh":["product_roadmap","prd_","product_strategy","mvp_"],"ph":["product_development","product_management"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"08_IT_Governance_Compliance": {
    "pp":"MEDIUM","personal":False,
    "en":{
        "it governance":4,"corporate governance":5,"governance report":5,"cobit":5,"itil":4,
        "iso 27001":5,"iso 20000":4,"information security":4,"cybersecurity":4,"data governance":4,
        "business continuity":5,"disaster recovery":5,"isms":4,"nca":5,"compliance":4,"grc":5,
        "board of director":4,"audit committee":4
    },
    "ar":{
        "حوكمة تقنية":5,"حوكمة مؤسسية":5,"حوكمة شركات":5,"حوكمة":4,"تقرير حوكمة":5,
        "امن معلومات":4,"امن سيبراني":5,"استمرارية اعمال":4,"تعافي من كوارث":5,"التزام":4,
        "امتثال":4,"هيئة وطنية للامن السيبراني":5,"سياسة امن":4,"مجلس ادارة":4,"لجنة مراجعة":4,
        "مخاطر ومطابقة":4
    },
    "fh":["governance","cobit","itil","iso27","isms","grc","compliance","حوكمة","الحوكمة"],
    "ph":["governance","compliance","information_security","grc"],
    "neg_en":["story","novel","children","kids"],
    "neg_ar":["قصة","رواية","اطفال"],
},
"09_Proposals_Tenders_RFPs": {
    "pp":"HIGH","personal":False,
    "en":{"request for proposal":5,"rfp":4,"rfq":4,"tender document":5,"bid submission":4,"technical proposal":5,"financial proposal":5,"commercial proposal":5,"scope of work":5,"sow":4,"evaluation criteria":4,"vendor":3},
    "ar":{"كراسة شروط":5,"عرض فني":5,"عرض مالي":5,"مناقصة":4,"مناقصات":4,"عطاء":4,"عطاءات":4,"نطاق عمل":5,"مواصفات فنية":4,"جدول كميات":4,"منافسة":4,"مشتريات":3,"مورد":3,"موردين":3},
    "fh":["proposal_","rfp_","rfq_","tender_","bid_","sow_"],"ph":["proposals","tenders","rfp","bids"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"10_Finance_Budgets": {
    "pp":"MEDIUM","personal":False,
    "en":{
        "budget":4,"financial statement":4,"invoice":5,"cost estimate":4,"revenue forecast":4,
        "profit and loss":4,"balance sheet":4,"cash flow":4,"receipt":5,"purchase order":5,"po":4,
        "payment":5, "settlement":5, "bank transfer":4, "payroll":4,
        "amount due":4, "subtotal":4, "total amount":4, "vat":5, "tax invoice":5, "bill to":4,
        "unit price":3, "remittance":4, "tax":3, "qty":3
    },
    "ar":{
        "ميزانية":4,"موازنة":4,"فاتورة":5,"فواتير":5,"قائمة دخل":4,"تدفق نقدي":4,"بيانات مالية":4,
        "ايصال":5,"ايصالات":5,"امر شراء":5,"اوامر شراء":5,
        "سداد":5, "مذكرة سداد":5, "سند صرف":5, "سند قبض":5, "تحويل مالي":4, "تحويل بنكي":4, 
        "كشف حساب":5, "مطالبة مالية":5, "دفعة":4, "دفعات":4, "مبلغ":3,
        "ضريبة القيمة المضافة":5, "المبلغ المستحق":4, "رقم الفاتورة":5, "فاتورة ضريبية":5,
        "اجمالي المبلغ":4, "الاجمالي":3, "الضريبة":3, "الكمية":3
    },
    "fh":["budget_","financial_","invoice","cost_estimate", "سداد", "payment", "receipt", "transfer", "سند", "inv", "po"],
    "ph":["finance","budget","accounting", "مالية", "حسابات", "invoices", "فواتير"],
    "neg_en":["story","novel","children","kids"],
    "neg_ar":["قصة","رواية","اطفال"],
},
"11_Contracts_Legal": {
    "pp":"LOW","personal":False,
    "en":{"contract":4,"agreement":3,"non-disclosure agreement":5,"nda":4,"term and condition":4,"indemnification":4,"governing law":4,"confidentiality agreement":5,"service level agreement":5,"sla":4,"memorandum of understanding":5,"mou":4},
    "ar":{"عقد":4,"عقود":4,"اتفاقية":4,"اتفاقيات":4,"عدم افشاء":5,"شروط واحكام":4,"سرية معلومات":4,"مستوى خدمة":4,"مذكرة تفاهم":5},
    "fh":["contract_","agreement_","nda_","sla_"],"ph":["legal","contracts"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"12_HR_People": {
    "pp":"LOW","personal":False,
    "en":{"human resource":4,"job description":4,"performance review":4,"onboarding":3,"payroll":4,"salary":3,"recruitment":3,"org chart":4,"timesheet":3,"employee":3},
    "ar":{"موارد بشرية":4,"وصف وظيفي":4,"تقييم اداء":4,"هيكل تنظيمي":4,"سلم رواتب":4,"مسير رواتب":4,"شؤون موظفين":4,"موظف":3,"موظفين":3,"سيرة ذاتية":4},
    "fh":["hr_","employee_","job_desc","payroll_"],"ph":["human_resources","hr"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"13_Reports_Presentations": {
    "pp":"MEDIUM","personal":False,
    "en":{"executive summary":4,"annual report":4,"quarterly report":4,"status report":4,"progress report":3,"dashboard":3,"presentation":3,"slide deck":4},
    "ar":{"تقرير سنوي":4,"تقرير ربع سنوي":4,"ملخص تنفيذي":4,"عرض تقديمي":4,"لوحة متابعة":4,"تقرير":3,"تقارير":3,"عروض":3},
    "fh":["report_","presentation_","dashboard_","deck_"],"ph":["reports","presentations"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"14_Training_Knowledge": {
    "pp":"HIGH","personal":False,
    "en":{"training material":4,"training course":4,"curriculum":3,"e-learning":4,"knowledge transfer":4,"instructional design":4,"workshop":3,"user manual":4,"training deck":4},
    "ar":{"حقيبة تدريبية":5,"مادة تدريبية":4,"دورة تدريبية":4,"نقل معرفة":4,"محتوى تعليمي":4,"دليل مستخدم":4,"ورشة عمل":3,"تدريب":3},
    "fh":["training_","course_","workshop_"],"ph":["training","courses","learning"],
    "neg_en":["story","novel","children","kids","fairy","coloring"],"neg_ar":["قصة","رواية","اطفال","تلوين"],
},
"15_Meeting_Communications": {
    "pp":"LOW","personal":False,
    "en":{"meeting minute":5,"mom":4,"meeting agenda":4,"action item":4,"memorandum":4,"memo":3,"attendee":3},
    "ar":{"محضر اجتماع":5,"محاضر اجتماعات":5,"جدول اعمال":4,"مذكرة":3,"توصيات اجتماع":4},
    "fh":["minutes_","meeting_","memo_","agenda_"],"ph":["meetings","minutes"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"16_LMS_ELearning": {
    "pp":"HIGH","personal":False,
    "en":{"learning management system":5,"scorm":5,"xapi":4,"tin can":4,"moodle":4,"blackboard":4},
    "ar":{"نظام ادارة تعلم":5,"تعلم الكتروني":4,"تصميم تعليمي":4},
    "fh":["lms_","scorm_","elearning_"],"ph":["lms","elearning"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"17_Infrastructure_Technical": {
    "pp":"MEDIUM","personal":False,
    "en":{"server infrastructure":4,"network architecture":4,"cloud computing":4,"aws":3,"azure":3,"kubernetes":3,"docker":3,"devops":4,"database design":4,"datacenter":4,"vmware":3,"cisco":3},
    "ar":{"بنية تحتية":4,"حوسبة سحابية":4,"قاعدة بيانات":4,"قواعد بيانات":4,"مركز بيانات":4,"خادم":3,"خوادم":3,"شبكة":3,"شبكات":3},
    "fh":["infrastructure_","server_","network_","cloud_"],"ph":["infrastructure","technical","devops"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"18_Policies_Procedures": {
    "pp":"MEDIUM","personal":False,
    "en":{"standard operating procedure":5,"sop":4,"policy document":4,"code of conduct":4,"quality management":4,"guideline":3,"process manual":5,"procedure manual":5},
    "ar":{"اجراءات تشغيل":4,"سياسة":3,"سياسات":3,"دليل ارشادي":4,"دليل عمل":4,"لائحة تنظيمية":4,"لوائح":4,"دليل اجراءات":5,"نماذج عمل":3},
    "fh":["policy_","procedure_","sop_","guideline_","manual"],"ph":["policies","procedures"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"19_Personal_Books": {
    "pp":"NONE","personal":True,
    "en":{"once upon a time":5,"fairy tale":5,"bedtime story":5,"chapter one":4,"novel":4,"fiction":3,"isbn":5,"published by":4,"author":3,"story":3,"tale":3,"happily ever after":5},
    "ar":{"رواية":4,"روايات":4,"قصة":4,"قصص":4,"كان يا مكان":5,"كان ياما كان":5,"كتاب":3,"كتب":3,"ادب":3,"شعر":3,"ديوان":4,"دار نشر":5,"مؤلف":3,"طبعة":4},
    "fh":["book","novel","story","ebook","reader","tales","كتاب","رواية","قصة","موسيقي","موسيقى","الات","منازل","ديكور"],
    "ph":["books","novels","ebooks","stories","reading","كتب","روايات","قصص"],
    "neg_en":[],"neg_ar":[],
},
"20_Kids_Activities": {
    "pp":"NONE","personal":True,
    "en":{
        "for kid":5,"for child":5,"coloring":4,"worksheet":4,"homework":4,
        "kindergarten":5,"preschool":5,"activity book":5,"phonics":4,"alphabet":4,
        "science experiment":5
    },
    "ar":{
        "طفل":4,"اطفال":4,"قصص اطفال":5,"انشطة":4,"تلوين":4,"مدرسة":3,"حضانة":5,
        "روضة":5,"رياض اطفال":5,"تعليم اطفال":5,"تجارب علمية":5,"تجربة علمية":5,
        "تجارب":4,"تجربة":4,"وحدة الماء":5,"وحدة الرمل":5,"وحدة الغذاء":5,
        "وحدة المسكن":5,"وحدة تعليمية":5,"السمك والماء":4,"طبخ":3,"نظافة":3,
        "حيوانات":4, "نباتات":4, "سكان العالم":4, "معالم سياحية":4, "مناظر طبيعية":4,
        "كائنات حية":5, "كائنات":4, "حروف":5, "الحروف":5, "كلمات":4, "املاء":5, "إملاء":5, "تهجئة":4
    },
    "fh":[
        "kids","children","child","activity","coloring","worksheet","school","kindergarten",
        "اطفال","انشطة","تلوين","وحدة","تجارب","تجربة","روضة","حيوانات","نباتات",
        "سكان","معالم","سياحيه","سياحية","مناظر","طبيعيه","طبيعية","عالم",
        "كائنات", "حروف", "كلمات", "املاء", "إملاء"
    ],
    "ph":["kids","children","school","activities","nursery","kindergarten",
          "اطفال","مدرسة","روضة","وحدات"],
    "neg_en":[],"neg_ar":[],
},
"21_Personal_Documents": {
    "pp":"NONE","personal":True,
    "en":{
        "curriculum vitae":5,"resume":4,"passport":5,"birth certificate":5,"marriage certificate":5,
        "insurance policy":4,"medical record":4,"visa application":4,"driver license":4,"national id":5,
        "school application":4,"admission form":4,"student record":4
    },
    "ar":{
        "سيرة ذاتية":5,"جواز سفر":5,"جوازات":4,"شهادة ميلاد":5,"شهادة زواج":5,"تأمين":3,"تأشيرة":4,
        "هوية وطنية":5,"اقامة":4,"رخصة قيادة":4,
        "ابناؤنا في الخارج":5,"أبناؤنا في الخارج":5,"استمارة طلب":4,"طلب تسجيل":4,"قبول طالب":4,
        "طالب":4,"طلاب":4,"شهادة مدرسية":4,"وزارة التربية والتعليم":4,"بوابة الكترونية":2,"طلب":3
    },
    "fh":["cv","resume","personal","passport","certificate","سيرة","جواز","شخصي","ابناؤنا","طالب","تسجيل","استمارة"],
    "ph":["personal","private","family","شخصي","عائلي","وثائق","ابناء","مدارس"],
    "neg_en":[],"neg_ar":[],
},
"22_Templates_Reusable": {
    "pp":"VERY_HIGH","personal":False,
    "en":{"template":4,"boilerplate":4,"toolkit":4,"checklist":4,"reusable":3,"blank form":4},
    "ar":{
        "قالب":4,"قوالب":4,"نموذج جاهز":5,"نماذج":3,"حقيبة ادوات":4,"قائمة مراجعة":4, 
        "قوائم":4, "لوحات":4, "وردي":3, "تصميم":3
    },
    "fh":["template_","tmpl_","toolkit_","checklist_", "قوائم", "لوحات", "وردي"],
    "ph":["templates","toolkits"],
    "neg_en":["story","novel","children","kids"],
    "neg_ar":["قصة","رواية","اطفال"],
},
"23_Diagrams_Visuals": {
    "pp":"MEDIUM","personal":False,
    "en":{"diagram":3,"flowchart":4,"uml":4,"sequence diagram":4,"network diagram":4,"architecture diagram":4,"mind map":4},
    "ar":{"رسم توضيحي":4,"مخطط انسيابي":5,"مخططات":3,"مخطط":3,"خريطة ذهنية":4},
    "fh":["diagram_","flowchart_","uml_"],"ph":["diagrams","visuals"],
    "neg_en":["story","novel","children","kids"],"neg_ar":["قصة","رواية","اطفال"],
},
"24_Software_Development_Code": {
    "pp":"LOW","personal":False,
    "en":{
        "source code":5,"repository":4,"git":5,"github":5,"pull request":4,
        "code review":4,"api documentation":4,"readme":4,"changelog":4,
        "python":4,"javascript":4,"html":4,"css":4,"sql":4,"script":4
    },
    "ar":{
        "كود مصدري":5,"مستودع كود":5,"برمجة":4,"تطوير برمجيات":5,
        "قاعدة بيانات":4,"خوارزمية":4,"سكربت":4
    },
    "fh":[
        ".py", ".bat", ".iss", ".md", ".json", ".xml", ".js", ".html", ".css", 
        ".sql", ".sh", ".spec", "readme", "setup", "build", "installer", 
        "config", "requirements", "app"
    ],
    "ph":["src","code","repos","scripts","github","development","env","lib"],
    "neg_en":["story","novel"],
    "neg_ar":["قصة","رواية"],
},
}

# ═══════════════════════════════════════════════
#  JOB ROLE PRESETS
# ═══════════════════════════════════════════════
#  Each preset is a list of category keys from _DEFAULTS
#  + any extra role-specific categories

_COMMON_PERSONAL = ["19_Personal_Books","20_Kids_Activities","21_Personal_Documents"]
_COMMON_BUSINESS = ["00_General_Administration","06_Strategy_Planning","10_Finance_Budgets","11_Contracts_Legal",
                    "12_HR_People","13_Reports_Presentations","15_Meeting_Communications",
                    "18_Policies_Procedures","22_Templates_Reusable","24_Software_Development_Code"]


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
                "en":{"source code":4,"repository":4,"git":4,"github":4,"pull request":4,"code review":4,"api documentation":4,"readme":3,"changelog":3},
                "ar":{"كود مصدري":4,"مستودع":3,"مستودعات":3},
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
                "en":{"marketing campaign":5,"brand guideline":5,"social media":4,"content calendar":4,"seo":3,"google analytic":4,"email marketing":4,"press release":4,"media kit":4,"target audience":4,"brand identity":4,"advertising":4,"conversion rate":4,"marketing funnel":4},
                "ar":{"حملة تسويقية":5,"حملات تسويقية":5,"هوية بصرية":4,"وسائل تواصل":4,"تسويق رقمي":4,"اعلان":4,"اعلانات":4,"جمهور مستهدف":4},
                "fh":["campaign_","marketing_","brand_","social_"],"ph":["marketing","campaigns","brand"],
                "neg_en":[],"neg_ar":[],
            },
            "Design_Creative": {
                "pp":"MEDIUM","personal":False,
                "en":{"design brief":4,"creative brief":4,"mockup":4,"wireframe":4,"brand book":4,"style guide":4,"logo":3,"typography":3,"color palette":3},
                "ar":{"تصميم":3,"تصاميم":3,"هوية بصرية":4,"شعار":3,"شعارات":3,"دليل هوية":4},
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
                "en":{"general ledger":5,"journal entry":5,"account payable":5,"account receivable":5,"trial balance":5,"chart of account":5,"depreciation":4,"tax return":5,"vat":4,"audit report":5,"reconciliation":4,"fiscal year":3},
                "ar":{"دفتر استاذ":5,"قيد يومية":5,"قيود يومية":5,"ذمم دائنة":5,"ذمم مدينة":5,"ميزان مراجعة":5,"شجرة حسابات":5,"اهلاك":4,"ضريبة":4,"ضرائب":4,"تقرير مراجعة":5},
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
                "ar":{"اعلان وظيفي":4,"مقابلة":3,"مقابلات":3,"عرض وظيفي":5,"عروض وظيفية":5,"عقد عمل":5,"عقود عمل":5,"تقييم مرشح":4,"هيكل تنظيمي":4,"خطة تعاقب":4,"اطار كفاءات":5},
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
                "en":{"lesson plan":5,"unit plan":4,"learning objective":4,"assessment rubric":5,"curriculum map":5,"differentiation":3,"classroom management":4,"student assessment":4,"grading":3,"syllabus":4,"semester plan":4},
                "ar":{"خطة درس":5,"خطط دروس":5,"خطة وحدة":4,"اهداف تعليمية":4,"معايير تقييم":5,"منهج":3,"مناهج":3,"تقييم طلاب":4,"فصل دراسي":3},
                "fh":["lesson_","syllabus_","rubric_","curriculum_"],"ph":["lessons","curriculum","teaching"],
                "neg_en":[],"neg_ar":[],
            },
            "Student_Records": {
                "pp":"NONE","personal":False,
                "en":{"student record":4,"transcript":4,"grade report":4,"attendance":4,"parent communication":4,"iep":4,"report card":4},
                "ar":{"سجل طالب":4,"سجلات طلاب":4,"كشف درجات":4,"حضور وغياب":4,"تقرير اداء":3,"ولي امر":3},
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
                "ar":{"ملف قضية":5,"مذكرة قانونية":5,"دعوى":4,"دعاوي":4,"حكم":3,"احكام":3,"تسوية":4,"شهادة":3,"رأي قانوني":5,"نظام":3,"انظمة":3,"لائحة":3,"لوائح":3},
                "fh":["case_","legal_","court_","litigation_"],"ph":["cases","litigation","court","legal"],
                "neg_en":[],"neg_ar":[],
            },
            "Legal_Research": {
                "pp":"MEDIUM","personal":False,
                "en":{"legal research":4,"case law":4,"regulatory analysis":4,"compliance review":4,"legal memorandum":5,"due diligence":5,"intellectual property":4},
                "ar":{"بحث قانوني":4,"تحليل تنظيمي":4,"عناية واجبة":5,"ملكية فكرية":4},
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
                "en":{"photo":3,"picture":3,"image":3,"video":3,"screenshot":4,"wallpaper":3},
                "ar":{"صورة":3,"صور":3,"فيديو":3,"لقطة شاشة":4},
                "fh":["photo","img_","screenshot","pic_"],"ph":["photos","pictures","media","صور"],
                "neg_en":[],"neg_ar":[],
            },
            "Recipes_Home": {
                "pp":"NONE","personal":True,
                "en":{"recipe":4,"ingredient":3,"cooking":4,"baking":4,"tablespoon":3,"teaspoon":3,"preheat":4,"serving":3},
                "ar":{"وصفة":4,"وصفات":4,"مقادير":3,"طبخ":4,"خبز":4,"ملعقة":3},
                "fh":["recipe_","cooking_","اكلات","أكلات","طبخ","طعام","مطبخ"],
                "ph":["recipes","cooking","kitchen","وصفات","طبخ"],
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
                "en":{"abstract":4,"literature review":5,"methodology":4,"hypothesis":4,"finding":3,"peer review":5,"journal":4,"publication":4,"citation":4,"reference":3,"doi":4,"research paper":5,"thesis":5,"dissertation":5,"conference paper":5,"systematic review":5,"meta-analysis":5,"research proposal":5,"bibliography":4,"appendix":3,"acknowledgment":3},
                "ar":{"ملخص بحث":5,"مراجعة ادبيات":5,"منهجية بحث":5,"فرضية":4,"فرضيات":4,"نتائج بحث":4,"مجلة علمية":4,"رسالة ماجستير":5,"رسالة دكتوراه":5,"اطروحة":5,"بحث علمي":5,"ابحاث علمية":5,"مؤتمر":3,"مؤتمرات":3,"مرجع":3,"مراجع":3,"اقتباس":3,"اقتباسات":3,"خطة بحثية":5},
                "fh":["paper_","thesis_","research_","dissertation_","journal_"],"ph":["research","papers","thesis","academic","بحث","رسالة","اطروحة"],
                "neg_en":["story","novel","kids","coloring"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Academic_Teaching": {
                "pp":"HIGH","personal":False,
                "en":{"lecture note":5,"course syllabus":5,"exam paper":5,"quiz":4,"assignment":4,"grading rubric":4,"academic calendar":4,"office hour":3,"tutorial":3,"seminar":4,"lab report":4,"field study":4},
                "ar":{"محاضرة":4,"محاضرات":4,"منهج دراسي":5,"امتحان":4,"امتحانات":4,"اختبار":4,"اختبارات":4,"واجب":4,"واجبات":4,"معايير تصحيح":4,"تقويم اكاديمي":4,"تقرير مختبر":4,"دراسة ميدانية":4,"حلقة بحث":4},
                "fh":["lecture_","exam_","syllabus_","course_","lab_"],"ph":["lectures","exams","courses","academic","محاضرات","امتحانات"],
                "neg_en":[],"neg_ar":[],
            },
            "Grants_Funding": {
                "pp":"HIGH","personal":False,
                "en":{"grant proposal":5,"funding application":5,"research grant":5,"budget justification":4,"principal investigator":4,"co-investigator":4,"grant report":4,"progress report":3,"impact factor":4,"h-index":3},
                "ar":{"منحة بحثية":5,"منح بحثية":5,"طلب تمويل":5,"ميزانية بحث":4,"باحث رئيسي":4,"تقرير منحة":4},
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
                "en":{"audiovisual":5,"av system":5,"av design":5,"display system":4,"projector":4,"sound system":5,"audio system":5,"video conferencing":5,"digital signage":5,"control system":5,"crestron":5,"extron":5,"biamp":5,"qsc":5,"shure":5,"dante":5,"hdmi":4,"av matrix":4,"av rack":4,"signal flow":4,"av integration":5},
                "ar":{"نظام سمعي بصري":5,"انظمة سمعية بصرية":5,"تصميم صوتي":4,"نظام عرض":4,"مؤتمرات فيديو":5,"لافتات رقمية":4,"نظام تحكم":4,"تكامل سمعي بصري":5,"نظام صوت":4},
                "fh":["av_","audiovisual_","sound_","display_","projector_"],"ph":["av","audiovisual","av_systems","سمعي_بصري"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "AV_Specs_BOQ": {
                "pp":"HIGH","personal":False,
                "en":{"bill of quantity":5,"boq":5,"av specification":5,"technical specification":4,"equipment list":4,"rack elevation":4,"cable schedule":4,"commissioning":4,"as-built":4,"riser diagram":4,"av tender":4},
                "ar":{"جدول كميات":5,"مواصفات فنية":5,"قائمة معدات":4,"جدول كابلات":4,"تشغيل وتسليم":4,"مخطط رايزر":4},
                "fh":["boq_","spec_","equipment_","cable_","commissioning_"],"ph":["specifications","boq","equipment"],
                "neg_en":[],"neg_ar":[],
            },
            "Events_Venues": {
                "pp":"MEDIUM","personal":False,
                "en":{"event setup":4,"venue":4,"stage design":4,"lighting design":4,"live streaming":4,"broadcast":4,"led wall":4,"rigging":4,"stage plot":4,"event production":4,"technical rider":5},
                "ar":{"تجهيز فعالية":4,"تصميم مسرح":4,"اضاءة":3,"بث مباشر":4,"انتاج فعاليات":4,"متطلبات فنية":4,"فعالية":4,"فعاليات":4},
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
                "ar":{"تقويم محتوى":5,"خطة محتوى":5,"استراتيجية محتوى":5,"جدول نشر":4,"اعمدة محتوى":4,"محتوى دائم":4,"محتوى":3},
                "fh":["content_","editorial_","calendar_","posting_"],"ph":["content","editorial","planning","محتوى"],
                "neg_en":["story","novel","isbn"],"neg_ar":["رواية","قصة"],
            },
            "Scripts_Storyboards": {
                "pp":"HIGH","personal":False,
                "en":{"script":4,"storyboard":5,"shot list":4,"video script":5,"podcast script":4,"voiceover":4,"thumbnail":4,"intro":3,"outro":3,"call to action":4,"hook":3,"b-roll":4,"talking head":3},
                "ar":{"سكربت":4,"نص فيديو":5,"لوحة قصة":5,"قائمة لقطات":4,"تعليق صوتي":4,"صورة مصغرة":4,"مقدمة":3},
                "fh":["script_","storyboard_","video_","podcast_"],"ph":["scripts","storyboards","videos","podcasts"],
                "neg_en":[],"neg_ar":[],
            },
            "Analytics_Growth": {
                "pp":"MEDIUM","personal":False,
                "en":{"analytics report":4,"engagement rate":4,"subscriber":4,"follower":4,"impression":3,"reach":3,"click-through rate":4,"ctr":4,"monetization":4,"sponsorship":4,"brand deal":4,"media kit":5,"rate card":4},
                "ar":{"تقرير تحليلات":4,"معدل تفاعل":4,"مشترك":4,"مشتركين":4,"متابع":4,"متابعين":4,"رعاية":4,"شراكة":4,"بطاقة اسعار":4},
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
                "en":{"sales pipeline":5,"crm":4,"lead generation":4,"prospecting":4,"sales funnel":5,"qualified lead":4,"opportunity":4,"deal":4,"close rate":4,"win rate":4,"cold call":4,"follow up":3,"sales forecast":4,"quota":3,"territory":3,"account management":4},
                "ar":{"خط مبيعات":5,"توليد عملاء":4,"فرصة بيع":4,"معدل اغلاق":4,"ادارة حسابات":4,"عميل محتمل":4,"متابعة":3,"حصة مبيعات":4,"مبيعات":4},
                "fh":["sales_","pipeline_","lead_","crm_","deal_"],"ph":["sales","pipeline","leads","crm","مبيعات"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Client_Presentations": {
                "pp":"HIGH","personal":False,
                "en":{"client presentation":5,"pitch deck":5,"demo":4,"product demo":4,"case study":4,"testimonial":4,"reference":3,"competitive positioning":4,"value proposition":5,"pricing proposal":4},
                "ar":{"عرض عميل":5,"عرض تقديمي":3,"دراسة حالة":4,"شهادة عميل":4,"عرض قيمة":5,"عرض تسعير":4},
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
                "en":{"user research":5,"usability test":5,"user interview":4,"persona":4,"user journey":5,"empathy map":5,"affinity diagram":4,"card sorting":4,"heuristic evaluation":5,"accessibility audit":4,"ux audit":5,"competitive analysis":4,"user flow":4,"information architecture":4},
                "ar":{"بحث مستخدم":5,"اختبار قابلية استخدام":5,"مقابلة مستخدم":4,"شخصية مستخدم":4,"رحلة مستخدم":5,"خريطة تعاطف":5,"تدقيق تجربة مستخدم":5},
                "fh":["ux_","usability_","persona_","journey_"],"ph":["ux","research","usability","تجربة_مستخدم"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "UI_Design_Assets": {
                "pp":"HIGH","personal":False,
                "en":{"design system":5,"component library":5,"style guide":4,"wireframe":5,"mockup":4,"prototype":4,"ui kit":4,"icon set":4,"figma":4,"sketch":4,"design token":4,"responsive design":4,"mobile design":4},
                "ar":{"نظام تصميم":5,"مكتبة مكونات":5,"دليل تصميم":4,"تصميم اولي":4,"نموذج تفاعلي":4,"تصميم متجاوب":4},
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
                "en":{"data analysis":5,"exploratory data":4,"statistical analysis":5,"regression":4,"correlation":4,"data visualization":5,"dashboard":4,"data cleaning":4,"etl":4,"data pipeline":4,"sql query":4,"python notebook":4,"jupyter":4,"pandas":4,"data model":4,"data dictionary":4,"data catalog":4},
                "ar":{"تحليل بيانات":5,"تحليل احصائي":5,"تصور بيانات":5,"لوحة بيانات":4,"تنظيف بيانات":4,"نموذج بيانات":4,"قاموس بيانات":4},
                "fh":["data_","analysis_","dashboard_","query_","notebook_"],"ph":["data","analysis","notebooks","analytics","بيانات","تحليل"],
                "neg_en":["story","novel","kids"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "ML_AI_Models": {
                "pp":"HIGH","personal":False,
                "en":{"machine learning":5,"deep learning":5,"neural network":4,"model training":4,"model evaluation":4,"feature engineering":4,"hyperparameter":4,"classification":4,"clustering":4,"natural language processing":5,"nlp":4,"computer vision":4,"reinforcement learning":4,"transfer learning":4,"mlops":4},
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
                "en":{"patient":4,"diagnosis":4,"treatment plan":5,"clinical trial":5,"medical report":5,"lab result":4,"radiology":4,"pathology":4,"prescription":4,"medical history":4,"discharge summary":4,"referral":4,"ehr":4,"icd":4,"cpt":4,"medical protocol":4},
                "ar":{"مريض":4,"مرضى":4,"تشخيص":4,"خطة علاج":5,"تقرير طبي":5,"تقارير طبية":5,"نتيجة مختبر":4,"نتائج مختبر":4,"اشعة":4,"وصفة طبية":4,"تاريخ مرضي":4,"ملخص خروج":4,"تحويل":3,"بروتوكول طبي":4},
                "fh":["patient_","clinical_","medical_","lab_","diagnosis_"],"ph":["medical","clinical","patients","hospital","طبي","عيادة"],
                "neg_en":["story","novel","kids","coloring"],"neg_ar":["قصة","رواية","اطفال"],
            },
            "Healthcare_Admin": {
                "pp":"MEDIUM","personal":False,
                "en":{"hospital policy":4,"accreditation":4,"jci":5,"cbahi":5,"quality improvement":4,"patient safety":4,"infection control":4,"clinical pathway":4,"formulary":4,"credentialing":4},
                "ar":{"سياسة مستشفى":4,"اعتماد":4,"تحسين جودة":4,"سلامة مرضى":4,"مكافحة عدوى":4,"مسار سريري":4,"اعتماد طبي":4,"سباهي":5},
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
                "en":{"lease agreement":5,"tenancy contract":5,"property valuation":5,"rent":4,"landlord":4,"tenant":4,"property inspection":4,"maintenance request":4,"occupancy rate":4,"property listing":4,"real estate":4,"title deed":5,"mortgage":4,"escrow":4},
                "ar":{"عقد ايجار":5,"عقود ايجار":5,"تقييم عقاري":5,"مالك":4,"مستأجر":4,"مستأجرين":4,"فحص عقار":4,"طلب صيانة":4,"صك ملكية":5,"صكوك ملكية":5,"رهن عقاري":4,"عقارات":4,"عقار":4,"ايجار":4},
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
                "en":{"standard operating procedure":5,"sop":4,"process improvement":4,"lean":4,"six sigma":4,"kaizen":4,"supply chain":5,"inventory":4,"logistic":4,"warehouse":4,"procurement":4,"vendor management":4,"kpi dashboard":4,"operational excellence":4},
                "ar":{"اجراءات تشغيل":5,"تحسين عمليات":4,"سلسلة امداد":5,"مخزون":4,"لوجستيات":4,"مشتريات":4,"ادارة موردين":4,"تميز تشغيلي":4,"عمليات":4},
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
    ".doc":   {"group":"documents",  "label_en":"Word 97-2003",          "label_ar":"وورد قديم",             "needs_ocr":False},
    ".rtf":   {"group":"documents",  "label_en":"Rich Text Format",      "label_ar":"نص منسق RTF",         "needs_ocr":False},
    ".odt":   {"group":"documents",  "label_en":"OpenDocument Text",     "label_ar":"مستند OpenDocument",   "needs_ocr":False},
    ".txt":   {"group":"documents",  "label_en":"Plain Text",            "label_ar":"نص عادي",               "needs_ocr":False},
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
    "pdf":           {"icon":"📕","label_en":"PDFs",            "label_ar":"ملفات PDF"},
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