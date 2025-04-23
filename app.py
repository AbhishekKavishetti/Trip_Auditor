from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import os
from datetime import datetime, timedelta
# from generate_report import generate_ai_report

app = FastAPI()

# Paths
TEMPLATE_DIR = "templates"
EXCEL_FILE = os.path.join(os.getcwd(), "trip_data.xlsx")

# Mount static files and Jinja2 templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Create Excel if not exists
if not os.path.exists(EXCEL_FILE):
    df = pd.DataFrame(columns=["Trip ID", "Driver", "Start Location", "End Location", "Start Date", "Fuel Usage (litres)", "Status"])
    df.to_excel(EXCEL_FILE, index=False)

@app.get("/")
def dashboard(request: Request):
    # Read data from the Excel file
    df = pd.read_excel(EXCEL_FILE)

    # Normalize the 'Status' column to lowercase for case-insensitive filtering
    if "Status" in df.columns:
        df["Status"] = df["Status"].str.lower()
    
    trips = df.to_dict(orient="records")
    
    # Calculate stats
    stats = {
        "total_trips": len(trips),
        "opened": len(df[df["Status"] == "in transit"]),  # Count trips with "In Transit" status
        "closed": len(df[df["Status"] == "completed"]),
        "flags": len(df[df["Status"] == "flagged"])
    }
    return templates.TemplateResponse("HTML TRIP AUDITOR DASHBOARD.html", {"request": request, "trips": trips, "stats": stats})

@app.get("/trip-stats")
def get_trip_stats():
    # Read data from the Excel file
    df = pd.read_excel(EXCEL_FILE)

    # Normalize the 'Status' column
    if "Status" in df.columns:
        df["Status"] = df["Status"].str.lower()

    # Ensure the 'Start Date' column is in datetime format
    if "Start Date" in df.columns:
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce")

    # Get today's date
    today = datetime.now()

    # Filter data for daily, weekly, and monthly periods
    daily = df[df["Start Date"].dt.date == today.date()]  # Compare as date
    weekly = df[df["Start Date"] >= (today - timedelta(days=7))]  # Compare as datetime
    monthly = df[(df["Start Date"] >= (today - timedelta(days=30))) | (df["Status"] == "delayed")]  # Include all delayed trips

    # Calculate stats
    def calculate_stats(data):
        return {
            "completed": len(data[data["Status"] == "completed"]),
            "in_transit": len(data[data["Status"] == "in transit"]),
            "delayed": len(data[data["Status"] == "delayed"]),
        }

    stats = {
        "daily": calculate_stats(daily),
        "weekly": calculate_stats(weekly),
        "monthly": calculate_stats(monthly),
    }

    # Debug: Print stats to verify correctness
    print("Stats:", stats)

    return stats

@app.get("/add")
def add_trip_page(request: Request):
    # Read data from the Excel file
    df = pd.read_excel(EXCEL_FILE)

    # Normalize the 'Status' column to lowercase for case-insensitive filtering
    if "Status" in df.columns:
       df["Status"] = df["Status"].str.lower()
    
    # Calculate stats
    total_trips = len(df)
    flags = len(df[df["Status"] == "Flagged"]) if "Status" in df.columns else 0
    notifications = len(df[df["Status"] == "Pending"]) if "Status" in df.columns else 0

    # Pass stats to the template
    stats = {
        "total_trips": total_trips,
        "flags": flags,
        "notifications": notifications
    }
    return templates.TemplateResponse("trip_generator.html", {"request": request, "stats": stats})

@app.post("/add")
def add_trip(
    request: Request,
    trip_id: str = Form(...),
    driver: str = Form(...),
    start_location: str = Form(...),
    end_location: str = Form(...),
    start_date: str = Form(...),
    fuel_usage: float = Form(...),
    status: str = Form(...)
):
    df = pd.read_excel(EXCEL_FILE)
    new_row = {
        "Trip ID": trip_id,
        "Driver": driver,
        "Start Location": start_location,
        "End Location": end_location,
        "Start Date": start_date,
        "Fuel Usage (litres)": fuel_usage,
        "Status": status
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)
    return RedirectResponse("/", status_code=303)

@app.get("/edit/{trip_id}")
def edit_trip_page(request: Request, trip_id: str):
    df = pd.read_excel(EXCEL_FILE)
    trip = df[df["Trip ID"] == trip_id].to_dict(orient="records")[0]
    return templates.TemplateResponse("Trip_Auditor_Page.html", {"request": request, "trip": trip})

@app.post("/edit/{trip_id}")
def edit_trip(
    request: Request,
    trip_id: str,
    driver: str = Form(...),
    start_location: str = Form(...),
    end_location: str = Form(...),
    start_date: str = Form(...),
    fuel_usage: float = Form(...),
    status: str = Form(...)
):
    df = pd.read_excel(EXCEL_FILE)
    index = df[df["Trip ID"] == trip_id].index[0]
    df.loc[index] = [trip_id, driver, start_location, end_location, start_date, fuel_usage, status]
    df.to_excel(EXCEL_FILE, index=False)
    return RedirectResponse("/", status_code=303)

@app.get("/delete/{trip_id}")
def delete_trip(request: Request, trip_id: str):
    df = pd.read_excel(EXCEL_FILE)
    df = df[df["Trip ID"] != trip_id]
    df.to_excel(EXCEL_FILE, index=False)
    return RedirectResponse("/", status_code=303)

# @app.post("/generate-report")
# def generate_report():
#     generate_ai_report(EXCEL_FILE)
#     return RedirectResponse("/", status_code=303)
