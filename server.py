import io
from flask import Flask, request, send_file, jsonify
from PIL import Image
from rembg import remove

app = Flask(__name__)

@app.get("/")
def health():
    return jsonify({"status": "ok"})

@app.post("/remove-bg")
def remove_bg():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Missing 'image' file field"}), 400

    try:
        # Read the image from the uploaded file
        img = Image.open(file.stream).convert("RGBA")

        # Remove background using rembg (returns PIL Image)
        out_img = remove(img)

        # Encode as PNG bytes
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Local dev run: python server.py
    # On Render, use gunicorn with a start command binding to $PORT
    app.run(host="0.0.0.0", port=5000)