from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from . import db
from .models import Course, DailyTask, GoalTask, InterviewGoal, Skill, User

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@goaltracker.local"
DEMO_PASSWORD = "DemoPass123!"


def _get_or_create_user():
    user = User.query.filter((User.username == DEMO_USERNAME) | (User.email == DEMO_EMAIL)).first()
    if user:
        return user

    user = User(
        username=DEMO_USERNAME,
        email=DEMO_EMAIL,
        full_name="Demo User",
    bio="Example account for general interview preparation tracking.",
        password_hash=generate_password_hash(DEMO_PASSWORD),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _add_goal(user, payload):
    goal = InterviewGoal.query.filter_by(user_id=user.id, title=payload["title"]).first()
    if goal:
        return goal

    goal = InterviewGoal(user_id=user.id, **payload["goal"])
    db.session.add(goal)
    db.session.flush()

    for task in payload.get("tasks", []):
        db.session.add(GoalTask(goal_id=goal.id, **task))

    for skill in payload.get("skills", []):
        db.session.add(Skill(goal_id=goal.id, **skill))

    db.session.flush()

    course_lookup = {}
    for course_spec in payload.get("courses", []):
        course = Course(goal_id=goal.id, **course_spec["course"])
        db.session.add(course)
        db.session.flush()
        course_lookup[course.name] = (course, course_spec.get("skill_names", []))

    skill_lookup = {skill.name: skill for skill in goal.skills}
    for course_name, (course, skill_names) in course_lookup.items():
        course.skills.extend([skill_lookup[name] for name in skill_names if name in skill_lookup])

    return goal


def seed_demo_data():
    user = _get_or_create_user()

    sample_goals = [
        {
            "title": "Platform Engineer - ABC Technologies",
            "goal": {
                "title": "Platform Engineer - ABC Technologies",
                "company_name": "ABC Technologies",
                "role": "Platform Engineer",
                "interview_date": date.today() + timedelta(days=14),
                "priority": 1,
                "status": "Preparing",
                "notes": "Focus on infrastructure, automation, cloud, and interview stories.",
                "job_description": "Build and automate infrastructure, manage cloud workloads, and develop reliable deployment pipelines.",
                "responsibilities": "Operate production systems, improve reliability, and mentor teams on automation.",
                "preferred_qualifications": "Cloud, Infrastructure as Code, CI/CD, Git, Linux, scripting.",
                "company_notes": "Emphasis on automation and incident response.",
            },
            "tasks": [
                {"title": "Review Docker networking", "due_date": date.today() + timedelta(days=2), "priority": 1, "completed": False},
                {"title": "Complete Kubernetes labs", "due_date": date.today() + timedelta(days=4), "priority": 1, "completed": False},
                {"title": "Practice Terraform workflows", "due_date": date.today() + timedelta(days=5), "priority": 2, "completed": False},
                {"title": "Prepare system design answers", "due_date": date.today() + timedelta(days=7), "priority": 2, "completed": False},
            ],
            "skills": [
                {"name": "Docker", "confidence_level": 3, "status": "Practicing", "notes": "Review image layering and networking."},
                {"name": "Kubernetes", "confidence_level": 2, "status": "Learning", "notes": "Practice deployments, services, and ingress."},
                {"name": "AWS", "confidence_level": 3, "status": "Learning", "notes": "Focus on IAM, EC2, EKS, and networking."},
                {"name": "Terraform", "confidence_level": 2, "status": "Learning", "notes": "Improve module structure and state management."},
                {"name": "Git", "confidence_level": 5, "status": "Ready", "notes": "Comfortable with branching and rebase workflows."},
            ],
            "courses": [
                {
                    "course": {
                        "name": "KodeKloud Kubernetes",
                        "platform": "KodeKloud",
                        "url": "https://kodekloud.com/",
                        "instructor": "KodeKloud",
                        "total_lessons": 24,
                        "completed_lessons": 8,
                        "notes": "Hands-on Kubernetes practice course.",
                    },
                    "skill_names": ["Kubernetes"],
                },
                {
                    "course": {
                        "name": "Terraform Associate Prep",
                        "platform": "HashiCorp Learn",
                        "url": "https://developer.hashicorp.com/terraform",
                        "instructor": "HashiCorp",
                        "total_lessons": 18,
                        "completed_lessons": 6,
                        "notes": "Official Terraform learning path.",
                    },
                    "skill_names": ["Terraform", "AWS"],
                },
            ],
        },
        {
            "title": "Senior Platform Engineer - XYZ Ltd",
            "goal": {
                "title": "Senior Platform Engineer - XYZ Ltd",
                "company_name": "XYZ Ltd",
                "role": "Senior Platform Engineer",
                "interview_date": date.today() + timedelta(days=21),
                "priority": 2,
                "status": "Planned",
                "notes": "Expect deep questions on Linux, networking, monitoring, and scripting.",
                "job_description": "Own Linux platform operations, monitoring, deployment automation, and CI/CD tooling.",
                "responsibilities": "Maintain platform reliability, optimize observability, and support release engineering.",
                "preferred_qualifications": "Linux, networking, Bash, Python, Jenkins, Prometheus, Grafana.",
                "company_notes": "Likely to include troubleshooting scenarios and platform design discussion.",
            },
            "tasks": [
                {"title": "Refresh Linux troubleshooting notes", "due_date": date.today() + timedelta(days=3), "priority": 1, "completed": False},
                {"title": "Review networking fundamentals", "due_date": date.today() + timedelta(days=6), "priority": 2, "completed": False},
                {"title": "Practice scripting exercises", "due_date": date.today() + timedelta(days=8), "priority": 2, "completed": False},
            ],
            "skills": [
                {"name": "Linux", "confidence_level": 4, "status": "Ready", "notes": "Strong at day-to-day troubleshooting."},
                {"name": "Networking", "confidence_level": 3, "status": "Practicing", "notes": "Review routing, DNS, and load balancing."},
                {"name": "Shell Scripting", "confidence_level": 3, "status": "Learning", "notes": "Practice automation patterns and safe scripting."},
                {"name": "Jenkins", "confidence_level": 2, "status": "Learning", "notes": "Review pipeline syntax and shared libraries."},
                {"name": "Monitoring", "confidence_level": 3, "status": "Practicing", "notes": "Study alerting and dashboard design."},
            ],
            "courses": [
                {
                    "course": {
                        "name": "Linux Foundation Essentials",
                        "platform": "Linux Foundation",
                        "url": "https://training.linuxfoundation.org/",
                        "instructor": "Linux Foundation",
                        "total_lessons": 20,
                        "completed_lessons": 12,
                        "notes": "Core Linux admin refresh.",
                    },
                    "skill_names": ["Linux"],
                },
                {
                    "course": {
                        "name": "Prometheus and Grafana Basics",
                        "platform": "Grafana Labs",
                        "url": "https://grafana.com/",
                        "instructor": "Grafana Labs",
                        "total_lessons": 14,
                        "completed_lessons": 5,
                        "notes": "Observability-focused learning path.",
                    },
                    "skill_names": ["Monitoring"],
                },
            ],
        },
    ]

    for payload in sample_goals:
        _add_goal(user, payload)

    if not DailyTask.query.filter_by(user_id=user.id).first():
        db.session.add_all(
            [
                DailyTask(user_id=user.id, title="Send one mock interview answer", due_date=date.today(), priority=1),
                DailyTask(user_id=user.id, title="Review today's skill gaps", due_date=date.today(), priority=2),
            ]
        )

    db.session.commit()
