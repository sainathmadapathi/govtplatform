"""Eight document layouts. The test is as much about what is *not* found as what is.

A procedure can be written as numbered steps, as headings, as bullets, as a table, or as
prose that simply describes what to do. The first four are structure and can be read; the
last is not, and reading it anyway would mean splitting paragraphs on guesswork and calling
the pieces stages. So half of these fixtures exist to prove the extractor stays quiet.

The junk cases matter too, because real documents are full of it: page numbers, navigation
menus, tracking scripts and policy banners all look like short lines with capital letters.
One run of this extractor promoted three page numbers to application stages.

No real authority's wording appears here.

Run: python -m tools.exam_builder.test_stages
"""
from __future__ import annotations

from .stages import Structure, discover_stages, procedure_regions

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def titles(text: str) -> list[str]:
    return [c.title for c in discover_stages(text)]


# ===================================================================== A. steps
A_STEPS = """
HOW TO APPLY
Candidates apply online.
Step 1 - Create Profile
Candidates shall create the profile and enter the mobile number to register.
Step 2 - Fill Application
Candidates must fill the application form and provide the roll number.
Step 3 - Make Payment
Candidates shall pay the prescribed fee and submit the application.
"""


def test_a_step_numbered() -> None:
    stages = discover_stages(A_STEPS)
    check('A: three steps', [c.title for c in stages],
          ['Create Profile', 'Fill Application', 'Make Payment'])
    check('A: recognised as explicit markers',
          {c.structure for c in stages}, {Structure.EXPLICIT_MARKER})
    check('A: ordered as written', [c.order for c in stages], [1, 2, 3])
    check('A: and confident, because the structure is explicit',
          all(c.confidence >= 0.9 for c in stages), True)


def test_a_lettered_parts_are_markers_too() -> None:
    """A part may be lettered. Requiring digits is what missed a real notice entirely."""
    text = """
PROCEDURE FOR FILLING ONLINE APPLICATION
The process consists of two parts.
Part-A (One Time Registration):
1. Candidates shall register on the website and create a password.
2. Candidates must enter the mobile number and verify it.
Part-B (Online Application Form):
1. Candidates shall fill the application form and select the centre.
2. Candidates must submit the form and pay the fee.
"""
    check('lettered parts are found',
          titles(text), ['One Time Registration', 'Online Application Form'])


# =================================================================== B. headings
B_HEADINGS = """
APPLICATION PROCESS

Registration
Candidates shall register on the portal using a valid mobile number. An account is
created once and remains valid for later examinations.

Filling of Application Form
Candidates must fill the application form completely. Candidates shall enter the
particulars exactly as they appear in the certificates.

Uploading Photograph
Candidates are required to upload the photograph. The photograph must be recent.

Payment
Candidates shall pay the prescribed fee online. Payment completes the application.
"""


def test_b_heading_based() -> None:
    stages = discover_stages(B_HEADINGS)
    check('B: the headings become the stages',
          [c.title for c in stages],
          ['Registration', 'Filling of Application Form', 'Uploading Photograph',
           'Payment'])
    check('B: recognised as headings', {c.structure for c in stages}, {Structure.HEADING})
    check('B: the authority’s wording is untouched',
          'Filling of Application Form' in [c.title for c in stages], True)


# ==================================================================== C. bullets
C_BULLETS = """
HOW TO APPLY
The application is made as follows.
- Register on the portal and create a password for the account.
- Fill the application form and enter the required particulars carefully.
- Upload the photograph and the signature in the prescribed manner.
- Pay the fee online and submit the completed application form.
"""


def test_c_bullet_based() -> None:
    stages = discover_stages(C_BULLETS)
    check('C: four bullets, four stages', len(stages), 4)
    check('C: recognised as bullets', {c.structure for c in stages}, {Structure.BULLET})
    check('C: the first bullet’s wording is kept',
          stages[0].title.startswith('Register on the portal'), True)


# ====================================================================== D. table
D_TABLE = """
APPLICATION PROCEDURE
The stages of the application are given below.
| Step | Activity | Instructions |
| 1 | Registration | Candidates shall register on the portal and create a password |
| 2 | Application Form | Candidates must fill the form and enter the particulars |
| 3 | Fee Payment | Candidates shall pay the fee online and submit the application |
"""


def test_d_table_based() -> None:
    stages = discover_stages(D_TABLE)
    check('D: the activity column becomes the title',
          [c.title for c in stages],
          ['Registration', 'Application Form', 'Fee Payment'])
    check('D: recognised as table rows',
          {c.structure for c in stages}, {Structure.TABLE_ROW})
    check('D: the header row is not a stage',
          any(c.title.lower() == 'activity' for c in stages), False)


def test_d_table_column_names_are_not_assumed() -> None:
    """The same table with different headings, and one that is not in English word order."""
    text = D_TABLE.replace('| Step | Activity | Instructions |',
                           '| Sl. | Particulars | What the candidate does |')
    check('a differently-headed table reads the same',
          titles(text), ['Registration', 'Application Form', 'Fee Payment'])


# =========================================================== E. prose, insufficient
E_PROSE = """
HOW TO APPLY
Candidates are required to apply online through the official portal. The application
must be submitted before the closing date. Candidates should ensure that the
particulars furnished are correct, since no correction is permitted afterwards. The
fee must be paid online and the application submitted in good time.
"""


def test_e_prose_yields_nothing() -> None:
    """Prose describes the procedure without structuring it, so there is nothing to read."""
    check('E: unstructured prose produces no stages', discover_stages(E_PROSE), [])
    check('E: and the region was found all the same, so this is not a miss',
          len(procedure_regions(E_PROSE)) >= 1, True)


# ============================================================ F. mixed structures
F_MIXED = """
APPLICATION PROCEDURE

One Time Registration
Candidates shall register on the portal. The following information is required.
1. The mobile number, to be verified.
2. The email address, to be verified.
3. An identity number.

Examination Application
Candidates must fill the application form for the examination. Candidates shall
select the centre and pay the fee before submitting the form.
"""


def test_f_mixed_headings_and_numbered_items() -> None:
    """Headings are the stages; the numbered items beneath them are instructions.

    This is the shape that produced the worst failure: promoting every numbered item gave
    eleven stages where the document describes two.
    """
    stages = discover_stages(F_MIXED)
    check('F: the headings are the stages',
          [c.title for c in stages],
          ['One Time Registration', 'Examination Application'])
    check('F: the numbered items beneath them are not',
          any(c.title.startswith('The mobile number') for c in stages), False)


# ========================================================= G. navigation and noise
G_NAVIGATION = """
Home | Sitemap | Contact Us | Screen Reader Access | Skip to main content
Accessibility Statement
Privacy Policy
Terms of Use
Last Updated
HOW TO APPLY
Candidates apply online at the portal.
Step 1 - Registration
Candidates shall register on the portal and create a password for the account.
Step 2 - Submission
Candidates must submit the completed application form before the closing date.
"""


def test_g_navigation_is_not_a_procedure() -> None:
    stages = discover_stages(G_NAVIGATION)
    check('G: only the real steps are found',
          [c.title for c in stages], ['Registration', 'Submission'])
    check('G: no menu item became a stage',
          [c for c in stages if c.title in ('Sitemap', 'Privacy Policy', 'Terms of Use')],
          [])


def test_g_page_furniture_is_not_a_stage() -> None:
    """Three page numbers were promoted to stages on the first multi-structure run."""
    text = """
HOW TO APPLY

Page 18 of 132
Candidates shall register on the portal and create a password for the account here.

Page 19 of 132
Candidates must submit the completed application form before the closing date here.
"""
    check('page markers never become stages', discover_stages(text), [])


# ================================================================ H. scripts/URLs
H_SCRIPT = """
HOW TO APPLY
<script>var d=document;d.createElement('iframe').src='https://www.googletagmanager.com/ns.html';
function gtag(){dataLayer.push(arguments);}</script>
Apply Now
Register Here
Click Here To Apply
"""


def test_h_markup_is_not_a_procedure() -> None:
    check('H: a region that opens with script is skipped', discover_stages(H_SCRIPT), [])


def test_h_link_text_alone_is_not_a_stage() -> None:
    """Short call-to-action links look like headings and have nothing under them."""
    text = """
HOW TO APPLY
Apply Now
Register Here
Download Notice
Check Status
"""
    check('link labels with no content beneath them are not stages',
          discover_stages(text), [])


# ================================================================== general rules
def test_a_keyword_alone_never_makes_a_stage() -> None:
    """Headings naming the right things, with bodies that are not instructions."""
    text = """
APPLICATION PROCEDURE
The following definitions apply to this notice and are given for reference only.

Registration
This term refers to the register of candidates maintained by the office for the
purposes of record keeping under the relevant rules and for no other purpose.

Photograph
This term refers to the image held on the record of the office, which is retained
in accordance with the retention policy applicable to records of this description.
"""
    check('a heading that merely names a topic is not a step',
          discover_stages(text), [])


def test_one_marker_is_a_coincidence() -> None:
    text = """
HOW TO APPLY
Candidates apply online at the portal and shall submit the form before the date.
Step 1 - Registration
Candidates shall register on the portal and create a password for their account.
"""
    check('a single marker does not make a procedure', discover_stages(text), [])


def test_stages_are_ordered_by_position_not_by_discovery() -> None:
    stages = discover_stages(A_STEPS)
    check('order follows the document',
          [c.offset for c in stages], sorted(c.offset for c in stages))
    check('and is numbered from one', [c.order for c in stages], [1, 2, 3])


def test_the_strongest_structure_present_is_used() -> None:
    """A document with both explicit markers and bullets is read by its markers."""
    text = A_STEPS + """
- Some later bullet about applying and submitting the form in good time.
- Another later bullet about paying the fee and uploading the photograph.
"""
    check('explicit markers outrank bullets',
          {c.structure for c in discover_stages(text)}, {Structure.EXPLICIT_MARKER})


def test_no_authority_is_named_anywhere() -> None:
    import io
    import re
    source = io.open('tools/exam_builder/stages.py', encoding='utf-8').read()
    for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc', 'tspsc', 'rrb', 'sbi'):
        check(f'stages.py never names {forbidden.upper()}',
              re.findall(rf'\b{forbidden}\b', source, re.I), [])
    check('and holds no list of expected stage names',
          re.findall(r'account creation|personal details|final submission', source, re.I),
          [])


def main() -> int:
    test_a_step_numbered()
    test_a_lettered_parts_are_markers_too()
    test_b_heading_based()
    test_c_bullet_based()
    test_d_table_based()
    test_d_table_column_names_are_not_assumed()
    test_e_prose_yields_nothing()
    test_f_mixed_headings_and_numbered_items()
    test_g_navigation_is_not_a_procedure()
    test_g_page_furniture_is_not_a_stage()
    test_h_markup_is_not_a_procedure()
    test_h_link_text_alone_is_not_a_stage()
    test_a_keyword_alone_never_makes_a_stage()
    test_one_marker_is_a_coincidence()
    test_stages_are_ordered_by_position_not_by_discovery()
    test_the_strongest_structure_present_is_used()
    test_no_authority_is_named_anywhere()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('stages: six structures read, prose and furniture left alone')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
