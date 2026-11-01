JNF_URL = "https://docs.google.com/document/d/1w1Q5-iCF7QW-GcY9G8NWQNm5FQwmmJyp/edit"
TP_URL = "https://www.manit.ac.in/training-placement-and-student-welfare-cell"
BROCHURE_URL = "https://www.manit.ac.in/sites/default/files/documents/Placement_Brochure_MANIT.pdf"
DEPT_URL = "https://www.manit.ac.in/departmnet-wise-placement-brochure"

SIGNATURE = """Dr. Aruna Saxena
Professor & Head
Training & Placement Cell
MANIT Bhopal

Email: tpwnitb@gmail.com
Mobile: +91 78982 16935"""

BACHELORS = """- B.Tech. — Computer Science and Engineering
- B.Tech. — Electronics and Communication Engineering
- B.Tech. — Mathematics & Data Science
- B.Tech. — Electrical Engineering
- B.Tech. — Civil Engineering
- B.Tech. — Mechanical Engineering
- B.Tech. — Chemical Engineering
- B.Tech. — Materials & Metallurgical Engineering
- B.Arch.
- B.Plan."""

MASTERS = """- Computer Science and Engineering: Computer Networking, Advanced Computing, Artificial Intelligence, Information Security
- Civil Engineering: Environmental Engineering, Geotechnical Engineering, Geo-Informatics Engineering, Structural Engineering, Water Resources and Management Engineering, Transportation Engineering
- Electronics & Communication Engineering: VLSI & Embedded Systems, Communication Systems
- Mathematics, Bioinformatics & Computer Applications: Agile Software Engineering, Bioinformatics, MCA
- Mechanical Engineering: Automation and Robotics, Industrial Engineering and Management, Thermal Engineering, Machine Design
- Electrical Engineering: Integrated Power System, Power Electronics and Drives
- Center of Excellence: Product Design and Smart Manufacturing
- Energy Center: Renewable Energy, Energy System Management
- Biological Science & Engineering: Biotechnology
- MBA: Finance, HR, Marketing
- Physics (M.Tech.): Nanotechnology
- M.Plan.: Housing and Urban Planning
- Chemical Engineering: Chemical Engineering
- M.Sc.: Chemistry and Physics
- Materials & Metallurgical Engineering: Material Science and Technology"""

INTERNSHIPS = """1. 2-Month Internship
- Duration: 10 May 2027 to 10 July 2027
- Eligible programs: B.Tech., B.Arch., B.Plan., M.Plan., M.Tech., M.Sc., MCA and MBA (HR, Finance, Marketing)

2. 6-Month Internship
- Duration: January 2027 to June 2027
- Eligible programs: B.Tech., M.Tech., B.Arch., B.Plan., M.Plan., M.Sc., MCA and MBA (HR, Finance, Marketing)

3. 11-Month Internship
- Duration: July 2026 to May 2027
- Eligible programs: M.Tech."""

INVITATION_BODY = f"""Respected Sir/Ma'am,

Greetings from the MANIT family!

It is a matter of great pleasure for our institute to get connected with you and your organization. We would like to invite your esteemed organization to MANIT Bhopal for the campus recruitment session for the graduating batch of 2027.

MANIT Bhopal, one of the leading National Institutes of Technology in India, aims to produce technical professionals equipped with competence, logical thinking and the skills required by global industries.

Our institute has students from a wide range of undergraduate and postgraduate programs, including B.Tech., M.Tech., MCA, MBA, B.Arch., B.Plan., M.Plan. and M.Sc.

Our students possess technical knowledge, management capabilities, practical experience and communication skills relevant to industry requirements.

We are delighted to invite your organization to participate in the upcoming placement drive for the 2026–27 session.

ACADEMIC PROGRAMS

Bachelor's Programs
{BACHELORS}

Master's Programs and Specializations
{MASTERS}

Please refer to the official placement brochure and department-wise brochures for detailed information.

INTERNSHIP OPPORTUNITIES

{INTERNSHIPS}

We value the internship opportunities extended by companies and recognize the learning experiences they offer our students.

We kindly request companies to communicate potential pre-placement offers (PPOs) by the conclusion of internships. This helps us maintain our one-student-one-placement policy and allows students to explore other opportunities effectively.

RECRUITMENT PROCESS

Please complete the Job Notification Form (JNF) using the link below. On receipt of the JNF, the Training & Placement Cell will coordinate with your organization to finalize a mutually convenient date for the recruitment process.

We would be delighted to host your organization at our campus or assist in conducting an online recruitment drive.

The JNF also includes a feedback form for HR representatives and interview panel members. The feedback helps the institute improve its curriculum and better prepare students for future opportunities. Submission of the feedback form after the recruitment drive is requested.

IMPORTANT LINKS

- Training & Placement Cell: {TP_URL}
- MANIT Placement Brochure: {BROCHURE_URL}
- Department-wise Placement Brochures: {DEPT_URL}
- Job Notification Form: [JNF_URL]

We look forward to establishing a long-standing and healthy relationship with your organization.

CONTACT

Dr. Aruna Saxena
Professor & Head
Training & Placement Cell
MANIT Bhopal

Mobile: +91 78982 16935
Office: 0755-2670802
Email: tpwnitb@gmail.com
Website: www.manit.ac.in

Thanks & Regards,
Dr. Aruna Saxena
Professor & Head, Training & Placement Cell
MANIT Bhopal"""

TEMPLATES = {
    "invitation": {
        "name": "Recruitment Invitation",
        "subject": "Invitation for Campus Recruitment Program 2026–27 — MANIT Bhopal",
        "body": INVITATION_BODY,
    },
    "visit_confirmation": {
        "name": "Campus Visit Confirmation",
        "subject": "Campus Recruitment Visit Confirmation — MANIT Bhopal",
        "body": f"""Respected Sir/Ma'am,

Greetings from MANIT Bhopal!

We are pleased to confirm your organization's campus recruitment visit to Maulana Azad National Institute of Technology, Bhopal.

Please find the approved visit details below:

- Company: [COMPANY_NAME]
- Visit Purpose: [PURPOSE]
- Approved Date: [APPROVED_DATE]
- Start Time: [START_TIME]
- End Time: [END_TIME]
- Visit Request ID: [REQUEST_ID]

We look forward to welcoming your team to MANIT Bhopal.

For any changes or further coordination, please contact the Training & Placement Cell.

Regards,

{SIGNATURE}""",
    },
    "call_confirmation": {
        "name": "Call Confirmation",
        "subject": "Call Confirmation with Head of Training & Placement — MANIT Bhopal",
        "body": f"""Respected Sir/Ma'am,

Greetings from MANIT Bhopal!

Your call with Dr. Aruna Saxena, Professor & Head, Training & Placement Cell, has been confirmed.

- Company: [COMPANY_NAME]
- Purpose: [PURPOSE]
- Date: [APPROVED_DATE]
- Time: [START_TIME] – [END_TIME] (IST)
- Duration: [DURATION] minutes
- Mode: [MODE]
- Meeting Link: [MEETING_LINK]
- Call Request ID: [REQUEST_ID]

Regards,

{SIGNATURE}""",
    },
    "rescheduling": {
        "name": "Rescheduling Update",
        "subject": "Schedule Update — [REQUEST_ID] — MANIT Bhopal",
        "body": f"""Respected Sir/Ma'am,

Greetings from MANIT Bhopal!

Please note that your [ITEM] (Request ID: [REQUEST_ID]) has been rescheduled. The updated schedule is:

- Company: [COMPANY_NAME]
- Purpose: [PURPOSE]
- Date: [APPROVED_DATE]
- Time: [START_TIME] – [END_TIME] (IST)

We regret any inconvenience caused.

Regards,

{SIGNATURE}""",
    },
    "cancellation": {
        "name": "Cancellation Update",
        "subject": "Cancellation Notice — [REQUEST_ID] — MANIT Bhopal",
        "body": f"""Respected Sir/Ma'am,

Greetings from MANIT Bhopal!

We regret to inform you that your [ITEM] (Request ID: [REQUEST_ID]) scheduled on [APPROVED_DATE], [START_TIME] – [END_TIME] (IST) has been cancelled. The Training & Placement Cell will coordinate with you regarding further steps.

Regards,

{SIGNATURE}""",
    },
    "jnf_reminder": {
        "name": "JNF Reminder",
        "subject": "Reminder: Job Notification Form (JNF) — MANIT Bhopal",
        "body": f"""Respected Sir/Ma'am,

Greetings from MANIT Bhopal!

This is a gentle reminder to kindly complete the Job Notification Form (JNF) for [COMPANY_NAME] so that we can coordinate a mutually convenient date for the recruitment process.

Job Notification Form: [JNF_URL]

Regards,

{SIGNATURE}""",
    },
}

KB_SEED = [
    {"title": "Training & Placement Cell — Official Page", "category": "Contact Information", "is_resource": True,
     "source_url": TP_URL,
     "content": "Official MANIT Bhopal Training, Placement & Student Welfare Cell web page. Source link saved; page content has not been imported into this knowledge base."},
    {"title": "MANIT Placement Brochure (PDF)", "category": "Placement Statistics", "is_resource": True,
     "source_url": BROCHURE_URL,
     "content": "Official MANIT placement brochure. Source link saved; the brochure content has not been imported. Any statistics in it are historical and must be verified before quoting."},
    {"title": "Department-wise Placement Brochures", "category": "Department Information", "is_resource": True,
     "source_url": DEPT_URL,
     "content": "Official department-wise placement brochures of MANIT Bhopal. Source link saved; contents have not been imported."},
    {"title": "Job Notification Form (JNF)", "category": "JNF Information", "is_resource": True,
     "source_url": JNF_URL,
     "content": "Companies interested in recruiting from MANIT Bhopal should complete the Job Notification Form (JNF) using the official Google Docs link. The JNF also includes a feedback form for HR representatives and interview panel members, to be submitted after the recruitment drive."},
    {"title": "About MANIT Bhopal", "category": "Institute Information", "source_url": "https://www.manit.ac.in",
     "content": "Maulana Azad National Institute of Technology (MANIT), Bhopal is one of the leading National Institutes of Technology in India. It aims to produce technical professionals equipped with competence, logical thinking and the skills required by global industries. Students come from a wide range of undergraduate and postgraduate programs including B.Tech., M.Tech., MCA, MBA, B.Arch., B.Plan., M.Plan. and M.Sc."},
    {"title": "Bachelor's Programs", "category": "Academic Programs", "academic_year": "2026–27", "content": BACHELORS},
    {"title": "Master's Programs and Specializations", "category": "Academic Programs", "academic_year": "2026–27", "content": MASTERS},
    {"title": "Internship Opportunities 2026–27", "category": "Internship Recruitment", "academic_year": "2026–27", "published": False,
     "content": INTERNSHIPS + "\n\nCompanies are requested to communicate potential pre-placement offers (PPOs) by the conclusion of internships to support the one-student-one-placement policy.\n\n[Pending Admin verification — publish after verifying dates and eligibility.]"},
    {"title": "Campus Recruitment Process", "category": "Placement Process", "academic_year": "2026–27",
     "content": "1. Company expresses interest and receives the official recruitment invitation with the JNF link.\n2. Company completes the Job Notification Form (JNF).\n3. On receipt of the JNF, the T&P Cell coordinates with the company to finalise a mutually convenient date.\n4. Recruitment can be conducted on campus or as an online drive.\n5. MANIT follows a one-student-one-placement policy."},
    {"title": "Campus Visit Guidelines", "category": "Campus Visit Guidelines",
     "content": "Companies can request a campus visit (placement drive, internship recruitment, pre-placement talk, assessment/interview, company presentation) through the portal or MANIT Connect. Every request receives a request ID and remains Pending Approval until reviewed by the Head of T&P or an authorised Admin. An official confirmation email is sent only after approval."},
    {"title": "Contact — Training & Placement Cell", "category": "Contact Information",
     "content": "Dr. Aruna Saxena, Professor & Head, Training & Placement Cell, MANIT Bhopal. Mobile: +91 78982 16935. Office: 0755-2670802. Email: tpwnitb@gmail.com. Website: https://www.manit.ac.in"},
]
