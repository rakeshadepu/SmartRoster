# SmartRoster – Workforce Scheduling System

SmartRoster is a full-stack workforce scheduling application that helps organizations efficiently manage employee shifts. It enables managers to create schedules based on employee availability, contract types, and business operating hours while ensuring a fair distribution of working hours.

---

# Features

## Admin (Manager)

* Create, update, and delete workers
* Assign employment types:

  * Full-Time (40 hrs/week)
  * Part-Time (20 hrs/week)
  * Mini Job (10 hrs/week)
* Configure organization opening and closing hours
* Automatically generate weekly schedules
* Manage worker accounts and permissions
* View schedules through a web dashboard
* Export schedules as PDF

## Worker

* Log in using assigned credentials
* Submit weekly availability
* View assigned schedules
* Update personal profile information
* Change password

---

# Tech Stack

| Component      | Technology             |
| -------------- | ---------------------- |
| Backend        | Django (Python)        |
| Frontend       | AngularJS              |
| Database       | SQLite                 |
| Authentication | Django Authentication  |
| PDF Generation | ReportLab / WeasyPrint |

---

# Database Models

* User (Abstract Django User)
* WorkerProfile

  * Employment Type
  * Weekly Hour Limit
* Availability

  * Date
  * Start Time
  * End Time
* Schedule
* OrganisationSettings

---

# Project Structure

```text
SmartRoster/
│
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── index.html
│   ├── app/
│   └── ...
│
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/SmartRoster.git
cd SmartRoster
```

## 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it.

**Windows**

```bash
venv\Scripts\activate
```

**Linux/macOS**

```bash
source venv/bin/activate
```

---

## 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

## 4. Run Database Migrations

```bash
python manage.py migrate
```

---

## 5. Start the Django Backend

```bash
python manage.py runserver
```

The backend runs at:

```text
http://127.0.0.1:8000/
```

---

## 6. Start the AngularJS Frontend

Open a new terminal.

```bash
cd frontend
http-server
```

The frontend will run on the URL displayed by `http-server` (commonly `http://127.0.0.1:8080`).

---

# System Workflow

1. Admin creates worker accounts.
2. Workers receive login credentials.
3. Workers submit weekly availability.
4. The scheduling algorithm processes availability.
5. Weekly schedules are generated automatically.
6. Managers review and export schedules.

---

# Scheduling Rules

* Workers cannot modify availability after the submission deadline.
* Only administrators can manage users.
* Weekly hour limits are enforced.
* Shifts must fall within organization operating hours.
* The scheduling algorithm aims to distribute work fairly among employees.

---

# Future Improvements

* AI-powered scheduling optimization
* Leave management
* Email notifications
* SMS notifications
* Mobile application
* Multi-branch organization support
* Calendar synchronization
* Shift swapping between employees

---

# Use Cases

SmartRoster can be used by:

* Retail stores
* Restaurants
* Schools
* Hospitals
* Small businesses
* Warehouses
* Offices

---

# Contributing

Contributions are welcome!

If you would like to contribute:

1. Fork the repository.
2. Create a feature or fix branch.
3. Commit your changes.
4. Submit a Pull Request.

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file before contributing.

---

# Reporting Issues

Found a bug or have a feature request?

Please open a GitHub Issue describing:

* The problem
* Steps to reproduce
* Expected behavior
* Screenshots (if applicable)

---

# Roadmap

* User authentication improvements
* Automatic conflict detection
* AI-assisted scheduling
* Multi-language support
* Employee leave management
* Dashboard analytics

---

# Author

**Rakesh Adepu**

---

# License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for details.
