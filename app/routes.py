from flask import render_template, flash, redirect, url_for, request, jsonify, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, CommitForm, CommentForm
from app.models import User, Assignment, AU_Relationships, Event, EU_Relationships, Commit, Section, Post, CommitComment, AssignmentNotes
from datetime import datetime
from app import general_url
from functools import wraps
import os
from threading import Thread

# TODO- user image thumbnail,
# DONT PLAY WITH PYTHON


def set_options(form, section, assignment):
    form.course.choices = [(section.id, section.title)]
    form.assignment.choices = [(assignment.id, assignment.title)]


@app.route('/sync_all/<password>')
@login_required
def sync_all(password):
    if password == 'SyncAllPassword123':
        users = User.query.all()
        for user in users:
            print('--------------------updating', user.username)
            user.update()
    else:
        flash('Innacurate Credentials')
        return render_template(request.referrer)
    return render_template('testing_chat.html', posts=Post.query.filter_by(assignment_id=1).all())

@app.route("/create_post/<option>/<id>", methods=['POST'])
@login_required
def create_post(option, id):
    if option == 'commit_comment':
        form = CommentForm()
        if form.is_submitted():
            if len(form.comment_post.data) >= 140 or len(form.comment_post.data) <= 5:
                flash('Your post must be between 5 and 140 characters!')
                return redirect(request.referrer)
            else:
                addition = CommitComment(commit_id=id, user_id=current_user.id, comment=form.comment_post.data)
    else:
        if option == 'commit':
            form = CommitForm()
        else:
            form = PostForm()
        assignment_id = form.assignment.data
        schoology_id = Assignment.query.filter_by(id=assignment_id).first().schoology_id
        if form.is_submitted() and option == 'commit':
            if len(form.post.data) <= 5:
                flash('Your post must be longer than 5 characters!')
                return redirect(request.referrer)
            elif len(form.post.data) >= 140:
                flash('Your post must be shorter than 140 characters!')
                return redirect(request.referrer)
            elif type(form.time_spent.data) != int:
                flash('Your time spent must be a number')
                return redirect(request.referrer)
            elif schoology_id is None:
                flash('You cannot post about a sample assignment')
                return redirect(request.referrer)
            else:
                addition = Commit(user_id=int(current_user.id), assignment_id=int(assignment_id), schoology_id=int(schoology_id),
                        body=str(form.post.data), time_spent=int(form.time_spent.data))
        if form.is_submitted() and option == 'post':
            if len(form.post.data) <= 12:
                flash('Your post must be longer than 12 characters!')
                return redirect(request.referrer)
            elif schoology_id is None:
                flash('You cannot post about a sample assignment')
                return redirect(request.referrer)
            else:
                addition = Post(user_id=int(current_user.id), assignment_id=int(assignment_id), schoology_id=int(schoology_id),
                                body=form.post.data)

    db.session.add(addition)
    db.session.commit()
    flash('Congratulations for posting!')
    return redirect(request.referrer)

@app.route("/delete_post/<type>/<id>")
@login_required
def delete_post(type, id):
    if type.lower() == 'post':
        post = Post.query.filter_by(id=id).first()
    elif type.lower() == 'commit':
        post = Commit.query.filter_by(id=id).first()
    elif type.lower() == 'commit_comment':
        post = CommitComment.query.filter_by(id=id).first()
    else:
        flash('nothing to delete')
        return redirect(request.referrer)

    db.session.delete(post)
    db.session.commit()
    flash('Your' + str(type).lower() + 'comment has been deleted')
    return redirect(request.referrer)


def give_user_data():
    return [current_user.api_key, current_user.api_secret, current_user.outeruid]


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


def restricted(user, type):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            accessible = user.get_followed_courses()
            if type == 'section':
                course = int(kwargs['id'])
            elif type == 'assignment':
                course = Assignment.query.filter_by(id=int(kwargs['id'])).first_or_404().section_id
            if course not in accessible:
                flash('No access', 'warning')
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator


@app.route('/')
@app.route('/None')

def main():
    return redirect(url_for('index'))


@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    commit_form = CommitForm()
    commit_form.course.choices = [(section.id, section.title) for section in current_user.sections]
    commit_form.assignment.choices = []
    if commit_form.is_submitted():
        commit_form = CommitForm(formdata=None)

    comment_form = CommentForm()
    if comment_form.is_submitted():
        comment_form = CommentForm(formdata=None)

    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_commits().paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None

    return render_template('index.html', title='Home', posts=posts.items, commit_form=commit_form, comment_form=comment_form, next_url=next_url, prev_url=prev_url,
                           )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.capitalize(), email=form.email.data)
        user.set_password(form.password.data)
        user.set_api_info(form.consumer_key.data, form.consumer_secret.data)
        user.set_outeruid(form.consumer_key.data, form.consumer_secret.data)
        db.session.add(user)
        db.session.commit()
        # sync()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    comment_form = CommentForm()
    if comment_form.is_submitted():
        comment_form = CommentForm(formdata=None)
    page = request.args.get('page', 1, type=int)
    commits = user.commits.paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=commits.next_num) \
        if commits.has_next else None
    prev_url = url_for('explore', page=commits.prev_num) \
        if commits.has_prev else None
    return render_template("user.html", user=user, comment_form=comment_form, posts=commits.items, next_url=next_url, prev_url=prev_url)


@app.route('/assignment/<id>', methods=['GET', 'POST'])
@login_required
@restricted(user=current_user, type='assignment')
def assignment(id):
    assignment = Assignment.query.filter_by(id=id).first_or_404()
    section = Section.query.filter_by(id=assignment.section_id).first_or_404()

    # commit form
    commit_form = CommitForm()
    set_options(commit_form, section, assignment)
    if commit_form.is_submitted():
        commit_form = CommitForm(formdata=None)
        set_options(commit_form, section, assignment)

    post_form = PostForm()
    set_options(post_form, section, assignment)
    if post_form.is_submitted():
        post_form = PostForm(formdata=None)
        set_options(post_form, section, assignment)

    comment_form = CommentForm()
    if comment_form.is_submitted():
        comment_form = CommentForm(formdata=None)

    return render_template('_assignment.html', assignment=assignment, commit_form=commit_form, post_form=post_form, comment_form=comment_form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.about_me = form.about_me.data
        current_user.api_key = form.consumer_key.data
        current_user.api_secret = form.consumer_secret.data
        db.session.commit()
        flash('Your changes have been made')
        return redirect(request.referrer)
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.about_me.data = current_user.about_me
        form.consumer_key.data = current_user.api_key
        form.consumer_secret.data = current_user.api_secret
    return render_template('edit_profile.html', title='Edit Profile', form=form)



@app.route('/events')
@login_required
def events():
    events = current_user.events
    # events = Event.query.join(EU_Relationships,
    #                                     (EU_Relationships.c.user_id == current_user.id)
    #                                     ).order_by(Event.start.asc())
    return render_template('events.html', title='Events', events=events)


@app.route('/assignments')
@login_required
def assignments():
    assignments = []
    for a in current_user.assignments:
        timestamp = datetime.strptime('09/19/06 13:55:26', '%m/%d/%y %H:%M:%S')
        counter = 0
        commits = a.commits.filter_by(user_id=current_user.id)
        for commit in commits:
            counter += commit.time_spent
            if commit.timestamp >= timestamp:
                timestamp = commit.timestamp
        assignments.append([a, counter, timestamp])
    assignments_time_desc = sorted(assignments, key=lambda r: r[1])
    assignments_time_desc = [x[0] for x in assignments_time_desc]
    assignments_time_asc = sorted(assignments, key=lambda r: r[1], reverse=True)
    assignments_time_asc = [x[0] for x in assignments_time_asc]
    assignments_latest_commited = sorted(assignments, key=lambda r: r[2], reverse=True)
    assignments_latest_commited = [x[0] for x in assignments_latest_commited]

    return render_template('assignments.html', title='Assignments',
                           assignments_due_desc=sorted(current_user.assignments, key=lambda r: (r.due is not None, r.due), reverse=True),
                           assignments_due_asc=sorted(current_user.assignments, key=lambda r: (r.due is not None, r.due)),
                           assignments_time_desc=assignments_time_desc,
                           assignments_time_asc=assignments_time_asc,
                           latest_commited =assignments_latest_commited
                           )


@app.route('/sections')
@login_required
def sections():
    sections = current_user.sections
    return render_template('sections.html', title='Sections', sections=sections)

@app.route('/section/<id>')
@login_required
@restricted(user=current_user, type='section')
def section(id):
    section = Section.query.filter_by(id=id).first_or_404()
    sample_assignment = section.assignments[0]

    return render_template('_section.html', title=section.title, section=section,
                           affiliations=sample_assignment.get_affiliations(current_user))


@app.route('/sync')
@login_required
def sync():
    return render_template('sync.html', title='Syncing with Schoology')


@app.route('/retrieve_data')
@login_required
def retrieve_data():
    print('syncing ', current_user.username)
    current_user.update_sections()
    current_user.update_assignments()
    current_user.update_events()
    current_user.set_avatar()
    current_user.update_grades()
    flash('All synced up!')
    return render_template('sync.html')


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are no longer following {}.'.format(username))
    return redirect(url_for('user', username=username))

@app.route('/delete_follower/<username>')
@login_required
def delete_follower(username):
    user = User.query.filter_by(username=username).first()
    current_user.delete_follower(user)
    db.session.commit()
    flash(str(username) + ' no longer follows you')
    return redirect(url_for('user', username=current_user.username))

@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Commit.query.order_by(Commit.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template("index.html", title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)

@app.route('/set_assignment_choices/<section_id>')
@login_required
def set_assignment_choices(section_id):
    assignments = Section.query.filter_by(id=section_id).first().assignments
    assignment_array = []
    for a in assignments:
        a_obj = {}
        a_obj['id'] = a.id
        a_obj['title'] = a.title
        assignment_array.append(a_obj)

    return jsonify({'assignments': assignment_array})

@app.route('/like/<type>/<id>')
@login_required
def like(type, id):
    if type == 'commit':
        format = Commit.query.filter_by(id=int(id)).first_or_404()
    elif type == 'post':
        format = Post.query.filter_by(id=int(id)).first_or_404()
    elif type == 'commit_comment':
        format = CommitComment.query.filter_by(id=int(id)).first_or_404()
    format.like(current_user)
    flash('Post Liked')

    return redirect(request.referrer)

@app.route('/unlike/<type>/<id>')
@login_required
def unlike(type, id):
    if type == 'commit':
        format = Commit.query.filter_by(id=int(id)).first_or_404()
    elif type == 'commit_comment':
        format = CommitComment.query.filter_by(id=int(id)).first_or_404()
    elif type == 'post':
        format = Post.query.filter_by(id=int(id)).first_or_404()
    format.unlike(current_user)
    flash('Post Unliked')
    return redirect(request.referrer)


@app.route('/assignment_comment/<uid>/<assignment>', methods=['GET', 'POST'])
@login_required
def assignment_comment(uid, assignment):
    if request.method == 'POST':
        if AssignmentNotes.query.filter_by(user_id=int(uid), assignment_id=int(assignment)).count() == 0:
            note = AssignmentNotes(user_id=int(uid), assignment_id=int(assignment), body=str(request.form['notes']))
        else:
            note = AssignmentNotes.query.filter_by(user_id=int(uid), assignment_id=int(assignment)).first()
            note.update_body(str(request.form['notes']))
        db.session.add(note)
        db.session.commit()

    return redirect(request.referrer)