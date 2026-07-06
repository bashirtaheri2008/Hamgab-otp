from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import requests
import random
import os
from datetime import datetime, timedelta
import secrets

app = Flask(__name__, static_folder='.')
CORS(app)

# ========== کلیدهای ثابت (همانهایی که خودت داری) ==========
TOKEN = '43b74ee7c5e883832f9d71300587c112'
API_URL = 'https://smsgateway24.com/getdata/addsms'
DEVICE_ID = '13068'

# ========== ذخیره OTP ==========
otp_store = {}

def generate_otp():
    return str(random.randint(100000, 999999))

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/generate-code', methods=['GET'])
def generate_code():
    code = generate_otp()
    request_id = secrets.token_urlsafe(16)
    otp_store[request_id] = {
        'code': code,
        'timestamp': datetime.now(),
        'verified': False
    }
    return jsonify({'code': code, 'requestId': request_id})

@app.route('/send-sms', methods=['POST'])
def send_sms():
    phone = request.form.get('sendto', '').strip()
    code = request.form.get('body', '').strip()
    
    # فرمت کردن شماره
    if not phone.startswith('+'):
        phone = '+93' + phone.replace('^0+', '')
    
    data = {
        'token': TOKEN,
        'sendto': phone,
        'body': code,
        'device_id': DEVICE_ID,
        'sim': '1'
    }
    
    try:
        response = requests.post(API_URL, data=data)
        return response.text, response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    request_id = data.get('requestId')
    code = data.get('code')
    
    if not request_id or not code:
        return jsonify({'success': False, 'message': 'اطلاعات ناقص'}), 400
    
    stored = otp_store.get(request_id)
    if not stored:
        return jsonify({'success': False, 'message': 'کد منقضی شده است'}), 404
    if stored['verified']:
        return jsonify({'success': False, 'message': 'کد قبلاً استفاده شده است'}), 400
    if datetime.now() - stored['timestamp'] > timedelta(minutes=5):
        del otp_store[request_id]
        return jsonify({'success': False, 'message': 'کد منقضی شده است'}), 404
    
    if stored['code'] == code:
        stored['verified'] = True
        return jsonify({'success': True, 'message': 'تأیید موفق'})
    return jsonify({'success': False, 'message': 'کد اشتباه است'}), 400

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'OK', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('🚀 سرور در حال اجرا...')
    print(f'📡 پورت: {port}')
    app.run(host='0.0.0.0', port=port, debug=False)
