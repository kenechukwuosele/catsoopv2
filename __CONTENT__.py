cs_content = """
<python>
import os

COURSES_DIR = '/home/alex/.local/share/catsoop/courses'
SKIP_DIRS = {'_cached', '_locks', '_logs', '__USERS__'}
course_icons = {
    'Physics': '&#9883;',
    'Programming': '&#128187;',
    'Sports': '&#127942;',
    'Biology': '&#129514;',
    'ENGLISH': '&#128220;',
    'Mathematics': '&#128300;',
    'Chemistry': '&#129514;',
    'History': '&#128220;',
}
default_desc = {
    'Physics': 'Explore mechanics, waves, thermodynamics and more.',
    'Programming': 'Test your programming knowledge.',
    'Sports': 'Quiz yourself on sports.',
    'Biology': 'Learn about living organisms.',
    'ENGLISH': 'Sharpen your language skills.',
    'Mathematics': 'Practice math problems.',
    'Chemistry': 'Discover chemical concepts.',
    'History': 'Journey through historical events.',
}

all_courses = []
if os.path.isdir(COURSES_DIR):
    for folder in sorted(os.listdir(COURSES_DIR)):
        if folder in SKIP_DIRS or folder.startswith('_'):
            continue
        path = os.path.join(COURSES_DIR, folder)
        if not os.path.isdir(path):
            continue
        desc = default_desc.get(folder, 'Explore this course.')
        info_path = os.path.join(path, '__INFO__.py')
        if os.path.exists(info_path):
            with open(info_path) as f:
                raw = f.read()
            for line in raw.splitlines():
                if 'cs_course_description' in line and '=' in line:
                    desc = line.split('=', 1)[-1].strip().strip('"').strip("'")
                    break
        icon = course_icons.get(folder, '&#128218;')
        display_name = folder.replace('_', ' ')
        all_courses.append((icon, display_name, desc, folder))

def normalize_enrollments(value):
    if not value:
        return []
    if isinstance(value, dict):
        value = value.get('courses', [])
    if isinstance(value, str):
        value = [v.strip() for v in value.split(',') if v.strip()]
    return list(value)

user_info = globals().get('cs_user_info', {}) or {}
username = user_info.get('username') or globals().get('cs_username')
role = user_info.get('role', 'Student')
log = globals().get('csm_cslog')
enrolled_courses = []
if username and log:
    enrolled_courses = normalize_enrollments(log.read_log('_course_enrollments', [], username))

form = globals().get('cs_form', {}) or {}
if username and log and form.get('enroll_submit'):
    selected = []
    valid_course_ids = {c[3] for c in all_courses}
    for key in form:
        if key.startswith('enroll_'):
            course_id = key.replace('enroll_', '', 1)
            if course_id in valid_course_ids:
                selected.append(course_id)
    selected = sorted(set(selected))
    log.update_log('_course_enrollments', [], username, selected)
    enrolled_courses = selected

visible_courses = all_courses
if role != 'Instructor' and enrolled_courses:
    visible_courses = [c for c in all_courses if c[3] in enrolled_courses]
elif role != 'Instructor' and not enrolled_courses:
    visible_courses = []

course_cards_html = ""
for icon, name, desc, folder in visible_courses:
    course_cards_html += '<div class="course-card"><div class="icon">' + icon + '</div><h3>' + name + '</h3><p>' + desc + '</p><a href="' + folder + '">Open Course</a></div>'

enroll_panel_html = ""
if username and role != 'Instructor':
    enroll_panel_html = '<div class="enroll-panel"><h2 class="section-title">My Courses</h2><p class="enroll-note">Select the courses you are enrolled in.</p><form method="post" class="enroll-form">'
    for icon, name, _desc, folder in all_courses:
        checked = ' checked' if folder in enrolled_courses else ''
        enroll_panel_html += (
            '<label class="enroll-item"><input type="checkbox" name="enroll_' + folder + '"' + checked + '> '
            + icon + ' ' + name + '</label>'
        )
    enroll_panel_html += '<button type="submit" name="enroll_submit" value="1">Save My Courses</button></form></div>'
</python>

<style>
  .home-wrapper {
    max-width: 900px;
    margin: 40px auto;
    font-family: 'Georgia', serif;
    color: #1a1a2e;
  }

  .home-hero {
    text-align: center;
    padding: 50px 20px 30px;
    border-bottom: 2px solid #2572F5;
    margin-bottom: 40px;
  }

  .home-hero h1 {
    font-size: 2.4em;
    color: #2572F5;
    margin-bottom: 10px;
    letter-spacing: 1px;
  }

  .home-hero p {
    font-size: 1.1em;
    color: #444;
    max-width: 650px;
    margin: 0 auto;
    line-height: 1.7;
  }

  .welcome-box {
    background: #f0f4ff;
    border-left: 5px solid #2572F5;
    padding: 20px 25px;
    border-radius: 4px;
    margin-bottom: 40px;
    font-size: 1em;
    color: #333;
    line-height: 1.8;
  }

  .courses-section h2 {
    font-size: 1.5em;
    color: #1a1a2e;
    margin-bottom: 20px;
    border-bottom: 1px solid #ccc;
    padding-bottom: 8px;
  }

  .course-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
  }

  .course-card {
    background: #ffffff;
    border: 1px solid #dce3f5;
    border-radius: 8px;
    padding: 25px 20px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(37,114,245,0.07);
    transition: transform 0.2s, box-shadow 0.2s;
    text-decoration: none;
    color: inherit;
    display: block;
  }

  .course-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 6px 18px rgba(37,114,245,0.15);
  }

  .course-card .icon {
    font-size: 2em;
    margin-bottom: 12px;
  }

  .course-card h3 {
    font-size: 1.2em;
    color: #2572F5;
    margin-bottom: 8px;
  }

  .course-card p {
    font-size: 0.9em;
    color: #666;
    line-height: 1.5;
  }

  .footer-note {
    text-align: center;
    margin-top: 50px;
    font-size: 0.85em;
    color: #999;
  }

  .enroll-panel {
    background: #ffffff;
    border: 1px solid #dce3f5;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
    box-shadow: 0 2px 8px rgba(37,114,245,0.07);
  }

  .section-title {
    font-size: 1.4em;
    color: #1a1a2e;
    border-bottom: 2px solid #2572F5;
    padding-bottom: 8px;
    margin-bottom: 18px;
  }

  .enroll-note {
    font-size: 0.92em;
    color: #666;
    margin-bottom: 14px;
  }

  .enroll-form {
    display: grid;
    gap: 10px;
  }

  .enroll-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.95em;
    color: #333;
  }

  .enroll-item input {
    width: auto;
  }
</style>

<div class="home-wrapper">

  <div class="home-hero">
    <h1>CU Quiz App</h1>
    <p>An interactive academic quiz platform for students of Covenant University, powered by CAT-SOOP — an automatic tutor for six-oh-one problems.</p>
  </div>

  <div class="welcome-box">
    <strong>Welcome!</strong> This platform hosts quizzes across multiple courses to help you test your understanding and prepare for assessments. Select a course below to get started. Your progress is tracked automatically.
  </div>

  <python>
print(enroll_panel_html)
  </python>

  <div class="courses-section">
    <h2>Available Courses (<python>print(len(visible_courses))</python>)</h2>
    <div class="course-cards">
      <python>
if course_cards_html:
    print(course_cards_html)
else:
    print('<div class="welcome-box">No courses available. Use the My Courses panel to enroll.</div>')
      </python>
    </div>
  </div>

  <div class="footer-note">
    &copy; Osele Kenechukwu Alexander &mdash; CU Quiz App
  </div>

</div>
"""
