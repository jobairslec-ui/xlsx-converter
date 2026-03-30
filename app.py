from flask import Flask, request, jsonify
import pandas as pd
import io
import traceback

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file in request. Keys: ' + str(list(request.files.keys())) + ' Form: ' + str(list(request.form.keys()))}), 400
        file = request.files['file']
        data = file.read()
        if len(data) == 0:
            return jsonify({'error': 'File is empty'}), 400
        df = pd.read_excel(io.BytesIO(data), header=0)
        return jsonify({'csv': df.to_csv(index=False)})
    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/')
def health():
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
