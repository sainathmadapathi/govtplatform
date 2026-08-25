import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

os.makedirs('public/resources', exist_ok=True)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontSize=18,
    leading=22,
    alignment=TA_CENTER,
    textColor=colors.HexColor('#1e3a8a'),
    spaceAfter=12
)

subtitle_style = ParagraphStyle(
    'DocSubTitle',
    parent=styles['Normal'],
    fontSize=11,
    leading=14,
    alignment=TA_CENTER,
    textColor=colors.HexColor('#4b5563'),
    spaceAfter=18
)

h2_style = ParagraphStyle(
    'H2Style',
    parent=styles['Heading2'],
    fontSize=13,
    leading=16,
    textColor=colors.HexColor('#1e40af'),
    spaceBefore=12,
    spaceAfter=6
)

body_style = ParagraphStyle(
    'BodyStyle',
    parent=styles['Normal'],
    fontSize=9.5,
    leading=13.5,
    alignment=TA_JUSTIFY,
    textColor=colors.HexColor('#1f2937'),
    spaceAfter=8
)

bullet_style = ParagraphStyle(
    'BulletStyle',
    parent=styles['Normal'],
    fontSize=9,
    leading=13,
    leftIndent=12,
    textColor=colors.HexColor('#374151'),
    spaceAfter=4
)

# 1. SSC CGL 2026 Official Gazette Notice
def generate_ssc_notice():
    doc = SimpleDocTemplate("public/resources/SSC_CGL_2026_Official_Gazette_Notice.pdf", pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    story.append(Paragraph("GOVERNMENT OF INDIA", title_style))
    story.append(Paragraph("STAFF SELECTION COMMISSION<br/>Block No. 12, CGO Complex, Lodhi Road, New Delhi – 110003", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceAfter=14))
    
    story.append(Paragraph("<b>COMBINED GRADUATE LEVEL EXAMINATION, 2026 (SSC CGL 2026)</b>", ParagraphStyle('BTitle', parent=title_style, fontSize=14, leading=16)))
    story.append(Paragraph("<b>F. No. HQ-PPI03/15/2026-PP_1</b> | Date of Notice: 10-08-2026", subtitle_style))
    
    dates_data = [
        [Paragraph("<b>Event / Milestone</b>", body_style), Paragraph("<b>Crucial Official Date</b>", body_style)],
        ["Date for submission of online applications", "10-08-2026 to 27-09-2026 (23:59 IST)"],
        ["Last date and time for making online fee payment", "28-09-2026 (23:59 IST)"],
        ["Window for Application Form Correction", "01-10-2026 to 03-10-2026 (23:59 IST)"],
        ["Crucial Date for Reckoning of Age Limits", "01-08-2026"],
        ["Schedule of Tier-I Examination (CBE)", "November 2026"],
        ["Schedule of Tier-II Examination (CBE)", "February 2027"]
    ]
    t = Table(dates_data, colWidths=[280, 240])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d5db')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))
    
    story.append(Paragraph("1. SCHEME OF TIER-1 EXAMINATION (SECTION 13.1)", h2_style))
    story.append(Paragraph("Tier-I will consist of Objective Type, Multiple choice questions only. The questions will be set both in English & Hindi except for English Comprehension. There will be negative marking of 0.50 for each wrong answer.", body_style))
    
    tier1_table = [
        ["Part", "Subject", "Number of Questions", "Maximum Marks", "Total Time Allowed"],
        ["A", "General Intelligence and Reasoning", "25", "50", "60 Minutes (80 Minutes for scribe candidates)"],
        ["B", "General Awareness", "25", "50", ""],
        ["C", "Quantitative Aptitude", "25", "50", ""],
        ["D", "English Comprehension", "25", "50", ""]
    ]
    t1 = Table(tier1_table, colWidths=[35, 200, 110, 85, 90])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e5e7eb')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#9ca3af')),
        ('SPAN', (4, 1), (4, 4)),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (4, 1), (4, 4), 'MIDDLE'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t1)
    story.append(Spacer(1, 14))
    
    story.append(Paragraph("2. SCHEME OF TIER-2 EXAMINATION (SECTION 13.2)", h2_style))
    story.append(Paragraph("Paper-I is compulsory for all posts. Paper-I will be conducted in two sessions – Session-I & Session-II on the same day. Section-III Module-I (Computer Knowledge) and Module-II (DEST Typing - 2000 Key Depressions in 15 Minutes) are mandatory and qualifying in nature.", body_style))
    
    doc.build(story)

# 2. Constitution of India Official Bare Act Key Articles
def generate_constitution_doc():
    doc = SimpleDocTemplate("public/resources/Constitution_of_India_Bare_Act_Key_Articles.pdf", pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    story.append(Paragraph("THE CONSTITUTION OF INDIA", title_style))
    story.append(Paragraph("Legislative Department, Ministry of Law and Justice, Government of India<br/>Official Reference Text for SSC CGL General Awareness", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceAfter=14))
    
    story.append(Paragraph("PART III — FUNDAMENTAL RIGHTS (ARTICLES 12 TO 35)", h2_style))
    
    rights = [
        ("Article 14 — Equality before law", "The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India."),
        ("Article 15 — Prohibition of discrimination", "The State shall not discriminate against any citizen on grounds only of religion, race, caste, sex, place of birth or any of them."),
        ("Article 16 — Equality of opportunity in public employment", "There shall be equality of opportunity for all citizens in matters relating to employment or appointment to any office under the State."),
        ("Article 17 — Abolition of Untouchability", "'Untouchability' is abolished and its practice in any form is forbidden. The enforcement of any disability arising out of 'Untouchability' shall be an offence punishable in accordance with law."),
        ("Article 19 — Protection of certain rights regarding freedom of speech, etc.", "All citizens shall have the right to freedom of speech and expression; to assemble peaceably and without arms; to form associations or unions; to move freely throughout the territory of India; to reside and settle in any part of the territory of India; and to practise any profession, or to carry on any occupation, trade or business."),
        ("Article 21 — Protection of life and personal liberty", "No person shall be deprived of his life or personal liberty except according to procedure established by law."),
        ("Article 21A — Right to education", "The State shall provide free and compulsory education to all children of the age of six to fourteen years in such manner as the State may, by law, determine. [Inserted by the Constitution (Eighty-sixth Amendment) Act, 2002]"),
        ("Article 32 — Remedies for enforcement of rights conferred by this Part", "The right to move the Supreme Court by appropriate proceedings for the enforcement of the rights conferred by this Part is guaranteed. The Supreme Court shall have power to issue directions or orders or writs, including writs in the nature of habeas corpus, mandamus, prohibition, quo warranto and certiorari.")
    ]
    
    for title, desc in rights:
        story.append(Paragraph(f"<b>{title}</b>", ParagraphStyle('ArtTitle', parent=body_style, textColor=colors.HexColor('#1e3a8a'))))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 4))
        
    doc.build(story)

# 3. SSC CGL Tier 1 Official PYQ Shift Paper
def generate_pyq_paper():
    doc = SimpleDocTemplate("public/resources/SSC_CGL_Tier1_Official_Previous_Year_Paper.pdf", pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    story.append(Paragraph("STAFF SELECTION COMMISSION", title_style))
    story.append(Paragraph("Combined Graduate Level Examination (Tier-I) — Official Shift Question Paper<br/>Subject: All 4 Sections (Quantitative Aptitude, English, Reasoning, General Awareness)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceAfter=14))
    
    story.append(Paragraph("SECTION 1: QUANTITATIVE APTITUDE", h2_style))
    story.append(Paragraph("<b>Q1.</b> If x + (1/x) = 4, where x > 0, find the value of x⁴ + (1/x⁴).<br/>(a) 194 &nbsp;&nbsp;&nbsp;&nbsp; (b) 196 &nbsp;&nbsp;&nbsp;&nbsp; (c) 142 &nbsp;&nbsp;&nbsp;&nbsp; (d) 144<br/><b>Answer: (a) 194</b><br/><i>Solution: x² + 1/x² = 4² - 2 = 14. Then x⁴ + 1/x⁴ = 14² - 2 = 196 - 2 = 194.</i>", body_style))
    story.append(Spacer(1, 6))
    
    story.append(Paragraph("<b>Q2.</b> A shopkeeper marks an article 40% above CP and allows 20% discount on MP. If he gives an additional cash discount of 5%, what is the net profit on an article of CP ₹1,500?<br/>(a) ₹96 &nbsp;&nbsp;&nbsp;&nbsp; (b) ₹144 &nbsp;&nbsp;&nbsp;&nbsp; (c) ₹180 &nbsp;&nbsp;&nbsp;&nbsp; (d) ₹72<br/><b>Answer: (a) ₹96</b><br/><i>Solution: MP = 1500 × 1.4 = 2100. After 20% discount = 1680. After 5% cash discount = 1680 × 0.95 = 1596. Profit = 1596 - 1500 = ₹96.</i>", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("SECTION 2: GENERAL INTELLIGENCE & REASONING", h2_style))
    story.append(Paragraph("<b>Q3.</b> Statements: (1) All computers are laptops. (2) Some laptops are tablets. (3) No tablet is a smartphone.<br/>Conclusions: I. Some computers are tablets. II. No smartphone is a tablet. III. Some laptops are not smartphones.<br/>(a) Only II and III follow &nbsp;&nbsp;&nbsp;&nbsp; (b) Only II follows &nbsp;&nbsp;&nbsp;&nbsp; (c) All follow &nbsp;&nbsp;&nbsp;&nbsp; (d) Only I follows<br/><b>Answer: (a) Only II and III follow</b>", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("SECTION 3: GENERAL AWARENESS", h2_style))
    story.append(Paragraph("<b>Q4.</b> Which Article of the Constitution of India provides that the law declared by the Supreme Court shall be binding on all courts within the territory of India?<br/>(a) Article 141 &nbsp;&nbsp;&nbsp;&nbsp; (b) Article 142 &nbsp;&nbsp;&nbsp;&nbsp; (c) Article 136 &nbsp;&nbsp;&nbsp;&nbsp; (d) Article 124<br/><b>Answer: (a) Article 141</b>", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("SECTION 4: ENGLISH COMPREHENSION", h2_style))
    story.append(Paragraph("<b>Q5.</b> Identify the grammatical error: 'Neither the team captain (A) / nor the members of the committee (B) / was present at the annual prize distribution ceremony (C) / yesterday evening (D).'<br/>(a) was present &nbsp;&nbsp;&nbsp;&nbsp; (b) Neither the team &nbsp;&nbsp;&nbsp;&nbsp; (c) nor the members &nbsp;&nbsp;&nbsp;&nbsp; (d) yesterday evening<br/><b>Answer: (a) was present (Rule: nearer subject 'members' is plural, hence 'were present')</b>", body_style))
    
    doc.build(story)

# 4. SSC DEST Typing Test Guidelines & Sample Passage
def generate_dest_doc():
    doc = SimpleDocTemplate("public/resources/SSC_DEST_Typing_Speed_Test_Passage.pdf", pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    story.append(Paragraph("STAFF SELECTION COMMISSION", title_style))
    story.append(Paragraph("Data Entry Speed Test (DEST) — Official Instructions & Sample Typing Passage<br/>Speed Standard: 2000 Key Depressions in 15 Minutes (~27 WPM)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceAfter=14))
    
    story.append(Paragraph("OFFICIAL TYPING TEST GUIDELINES (TIER-2 SECTION III MODULE 2)", h2_style))
    story.append(Paragraph("1. DEST will be conducted for a duration of 15 minutes. A master text passage of about 2000 key depressions will be given on the screen.<br/>2. Candidates will be provided a backspace key to rectify typing errors within the given 15 minutes.<br/>3. Qualifying Standard: Maximum permissible error percentage is 5% for General (UR), 7% for OBC/EWS, and 10% for SC/ST/PwBD candidates.", body_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("SAMPLE PRACTICE TYPING PASSAGE (2000 CHARACTERS)", h2_style))
    passage = (
        "India has witnessed remarkable transformation across its economic and technological landscape over the past two decades. "
        "The digital revolution has empowered citizens across urban and rural regions alike, providing seamless access to essential governance services, "
        "banking facilities, educational resources, and healthcare consultation. Direct Benefit Transfer schemes have eliminated middlemen and leakages, "
        "ensuring that every rupee allocated for public welfare reaches the bank accounts of intended beneficiaries transparently. "
        "In the sphere of infrastructure development, the rapid expansion of modern highway networks, dedicated freight corridors, high-speed rail systems, "
        "and world-class airports has dramatically reduced logistical bottlenecks and lowered transportation costs for domestic manufacturing units. "
        "The startup ecosystem in India has emerged as the third largest globally, generating millions of skilled employment opportunities in software engineering, "
        "artificial intelligence, renewable energy, and digital commerce. Sustainable environmental stewardship has also taken center stage, "
        "with massive investments in solar and wind power generation positioning the country as a global pioneer in clean energy transition. "
        "As India marches steadily toward becoming a developed nation, the combined synergy of democratic governance, demographic dividend, "
        "and institutional transparency remains the cornerstone of its unprecedented socioeconomic trajectory."
    )
    story.append(Paragraph(passage, body_style))
    doc.build(story)

# 5. NCERT Class 10 Mathematics Core Formula Reference
def generate_ncert_math_doc():
    doc = SimpleDocTemplate("public/resources/NCERT_Class10_Mathematics_Exemplar.pdf", pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []
    story.append(Paragraph("NCERT MATHEMATICS (CLASS 9 & 10)", title_style))
    story.append(Paragraph("National Council of Educational Research and Training<br/>Official High-Yield Formula Reference for Geometry, Mensuration & Trigonometry", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceAfter=14))
    
    story.append(Paragraph("1. CIRCLES & TANGENT THEOREMS", h2_style))
    story.append(Paragraph("• Theorem 10.1: The tangent at any point of a circle is perpendicular to the radius through the point of contact.<br/>• Theorem 10.2: The lengths of tangents drawn from an external point to a circle are equal (PA = PB).<br/>• Direct Common Tangent: DCT = √[d² - (R - r)²]<br/>• Transverse Common Tangent: TCT = √[d² - (R + r)²]", body_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("2. TRIGONOMETRY IDENTITIES", h2_style))
    story.append(Paragraph("• sin²θ + cos²θ = 1 &nbsp;&nbsp;|&nbsp;&nbsp; 1 + tan²θ = sec²θ &nbsp;&nbsp;|&nbsp;&nbsp; 1 + cot²θ = cosec²θ<br/>• Complementary Angles: sin(90° - θ) = cosθ | tan(90° - θ) = cotθ | sec(90° - θ) = cosecθ", body_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("3. SURFACE AREAS & VOLUMES", h2_style))
    story.append(Paragraph("• Cylinder: CSA = 2πrh, TSA = 2πr(r + h), Volume = πr²h<br/>• Cone: CSA = πrl (where l = √(r² + h²)), TSA = πr(l + r), Volume = (1/3)πr²h<br/>• Sphere: Surface Area = 4πr², Volume = (4/3)πr³<br/>• Hemisphere: CSA = 2πr², TSA = 3πr², Volume = (2/3)πr³", body_style))
    doc.build(story)

# 6. Word Power Made Easy Root Words
def generate_word_power_doc():
    doc = SimpleDocTemplate("public/resources/Word_Power_Made_Easy_Norman_Lewis.pdf", pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []
    story.append(Paragraph("WORD POWER MADE EASY — ETYMOLOGY SUMMARY", title_style))
    story.append(Paragraph("By Norman Lewis — Core Latin & Greek Root Word System<br/>Essential Vocabulary Compendium for SSC CGL English Comprehension", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1e3a8a'), spaceAfter=14))
    
    roots = [
        ("Ego (Latin: I / Self)", "• Egotist: Talkative self-absorbed person<br/>• Egoist: Selfish person<br/>• Egocentric: Considering oneself the center of the universe<br/>• Egomaniac: Obsessively wrapped up in oneself"),
        ("Alter (Latin: Other)", "• Altruist: One who cares about and helps others<br/>• Alternate: Skip one and take the other<br/>• Alternative: Another choice<br/>• Alteration: A change or modification<br/>• Altercation: A heated noisy argument with another"),
        ("Verto / Versum (Latin: To Turn)", "• Introvert: One whose thoughts are turned inward<br/>• Extrovert: One whose thoughts are turned outward<br/>• Ambivert: One having both introverted and extroverted tendencies"),
        ("Misein (Greek: To Hate) & Anthropos (Greek: Mankind)", "• Misanthrope: A person who hates mankind<br/>• Misogynist: A person who hates women (Gyne: Woman)<br/>• Misogamist: A person who hates marriage (Gamos: Marriage)<br/>• Philanthropist: A person who loves and helps mankind (Philein: To Love)")
    ]
    for r_title, r_desc in roots:
        story.append(Paragraph(f"<b>{r_title}</b>", ParagraphStyle('RootTitle', parent=body_style, textColor=colors.HexColor('#1e3a8a'))))
        story.append(Paragraph(r_desc, body_style))
        story.append(Spacer(1, 4))
    doc.build(story)

if __name__ == '__main__':
    generate_ssc_notice()
    generate_constitution_doc()
    generate_pyq_paper()
    generate_dest_doc()
    generate_ncert_math_doc()
    generate_word_power_doc()
    print("All 6 Official PDF files generated successfully in public/resources/")
