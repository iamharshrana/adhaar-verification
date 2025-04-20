import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import re
from datetime import datetime
from pdf2image import convert_from_bytes
from pyzbar.pyzbar import decode as pyzbar_decode
from pyaadhaar.decode import AadhaarSecureQr

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy.
    """
    image = image.convert("L")
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)
    image = image.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.2)
    return image

def extract_text_from_file(file_bytes: bytes, content_type: str) -> str:
    """
    Extract text from an image or PDF using OCR (pytesseract).
    """
    text = ""
    if content_type == "application/pdf":
        images = convert_from_bytes(file_bytes)
        for img in images:
            img = preprocess_image(img)
            text += pytesseract.image_to_string(img)
    elif content_type.startswith("image/"):
        image = Image.open(io.BytesIO(file_bytes))
        image = preprocess_image(image)
        text = pytesseract.image_to_string(image)
    else:
        raise ValueError("Unsupported file type")
    return text

def extract_qr_code(image: Image.Image) -> str:
    """
    Extract QR code data from an image using pyzbar.
    """
    try:
        print("Attempting QR code extraction...")
        qr_image = preprocess_image(image)
        qr_codes = pyzbar_decode(qr_image)
        if qr_codes:
            qr_data = qr_codes[0].data.decode('utf-8')
            print("QR Code Raw Data:", qr_data)
            return qr_data
        else:
            print("No QR code detected in image.")
            return None
    except Exception as e:
        print("QR Code Extraction Error:", str(e))
        return None

def verify_aadhaar(file_bytes: bytes, content_type: str):
    """
    Verify Aadhaar details by decoding QR code or using OCR.
    """
    aadhaar_data = {
        "aadhaar_number": None,
        "dob": None,
        "name": None,
        "is_18_or_older": False,
        "valid": False,
        "error": None
    }

    try:
        qr_data = None
        qr_code_string = None

        if content_type == "application/pdf":
            images = convert_from_bytes(file_bytes)
            for img in images:
                qr_code_string = extract_qr_code(img)
                if qr_code_string:
                    break
        elif content_type.startswith("image/"):
            image = Image.open(io.BytesIO(file_bytes))
            qr_code_string = extract_qr_code(image)
        else:
            raise ValueError("Unsupported file type")

        if qr_code_string:
            try:
                qr_decoder = AadhaarSecureQr(base10encodedstring=qr_code_string)
                qr_data = qr_decoder.decoded_dict()
                print("Decoded QR Data:", qr_data)
            except Exception as e:
                print("QR Decoding Error:", str(e))
                qr_data = None

            if qr_data:
                aadhaar_number = qr_data.get("aadhaar_number")
                dob = qr_data.get("dob")
                name = qr_data.get("name")

                if aadhaar_number and re.match(r'^\d{12}$', aadhaar_number):
                    aadhaar_data["aadhaar_number"] = aadhaar_number
                    aadhaar_data["valid"] = True

                if dob:
                    try:
                        dob_date = datetime.strptime(dob, "%d-%m-%Y")
                        aadhaar_data["dob"] = dob
                        age = (datetime.now() - dob_date).days // 365
                        aadhaar_data["is_18_or_older"] = age >= 18
                    except ValueError:
                        aadhaar_data["dob"] = None
                        aadhaar_data["is_18_or_older"] = False

                aadhaar_data["name"] = name

                if aadhaar_data["valid"] and aadhaar_data["dob"] and aadhaar_data["name"]:
                    aadhaar_data["aadhaar_number"] = f"XXXX XXXX {aadhaar_data['aadhaar_number'][-4:]}"
                    return aadhaar_data

        # Fallback to OCR
        text = extract_text_from_file(file_bytes, content_type)
        print("OCR Extracted Text:", text)

        # Aadhaar number: 12 digits pattern (e.g., 1234 5678 9012)
        aadhaar_number_match = re.search(r'\b\d{4}\s\d{4}\s\d{4}\b', text)
        aadhaar_number = aadhaar_number_match.group().replace(" ", "") if aadhaar_number_match else None

        # DOB: Match DD-MM-YYYY, DD/MM/YYYY, DD MM YYYY, or YYYY-MM-DD
        dob_match = re.search(r'\b(?:\d{2}[/-]\d{2}[/-]\d{4}|\d{2}\s\d{2}\s\d{4}|\d{4}-\d{2}-\d{2})\b', text)
        dob = dob_match.group() if dob_match else None

        # Name: Match multi-word name (2-3 words, near DOB or Male)
        name_match = re.search(r'(?:(?:DOB|Male).*\n.*\b([A-Za-z]{2,}\s+[A-Za-z]{2,}(?:\s+[A-Za-z]{2,})?)\b)|(?:\b([A-Za-z]{2,}\s+[A-Za-z]{2,}(?:\s+[A-Za-z]{2,})?)\b)', text, re.IGNORECASE)
        name = (name_match.group(1) or name_match.group(2)).strip() if name_match else None

        if aadhaar_number and re.match(r'^\d{12}$', aadhaar_number):
            aadhaar_data["aadhaar_number"] = aadhaar_number
            aadhaar_data["valid"] = True

        if dob:
            try:
                if "/" in dob:
                    dob_date = datetime.strptime(dob, "%d/%m/%Y")
                elif "-" in dob:
                    dob_date = datetime.strptime(dob, "%d-%m-%Y") if len(dob.split("-")[0]) == 2 else datetime.strptime(dob, "%Y-%m-%d")
                else:
                    dob_date = datetime.strptime(dob, "%d %m %Y")
                aadhaar_data["dob"] = dob
                age = (datetime.now() - dob_date).days // 365
                aadhaar_data["is_18_or_older"] = age >= 18
            except ValueError:
                aadhaar_data["dob"] = None
                aadhaar_data["is_18_or_older"] = False

        aadhaar_data["name"] = name

        if not aadhaar_data["valid"]:
            aadhaar_data["error"] = "Could not extract valid Aadhaar details"

        # Mask Aadhaar number
        if aadhaar_data["aadhaar_number"]:
            aadhaar_data["aadhaar_number"] = f"XXXX XXXX {aadhaar_data['aadhaar_number'][-4:]}"

        return aadhaar_data

    except Exception as e:
        aadhaar_data["error"] = str(e)
        aadhaar_data["valid"] = False
        return aadhaar_data