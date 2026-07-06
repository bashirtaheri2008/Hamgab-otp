from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import random
import string
import requests
import os
from datetime import datetime, timedelta
import secrets

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# تنظیمات SMS Gateway 24
SMS_GATEWAY_URL = os.environ.get('SMS_GATEWAY_URL', 'https://api.smsgateway24.com')
API_KEY = os.environ.get('SMS_GATEWAY_API_KEY', 'YOUR_API_KEY')
SENDER_ID = os.environ.get('SMS_GATEWAY_SENDER_ID', 'YOUR_PHONE_NUMBER')

otp_store = {}

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

@app.route('/')
def serve_index():
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
    try:
        sendto = request.form.get('sendto')
        body = request.form.get('body')
        if not sendto or not body:
            return 'شماره و متن الزامی است', 400
        
        payload = {'to': sendto, 'message': body, 'sender': SENDER_ID}
        headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
        response = requests.post(f'{SMS_GATEWAY_URL}/send-sms', json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return 'SMS ارسال شد', 200
        return 'خطا در ارسال SMS', 500
    except Exception as e:
        return f'خطا: {str(e)}', 500

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
    app.run(host='0.0.0.0', port=port, debug=False)
