# Vehicle Service Booking System

A web-based vehicle service management application built using **Python, Flask, PostgreSQL, and SQLAlchemy**. The system allows customers to manage their vehicles, book vehicle servicing appointments, and track booking status. It also provides administrative controls and a Business Insights module for analysing service booking data.

## Features

### 1. User Management

* User registration and login.
* Authentication and session management.
* Role-based access for customers and administrators.
* Secure access to application features.

### 2. Vehicle Management

* Add vehicles to a personal account.
* View registered vehicles.
* Edit vehicle information.
* Delete vehicle records.

### 3. Service Booking

* Book vehicle servicing appointments.
* Select service types and appointment details.
* View personal booking history.
* Track booking statuses.

### 4. Admin Dashboard

* View registered users and vehicles.
* Monitor service bookings.
* Track total, pending, and completed bookings.
* Manage booking statuses, including confirmation, completion, and cancellation.

### 5. Business Insights

The Business Insights module provides an administrative overview of service booking activity using data retrieved from the database.

Features include:

* Booking status analysis.
* Popular service identification.
* Frequent customer analysis.
* Summary statistics and business recommendations.

### 6. Data Mining and Analytics

The project includes Python modules for analysing booking and customer data.

| Module                  | Description                                                                 |
| ----------------------- | --------------------------------------------------------------------------- |
| ETL Pipeline            | Extracts, cleans, transforms, and prepares application data for analysis.   |
| Data Warehouse          | Organises data into dimensions and a fact table for analytical queries.     |
| OLAP Analysis           | Supports roll-up, drill-down, slice, dice, and pivot operations.            |
| Association Rule Mining | Identifies frequently occurring service combinations and association rules. |
| Classification          | Experiments with machine learning models to classify booking outcomes.      |
| Clustering Analysis     | Groups customers based on selected behavioural characteristics.             |
| Outlier Detection       | Identifies unusual patterns in customer or booking activity.                |
| Customer Segmentation   | Groups customers using booking-related features.                            |

Generated analysis outputs are excluded from the Git repository to keep it focused on source code and documentation. Run the relevant scripts to generate outputs locally.

## Technology Stack

**Backend**

* Python
* Flask
* Flask-Login
* Flask-SQLAlchemy
* SQLAlchemy

**Database**

* PostgreSQL

**Frontend**

* HTML5
* CSS3
* Bootstrap 5
* JavaScript
* Chart.js, where used by the interface

**Data Analytics**

* Pandas
* NumPy
* Scikit-learn
* ML and data mining techniques

**Development Tools**

* Visual Studio Code
* Git
* GitHub
* pgAdmin

## Project Structure

```text
Vehicle-Service-Booking-System/
│
├── app.py
├── config.py
├── extensions.py
├── requirements.txt
├── README.md
├── DATABASE_DESIGN.md
│
├── models/
│   ├── user.py
│   ├── vehicle.py
│   └── booking.py
│
├── routes/
│   ├── auth.py
│   ├── booking.py
│   ├── dashboard.py
│   └── main.py
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── admin_dashboard.html
│   └── business_dashboard.html
│
├── static/
│   └── css/
│       └── styles.css
│
├── data_mining/
│   ├── __init__.py
│   ├── etl_pipeline.py
│   ├── warehouse.py
│   ├── olap_analysis.py
│   ├── association_mining.py
│   ├── classification.py
│   ├── clustering_analysis.py
│   ├── outlier_detection.py
│   └── business_dashboard.py
│
└── .gitignore
```

*The structure above illustrates the main components. The actual repository may contain additional files or folders.*

## Prerequisites

Before running the project, install:

* Python 3.10 or a compatible version supported by the dependencies.
* PostgreSQL.
* Git.
* A code editor such as Visual Studio Code.

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/fcbsoham/vehicle-service-booking-system.git
cd vehicle-service-booking-system
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, consult the Python documentation or use Command Prompt to activate the environment.

### 3. Install dependencies

If `requirements.txt` is present:

```bash
pip install -r requirements.txt
```

Otherwise, install the packages listed in the project's dependency configuration.

### 4. Create the PostgreSQL database

Open PostgreSQL or pgAdmin and create a database named:

```sql
CREATE DATABASE vehicle_service_booking;
```

If the database already exists, do not create it again.

### 5. Configure environment variables

Create a `.env` file in the project root and configure the database connection and Flask settings according to `config.py`.

For example:

```env
SECRET_KEY=replace-with-a-strong-random-secret
DATABASE_URL=postgresql://YOUR_DB_USER:YOUR_DB_PASSWORD@localhost:5432/vehicle_service_booking
```

Replace the example credentials with your local PostgreSQL username and password.

**Security:** Never commit `.env` or real credentials to GitHub.

### 6. Initialise the database

Follow the database initialisation procedure implemented by the application. If the project uses Flask-SQLAlchemy's `db.create_all()`, ensure that the models are imported before the database tables are created.

Do not run initialisation commands that delete or recreate existing tables unless you intend to reset the database.

### 7. Run the application

From the project root, run:

```bash
python app.py
```

Open the local address printed by Flask in your browser. If the application uses the default development configuration, this is usually:

```text
http://127.0.0.1:5000/
```

## Using the Application

1. Register a customer account or sign in with an existing account.
2. Add your vehicle details.
3. Book a vehicle service appointment.
4. Open your bookings page to review booking information and status.
5. Sign in with an authorised administrator account to access the Admin Dashboard.
6. Use Business Insights to review service trends and booking statistics.
7. Run the Data Mining modules separately when you need to perform additional analysis.

Administrator access should be granted only to authorised users.

## Running the Data Mining Modules

The scripts in `data_mining/` are intended for local analytical processing.

From the project root, run the relevant module using Python. For example:

```bash
python -m data_mining.etl_pipeline
```

Other available modules include:

```text
data_mining.warehouse
data_mining.olap_analysis
data_mining.association_mining
data_mining.classification
data_mining.clustering_analysis
data_mining.outlier_detection
```

The exact execution order, required inputs, and output locations depend on each script's implementation. Check the individual Python files before running them.

Some modules may depend on the PostgreSQL database or on files generated by earlier steps. Run prerequisite steps first.

Generated CSV files, model files, and analysis outputs are not intended to be committed to the repository.

## Database Design

The application uses PostgreSQL to store information related to users, vehicles, and service bookings.

The primary entities include:

* **Users:** Account and customer information.
* **Vehicles:** Vehicles registered by users.
* **Bookings:** Service appointments, service types, dates, and booking statuses.

The Data Mining modules use application data to prepare analytical datasets and perform additional analysis.

Refer to `DATABASE_DESIGN.md` for the detailed schema and relationships, if included in the repository.

## Security and Data Management

* Store credentials in environment variables rather than source code.
* Keep `.env` and virtual-environment directories out of Git.
* Restrict administrator functionality to authorised accounts.
* Avoid committing personal customer information or production database exports.
* Keep generated Data Mining outputs separate from the source-code repository.
* Use appropriate CSRF protection and secure deployment settings before deploying the application publicly.

## Future Enhancements

Potential improvements include:

* Email or SMS booking notifications.
* Online payment integration.
* Service reminders and maintenance history.
* Advanced demand forecasting.
* More detailed customer segmentation.
* Improved reporting and analytics.
* Deployment to a production hosting platform.

## Learning Outcomes

This project demonstrates practical implementation of:

* Full-stack web application development.
* REST-style routing and server-side request handling.
* Relational database design and SQL.
* Authentication and role-based access control.
* ETL and data warehousing.
* OLAP operations and association rule mining.
* Machine learning classification and clustering.
* Git-based source-code management.

## Author

**Soham Sawant**

GitHub: [@fcbsoham](https://github.com/fcbsoham)

## License

No license has been specified. Unless a license is added to the repository, reuse and redistribution are subject to the applicable copyright rules.
