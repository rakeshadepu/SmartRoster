# Contributing to SmartRoster

Thank you for your interest in contributing to **SmartRoster**! We appreciate all contributions, whether they involve fixing bugs, improving documentation, adding features, or enhancing the scheduling algorithm.

---

# Getting Started

## 1. Fork the Repository

Fork this repository to your own GitHub account.

## 2. Clone Your Fork

```bash
git clone https://github.com/<your-username>/SmartRoster.git
cd SmartRoster
```

## 3. Create a Virtual Environment

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

## 4. Install Backend Dependencies

The Django backend is located in the `backend` folder.

```bash
cd backend
pip install -r requirements.txt
```

## 5. Run Database Migrations

From the `backend` folder:

```bash
python manage.py migrate
```

## 6. Start the Backend Server

From the `backend` folder:

```bash
python manage.py runserver
```

The backend will run on:

```
http://127.0.0.1:8000/
```

## 7. Start the Frontend

Open a **new terminal**.

```bash
cd SmartRoster/frontend
http-server
```

The frontend will run on the URL displayed by `http-server` (commonly `http://127.0.0.1:8080`).

---

# Workflow

## Reporting an Issue

If you find a bug or would like to request a new feature:

1. Check whether an issue already exists.
2. If not, create a new GitHub Issue.
3. Clearly describe:

   * the problem
   * steps to reproduce it
   * expected behavior
   * screenshots (if applicable)

Comment on the issue if you would like to work on it.

---

## Creating a Branch

Create a branch from `main`.

Use one of these prefixes:

* `feature/`
* `fix/`
* `docs/`
* `chore/`
* `refactor/`

Example:

```bash
git checkout -b fix/login-validation
```

---

# Coding Guidelines

* Follow the existing project structure.
* Write clean and readable code.
* Keep functions small and focused.
* Comment complex logic where necessary.
* Test your changes before submitting.

---

# Commit Messages

Use meaningful commit messages.

Good examples:

```text
Fix worker login validation

Add PDF export feature

Update contributing guide
```

Avoid:

```text
Update

Fix

Changes
```

---

# Pushing Your Changes

```bash
git add .
git commit -m "Fix worker login validation"
git push -u origin fix/login-validation
```

---

# Creating a Pull Request

After pushing your branch:

1. Open your fork on GitHub.
2. Click **Compare & pull request**.
3. Select:

   * **Source:** your branch
   * **Target:** `main`
4. Add a clear title.
5. In the description, reference the related issue using:

```text
Closes #12
```

6. Submit the Pull Request.

After the Pull Request is reviewed and merged, GitHub will automatically close the linked issue if you used `Closes #<issue-number>` in the description.

---

# Reporting Bugs

Please include:

* Description
* Steps to reproduce
* Expected behavior
* Actual behavior
* Screenshots (if applicable)
* Operating System
* Python version
* Django version

---

# Suggesting Features

Feature requests are always welcome.

Please include:

* Problem statement
* Proposed solution
* Alternative solutions
* Additional context

---

# Questions

If you have questions, feel free to open a GitHub Issue.

---

## Maintainer

**Rakesh Adepu**

Thank you for contributing to **SmartRoster**!
