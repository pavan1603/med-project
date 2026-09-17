# MED Project

An AI-powered healthcare management and risk assessment system designed to support patients, doctors, receptionists, hospital administrators, and super administrators through a unified web application.

## Overview

MED Project combines healthcare management features with AI-based health risk prediction and an AI chatbot.

The system provides role-based access for different hospital users and includes machine-learning models for diabetes and heart-disease risk assessment.

## Features

### AI & Machine Learning
- Diabetes risk prediction
- Heart disease risk prediction
- AI healthcare chatbot
- Retrieval-Augmented Generation (RAG)
- Medical knowledge retrieval
- Health-related explanations and recommendations
- Safety-focused response handling

### Hospital Management
- Patient management
- Doctor management
- Hospital administration
- Receptionist dashboard
- Patient accounts
- Visit management
- Reports
- Analytics
- Audit records
- Role-based permissions

### User Interfaces
- Patient dashboard
- Doctor dashboard
- Receptionist dashboard
- Hospital dashboard
- Hospital administration
- Super administrator dashboard
- AI chatbot interface

## Tech Stack

### Backend
- Python
- Flask
- SQLite
- REST APIs

### AI / Machine Learning
- XGBoost
- Random Forest
- RAG
- Vector database
- Machine-learning classification models

### Frontend
- HTML
- CSS
- JavaScript

### Data
- Diabetes datasets
- Heart disease datasets
- Medical knowledge documents

## Project Structure

```text
MED PROJECT/
│
├── backend/
│   ├── database/
│   ├── knowledge/
│   ├── prompts/
│   ├── vectordb/
│   ├── app.py
│   ├── predict.py
│   ├── rag.py
│   ├── safety.py
│   └── ...
│
├── data/
│   ├── diabetes.csv
│   ├── diabetes_clean.csv
│   ├── heart_clean.csv
│   └── ...
│
├── models/
│   ├── diabetes_rf_model.pkl
│   ├── diabetes_xgb_final.pkl
│   ├── heart_xgb_model.pkl
│   └── ...
│
├── ui/
│   ├── css/
│   ├── js/
│   ├── index.html
│   ├── patient.html
│   ├── doctor.html
│   └── ...
│
├── .env.example
├── .gitignore
├── requirements.txt
├── RUN_LOCAL.md
└── run.bat
