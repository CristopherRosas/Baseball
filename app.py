import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, json
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, getSalary, usd, getPosition, getFullName, numPeople, getPlayersOfPosition, getAvg
from game import simulateGame, getHomeTeamRuns, getCpuRuns

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///baseball.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    # make sure to update the value of every stock before calculating value
    # do this in roster to have both changing values / transaction values (important for calculating marginal gains/losses)
    # [two tables makes for easier access/seperation, less convoluted queries]
    current_ID = session["user_id"]

    playersOwned = db.execute(
        "SELECT playerID, salary, position from roster WHERE userID = ?", current_ID)

    # for userCash, use 0 to index to this query's first and only row (returned user's cash)
    userCash = db.execute("SELECT cash FROM users WHERE id=?", current_ID)[
        0]["cash"]
    TOTALVALUE = userCash
    names = {}

    for player in playersOwned:
        if player["playerID"].split(" ")[0] == "Basic":
            names[player["playerID"]] = "Basic" + " " + player["position"]
        else:
            names[player["playerID"]] = getFullName(player["playerID"])
        TOTALVALUE = TOTALVALUE + player["salary"]

    return render_template("index.html", playersOwned=playersOwned, cash=userCash, TOTALVALUE=TOTALVALUE, names=names)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    current_ID = session["user_id"]
    if request.method == "POST":

        # earmark stock + related variables for condensed price and symbol statements
        formFirst = request.form.get("firstName")
        formLast = request.form.get("lastName")

       # for userCash, use 0 to index to this query's first and only row (returned user's cash)
        userCash = db.execute("SELECT cash FROM users WHERE id=?", current_ID)[
            0]["cash"]

        # set of checks, as requested
        if numPeople(formFirst, formLast) == 0:
            return apology("Name not Found")

        desiredPlayerID = lookup(formFirst, formLast)
        if db.execute("SELECT COUNT (playerID) from roster WHERE userID = ? and playerID = ?", current_ID, desiredPlayerID)[0]["COUNT (playerID)"]:
            return apology("Already owned")
        if getPosition(desiredPlayerID) == "OF" and db.execute("SELECT COUNT (playerID) from roster WHERE userID = ? and position = ?", current_ID, getPosition(desiredPlayerID))[0]["COUNT (playerID)"] > 2:
            return apology("You have too many outfielders")
        elif db.execute("SELECT COUNT (playerID) from roster WHERE userID = ? and position = ?", current_ID, getPosition(desiredPlayerID))[0]["COUNT (playerID)"]:
            return apology("You own a player for that position already. Must sell old to buy new.")
        else:
            playerPrice = getSalary(desiredPlayerID)
            if userCash < int(playerPrice):
                return apology("Insufficient Funds, Chief")
            else:
                db.execute("INSERT INTO transactionLog (userID, playerID, lastName, firstName, price) VALUES (?, ?, ?, ?, ?)",
                           current_ID, desiredPlayerID, formLast, formFirst, playerPrice)

                db.execute("INSERT INTO roster (userID, playerID, salary, position) VALUES (?, ?, ?, ?)",
                           current_ID, desiredPlayerID, playerPrice, getPosition(desiredPlayerID))

                # reduce user cash
                db.execute("UPDATE users SET cash=? WHERE id=?",
                           userCash-playerPrice, current_ID)

                flash('Purchase Successful!')
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    history = db.execute(
        "SELECT time, lastName, firstName, price, playerID FROM transactionLog WHERE userID=?", session["user_id"])
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash('Login Successful!')
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
       position = request.form.get("position")
       playersOfPosition = getPlayersOfPosition(position)

       prices = {}
       names = {}
       battingAverages = {}

       for player in playersOfPosition:
            prices[player['playerID']] = getSalary(player['playerID'])
            names[player['playerID']] = getFullName(player['playerID'])
            battingAverages[player['playerID']] = getAvg(player['playerID'])

       flash('Search Successful!')
       return render_template("quoted.html", prices = prices, names = names, battingAverages = battingAverages, playersOfPosition = playersOfPosition)
    else:
       positions = ["1B", "2B", "3B", "SS", "OF", "C", "P"]
       return render_template("quote.html", positions=positions)



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Access form data
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not (username and password and confirmation):
            return apology("Incomplete Data Entry")
        elif password != confirmation:
            return apology("password and confirmation don't match")
        elif len(db.execute("SELECT * FROM users WHERE username = ?", username)) != 0:
            return apology("Repeat Username")

        # Insert data into database
        hashPass = generate_password_hash(
            password, method='pbkdf2:sha256', salt_length=8)
        session["user_id"] = db.execute(
            "INSERT INTO users (username, hash) VALUES(?, ?)", username, hashPass)

        # Create Default Players
        positionsBasic = ["1B", "2B", "3B", "SS", "LF","CF","RF", "C", "P"]
        for position in positionsBasic:
            db.execute("INSERT INTO roster (userID, playerID, salary, position) VALUES (?, ?, ?, ?)",
                            session["user_id"], "Basic" + " " + position , 1000000, position)

        # Go back to homepage
        flash('Registered!')
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    current_ID = session["user_id"]

    """Sell shares of stock"""
    # earmark stock + related variables for condensed price and symbol statements
    if request.method == "POST":
        formName = request.form.get("playerName")

        # required backend check, even if monitored @ html level (frontend)
        if formName == None:
            return apology("YOU DONT OWN, or DID NOT ENTER")

        else:
            firstName = formName.split(" ")[0]
            lastName = formName.split(" ")[1]
            if firstName == "Basic":
                playerID = firstName + " " + lastName
                playerPrice =  db.execute("SELECT salary from roster WHERE playerID = ?", playerID)[0]["salary"]
            else:
                playerID = lookup(firstName, lastName)
                playerPrice = getSalary(playerID)

            userMoney = db.execute(
                "SELECT cash FROM users WHERE id=?", current_ID)

            # insert new data into transactionLog
            db.execute("INSERT INTO transactionLog (userID, playerID, lastName, firstName, price) VALUES (?, ?, ?, ?, ?)",
                       current_ID, playerID, lastName, firstName, -1 * playerPrice)

            # increase user cash
            db.execute("UPDATE users SET cash=? WHERE id =?", userMoney[0]["cash"]+playerPrice, current_ID)

            # make change to roster
            db.execute("DELETE FROM roster where playerID = ? AND userID = ?", playerID, current_ID)

            flash('Share(s) Sold!')
            return redirect("/")
    else:
        # create a list of unique stock symbols that we own, from info in roster (allows html to run basic jinja for loop)
        playersOwned = []
        for row in db.execute("SELECT playerID, position from roster WHERE userID = ?", current_ID):
            if row["playerID"].split(" ")[0] == "Basic":
                playersOwned.append("Basic" + " " + row["position"])
            else:
                playersOwned.append(getFullName(row["playerID"]))
        return render_template("sell.html", playersOwned=playersOwned)


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    current_ID = session["user_id"]
    """Deposit Cash"""
    if request.method == "POST":
        depositAmount = request.form.get("deposit")

        # super careful checking
        if request.form.get("accountNumber") != request.form.get("confirmAccount"):
            return apology("Sorry, Account Number was not Confirmed Correctly")
        elif depositAmount == None or not depositAmount.isdigit():
            return apology("Please Enter Amount for Deposit")
        else:
            userMoney = db.execute(
                "SELECT cash FROM users WHERE id=?", current_ID)[0]["cash"]

            # add amount to previous cash
            db.execute("UPDATE users SET cash=? WHERE id =?",
                       userMoney+int(depositAmount), current_ID)

            # put into transactionLog for reflection in history
            db.execute("INSERT INTO transactionLog (userID, playerID, firstName, lastName, price) VALUES (?, ?, ?, ?, ?)",
                       current_ID, "$", "Cash", "Deposit", depositAmount)
            flash('Deposit Successful!')
            return redirect("/")
    else:
        return render_template("deposit.html")

@app.route("/gameSimulate", methods=["GET", "POST"])
@login_required
def gameSimulate():
     outcome = simulateGame(session["user_id"])
     homeInnings = json.dumps(getHomeTeamRuns())
     cpuInnings = json.dumps(getCpuRuns())

     return render_template("gameSimulate.html", outcome = outcome, homeInnings = homeInnings, cpuInnings = cpuInnings)

