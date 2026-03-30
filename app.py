from flask import Flask, request, jsonify
import pandas as pd
import io, base64

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert():
    try:
        file_b64 = request.get_json().get('file')
        file_bytes = base64.b64decode(file_b64)
        df = pd.read_excel(io.BytesIO(file_bytes), header=0)
        return jsonify({'csv': df.to_csv(index=False)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def health():
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
```
