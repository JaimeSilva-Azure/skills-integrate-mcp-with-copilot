"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import sqlite3
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = current_dir / "activities.db"

INITIAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS activities (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            schedule TEXT NOT NULL,
            max_participants INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS participants (
            activity_name TEXT NOT NULL,
            email TEXT NOT NULL,
            PRIMARY KEY (activity_name, email),
            FOREIGN KEY(activity_name) REFERENCES activities(name) ON DELETE CASCADE
        );
        """
    )


def seed_initial_data(conn):
    activity_count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    if activity_count > 0:
        return

    for name, activity in INITIAL_ACTIVITIES.items():
        conn.execute(
            "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
            (name, activity["description"], activity["schedule"], activity["max_participants"])
        )
        for email in activity["participants"]:
            conn.execute(
                "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
                (name, email)
            )
    conn.commit()


@app.on_event("startup")
def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        create_tables(conn)
        seed_initial_data(conn)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


def load_activity(activity_name: str):
    with get_db_connection() as conn:
        activity_row = conn.execute(
            "SELECT name, description, schedule, max_participants FROM activities WHERE name = ?",
            (activity_name,)
        ).fetchone()
        if activity_row is None:
            return None

        participants = [
            row["email"]
            for row in conn.execute(
                "SELECT email FROM participants WHERE activity_name = ? ORDER BY email",
                (activity_name,)
            ).fetchall()
        ]

        return {
            "name": activity_row["name"],
            "description": activity_row["description"],
            "schedule": activity_row["schedule"],
            "max_participants": activity_row["max_participants"],
            "participants": participants,
        }


def load_all_activities():
    with get_db_connection() as conn:
        activities = {}
        for activity_row in conn.execute(
            "SELECT name, description, schedule, max_participants FROM activities ORDER BY name"
        ).fetchall():
            participants = [
                row["email"]
                for row in conn.execute(
                    "SELECT email FROM participants WHERE activity_name = ? ORDER BY email",
                    (activity_row["name"],)
                ).fetchall()
            ]
            activities[activity_row["name"]] = {
                "description": activity_row["description"],
                "schedule": activity_row["schedule"],
                "max_participants": activity_row["max_participants"],
                "participants": participants,
            }
        return activities


@app.get("/activities")
def get_activities():
    return load_all_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    activity = load_activity(activity_name)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
            (activity_name, email)
        )
        conn.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    activity = load_activity(activity_name)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM participants WHERE activity_name = ? AND email = ?",
            (activity_name, email)
        )
        conn.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
