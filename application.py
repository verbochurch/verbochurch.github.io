from functools import wraps

from flask import Flask, session, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, RadioField, SubmitField, IntegerField, TextAreaField
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, PasswordField, BooleanField, \
    ValidationError
from wtforms.validators import Email, Length, DataRequired, NumberRange, InputRequired, EqualTo
from wtforms.validators import Length
from wtforms import validators
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message


import db
from mail_settings import config_email

app = Flask(__name__)
config_email(app)
app.config['SECRET_KEY'] = 'Super Secret Unguessable Key'
mail = Mail(app)

bcrypt = Bcrypt(app)
login_mgr = LoginManager()
login_mgr = LoginManager(app)


@app.before_request
def before():
    db.open_db_connection()


@app.teardown_request
def after(exception):
    db.close_db_connection()


# this initializes some test users -- we can no longer do this in the db because of the password hashing
def init_test_user():
    if db.find_user('john@example.com') is None:
        password = 'password'
        pw_hash = bcrypt.generate_password_hash(password)
        db.create_user('john@example.com', pw_hash, 2)
    if db.find_user('admin@example.com') is None:
        password = 'password'
        pw_hash = bcrypt.generate_password_hash(password)
        db.create_user('admin@example.com', pw_hash, 3)


########################## INDEX + MAP + Dashboard##############################################

# this takes the user to the index page which is a map of all the homegroups
@app.route('/')
def index():
    # return redirect(url_for("homegroup", homegroup_id=session['homegroup_id']))
    # msg = Message(
    #     'Hello',
    #     sender='verbovelocity@gmail.com',
    #     recipients=
    #     ['verbovelocity@gmail.com'])
    # msg.body = "This is the email body"
    # mail.send(msg)

    return render_template('index.html')


# this displays the dashboard depending on user role
@app.route('/dashboard')
def dashboard():
    email = current_user.email
    role = current_user.role
    if role == 'homegroup_leader':
        homegroup_id = db.find_user_homegroup(email)
        return redirect(url_for('homegroup', homegroup_id=homegroup_id))
    if role == "admin":
        return redirect(url_for('admin_home'))
    return redirect(url_for('index'))


# displays the map of all the homegroups
@app.route('/map')
def map():
    homegroups = db.get_all_homegroup_info()
    return render_template('map.html', homegroups=homegroups)

# displays the faq page
@app.route('/faq')
def faq():
    return render_template('faq.html')

# displays the homegroup leader faq page
@app.route('/faq/homegroup_leader')
def faq_homegroup_leader():
    return render_template('faq_homegroup_leader.html')

# displays the admin faq page
@app.route('/faq/admin')
def faq_admin():
    return render_template('faq_admin.html')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('E-mail Address', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Email')

# displays the contact page
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    recipient_list=[]
    contact_form = ContactForm()
    if contact_form.validate_on_submit():
        name = contact_form.name.data
        email = contact_form.email.data
        recipient_list.append('verbovelocity@gmail.com')
        message = contact_form.message.data
        email_html = render_template('contact_email.html', name=name, email=email, message=message)
        msg = Message(
            'Message Received',
            sender=email,
            recipients=recipient_list,
            html=email_html)
        mail.send(msg)
        flash('Email Sent!')
        return redirect(url_for('index'))
    return render_template('contact.html', form=contact_form)

########################## USER + LOGIN + Profile/Settings ##############################################

# this allows/disallows users from accessing pages based on their roles
def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not hasattr(current_user, 'role'):
                flash('User does not have sufficient privileges ')
                return redirect(url_for('index'))
            elif current_user.role not in roles:
                flash('User does not have sufficient privileges ')
                return redirect(url_for('index'))
            return f(*args, **kwargs)

        return wrapped

    return wrapper


class UserForm(FlaskForm):

    password = PasswordField('Temporary Password', validators=[DataRequired()])
    role = SelectField('Change Role', choices=[], coerce=int)
    homegroups = SelectField('Choose Homegroup', choices=[], coerce=int)
    submit = SubmitField('Create User')


# Creates a new user and hashes their password in the database
@app.route('/user/create/<member_id>', methods=['GET', 'POST'])
def create_user(member_id):
    allRoles = db.find_roles()
    roleList = []
    email_list = []
    for role in allRoles:
        roleList.append((role["id"], role["role"]))
    member = db.find_member(member_id)
    email = member['email']
    user_form = UserForm()
    user_form.role.choices = roleList

    homegroups = db.get_all_homegroups()
    homegroup_list = []
    for homegroup in homegroups:
        homegroup_list.append((homegroup['id'], homegroup['name']))
    user_form.homegroups.choices = homegroup_list

    if user_form.validate_on_submit():
        email_list.append(email)
        password = user_form.password.data
        pw_hash = bcrypt.generate_password_hash(password)
        db.create_user(email, pw_hash, user_form.role.data)
        user = db.find_user(email)
        email_html = render_template('user_account_email.html', email=email, password=password, user_id=user['id'])
        msg = Message(
            'User account created for Verbo Velocity',
            sender='verbovelocity@gmail.com',
            recipients=email_list,
            html=email_html)
        mail.send(msg)
        if user_form.homegroups.data is not None:
            homegroupId = user_form.homegroups.data
            user_id = db.find_user(email)['id']
            db.add_leader_to_homegroup(user_id, homegroupId)

        flash('User Created')
        return redirect(url_for('all_members'))
    return render_template('create_user.html', form=user_form, email = email)

class UpdateUserForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Update Password')


#this updates user passwords
@app.route('/user/edit/<user_id>', methods=['GET', 'POST'])
def update_user(user_id):
    member = db.find_user_info(user_id)
    email = member['email']
    user_form = UpdateUserForm(email=member['email'])
    if user_form.validate_on_submit():
        old_password = user_form.old_password.data
        new_password = user_form.new_password.data
        confirm_password = user_form.confirm_password.data
        if bcrypt.check_password_hash(member['password'], old_password):
            if new_password == confirm_password:
                password = new_password
                pw_hash = bcrypt.generate_password_hash(password)
                print(member['role_id'])
                db.update_user(email, pw_hash, member['role_id'])
                flash('Password updated')
                return redirect(url_for('index'))
            else:
                flash('New Password and Confirmation Password Do Not Match')
                return redirect(url_for('update_user', user_id))
        else:
            flash('Entered in wrong current password')
            return redirect(url_for('update_user', user_id))
    return render_template('update_user.html', form=user_form, email=email)


class User(object):
    """Class for the currently logged-in user (if there is one). Only stores the user's e-mail."""

    def __init__(self, email):
        self.email = email
        if db.find_user(self.email) is not None:
            self.role = db.find_user(self.email)['role']
            self.name = db.find_member_info(self.email)['first_name']
            self.user_id = db.find_user(self.email)['id']
            self.member_id = db.find_member_info(self.email)['id']
        else:
            self.role = 'no role'
            self.name = 'no name'
        if (self.role == 'homegroup_leader'):
            self.homegroup_id = db.find_user_homegroup(self.email)

        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        """Return the unique ID for this user. Used by Flask-Login to keep track of the user in the session object."""
        return self.email

    def get_role(self):
        """Returns the role of the user from the db"""
        return self.role

    def __repr__(self):
        return "<User '{}' {} {} {} {}>".format(self.email, self.role, self.is_authenticated, self.is_active,
                                                self.is_anonymous)


@login_mgr.user_loader
def load_user(id):
    """Return the currently logged-in user when given the user's unique ID"""
    return User(id)


# checks to see if the password entered matches the hash password
def authenticate(email, password):
    """Check whether the arguments match a user from the "database" of valid users."""
    valid_users = db.get_all_users()
    for user in valid_users:
        if email == user['email'] and bcrypt.check_password_hash(user['password'], password):
            return email
    return None


class LoginForm(FlaskForm):
    email = StringField('E-mail Address', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


# logs the user in, creates a new session, and creates a current user which is of the class "User"
@app.route('/login', methods=['GET', 'POST'])
def login():
    # temporary
    init_test_user()
    login_form = LoginForm()

    if login_form.validate_on_submit() and login_form.validate():
        if authenticate(login_form.email.data, login_form.password.data):
            # Credentials authenticated.
            # Create the user object, let Flask-Login know, and redirect to the home page
            current_user = User(login_form.email.data)
            login_user(current_user)
            session['username'] = current_user.email
            flash('Logged in successfully as {}'.format(login_form.email.data))
            return redirect(url_for('dashboard'))
        else:
            # Authentication failed.
            flash('Invalid email address or password')
            return redirect(url_for('login'))

    return render_template('login.html', form=login_form)


# logs the user out and removes the session
@app.route('/logout')
def logout():
    logout_user()
    user_name = session.pop('username', None)
    flash('Logged out')
    return redirect(url_for('index'))

@app.route('/user/profile/<user_id>')
@login_required
def user_profile(user_id):
    user_info = db.find_user_info(user_id)
    member = db.find_member_info(user_info['email'])
    return redirect (url_for('edit_member', member_id = member['id']))


########################## HOME GROUP  (Home Group Leader)##############################################

# this is the homegroup main page / dashboard
@app.route('/homegroup/<homegroup_id>')
@login_required
@requires_roles('homegroup_leader', 'admin')
def homegroup(homegroup_id):
    homegroup = db.find_homegroup(homegroup_id)
    attendance_count = db.get_homegroup_attendance_counts(homegroup_id)
    return render_template('homegroup.html', currentHomegroup=homegroup,
                           attendance_count=attendance_count)


class AttendanceForm(FlaskForm):
    # member_id = StringField('member Id', validators=[Length(min=1, max=40)])
    # meeting_id = StringField('Meeting Id', validators=[Length(min=1, max=40)])
    radio = RadioField('Attendance', choices=["y", "n"])
    submit = SubmitField('Submit')


# this is the default attendance page (allows you to select date/time then generate an attendance report)
@app.route('/homegroup/attendance/<homegroup_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('homegroup_leader')
def attendance(homegroup_id):
    error = ""
    attendance_form = AttendanceForm()
    members = db.get_homegroup_members(homegroup_id)
    show_members = 'N'
    if (request.method == "POST"):
        date = request.form['AttendanceDate']
        time = request.form['AttendanceTime']
        meeting_id = db.add_date(date, time)['id']
        db.generate_attendance_report(homegroup_id, meeting_id)
        return redirect(url_for('edit_attendance', homegroup_id=homegroup_id, meeting_id=meeting_id))
    return render_template('attendance.html', currentHomegroup=homegroup_id, form=attendance_form, members=members,
                           showmembers=show_members)

#sends email if user and missed a certain number of meetings
def system_notify_member(member_id, num_misses):
    homegroup_id = db.find_member_homegroup(member_id)['homegroup_id']
    leader = db.find_homegroup_leader(homegroup_id)
    email = db.find_member(member_id)['email']
    email_list = []
    email_list.append(email)
    leader_email = leader['email']
    leader_phone = leader['phone_number']
    leader_name = leader['first_name'] + ' ' + leader['last_name']
    email_html = render_template('notify_member_email.html', num_misses = num_misses, leader_name = leader_name, leader_phone = leader_phone, leader_email = leader_email )
    msg = Message(
        'System Reminder: Missing meetings',
        sender='verbovelocity@gmail.com',
        recipients=email_list,
        html=email_html)
    mail.send(msg)


# adds (or updates) a new entry of attendance into the db
def updateAttendance(homegroup_id, member_id, meeting_id, attendance):
    db.update_attendance(homegroup_id, member_id, meeting_id, attendance)
    return redirect(url_for('edit_attendance', homegroup_id=homegroup_id, meeting_id=meeting_id))


class EditAttendanceForm(FlaskForm):
    submit = SubmitField('Save')

# This allows you to edit homegroup attendance
@app.route('/homegroup/attendance/edit/<homegroup_id>/<meeting_id>',  methods=['GET', 'POST'])
@login_required
@requires_roles('homegroup_leader','admin')
def edit_attendance(homegroup_id, meeting_id):
    print(meeting_id)
    att_form = EditAttendanceForm()
    members_in_attendance = db.get_attendance(homegroup_id, meeting_id)
    date = db.find_date(meeting_id)['date']
    time = db.find_date(meeting_id)['time']
    edit_or_new = 'new'
    for member in members_in_attendance:
        if (member['attendance'] == 1):
            edit_or_new = 'edit'
    print("Edit/New: " + edit_or_new)
    if att_form.validate_on_submit():
        for member in members_in_attendance:
            input_name =  'member_' + str(member['member_id'] )
            if input_name in request.form:
                print(member['first_name'] + " in attendance")
                updateAttendance(homegroup_id, member['member_id'], meeting_id, 1)
            else:
                updateAttendance(homegroup_id, member['member_id'], meeting_id, 0)
                if(edit_or_new == 'new'):
                    print(member['first_name'] + " not in attendance")
                    attendancedates = db.system_attendance_alert(homegroup_id, member['id'], 3)
                    notify = True
                    for date in attendancedates:
                        print('meeting ' + str(date['meeting_id']))
                        print('attendance: ' + str(date['attendance']))

                        if date['attendance'] == 1:
                            notify = False
                    if len(attendancedates) <3:
                        notify = False
                    if notify == True:
                        system_notify_member(member['id'], 3)

        return redirect(url_for('get_attendance_dates', homegroup_id = homegroup_id))

    return render_template('edit_attendance.html', currentHomegroup=homegroup_id, meeting_id=meeting_id,
                           members=members_in_attendance, date=date, time=time, form = att_form)


# returns all the attendance dates -- this is for the attendance reports page
@app.route('/homegroup/attendance/dates/<homegroup_id>', methods=['GET'])
@login_required
@requires_roles('homegroup_leader', 'admin')
def get_attendance_dates(homegroup_id):

    return render_template('attendance_reports.html', currentHomegroup=homegroup_id,
                           records=db.get_attendance_dates(homegroup_id))

#view attendance history for a particular
@app.route('/homegroup/attendance/view/<homegroup_id>', methods=['GET'])
@login_required
@requires_roles('admin')
def view_attendance(homegroup_id):
    homegroup = db.find_homegroup(homegroup_id)
    attendance_count = db.get_homegroup_attendance_counts(homegroup_id)
    return render_template('view_attendance.html', currentHomegroup=homegroup,
                           attendance_count=attendance_count, myHomegroup=homegroup_id, records=db.get_attendance_dates(homegroup_id))

@app.route('/homegroup/attendance/view/report/<homegroup_id>/<meeting_id>',  methods=['GET'])
@login_required
@requires_roles('homegroup_leader','admin')
def view_attendance_report(homegroup_id, meeting_id):
    members_in_attendance = db.get_attendance(homegroup_id, meeting_id)
    attendance_count = db.get_homegroup_attendance_counts(homegroup_id)
    date = db.find_date(meeting_id)['date']
    time = db.find_date(meeting_id)['time']
    return render_template('view_attendance_report.html', currentHomegroup=homegroup_id, meeting_id=meeting_id,
                           members=members_in_attendance, date=date, time=time, attendance_count=attendance_count)

# edit a particular homegroup
@app.route('/homegroup/edit/<homegroup_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('homegroup_leader', 'admin')
def edit_homegroup(homegroup_id):
    row = db.find_homegroup(homegroup_id)
    hg_form = CreateHomeGroupForm(name=row['name'],
                                  description=row['description'],
                                  location=row['location'],
                                  latitude=row['latitude'],
                                  longitude=row['longitude'])
    if request.method == "POST" and hg_form.validate():
        name = hg_form.name.data
        description = hg_form.description.data
        location = hg_form.location.data
        latitude = hg_form.latitude.data
        longitude = hg_form.longitude.data
        print(latitude)
        print(longitude)
        rowcount = db.edit_homegroup(homegroup_id, name, location, description, latitude, longitude)
        if (rowcount == 1):
            flash("Home Group updated!")
            if (current_user.role == 'admin'):
                return redirect(url_for('get_homegroups'))
            return redirect(url_for('homegroup', homegroup_id=homegroup_id))

    return render_template('edit_homegroup.html', form=hg_form)


# this is the iframe that is in the creating/editing homegroup -- allows you to type in address and finds location
@app.route('/homegroup/select_location')
def select_location():
    return render_template('select_location.html')


########################## MEMBER (Home Group Leader) ##############################################

class CreateMemberForm(FlaskForm):
    first_name = StringField('First Name', [validators.Length(min=2, max=30, message="First name is a required field")])
    last_name = StringField('Last Name', [validators.Length(min=2, max=30, message="Last name is a required field")])
    email = StringField('Email', [validators.Email("Please enter valid email")])
    phone_number = StringField('Phone Number', [validators.InputRequired(message="Please enter valid phone number")])
    gender = SelectField('Gender', choices=[('M', 'Male'), ('F', 'Female')])
    baptism_status = SelectField('Baptized?', choices=[('1', 'Yes'), ('0', 'No')])
    marital_status = SelectField('Married?', choices=[('1', 'Yes'), ('0', 'No')])
    submit = SubmitField('Save Member')

@app.route('/homegroup/member/new/<homegroup_id>')
@login_required
@requires_roles('homegroup_leader', 'admin')
def member_search(homegroup_id):
    members = db.get_all_members_not_in_homegroup(homegroup_id)
    return render_template ('member_search.html', all_members = members, homegroup_id = homegroup_id)


#adds a member to a particular homegroup
@app.route('/homegroup/member/add/<homegroup_id>/<member_id>')
@login_required
@requires_roles('homegroup_leader', 'admin')
def add_member_to_homegroup(homegroup_id, member_id):
    inactive_homegroup_members = db.get_homegroup_inactive_members(homegroup_id)
    new = 'Y'
    for members in inactive_homegroup_members:
        print(members['member_id'])
        if int (members['member_id']) == int(member_id):
            new = 'N'
            db.reactive_homegroup_member(homegroup_id, member_id)
    print(new)
    if new == 'Y':
        db.add_member_to_homegroup(homegroup_id, member_id)
    member = db.find_member(member_id)
    flash ("Member {} added to homegroup".format(member['first_name']  + " " + member['last_name']))
    return redirect (url_for('get_homegroup_members', homegroup_id = homegroup_id))


# creates a new member for a particular homegroup
@app.route('/homegroup/create_member/<homegroup_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('homegroup_leader', 'admin')
def create_new_member_for_homegroup(homegroup_id):
    member = CreateMemberForm()
    if request.method == "POST" and member.validate():
        first_name = member.first_name.data
        last_name = member.last_name.data
        email = member.email.data
        phone_number = member.phone_number.data
        gender = member.gender.data
        birthday = request.form['Birthday']
        baptism_status = member.baptism_status.data
        marital_status = member.marital_status.data
        join_date = request.form['JoinDate']
        rowcount = db.create_member(first_name, last_name, email, phone_number, gender, birthday, baptism_status,
                                    marital_status, join_date)
        if rowcount == 1:
            row = db.recent_member()
            member_id = row['id']
            db.add_member_to_homegroup(homegroup_id, member_id)
            flash("Member {} Created!".format(member.first_name.data, member.last_name.data))
            return redirect(url_for('get_homegroup_members', homegroup_id=homegroup_id))

    return render_template('create_member.html', form=member, homegroup_id=homegroup_id)


# views all members in a homegroup
@app.route('/homegroup/members/<homegroup_id>')
@login_required
@requires_roles('homegroup_leader', 'admin')
def get_homegroup_members(homegroup_id):
    current_homegroup = db.find_homegroup(homegroup_id)
    homegroup_members = db.get_homegroup_members(homegroup_id)
    list = []
    for member in homegroup_members:
        list.append(member["email"])
    list2 = ""
    for item in list:
        list2 = list2 + ", " + item
    return render_template('homegroup_members.html', homegroup=db.get_homegroup_members(homegroup_id),
                           currentHomegroup=current_homegroup, homegroupEmails=db.get_homegroup_emails(homegroup_id), emails=list2)


# edits member information
@app.route('/member/edit/<member_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('homegroup_leader', 'admin')
def edit_member(member_id):
    if (int(current_user.member_id )== int(member_id)):
        heading_text = 'Edit My Info'
    else:
        heading_text = 'Edit Member'
    row = db.find_member(member_id)
    member_form = CreateMemberForm(first_name=row['first_name'],
                                   last_name=row['last_name'],
                                   email=row['email'],
                                   phone_number=row['phone_number'],
                                   gender=row['gender'],
                                   baptism_status=row['baptism_status'],
                                   marital_status=row['marital_status'])
    birthday_form = row['birthday']
    join_date_form = row['join_date']
    if request.method == "POST" and member_form.validate():
        first_name = member_form.first_name.data
        last_name = member_form.last_name.data
        email = member_form.email.data
        phone_number = member_form.phone_number.data
        gender = member_form.gender.data
        birthday = request.form['Birthday']
        baptism_status = member_form.baptism_status.data
        marital_status = member_form.marital_status.data
        join_date = request.form['JoinDate']
        rowcount = db.edit_member(member_id, first_name, last_name, email, phone_number, gender, birthday,
                                  baptism_status, marital_status, join_date)
        if (rowcount == 1):
            flash("Member {} Updated!".format(member_form.first_name.data))
            if (current_user.role == 'admin'):
                return redirect(url_for('all_members'))
            else:
                homegroup_id = db.find_member_homegroup(member_id)['homegroup_id']
                return redirect(url_for('get_homegroup_members', homegroup_id = homegroup_id))

    return render_template('edit_member.html', heading_text = heading_text, form=member_form, bDay=birthday_form, joinDay=join_date_form)


# removes a member from a particular homegroup
@app.route('/homegroup/member/delete/<homegroup_id>/<member_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('homegroup_leader', 'admin')
def remove_member(homegroup_id, member_id):
    rowcount = db.remove_member(homegroup_id, member_id)
    if rowcount == 1:
        flash("Member Removed!")
    return redirect(url_for('get_homegroup_members', homegroup_id=homegroup_id))


########################## ADMIN FUNCTIONS ##############################################

#### Admin - Home Group ####
class CreateHomeGroupForm(FlaskForm):
    name = StringField('Name', [validators.Length(min=2, max=30, message="Name is a required field")])
    description = TextAreaField('Description', [validators.InputRequired(message="Please enter a description")])
    location = StringField('Address', [validators.InputRequired(message="Please enter valid Address")])
    latitude = StringField('Latitude')
    longitude = StringField('Longitude')
    submit = SubmitField('Save Home Group')


# displays admin home page
@app.route('/admin')
def admin_home():
    attendance_count = db.get_attendance_counts()
    print(attendance_count)
    return render_template('admin_home.html', attendance_count=attendance_count)


# create homegroup
@app.route('/homegroup/create', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def create_homegroup():
    new_homegroup = CreateHomeGroupForm()

    if request.method == "POST" and new_homegroup.validate():
        name = new_homegroup.name.data
        location = new_homegroup.location.data
        description = new_homegroup.description.data
        latitude = new_homegroup.latitude.data
        longitude = new_homegroup.longitude.data
        rowcount = db.create_homegroup(name, location, description, latitude, longitude)

        if rowcount == 1:
            flash("Homegroup {} Created!".format(new_homegroup.name.data))
            return redirect(url_for('get_homegroups'))

    return render_template('create_homegroup.html', form=new_homegroup)


# shows all homegroups
@app.route('/homegroup/all')
@login_required
@requires_roles('admin')
def get_homegroups():
    return render_template('homegroup_list.html', homegroup_list=db.get_all_homegroups(),
                           inactiveHomegroups=db.get_all_inactive_homegroups(), showInactive=False)


# deactivates a homegroup
@app.route('/homegroup/delete/<homegroup_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def deactivate_homegroup(homegroup_id):
    rowcount = db.deactivate_homegroup(homegroup_id)
    print(db.find_homegroup(homegroup_id)[6])
    # if the member is not active
    if db.find_homegroup(homegroup_id)[6] == 0:
        flash("Homegroup Deactivated!")
    return redirect(url_for('get_homegroups'))


#this reactivates a homegroup
@app.route('/homegroup/reactivate/<homegroup_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def reactivate_homegroup(homegroup_id):
    rowcount = db.reactivate_homegroup(homegroup_id)
    print(db.find_homegroup(homegroup_id)[6])
    # if the member is not active
    if db.find_homegroup(homegroup_id)[6] == 0:
        flash("Homegroup Reactivated!")
    return redirect(url_for('get_homegroups'))


#### Admin - Member ###########

# shows all members
@app.route('/member/all')
@login_required
@requires_roles('admin')
def all_members():
    emails = db.get_all_members_emails()
    list = []
    for email in emails:
        list.append(email["email"])
    list2=""
    for item in list:
        list2 = list2+", " + item
    return render_template('all_members.html', members=db.get_all_members(), emails=list2,
                           inactiveMembers=db.get_all_inactive_members(), showInactive=False)


# creates a member
@app.route('/member/create', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def create_member():
    member = CreateMemberForm()

    if request.method == "POST" and member.validate():
        first_name = member.first_name.data
        last_name = member.last_name.data
        email = member.email.data
        phone_number = member.phone_number.data
        gender = member.gender.data
        birthday = request.form['Birthday']
        baptism_status = member.baptism_status.data
        marital_status = member.marital_status.data
        join_date = request.form['JoinDate']
        rowcount = db.create_member(first_name, last_name, email, phone_number, gender, birthday, baptism_status,
                                    marital_status, join_date)

        if rowcount == 1:
            flash("Member {} Created!".format(member.first_name.data))
            return redirect(url_for('all_members'))

    return render_template('create_member.html', form=member)


# sets a member inactive in the system
@app.route('/member/delete/<member_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def deactivate_member(member_id):
    rowcount = db.deactivate_member(member_id)
    print(db.find_member(member_id)[9])
    # if the member is not active
    if db.find_member(member_id)[9] == 0:
        flash("Member Deactivated!")
    return redirect(url_for('all_members'))


# sets a member active in the system
@app.route('/member/add/<member_id>', methods=['GET', 'POST'])
@login_required
@requires_roles('admin')
def reactivate_member(member_id):
    rowcount = db.reactivate_member(member_id)
    print(db.find_member(member_id)[9])
    # if the member is not active
    if db.find_member(member_id)[9] == 0:
        flash("Member Reactivated!")
    return redirect(url_for('all_members'))


# shows all members
@app.route('/member/all/advanced_search')
@login_required
@requires_roles('admin')
def advanced_search():
    return render_template('advanced_search.html', members=db.get_all_members(), inactiveMembers=db.get_all_inactive_members(), showInactive=False)


#### Admin - Admin ###########

# shows all members
@app.route('/admin/all')
@login_required
@requires_roles('admin')
def all_admin():
    return render_template('admin_profiles.html', admin=db.get_all_admin(),
                           inactiveAdmin=db.get_all_inactive_admin(), showInactive=False)


# Make this the last line in the file!
if __name__ == '__main__':
    app.run(debug=True)


