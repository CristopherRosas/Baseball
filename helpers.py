import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps

import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
import math

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///lahmansbaseballdb.sqlite")
db1 = SQL("sqlite:///baseball.db")


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(firstName, lastName):
    if firstName == "Basic":
        return ("firstName" + " " + lastName)
    else:
        return db.execute("SELECT playerID FROM people WHERE nameFirst = ? AND nameLast = ? LIMIT 1", firstName, lastName)[0]['playerID']

def getFullName(id):
    return db.execute("SELECT nameFirst FROM people WHERE playerID = ?", id)[0]['nameFirst'] + " " + db.execute("SELECT nameLast FROM people WHERE playerID = ?", id)[0]['nameLast']

def getSalary(id):
        if len(db.execute("SELECT salary FROM salaries WHERE playerID = ? ORDER BY yearID desc LIMIT 1", id)) > 0:
            return db.execute("SELECT salary FROM salaries WHERE playerID = ? ORDER BY yearID desc LIMIT 1", id)[0]['salary']
        else:
            return 15000000

def getPosition(id):
    return db.execute("SELECT POS FROM fielding WHERE playerID = ?", id)[0]['POS']

def getAvg(id):
    if db.execute("SELECT AB FROM batting WHERE playerID = ? AND AB > 0", id) > 0:
        search = db.execute("SELECT H, AB FROM batting WHERE playerID = ?", id)
        return math.ceil((search[0]['H']/search[0]['AB']) * 1000.0 / 1000.0)
    else:
        return .05

def numPeople(firstName, lastName):
    return db.execute("SELECT COUNT (playerID) from people where nameFirst = ? AND nameLast = ?", firstName, lastName)[0]["COUNT (playerID)"]

def getPlayersOfPosition(pos):
    return db.execute("SELECT DISTINCT playerID FROM fielding WHERE POS = ? AND yearID > 2016", pos)

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
