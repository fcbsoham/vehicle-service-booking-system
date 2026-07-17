# Vehicle Service Booking System - Database Design

## Users

| Column | Type | Constraints |
|---------|------|-------------|
| user_id | SERIAL | Primary Key |
| name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(100) | UNIQUE |
| password | VARCHAR(255) | NOT NULL |
| phone | VARCHAR(15) | NOT NULL |
| role | VARCHAR(20) | DEFAULT 'customer' |

---

## Vehicles

| Column | Type | Constraints |
|---------|------|-------------|
| vehicle_id | SERIAL | Primary Key |
| user_id | INT | Foreign Key |
| brand | VARCHAR(50) | NOT NULL |
| model | VARCHAR(50) | NOT NULL |
| year | INT | NOT NULL |
| registration_number | VARCHAR(20) | UNIQUE |

---

## Service Centers

| Column | Type | Constraints |
|---------|------|-------------|
| center_id | SERIAL | Primary Key |
| center_name | VARCHAR(100) | NOT NULL |
| address | TEXT | NOT NULL |
| city | VARCHAR(50) | NOT NULL |
| phone | VARCHAR(15) | NOT NULL |

---

## Bookings

| Column | Type | Constraints |
|---------|------|-------------|
| booking_id | SERIAL | Primary Key |
| user_id | INT | Foreign Key |
| vehicle_id | INT | Foreign Key |
| center_id | INT | Foreign Key |
| service_type | VARCHAR(100) | NOT NULL |
| booking_date | DATE | NOT NULL |
| booking_time | TIME | NOT NULL |
| status | VARCHAR(20) | DEFAULT 'Pending' |
