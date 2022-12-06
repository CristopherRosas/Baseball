from cs50 import SQL
import random

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///baseball.db")
homeTeamRuns = [0,0,0,0,0,0,0,0,0]
cpuRuns = [0,0,0,0,0,0,0,0,0]
cpuAvg = .2

def getHomeTeamRuns():
    return homeTeamRuns

def getCpuRuns():
    return cpuRuns

def simulateAtBat(avg):
    num = random.random()
    if avg >= num:
        return random.randint(1, 4)
    else:
        return 0

def simulateInning(text, inning, current_ID):
    outs = 0
    battingOrder = -1

    if text == "cpu":
        cpuRuns[inning] = 0

        while (outs < 3):
            result = simulateAtBat(cpuAvg)
            if result == 0:
                outs = outs + 1
            else:
                cpuRuns[inning] = cpuRuns[inning] + result

    if text == "home":
        homeTeamRuns[inning] = 0

        lineup = db.execute("SELECT playerID from roster WHERE userID = ?", current_ID)

        while (outs < 3):
            if battingOrder > 8:
                battingOrder = -1

            battingOrder = battingOrder + 1
            if lineup[battingOrder]["playerID"].split(" ")[0] == "Basic":
                result = simulateAtBat(.18)

            else:
                result = simulateAtBat(getAverage(lineup[battingOrder]["playerID"]))

            if result == 0:
                outs = outs + 1

            else:
                homeTeamRuns[inning] = homeTeamRuns[inning] + result

def finalOutcome(homeScore, cpuScore):
    if homeScore > cpuScore:
        return "You Win!"
    elif cpuScore > homeScore:
        return "You Lose."
    else:
        return "Tie."

def simulateGame(current_ID):
    for inning in range(9):
        simulateInning("cpu", inning, current_ID)
        simulateInning("home", inning, current_ID)

    homeScore = 0
    cpuScore = 0

    for i in range(9):
        homeScore = homeScore + homeTeamRuns[i]
        cpuScore = cpuScore + cpuRuns[i]

    return finalOutcome(homeScore, cpuScore)