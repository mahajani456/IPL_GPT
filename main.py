import os
import re
import sqlite3
import pandas as pd
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import openai
import sqlparse
import uvicorn
from fastapi.staticfiles import StaticFiles

openai.api_key = os.environ['OPENAI_API_KEY']



app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

DATABASE = 'ipl.db'
templates = Jinja2Templates(directory="templates")


def get_db():
  db = sqlite3.connect(DATABASE)
  return db


@app.on_event("startup")
async def startup_event():
  init_db()


def init_db():
  db = get_db()
  with open('schema.sql', mode='r') as f:
    db.cursor().executescript(f.read())
  db.commit()


  # Load data from CSV files
  match_ball_by_ball_data = pd.read_csv('data/ipl_match_ball_by_ball_data.csv')
  match_info_data = pd.read_csv('data/ipl_match_info_data.csv')

  # Insert data into the tables
  match_ball_by_ball_data.to_sql('match_ball_by_ball',
                                 db,
                                 if_exists='append',
                                 index=False)
  match_info_data.to_sql('match_info', db, if_exists='append', index=False)


init_db()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
  return templates.TemplateResponse("index.html", {"request": request})


sample_query = "get top 5 bowlers"


@app.get("/top_scorers")
async def top_scorers():
  top_scorers_query = '''
    SELECT striker, SUM(runs_off_bat) as total_runs
    FROM match_ball_by_ball
    GROUP BY striker
    ORDER BY total_runs DESC
    LIMIT 10
    '''

  db = get_db()
  result = db.execute(top_scorers_query).fetchall()
  top_scorers = [{"striker": row[0], "total_runs": row[1]} for row in result]
  return top_scorers


############ defining database schema to be used by GPT3.5 ############
database_schema = """
The IPL database has two tables: match_ball_by_ball and match_info.

The match_ball_by_ball table has the following columns:
- match_id: integer
- season: integer
- start_date: text
- venue: text
- innings: integer
- ball: real
- batting_team: text
- bowling_team: text
- striker: text
- non_striker: text
- bowler: text
- runs_off_bat: integer
- extras: integer
- wides: integer
- noballs: integer
- byes: integer
- legbyes: integer
- penalty: integer
- wicket_type: text
- player_dismissed: text
- other_wicket_type: text
- other_player_dismissed: text

The match_info table has the following columns:
- match_id: integer (primary key)
- season: integer
- date: text
- city: text
- venue: text
- team1: text
- team2: text
- toss_winner: text
- toss_decision: text
- player_of_match: text
- winner: text
- winner_wickets: integer
- winner_runs: integer
- outcome: text
- result_type: text
- results: text
- gender: text
- event: text
- match_number: integer
- umpire1: text
- umpire2: text
- reserve_umpire: text
- tv_umpire: text
- match_referee: text
- eliminator: text
- method: text
- date_1: text
"""


async def text_to_sql(prompt):
  full_prompt = f"{database_schema}\nTranslate the following English text into an SQL query.: {prompt}"
  chat_prompt = {
    "role": "system",
    "content": "You are a helpful assistant that translates English to SQL."
  }
  user_message = {"role": "user", "content": full_prompt}

  response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[chat_prompt, user_message],
    max_tokens=150,
    n=1,
    stop=None,
    temperature=0.5,
  )
  raw_content = response.choices[0].message['content'].strip()
  print("raw_content: ")
  print(raw_content)
  print('####')
  # Extract the content between triple backticks
  pattern = r"(SELECT[\s\S]*LIMIT \d+;)"
  match = re.search(pattern, raw_content)
  #match = re.search(r"```(.+?)```", raw_content, flags=re.DOTALL)
  if match:
    sql_query = match.group(1).strip()
  else:
    sql_query = raw_content
  print("sql_query_output: ")
  print(sql_query)
  return sql_query


def is_valid_sql(sql_query):
  try:
    parsed = sqlparse.parse(sql_query)
    if not parsed:
      return False

    # Check if the query is a SELECT statement
    statement = parsed[0]
    if not isinstance(
        statement,
        sqlparse.sql.Statement) or statement.get_type().upper() != 'SELECT':
      return False

    return True
  except sqlparse.exceptions.SQLParseError:
    return False


def query_db(db, query, args=(), one=False):
  cur = db.execute(query, args)
  rv = [
    dict((cur.description[idx][0], value) for idx, value in enumerate(row))
    for row in cur.fetchall()
  ]
  return (rv[0] if rv else None) if one else rv


#### Adding code for most searched queries ####
def update_query_history(query):
  db = get_db()
  existing_query = query_db(
    db,
    "SELECT id, query_count FROM query_history WHERE query = ?", (query, ),
    one=True)

  print(existing_query)
  if existing_query:
    query_id = existing_query["id"]
    new_count = existing_query["query_count"] + 1
    db.execute("UPDATE query_history SET query_count = ? WHERE id = ?",
               (new_count, query_id))
  else:
    db.execute("INSERT INTO query_history (query) VALUES (?)", (query, ))
  db.commit()


@app.post("/query", response_class=HTMLResponse)
async def user_query(request: Request, query: str = Form(default=None)):
  print("all headers")
  print(request.headers)
  if not query:
    # Process XHR request
    query = await request.form().get("query")
  sql_query = await text_to_sql(query)
  ##print("sql_query generated: ")
  ##print(sql_query)
  if not is_valid_sql(sql_query):
    print("Invalid SQL query")
    return "Invalid or unsupported SQL query. Please try again."

  try:
    update_query_history(query)  # Update the query history
    db = get_db()
    result = query_db(db, sql_query)
    print('result: ')
    print(result)
    # Check if the request is XHR
    print('X-Requested-With')
    print(request.headers.get("X-Request-Type"))
    if (request.headers.get("X-Request-Type") == "XHR"):
      return JSONResponse(content={
        "result": result,
        "query2": query,
        "sql_query": sql_query
      })
    else:
      # Display the result in a new template or the existing one based on your requirements
      return templates.TemplateResponse(
        "query_result.html", {
          "request": request,
          "result": result,
          "query2": query,
          "sql_query": sql_query
        })
  except Exception as e:
    print('error: ')
    print(e)
    return str(e)


@app.get("/most_run_queries")
async def most_run_queries():
  most_run_queries_query = '''
    SELECT query, query_count
    FROM query_history
    ORDER BY query_count DESC
    LIMIT 10
    '''
  db = get_db()
  result = query_db(db, most_run_queries_query)
  print('result2:')
  print(result)
  most_run_queries = [{
    "query": row["query"],
    "query_count": row["query_count"]
  } for row in result]
  return most_run_queries


print('Initializing sample query')
update_query_history(sample_query)

uvicorn.run(app, host="0.0.0.0", port="8080")
