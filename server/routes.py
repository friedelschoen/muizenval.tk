from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from PIL import Image

from .app import app, bcrypt, db
from .forms import AdminForm, LoginForm, RegistrationForm, SearchForm, UpdateAccountForm, UpdateTrapForm
from .models import Trap, User

import secrets
import os

current_user: User


# index.html (home-page) route
@app.route("/")
def index():
    return render_template('index.html')

# about.html route


@app.route("/about")
def about():
    return render_template('about.html')

# register.html route


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('U bent al ingelogd', 'warning')
        return redirect('/')

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')
        address = f"{form.street} {form.housenumber}\n{form.postcode} {form.place}"
        user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
            phone=form.phone.data,
            address=address
        )
        db.session.add(user)
        db.session.commit()
        flash('Uw profiel is toegevoegd! U kunt nu inloggen.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Registeren', form=form)


# login.html route
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('U bent al ingelogd', 'warning')
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            if bcrypt.check_password_hash(user.password, form.email.data):
                flash(
                    'Wij raden u aan om uw wachtwoord te veranderen', 'warning')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else '/')
        else:
            flash('Inloggen mislukt, is uw e-mail en/of wachtwoord juist?', 'danger')
    return render_template('login.html', title='Inloggen', form=form)


# logout route
@app.route("/logout")
def logout():
    logout_user()
    return redirect('/')


# save-picture function for account.html
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picturepath = os.path.join(
        app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picturepath)

    return picture_fn


""" account.html route """


@app.route("/user/self", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        if form.password.data:
            current_user.password = bcrypt.generate_password_hash(
                form.password.data).decode('utf-8')
        db.session.commit()
        flash('Uw profiel is bewerkt!', 'success')
        return redirect(url_for('account'))

    elif request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email
    image_file = url_for(
        'static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html',  title='Profiel', image_file=image_file, form=form)


@app.route('/traps')
@login_required
def traps():
    return render_template('trap.html')


@app.route('/contact')
@login_required
def contact():
    return render_template('contact.html', contact=current_user.contact_class())


""" admin.html route """


@app.route("/users", methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.admin:
        flash('U mag deze website niet bereiken', 'error')
        return redirect('/')
    form = SearchForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.username.data).first()
        if user == None:
            flash(
                f'Geen gebrukers gevonden met de gebruikersnaam: {form.username.data}!', 'danger')
        else:
            flash(
                f'Gebruiker gevonden met gebruikersnaam: {form.username.data}!', 'success')
            return redirect(url_for('admin_user', user_id=user.id))
    return render_template('admin.html', form=form)


""" account-admin route """


@app.route("/user/<int:user_id>", methods=['GET', 'POST'])
@login_required
def admin_user(user_id):
    if not current_user.admin:
        flash('U mag deze website niet bereiken', 'error')
        return redirect('/')
    form = AdminForm()
    user = User.query.filter_by(id=user_id).first()
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    if form.validate_on_submit():
        user.admin = form.type.data == 'admin'
        db.session.commit()
        flash(f'De gebruiker {user.username} is nu een {user.type}', 'success')
        return redirect(url_for('admin'))
    elif request.method == 'GET':
        form.type.data = 'admin' if user.admin else 'client'
    return render_template('admin_user.html', form=form, user=user, image_file=image_file)


""" delete-user route """


@app.route("/user/<int:user_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    if not current_user.admin:
        flash('U mag deze website niet bereiken', 'danger')
        return redirect('/')
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'De gebruiker {user.username} is verwijderd', 'success')
    return redirect(url_for('admin'))


""" reset user's password route """


@app.route("/user/<int:user_id>/reset", methods=['GET', 'POST'])
@login_required
def reset_user(user_id):
    if not current_user.admin:
        flash('U mag deze website niet bereiken', 'danger')
        return redirect('/')
    user = User.query.get_or_404(user_id)
    user.password = bcrypt.generate_password_hash(user.email).decode('utf-8')
    db.session.commit()
    flash(f'{user.name}\'s wachtwoord is nu zijn/haar e-mail', 'success')
    return redirect(url_for('admin'))


""" 404 not found handler """


@app.errorhandler(404)
def not_found(error):
    flash(f"De pagina is niet gevonden", 'danger')
    return index()  # geen redirect om de '/bla' te houden
