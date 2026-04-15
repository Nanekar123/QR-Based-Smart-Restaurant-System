import qrcode
import os

BASE_URL = "http://10.150.202.166:5000/menu?table="

output_folder = "utils/static/qr"
os.makedirs(output_folder, exist_ok=True)

for i in range(1, 11):
    url = BASE_URL + str(i)

    qr = qrcode.make(url)
    qr.save(f"{output_folder}/table_{i}.png")

print("✅ QR Codes Generated Successfully!")