from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import sqlite3
import json
import csv
import requests
import os
import io
import re

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
def upload_csv(file: UploadFile = File(...)):
    """Uploads a CSV and stores it in an in-memory SQLite table."""
    try:
        contents = file.file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

        # Store in SQLite
        df.to_sql("uploaded_data", conn, if_exists="replace", index=False)
        return {"message": "CSV uploaded successfully!", "columns": df.columns.tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()

@app.get("/extract-schema/")
def extract_schema():
    """Extracts and returns the database schema."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(uploaded_data)")
        columns = cursor.fetchall()

        schema = [
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
    """Generates an SQL query based on user input."""
    schema_response = extract_schema()
    schema_text = "\n".join(
        [f"{col['Column Name']} {col['Type']}" for col in schema_response["schema"]]
    )

    prompt = f"""
    You are an expert SQLite query writer. Here is the database schema:
    {schema_text}

    User's Question: {question}

    Write a SQLite query (assuming table name is 'uploaded_data') to answer the question.
    """
    
    response = requests.post(
        "https://llmfoundry.straive.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLMFOUNDRY_TOKEN')}:my-test-project"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    )
    
    # sql_query = response.json()["choices"][0]["message"]["content"]
    response1 = response.json()["choices"][0]["message"]["content"]
    match = re.search(r"```sql\n(.*?)\n```", response1, re.DOTALL)
    sql_query = match.group(1).strip() if match else response.strip()
    print("Extracted SQL Query:", sql_query)
    
    
    return {"sql_query": sql_query}

@app.post("/re_generate/")
def re_generate(question: str = Form(...), previous_response: str = Form(...), user_description: str = Form(...)):
    """Regenerates an improved SQL query based on user feedback."""
    schema_response = extract_schema()
    schema_text = "\n".join(
        [f"{col['Column Name']} {col['Type']}" for col in schema_response["schema"]]
    )
    print("1")
    print(question)
    print(previous_response)
    print(user_description)

    prompt = f"""
    You are an expert SQLite query writer. Here is the database schema:
    {schema_text}

    User's Original Question: {question}
    Previous LLM Response: {previous_response}
    Additional User Description: {user_description}

    Based on the additional details provided by the user, regenerate and refine the SQL query for better accuracy and completeness.
    """
    
    response = requests.post(
        "https://llmfoundry.straive.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLMFOUNDRY_TOKEN')}:my-test-project"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    )
    
    response_text = response.json()["choices"][0]["message"]["content"]
    match = re.search(r"```sql\n(.*?)\n```", response_text, re.DOTALL)
    sql_query = match.group(1).strip() if match else response_text.strip()

    print("Regenerated SQL Query:", sql_query)
    
    return {"re_generated_sql_query": sql_query}



@app.post("/run-query/")
def run_query(query: str = Form(...)):
    """Executes the generated SQL query."""
    print("hello")
    try:
        df = pd.read_sql_query(query, conn)
        result = df.to_dict(orient="records")
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/format-response/")
def format_response(question: str = Form(...), result: str = Form(...)):
    """Formats the result into human-readable language using LLM."""
    prompt = f"Convert the following database query result into a human-readable format:\n\n{result}"
    
    response = requests.post(
        "https://llmfoundry.straive.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('LLMFOUNDRY_TOKEN')}:my-test-project"},
        json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    )
    
    human_readable_response = response.json()["choices"][0]["message"]["content"]
    
    return {"formatted_answer": human_readable_response}

# Run the server with: uvicorn main:app --reload
