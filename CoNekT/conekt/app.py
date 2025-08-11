"""
Everything that needs to be set up to get flask running is initialized in this file.

  * set up and configure the app

  * configure extensions (db, debugtoolbar, compress, ...)

  * load all controllers and register their blueprints to a subdomain

  * Note: as long as models are used by a controller they are loaded and included in create_db !

  * add admin panel

  * set up global things like the search form and custom 403/404 error messages
"""
from flask import Flask, render_template, g, request, url_for, flash, redirect
from flask_admin.menu import MenuLink
from flask_login import current_user
from flask_admin import Admin

from conekt.extensions import toolbar, db, login_manager, cache, htmlmin, \
    blast_thread, compress, whooshee, migrate, csrf

import coloredlogs


def create_app(config):
    # Set up app, database and login manager before importing models and controllers
    # Important for db_create script

    app = Flask(__name__)

    coloredlogs.install()

    app.config.from_object(config)
    configure_extensions(app)
    configure_blueprints(app)
    configure_admin_panel(app)
    configure_error_handlers(app)
    configure_hooks(app)

    return app


def configure_extensions(app):
    db.app = app
    db.init_app(app)

    # Enable Whooshee
    whooshee.init_app(app)

    # Enable login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Enable cach
    cache.init_app(app)

    # Enable Compress
    compress.init_app(app)

    # Enable HTMLMIN
    htmlmin.init_app(app)

    # Enable CSRF Protect globally
    csrf.init_app(app)

    # Enable DebugToolBar
    toolbar.init_app(app)

    migrate.init_app(app, db=db)

    BLAST_ENABLED = app.config['BLAST_ENABLED']

    # Enable BLAST
    if BLAST_ENABLED:
        blast_thread.init_app(app)

    from conekt.models.users import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    @login_manager.unauthorized_handler
    def unauthorized():
        return render_template('error/403.html'), 403


def configure_blueprints(app):
    # Import controllers and register as blueprint
    from conekt.controllers.main import main
    from conekt.controllers.auth import auth, no_login
    from conekt.controllers.blast import blast
    from conekt.controllers.sequence import sequence
    from conekt.controllers.species import species
    from conekt.controllers.go import go
    from conekt.controllers.interpro import interpro
    from conekt.controllers.cazyme import cazyme
    from conekt.controllers.family import family
    from conekt.controllers.expression_cluster import expression_cluster
    from conekt.controllers.expression_profile import expression_profile
    from conekt.controllers.expression_network import expression_network
    from conekt.controllers.search import search
    from conekt.controllers.help import help
    from conekt.controllers.heatmap import heatmap
    from conekt.controllers.profile_comparison import profile_comparison
    from conekt.controllers.custom_network import custom_network
    from conekt.controllers.graph_comparison import graph_comparison
    from conekt.controllers.clade import clade
    from conekt.controllers.ecc import ecc
    from conekt.controllers.specificity_comparison import specificity_comparison
    from conekt.controllers.tree import tree
    from conekt.controllers.literature import literature

    LOGIN_ENABLED = app.config['LOGIN_ENABLED']
    BLAST_ENABLED = app.config['BLAST_ENABLED']

    app.register_blueprint(main)
    if LOGIN_ENABLED:
        app.register_blueprint(auth, url_prefix='/auth')
    else:
        app.register_blueprint(no_login, url_prefix='/auth')
        app.register_blueprint(no_login, url_prefix='/admin_controls')

    if BLAST_ENABLED:
        app.register_blueprint(blast, url_prefix='/blast')

    app.register_blueprint(sequence, url_prefix='/sequence')
    app.register_blueprint(species, url_prefix='/species')
    app.register_blueprint(go, url_prefix='/go')
    app.register_blueprint(interpro, url_prefix='/interpro')
    app.register_blueprint(cazyme, url_prefix='/cazyme')
    app.register_blueprint(family, url_prefix='/family')
    app.register_blueprint(expression_cluster, url_prefix='/cluster')
    app.register_blueprint(expression_profile, url_prefix='/profile')
    app.register_blueprint(expression_network, url_prefix='/network')
    app.register_blueprint(search, url_prefix='/search')
    app.register_blueprint(help, url_prefix='/help')
    app.register_blueprint(heatmap, url_prefix='/heatmap')
    app.register_blueprint(profile_comparison, url_prefix='/profile_comparison')
    app.register_blueprint(custom_network, url_prefix='/custom_network')
    app.register_blueprint(literature, url_prefix='/literature')
    app.register_blueprint(graph_comparison, url_prefix='/graph_comparison')
    app.register_blueprint(clade, url_prefix='/clade')
    app.register_blueprint(ecc, url_prefix='/ecc')
    app.register_blueprint(specificity_comparison, url_prefix='/specificity_comparison')
    app.register_blueprint(tree, url_prefix='/tree')


def configure_admin_panel(app):
    # Admin panel
    LOGIN_ENABLED = app.config['LOGIN_ENABLED']
    if LOGIN_ENABLED:
        from conekt.controllers.admin.views import MyAdminIndexView

        from conekt.controllers.admin.views.news import NewsAdminView

        from conekt.models.news import News

        admin = Admin(template_mode='bootstrap3', base_template='admin/my_base.html')

        admin.init_app(app, index_view=MyAdminIndexView(template='admin/home.html'))

        # CRUD for various database tables
        admin.add_view(
            NewsAdminView(
                News,
                db.session,
                endpoint='admin.news',
                url='news',
                name='News'
            )
        )



def configure_error_handlers(app):
    # Custom error handler for 404 errors

    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash("Could not handle request, CSRF token has expired. Please try again...", "warning")
        return redirect(url_for('main.screen'))

    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template('error/405.html'), 405

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error/404.html'), 404

    @app.errorhandler(403)
    def access_denied(e):
        next_page = request.url_rule
        if not current_user.is_authenticated:
            flash("Log in first...", "info")
            return redirect(url_for('auth.login', next=next_page))
        else:
            flash("Not permitted! Admin rights required.", "warning")
            return render_template('error/403.html'), 403


def configure_hooks(app):
    # Register form for basic searches, needs to be done here as it is included on every page!
    from conekt.forms.search import BasicSearchForm

    LOGIN_ENABLED = app.config['LOGIN_ENABLED']
    BLAST_ENABLED = app.config['BLAST_ENABLED']
    TWITTER_HANDLE = app.config['TWITTER_HANDLE'] if 'TWITTER_HANDLE' in app.config.keys() else None
    TUTORIAL_URL = app.config['TUTORIAL_URL'] if 'TUTORIAL_URL' in app.config.keys() else None
    IMPRINT = app.config['IMPRINT_URL'] if 'IMPRINT_URL' in app.config.keys() else None
    PRIVACY = app.config['PRIVACY_POLICY_URL'] if 'PRIVACY_POLICY_URL' in app.config.keys() else None

    @app.before_request
    def before_request():
        g.login_enabled = LOGIN_ENABLED
        g.blast_enabled = BLAST_ENABLED
        g.search_form = BasicSearchForm()
        g.twitter_handle = TWITTER_HANDLE
        g.imprint = IMPRINT
        g.privacy = PRIVACY

        g.tutorial = TUTORIAL_URL

        g.page_items = 30

        g.debug = app.config['DEBUG'] if 'DEBUG' in app.config else False

        if 'GLOB_MSG' in app.config and app.config['GLOB_MSG'] is not None:
            g.msg = app.config['GLOB_MSG']
            g.msg_title = app.config['GLOB_MSG_TITLE'] if 'GLOB_MSG_TITLE' in app.config else 'info'
        else:
            g.msg = None
