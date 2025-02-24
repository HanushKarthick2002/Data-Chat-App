import React, { useState } from "react";
import axios from "axios";
import "./App.css"; // Import the CSS file

function App() {
    const [file, setFile] = useState(null);
    const [question, setQuestion] = useState("");
    const [description, setDescription] = useState("");
    const [schema, setSchema] = useState([]);
    const [sqlQuery, setSqlQuery] = useState("");
    const [queryResult, setQueryResult] = useState([]);
    const [formattedAnswer, setFormattedAnswer] = useState("");

    const handleFileUpload = async () => {
        const formData = new FormData();
        formData.append("file", file);
        
        const response = await axios.post("http://127.0.0.1:8001/upload-csv/", formData);
        alert(response.data.message);
        fetchSchema();
    };

    const fetchSchema = async () => {
        const response = await axios.get("http://127.0.0.1:8001/extract-schema/");
        setSchema(response.data.schema);
    };

    const generateQuery = async () => {
        const formData = new FormData();
        formData.append("question", question);
    
        try {
            const response = await axios.post("http://127.0.0.1:8001/generate-query/", formData);
            const responseText = String(response.data.sql_query);
            const match = responseText.match(/```sql\n([\s\S]*?)\n```/);
            const sqlQuery = match ? match[1].trim() : "";
            setSqlQuery(sqlQuery);
        } catch (error) {
            console.error("Error generating query:", error);
        }
    };

    const regenerateQuery = async () => { 
        const payload = {
            question: question,
            previous_response: sqlQuery,
            user_description: description
        };
    
        try {
            const response = await axios.post("http://127.0.0.1:8001/re_generate/", payload, {
                headers: { "Content-Type": "application/json" }
            });
    
            let sqlQuery = response.data.re_generated_sql_query;
            const match = sqlQuery.match(/```sql\n([\s\S]*?)\n```/);
            sqlQuery = match ? match[1].trim() : sqlQuery.trim();
    
            setSqlQuery(sqlQuery);
            setQueryResult([]);
            setFormattedAnswer("");
        } catch (error) {
            console.error("Error regenerating query:", error.response?.data || error.message);
            alert("Failed to regenerate query.");
        }
    };

    const runQuery = async () => {
        const formData = new FormData();
        formData.append("query", sqlQuery);

        const response = await axios.post("http://127.0.0.1:8001/run-query/", formData);
        setQueryResult(response.data.result);
    };

    const formatAnswer = async () => {
        const formData = new FormData();
        formData.append("question", question);
        formData.append("result", JSON.stringify(queryResult));

        const response = await axios.post("http://127.0.0.1:8001/format-response/", formData);
        setFormattedAnswer(response.data.formatted_answer);
    };

    return (
        <div className="container">
            <h1 className="title">CSV to SQL Query Generator</h1>

            <div className="card">
                <input type="file" onChange={(e) => setFile(e.target.files[0])} className="file-input" />
                <button onClick={handleFileUpload} className="btn">Upload CSV</button>
            </div>

            <div className="card">
                <h2>Schema</h2>
                <pre className="output">{JSON.stringify(schema, null, 2)}</pre>
            </div>

            <div className="card">
                <input type="text" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question" className="input" />
                <button onClick={generateQuery} className="btn">Generate Query</button>
            </div>

            <div className="card">
                <h2>Generated SQL</h2>
                <pre className="output">{sqlQuery}</pre>
            </div>

            <div className="card">
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Provide additional details" className="input"></textarea>
                <button onClick={regenerateQuery} className="btn">Re-generate</button>
            </div>

            <button onClick={runQuery} className="btn">Run Query</button>

            <div className="card">
                <h2>Query Result</h2>
                <pre className="output">{JSON.stringify(queryResult, null, 2)}</pre>
            </div>

            <button onClick={formatAnswer} className="btn">Format Answer</button>

            <div className="card">
                <h2>Formatted Answer</h2>
                <pre className="output">{formattedAnswer}</pre>
            </div>
        </div>
    );
}

export default App;
