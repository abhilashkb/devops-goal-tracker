from datetime import datetime

from flask_login import UserMixin

from . import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False, default="")
    bio = db.Column(db.Text, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    goals = db.relationship("InterviewGoal", backref="user", lazy=True, cascade="all, delete-orphan")
    daily_tasks = db.relationship("DailyTask", backref="user", lazy=True, cascade="all, delete-orphan")
    activities = db.relationship("Activity", backref="user", lazy=True, cascade="all, delete-orphan")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class InterviewGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    company_name = db.Column(db.String(140), nullable=False)
    role = db.Column(db.String(140), nullable=False)
    interview_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.Integer, default=2, nullable=False)
    status = db.Column(db.String(20), default="Planned", nullable=False)
    notes = db.Column(db.Text, default="")
    job_description = db.Column(db.Text, default="")
    responsibilities = db.Column(db.Text, default="")
    preferred_qualifications = db.Column(db.Text, default="")
    company_notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tasks = db.relationship("GoalTask", backref="goal", lazy=True, cascade="all, delete-orphan")
    skills = db.relationship("Skill", backref="goal", lazy=True, cascade="all, delete-orphan")
    courses = db.relationship("Course", backref="goal", lazy=True, cascade="all, delete-orphan")


class GoalTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("interview_goal.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.Integer, default=2, nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("interview_goal.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    confidence_level = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="Not Started", nullable=False)
    notes = db.Column(db.Text, default="")
    resource_url = db.Column(db.String(500), default="")


course_skill = db.Table(
    "course_skill",
    db.Column("course_id", db.Integer, db.ForeignKey("course.id"), primary_key=True),
    db.Column("skill_id", db.Integer, db.ForeignKey("skill.id"), primary_key=True),
)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("interview_goal.id"), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    platform = db.Column(db.String(120), nullable=False, default="")
    url = db.Column(db.String(500), nullable=False, default="")
    instructor = db.Column(db.String(120), default="")
    total_lessons = db.Column(db.Integer, default=0, nullable=False)
    completed_lessons = db.Column(db.Integer, default=0, nullable=False)
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    skills = db.relationship("Skill", secondary=course_skill, backref="courses")
    chapters = db.relationship("Chapter", backref="course", lazy=True, cascade="all, delete-orphan")


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="Active", nullable=False)
    priority = db.Column(db.Integer, default=2, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    subtasks = db.relationship("ProjectSubTask", backref="project", lazy=True, cascade="all, delete-orphan")


class DailyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.Integer, default=2, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_type = db.Column(db.String(20), default="none", nullable=False)
    recurrence_interval_days = db.Column(db.Integer, default=1, nullable=False)
    recurrence_days_of_week = db.Column(db.String(50), default="", nullable=False)
    recurring = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=True)
    task_id = db.Column(db.Integer, db.ForeignKey("goal_task.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    google_doc_url = db.Column(db.String(500), default="")
    external_url = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    task = db.relationship("GoalTask", backref=db.backref("chapters", lazy=True, cascade="all, delete-orphan"))


class ProjectSubTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.Integer, default=2, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey("interview_goal.id"), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    goal = db.relationship("InterviewGoal")
