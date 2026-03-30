from flask import Flask, request, jsonify
import pandas as pd
import io

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert():
    try:
        file = request.files.get('file')
        df = pd.read_excel(io.BytesIO(file.read()), header=0)
        return jsonify({'csv': df.to_csv(index=False)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def health():
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
