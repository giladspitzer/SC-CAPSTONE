from datetime import datetime
from app import app, db, login
from time import time
import jwt
from flask import request
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import app.apiclean as sc
from dateutil.parser import parse

import pprint

from hashlib import md5

general_url = 'http://127.0.0.1:5000/'


@login.user_loader  # explain
def load_user(id):
    return User.query.get(int(id))

Post_Comment_Likes = db.Table('Post_Comment_Likes',
                      db.Column('comment_id', db.Integer, db.ForeignKey('post_comment.id')),
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
                      )

Commit_Comment_Likes = db.Table('Commit_Comment_Likes',
                      db.Column('comment_id', db.Integer, db.ForeignKey('commit_comment.id')),
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
                      )

Post_Likes = db.Table('Post_Likes',
                      db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
                      )


Commit_Likes = db.Table('Commit_Likes',
                        db.Column('commit_id', db.Integer, db.ForeignKey('commit.id')),
                        db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
                        )

AU_Relationships = db.Table('AU_Relationships',
                            db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                            db.Column('assignment_id', db.Integer, db.ForeignKey('assignment.id'))
                            )

EU_Relationships = db.Table('AE_Relationships',
                            db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                            db.Column('event_id', db.Integer, db.ForeignKey('event.id'))
                            )

followers = db.Table('followers',
                     db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
                     db.Column('followed_id', db.Integer, db.ForeignKey('user.id')),
                     db.Column('status', db.Integer)
                     )

SE_Relationships = db.Table('SE_Relationships',
                            db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                            db.Column('section_id', db.Integer, db.ForeignKey('section.id'))
                            )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    api_key = db.Column(db.String(128))
    api_secret = db.Column(db.String(128))
    outeruid = db.Column(db.String(128))
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    picture_url = db.Column(db.String())
    commits = db.relationship('Commit', backref='author', lazy='dynamic', order_by='desc(Commit.timestamp)')  # explain
    posts = db.relationship('Post', backref='author', lazy='dynamic')  # explain
    assignments = db.relationship('Assignment',
                                  secondary=AU_Relationships,
                                  backref=db.backref('students', lazy='dynamic'),
                                  order_by='desc(Assignment.due)'
                                  )
    events = db.relationship('Event',
                             secondary=EU_Relationships,
                             backref=db.backref('students', lazy='dynamic'),
                             order_by='desc(Event.start)'
                             )
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    sections = db.relationship('Section',
                               secondary=SE_Relationships,
                               backref=db.backref('students', lazy='dynamic')
                               )
    grades = db.relationship('SectionGrade', backref='author', lazy='dynamic')  # explain
    commit_comments = db.relationship('CommitComment', backref='author', lazy='dynamic')  # explain
    post_comments = db.relationship('PostComment', backref='author', lazy='dynamic')  # explain
    notes = db.relationship('AssignmentNotes', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_api_info(self, key, secret):
        self.api_key = key
        self.api_secret = secret

    def set_outeruid(self, key, secret):
        self.outeruid = sc.get_user_id(key, secret)

    def set_avatar(self):
        # digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        # return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
        #     digest, size)\
        self.picture_url = sc.get_pic(self.api_key, self.api_secret)
        db.session.add(self)
        db.session.commit()

    # def request_follow(self, user):
    #     if not self.is_following(user):

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def delete_follower(self, user):
        if user.is_following(self):
            user.followed.remove(self)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_commits(self):
        followed_commits = Commit.query.join(
            followers, (followers.c.followed_id == Commit.user_id)).filter(
            followers.c.follower_id == self.id)
        own_commits = Commit.query.filter_by(user_id=self.id)
        return followed_commits.union(own_commits).order_by(Commit.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def trending_discussions(self):
        trending = []
        for a in self.assignments:
            posts = sorted(a.posts.all(), key=lambda r: r.timestamp, reverse=True)
            if len(posts) > 0:
                post = posts[0]
                if len(trending) < 5:
                    trending.append(post)
                else:
                    if post.timestamp >= trending[0].timestamp:
                        trending.insert(0, post)
        assignments = []
        for x in sorted(trending[:5], key=lambda r: r.timestamp, reverse=True):
            assignments.append(Assignment.query.filter_by(id=x.assignment_id).first())
        return assignments

    def update_assignments(self):
        for s in self.sections:
            assignments = sc.get_section_assignments([self.api_key, self.api_secret], s.schoology_id)
            if len(assignments) > 0:
                for a in assignments:
                    if Assignment.query.filter_by(section_id=s.id, title='Sample Assignment').count() > 0:
                        assignment = Assignment.query.filter_by(section_id=s.id, title='Sample Assignment').first()
                        db.session.remove(assignment)
                    if not bool(Assignment.query.filter_by(schoology_id=a.id).first()):  # if no assignment exists then create one
                        assignment = Assignment(schoology_id=a.id, web_url=a.web_url, section_id=s.id, course=s.title,
                                                img=s.img)
                        assignment.update_title(a.title)
                        assignment.update_description(a.description)
                        assignment.update_due(a.due)
                        assignment.users.append(self)
                        print('Added ' + str(a.title))
                    else:
                        assignment = Assignment.query.filter_by(schoology_id=a.id).first()
                        if not bool(db.session.query(AU_Relationships).filter_by(assignment_id=assignment.id,
                                                                                 user_id=self.id).first()):  # if no relation exists then create one
                            assignment.users.append(self)
                        else:
                            assignment.update_due(a.due)
                            assignment.update_description(a.description)
                            assignment.update_title(a.title)

                    db.session.add(assignment)
                    db.session.add(self)
                    if a.allow_discussion == '1':
                        comments = sc.get_assignment_comments([self.api_key, self.api_secret], s.id, a.id)
                        for comment in comments:
                            if User.query.filter_by(outeruid=comment.uid).count() < 1:
                                person = sc.get_user_info([self.api_key, self.api_secret], comment.uid)
                                name = person.name_display
                                pic = person.picture_url
                                link = 'https://app.schoology.com/user/' + str(person.uid) + '/info'
                            else:
                                person = User.query.filter_by(outeruid=comment.uid).first()
                                name = str(person.username) + ' *'
                                pic = person.picture_url
                                link = general_url + 'user/' + name

                            if SchoologyAssignmentComment.query.filter_by(schoology_id=comment.id).count() < 1:
                                comment_added = SchoologyAssignmentComment(assignment_id=Assignment.query.filter_by(schoology_id=a.id).first().id,
                                                                 timestamp=datetime.utcfromtimestamp(comment.created),
                                                                           schoology_id=comment.id)
                                comment_added.update_contents(name, pic, comment.comment, comment.likes, link)
                                print('Added Assignment Comment for', a.title, name)
                            else:
                                comment_added = SchoologyAssignmentComment.query.filter_by(schoology_id=comment.id).first()
                                comment_added.update_contents(name, pic, comment.comment, comment.likes, link)
                            db.session.add(comment_added)
            else:
                section = Section.query.filter_by(id=s.id).first()
                if 'Sample Assignment' not in [x.title for x in section.assignments]:
                    assignment = Assignment(section_id=s.id, course=s.title, img=s.img)
                    assignment.update_title('Sample Assignment')
                    assignment.update_description('This is not a real assignment... just a placeholder since this section has nothing currently assigned!')
                    assignment.users.append(self)
                    print('Added ' + 'Sample Assignment')
                    db.session.add(assignment)
                    db.session.add(self)
        db.session.commit()

    def update_events(self):
        events = sc.get_events([self.api_key, self.api_secret, self.outeruid])
        for e in events:
            if not bool(db.session.query(Event).filter_by(schoology_id=e.id).first()):
                event = Event(schoology_id=e.id)
                event.update_title(e.title)
                event.update_description(e.description)
                event.update_date(e.start, e.end)
                event.users.append(self)
            else:
                event = Event.query.filter_by(schoology_id=e.id).first()
                if not bool(db.session.query(EU_Relationships).filter_by(event_id=event.id, user_id=self.id).first()):
                    event.users.append(self)
                else:
                    event.update_date(e.start, e.end)
                    event.update_description(e.description)
                    event.update_title(e.title)
            db.session.add(event)
            db.session.add(self)
        db.session.commit()

    def update_sections(self):
        sections = sc.get_courses([self.api_key, self.api_secret, self.outeruid])
        for s in sections:
            if not bool(db.session.query(Section).filter_by(schoology_id=s.id).first()):
                instructor = sc.get_section_instructor(self.api_key, self.api_secret, s.id)
                section = Section(schoology_id=s.id,
                                  title=s.course_title + ' ' + str(s.section_title),
                                  web_url='https://app.schoology.com/course/' + str(s.id),
                                  img=s.profile_url,
                                  instructor_name=instructor.name_display,
                                  instructor_email=instructor.email)
                section.users.append(self)
            else:
                section = Section.query.filter_by(schoology_id=s.id).first()
                if not bool(
                        db.session.query(SE_Relationships).filter_by(section_id=section.id, user_id=self.id).first()):
                    section.users.append(self)
            db.session.add(section)
            db.session.add(self)
        db.session.commit()

    def update_grades(self):
        grades = sc.get_section_grade([self.api_key, self.api_secret, self.outeruid])
        sections = [i.schoology_id for i in self.sections]
        assignments = [j.schoology_id for j in self.assignments]
        for i in grades:
            if int(i.section_id) in sections:
                section = Section.query.filter_by(schoology_id=i.section_id).first_or_404()
                section_grade = str(i.final_grade[-1]['grade'])

                if SectionGrade.query.filter_by(section_id=section.id, user_id=self.id).count() < 1:
                    addition = SectionGrade(section_id=section.id, user_id=self.id, grade=section_grade)
                    db.session.add(addition)
                    print('Added Grade For:', section.title, self.username)
                else:
                    addition = SectionGrade.query.filter_by(section_id=section.id, user_id=self.id).first()
                    addition.update_grade(section_grade)
                db.session.add(addition)
                db.session.commit()
                assignments_response = []
                for x in i.period:
                    for j in x['assignment']:
                        assignments_response.append(j)
                for grade in assignments_response:
                    if int(grade['assignment_id']) in assignments:
                        assignment = Assignment.query.filter_by(schoology_id=int(grade['assignment_id'])).first()
                        if AssignmentGrade.query.filter_by(assignment_id=assignment.id, user_id=self.id).count() < 1:
                            addition = AssignmentGrade(user_id=self.id, section_id=section.id, assignment_id=assignment.id, max_points=grade['max_points'],
                                                       received_points=grade['grade'], comments=str(grade['comment']))
                            db.session.add(addition)

                            print('Added Grade For', self.username, assignment.title)
                        else:
                            graded_assignment = AssignmentGrade.query.filter_by(assignment_id=assignment.id, user_id=self.id).first()
                            graded_assignment.update_max_points(grade['max_points'])
                            graded_assignment.update_received_points(grade['grade'])
                            graded_assignment.update_comment(str(grade['comment']))
                            db.session.add(graded_assignment)
                    else:
                        print('--------', int(grade['assignment_id']))
                        # print('--------------', sc.get_assignment([self.api_key, self.api_secret], int(grade['assignment_id']), i.section_id))
            db.session.commit()

    def get_followed_courses(self):
        sections = []
        for i in self.sections:
            sections.append(i.id)
        for i in self.followed:
            for j in i.sections:
                sections.append(j.id)
        return sections

    def upcoming_assignments(self, number):
        upcoming = []
        for assignment in self.assignments:
            if assignment.title == 'Sample Assignment':
                break
            else:
                if assignment.due is not None and assignment.due >= datetime.now():
                    upcoming.insert(0, assignment)
        if len(upcoming) > number:
            return upcoming[:number]
        else:
            return upcoming

    def latest_grades(self, number):
        latest = []
        grades = AssignmentGrade.query.filter_by(user_id=current_user.id).all()
        sorted_grades = sorted(grades, key=lambda r: (r.received_points is not None, r.id), reverse=True)[:number]
        for g in sorted_grades:
            latest.append(Assignment.query.filter_by(id=g.assignment_id).first())
        return latest

    def update(self):
        print('syncing ', self.username)
        self.update_sections()
        self.update_assignments()
        self.update_events()
        self.set_avatar()
        self.update_grades()


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schoology_id = db.Column(db.Integer, index=True, unique=True)  # id
    title = db.Column(db.String())  # course_title + section_title
    web_url = db.Column(db.String(55))  # https://app.schoology.com/course/ + id
    img = db.Column(db.String())  # profile_url
    instructor_name = db.Column(db.String())  # name_display
    instructor_email = db.Column(db.String())  # email
    users = db.relationship('User',
                            secondary=SE_Relationships,
                            backref='section_enrollments')
    assignments = db.relationship('Assignment', backref='section', lazy='dynamic', order_by='desc(Assignment.due)')
    grades = db.relationship('SectionGrade', backref='xxx', lazy='dynamic')

    def get_upcoming_assignments(self):
        upcoming = []
        for assignment in self.assignments:
            if assignment.title == 'Sample Assignment':
                break
            else:
                if assignment.due is not None and assignment.due >= datetime.now():
                    upcoming.append(assignment)
        return upcoming

    def get_section_grade(self, user):
        try:
            return user.grades.filter_by(section_id=self.id).first().grade
        except AttributeError:
            return 'None'


class SectionGrade(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    section_id = db.Column(db.Integer(), db.ForeignKey('section.id'))
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    grade = db.Column(db.String())

    def update_grade(self, grade):
        self.grade = grade


class AssignmentGrade(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'))
    section_id = db.Column(db.Integer(), db.ForeignKey('section.id'))
    assignment_id = db.Column(db.Integer(), db.ForeignKey('assignment.id'))
    max_points = db.Column(db.Float())
    received_points = db.Column(db.Float())
    comments = db.Column(db.String())

    def update_max_points(self, max):
        self.max_points = max

    def update_received_points(self, received):
        self.received_points = received

    def update_comment(self, comment):
        self.comments = comment


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schoology_id = db.Column(db.Integer, index=True, unique=True)
    title = db.Column(db.String())
    description = db.Column(db.String())
    due = db.Column(db.DateTime())
    web_url = db.Column(db.String(55))
    section_id = db.Column(db.Integer(), db.ForeignKey('section.id'))
    course = db.Column(db.String(50))
    img = db.Column(db.String())
    users = db.relationship(
        'User',
        secondary=AU_Relationships,
        backref=db.backref('work', lazy='dynamic'))
    commits = db.relationship('Commit', backref='assignment', lazy='dynamic')
    posts = db.relationship('Post', backref='assignment', lazy='dynamic')
    grades = db.relationship('AssignmentGrade', backref='assignment', lazy='dynamic')
    sc_comments = db.relationship('SchoologyAssignmentComment', backref='xxx', lazy='dynamic', order_by='desc(SchoologyAssignmentComment.timestamp)')
    notes = db.relationship('AssignmentNotes', backref='assignment', lazy='dynamic')

    def update_title(self, text):
        self.title = text

    def update_description(self, text):
        self.description = text

    def update_due(self, date):
        if date != '':
            self.due = parse(date)
        else:
            self.due = None

    def get_affiliations(self, user):
        section = Section.query.filter_by(id=self.section_id).first()
        affiliations = []
        if user in section.users:
            affiliations.append(1)
        else:
            affiliations.append(0)
        others = []
        for i in user.followed:
            if i in section.users:
                others.append(i)
        affiliations.append(others)
        return affiliations

    def get_average_time_spent(self):
        commits = 0
        users = []
        total_time = 0
        for commit in self.commits:
            commits += 1
            total_time += int(commit.time_spent)
            if commit.user_id not in users:
                users.append(commit.user_id)
        return [total_time, commits, len(users)]

    def get_public_posts(self):
        return Post.query.filter_by(assignment_id=self.id, public=True)

    def get_private_posts(self, user):
        return Post.query.filter_by(assignment_id=self.id, public=False, user_id=user.id)

    def get_extrema(self):
        times = [t.time_spent for t in self.commits]
        if len(times) > 0:
            return [min(times), max(times)]
        else:
            return [0,0]

    def get_number_commits(self):
        commits = 0
        for a in self.commits:
            commits += 1
        return commits


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schoology_id = db.Column(db.Integer, index=True, unique=True)
    title = db.Column(db.String())
    description = db.Column(db.String())
    start = db.Column(db.DateTime())
    end = db.Column(db.DateTime())
    users = db.relationship(
        'User',
        secondary=EU_Relationships,
        backref=db.backref('calendar_events', lazy='dynamic'))

    def update_title(self, text):
        self.title = text

    def update_description(self, text):
        self.description = text

    def update_date(self, start, end):
        self.start = parse(start)
        if end != '':
            self.end = parse(end)
        else:
            self.end = None


class Commit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    schoology_id = db.Column(db.Integer)
    body = db.Column(db.String(140))
    time_spent = db.Column(db.Integer())
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('User',
                            secondary=Commit_Likes,
                            backref=db.backref('liked', lazy='dynamic')
                            )
    comments = db.relationship('CommitComment', backref='xxx', lazy='dynamic', order_by='desc(CommitComment.timestamp)')



    def __repr__(self):
        return '<Commit {}>'.format(self.body)

    def get_assignment_title(self):
        title = Assignment.query.filter_by(schoology_id=self.schoology_id).first().title
        return title

    def get_assignment_course(self):
        assignment = Assignment.query.filter_by(schoology_id=self.schoology_id).first()
        course, id = assignment.course, assignment.section_id
        return course, id

    def like(self, user):
        self.likes.append(user)
        db.session.add(self)
        db.session.commit()

    def unlike(self, user):
        if user in self.likes:
            self.likes.remove(user)
        db.session.add(self)
        db.session.commit()

    def is_liked(self, user):
        if user in self.likes:
            return True
        else:
            return False

    def get_liked(self):
        return [i.username for i in self.likes]

    def get_tooltip(self):
        commits = Assignment.query.filter_by(id=self.assignment_id).first().commits
        times = [x.time_spent for x in commits]
        avg = sum(times) / len(times)
        leeway = avg * 0.01
        if self.time_spent + leeway == avg or self.time_spent - leeway == avg or self.time_spent == avg:
            return 'Around Average (' + str(avg) + ') minutes'
        elif self.time_spent + leeway > avg or self.time_spent - leeway > avg:
            return 'Above Average (' + str(avg) + ') minutes'
        elif self.time_spent + leeway < avg or self.time_spent - leeway < avg:
            return 'Below Average (' + str(avg) + ') minutes'


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    schoology_id = db.Column(db.Integer)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('User',
                            secondary=Post_Likes,
                            )
    comments = db.relationship('PostComment', lazy='dynamic', order_by='desc(PostComment.timestamp)')

    def __repr__(self):
        return '<Commit {}>'.format(self.body)

    def get_assignment_title(self):
        title = Assignment.query.filter_by(schoology_id=self.schoology_id).first().title
        return title

    def get_assignment_course(self):
        assignment = Assignment.query.filter_by(schoology_id=self.schoology_id).first()
        course, id = assignment.course, assignment.id
        return course, id

    def like(self, user):
        self.likes.append(user)
        db.session.add(self)
        db.session.commit()

    def unlike(self, user):
        if user in self.likes:
            self.likes.remove(user)
        db.session.add(self)
        db.session.commit()

    def is_liked(self, user):
        if user in self.likes:
            return True
        else:
            return False

    def get_liked(self):
        return [i.username for i in self.likes]


class SchoologyAssignmentComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schoology_id = db.Column(db.Integer)
    commenter_name = db.Column(db.String(140))
    commenter_img = db.Column(db.String())
    commenter_link = db.Column(db.String())
    comment = db.Column(db.String())
    assignment_id = db.Column(db.Integer(), db.ForeignKey('assignment.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer())

    def update_contents(self, name, pic, comment, likes, link):
        self.commenter_name = name
        self.commenter_img = pic
        self.commenter_link = link
        self.likes = likes
        self.comment = comment


class CommitComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commit_id = db.Column(db.Integer(), db.ForeignKey('commit.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comment = db.Column(db.String())
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('User',
                            secondary=Commit_Comment_Likes,
                            )
    def like(self, user):
        self.likes.append(user)
        db.session.add(self)
        db.session.commit()

    def unlike(self, user):
        if user in self.likes:
            self.likes.remove(user)
        db.session.add(self)
        db.session.commit()

    def is_liked(self, user):
        if user in self.likes:
            return True
        else:
            return False

    def get_liked(self):
        return [i.username for i in self.likes]


class PostComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commit_id = db.Column(db.Integer(), db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comment = db.Column(db.String())
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('User',
                            secondary=Post_Comment_Likes,
                            )
    def like(self, user):
        self.likes.append(user)
        db.session.add(self)
        db.session.commit()

    def unlike(self, user):
        if user in self.likes:
            self.likes.remove(user)
        db.session.add(self)
        db.session.commit()

    def is_liked(self, user):
        if user in self.likes:
            return True
        else:
            return False

    def get_liked(self):
        return [i.username for i in self.likes]


class AssignmentNotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    body = db.Column(db.String())

    def update_body(self, text):
        self.body = text
