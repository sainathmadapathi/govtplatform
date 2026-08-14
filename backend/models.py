"""
GovOS Backend Database Models Architecture (Production V1 Schema)
==================================================================
Strict Trust-First Schema incorporating:
- Nested RuleGroup expression trees with CheckConstraint enforcement
- Fact-level DataProvenance with 4-tier taxonomy
- SourceEndpoint monitoring with 3-layer SHA-256 hash checks
- SourceDocument vs SourceDocumentVersion decoupling
- ImportantDate DateTime & Timezone support
- Exam -> ExamCycle -> Post -> EligibilityRule hierarchy
- UserReport human feedback loop
"""

from django.db import models
from django.conf import settings
from django.db.models import Q, CheckConstraint

# ==========================================
# 1. SOURCE & TRUST DOMAIN
# ==========================================

class SourceAuthority(models.Model):
    name = models.CharField(max_length=255, help_text="e.g. Staff Selection Commission")
    code = models.CharField(max_length=50, unique=True, help_text="e.g. SSC")
    official_domain = models.URLField(help_text="e.g. https://ssc.gov.in")
    allowed_subdomains = models.JSONField(default=list, help_text="Security boundary allowed subdomains")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class PrecedenceRule(models.Model):
    authority = models.ForeignKey(SourceAuthority, on_delete=models.CASCADE, related_name="precedence_rules")
    source_type = models.CharField(max_length=100, help_text="CORRIGENDUM, NOTIFICATION_PDF, NOTICE_BOARD, WEBPAGE")
    rank = models.PositiveIntegerField(help_text="Lower rank = Higher authority precedence")

    class Meta:
        ordering = ['rank']


class SourceEndpoint(models.Model):
    FREQUENCY_CHOICES = [
        ('6H', 'High Priority (6 Hours)'),
        ('12H', 'Notification Board (12 Hours)'),
        ('24H', 'Standard Page (24 Hours)'),
        ('7D', 'Historical (7 Days)'),
    ]
    authority = models.ForeignKey(SourceAuthority, on_delete=models.CASCADE, related_name="endpoints")
    endpoint_url = models.URLField()
    endpoint_type = models.CharField(max_length=100, help_text="NOTIFICATION_PAGE, APPLY_PORTAL, RESULT_PAGE")
    check_frequency = models.CharField(max_length=5, choices=FREQUENCY_CHOICES, default='24H')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.authority.code} - {self.endpoint_type} ({self.endpoint_url})"


class SourceDocument(models.Model):
    endpoint = models.ForeignKey(SourceEndpoint, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, help_text="PDF, HTML, IMAGE")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.file_type})"


class SourceDocumentVersion(models.Model):
    document = models.ForeignKey(SourceDocument, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField(default=1)
    file_url = models.URLField()
    local_path = models.CharField(max_length=512, blank=True, null=True)
    raw_content_hash = models.CharField(max_length=64, help_text="Raw HTTP Payload SHA-256")
    normalized_content_hash = models.CharField(max_length=64, help_text="Clean DOM Content SHA-256")
    extracted_text_hash = models.CharField(max_length=64, help_text="Extracted Text SHA-256")
    published_date = models.DateField()
    retrieved_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('document', 'version_number')


class SourceHealthLog(models.Model):
    endpoint = models.ForeignKey(SourceEndpoint, on_delete=models.CASCADE, related_name="health_logs")
    http_status = models.IntegerField()
    checked_at = models.DateTimeField(auto_now_add=True)
    raw_content_hash = models.CharField(max_length=64)
    normalized_content_hash = models.CharField(max_length=64)
    text_changed = models.BooleanField(default=False)
    admin_review_status = models.CharField(max_length=50, default="HEALTHY")  # HEALTHY, CONFLICT_DETECTED, REVIEWED


class DataProvenance(models.Model):
    TAXONOMY_CHOICES = [
        ('FACT', 'Official Fact (A)'),
        ('INTERPRETATION', 'Official Interpretation (B)'),
        ('EXPLANATION', 'GovOS Simple Explanation (C)'),
        ('RECOMMENDATION', 'GovOS Recommendation (D)'),
    ]
    VERIFICATION_CHOICES = [
        ('OFFICIALLY_VERIFIED', 'Officially Verified'),
        ('UNDER_VERIFICATION', 'Under Verification'),
        ('SUPERSEDED', 'Superseded / Outdated'),
    ]
    document_version = models.ForeignKey(SourceDocumentVersion, on_delete=models.PROTECT)
    page_number = models.IntegerField(null=True, blank=True)
    clause_number = models.CharField(max_length=100, blank=True)
    retrieved_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=100, blank=True)
    taxonomy_type = models.CharField(max_length=50, choices=TAXONOMY_CHOICES)
    verification_level = models.CharField(max_length=50, choices=VERIFICATION_CHOICES, default='UNDER_VERIFICATION')

    def __str__(self):
        return f"Provenance #{self.id}: Page {self.page_number or 'N/A'}, Clause '{self.clause_number or 'N/A'}' ({self.get_verification_level_display()})"


class UserReport(models.Model):
    user_profile = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name="reports")
    entity_type = models.CharField(max_length=100, help_text="ImportantDate, EligibilityRule, SyllabusTopic, Link")
    entity_id = models.IntegerField()
    issue_category = models.CharField(max_length=100, help_text="WRONG_ELIGIBILITY, OUTDATED_DATE, BROKEN_LINK")
    description = models.TextField()
    provenance = models.ForeignKey(DataProvenance, null=True, blank=True, on_delete=models.SET_NULL)
    admin_status = models.CharField(max_length=50, default="PENDING")  # PENDING, RESOLVED, REJECTED
    created_at = models.DateTimeField(auto_now_add=True)


# ==========================================
# 2. EXAM & RECRUITMENT DOMAIN
# ==========================================

class Exam(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="e.g. SSC_CGL")
    title = models.CharField(max_length=255)
    authority = models.ForeignKey(SourceAuthority, on_delete=models.CASCADE, related_name="exams")
    overview_description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.code})"


class ExamCycle(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="cycles")
    year = models.IntegerField(help_text="Recruitment Year e.g. 2026")
    cycle_code = models.CharField(max_length=100, unique=True, help_text="e.g. SSC_CGL_2026")
    status = models.CharField(max_length=50, default="UPCOMING")  # UPCOMING, OPEN, CLOSED, COMPLETED
    is_current = models.BooleanField(default=True)

    def __str__(self):
        return self.cycle_code


class Notification(models.Model):
    exam_cycle = models.ForeignKey(ExamCycle, on_delete=models.CASCADE, related_name="notifications")
    document_version = models.ForeignKey(SourceDocumentVersion, on_delete=models.PROTECT)
    notification_type = models.CharField(max_length=50)  # ORIGINAL_NOTIFICATION, CORRIGENDUM, EXTENSION_NOTICE
    notification_number = models.CharField(max_length=100, blank=True)
    published_date = models.DateField()
    effective_date = models.DateField()
    supersedes_notification = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    summary = models.TextField()
    status = models.CharField(max_length=50, default="ACTIVE")


class ExamCycleVersion(models.Model):
    exam_cycle = models.ForeignKey(ExamCycle, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=50, default="CURRENT")  # CURRENT, SUPERSEDED
    superseded_by_version = models.IntegerField(null=True, blank=True)
    notification = models.ForeignKey(Notification, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class ImportantDate(models.Model):
    DATE_TYPE_CHOICES = [
        ('NOTIFICATION', 'Notification Date'),
        ('APPLICATION_OPEN', 'Application Start Date'),
        ('APPLICATION_CLOSE', 'Application End Date'),
        ('ADMIT_CARD', 'Admit Card Release Date'),
        ('EXAM_TIER1', 'Tier 1 Exam Start Date'),
        ('EXAM_TIER2', 'Tier 2 Exam Start Date'),
        ('ANSWER_KEY', 'Answer Key Release Date'),
        ('OBJECTION_WINDOW', 'Objection Window End Date'),
        ('RESULT', 'Result Declaration Date'),
        ('DOCUMENT_VERIFICATION', 'Document Verification Date'),
    ]
    exam_cycle = models.ForeignKey(ExamCycle, on_delete=models.CASCADE, related_name="important_dates")
    date_type = models.CharField(max_length=50, choices=DATE_TYPE_CHOICES)
    date_time = models.DateTimeField(null=True, blank=True)
    timezone_str = models.CharField(max_length=50, default='Asia/Kolkata')
    is_tentative = models.BooleanField(default=False)
    provenance = models.ForeignKey(DataProvenance, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.exam_cycle.cycle_code} - {self.get_date_type_display()}: {self.date_time}"


class Post(models.Model):
    exam_cycle = models.ForeignKey(ExamCycle, on_delete=models.CASCADE, related_name="posts")
    post_name = models.CharField(max_length=255)  # "Assistant Section Officer"
    department = models.CharField(max_length=255)  # "Central Secretariat Service"
    pay_level = models.CharField(max_length=50)  # "Pay Level 7"
    classification = models.CharField(max_length=50)  # Group B
    provenance = models.ForeignKey(DataProvenance, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.post_name} ({self.department})"


class RuleGroup(models.Model):
    OPERATOR_CHOICES = [('AND', 'All Rules Must Pass'), ('OR', 'At Least One Rule Must Pass')]
    post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE, related_name="rule_groups")
    exam_cycle = models.ForeignKey(ExamCycle, null=True, blank=True, on_delete=models.CASCADE, related_name="global_rule_groups")
    parent_group = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name="child_groups")
    group_operator = models.CharField(max_length=3, choices=OPERATOR_CHOICES, default='AND')
    provenance = models.ForeignKey(DataProvenance, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            CheckConstraint(
                check=(Q(post__isnull=False, exam_cycle__isnull=True) | Q(post__isnull=True, exam_cycle__isnull=False)),
                name='rulegroup_post_or_examcycle_only'
            )
        ]


class EligibilityRule(models.Model):
    rule_group = models.ForeignKey(RuleGroup, on_delete=models.CASCADE, related_name="rules")
    rule_type = models.CharField(max_length=50, help_text="AGE_MIN, AGE_MAX, DEGREE_REQUIRED, PERCENTAGE_MIN")
    operator = models.CharField(max_length=10, help_text=">=, <=, =, IN, BETWEEN")
    rule_value = models.JSONField(help_text="e.g. '18', ['B.E', 'B.Tech'], '01-08-2026'")
    category = models.CharField(max_length=50, default="GENERAL")
    provenance = models.ForeignKey(DataProvenance, on_delete=models.PROTECT)


class ExamStage(models.Model):
    exam_cycle = models.ForeignKey(ExamCycle, on_delete=models.CASCADE, related_name="stages")
    stage_number = models.PositiveIntegerField()
    stage_name = models.CharField(max_length=100)  # Tier 1 (CBR)
    duration_minutes = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    total_marks = models.FloatField()
    negative_marking = models.CharField(max_length=100)
    languages = models.JSONField(default=list)
    provenance = models.ForeignKey(DataProvenance, on_delete=models.PROTECT)


class SyllabusTopic(models.Model):
    stage = models.ForeignKey(ExamStage, on_delete=models.CASCADE, related_name="topics")
    subject = models.CharField(max_length=100)
    topic_name = models.CharField(max_length=255)
    parent_topic = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name="subtopics")
    weightage_percentage = models.FloatField(default=0.0)
    weightage_provenance = models.ForeignKey(DataProvenance, null=True, blank=True, on_delete=models.SET_NULL, related_name="weightage_topics")
    syllabus_provenance = models.ForeignKey(DataProvenance, on_delete=models.PROTECT, related_name="official_topics")


class PracticeQuestion(models.Model):
    TYPE_CHOICES = [
        ('OFFICIAL_PYQ', 'Official Previous Year Question'),
        ('USER_SUBMITTED', 'User Submitted Question'),
        ('GOVOS_CREATED', 'GovOS Content Team Question'),
        ('AI_GENERATED', 'AI Generated Practice Question'),
        ('REFERENCE_SOURCE', 'Reference Book Question'),
    ]
    topic = models.ForeignKey(SyllabusTopic, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='OFFICIAL_PYQ')
    question_text = models.TextField()
    options = models.JSONField()  # ["Option A", "Option B", "Option C", "Option D"]
    correct_option_index = models.PositiveIntegerField()
    explanation = models.TextField()
    year = models.IntegerField(null=True, blank=True)
    provenance = models.ForeignKey(DataProvenance, null=True, blank=True, on_delete=models.SET_NULL)


# ==========================================
# 3. STUDENT JOURNEY & PROGRESS DOMAIN
# ==========================================

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255)
    age = models.IntegerField()
    date_of_birth = models.DateField()
    qualification_degree = models.CharField(max_length=255)
    specialization_branch = models.CharField(max_length=255)
    percentage = models.FloatField()
    category = models.CharField(max_length=50)  # GENERAL, OBC, SC, ST, PwBD
    gender = models.CharField(max_length=20)
    domicile_state = models.CharField(max_length=100)


class TopicProgress(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="topic_progress")
    syllabus_topic = models.ForeignKey(SyllabusTopic, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default="NOT_STARTED")  # NOT_STARTED, IN_PROGRESS, COMPLETED
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    accuracy_percentage = models.FloatField(default=0.0)
    attempts_count = models.PositiveIntegerField(default=0)
    last_practiced = models.DateTimeField(auto_now=True)


class UserExamProgress(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="exam_progress")
    target_cycle = models.ForeignKey(ExamCycle, on_delete=models.CASCADE)
    current_step = models.PositiveIntegerField(default=1)  # Steps 1 to 10
    mocks_completed = models.PositiveIntegerField(default=0)
    last_active = models.DateTimeField(auto_now=True)
