from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import pandas as pd
import re
import io

app = FastAPI()

name_mapping = {
    'Sarbin Towers': 'Sarbin',
    'Richman Towers': 'Richman',
    'Park Marconi': 'Marconi',
    'Jubilee Maycroft Apartments LP': 'Maycroft',
    'Jubilee Ontario Apartments LP': 'Ontario',
    'The Fuller': 'Fuller',
    'Ritz Apartments': 'Ritz'
}

def clean_excel_file(file_bytes: bytes) -> list:
    df = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd')

    # Extract property name
    cell_value = str(df.iloc[0, 3])
    prop_name = "unknown"
    if "Jubilee Housing, Inc. - " in cell_value:
        prop_name = cell_value.split("Jubilee Housing, Inc. - ")[1].strip()
    prop_name = name_mapping.get(prop_name, prop_name)

    # Clean the dataframe
    df.drop(df.index[:8], inplace=True)
    df.dropna(subset=[df.columns[0]], inplace=True)
    df.reset_index(drop=True, inplace=True)
    df["Property"] = prop_name

    # Rename and keep columns
    df = df.rename(columns={
        "Unnamed: 0": "Unit", 
        "Unnamed: 2": "Name", 
        "Unnamed: 4": "DOB", 
        "Unnamed: 5": "Gender", 
        "Unnamed: 6": "Marital Status", 
        "Unnamed: 7": "Ethnic Origin", 
        "Unnamed: 9": "Household Status"
    })

    columns_to_keep = [
        'Unit', 'Name', 'DOB', 'Gender', 
        'Marital Status', 'Household Status', 'Property'
    ]
    df = df[columns_to_keep]

    # Clean cells
    def clean_cells(cell):
        if isinstance(cell, str):
            cell = re.sub(r'\\.*', '', cell).strip()
            cell = re.sub(r'\n.*', '', cell).strip()
        return cell

    df = df.map(clean_cells)

    # Drop duplicates and parse dates
    df = df.drop_duplicates()
    df["DOB"] = pd.to_datetime(df["DOB"], errors="coerce")

    # Add Age
    df["Age"] = (pd.to_datetime("today") - df["DOB"]).dt.days // 365
    df["Unit"] = df["Property"] + " " + df["Unit"].astype(str)

    # Age groups
    detailed_bins = [0, 17, 24, 54, 64, float('inf')]
    detailed_labels = ['0-17', '18-24', '25-54', '55-64', '65+']
    df['Age Group Detailed'] = pd.cut(df['Age'], bins=detailed_bins, labels=detailed_labels, right=False)

    general_bins = [0, 17, 64, float('inf')]
    general_labels = ['0-17', '18-64', '65+']
    df['Age Group General'] = pd.cut(df['Age'], bins=general_bins, labels=general_labels, right=False)

    df_columns = df.columns

    for col in df.columns:
        if not pd.api.types.is_categorical_dtype(df[col]):
            df[col] = df[col].fillna("")

    return df.to_dict(orient="records"), list(df_columns)

@app.post("/onesite-upload/")
async def upload_clean_xls(file: UploadFile = File(...)):
    if not file.filename.endswith(".xls"):
        return JSONResponse(content={"error": "Only .xls files are supported"}, status_code=400)
    
    file_bytes = await file.read()
    try:
        clean_data, df_columns = clean_excel_file(file_bytes)
    except Exception as e:
        return JSONResponse(content={"error": f"Processing failed: {str(e)}"}, status_code=500)

    return {"data": clean_data, "onesite_columns":df_columns}

@app.post("/apricot-upload/")
async def upload_xlsx(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        return JSONResponse(content={"error": "Only .xlsx files are allowed"}, status_code=400)

    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    df = df.fillna("")  
    df_columns = list(df.columns)

    return {"data": df.to_dict(orient="records"), "apricot_columns":df_columns}