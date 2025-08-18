#!/usr/bin/env python3
import click
import os
from conekt import (
    create_app,
    db
)

app = create_app('config')


@app.cli.command()
def initdb():
    """Initialize the database."""
    click.echo('Init the db')
    SQLALCHEMY_DATABASE_URI = app.config['SQLALCHEMY_DATABASE_URI']

    if SQLALCHEMY_DATABASE_URI.startswith('sqlite:///'):
        path = os.path.dirname(os.path.realpath(SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')))
        if not os.path.exists(path):
            os.makedirs(path)

    db.create_all(app=app)


if __name__ == '__main__':
    app.run()