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

        # Force columns N and O to numeric
        df.iloc[:, 13] = pd.to_numeric(df.iloc[:, 13], errors='coerce').fillna(0)
        df.iloc[:, 14] = pd.to_numeric(df.iloc[:, 14], errors='coerce').fillna(0)
        # Fill column E NaN with empty string
        df.iloc[:, 4] = df.iloc[:, 4].fillna('').astype(str)

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

        # ── Keyword lists (matching ChatGPT prompt exactly) ──

        # Nutique PB keywords (checked on normalized text: lowercase, no spaces/underscores/hyphens)
        pb_kw_norm = [
            'peanutbutter', 'peanut', 'creamy', 'darkchocolate', 'whitechocolate',
            'chocolatecombo', 'pbcombo', 'macapowder', 'oliveoil'
        ]
        # Nutique PB Bengali (checked on original text)
        pb_kw_bengali = [
            '\u09aa\u09bf\u09a8\u09be\u099f',        # পিনাট
            '\u09ac\u09be\u099f\u09be\u09b0',          # বাটার
            '\u0995\u09cd\u09b0\u09bf\u09ae\u09bf',    # ক্রিমি
            '\u099a\u0995\u09b2\u09c7\u099f',          # চকলেট
            '\u09ae\u09be\u0995\u09be',                # মাকা
            '\u099c\u09be\u09df\u09a4\u09c1\u09a8'     # জায়তুন
        ]
        # dark/white exclusions for PB detection
        dw_excl = ['ml', 'dior', 'chanel', 'opium', 'orchid']

        # Nutique Niramay keywords (normalized)
        niramay_kw_norm = [
            'niramay', 'niramoy', 'stressrelief', 'painrelief', 'painspray', 'reliefcombo'
        ]
        # Niramay Bengali (original text)
        niramay_kw_bengali = [
            '\u09a8\u09bf\u09b0\u09be\u09ae\u09df\u09bc',  # নিরাময়
            '\u09b8\u09cd\u099f\u09cd\u09b0\u09c7\u09b8',  # স্ট্রেস
            '\u09b0\u09bf\u09b2\u09bf\u09ab',              # রিলিফ
            '\u09ac\u09cd\u09af\u09a5\u09be'               # ব্যথা
        ]

        # Ayra keywords (checked on normalized text)
        ayra_kw_norm = [
            'hair', 'facewash', 'serum', 'cream', 'moisturizer', 'sunscreen',
            'toner', 'scrub', 'bodylotion', 'bodybutter', 'skincare',
            'shampoo', 'shampo', 'newshampo', 'conditioner',
            'tonic', 'rosemary', 'rosemerit', 'rmint', 'mint',
            'caffeine', 'caffiene', 'caffine',
            'hairpack', 'facepack', 'facemask', 'facemusk', 'acnemusk', 'acnefree',
            'facial', 'essentialoil', 'coconutoil', 'coconut', 'castor',
            'blackseed', 'teatree', 'goldenoil', 'reviveoil', 'ricetonic',
            'protein', 'ayra', 'antidandruff', 'goldenoil', 'driedleaves',
            'glow', 'glowdust', 'facemaskcombo', '3facepackcombo',
            'facialmaskcombo', 'coustom', 'oil'
        ]

        # ── Counters ──
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
            inv_raw = str(row.iloc[4]).strip()
            cod = int(row.iloc[13])
            ship = int(row.iloc[14])

            inv_lower = inv_raw.lower()
            inv_norm = inv_lower.replace(' ', '').replace('_', '').replace('-', '')

            # ── STEP 1: Exclude ──
            if re.match(r'^\d{6}-\d+', inv_raw):
                excluded += 1
                continue
            if 'spraymatha' in inv_lower or 'spray-matha' in inv_lower or 'spray_matha' in inv_lower:
                excluded += 1
                continue
            if '228283819' in inv_raw:
                excluded += 1
                continue

            # ── STEP 2: Fixed price (before keyword matching) ──
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

            # ── STEP 3A: Nutique PB ──
            is_pb = False
            # Check normalized keywords
            for kw in pb_kw_norm:
                if kw in inv_norm:
                    is_pb = True
                    break
            # Check dark/white PB combos (not perfume)
            if not is_pb and ('dark' in inv_norm or 'white' in inv_norm):
                if not any(x in inv_norm for x in dw_excl):
                    is_pb = True
            # Check Bengali
            if not is_pb:
                for kw in pb_kw_bengali:
                    if kw in inv_raw:
                        is_pb = True
                        break
            if is_pb:
                nutique_pb += 1
                continue

            # ── STEP 3B: Nutique Niramay ──
            is_nir = False
            for kw in niramay_kw_norm:
                if kw in inv_norm:
                    is_nir = True
                    break
            if not is_nir:
                for kw in niramay_kw_bengali:
                    if kw in inv_raw:
                        is_nir = True
                        break
            if is_nir:
                nutique_niramay += 1
                continue

            # ── STEP 3C: Ayra ──
            is_ayra = False
            for kw in ayra_kw_norm:
                if kw in inv_norm:
                    is_ayra = True
                    break
            if is_ayra:
                ayra_identified += 1
                ayra_cod += cod
                ayra_ship += ship
                continue

            # ── STEP 3D: Aroma (everything else) ──
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
