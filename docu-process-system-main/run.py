"""
Complete startup script to run all services
"""

import subprocess
import time
import os


def main():
    """Start all services in the correct order"""

    print("Starting Document Processing System...")

    # Create necessary directories
    os.makedirs("robot_folder", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Start services using Docker Compose
    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        print("All services started successfully!")
        print("\nService URLs:")
        print("- Main API: http://localhost:8000")
        print("- Analysis Service: http://localhost:8001")
        print("- Email Service: http://localhost:8002")
        print("- RPA Service: http://localhost:8003")
        print("\nAPI Documentation:")
        print("- Main API Docs: http://localhost:8000/docs")

    except subprocess.CalledProcessError as e:
        print(f"Error starting services: {e}")
        return False

    return True


if __name__ == "__main__":
    main()