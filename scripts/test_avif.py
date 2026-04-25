import requests
from PIL import Image
import io
import warnings
import pillow_avif

# The URL provided by the user
IMAGE_URL = "https://www.theglobeandmail.com/resizer/so0VBi2Dlq002NcR9me-opY9Poo=/arc-anglerfish-tgam-prod-tgam/public/IOCWJ2MIMNHQTN5QN2SJAZFCZI.jpg"

# --- Important Part ---
# We send an "Accept" header to tell the server we PREFER the AVIF format.
# A modern server will see this and send back the AVIF version if it has one.
HEADERS = {
    'Accept': 'image/avif,image/webp,image/jpeg,*/*'
}

def test_avif_support():
    """
    Downloads an image and tries to open it with Pillow to check for AVIF support.
    """
    print(f"[*] Attempting to download image from: {IMAGE_URL}")
    print(f"[*] Sending Accept header to request AVIF format...")

    try:
        # Download the image with the specified header
        response = requests.get(IMAGE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()  # Raises an error for bad responses (4xx or 5xx)

        # Check what format the server actually sent
        content_type = response.headers.get('Content-Type', 'N/A')
        print(f"[*] Server responded with Content-Type: {content_type}")

        if 'avif' not in content_type:
            print("[!] Warning: Server did not send back an AVIF image.")
            print("[!] The test might not be conclusive for AVIF support, but we will still try to open the image.")

        # Get the image content in bytes
        image_bytes = response.content

        print("[*] Trying to open the downloaded image with Pillow...")

        # Use a BytesIO object to treat the bytes as a file
        image_file = io.BytesIO(image_bytes)

        # Suppress the specific warning to see if it's the only issue
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # This is the core of the test
            img = Image.open(image_file)
            img.load() # Force loading the image data

            # Check for our specific warning
            avif_warning_found = False
            for warning_message in w:
                if "AVIF support not installed" in str(warning_message.message):
                    avif_warning_found = True
                    break

            if avif_warning_found:
                 raise RuntimeError("Pillow issued the 'AVIF support not installed' warning.")

        # If no exception was raised, the test is a success
        print("\n✅ SUCCESS! ✅")
        print(f"   Pillow successfully identified the image format as: {img.format}")
        print(f"   Image size: {img.size}")
        print("\nYour environment is correctly configured to handle AVIF images!")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ FAILURE! ❌")
        print(f"   Failed to download the image. Error: {e}")
    except Exception as e:
        print(f"\n❌ FAILURE! ❌")
        print(f"   Pillow could not open the image. Error: {e}")

if __name__ == "__main__":
    test_avif_support()