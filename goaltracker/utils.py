from datetime import date, timedelta
from flask import current_app
import smtplib
from email.message import EmailMessage

from .models import Course, GoalTask, ProjectSubTask, Skill


SKILL_KEYWORDS = [
    "linux",
    "docker",
    "kubernetes",
    "aws",
    "terraform",
    "jenkins",
    "git",
    "network",
    "shell",
    "ci/cd",
    "monitoring",
    "python",
    "ansible",
    "prometheus",
    "grafana",
    "bash",
]

SKILL_STATUS_WEIGHT = {
    "Not Started": 0.0,
    "Learning": 0.25,
    "Practicing": 0.6,
    "Ready": 1.0,
}


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def parse_date(value):
    if not value:
        return None
    return date.fromisoformat(value)


def task_completion(goal):
    tasks = list(goal.tasks)
    if not tasks:
        return 0
    return round((sum((task.progress if hasattr(task, "progress") else (100 if task.completed else 0)) for task in tasks) / (len(tasks) * 100)) * 100)


def project_progress(project):
    subtasks = list(project.subtasks)
    if not subtasks:
        return 0
    total = len(subtasks)
    completed = sum(1 for subtask in subtasks if subtask.completed)
    return round(clamp((completed / total) * 100, 0, 100))


def course_progress(course):
    chapters = list(course.chapters)
    if not chapters:
        return 0
    total = course.total_lessons or len(chapters)
    if total <= 0:
        return 0
    completed = sum(1 for chapter in chapters if chapter.completed)
    return round(clamp((completed / total) * 100, 0, 100))


def goal_progress(goal):
    tasks = list(goal.tasks)
    skills = list(goal.skills)
    courses = list(goal.courses)

    task_score = (sum(1 for task in tasks if task.completed) / len(tasks)) if tasks else 0
    skill_score = (
        sum(SKILL_STATUS_WEIGHT.get(skill.status, 0) for skill in skills) / len(skills)
        if skills
        else 0
    )
    course_score = (
        sum((course.completed_lessons / course.total_lessons) if course.total_lessons else 0 for course in courses)
        / len(courses)
        if courses
        else 0
    )

    filled_sections = sum(1 for score in (task_score, skill_score, course_score) if score > 0)
    if filled_sections == 0:
        return 0

    blended = (task_score * 0.5) + (skill_score * 0.3) + (course_score * 0.2)
    return round(clamp(blended * 100, 0, 100))


def skill_readiness(skill):
    return round(SKILL_STATUS_WEIGHT.get(skill.status, 0) * 100)


def auto_detect_skills(text):
    lower = (text or "").lower()
    found = []
    for keyword in SKILL_KEYWORDS:
        if keyword in lower:
            pretty = keyword.upper() if keyword in {"aws", "git"} else keyword.replace("ci/cd", "CI/CD").title()
            if pretty.lower() not in {item.lower() for item in found}:
                found.append(pretty)
    return found


def derive_skill_status(skills):
    strong = []
    needs_practice = []
    for skill in skills:
        if skill.status == "Ready" or skill.confidence_level >= 4:
            strong.append(skill)
        else:
            needs_practice.append(skill)
    return strong, needs_practice


def recent_activity_messages(activities):
    return [activity.message for activity in activities]


WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_weekdays(values):
    cleaned = []
    for value in values or []:
        try:
            idx = int(value)
        except ValueError:
            continue
        if 0 <= idx <= 6:
            cleaned.append(str(idx))
    return ",".join(sorted(set(cleaned), key=int))


def weekday_list(encoded):
    if not encoded:
        return []
    return [int(item) for item in encoded.split(",") if item != ""]


def next_interval_date(base_date, interval_days):
    base = base_date or date.today()
    interval_days = max(1, int(interval_days or 1))
    return base + timedelta(days=interval_days)


def next_weekly_date(base_date, weekdays):
    base = base_date or date.today()
    weekday_set = {int(day) for day in weekdays if 0 <= int(day) <= 6}
    for offset in range(1, 15):
        candidate = base + timedelta(days=offset)
        if candidate.weekday() in weekday_set:
            return candidate
    return base + timedelta(days=7)


def send_email(to_address, subject, body, html=None):
    """Send a simple email using SMTP settings from Flask app config.

    Config keys read:
      MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD,
      MAIL_USE_TLS (bool), MAIL_USE_SSL (bool), MAIL_DEFAULT_SENDER

    Returns (True, None) on success or (False, error_message) on failure.
    """
    cfg = current_app.config
    server = cfg.get("MAIL_SERVER")
    if not server:
        return False, "Mail server not configured (set MAIL_SERVER)"
    port = int(cfg.get("MAIL_PORT", 587))
    username = cfg.get("MAIL_USERNAME")
    password = cfg.get("MAIL_PASSWORD")
    use_tls = bool(cfg.get("MAIL_USE_TLS", True))
    use_ssl = bool(cfg.get("MAIL_USE_SSL", False))
    sender = cfg.get("MAIL_DEFAULT_SENDER") or (username or "no-reply@localhost")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_address
    if html:
        msg.set_content(body)
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(body)

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(server, port) as smtp:
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(server, port) as smtp:
                if use_tls:
                    smtp.starttls()
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(msg)
        return True, None
    except Exception as exc:  # pragma: no cover - network errors in CI
        return False, str(exc)
