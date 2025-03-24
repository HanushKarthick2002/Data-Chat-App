from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import sqlite3
import json
import csv
import requests
import os
import io
import re
from typing import List
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection for in-memory database
conn = sqlite3.connect(":memory:", check_same_thread=False)
conn.row_factory = sqlite3.Row

@app.post("/upload-csv/")
def upload_csv(files: List[UploadFile] = File(...)):
    """Uploads multiple CSVs and stores them in separate in-memory SQLite tables."""
    try:
        table_names = []
        for file in files:
            contents = file.file.read()
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
            table_name = os.path.splitext(file.filename)[0].replace(" ", "_").replace("-", "_")
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            table_names.append(table_name)
        return {"message": "CSV files uploaded successfully!", "tables": table_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for file in files:
            file.file.close()

@app.get("/extract-schema/")
def extract_schema():
    """Extracts and returns the database schema for all uploaded tables."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        schema = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            schema[table] = [
                {
                    "Column Name": col[1],
                    "Type": col[2],
                    "Not Null": "Yes" if col[3] else "No",
                    "Default Value": col[4] if col[4] else "NULL",
                    "Primary Key": "Yes" if col[5] else "No"
                }
                for col in columns
            ]
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-query/")
def generate_query(question: str = Form(...)):
    """Generates an SQL query based on user input and multiple tables."""
    schema_response = extract_schema()
    schema_text = "\n".join(
        [f"Table: {table}\n" + "\n".join([f"{col['Column Name']} {col['Type']}" for col in columns]) for table, columns in schema_response["schema"].items()]
    )

    prompt = f"""
    You are an expert SQLite query writer. Here is the database schema:
    {schema_text}

    User's Question: {question}

    Write a SQLite query using appropriate joins if necessary to answer the question. 
    Always use column names in brackets [] without altering the original column name in case of LIKE statements.
    """
    
    response = requests.post(
        "https://llmfoundry.straive.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLMFOUNDRY_TOKEN')}:my-test-project"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    )
    
    response1 = response.json()["choices"][0]["message"]["content"]
    print("Extracted SQL Query:", response1)
    return {"sql_query": response1}

@app.post("/run-query/")
def run_query(query: str = Form(...)):
    """Executes the generated SQL query."""
    try:
        df = pd.read_sql_query(query, conn)
        result = df.to_dict(orient="records")
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/format-response/")
def format_response(question: str = Form(...), result: str = Form(...)):
    """Formats the result into human-readable language using LLM."""
    prompt = f"""
    Convert the following database query result into a human-readable format:\n\n
    User's Question: {question}
    Answer:
    {result}
    Format the answer and present it in a neat and understandable way for the user.
    """
    
    response = requests.post(
        "https://llmfoundry.straive.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLMFOUNDRY_TOKEN')}:my-test-project"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    )
    
    human_readable_response = response.json()["choices"][0]["message"]["content"]
    
    return {"formatted_answer": human_readable_response}

@app.post("/re_generate/")
def re_generate(
    question: str = Body(...), 
    previous_response: str = Body(...), 
    user_description: str = Body(...)
):
    """Regenerates an improved SQL query based on user feedback."""
    schema_response = extract_schema()
    schema_text = "\n".join(
        [f"Table: {table}\n" + "\n".join([f"{col['Column Name']} {col['Type']}" for col in columns]) for table, columns in schema_response["schema"].items()]
    )
    prompt = f"""
    You are an expert SQLite query writer. Here is the database schema:
    {schema_text}

    User's Original Question: {question}
    Previous LLM Response: {previous_response}
    Additional User Description: {user_description}

    Based on the additional details provided by the user, regenerate and refine the SQL query for better accuracy and completeness.
    Always use column names in brackets [] without altering the original column name in case of LIKE statements.Make sure to give only one sql query as response.
    """
    
    response = requests.post(
        "https://llmfoundry.straive.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLMFOUNDRY_TOKEN')}:my-test-project"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    )
    
    sql_query = response.json()["choices"][0]["message"]["content"]
    print("Regenerated SQL Query:", sql_query)
    
    return {"re_generated_sql_query": sql_query}

def reset_database():
    """Drops all tables to ensure a fresh in-memory database after a page reload."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
    conn.commit()

@app.post("/reset-db/")
def reset_db():
    """Manually clears all tables from the database."""
    reset_database()
    return {"message": "Database reset successfully!"}


# Call reset_database() when FastAPI starts
reset_database()

