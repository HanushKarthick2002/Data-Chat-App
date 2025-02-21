import React, { useState } from "react";
import axios from "axios";

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

        const response = await axios.post("http://127.0.0.1:8001/generate-query/", formData);
        setSqlQuery(response.data.sql_query);
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
            setSqlQuery(response.data.re_generated_sql_query);
            setQueryResult([]); // Reset previous result
            setFormattedAnswer(""); // Reset formatted answer
        } catch (error) {
            console.error("Error regenerating query:", error.response?.data || error.message);
            alert("Failed to regenerate query. Check console for details.");
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
        <div>
            <h1>CSV to SQL Query Generator</h1>

            <input type="file" onChange={(e) => setFile(e.target.files[0])} />
            <button onClick={handleFileUpload}>Upload CSV</button>

            <h2>Schema</h2>
            <pre>{JSON.stringify(schema, null, 2)}</pre>

            <input type="text" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask a question" />
            <button onClick={generateQuery}>Generate Query</button>

            <h2>Generated SQL</h2>
            <pre>{sqlQuery}</pre>

            <h2>Re-generate Query</h2>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Provide additional details" />
            <button onClick={regenerateQuery}>Re-generate</button>

            <button onClick={runQuery}>Run Query</button>

            <h2>Query Result</h2>
            <pre>{JSON.stringify(queryResult, null, 2)}</pre>

            <button onClick={formatAnswer}>Format Answer</button>

            <h2>Formatted Answer</h2>
            <pre>{formattedAnswer}</pre>
        </div>
    );
}

export default App;
