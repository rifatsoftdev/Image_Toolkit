import uvicorn
import socket


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=get_ip(),
        port=8000,
        reload=True,
        log_level="info"
    ) 

# uvicorn app.main:app --reload

# docker build --no-cache -t pocketpay-server .
# docker run -p 8000:8000 pocketpay-server