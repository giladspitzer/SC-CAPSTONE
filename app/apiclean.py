from app.schoologyapi.api import Schoology


def authenticate(key, secret):
    return Schoology(key, secret)


def get_user_id(key, secret):
    return authenticate(key, secret).get_me().id


def get_courses(data):
    courses = authenticate(data[0], data[1]).get_user_sections(data[2])
    return courses


def get_events(data):
    events = authenticate(data[0], data[1]).get_events(user_id=data[2])
    return events


def get_section_assignments(data, section_id):
    assignments = []
    section_assignments = authenticate(data[0], data[1]).get_assignments(section_id)
    for i in section_assignments:
        assignments.append(i)
    return assignments


def get_pic(key, secret):
    return authenticate(key, secret).get_me().picture_url


def get_section_instructor(key, secret, section_id):
    members =  authenticate(key, secret).get_section_enrollments(section_id)
    for mem in members:
        if mem.admin == 1:
            mem['email'] = authenticate(key, secret).get_user(mem.uid).primary_email
            return mem


def get_assignment_comments(data, sectionid, assignmentid):
    return authenticate(data[0], data[1]).get_assignment_comments(sectionid, assignmentid)


def get_user_info(data, uid):
    return authenticate(data[0], data[1]).get_user(uid)

def get_attendance(data, section_id, enrollment_id):
    return authenticate(data[0], data[1]).get_attendance(section_id, enrollment_id)

def get_section_enrollments(data, section_id):
    return authenticate(data[0], data[1]).get_section_enrollments(section_id)

def get_section_grade(data):
    d = authenticate(data[0], data[1]).get_user_grades(data[2])
    return d

def get_section_info(data, section_id):
    return authenticate(data[0], data[1]).get_section(section_id)

def get_assignment(data, assignment_id, section_id):
    return authenticate(data[0], data[1]).get_assignment(section_id, assignment_id)