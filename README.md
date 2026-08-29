# 🏛️ Smart Inspection & Monitoring System

A web-based **Smart Inspection & Monitoring System** developed using **Python Flask and SQLite**. The system helps organizations conduct inspections, report issues, prioritize them, monitor their status, and manage users through role-based access.

## ✨ Features

- 🔐 Secure login using Unique ID and Password
- 👥 Role-Based Access Control
- 📋 Digital Inspection Form
- 👷 Workers and Inspectors can conduct inspections
- 🚫 Workers cannot access the monitoring dashboard
- 👨‍💼 Authority can manage users and issues
- 📊 Live Monitoring Dashboard for authorized users
- ⚠️ Issue reporting and tracking
- 🔴🟡🟢 Issue status management
- 🚨 Priority-based issue management
- 🔑 Forgot Password / Password Reset feature
- 🆔 Automatically generated Unique IDs for users

## 👥 User Roles

### 👨‍💼 Authority
- Manage system users
- Create Worker, Inspector, Officer, and Authority accounts
- Monitor all reported issues
- Update issue status
- Manage priorities

### 🔍 Inspector
- Conduct inspections
- Report issues
- View the dashboard (if enabled in the system)

### 👷 Worker
- Conduct inspections
- Submit inspection reports
- Cannot access the dashboard or administrative features

### 👨‍💻 Officer
- Access features based on permissions assigned by the system

## ⚙️ Technology Stack

- **Frontend:** HTML & CSS
- **Backend:** Python
- **Framework:** Flask
- **Database:** SQLite
- **Deployment:** Render

## 📂 Project Structure

```text
inspection_app-sih-
│
├── app.py
├── requirements.txt
└── README.md
