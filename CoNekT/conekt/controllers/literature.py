from flask import Blueprint, redirect, url_for, render_template

from conekt import cache

literature = Blueprint('literature', __name__)

@literature.route('/')
def literature_overview():
    """
    For lack of a better alternative redirect users to the main page
    """
    return redirect(url_for('main.screen'))