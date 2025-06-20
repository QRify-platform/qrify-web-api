import qrcode
import re
from io import BytesIO
from utils.s3_utils import upload_to_s3

def generate_qr_code(url: str) -> dict:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    file_name = "qr_codes/" + re.sub(r'[^\w\-_.]', '_', url) + ".png"
    return upload_to_s3(img_byte_arr, file_name)