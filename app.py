from flask import Flask, request, jsonify
import pandas as pd
import io
import re
import traceback
from datetime import datetime

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


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        data = file.read()
        if len(data) == 0:
            return jsonify({'error': 'File is empty'}), 400

        df = pd.read_excel(io.BytesIO(data), header=0)

        # Extract date from first row
        date_str = "unknown"
        try:
            raw_date = df.iloc[0, 0]
            if isinstance(raw_date, datetime):
                date_str = raw_date.strftime('%Y-%m-%d')
            elif hasattr(raw_date, 'strftime'):
                date_str = raw_date.strftime('%Y-%m-%d')
            elif raw_date:
                for fmt in ['%Y-%m-%d %I:%M:%S %p', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d-%m-%Y']:
                    try:
                        date_str = datetime.strptime(str(raw_date).strip(), fmt).strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
        except Exception:
            pass

        # Keywords
        ayra_kw = [
            'hair', 'facewash', 'serum', 'cream', 'moisturizer', 'sunscreen',
            'toner', 'scrub', 'bodylotion', 'skincare', 'shampoo', 'shampo',
            'conditioner', 'tonic', 'rosemary', 'mint', 'caffeine', 'caffiene',
            'caffine', 'hairpack', 'facepack', 'facemask', 'facemusk', 'acnemusk',
            'acnefree', 'facial', 'coconut', 'castor', 'blackseed', 'teatree',
            'goldenoil', 'reviveoil', 'ricetonic', 'protein', 'ayra',
            'antidandruff', 'driedleaves', 'glowdust'
        ]
        pb_kw = ['peanut', 'creamy', 'darkchocolate', 'whitechocolate',
                 'pbcombo', 'macapowder', 'oliveoil']
        dw_excl = ['ml', 'dior', 'chanel', 'opium', 'orchid']
        niramay_kw = ['niramay', 'niramoy', 'stressrelief', 'painrelief',
                      'painspray', 'reliefcombo']

        # Counters
        nutique_pb = 0
        nutique_niramay = 0
        ayra_identified = 0
        ayra_fixed_900 = 0
        ayra_fixed_1100 = 0
        ayra_cod = 0
        ayra_ship = 0
        aroma_identified = 0
        aroma_fixed_899 = 0
        aroma_fixed_1099 = 0
        aroma_cod = 0
        aroma_ship = 0
        excluded = 0

        for _, row in df.iterrows():
            inv_raw = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ""
            try:
                cod = int(float(row.iloc[13])) if pd.notna(row.iloc[13]) else 0
            except (ValueError, TypeError):
                cod = 0
            try:
                ship = int(float(row.iloc[14])) if pd.notna(row.iloc[14]) else 0
            except (ValueError, TypeError):
                ship = 0

            inv_lower = inv_raw.lower()
            inv_norm = inv_lower.replace(' ', '').replace('_', '').replace('-', '')

            # STEP 1: Exclude
            if re.match(r'\d{6}-\d{5}', inv_raw):
                excluded += 1
                continue
            if 'spraymatha' in inv_lower:
                excluded += 1
                continue
            if '228283819' in inv_raw:
                excluded += 1
                continue

            # STEP 2: Fixed price
            if cod == 900:
                ayra_fixed_900 += 1
                continue
            if cod == 1100:
                ayra_fixed_1100 += 1
                continue
            if cod == 899:
                aroma_fixed_899 += 1
                continue
            if cod == 1099:
                aroma_fixed_1099 += 1
                continue

            # STEP 3A: Nutique PB
            is_pb = any(k in inv_norm for k in pb_kw)
            if not is_pb and ('dark' in inv_norm or 'white' in inv_norm):
                if not any(x in inv_norm for x in dw_excl):
                    is_pb = True
            if not is_pb and ('\u09aa\u09bf\u09a8\u09be\u099f' in inv_raw or '\u09ac\u09be\u099f\u09be\u09b0' in inv_raw):
                is_pb = True
            if is_pb:
                nutique_pb += 1
                continue

            # STEP 3B: Nutique Niramay
            is_nir = any(k in inv_norm for k in niramay_kw)
            if not is_nir and ('\u09b8\u09cd\u099f\u09cd\u09b0\u09c7\u09b8' in inv_raw or '\u09b0\u09bf\u09b2\u09bf\u09ab' in inv_raw or '\u09a8\u09bf\u09b0\u09be\u09ae\u09df\u09bc' in inv_raw):
                is_nir = True
            if is_nir:
                nutique_niramay += 1
                continue

            # STEP 3C: Ayra
            if any(k in inv_norm for k in ayra_kw):
                ayra_identified += 1
                ayra_cod += cod
                ayra_ship += ship
                continue

            # STEP 3D: Aroma (everything else)
            aroma_identified += 1
            aroma_cod += cod
            aroma_ship += ship

        return jsonify({
            "date": date_str,
            "nutique": {"pb": nutique_pb, "niramay": nutique_niramay},
            "ayra": {
                "identified": ayra_identified,
                "fixed_900": ayra_fixed_900,
                "fixed_1100": ayra_fixed_1100,
                "net_cod": ayra_cod - ayra_ship,
                "total": ayra_identified + ayra_fixed_900 + ayra_fixed_1100
            },
            "aroma": {
                "identified": aroma_identified,
                "fixed_899": aroma_fixed_899,
                "fixed_1099": aroma_fixed_1099,
                "net_cod": aroma_cod - aroma_ship,
                "total": aroma_identified + aroma_fixed_899 + aroma_fixed_1099
            },
            "excluded_count": excluded,
            "error": None
        })

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/')
def health():
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
