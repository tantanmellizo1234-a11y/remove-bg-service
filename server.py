import io
from flask import Flask, request, send_file, jsonify
from PIL import Image
import threading
# Lazy import rembg to speed up startup and allow immediate port binding
remove_fn = None
session = None

app = Flask(__name__)

# Preload rembg in a background thread so the first request is faster
def _preload_rembg():
    global remove_fn, session
    try:
        from rembg import remove as _remove, new_session as _new_session
        remove_fn = _remove
        # Use a lighter/faster model to reduce processing time on free-tier CPU
        session = _new_session("u2netp")
        # Warm up the model to avoid first-request timeouts
        try:
            from PIL import Image as _Image
            blank_img = _Image.new("RGBA", (8, 8), (0, 0, 0, 0))
            remove_fn(blank_img, session=session)
        except Exception as warm_e:
            print(f"rembg warm-up failed (continuing): {warm_e}")
    except Exception as e:
        print(f"rembg preload failed: {e}")

threading.Thread(target=_preload_rembg, daemon=True).start()

def downscale_if_needed(img: Image.Image, max_dim: int = 1024) -> Image.Image:
    try:
        w, h = img.size
        if max(w, h) > max_dim:
            # Use thumbnail to preserve aspect ratio and reduce memory
            img = img.copy()
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        return img
    except Exception:
        # If anything goes wrong, return original image
        return img

@app.get("/")
def health():
    return jsonify({"status": "ok"})

@app.post("/remove-bg")
def remove_bg():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "Missing 'image' file field"}), 400

    try:
        # Initialize rembg lazily on first request to avoid heavy import at startup
        global remove_fn, session
        if remove_fn is None or session is None:
            from rembg import remove as _remove, new_session as _new_session
            remove_fn = _remove
            session = _new_session("u2netp")

        # Read the image from the uploaded file
        img = Image.open(file.stream).convert("RGBA")
        img = downscale_if_needed(img, max_dim=1024)

        # Remove background using rembg (returns PIL Image)
        out_img = remove_fn(img, session=session)

        # Encode as PNG bytes
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")
    except Exception as e:
        # Return plaintext error for easier client-side logging
        return (str(e), 500, {"Content-Type": "text/plain"})

if __name__ == "__main__":
    # Local dev run: python server.py
    # On Render, use gunicorn with a start command binding to $PORT
    app.run(host="0.0.0.0", port=5000)
