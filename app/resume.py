import os,re,json
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,HRFlowable
from reportlab.lib.units import mm
from app.config import PROFILE_PATH,RESUME_DIR
from app.ai import tailor_profile

def build_resume(job):
    with open(PROFILE_PATH,encoding="utf-8") as f: profile=json.load(f)
    d=tailor_profile(profile,job); os.makedirs(RESUME_DIR,exist_ok=True)
    safe=lambda s: re.sub(r"[^A-Za-z0-9_-]+","_",s).strip("_")[:60]
    path=os.path.join(RESUME_DIR,f"{job['id']}_{safe(job['company'])}_{safe(job['title'])}.pdf")
    doc=SimpleDocTemplate(path,pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=13*mm,bottomMargin=13*mm)
    s=getSampleStyleSheet()
    s.add(ParagraphStyle(name="Name",parent=s["Title"],fontSize=18,leading=21,alignment=TA_CENTER,textColor=colors.HexColor("#172554")))
    s.add(ParagraphStyle(name="Contact",parent=s["Normal"],fontSize=8,leading=10,alignment=TA_CENTER,spaceAfter=7))
    s.add(ParagraphStyle(name="Sec",parent=s["Heading2"],fontSize=10,leading=12,textColor=colors.HexColor("#1D4ED8"),spaceBefore=6,spaceAfter=3))
    s.add(ParagraphStyle(name="Small",parent=s["BodyText"],fontSize=8.5,leading=10.5,spaceAfter=2))
    story=[Paragraph(escape(d.get("full_name",profile.get("full_name","Resume"))),s["Name"])]
    contact=" | ".join(x for x in [profile.get("email",""),profile.get("phone",""),profile.get("location",""),profile.get("linkedin",""),profile.get("github","")] if x)
    story.append(Paragraph(escape(contact),s["Contact"]))
    def section(title):
        story.extend([Paragraph(escape(title.upper()),s["Sec"]),HRFlowable(width="100%",thickness=.5,color=colors.HexColor("#CBD5E1"),spaceAfter=3)])
    if d.get("summary"):
        section("Professional Summary"); story.append(Paragraph(escape(d["summary"]),s["Small"]))
    if d.get("skills"):
        section("Technical Skills"); story.append(Paragraph(escape(" • ".join(d["skills"])),s["Small"]))
    for key,label in [("experience","Experience"),("projects","Projects"),("education","Education")]:
        items=d.get(key) or []
        if items:
            section(label)
            for x in items:
                if key=="experience":
                    heading=f"<b>{escape(x.get('title',''))}</b> — {escape(x.get('company',''))} ({escape(x.get('dates',''))})"
                elif key=="projects":
                    heading=f"<b>{escape(x.get('name',''))}</b> — {escape(', '.join(x.get('technologies',[])))}"
                else:
                    heading=f"<b>{escape(x.get('degree',''))}</b> — {escape(x.get('institution',''))} ({escape(x.get('dates',''))})"
                story.append(Paragraph(heading,s["Small"]))
                for b in x.get("bullets",[]): story.append(Paragraph("• "+escape(b),s["Small"]))
    if d.get("certifications"):
        section("Certifications"); story.append(Paragraph(escape(" • ".join(d["certifications"])),s["Small"]))
    doc.build(story)
    return path
