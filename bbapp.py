import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///lahmansbaseballdb.sqlite")

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
    current_ID = session["user_id"]
    for symbol in db.execute("SELECT symbol from portfolio where user_ID=?", current_ID):
        reloadStock = lookup(symbol["symbol"])
        db.execute("UPDATE portfolio SET price=? WHERE user_ID=? AND name=?",
                   reloadStock['price'], current_ID, reloadStock['name'])

    stocksOwned = db.execute(
        "SELECT symbol, quantity_owned, name, price from portfolio WHERE user_ID = ?", current_ID)

    # for userCash, use 0 to index to this query's first and only row (returned user's cash)
    userCash = db.execute("SELECT cash FROM users WHERE id=?", current_ID)[0]["cash"]
    stockWorth = {}
    TOTALVALUE = userCash

    for stock in stocksOwned:
        stockWorth[stock["symbol"]] = int(stock["quantity_owned"]) * lookup(stock["symbol"])["price"]
        TOTALVALUE = TOTALVALUE + stockWorth[stock["symbol"]]

    return render_template("index.html", stocksOwned=stocksOwned, cash=userCash, TOTALVALUE=TOTALVALUE, stockWorth=stockWorth)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    current_ID = session["user_id"]
    if request.method == "POST":

        # earmark stock + related variables for condensed price and symbol statements
        formShares = request.form.get("shares")
        formSymbol = request.form.get("symbol")
        desiredStock = lookup(formSymbol)
       # for userCash, use 0 to index to this query's first and only row (returned user's cash)
        userCash = db.execute("SELECT cash FROM users WHERE id=?", current_ID)[0]["cash"]

        # set of checks, as requested
        if formSymbol == None:
            return apology("Sorry, Symbol Not Found")
        if not desiredStock:
            return apology("Symbol not Valid")
        elif not formShares or not formShares.isdigit():
            return apology("Shares value needed, or is not valid", 400)
        else:
            if userCash < int(formShares) * desiredStock['price']:
                return apology("Insufficient Funds, Chief")
            else:
                db.execute("INSERT INTO transactionLog (user_ID, symbol, quantity, type, price) VALUES (?, ?, ?, ?, ?)",
                           current_ID, desiredStock['symbol'], formShares, "purchase", desiredStock['price'])

                # reduce user cash
                db.execute("UPDATE users SET cash=? WHERE id=?", userCash-int(
                    formShares) * desiredStock['price'], current_ID)

                # for index and sell, will be helpful to have user specific portfolio list (portfolio table monitors constant quantity of owned stock)
                # check if stock is already owned
                old_quantity = db.execute("SELECT quantity_owned FROM portfolio WHERE symbol=? AND user_ID=?",
                                          formSymbol, current_ID)
                if len(old_quantity) > 0:
                    db.execute("UPDATE portfolio SET quantity_owned=? WHERE user_ID=? AND symbol=?", old_quantity[0]["quantity_owned"] +
                               int(formShares), current_ID, formSymbol)
                else:
                    db.execute("INSERT INTO portfolio (user_ID, symbol, quantity_owned, name, price) VALUES (?, ?, ?, ?, ?)",
                               current_ID, formSymbol, formShares, desiredStock['name'], desiredStock['price'])

            flash('Purchase Successful!')
            return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    history = db.execute(
        "SELECT symbol, quantity, type, price, time FROM transactionLog WHERE user_ID=?", session["user_id"])
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
        # Access form data
        symbolQuote = lookup(request.form.get("symbol"))
        if symbolQuote == None:
            return apology("Symbol Not Found")
        else:
            flash('Search Successful!')
            return render_template("quoted.html", name=symbolQuote['name'], price=symbolQuote['price'], symbol=symbolQuote['symbol'])

    else:
        return render_template("quote.html")


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
    formShares = request.form.get("shares")
    formSymbol = request.form.get("symbol")
    quantity = db.execute("SELECT quantity_owned FROM portfolio WHERE user_ID=? AND symbol=?",
                          current_ID, formSymbol)

    if request.method == "POST":

        # required backend check, even if monitored @ html level (frontend)
        if formSymbol == None:
            return apology("Sorry, Symbol Not Found")
        elif formShares == None:
            return apology("Sorry, number of shares was not positive")
        elif not quantity:
            return apology("You do not own this stock")

        # for quantity, use 0 to index to this query's first and only row (quanity_owned in portfolio)
        # (we know not empty because of previous check)
        elif int(formShares) > quantity[0]["quantity_owned"]:
            return apology("You are trying to sell more shares than you have")
        else:
            desiredStock = lookup(formSymbol)
            userMoney = db.execute(
                "SELECT cash FROM users WHERE id=?", current_ID)

            # insert new data into transactionLog
            db.execute("INSERT INTO transactionLog (user_ID, symbol, quantity, type, price) VALUES (?, ?, ?, ?, ?)",
                       current_ID, desiredStock['symbol'], -1 * int(formShares), "sell", desiredStock['price'])

            # increase user cash
            db.execute("UPDATE users SET cash=? WHERE id =?", userMoney[0]["cash"]+int(
                formShares) * desiredStock['price'], current_ID)

            # make change to portfolio
            db.execute("UPDATE portfolio SET quantity_owned=? WHERE user_ID=? AND symbol=?", int(
                quantity[0]["quantity_owned"])-int(formShares), current_ID, formSymbol)

            flash('Share(s) Sold!')
            return redirect("/")
    else:

        # create a list of unique stock symbols that we own, from info in portfolio (allows html to run basic jinja for loop)
        stocksOwned = []
        for row in db.execute("SELECT symbol from portfolio WHERE user_ID = ?", current_ID):
            stocksOwned.append(row["symbol"])
        return render_template("sell.html", stocksOwned=stocksOwned)


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
            db.execute("INSERT INTO transactionLog (user_ID, symbol, quantity, type, price) VALUES (?, ?, ?, ?, ?)",
                       current_ID, "$", depositAmount, "deposit", depositAmount)
            flash('Deposit Successful!')
            return redirect("/")
    else:
        return render_template("deposit.html")
