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

