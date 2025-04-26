from fastapi import FastAPI, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import pandas as pd
import os
from datetime import datetime, timedelta
from fastapi.responses import Response
from generate_report import generate_ai_report  # Make sure this file exists

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key='secret-key')

# Paths
TEMPLATE_DIR = "templates"
EXCEL_FILE = os.path.join(os.getcwd(), "trip_data.xlsx")

# Mount static files and Jinja2 templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Create Excel if not exists
if not os.path.exists(EXCEL_FILE):
    df = pd.DataFrame(columns=[
        "Trip ID", 
        "Driver", 
        "Vehicle Number",
        "Start Location", 
        "End Location", 
        "Start Date",
        "End Date",
        "Distance (km)",
        "Fuel Usage (litres)", 
        "Status"
    ])
    df.to_excel(EXCEL_FILE, index=False)

# Helper function for Normalization of Status Column
def normalize_status_column(df):
    if "Status" in df.columns:
        df["Status"] = df["Status"].str.lower()
    return df

# Helper function to Read the Excel sheet
def read_excel_file():
    try:
        return pd.read_excel(EXCEL_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Trip ID", "Driver", "Start Location", "End Location", "Start Date", "Fuel Usage (litres)", "Status"])
    
# Helper function to Write to the Excel sheet
def write_excel_file(df):
    try:
        df.to_excel(EXCEL_FILE, index=False)
    except Exception as e:
        print(f"Error writing to Excel file: {e}")

# Helper function to filter data based on a time period
def filter_data_by_period(df, period):
    today = datetime.now()
    if period == "daily":
        return df[df["Start Date"].dt.date == today.date()]
    elif period == "weekly":
        return df[df["Start Date"] >= (today - timedelta(days=7))]
    elif period == "monthly":
        return df[df["Start Date"] >= (today - timedelta(days=30))]
    return df

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Redirect to the Fleet Owner Dashboard
    return RedirectResponse("/fleet-dashboard")


@app.get("/trip-stats")
def get_trip_stats():
    # Read data from the Excel file
    df = read_excel_file()

    # Normalize the 'Status' column to lowercase for case-insensitive filtering
    df = normalize_status_column(df)

    # Ensure the 'Start Date' column is in datetime format
    if "Start Date" in df.columns:
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce")
        df = df[df["Start Date"].notna()]  # Filter out rows with invalid or missing dates

    # Get today's date
    today = datetime.now()

    # Filter data for daily, weekly, and monthly periods
    daily   = filter_data_by_period(df, "daily")
    weekly  = filter_data_by_period(df, "weekly")
    monthly = filter_data_by_period(df, "monthly")

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
    df = read_excel_file()

    # Normalize the 'Status' column to lowercase for case-insensitive filtering
    df = normalize_status_column(df)
    
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
    trip_id: str = Form(...),
    driver: str = Form(...),
    vehicle_number: str = Form(...),  # New Field
    start_location: str = Form(...),
    end_location: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(None),  # New Field
    distance: float = Form(None),  # New Field
    fuel_usage: float = Form(...),
    status: str = Form(...)
):
    df = read_excel_file()
    new_row = {
        "Trip ID": trip_id,
        "Driver": driver,
        "Vehicle Number": vehicle_number,  # New Field
        "Start Location": start_location,
        "End Location": end_location,
        "Start Date": start_date,
        "End Date": end_date,  # New Field
        "Distance (km)": distance,  # New Field
        "Fuel Usage (litres)": fuel_usage,
        "Status": status
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    write_excel_file(df)
    return RedirectResponse("/", status_code=303)

@app.get("/edit/{trip_id}")
def edit_trip_page(request: Request, trip_id: str):
    df = read_excel_file()

    # Filter the DataFrame for the given trip_id
    filtered_trips = df[df["Trip ID"] == trip_id].to_dict(orient="records")

    # Check if the trip exists
    if not filtered_trips:
        return Response(
            content=f"Trip ID {trip_id} not found.",
            status_code=404,
            media_type="text/plain"
        )

    trip = filtered_trips[0]
    return templates.TemplateResponse("trip_edit.html", {"request": request, "trip": trip})

@app.post("/edit/{trip_id}")
def edit_trip(
    trip_id: str,
    driver: str = Form(...),
    vehicle_number: str = Form(...),  # New Field
    start_location: str = Form(...),
    end_location: str = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(None),  # New Field
    distance: float = Form(None),  # New Field
    fuel_usage: float = Form(...),
    status: str = Form(...)
):
    df = read_excel_file()
    index = df[df["Trip ID"] == trip_id].index[0]
    df.loc[index] = [
        trip_id, driver, vehicle_number, start_location, end_location, start_date, end_date, distance, fuel_usage, status
    ]
    write_excel_file(df)
    return RedirectResponse("/", status_code=303)

@app.get("/delete/{trip_id}")
def delete_trip(request: Request, trip_id: str):
    df = read_excel_file()
    df = df[df["Trip ID"] != trip_id]
    write_excel_file(df)
    return RedirectResponse("/", status_code=303)

@app.post("/generate-report")
def generate_report():
    df = read_excel_file()

    # Generate mock insights
    insights = []
    for _, row in df.iterrows():
        insights.append(
            f"Trip ID {row['Trip ID']} by {row['Driver']} (Vehicle: {row['Vehicle Number']}) "
            f"from {row['Start Location']} to {row['End Location']} covered {row['Distance (km)']} km, "
            f"used {row['Fuel Usage (litres)']}L fuel, and is currently {row['Status']}."
        )

    # Generate PDF report
    file_path = generate_ai_report(insights)

    # Read and return the file as downloadable PDF
    with open(file_path, "rb") as f:
        pdf_data = f.read()

    os.remove(file_path)  # Optional: Delete after sending

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=AI_Insights_Report.pdf"}
    )

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/fleet-dashboard", response_class=HTMLResponse)
async def fleet_dashboard(request: Request):
    df = read_excel_file()

    # Normalize the 'Status' column to lowercase for case-insensitive filtering
    df = normalize_status_column(df)

    # Remove duplicate rows based on the "Trip ID" column
    df = df.drop_duplicates(subset=["Trip ID"], keep="last")

    # Calculate dynamic values
    total_trips = len(df)
    ongoing_trips = len(df[(df["Status"] == "in transit") | (df["Status"] == "delayed")])
    closed_trips = len(df[df["Status"] == "completed"])
    total_flags = len(df[df["Status"] == "delayed"])
    trip_id = df["Trip ID"].iloc[-1] if not df.empty else "N/A"
    resolved_flags = len(df[df["Status"] == "resolved"])
    total_revenue = df["Distance (km)"].sum() * 10  # Example: Revenue per km = 10
    total_expense = df["Fuel Usage (litres)"].sum() * 5  # Example: Expense per litre = 5
    net_profit = total_revenue - total_expense
    total_kms_travelled = df["Distance (km)"].sum()
    per_km_cost = total_expense / total_kms_travelled if total_kms_travelled > 0 else 0

    # Pass data to the template
    return templates.TemplateResponse("fleet_owner_dashboard.html", {
        "request": request,
        "total_trips": total_trips,
        "ongoing_trips": ongoing_trips,
        "closed_trips": closed_trips,
        "total_flags": total_flags,
        "trip_id": trip_id,
        "resolved_flags": resolved_flags,
        "total_revenue": total_revenue,
        "total_expense": total_expense,
        "net_profit": net_profit,
        "total_kms_travelled": total_kms_travelled,
        "per_km_cost": per_km_cost,
        "ai_reports": ["Report 1", "Report 2", "Report 3"],  # Example AI reports
    })

@app.get("/trip-auditor-dashboard", response_class=HTMLResponse)
async def trip_auditor_dashboard(request: Request):
    return templates.TemplateResponse("trip_auditor_dashboard.html", {"request": request})

@app.get("/trip-auditor", response_class=HTMLResponse)
async def trip_auditor(request: Request):
    # Read data from the Excel file
    df = read_excel_file()

    # Remove duplicate rows based on the "Trip ID" column
    df = df.drop_duplicates(subset=["Trip ID"], keep="last")

    # Normalize the 'Status' column to lowercase for case-insensitive filtering
    df = normalize_status_column(df)

    # Format Start Date and End Date to include only the date
    if "Start Date" in df.columns:
        df["Start Date"] = pd.to_datetime(df["Start Date"], errors="coerce").dt.strftime('%Y-%m-%d')
    if "End Date" in df.columns:
        df["End Date"] = pd.to_datetime(df["End Date"], errors="coerce").dt.strftime('%Y-%m-%d')

    # Reassign Trip IDs to maintain sequential order
    df = df.sort_values(by="Trip ID").reset_index(drop=True)
    df["Trip ID"] = range(1, len(df) + 1)

    # Convert the DataFrame to a list of dictionaries
    trips = df.to_dict(orient="records")

    # Calculate stats
    stats = {
        "total_trips": len(trips),
        "opened": len(df[df["Status"] == "in transit"]),  # Count trips with "in transit" status
        "closed": len(df[df["Status"] == "completed"]),  # Count trips with "completed" status
        "delayed": len(df[df["Status"] == "delayed"])    # Count trips with "delayed" status
    }

    # Pass data to the template
    return templates.TemplateResponse("trip_auditor.html", {"request": request, "trips": trips, "stats": stats})

@app.post("/update-trips")
async def update_trips(request: Request):
    try:
        # Read the updated data from the request
        updated_data = await request.json()

        # Load the Excel file
        df = read_excel_file()

        for row in updated_data:
            if "action" in row and row["action"] == "delete":
                # Delete the trip if the action is "delete"
                trip_id_to_delete = row["Trip ID"]
                if trip_id_to_delete in df["Trip ID"].astype(str).values:
                    df = df[df["Trip ID"].astype(str) != trip_id_to_delete]
                    # Reassign Trip IDs to maintain sequential order
                    df = df.sort_values(by="Trip ID").reset_index(drop=True)
                    df["Trip ID"] = range(1, len(df) + 1)  # Reassign Trip IDs sequentially
                else:
                    return {"success": False, "error": f"Trip ID {trip_id_to_delete} not found."}
            else:
                # Handle update or add logic
                trip_id = row["Trip ID"]

                # Check if the Trip ID already exists
                if trip_id in df["Trip ID"].values:
                    # Update the existing trip
                    for column, value in row.items():
                        if column in df.columns and column != "Trip ID":
                            # Cast the value to the column's data type
                            if pd.api.types.is_numeric_dtype(df[column]):
                                value = pd.to_numeric(value, errors="coerce")
                            elif pd.api.types.is_datetime64_any_dtype(df[column]):
                                value = pd.to_datetime(value, errors="coerce")
                            df.loc[df["Trip ID"] == trip_id, column] = value
                else:
                    # Add a new trip if the Trip ID does not exist
                    new_row = {col: row.get(col, None) for col in df.columns}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Save the updated Excel file
        write_excel_file(df)

        # Return the updated trip list to the frontend
        return {"success": True, "updated_trips": df.to_dict(orient="records")}
    except Exception as e:
        print(f"Error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    request.session["user"] = email
    return RedirectResponse("/", status_code=303)

@app.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
def signup(request: Request, email: str = Form(...), password: str = Form(...)):
    request.session["user"] = email
    return RedirectResponse("/", status_code=303)

@app.get("/trip-edit", response_class=HTMLResponse)
async def trip_edit(request: Request):
    return templates.TemplateResponse("trip_edit.html", {"request": request})

@app.get("/user-settings", response_class=HTMLResponse)
async def user_settings(request: Request):
    return templates.TemplateResponse("user_settings.html", {"request": request})

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
