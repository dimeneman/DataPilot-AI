# 🚀 DataPilot AI

> An Agentic AI Platform for SQL Analytics and ETL Automation powered by **LangGraph**, **Google Gemini**, **FastAPI**, **PostgreSQL**, and **Pandas**.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-purple)
![Gemini](https://img.shields.io/badge/Google-Gemini-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![License](https://img.shields.io/badge/License-MIT-success)

---

# 📌 Overview

DataPilot AI is an **Agentic AI Data Engineering Platform** that allows users to interact with databases and data pipelines using natural language.

Instead of writing SQL queries or Pandas code manually, users simply ask questions in plain English. The system intelligently chooses the appropriate workflow, generates the required code, validates it, executes it, and returns human-friendly results.

The project demonstrates practical applications of:

- Agentic AI
- LangGraph Workflows
- LLM Tool Calling
- SQL Generation
- ETL Automation
- Function Calling
- FastAPI APIs
- PostgreSQL Integration

---

# ✨ Features

## 🤖 SQL Analyst Agent

- Natural Language → SQL
- Automatic SQL Generation
- Database Schema Understanding
- SQL Safety Validation
- PostgreSQL Query Execution
- Natural Language Result Generation

---

## 🔄 ETL Agent

Supports automated ETL operations including

- Extract data from REST APIs
- Save data as CSV
- Save data as JSON
- Save data as Parquet
- Data inspection
- Context-aware Pandas code generation
- Automatic code execution

---

## 🧠 AI Powered

Uses Google Gemini models

- Gemini 3.8 Flash
- Gemini 3.5 Flash Lite

for

- SQL Generation
- Data Analysis
- Pandas Code Generation
- Result Explanation
- Tool Calling

---

# 🏗 Architecture

```
                User
                  │
                  ▼
        Streamlit Frontend
                  │
                  ▼
            FastAPI Backend
                  │
                  ▼
              LangGraph
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
 SQL Analyst Agent     ETL Agent
         │                 │
         ▼                 ▼
     Google Gemini     Google Gemini
         │                 │
         ▼                 ▼
 PostgreSQL         REST APIs + Pandas
         │                 │
         └────────┬────────┘
                  ▼
           Final Response
```

---

# ⚙ Tech Stack

## Backend

- FastAPI
- Python 3.12

## AI

- LangGraph
- LangChain
- Google Gemini
- Function Calling

## Database

- PostgreSQL

## Data Processing

- Pandas
- NumPy

## API

- Requests

## Environment

- python-dotenv

---

# 📂 Project Structure

```
DataPilot-AI/

agents/
│
├── sql_analyst.py
├── etl_agent.py

utils/
│
├── database.py
├── etl_tools.py
├── llm_pick.py

models/
│
├── schema.py

data/
│
├── extract/
├── transform/
├── load/

server.py

requirements.txt

README.md
```

---

# 🧩 SQL Agent Workflow

```
User Question

        │

        ▼

Curate Question

        │

        ▼

Read Database Schema

        │

        ▼

Generate SQL

        │

        ▼

Safety Validation

        │

   Yes / No

   │        │

Execute   Cancel

   │

   ▼

Generate Final Answer

   │

   ▼

Return Response
```

---

# 🔄 ETL Workflow

```
User Request

      │

      ▼

LangGraph

      │

      ▼

Choose Tool

      │

      ▼

Extract Data

      │

      ▼

Generate Pandas Code

      │

      ▼

Execute Code

      │

      ▼

Save Dataset

      │

      ▼

Return Result
```

---

# 🚀 Installation

Clone the repository

```bash
git clone https://github.com/<your-username>/DataPilot-AI.git

cd DataPilot-AI
```

Create virtual environment

```bash
python -m venv .venv
```

Activate

Linux

```bash
source .venv/bin/activate
```

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Variables

Create a `.env` file

```env
GOOGLE_API_KEY=your_api_key

DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=password
DB_NAME=database_name
```

---

# ▶ Running the Project

Start FastAPI

```bash
uvicorn server:app --reload
```

Run SQL Agent

```bash
python agents/sql_analyst.py
```

Run ETL Agent

```bash
python agents/etl_agent.py
```

---

# 💡 Example Queries

## SQL Agent

```
Show the top 10 customers by total spending.

List all available payment methods.

Find products with stock less than 20.

Show monthly revenue.

Find the most purchased product.
```

---

## ETL Agent

```
Extract data from https://pokeapi.co/api/v2/pokemon
and save it as CSV.

Filter only Bulbasaur records.

Convert CSV into Parquet.

Keep only selected columns.

Remove duplicate rows.

Save transformed data as JSON.
```

---

# 📈 Current Capabilities

- SQL Query Generation
- SQL Safety Validation
- PostgreSQL Execution
- REST API Data Extraction
- Pandas Transformation
- CSV Export
- JSON Export
- Parquet Export
- LangGraph Multi-Step Workflows
- Tool Calling
- Structured Outputs

---

# 🔮 Future Improvements

- Supervisor Agent
- Data Analysis Agent
- Visualization Agent
- ML Pipeline Agent
- Report Generator
- Dashboard Generation
- Multi-Database Support
- RAG Integration
- Memory-enabled Agents
- Docker Deployment

---

# 📷 Screenshots

Add screenshots here.

- Architecture Diagram
- LangGraph Workflow
- SQL Agent Output
- ETL Agent Output
- Streamlit UI

---

# 🤝 Contributing

Contributions are welcome.

Feel free to fork the repository, open issues, and submit pull requests.

---

# 📄 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

**Eman Gope**

Computer Science Undergraduate

Interested in

- AI Engineering
- Applied AI
- Machine Learning
- Agentic AI
- Generative AI
- Data Engineering
