# MediRisk Local Setup

This package contains the files needed to run MediRisk locally.

## What is included

- `backend/` - Flask API, RAG chatbot, prediction logic, database modules, knowledge base, prompts, and ChromaDB vector store.
- `models/` - trained diabetes and heart disease ML models.
- `ui/` - local HTML/CSS/JS frontend pages.
- `data/` - cleaned/reference datasets used during development.
- `backend/medirisk.db` - demo SQLite database with sample hospital users and data.

## What is not included

- `.env`
- `google-translate-key.json`
- `venv/`
- notebook/report/documentation folders
- Python cache files

Private API keys must be created again on the new laptop.

## Setup

Open PowerShell inside the unzipped `MediRisk` folder and run:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` file by copying `.env.example`, then add your OpenRouter key:

```env
OPENROUTER_API_KEY=your_real_key_here
```

Google Translate is optional. If you want Telugu/Hindi translation through Google Cloud, place your own JSON key file on the laptop and set:

```env
GOOGLE_APPLICATION_CREDENTIALS=D:\path\to\google-translate-key.json
```

## Run

Start the backend:

```powershell
python backend\app.py
```

Then open the UI in a browser:

```text
ui\hospital-login.html
```

The backend runs at:

```text
http://127.0.0.1:5000
```

## Demo logins

Use the demo buttons on the login page, or try these accounts if they exist in the included demo database:

- `xyz_admin`
- `xyz_reception`
- `xyz_doctor`

Patient accounts are generated when a patient is registered. Hospital admin and super admin can view patient login details from the patient credential section.

## Notes

- Do not share your real `.env` or Google Cloud JSON key.
- The first RAG/chatbot run may take time because the sentence-transformer embedding model may download from Hugging Face if it is not already cached.
- SQLite is fine for this local demo. For multi-user hospital deployment, PostgreSQL is recommended.
