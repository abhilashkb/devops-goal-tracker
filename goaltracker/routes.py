from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import Activity, Chapter, Course, DailyTask, GoalTask, InterviewGoal, Project, ProjectSubTask, Skill, User
from .utils import (
    auto_detect_skills,
    course_progress,
    derive_skill_status,
    goal_progress,
    project_progress,
    parse_date,
    next_interval_date,
    next_weekly_date,
    recent_activity_messages,
    parse_weekdays,
    weekday_list,
    skill_readiness,
    task_completion,
    send_email,
)

bp = Blueprint("main", __name__)


def require_ownership(goal):
    return goal.user_id == current_user.id


def log_activity(message, goal_id=None):
    db.session.add(Activity(user_id=current_user.id, goal_id=goal_id, message=message))


def form_int(name, default=0, minimum=None, maximum=None):
    raw = request.form.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def sync_course_skills(course, goal):
    selected_skill_ids = request.form.getlist("skill_ids")
    if not selected_skill_ids:
        course.skills = []
        return
    skills = Skill.query.filter(Skill.id.in_(selected_skill_ids), Skill.goal_id == goal.id).all()
    course.skills = skills


def resolve_default_goal(goals, goal_id=None):
    if goal_id:
        selected = InterviewGoal.query.get(goal_id)
        if selected and require_ownership(selected):
            return selected
    return goals[0] if goals else None


def chapter_parent_goal(chapter):
    parent = chapter.course or chapter.task
    return parent.goal if parent else None


@bp.route("/")
@login_required
def dashboard():
    goals = InterviewGoal.query.filter_by(user_id=current_user.id).order_by(InterviewGoal.updated_at.desc()).all()
    daily_tasks = DailyTask.query.filter_by(user_id=current_user.id).order_by(DailyTask.completed.asc(), DailyTask.priority.asc()).all()
    activities = Activity.query.filter_by(user_id=current_user.id).order_by(Activity.created_at.desc()).limit(6).all()

    goal_ids = [goal.id for goal in goals]
    upcoming_tasks = (
        GoalTask.query.filter(GoalTask.goal_id.in_(goal_ids), GoalTask.completed.is_(False), GoalTask.due_date.isnot(None))
        .order_by(GoalTask.due_date.asc())
        .limit(5)
        .all()
        if goal_ids
        else []
    )
    upcoming_interviews = [goal for goal in goals if goal.interview_date and goal.interview_date >= date.today()]
    strong_skills = []
    weak_skills = []
    active_courses = []
    for goal in goals:
        strong, weak = derive_skill_status(goal.skills)
        strong_skills.extend(strong)
        weak_skills.extend(weak)
        active_courses.extend(goal.courses)

    goal_metrics = [{"label": goal.title, "progress": goal_progress(goal)} for goal in goals[:6]]
    task_metrics = [{"label": goal.title, "progress": task_completion(goal)} for goal in goals[:6]]
    course_metrics = []
    for course in active_courses[:6]:
        course_metrics.append({"label": course.name, "progress": course_progress(course)})

    dashboard_stats = {
        "goals": len(goals),
        "pending_tasks": sum(1 for task in daily_tasks if not task.completed),
        "courses": len(active_courses),
        "weak_skills": len(weak_skills),
    }

    return render_template(
        "dashboard.html",
        goals=goals,
        daily_tasks=daily_tasks,
        activities=activities,
        upcoming_tasks=upcoming_tasks,
        upcoming_interviews=upcoming_interviews,
        strong_skills=strong_skills[:6],
        weak_skills=weak_skills[:6],
        active_courses=active_courses[:6],
        goal_metrics=goal_metrics,
        task_metrics=task_metrics,
        course_metrics=course_metrics,
        dashboard_stats=dashboard_stats,
        today=date.today(),
        goal_progress=goal_progress,
    )


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Please fill in all required fields.", "danger")
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash("That username or email is already in use.", "danger")
        else:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created. Welcome aboard.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Welcome back.", "success")
            return redirect(url_for("main.dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name", "").strip()
        current_user.bio = request.form.get("bio", "").strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("main.profile"))
    return render_template("profile.html")


@bp.route("/goals")
@login_required
def goals():
    items = InterviewGoal.query.filter_by(user_id=current_user.id).order_by(InterviewGoal.updated_at.desc()).all()
    return render_template("goals/list.html", goals=items, goal_progress=goal_progress)


@bp.route("/courses")
@login_required
def courses():
    items = (
        Course.query.join(InterviewGoal)
        .filter(InterviewGoal.user_id == current_user.id)
        .order_by(Course.created_at.desc())
        .all()
    )
    return render_template("courses/list.html", courses=items, course_progress=course_progress)


@bp.route("/skills")
@login_required
def skills():
    goals = InterviewGoal.query.filter_by(user_id=current_user.id).order_by(InterviewGoal.updated_at.desc()).all()
    skills = []
    for goal in goals:
        for skill in goal.skills:
            skills.append(skill)
    strong_skills, weak_skills = derive_skill_status(skills)
    return render_template(
        "skills/list.html",
        skills=skills,
        goals=goals,
        strong_skills=strong_skills,
        weak_skills=weak_skills,
        skill_readiness=skill_readiness,
        derive_skill_status=derive_skill_status,
    )


@bp.route("/skills/new", methods=["POST"])
@login_required
def skills_create():
    """Create a new skill from the global skills page. Expects form field `goal_id`."""
    goals = InterviewGoal.query.filter_by(user_id=current_user.id).all()
    raw_goal_id = request.form.get("goal_id")
    if not raw_goal_id:
        flash("Please select a goal for the new skill.", "danger")
        return redirect(url_for("main.skills"))
    try:
        goal_id = int(raw_goal_id)
    except ValueError:
        flash("Invalid goal selected.", "danger")
        return redirect(url_for("main.skills"))
    goal = InterviewGoal.query.get_or_404(goal_id)
    if not require_ownership(goal):
        flash("You do not have access to that goal.", "danger")
        return redirect(url_for("main.skills"))

    skill = Skill(
        goal_id=goal.id,
        name=request.form.get("name", "").strip(),
        confidence_level=form_int("confidence_level", 1, 1, 5),
        status=request.form.get("status", "Not Started"),
        notes=request.form.get("notes", "").strip(),
        resource_url=request.form.get("resource_url", "").strip(),
    )
    db.session.add(skill)
    db.session.commit()
    log_activity(f"Added skill: {skill.name}", goal.id)
    db.session.commit()
    flash("Skill added.", "success")
    return redirect(url_for("main.skills"))


@bp.route("/courses/new", methods=["GET", "POST"])
@login_required
def course_create():
    goals = InterviewGoal.query.filter_by(user_id=current_user.id).order_by(InterviewGoal.updated_at.desc()).all()
    if request.method == "POST":
        goal = resolve_default_goal(goals, request.form.get("goal_id"))
        if goal is None:
            flash("Create a project first, then add a course.", "danger")
            return redirect(url_for("main.courses"))
        course = Course(
            goal_id=goal.id,
            name=request.form.get("name", "").strip(),
            platform=request.form.get("platform", "").strip(),
            url=request.form.get("url", "").strip(),
            instructor=request.form.get("instructor", "").strip(),
            total_lessons=form_int("total_lessons", 0, 0),
            completed_lessons=form_int("completed_lessons", 0, 0),
            notes=request.form.get("notes", "").strip(),
        )
        db.session.add(course)
        db.session.flush()
        sync_course_skills(course, goal)
        db.session.commit()
        log_activity(f"Added course: {course.name}", goal.id)
        db.session.commit()
        flash("Course added.", "success")
        return redirect(url_for("main.courses"))
    return render_template("courses/course_form.html", goals=goals, goal=resolve_default_goal(goals), selected_skill_ids=set())


@bp.route("/project-tasks")
@login_required
def project_tasks():
    return redirect(url_for("main.projects"))


@bp.route("/project-tasks/new", methods=["GET", "POST"])
@login_required
def project_task_create():
    return redirect(url_for("main.projects"))


@bp.route("/projects", methods=["GET"])
@login_required
def projects():
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.updated_at.desc()).all()
    overall_progress, completed_subtasks, total_subtasks = project_progress_summary(projects)
    return render_template(
        "tasks/progress.html",
        projects=projects,
        overall_progress=overall_progress,
        completed_tasks=completed_subtasks,
        total_tasks=total_subtasks,
        project_progress=project_progress,
    )


def project_progress_summary(projects):
    subtasks = [subtask for project in projects for subtask in project.subtasks]
    total = len(subtasks)
    completed = sum(1 for subtask in subtasks if subtask.completed)
    progress = round((completed / total) * 100) if total else 0
    return progress, completed, total


@bp.route("/projects/new", methods=["GET", "POST"])
@login_required
def project_create():
    if request.method == "POST":
        project = Project(
            user_id=current_user.id,
            title=request.form.get("title", "").strip(),
            description=request.form.get("description", "").strip(),
            status=request.form.get("status", "Active"),
            priority=form_int("priority", 2, 1, 5),
        )
        db.session.add(project)
        db.session.commit()
        flash("Project created.", "success")
        return redirect(url_for("main.projects"))
    return render_template("tasks/project_form.html")


@bp.route("/projects/<int:project_id>/subtasks/new", methods=["POST"])
@login_required
def project_subtask_new(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash("You do not have access to that project.", "danger")
        return redirect(url_for("main.projects"))
    subtask = ProjectSubTask(
        project_id=project.id,
        title=request.form.get("title", "").strip(),
        progress=form_int("progress", 0, 0, 100),
        completed=request.form.get("completed") == "on",
        due_date=parse_date(request.form.get("due_date", "")),
        priority=form_int("priority", 2, 1, 5),
    )
    if subtask.completed:
        subtask.progress = 100
    db.session.add(subtask)
    db.session.commit()
    flash("Sub-task added.", "success")
    return redirect(url_for("main.projects"))


@bp.route("/projects/<int:project_id>/subtasks/<int:subtask_id>/edit", methods=["POST"])
@login_required
def project_subtask_edit(project_id, subtask_id):
    project = Project.query.get_or_404(project_id)
    subtask = ProjectSubTask.query.get_or_404(subtask_id)
    if subtask.project_id != project.id or project.user_id != current_user.id:
        flash("You do not have access to that sub-task.", "danger")
        return redirect(url_for("main.projects"))
    subtask.title = request.form.get("title", "").strip() or subtask.title
    subtask.progress = form_int("progress", subtask.progress, 0, 100)
    subtask.completed = request.form.get("completed") == "on"
    if subtask.completed:
        subtask.progress = 100
    subtask.due_date = parse_date(request.form.get("due_date", ""))
    subtask.priority = form_int("priority", 2, 1, 5)
    db.session.commit()
    flash("Sub-task updated.", "success")
    return redirect(url_for("main.projects"))


@bp.route("/projects/<int:project_id>/subtasks/<int:subtask_id>/toggle", methods=["POST"])
@login_required
def project_subtask_toggle(project_id, subtask_id):
    project = Project.query.get_or_404(project_id)
    subtask = ProjectSubTask.query.get_or_404(subtask_id)
    if subtask.project_id != project.id or project.user_id != current_user.id:
        flash("You do not have access to that sub-task.", "danger")
        return redirect(url_for("main.projects"))
    subtask.completed = not subtask.completed
    subtask.progress = 100 if subtask.completed else min(subtask.progress or 0, 99)
    db.session.commit()
    flash("Sub-task updated.", "success")
    return redirect(url_for("main.projects"))


@bp.route("/projects/<int:project_id>/subtasks/<int:subtask_id>/delete", methods=["POST"])
@login_required
def project_subtask_delete(project_id, subtask_id):
    project = Project.query.get_or_404(project_id)
    subtask = ProjectSubTask.query.get_or_404(subtask_id)
    if subtask.project_id != project.id or project.user_id != current_user.id:
        flash("You do not have access to that sub-task.", "danger")
        return redirect(url_for("main.projects"))
    db.session.delete(subtask)
    db.session.commit()
    flash("Sub-task deleted.", "info")
    return redirect(url_for("main.projects"))


def clone_recurring_task(task):
    if not task.recurring or task.recurrence_type == "none":
        return
    due_date = task.due_date or date.today()
    if task.recurrence_type == "interval":
        next_due = next_interval_date(due_date, task.recurrence_interval_days)
    elif task.recurrence_type == "weekly":
        next_due = next_weekly_date(due_date, weekday_list(task.recurrence_days_of_week))
    else:
        return
    db.session.add(
        DailyTask(
            user_id=task.user_id,
            title=task.title,
            due_date=next_due,
            priority=task.priority,
            recurring=True,
            recurrence_type=task.recurrence_type,
            recurrence_interval_days=task.recurrence_interval_days,
            recurrence_days_of_week=task.recurrence_days_of_week,
        )
    )


@bp.route("/goals/new", methods=["GET", "POST"])
@login_required
def goal_new():
    if request.method == "POST":
        goal = InterviewGoal(
            user_id=current_user.id,
            title=request.form.get("title", "").strip(),
            company_name=request.form.get("company_name", "").strip(),
            role=request.form.get("role", "").strip(),
            interview_date=parse_date(request.form.get("interview_date", "")),
            priority=form_int("priority", 2, 1, 5),
            status=request.form.get("status", "Planned"),
            notes=request.form.get("notes", "").strip(),
            job_description=request.form.get("job_description", "").strip(),
            responsibilities=request.form.get("responsibilities", "").strip(),
            preferred_qualifications=request.form.get("preferred_qualifications", "").strip(),
            company_notes=request.form.get("company_notes", "").strip(),
        )
        db.session.add(goal)
        db.session.flush()
        for skill_name in auto_detect_skills(goal.job_description):
            db.session.add(Skill(goal_id=goal.id, name=skill_name, confidence_level=2, status="Learning"))
        db.session.commit()
        log_activity(f"Created interview goal: {goal.title}", goal.id)
        db.session.commit()
        flash("Interview goal created.", "success")
        return redirect(url_for("main.goal_detail", goal_id=goal.id))
    return render_template("goals/form.html", goal=None)


@bp.route("/goals/<int:goal_id>")
@login_required
def goal_detail(goal_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    if not require_ownership(goal):
        flash("You do not have access to that goal.", "danger")
        return redirect(url_for("main.dashboard"))
    strong_skills, weak_skills = derive_skill_status(goal.skills)
    return render_template(
        "goals/detail.html",
        goal=goal,
        goal_progress=goal_progress,
        task_completion=task_completion,
        course_progress=course_progress,
        skill_readiness=skill_readiness,
        strong_skills=strong_skills,
        weak_skills=weak_skills,
    )


@bp.route("/goals/<int:goal_id>/edit", methods=["GET", "POST"])
@login_required
def goal_edit(goal_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    if not require_ownership(goal):
        flash("You do not have access to that goal.", "danger")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        goal.title = request.form.get("title", "").strip()
        goal.company_name = request.form.get("company_name", "").strip()
        goal.role = request.form.get("role", "").strip()
        goal.interview_date = parse_date(request.form.get("interview_date", ""))
        goal.priority = form_int("priority", 2, 1, 5)
        goal.status = request.form.get("status", "Planned")
        goal.notes = request.form.get("notes", "").strip()
        goal.job_description = request.form.get("job_description", "").strip()
        goal.responsibilities = request.form.get("responsibilities", "").strip()
        goal.preferred_qualifications = request.form.get("preferred_qualifications", "").strip()
        goal.company_notes = request.form.get("company_notes", "").strip()
        db.session.commit()
        flash("Goal updated.", "success")
        return redirect(url_for("main.goal_detail", goal_id=goal.id))
    return render_template("goals/form.html", goal=goal)


@bp.route("/goals/<int:goal_id>/delete", methods=["POST"])
@login_required
def goal_delete(goal_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    if not require_ownership(goal):
        flash("You do not have access to that goal.", "danger")
        return redirect(url_for("main.dashboard"))
    db.session.delete(goal)
    db.session.commit()
    flash("Goal deleted.", "info")
    return redirect(url_for("main.goals"))


@bp.route("/goals/<int:goal_id>/tasks/new", methods=["GET", "POST"])
@login_required
def task_new(goal_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    if not require_ownership(goal):
        flash("You do not have access to that goal.", "danger")
        return redirect(url_for("main.dashboard"))
    if request.method == "GET":
        return render_template("tasks/task_form.html", goal=goal)
    task = GoalTask(
        goal_id=goal.id,
        title=request.form.get("title", "").strip(),
        due_date=parse_date(request.form.get("due_date", "")),
        priority=form_int("priority", 2, 1, 5),
        progress=form_int("progress", 0, 0, 100),
        completed=request.form.get("completed") == "on",
    )
    db.session.add(task)
    db.session.commit()
    log_activity(f"Added task: {task.title}", goal.id)
    db.session.commit()
    flash("Task added.", "success")
    return redirect(url_for("main.goal_detail", goal_id=goal.id))


@bp.route("/goals/<int:goal_id>/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def task_edit(goal_id, task_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    task = GoalTask.query.get_or_404(task_id)
    if task.goal_id != goal.id or not require_ownership(goal):
        flash("You do not have access to that task.", "danger")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        task.title = request.form.get("title", "").strip()
        task.due_date = parse_date(request.form.get("due_date", ""))
        task.priority = form_int("priority", 2, 1, 5)
        task.progress = form_int("progress", task.progress, 0, 100)
        task.completed = request.form.get("completed") == "on"
        if task.completed:
            task.progress = 100
        db.session.commit()
        log_activity(f"Updated task: {task.title}", goal.id)
        db.session.commit()
        flash("Task updated.", "success")
        return redirect(url_for("main.goal_detail", goal_id=goal.id))
    return render_template("goals/task_form.html", goal=goal, task=task)


@bp.route("/tasks/<int:task_id>/chapters/new", methods=["POST"])
@login_required
def task_chapter_new(task_id):
    task = GoalTask.query.get_or_404(task_id)
    if not require_ownership(task.goal):
        flash("You do not have access to that task.", "danger")
        return redirect(url_for("main.project_tasks"))
    chapter = Chapter(
        task_id=task.id,
        title=request.form.get("title", "").strip() or "Untitled chapter",
        progress=form_int("progress", 0, 0, 100),
        completed=request.form.get("completed") == "on",
        google_doc_url=request.form.get("google_doc_url", "").strip(),
        external_url=request.form.get("external_url", "").strip(),
    )
    db.session.add(chapter)
    db.session.commit()
    flash("Chapter added.", "success")
    return redirect(url_for("main.project_tasks"))


@bp.route("/chapters/<int:chapter_id>/edit", methods=["POST"])
@login_required
def chapter_edit(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    parent_goal = chapter_parent_goal(chapter)
    if parent_goal is None or not require_ownership(parent_goal):
        flash("You do not have access to that chapter.", "danger")
        return redirect(url_for("main.courses"))
    chapter.title = request.form.get("title", "").strip() or chapter.title
    chapter.progress = form_int("progress", chapter.progress, 0, 100)
    chapter.completed = request.form.get("completed") == "on"
    chapter.google_doc_url = request.form.get("google_doc_url", "").strip()
    chapter.external_url = request.form.get("external_url", "").strip()
    db.session.commit()
    flash("Chapter updated.", "success")
    return redirect(request.referrer or url_for("main.courses"))


@bp.route("/chapters/<int:chapter_id>/delete", methods=["POST"])
@login_required
def chapter_delete(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    parent_goal = chapter_parent_goal(chapter)
    if parent_goal is None or not require_ownership(parent_goal):
        flash("You do not have access to that chapter.", "danger")
        return redirect(url_for("main.courses"))
    db.session.delete(chapter)
    db.session.commit()
    flash("Chapter deleted.", "info")
    return redirect(request.referrer or url_for("main.courses"))


@bp.route("/chapters/<int:chapter_id>/toggle", methods=["POST"])
@login_required
def chapter_toggle(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    parent_goal = chapter_parent_goal(chapter)
    if parent_goal is None or not require_ownership(parent_goal):
        flash("You do not have access to that chapter.", "danger")
        return redirect(url_for("main.courses"))
    chapter.completed = not chapter.completed
    chapter.progress = 100 if chapter.completed else min(chapter.progress or 0, 99)
    db.session.commit()
    flash("Chapter updated.", "success")
    return redirect(request.referrer or url_for("main.courses"))


@bp.route("/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def task_toggle(task_id):
    task = GoalTask.query.get_or_404(task_id)
    if not require_ownership(task.goal):
        flash("You do not have access to that task.", "danger")
        return redirect(url_for("main.dashboard"))
    task.completed = not task.completed
    db.session.commit()
    log_activity(f"Marked task {'complete' if task.completed else 'incomplete'}: {task.title}", task.goal_id)
    db.session.commit()
    flash("Task updated.", "success")
    return redirect(url_for("main.goal_detail", goal_id=task.goal_id))


@bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def task_delete(task_id):
    task = GoalTask.query.get_or_404(task_id)
    goal_id = task.goal_id
    if not require_ownership(task.goal):
        flash("You do not have access to that task.", "danger")
        return redirect(url_for("main.dashboard"))
    db.session.delete(task)
    db.session.commit()
    log_activity("Deleted a preparation task", goal_id)
    db.session.commit()
    flash("Task deleted.", "info")
    return redirect(url_for("main.goal_detail", goal_id=goal_id))


@bp.route("/goals/<int:goal_id>/skills/new", methods=["POST"])
@login_required
def skill_new(goal_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    if not require_ownership(goal):
        flash("You do not have access to that goal.", "danger")
        return redirect(url_for("main.dashboard"))
    skill = Skill(
        goal_id=goal.id,
        name=request.form.get("name", "").strip(),
        confidence_level=form_int("confidence_level", 1, 1, 5),
        status=request.form.get("status", "Not Started"),
        notes=request.form.get("notes", "").strip(),
        resource_url=request.form.get("resource_url", "").strip(),
    )
    db.session.add(skill)
    db.session.commit()
    log_activity(f"Added skill: {skill.name}", goal.id)
    db.session.commit()
    flash("Skill added.", "success")
    return redirect(url_for("main.goal_detail", goal_id=goal.id))


@bp.route("/goals/<int:goal_id>/skills/<int:skill_id>/edit", methods=["GET", "POST"])
@login_required
def skill_edit(goal_id, skill_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    skill = Skill.query.get_or_404(skill_id)
    if skill.goal_id != goal.id or not require_ownership(goal):
        flash("You do not have access to that skill.", "danger")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        skill.name = request.form.get("name", "").strip()
        skill.confidence_level = form_int("confidence_level", 1, 1, 5)
        skill.status = request.form.get("status", "Not Started")
        skill.notes = request.form.get("notes", "").strip()
        skill.resource_url = request.form.get("resource_url", "").strip()
        db.session.commit()
        log_activity(f"Updated skill: {skill.name}", goal.id)
        db.session.commit()
        flash("Skill updated.", "success")
        return redirect(url_for("main.goal_detail", goal_id=goal.id))
    return render_template("goals/skill_form.html", goal=goal, skill=skill)


@bp.route("/skills/<int:skill_id>/update", methods=["POST"])
@login_required
def skill_update(skill_id):
    """AJAX-friendly endpoint to update a skill's editable fields.

    Accepts JSON or form-encoded data with: name, confidence_level, status, notes.
    Returns JSON with success flag and updated fields (including readiness).
    """
    skill = Skill.query.get_or_404(skill_id)
    if not require_ownership(skill.goal):
        return jsonify({"success": False, "error": "unauthorized"}), 403

    data = request.get_json(silent=True) or request.form
    # update fields with safe parsing
    skill.name = (data.get("name", "") or "").strip()
    try:
        skill.confidence_level = int(data.get("confidence_level", skill.confidence_level))
    except (TypeError, ValueError):
        # leave unchanged on bad input
        pass
    skill.status = (data.get("status", skill.status) or skill.status)
    skill.notes = (data.get("notes", "") or "").strip()
    db.session.commit()
    log_activity(f"Updated skill: {skill.name}", skill.goal_id)
    db.session.commit()

    # compute readiness via helper exposed earlier
    readiness = skill_readiness(skill)

    return jsonify(
        {
            "success": True,
            "skill": {
                "id": skill.id,
                "name": skill.name,
                "confidence_level": skill.confidence_level,
                "status": skill.status,
                "notes": skill.notes,
                "readiness": readiness,
            },
        }
    )


@bp.route("/skills/<int:skill_id>/delete", methods=["POST"])
@login_required
def skill_delete(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    goal_id = skill.goal_id
    if not require_ownership(skill.goal):
        flash("You do not have access to that skill.", "danger")
        return redirect(url_for("main.dashboard"))
    db.session.delete(skill)
    db.session.commit()
    log_activity("Removed a skill from the tracker", goal_id)
    db.session.commit()
    flash("Skill removed.", "info")
    return redirect(url_for("main.goal_detail", goal_id=goal_id))


@bp.route("/goals/<int:goal_id>/courses/new", methods=["GET", "POST"])
@login_required
def course_new(goal_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    if not require_ownership(goal):
        flash("You do not have access to that goal.", "danger")
        return redirect(url_for("main.dashboard"))
    if request.method == "GET":
        return render_template("courses/course_form.html", goal=goal, course=None, selected_skill_ids=set())
    course = Course(
        goal_id=goal.id,
        name=request.form.get("name", "").strip(),
        platform=request.form.get("platform", "").strip(),
        url=request.form.get("url", "").strip(),
        instructor=request.form.get("instructor", "").strip(),
        total_lessons=form_int("total_lessons", 0, 0),
        completed_lessons=form_int("completed_lessons", 0, 0),
        notes=request.form.get("notes", "").strip(),
    )
    db.session.add(course)
    db.session.flush()
    sync_course_skills(course, goal)
    db.session.commit()
    log_activity(f"Added course: {course.name}", goal.id)
    db.session.commit()
    flash("Course added.", "success")
    return redirect(url_for("main.goal_detail", goal_id=goal.id))


@bp.route("/goals/<int:goal_id>/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
def course_edit(goal_id, course_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    course = Course.query.get_or_404(course_id)
    if course.goal_id != goal.id or not require_ownership(goal):
        flash("You do not have access to that course.", "danger")
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        course.name = request.form.get("name", "").strip()
        course.platform = request.form.get("platform", "").strip()
        course.url = request.form.get("url", "").strip()
        course.instructor = request.form.get("instructor", "").strip()
        course.total_lessons = form_int("total_lessons", 0, 0)
        course.completed_lessons = form_int("completed_lessons", 0, 0)
        course.notes = request.form.get("notes", "").strip()
        sync_course_skills(course, goal)
        db.session.commit()
        log_activity(f"Updated course: {course.name}", goal.id)
        db.session.commit()
        flash("Course updated.", "success")
        return redirect(url_for("main.goal_detail", goal_id=goal.id))
    selected_skill_ids = {skill.id for skill in course.skills}
    return render_template("goals/course_form.html", goal=goal, course=course, selected_skill_ids=selected_skill_ids)


@bp.route("/courses/<int:course_id>/chapters/new", methods=["POST"])
@login_required
def course_chapter_new(course_id):
    course = Course.query.get_or_404(course_id)
    if not require_ownership(course.goal):
        flash("You do not have access to that course.", "danger")
        return redirect(url_for("main.courses"))
    chapter = Chapter(
        course_id=course.id,
        title=request.form.get("title", "").strip() or "Untitled chapter",
        progress=form_int("progress", 0, 0, 100),
        google_doc_url=request.form.get("google_doc_url", "").strip(),
        external_url=request.form.get("external_url", "").strip(),
    )
    db.session.add(chapter)
    db.session.commit()
    flash("Chapter added.", "success")
    return redirect(url_for("main.courses"))


@bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
def course_delete(course_id):
    course = Course.query.get_or_404(course_id)
    goal_id = course.goal_id
    if not require_ownership(course.goal):
        flash("You do not have access to that course.", "danger")
        return redirect(url_for("main.dashboard"))
    db.session.delete(course)
    db.session.commit()
    log_activity("Removed a course", goal_id)
    db.session.commit()
    flash("Course deleted.", "info")
    return redirect(url_for("main.goal_detail", goal_id=goal_id))


@bp.route("/daily", methods=["GET", "POST"])
@login_required
def daily():
    if request.method == "POST":
        recurrence_type = request.form.get("recurrence_type", "none")
        recurrence_interval_days = form_int("recurrence_interval_days", 1, 1, 365)
        recurrence_days_of_week = parse_weekdays(request.form.getlist("recurrence_days_of_week"))
        recurring = recurrence_type != "none"
        item = DailyTask(
            user_id=current_user.id,
            title=request.form.get("title", "").strip(),
            due_date=parse_date(request.form.get("due_date", "")),
            priority=form_int("priority", 2, 1, 5),
            recurring=recurring,
            recurrence_type=recurrence_type if recurring else "none",
            recurrence_interval_days=recurrence_interval_days,
            recurrence_days_of_week=recurrence_days_of_week,
        )
        db.session.add(item)
        db.session.commit()
        flash("Daily task added.", "success")
        return redirect(url_for("main.daily"))
    items = DailyTask.query.filter_by(user_id=current_user.id).order_by(DailyTask.completed.asc(), DailyTask.priority.asc()).all()
    return render_template("daily.html", daily_tasks=items)


@bp.route("/daily/<int:item_id>/toggle", methods=["POST"])
@login_required
def daily_toggle(item_id):
    item = DailyTask.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("You do not have access to that task.", "danger")
        return redirect(url_for("main.daily"))
    item.completed = not item.completed
    if item.completed:
        clone_recurring_task(item)
    db.session.commit()
    flash("Daily task updated.", "success")
    return redirect(url_for("main.daily"))


@bp.route("/daily/<int:item_id>/delete", methods=["POST"])
@login_required
def daily_delete(item_id):
    item = DailyTask.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash("You do not have access to that task.", "danger")
        return redirect(url_for("main.daily"))
    db.session.delete(item)
    db.session.commit()
    flash("Daily task deleted.", "info")
    return redirect(url_for("main.daily"))


@bp.route("/daily/send-summary", methods=["POST"])  # small action from the daily page
@login_required
def daily_send_summary():
    """Compile a short summary of today's daily tasks and email it to the current user."""
    # Gather today's tasks for the user
    tasks = DailyTask.query.filter_by(user_id=current_user.id).order_by(DailyTask.completed.asc(), DailyTask.priority.asc()).all()
    open_tasks = [t for t in tasks if not t.completed]
    completed_tasks = [t for t in tasks if t.completed]

    subject = f"Daily summary for {current_user.full_name or current_user.username} - {date.today().isoformat()}"
    lines = []
    lines.append(f"Daily summary generated by GoalTracker on {date.today().strftime('%b %d, %Y')}")
    lines.append("")
    lines.append(f"Open tasks ({len(open_tasks)}):")
    for t in open_tasks:
        due = f" (due {t.due_date.strftime('%b %d')})" if t.due_date else ""
        lines.append(f" - [{t.priority}] {t.title}{due}")
    lines.append("")
    lines.append(f"Completed tasks ({len(completed_tasks)}):")
    for t in completed_tasks:
        lines.append(f" - {t.title}")

    body = "\n".join(lines)

    to_address = current_user.email
    success, error = send_email(to_address, subject, body)
    if success:
        flash("Daily summary sent to your email.", "success")
    else:
        flash(f"Failed to send email: {error}", "danger")
    return redirect(url_for("main.daily"))


@bp.route("/goals/<int:goal_id>/derive-skills", methods=["POST"])
@login_required
def derive_skills(goal_id):
    goal = InterviewGoal.query.get_or_404(goal_id)
    if not require_ownership(goal):
        flash("You do not have access to that goal.", "danger")
        return redirect(url_for("main.dashboard"))
    existing = {skill.name.lower() for skill in goal.skills}
    created = 0
    for skill_name in auto_detect_skills(goal.job_description):
        if skill_name.lower() not in existing:
            db.session.add(Skill(goal_id=goal.id, name=skill_name, confidence_level=2, status="Learning"))
            created += 1
    db.session.commit()
    flash(f"Added {created} suggested skill(s).", "success")
    return redirect(url_for("main.goal_detail", goal_id=goal.id))
