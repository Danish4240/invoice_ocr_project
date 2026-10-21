import cv2
import easyocr
import numpy as np
import pandas as pd
import re
import streamlit as st
from PIL import Image
import os

# 1. Page Configuration
st.set_page_config(page_title="Invoice OCR to Excel", layout="wide")

st.title("📄 Invoice/Bill OCR to Auto-Excel Entry")
st.write("Upload an invoice image to automatically extract key details and save them to an Excel sheet.")

# 2. Initialize EasyOCR Reader (Cached for performance)
@st.cache_resource
def load_ocr_model():
    return easyocr.Reader(['en'], gpu=False)

with st.spinner("Loading OCR Model... Please wait."):
    reader = load_ocr_model()

# 3. OpenCV Preprocessing Function
def preprocess_image(image):
    img_cv = np.array(image)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    filtered = cv2.bilateralFilter(gray, 11, 17, 17)
    return filtered

# 4. Information Extraction using Regex
def extract_invoice_data(text_list):
    full_text = " ".join(text_list)
    
    data = {
        "Invoice Number": "N/A",
        "Date": "N/A",
        "Total Amount": "N/A"
    }
    
    # Regex patterns to parse common invoice fields
    inv_match = re.search(r'(?:invoice\s*no|inv\s*#|bill\s*no)[:#]?\s*([A-Za-z0-9\-_]+)', full_text, re.IGNORECASE)
    if inv_match:
        data["Invoice Number"] = inv_match.group(1)
        
    date_match = re.search(r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|(?:\d{4}[-/]\d{1,2}[-/]\d{1,2})\b', full_text)
    if date_match:
        data["Date"] = date_match.group(0)
        
    amount_match = re.search(r'(?:total|amount\s*due|balance|grand\s*total)[:\s]*[\$]?\s*([0-9]+\.[0-9]{2})', full_text, re.IGNORECASE)
    if amount_match:
        data["Total Amount"] = amount_match.group(1)
    else:
        amounts = re.findall(r'\b\d+\.\d{2}\b', full_text)
        if amounts:
            data["Total Amount"] = max(amounts, key=lambda x: float(x))
            
    return data

# 5. Streamlit File Uploader Interface
uploaded_file = st.file_uploader("Upload Invoice Image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    col1, col2 = st.columns(2)
    
    image = Image.open(uploaded_file)
    with col1:
        st.subheader("Uploaded Invoice")
        st.image(image, use_container_width=True)
        
    with col2:
        st.subheader("Extraction Results")
        
        with st.spinner("Processing image and running OCR..."):
            processed_img = preprocess_image(image)
            ocr_results = reader.readtext(processed_img, detail=0)
            extracted_info = extract_invoice_data(ocr_results)
            
            with st.expander("View Raw OCR Text"):
                st.write(ocr_results)
                
            st.json(extracted_info)
            
            excel_file = "extracted_invoices.xlsx"
            df_new = pd.DataFrame([extracted_info])
            
            if st.button("Save to Excel Database"):
                if os.path.exists(excel_file):
                    df_existing = pd.read_excel(excel_file)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                else:
                    df_combined = df_new
                    
                df_combined.to_excel(excel_file, index=False)
                st.success(f"Successfully saved data to `{excel_file}`!")

    if os.path.exists("extracted_invoices.xlsx"):
        with open("extracted_invoices.xlsx", "rb") as f:
            st.download_button(
                label="Download Complete Excel Database",
                data=f,
                file_name="invoice_database.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )