# SmartRoster – Workforce Scheduling System

## Overview

SmartRoster is a full-stack web application designed to manage employee scheduling efficiently. It allows organizations such as shops, schools, or small companies to assign working hours based on employee preferences, contract types, and operational constraints.

The system ensures fair distribution of work hours while respecting individual availability and company policies.

---

## Tech Stack

* Backend: Django (Python)
* Frontend: AngularJS
* Database: SQLite (development)
* Authentication: Django Authentication System
* PDF Generation: ReportLab / WeasyPrint (development)

---

## Features

### Admin / Employee (Manager Role)

* Create, update, and delete workers
* Assign roles:

  * Full-Time (40 hrs/week)
  * Part-Time (20 hrs/week)
  * Mini Job (10 hrs/week)
* Set shop opening and closing hours
* Generate weekly timetable automatically
* Modify worker profiles and permissions
* Export timetable as PDF
* View digital timetable dashboard

---

### Worker (User Role)

* Login with assigned credentials
* Select available working days and times
* Submit weekly availability before deadline (e.g., Saturday)
* View assigned schedule
* Update personal profile (limited access)

---

## Authentication Flow

* Workers are created by the admin
* System auto-generates:

  * User ID
  * Default password
* Workers must log in and can later update their password

---

## Core Functionalities

### 1. Employee Management (CRUD)

* Add new workers
* Assign role & working hour limits
* Delete or update workers

### 2. Availability Submission

* Workers select:

  * Start date
  * Preferred working time slots

### 3. Smart Scheduling Algorithm

* Generates timetable based on:

  * Worker preferences
  * Weekly hour limits
  * Shop working hours
* Ensures fair distribution of shifts

### 4. Timetable Generation

* Weekly schedule auto-generated
* Export options:

  * PDF timetable
  * Web dashboard view

---

## Database Models (Simplified)

* User (Abstract Django User)
* WorkerProfile

  * Role (Full-time, Part-time, Mini job)
  * Weekly hour limit
* Availability

  * Date
  * Start time
  * End time
* Schedule

  * Assigned shifts
* OrganisationSettings

  * Opening time
  * Closing time

---

## System Workflow

1. Admin creates workers
2. Workers receive login credentials
3. Workers submit availability before deadline
4. System processes data
5. Timetable is generated automatically
6. Admin reviews & exports schedule

---

## Constraints & Rules

* Workers cannot modify schedules after submission
* Only admins can edit or delete users
* Weekly hour limits must be respected
* Scheduling must fit within business/organisation hours

---

## Installation (Basic)

* The project is at initial stage, so installation steps can be added soon. 

---

## Future Improvements

* AI-based scheduling optimization
* Mobile app version
* Notifications (email/SMS)
* Leave management system
* Multi-branch support

---

## Use Cases

* Retail shops
* Restaurants
* Schools
* Small businesses

---

## Author

Rakesh Adepu

---

## License

MIT License
